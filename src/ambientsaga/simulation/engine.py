"""
Core simulation engine - Tick-driven simulation with event bus and batch scheduling.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, Any
from collections import deque
import heapq

from ambientsaga.config import SimulationConfig
from ambientsaga.types import Tick, EntityID
from ambientsaga.world import World
from ambientsaga.agents import AgentRegistry


@dataclass
class SimulationEvent:
    """Event in the simulation event bus."""
    tick: Tick
    event_type: str
    source_id: EntityID | None = None
    target_id: EntityID | None = None
    data: dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Lower = higher priority


@dataclass
class SimulationState:
    """Current state of the simulation."""
    tick: Tick = 0
    paused: bool = False
    speed: float = 1.0
    total_events: int = 0
    agents_processed: int = 0
    events_per_second: float = 0.0
    start_time: float = field(default_factory=time.time)
    last_stats_time: float = field(default_factory=time.time)
    events_this_second: int = 0


class EventBus:
    """Central event bus for inter-component communication."""

    def __init__(self, max_queue_size: int = 100000):
        self._subscribers: dict[str, list[Callable]] = {}
        self._event_queue: deque[SimulationEvent] = deque(maxlen=max_queue_size)
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, callback: Callable[[SimulationEvent], Any]) -> None:
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    async def publish(self, event: SimulationEvent) -> None:
        """Publish an event to all subscribers."""
        async with self._lock:
            self._event_queue.append(event)
            if event.event_type in self._subscribers:
                for callback in self._subscribers[event.event_type]:
                    try:
                        result = callback(event)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        pass  # Log errors in production

    async def get_events(self, event_type: str | None = None, since_tick: Tick = 0) -> list[SimulationEvent]:
        """Retrieve events from the queue."""
        async with self._lock:
            if event_type is None:
                return [e for e in self._event_queue if e.tick >= since_tick]
            return [e for e in self._event_queue if e.event_type == event_type and e.tick >= since_tick]

    def clear(self) -> None:
        """Clear the event queue."""
        self._event_queue.clear()


class BatchScheduler:
    """Scheduler for batched agent processing."""

    def __init__(self, batch_size: int = 100):
        self._batch_size = batch_size
        self._pending_agents: list[tuple[int, EntityID]] = []  # (priority, agent_id)
        self._running: dict[EntityID, asyncio.Task] = {}

    def schedule(self, agent_id: EntityID, priority: int = 0) -> None:
        """Schedule an agent for processing."""
        heapq.heappush(self._pending_agents, (priority, agent_id))

    def get_next_batch(self) -> list[EntityID]:
        """Get the next batch of agents to process."""
        batch = []
        for _ in range(self._batch_size):
            if self._pending_agents:
                _, agent_id = heapq.heappop(self._pending_agents)
                batch.append(agent_id)
            else:
                break
        return batch

    def reschedule(self, agent_id: EntityID, priority: int = 0) -> None:
        """Reschedule an agent for next tick."""
        self.schedule(agent_id, priority)

    @property
    def pending_count(self) -> int:
        """Number of pending agents."""
        return len(self._pending_agents)


class SimulationEngine:
    """
    Core simulation engine that drives the world forward tick by tick.
    Handles batched agent processing, event distribution, and world updates.
    """

    def __init__(self, config: SimulationConfig, world: World, agent_registry: AgentRegistry):
        self.config = config
        self.world = world
        self.agent_registry = agent_registry
        self.event_bus = EventBus(max_queue_size=config.event_queue_size)
        self.scheduler = BatchScheduler(batch_size=config.agent_batch_size)
        self.state = SimulationState()

        # Tick handlers
        self._tick_handlers: list[Callable[[Tick], Any]] = []

        # Processing statistics
        self._agent_processing_times: dict[EntityID, float] = {}

    def register_tick_handler(self, handler: Callable[[Tick], Any]) -> None:
        """Register a handler that runs every tick."""
        self._tick_handlers.append(handler)

    async def initialize(self) -> None:
        """Initialize the simulation engine."""
        # Register default event handlers
        self.event_bus.subscribe("agent_born", self._on_agent_born)
        self.event_bus.subscribe("agent_died", self._on_agent_died)
        self.event_bus.subscribe("agent_moved", self._on_agent_moved)
        self.event_bus.subscribe("world_event", self._on_world_event)

        # Schedule all initial agents
        for agent_id in self.agent_registry.list_all_agents():
            self.scheduler.schedule(agent_id, priority=0)

    async def _on_agent_born(self, event: SimulationEvent) -> None:
        """Handle agent birth event."""
        if event.target_id:
            self.scheduler.schedule(event.target_id, priority=1)

    async def _on_agent_died(self, event: SimulationEvent) -> None:
        """Handle agent death event."""
        pass  # Clean up resources

    async def _on_agent_moved(self, event: SimulationEvent) -> None:
        """Handle agent movement event."""
        pass  # Update spatial indices

    async def _on_world_event(self, event: SimulationEvent) -> None:
        """Handle world events (disasters, seasons, etc.)."""
        pass  # Trigger world updates

    async def run(self) -> None:
        """Run the main simulation loop."""
        await self.initialize()

        while not self._should_stop():
            if self.state.paused:
                await asyncio.sleep(0.1)
                continue

            tick_start = time.perf_counter()

            # Execute tick
            await self._tick()

            # Calculate actual tick duration and sleep if needed
            tick_duration = time.perf_counter() - tick_start

            # Handle unlimited speed (ticks_per_second = 0 or speed = 0)
            speed_factor = self.config.ticks_per_second * self.state.speed
            if speed_factor > 0:
                target_tick_duration = 1.0 / speed_factor
                sleep_time = max(0, target_tick_duration - tick_duration)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            # else: unlimited speed, no sleep

            # Update statistics
            self._update_stats(tick_duration)

    def _should_stop(self) -> bool:
        """Check if simulation should stop."""
        return (
            self.config.max_ticks is not None and
            self.state.tick >= self.config.max_ticks
        )

    async def _tick(self) -> None:
        """Execute a single simulation tick."""
        self.state.tick += 1
        tick = self.state.tick

        # Run tick handlers
        for handler in self._tick_handlers:
            try:
                result = handler(tick)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                pass  # Log in production

        # Update world
        await self.world.run_tick_async(tick)

        # Process agents in batches
        await self._process_agent_batch()

        # Update statistics
        self.state.agents_processed += 1

    async def _process_agent_batch(self) -> None:
        """Process a batch of agents."""
        batch = self.scheduler.get_next_batch()

        for agent_id in batch:
            agent = self.agent_registry.get_agent(agent_id)
            if agent is None:
                continue

            try:
                start_time = time.perf_counter()

                # Execute agent tick
                result = await agent.tick(self.state.tick)
                processing_time = time.perf_counter() - start_time
                self._agent_processing_times[agent_id] = processing_time

                # Reschedule if agent is still active
                if result.get("alive", True):
                    priority = result.get("priority", 10)
                    self.scheduler.reschedule(agent_id, priority)

            except Exception as e:
                pass  # Log in production

    def _update_stats(self, tick_duration: float) -> None:
        """Update simulation statistics."""
        current_time = time.time()

        # Events per second
        self.state.events_this_second += 1
        if current_time - self.state.last_stats_time >= 1.0:
            self.state.events_per_second = self.state.events_this_second / (current_time - self.state.last_stats_time)
            self.state.events_this_second = 0
            self.state.last_stats_time = current_time

    def pause(self) -> None:
        """Pause the simulation."""
        self.state.paused = True

    def resume(self) -> None:
        """Resume the simulation."""
        self.state.paused = False

    def set_speed(self, speed: float) -> None:
        """Set simulation speed (1.0 = normal, 2.0 = 2x speed, etc.)."""
        self.state.speed = max(0.1, min(10.0, speed))

    def get_stats(self) -> dict[str, Any]:
        """Get current simulation statistics."""
        elapsed = time.time() - self.state.start_time
        return {
            "tick": self.state.tick,
            "paused": self.state.paused,
            "speed": self.state.speed,
            "elapsed_seconds": elapsed,
            "ticks_per_second": self.state.tick / elapsed if elapsed > 0 else 0,
            "events_per_second": self.state.events_per_second,
            "agents_processed": self.state.agents_processed,
            "pending_agents": self.scheduler.pending_count,
            "avg_agent_processing_time": sum(self._agent_processing_times.values()) / len(self._agent_processing_times) if self._agent_processing_times else 0,
        }

    async def shutdown(self) -> None:
        """Shutdown the simulation engine."""
        self.event_bus.clear()