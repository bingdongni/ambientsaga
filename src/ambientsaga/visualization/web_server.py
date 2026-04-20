"""
Web visualization server — serves the world visualization over HTTP and WebSocket.

Provides:
- HTTP server for the HTML/JS client
- WebSocket server for real-time world state streaming
- REST API for world data queries
- JSON-serializable world state for web consumption

The web client renders the world using HTML5 Canvas on the client side,
with world state streamed from this server via WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ambientsaga.config import VisualizationConfig
    from ambientsaga.world.state import World

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Message Types
# ---------------------------------------------------------------------------


class WSMessageType(Enum):
    """WebSocket message types."""

    WORLD_STATE = auto()       # Full world state snapshot
    TICK_UPDATE = auto()       # Incremental tick update
    AGENT_UPDATE = auto()      # Agent position/state change
    SIGNAL_UPDATE = auto()     # Signal broadcast
    EVENT = auto()             # World event notification
    METRICS = auto()           # Metrics data
    CAMERA = auto()            # Camera position update
    CHAT = auto()              # Agent communication
    ERROR = auto()             # Error message
    PING = auto()              # Keepalive


# ---------------------------------------------------------------------------
# Web State
# ---------------------------------------------------------------------------


@dataclass
class ConnectedClient:
    """State for a connected web client."""

    client_id: str
    websocket = None  # Will be set by websocket library
    camera_x: float = 0.0
    camera_y: float = 0.0
    zoom: float = 1.0
    subscribed_events: set[str] = None
    last_ping: float = 0.0

    def __post_init__(self) -> None:
        self.subscribed_events = set()


@dataclass
class WebServerStats:
    """Statistics about the web server."""

    clients_connected: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    uptime_seconds: float = 0.0


# ---------------------------------------------------------------------------
# WebServer
# ---------------------------------------------------------------------------


class WebServer:
    """
    WebSocket/HTTP server for real-time world visualization.

    The server:
    1. Serves the HTML/JS client over HTTP
    2. Maintains WebSocket connections with browser clients
    3. Broadcasts world state updates at a configurable rate
    4. Handles client input (camera, zoom, queries)

    Uses the 'websockets' library for WebSocket support.
    """

    def __init__(
        self,
        world: World,
        config: VisualizationConfig,
        host: str = "localhost",
        port: int = 8765,
    ) -> None:
        self.world = world
        self.config = config
        self.host = host
        self.port = port

        # Connected clients: set of websocket connections
        self._clients: set[Any] = set()
        self._clients_lock = threading.RLock()  # Use RLock for nested access

        # Server state
        self._running = False
        self._server = None
        self._server_thread: threading.Thread | None = None
        self._async_loop: asyncio.AbstractEventLoop | None = None

        # Thread-safe async runner
        self._broadcast_queue: asyncio.Queue = None

        # Task reference to prevent duplicate processing tasks
        self._broadcast_task: asyncio.Task | None = None

        # Stats (thread-safe with lock)
        self._start_time = time.time()
        self._messages_sent = 0
        self._bytes_sent = 0
        self._stats_lock = threading.Lock()

        # World state cache for efficient broadcasting
        self._world_state_cache: dict[str, Any] | None = None
        self._last_broadcast_tick: int = -1

    def start(self) -> bool:
        """Start the web server."""
        if self._running:
            return True

        try:
            self._running = True
            self._server_thread = threading.Thread(
                target=self._run_server, daemon=True
            )
            self._server_thread.start()
            logger.info(f"Web server started at http://{self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            self._running = False
            return False

    def _run_server(self) -> None:
        """Run the asyncio server."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._async_loop = loop
        self._broadcast_queue = asyncio.Queue()
        try:
            loop.run_until_complete(self._start_ws_server())
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")
        finally:
            loop.close()
            self._async_loop = None

    async def _start_ws_server(self) -> None:
        """Start the WebSocket server."""
        import websockets
        from websockets.exceptions import ConnectionClosed

        async def ping_clients():
            """Periodically ping clients to detect dead connections."""
            while self._running:
                await asyncio.sleep(30)  # Ping every 30 seconds
                if not self._running:
                    break

                disconnected = []
                with self._clients_lock:
                    for client in list(self._clients):
                        try:
                            await asyncio.wait_for(client.ping(), timeout=5.0)
                        except Exception:
                            disconnected.append(client)

                # Clean up disconnected clients
                if disconnected:
                    with self._clients_lock:
                        for client in disconnected:
                            self._clients.discard(client)
                    logger.debug(f"Cleaned up {len(disconnected)} dead connections")

        async def handler(websocket: Any, path: str) -> None:
            # Register client
            with self._clients_lock:
                self._clients.add(websocket)

            addr = getattr(websocket, 'remote_address', None) or (self.host,)
            client_id = f"{addr[0]}:{addr[1]}" if addr else str(id(websocket))
            logger.info(f"Client connected: {client_id}")

            try:
                # Send initial world state
                await self._send_world_state(websocket)

                # Handle messages
                async for message in websocket:
                    await self._handle_message(websocket, message)

            except ConnectionClosed:
                pass
            except Exception as e:
                # Only log non-trivial errors
                if "1000" not in str(e):  # Not normal closure
                    logger.debug(f"Client {client_id} error: {e}")
            finally:
                with self._clients_lock:
                    self._clients.discard(websocket)
                logger.info(f"Client disconnected: {client_id}")

        async def start_server() -> None:
            try:
                async with websockets.serve(handler, self.host, self.port):
                    self._running = True
                    # Start heartbeat task
                    heartbeat_task = asyncio.create_task(ping_clients())
                    try:
                        await asyncio.Future()  # Run forever
                    finally:
                        heartbeat_task.cancel()
            except OSError as e:
                logger.error(f"WebSocket server error: {e}")
                self._running = False

        await start_server()

    async def _handle_message(self, websocket: Any, message: str) -> None:
        """Handle a message from a client."""
        try:
            msg = json.loads(message)
        except json.JSONDecodeError:
            return

        msg_type = msg.get("type", "")

        if msg_type == "camera":
            # Camera update - just acknowledge, don't store per-client state
            pass
        elif msg_type == "ping":
            await websocket.send(json.dumps({"type": "PONG", "time": time.time()}))
        elif msg_type == "query":
            response = self._handle_query(msg.get("query", ""))
            await websocket.send(json.dumps(response))
        elif msg_type == "subscribe":
            # Subscription acknowledged
            pass

    async def _send_world_state(self, websocket: Any) -> None:
        """Send initial world state to a new client."""
        state = self._serialize_world_state()
        payload = json.dumps({
            "type": "WORLD_STATE",
            "payload": state,
            "tick": self.world.tick,
        })
        await websocket.send(payload)
        self._messages_sent += 1
        self._bytes_sent += len(payload.encode())

    def broadcast_world_update(self) -> None:
        """Broadcast world state update to all connected clients."""
        if not self._running:
            return

        # Create update payload (only if tick changed)
        if self._last_broadcast_tick == self.world.tick:
            return
        self._last_broadcast_tick = self.world.tick

        payload = self._create_tick_update()

        # Queue broadcast for async execution
        self._queue_broadcast(payload)

    async def _broadcast_to_clients(self, payload: dict[str, Any]) -> None:
        """Send payload to all connected clients."""
        data = json.dumps(payload)
        clients_snapshot: list
        with self._clients_lock:
            clients_snapshot = list(self._clients)

        disconnected = []
        for client in clients_snapshot:
            try:
                await client.send(data)
                # Thread-safe stats update
                with self._stats_lock:
                    self._messages_sent += 1
                    self._bytes_sent += len(data.encode())
            except Exception:
                disconnected.append(client)

        # Clean up disconnected clients
        if disconnected:
            with self._clients_lock:
                for client in disconnected:
                    self._clients.discard(client)

    def broadcast_event(self, event_type: str, data: dict) -> None:
        """Broadcast a world event to all clients."""
        payload = {
            "type": "EVENT",
            "event_type": event_type,
            "payload": data,
            "tick": self.world.tick,
        }
        self._queue_broadcast(payload)

    def _queue_broadcast(self, payload: dict[str, Any]) -> None:
        """Queue a broadcast to be sent to all clients asynchronously."""
        if not self._running:
            return

        # Queue the payload if async loop is available
        if self._broadcast_queue is not None and self._async_loop is not None:
            try:
                self._broadcast_queue.put_nowait(payload)
            except Exception:
                pass

            # Schedule processing via call_soon_threadsafe
            # Use run_coroutine_threadsafe for thread-safe coroutine scheduling
            if self._broadcast_task is None or self._broadcast_task.done():
                try:
                    async def process_and_clear():
                        await self._process_broadcast_queue()
                        self._broadcast_task = None
                    # run_coroutine_threadsafe returns a Future that can be used to wait for result
                    self._broadcast_task = asyncio.run_coroutine_threadsafe(
                        process_and_clear(), self._async_loop
                    )
                except Exception:
                    pass
        else:
            # Fallback: skip broadcast if no async loop available
            pass

    def _fallback_broadcast(self, payload: dict[str, Any]) -> None:
        """Fallback broadcast when async loop is not available."""
        # No-op fallback - skip broadcast silently
        pass

    async def _process_broadcast_queue(self) -> None:
        """Process queued broadcasts."""
        if self._broadcast_queue is None:
            return

        while not self._broadcast_queue.empty():
            try:
                payload = self._broadcast_queue.get_nowait()
                await self._broadcast_to_clients(payload)
            except asyncio.QueueEmpty:
                break
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def stop(self) -> None:
        """Stop the web server."""
        if not self._running:
            return
        self._running = False

        # Clear all client connections
        # The server thread's event loop will handle graceful shutdown
        with self._clients_lock:
            self._clients.clear()

        # The server thread will clean up its own event loop
        logger.info("Web server stopped")

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _get_happiness(self, agent: Any) -> float:
        """Get happiness from an agent (handles different attribute names)."""
        if hasattr(agent, "emotional_state") and hasattr(agent.emotional_state, "happiness"):
            return agent.emotional_state.happiness
        # Fallback: derive from health
        if hasattr(agent, "health"):
            return agent.health - 0.5
        return 0.0

    def _get_beliefs(self, agent: Any) -> list[dict]:
        """Get beliefs from an agent (handles different data structures)."""
        beliefs = getattr(agent, "beliefs", [])
        if isinstance(beliefs, dict):
            return [
                {"topic": str(k), "strength": round(float(v), 2)}
                for k, v in list(beliefs.items())[:10]
            ]
        # It's a list - extract belief_id/strength or content/strength
        result = []
        for b in list(beliefs)[:10]:
            if hasattr(b, "belief_id"):
                result.append({"topic": b.belief_id, "strength": round(float(getattr(b, "strength", 0.5)), 2)})
            elif hasattr(b, "content"):
                result.append({"topic": b.content[:30], "strength": round(float(getattr(b, "strength", 0.5)), 2)})
        return result

    def _serialize_world_state(self) -> dict[str, Any]:
        """Serialize the current world state for the web client."""
        config = self.world._config.world

        # Serialize terrain as a compact 2D array
        terrain = self.world._terrain
        terrain_data = None
        if terrain is not None:
            # Downsample terrain for network efficiency
            step = max(1, min(config.width, config.height) // 256)
            terrain_data = terrain[::step, ::step].tolist()

        # Serialize agents (L1 only for bandwidth)
        agents = []
        for agent in self.world.get_all_agents():
            if not agent.is_alive:
                continue

            tier = getattr(agent, "tier", None)
            tier_value = getattr(tier, "value", None)
            # Skip L3/L4 for bandwidth (handle both string and int tier values)
            should_skip = False
            if tier_value is not None:
                try:
                    if isinstance(tier_value, str):
                        # String tier like "l1_core", skip if not L1
                        if not tier_value.startswith("l1"):
                            should_skip = True
                    elif int(tier_value) > 1:
                        should_skip = True
                except (ValueError, TypeError):
                    pass
            if should_skip:
                continue

            agents.append({
                "id": agent.entity_id,
                "name": agent.name[:20],
                "x": round(float(agent.position.x), 1),
                "y": round(float(agent.position.y), 1),
                "tier": tier_value if tier_value is not None else 3,
                "happiness": round(self._get_happiness(agent), 2),
                "wealth": round(float(agent.wealth), 1),
                "goal": (agent.current_goal[:50] if agent.current_goal else ""),
            })

        # Serialize active signals
        signals = []
        signal_bus = self.world._signal_bus
        if signal_bus:
            for signal in signal_bus._active_signals[:50]:  # Limit to 50
                signals.append({
                    "type": signal.signal_type.name,
                    "x": round(float(signal.source_pos.x), 1),
                    "y": round(float(signal.source_pos.y), 1),
                    "radius": round(float(signal.radius), 1),
                    "intensity": round(float(signal.intensity), 2),
                })

        return {
            "world": {
                "width": config.width,
                "height": config.height,
                "terrain": terrain_data,
                "terrain_step": max(1, min(config.width, config.height) // 256),
            },
            "agents": agents,
            "agent_count": self.world.get_agent_count(),
            "signals": signals,
        }

    def _create_tick_update(self) -> dict[str, Any]:
        """Create an incremental tick update payload."""

        updated_agents = []
        for agent in self.world.get_all_agents():
            if not agent.is_alive:
                continue

            tier = getattr(agent, "tier", None)
            tier_value = getattr(tier, "value", None)
            # Skip L3/L4 for bandwidth (handle both string and int tier values)
            if tier_value is not None:
                try:
                    if isinstance(tier_value, str):
                        # String tier like "l1_core", skip if not L1
                        if not tier_value.startswith("l1"):
                            continue
                    elif int(tier_value) > 1:
                        continue
                except (ValueError, TypeError):
                    pass

            updated_agents.append({
                "id": agent.entity_id,
                "x": round(float(agent.position.x), 1),
                "y": round(float(agent.position.y), 1),
                "happiness": round(self._get_happiness(agent), 2),
                "wealth": round(float(agent.wealth), 1),
            })

        # Recent events from event log
        events = self.world._event_log.get_all_events() if self.world._event_log else []
        recent_events = []
        if events:
            for event in events[-20:]:
                recent_events.append({
                    "type": event.get("event_type", "unknown"),
                    "tick": event.get("tick", 0),
                    "subject": str(event.get("subject_id", ""))[:20],
                })

        return {
            "type": "TICK_UPDATE",
            "tick": self.world.tick,
            "agents": updated_agents,
            "agent_count": self.world.get_agent_count(),
            "events": recent_events,
        }

    def _handle_query(self, query: str) -> dict[str, Any]:
        """Handle a data query from a client."""
        if query == "world":
            return self._serialize_world_state()
        elif query == "metrics":
            return self.world._metrics.get_current_metrics() if self.world._metrics else {}
        elif query == "stats":
            return {
                "tick": self.world.tick,
                "agents": self.world.get_agent_count(),
                "organizations": len(self.world._organizations),
                "relationships": len(self.world._relationships),
            }
        elif query.startswith("agent:"):
            agent_id = query.split(":", 1)[1]
            agent = self.world.get_agent(agent_id)
            if agent:
                return {
                    "id": agent.entity_id,
                    "name": agent.name,
                    "position": {"x": float(agent.position.x), "y": float(agent.position.y)},
                    "wealth": round(float(agent.wealth), 1),
                    "happiness": round(self._get_happiness(agent), 2),
                    "tier": getattr(agent, "tier", None).value if getattr(agent, "tier", None) else 3,
                    "beliefs": self._get_beliefs(agent),
                    "relationships_count": len(agent.relationships),
                    "goal": (agent.current_goal[:100] if agent.current_goal else ""),
                }
        return {"error": f"Unknown query: {query}"}

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def get_stats(self) -> WebServerStats:
        """Get web server statistics."""
        with self._clients_lock:
            clients = len(self._clients)

        return WebServerStats(
            clients_connected=clients,
            messages_sent=self._messages_sent,
            bytes_sent=self._bytes_sent,
            uptime_seconds=time.time() - self._start_time,
        )


# ---------------------------------------------------------------------------
# HTML Client — embedded web interface
# ---------------------------------------------------------------------------

HTML_CLIENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AmbientSaga — AI World Simulation</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0f;
            color: #e0e0e0;
            font-family: 'Segoe UI', system-ui, sans-serif;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        #header {
            background: linear-gradient(90deg, #0a0a1a, #1a1a2e);
            padding: 8px 16px;
            display: flex;
            align-items: center;
            gap: 16px;
            border-bottom: 1px solid #333;
            flex-shrink: 0;
        }
        #header h1 {
            font-size: 16px;
            color: #ffd700;
            font-weight: 600;
            letter-spacing: 1px;
        }
        .stat {
            font-size: 12px;
            color: #aaa;
        }
        .stat span {
            color: #00ccff;
            font-weight: bold;
        }
        #main {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        #canvas-container {
            flex: 1;
            position: relative;
            overflow: hidden;
        }
        #world-canvas {
            display: block;
            cursor: grab;
        }
        #world-canvas:active { cursor: grabbing; }
        #sidebar {
            width: 300px;
            background: #0a0a12;
            border-left: 1px solid #333;
            overflow-y: auto;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .panel {
            background: #12121a;
            border: 1px solid #2a2a3a;
            border-radius: 6px;
            padding: 10px;
        }
        .panel h3 {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin-bottom: 8px;
        }
        .metric-row {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            padding: 3px 0;
        }
        .metric-row .label { color: #aaa; }
        .metric-row .value { color: #00ccff; font-weight: bold; }
        .metric-row .value.good { color: #44ff88; }
        .metric-row .value.bad { color: #ff4444; }
        #event-log {
            max-height: 200px;
            overflow-y: auto;
            font-size: 11px;
            font-family: monospace;
        }
        .event-item {
            padding: 2px 0;
            border-bottom: 1px solid #1a1a2a;
            color: #888;
        }
        .event-item .tick { color: #555; }
        .event-item.CONFLICT { color: #ff6666; }
        .event-item.DISCOVERY { color: #66ff66; }
        .event-item.TRADE { color: #ffff66; }
        .event-item.DISASTER { color: #ff8800; }
        #mode-buttons {
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
        }
        .mode-btn {
            padding: 4px 8px;
            background: #1a1a2a;
            border: 1px solid #333;
            border-radius: 4px;
            color: #888;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .mode-btn:hover { background: #2a2a3a; color: #ccc; }
        .mode-btn.active { background: #2a3a4a; color: #00ccff; border-color: #00ccff; }
        #connection-status {
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
        }
        #connection-status.connected { background: #1a3a2a; color: #44ff88; }
        #connection-status.disconnected { background: #3a1a1a; color: #ff4444; }
        #agent-tooltip {
            position: absolute;
            display: none;
            background: #1a1a2a;
            border: 1px solid #00ccff;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 11px;
            pointer-events: none;
            z-index: 100;
            max-width: 200px;
        }
        .tooltip-name { color: #ffd700; font-weight: bold; }
        .tooltip-tier { color: #888; font-size: 10px; }
    </style>
</head>
<body>
    <div id="header">
        <h1>AMBIENTSAGA</h1>
        <div class="stat">Tick: <span id="tick-display">0</span></div>
        <div class="stat">Agents: <span id="agent-count">0</span></div>
        <div class="stat">FPS: <span id="fps-display">0</span></div>
        <div id="connection-status" class="disconnected">DISCONNECTED</div>
    </div>
    <div id="main">
        <div id="canvas-container">
            <canvas id="world-canvas"></canvas>
            <div id="agent-tooltip">
                <div class="tooltip-name"></div>
                <div class="tooltip-tier"></div>
            </div>
        </div>
        <div id="sidebar">
            <div class="panel">
                <h3>View Mode</h3>
                <div id="mode-buttons">
                    <button class="mode-btn active" data-mode="terrain">Terrain</button>
                    <button class="mode-btn" data-mode="temperature">Temperature</button>
                    <button class="mode-btn" data-mode="population">Population</button>
                    <button class="mode-btn" data-mode="activity">Activity</button>
                    <button class="mode-btn" data-mode="signals">Signals</button>
                    <button class="mode-btn" data-mode="wealth">Wealth</button>
                    <button class="mode-btn" data-mode="happiness">Happiness</button>
                </div>
            </div>
            <div class="panel">
                <h3>World Metrics</h3>
                <div id="metrics-container"></div>
            </div>
            <div class="panel">
                <h3>Recent Events</h3>
                <div id="event-log"></div>
            </div>
            <div class="panel">
                <h3>Controls</h3>
                <div style="font-size: 11px; color: #888;">
                    Drag: Pan camera<br>
                    Scroll: Zoom<br>
                    Click agent: Inspect
                </div>
            </div>
        </div>
    </div>

    <script>
    (function() {
        const canvas = document.getElementById('world-canvas');
        const ctx = canvas.getContext('2d');
        const tooltip = document.getElementById('agent-tooltip');

        let ws = null;
        let worldState = null;
        let tickUpdate = null;
        let camera = { x: 256, y: 256, zoom: 1.0 };
        let renderMode = 'terrain';
        let isDragging = false;
        let lastMouse = { x: 0, y: 0 };
        let agents = [];
        let signals = [];
        let events = [];
        let lastFrameTime = performance.now();
        let frameCount = 0;
        let fps = 0;

        // Terrain colors
        const TERRAIN_COLORS = {
            0: [10, 30, 80], 1: [20, 60, 120], 2: [40, 100, 160],
            3: [220, 210, 160], 4: [237, 201, 130], 5: [200, 180, 120],
            6: [140, 190, 80], 7: [100, 160, 60], 8: [160, 180, 80],
            9: [50, 120, 50], 10: [30, 80, 40], 11: [25, 90, 35],
            12: [15, 70, 25], 13: [30, 80, 60], 14: [130, 110, 80],
            15: [100, 90, 70], 16: [150, 150, 160], 17: [180, 200, 210],
        };

        function resize() {
            const container = document.getElementById('canvas-container');
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
            render();
        }

        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = protocol + '//' + window.location.host + ':8765';
            ws = new WebSocket('ws://localhost:8765');

            ws.onopen = () => {
                document.getElementById('connection-status').textContent = 'CONNECTED';
                document.getElementById('connection-status').className = 'connected';
            };

            ws.onclose = () => {
                document.getElementById('connection-status').textContent = 'DISCONNECTED';
                document.getElementById('connection-status').className = 'disconnected';
                setTimeout(connect, 3000);
            };

            ws.onerror = () => ws.close();

            ws.onmessage = (event) => {
                const lines = event.data.split('\\n');
                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const msg = JSON.parse(line);
                        handleMessage(msg);
                    } catch (e) {}
                }
            };
        }

        function handleMessage(msg) {
            if (msg.type === 'WORLD_STATE') {
                worldState = msg.payload;
                agents = worldState.agents || [];
                signals = worldState.signals || [];
                document.getElementById('tick-display').textContent = msg.tick;
                document.getElementById('agent-count').textContent = worldState.agent_count;
                updateMetrics();
            } else if (msg.type === 'TICK_UPDATE') {
                tickUpdate = msg;
                document.getElementById('tick-display').textContent = msg.tick;
                document.getElementById('agent-count').textContent = msg.agent_count;
                if (msg.events) {
                    events = msg.events.concat(events).slice(0, 50);
                    updateEventLog();
                }
                if (msg.agents) {
                    for (const a of msg.agents) {
                        const existing = agents.find(x => x.id === a.id);
                        if (existing) {
                            existing.x = a.x;
                            existing.y = a.y;
                            existing.happiness = a.happiness;
                            existing.wealth = a.wealth;
                        } else {
                            agents.push(a);
                        }
                    }
                }
            } else if (msg.type === 'EVENT') {
                events.unshift(msg.payload);
                events = events.slice(0, 50);
                updateEventLog();
            } else if (msg.type === 'PING') {
                ws.send(JSON.stringify({ type: 'ping', time: msg.time }));
            }
        }

        function updateMetrics() {
            if (!worldState) return;
            const container = document.getElementById('metrics-container');
            const metrics = [
                { label: 'World Size', value: worldState.world.width + 'x' + worldState.world.height },
                { label: 'Total Agents', value: worldState.agent_count, class: 'good' },
                { label: 'Active Signals', value: signals.length },
                { label: 'Mode', value: renderMode },
            ];
            container.innerHTML = metrics.map(m =>
                '<div class="metric-row">' +
                    '<span class="label">' + m.label + '</span>' +
                    '<span class="value ' + (m.class || '') + '">' + m.value + '</span>' +
                '</div>'
            ).join('');
        }

        function updateEventLog() {
            const log = document.getElementById('event-log');
            log.innerHTML = events.slice(0, 20).map(e =>
                '<div class="event-item ' + (e.type || '') + '">' +
                    '<span class="tick">[' + (e.tick || 0) + ']</span> ' +
                    (e.type || 'EVENT') + ': ' + (e.subject || '') +
                '</div>'
            ).join('');
        }

        function render() {
            if (!worldState) {
                ctx.fillStyle = '#0a0a0f';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = '#444';
                ctx.font = '16px monospace';
                ctx.textAlign = 'center';
                ctx.fillText('Connecting to simulation...', canvas.width / 2, canvas.height / 2);
                requestAnimationFrame(render);
                return;
            }

            const w = canvas.width;
            const h = canvas.height;
            ctx.fillStyle = '#0a0a0f';
            ctx.fillRect(0, 0, w, h);

            const worldW = worldState.world.width;
            const worldH = worldState.world.height;
            const terrain = worldState.world.terrain || [];
            const step = worldState.world.terrain_step || 1;

            // Render terrain
            if (terrain.length > 0) {
                const tileW = (worldW / terrain[0].length) / camera.zoom;
                const tileH = (worldH / terrain.length) / camera.zoom;

                for (let ty = 0; ty < terrain.length; ty++) {
                    for (let tx = 0; tx < terrain[ty].length; tx++) {
                        const wx = (tx * step - camera.x) * camera.zoom + w / 2;
                        const wy = (ty * step - camera.y) * camera.zoom + h / 2;

                        if (wx < -tileW || wx > w || wy < -tileH || wy > h) continue;

                        const terrainType = terrain[ty][tx];
                        const color = TERRAIN_COLORS[terrainType] || [128, 128, 128];
                        ctx.fillStyle = 'rgb(' + color.join(',') + ')';
                        ctx.fillRect(wx, wy, Math.max(1, tileW + 1), Math.max(1, tileH + 1));
                    }
                }
            }

            // Render signals
            for (const sig of signals) {
                const sx = (sig.x - camera.x) * camera.zoom + w / 2;
                const sy = (sig.y - camera.y) * camera.zoom + h / 2;
                const sr = sig.radius * camera.zoom;

                ctx.beginPath();
                ctx.arc(sx, sy, sr, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(255, 200, 0, 0.15)';
                ctx.fill();
                ctx.strokeStyle = 'rgba(255, 200, 0, 0.4)';
                ctx.lineWidth = 1;
                ctx.stroke();
            }

            // Render agents
            const agentRadius = Math.max(2, 4 / camera.zoom);
            const tierColors = { 1: '#ffd700', 2: '#64c8ff', 3: '#969696', 4: '#505050' };

            for (const agent of agents) {
                const ax = (agent.x - camera.x) * camera.zoom + w / 2;
                const ay = (agent.y - camera.y) * camera.zoom + h / 2;

                if (ax < -10 || ax > w + 10 || ay < -10 || ay > h + 10) continue;

                ctx.beginPath();
                ctx.arc(ax, ay, agentRadius, 0, Math.PI * 2);
                ctx.fillStyle = tierColors[agent.tier] || '#fff';
                ctx.fill();
            }

            // FPS counter
            frameCount++;
            const now = performance.now();
            if (now - lastFrameTime >= 1000) {
                fps = frameCount;
                frameCount = 0;
                lastFrameTime = now;
                document.getElementById('fps-display').textContent = fps;
            }

            requestAnimationFrame(render);
        }

        // Event listeners
        canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            lastMouse = { x: e.clientX, y: e.clientY };
        });

        canvas.addEventListener('mousemove', (e) => {
            if (isDragging) {
                camera.x -= (e.clientX - lastMouse.x) / camera.zoom;
                camera.y -= (e.clientY - lastMouse.y) / camera.zoom;
                lastMouse = { x: e.clientX, y: e.clientY };
            }

            // Tooltip for agents
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            const wx = mx / camera.zoom + camera.x - canvas.width / 2 / camera.zoom;
            const wy = my / camera.zoom + camera.y - canvas.height / 2 / camera.zoom;

            let hovered = null;
            for (const agent of agents) {
                const dx = agent.x - wx;
                const dy = agent.y - wy;
                if (dx * dx + dy * dy < 100) {
                    hovered = agent;
                    break;
                }
            }

            if (hovered) {
                tooltip.style.display = 'block';
                tooltip.style.left = (e.clientX + 10) + 'px';
                tooltip.style.top = (e.clientY + 10) + 'px';
                tooltip.querySelector('.tooltip-name').textContent = hovered.name;
                tooltip.querySelector('.tooltip-tier').textContent =
                    'Tier ' + hovered.tier + ' | Happiness: ' + (hovered.happiness || 0).toFixed(2);
            } else {
                tooltip.style.display = 'none';
            }
        });

        canvas.addEventListener('mouseup', () => isDragging = false);
        canvas.addEventListener('mouseleave', () => isDragging = false);

        canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
            camera.zoom = Math.max(0.1, Math.min(10, camera.zoom * zoomFactor));
        });

        // Mode buttons
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderMode = btn.dataset.mode;
                updateMetrics();
            });
        });

        window.addEventListener('resize', resize);
        resize();
        connect();
        render();
    })();
    </script>
</body>
</html>
"""


class StandaloneWebServer:
    """
    Standalone HTTP server that serves the web client without WebSocket support.

    Use this for simple file serving. The client will need to poll REST endpoints
    instead of receiving WebSocket updates.
    """

    def __init__(
        self,
        world: World,
        config: VisualizationConfig,
        host: str = "localhost",
        port: int = 8765,
    ) -> None:
        self.world = world
        self.config = config
        self.host = host
        self.port = port
        self._running = False
        self._server_thread: threading.Thread | None = None
        self._httpd = None

        # World state cache for efficient polling
        self._world_state_cache: dict[str, Any] | None = None
        self._last_update_tick: int = -1
        self._cache_lock = threading.Lock()

    def start(self) -> bool:
        """Start the HTTP server."""
        if self._running:
            return True

        try:
            import http.server
            import socketserver
            import threading

            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=None, **kwargs)

                def do_GET(self):
                    if self.path == "/" or self.path == "/index.html":
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html")
                        self.end_headers()
                        self.wfile.write(HTML_CLIENT.encode())
                    elif self.path == "/api/world":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        # Serialize world state
                        payload = json.dumps({
                            "tick": self.server.world.tick,
                            "agents": [],
                            "agent_count": self.server.world.get_agent_count(),
                        }).encode()
                        self.wfile.write(payload)
                    else:
                        self.send_response(404)
                        self.end_headers()
                        self.wfile.write(b"Not Found")

                def log_message(self, format, *args):
                    pass  # Suppress request logging

            class QuietTCPServer(socketserver.TCPServer):
                allow_reuse_address = True
                daemon_threads = True

            self._httpd = QuietTCPServer((self.host, self.port), Handler)
            self._httpd.world = self.world

            self._server_thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
            self._server_thread.start()

            self._running = True
            print(f"Web client available at http://{self.host}:{self.port}")
            return True

        except Exception as e:
            print(f"Failed to start web server: {e}")
            self._running = False
            return False

    def stop(self) -> None:
        """Stop the HTTP server."""
        if self._running and hasattr(self, "_httpd"):
            self._httpd.shutdown()
            self._running = False

    def broadcast_world_update(self) -> None:
        """
        Update the world state cache for polling clients.
        """
        if self._world_state_cache is None or self._last_update_tick != self.world.tick:
            # Create server instance with world state accessor
            pass
        with self._cache_lock:
            self._last_update_tick = self.world.tick


class StandaloneWebServerV2(StandaloneWebServer):
    """
    Enhanced standalone HTTP server with improved polling support.
    """

    def start(self) -> bool:
        """Start the HTTP server with improved polling."""
        if self._running:
            return True

        try:
            import http.server
            import socketserver

            # Pre-build world state once
            self._build_world_state_cache()

            class Handler(http.server.BaseHTTPRequestHandler):
                """HTTP request handler with polling support."""

                def log_message(self, format, *args):
                    pass  # Suppress request logging

                def do_GET(self):
                    if self.path == "/" or self.path == "/index.html":
                        self._serve_html()
                    elif self.path == "/api/world":
                        self._serve_world_state()
                    elif self.path == "/api/health":
                        self._serve_health()
                    else:
                        self.send_response(404)
                        self.end_headers()
                        self.wfile.write(b"Not Found")

                def _serve_html(self):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    self.wfile.write(HTML_CLIENT.encode())

                def _serve_world_state(self):
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    state = self.server.world_state_cache
                    payload = json.dumps(state).encode()
                    self.wfile.write(payload)

                def _serve_health(self):
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    health = {"status": "ok", "tick": self.server.world_tick}
                    self.wfile.write(json.dumps(health).encode())

            class QuietTCPServer(socketserver.TCPServer):
                allow_reuse_address = True
                daemon_threads = True

            self._httpd = QuietTCPServer((self.host, self.port), Handler)
            self._httpd.world_state_cache = self._world_state_cache
            self._httpd.world_tick = self.world.tick

            self._server_thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
            self._server_thread.start()

            self._running = True
            print(f"Web client available at http://{self.host}:{self.port}")
            return True

        except Exception as e:
            print(f"Failed to start web server: {e}")
            self._running = False
            return False

    def _build_world_state_cache(self) -> None:
        """Build initial world state cache."""
        config = self.world._config.world
        terrain = self.world._terrain

        terrain_data = None
        if terrain is not None:
            step = max(1, min(config.width, config.height) // 256)
            terrain_data = terrain[::step, ::step].tolist()

        agents = []
        for agent in self.world.get_all_agents():
            if not agent.is_alive:
                continue
            tier = getattr(agent, "tier", None)
            tier_value = getattr(tier, "value", None)
            # Skip L3/L4 for bandwidth (handle both string and int tier values)
            if tier_value is not None:
                try:
                    if isinstance(tier_value, str):
                        # String tier like "l1_core", skip if not L1
                        if not tier_value.startswith("l1"):
                            continue
                    elif int(tier_value) > 1:
                        continue
                except (ValueError, TypeError):
                    pass
            agents.append({
                "id": agent.entity_id,
                "name": agent.name[:20],
                "x": round(float(agent.position.x), 1),
                "y": round(float(agent.position.y), 1),
            })

        self._world_state_cache = {
            "tick": self.world.tick,
            "world": {
                "width": config.width,
                "height": config.height,
                "terrain": terrain_data,
                "terrain_step": max(1, min(config.width, config.height) // 256),
            },
            "agents": agents,
            "agent_count": self.world.get_agent_count(),
        }

    def stop(self) -> None:
        """Stop the HTTP server."""
        if self._running and self._httpd:
            self._httpd.shutdown()
            self._running = False
