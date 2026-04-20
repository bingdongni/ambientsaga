"""
World State — the central simulation state manager.

The World class coordinates all subsystems:
- Natural world (terrain, climate, water, ecology, disasters)
- Social world (agents, organizations, institutions, relationships)
- Economic world (markets, production, trade, currency)
- Political world (governance, law, conflict)
- Cultural world (beliefs, language, art, religion)
- Historical world (events, chronicles, narratives)

All state changes go through this class to ensure consistency.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, Any

import msgspec
import numpy as np

from ambientsaga.agents.cognition import CognitiveManager
from ambientsaga.causal import UnifiedCausalEngine
from ambientsaga.config import Config, SimulationConfig

# === Cultural Collision System ===
from ambientsaga.culture.collision import CulturalCollisionSystem

# === NEW: Ultimate Emergence Systems ===
from ambientsaga.emergence.butterfly_effects import (
    ButterflyEffectSystem,
)
from ambientsaga.emergence.full_domain_coupling import (
    Domain,
    FullDomainCouplingEngine,
)
from ambientsaga.emergence.institutional_emergence import (
    InstitutionalEmergenceEngine,
)
from ambientsaga.emergence.nexus import (
    CausalDomain,
    CausalPropagationEngine,
    HumanDecisionMaker,
)
from ambientsaga.emergence.true_emergence import TrueEmergenceLayer
from ambientsaga.evolution import EvolutionConfig, EvolutionEngine
from ambientsaga.history.butterfly import HistoricalButterflySystem

# === Natural Diversity System ===
from ambientsaga.natural.diversity import NaturalDiversitySystem
from ambientsaga.optimization import PerformanceOptimizer
from ambientsaga.protocol.emergent_econ import EmergentEconomy
from ambientsaga.protocol.interaction import MetaProtocol
from ambientsaga.protocol.language_emergence import LanguageEmergence
from ambientsaga.protocol.reputation import ReputationNetwork
from ambientsaga.protocol.social_norms import EmergentNorms
from ambientsaga.science import ScienceEngine
from ambientsaga.science.functional_science import FunctionalScienceEngine
from ambientsaga.social.ethnicity import EthnicGroupManager

# === NEW: Social Systems ===
from ambientsaga.social.settlement import SettlementManager

# === Social Stratification System ===
from ambientsaga.social.stratification import SocialStratificationSystem
from ambientsaga.types import (
    EntityID,
    Event,
    EventPriority,
    EventType,
    Organization,
    OrganizationType,
    Pos2D,
    Signal,
    SignalType,
    TerrainType,
    new_entity_id,
)
from ambientsaga.world.chunk import ChunkManager
from ambientsaga.world.events import EventLog
from ambientsaga.world.signal_bus import SignalBus
from ambientsaga.world.tick import TickEngine

if TYPE_CHECKING:
    from ambientsaga.agents.agent import Agent


# ---------------------------------------------------------------------------
# Snapshot for Save/Load
# ---------------------------------------------------------------------------


@dataclass
class WorldSnapshot:
    """Complete state of the world for save/load."""

    version: str
    tick: int
    config: dict[str, Any]
    agent_states: list[dict[str, Any]]
    organization_states: list[dict[str, Any]]
    chunk_states: list[dict[str, Any]]
    market_states: dict[str, dict[str, Any]]
    climate_state: dict[str, Any]
    event_count: int


# ---------------------------------------------------------------------------
# World State
# ---------------------------------------------------------------------------


class World:
    """
    The central simulation state manager.

    The World class is the single source of truth for the entire simulation.
    All subsystems read from and write to the World state.

    Thread Safety:
    The World uses a single RLock that must be acquired before any state access.
    For read-heavy workloads, use get_state() / release_state() pattern.

    Example:
        world = World(config)
        with world.state_lock():
            agent = world.agents[agent_id]
            agent.health -= 0.1
            world.publish_signal(...)
    """

    def __init__(self, config: Config | SimulationConfig) -> None:
        # Resolve config
        if isinstance(config, Config):
            self._config = config.simulation
        else:
            self._config = config

        # Core systems
        self._lock = RLock()
        self._tick_engine = TickEngine(
            tick_rate=self._config.tick_rate,
        )
        self._signal_bus = SignalBus()
        self._chunk_manager = ChunkManager(
            world_width=self._config.world.width,
            world_height=self._config.world.height,
            chunk_size=self._config.world.chunk_size,
            world=self,
        )
        self._event_log = EventLog()

        # RNG (deterministic for reproducibility)
        self._rng = np.random.Generator(np.random.PCG64(self._config.world.seed))

        # Entity registries
        self._agents: dict[EntityID, Agent] = {}
        self._agent_positions: dict[EntityID, Pos2D] = {}
        self._organizations: dict[EntityID, Organization] = {}
        self._relationships: dict[tuple[EntityID, EntityID], dict[str, Any]] = {}
        self._markets: dict[str, dict[str, Any]] = {}

        # Natural world systems
        self._terrain: np.ndarray | None = None  # [height, height] terrain types
        self._elevation: np.ndarray | None = None  # [height, height] elevation in meters
        self._soil: np.ndarray | None = None  # [height, height] soil types
        self._aquifer: np.ndarray | None = None  # [height, height] aquifer level 0-1
        self._temperature: np.ndarray | None = None  # [height, height] temperature
        self._humidity: np.ndarray | None = None  # [height, height] humidity
        self._precipitation: np.ndarray | None = None  # [height, height] precipitation
        self._vegetation: np.ndarray | None = None  # [height, height] vegetation cover

        # Subsystems (initialized later)
        self._climate_system: Any = None
        self._hydrology_system: Any = None
        self._ecosystem: Any = None
        self._disaster_system: Any = None
        self._market_system: Any = None
        self._org_manager: Any = None
        self._governance: Any = None
        self._production_system: Any = None
        self._culture_system: Any = None
        self._belief_system: Any = None
        self._ritual_system: Any = None
        self._art_system: Any = None
        self._language_system: Any = None
        self._visualization: Any = None

        # Emergent Protocol Systems (open-ended interaction)
        self._protocol: MetaProtocol | None = None
        self._reputation: ReputationNetwork | None = None
        self._language: LanguageEmergence | None = None
        self._norms: EmergentNorms | None = None
        self._economy: EmergentEconomy | None = None

        # Self-Evolution System
        self._evolution: EvolutionEngine | None = None

        # Science Engine (unified physics, chemistry, biology, ecology)
        self._science: ScienceEngine | None = None

        # === NEW: Enhanced Systems for True Emergence ===

        # Unified Causal Engine (domain coupling)
        self._causal_engine: UnifiedCausalEngine | None = None

        # Functional Science Engine (actual scientific calculations)
        self._functional_science: FunctionalScienceEngine | None = None

        # True Emergence Layer (real spontaneous emergence)
        self._emergence_layer: TrueEmergenceLayer | None = None

        # Historical Butterfly System (historical uniqueness)
        self._butterfly_system: HistoricalButterflySystem | None = None

        # Performance Optimizer
        self._optimizer: PerformanceOptimizer | None = None

        # === ULTIMATE EMERGENCE: Full Domain Coupling ===
        # Butterfly Effect System (chaos and historical branching)
        self._butterfly_effect: ButterflyEffectSystem | None = None

        # Full Domain Coupling Engine (all scientific domains connected)
        self._domain_coupling: FullDomainCouplingEngine | None = None

        # Institutional Emergence Engine (law, government, religion, class)
        self._institutional_emergence: InstitutionalEmergenceEngine | None = None

        # === Natural Diversity System ===
        # Manages biomes, geological features, and natural disasters
        self._natural_diversity: NaturalDiversitySystem | None = None

        # === Cultural Collision System ===
        # Manages cultural encounters, collisions, and synthesis
        self._cultural_collision: CulturalCollisionSystem | None = None

        # === Social Stratification System ===
        # Manages emergent social classes and hierarchies
        self._social_stratification: SocialStratificationSystem | None = None

        # === NEW: Settlement System ===
        # Manages villages, towns, cities, and territorial control
        self._settlement_manager: SettlementManager | None = None

        # === NEW: Ethnic Group System ===
        # Manages ethnic groups, cultures, and cultural identities
        self._ethnicity_manager: EthnicGroupManager | None = None

        # LLM Integration
        self._llm_thread_pool: ThreadPoolExecutor | None = None
        self._llm_enabled: bool = False
        self._llm_pending_results: dict[str, dict] = {}  # agent_id -> result

        # Statistics
        self._stats = {
            "ticks_run": 0,
            "events_logged": 0,
            "signals_published": 0,
            "decisions_made": 0,
        }

        # Callbacks
        self._state_change_callbacks: list[Callable[[str, Any], None]] = []

        # Initialize subsystems
        self._initialize()

    def _initialize(self) -> None:
        """Initialize the world and all subsystems."""
        # Register tick phases
        for phase in TickEngine.TICK_PHASES:
            self._tick_engine.register_phase_callback(phase, self._on_tick_phase(phase))

        # Initialize natural world arrays
        h, w = self._config.world.height, self._config.world.width
        self._terrain = np.zeros((h, w), dtype=np.int32)
        self._elevation = np.zeros((h, w), dtype=np.float64)
        self._soil = np.zeros((h, w), dtype=np.int32)
        self._aquifer = np.full((h, w), 0.5, dtype=np.float64)
        self._temperature = np.zeros((h, w), dtype=np.float64)
        self._humidity = np.zeros((h, w), dtype=np.float64)
        self._precipitation = np.zeros((h, w), dtype=np.float64)
        self._vegetation = np.zeros((h, w), dtype=np.float64)

        # Generate terrain
        self._generate_terrain()

        # Initialize emergent protocol systems with cognitive support
        llm_api_key = getattr(self._config, 'llm', None)
        llm_key = getattr(llm_api_key, 'api_key', None) if llm_api_key else None
        self._cognitive_manager = CognitiveManager(llm_api_key=llm_key)
        self._llm_enabled = llm_key is not None

        if self._llm_enabled:
            # Set up thread pool for async LLM calls
            self._llm_thread_pool = ThreadPoolExecutor(max_workers=4)

        self._protocol = MetaProtocol(self, cognitive_manager=self._cognitive_manager)
        self._reputation = ReputationNetwork(self)
        self._language = LanguageEmergence()
        self._norms = EmergentNorms(self)
        self._economy = EmergentEconomy(self)

        # Initialize self-evolution system
        # Use a seeded Python RNG for evolution (it expects random.Random, not numpy Generator)
        import random
        seed = int(self._rng.random() * 2**31)
        evo_rng = random.Random(seed)
        self._evolution = EvolutionEngine(
            config=EvolutionConfig(
                population_size=len(self._agents) if self._agents else 1000,
            ),
            rng=evo_rng,
        )

        # Initialize unified science engine
        self._science = ScienceEngine(config=self._config.science if hasattr(self._config, 'science') else None)

        # === NEW: Initialize Enhanced Systems ===

        # Initialize Unified Causal Engine
        self._causal_engine = UnifiedCausalEngine(self)

        # Initialize Functional Science Engine
        self._functional_science = FunctionalScienceEngine(self)

        # Initialize True Emergence Layer
        self._emergence_layer = TrueEmergenceLayer(self)

        # === NEXUS: 原生涌现核心引擎 ===
        # 单一因果链驱动，不是模块化组件
        self._nexus = CausalPropagationEngine(self)
        self._agent_decision_makers: dict[str, HumanDecisionMaker] = {}

        # Initialize Historical Butterfly System
        seed = self._config.world.seed if hasattr(self._config, 'world') else None
        self._butterfly_system = HistoricalButterflySystem(self, base_seed=seed)

        # Initialize Performance Optimizer
        self._optimizer = PerformanceOptimizer()

        # === ULTIMATE EMERGENCE: Initialize Full Domain Systems ===

        # Initialize Butterfly Effect System (chaos-based historical branching)
        self._butterfly_effect = ButterflyEffectSystem(self)

        # Initialize Full Domain Coupling Engine (all scientific domains)
        self._domain_coupling = FullDomainCouplingEngine(self)

        # Initialize Institutional Emergence Engine (law, government, religion, class)
        self._institutional_emergence = InstitutionalEmergenceEngine(self)

        # === NEW: Initialize Natural Diversity System ===
        # Manages biomes, geological features, and natural disaster diversity
        self._natural_diversity = NaturalDiversitySystem(
            width=w,
            height=h,
            seed=self._config.world.seed or 42
        )

        # === NEW: Initialize Cultural Collision System ===
        # Manages cultural encounters, collisions, and synthesis
        self._cultural_collision = CulturalCollisionSystem(
            seed=self._config.world.seed or 42
        )

        # === NEW: Initialize Social Stratification System ===
        # Manages emergent social classes and hierarchies
        self._social_stratification = SocialStratificationSystem(
            seed=self._config.world.seed or 42
        )

        # === NEW: Initialize Settlement System ===
        # Manages villages, towns, cities, and territorial control
        self._settlement_manager = SettlementManager(
            world=self,
            seed=self._config.world.seed or 42
        )

        # === NEW: Initialize Ethnicity System ===
        # Manages ethnic groups, cultures, and cultural identities
        self._ethnicity_manager = EthnicGroupManager(
            world=self,
            seed=self._config.world.seed or 42
        )

    def _generate_terrain(self) -> None:
        """Generate world terrain using noise and classification."""
        h, w = self._config.world.height, self._config.world.width
        rng = self._rng

        # Generate elevation with simple noise
        for y in range(h):
            for x in range(w):
                # Simple noise-based elevation
                self._elevation[y, x] = rng.random()
                # Moisture variation
                self._humidity[y, x] = rng.random() * 0.6 + 0.2
                # Temperature based on latitude
                self._temperature[y, x] = 15 + 25 * (1 - y / h)

        # Classify terrain based on elevation and moisture
        for y in range(h):
            for x in range(w):
                e = self._elevation[y, x]
                m = self._humidity[y, x]
                t = self._temperature[y, x]

                # Classify terrain
                if e < 0.25:
                    self._terrain[y, x] = TerrainType.DEEP_OCEAN.value
                elif e < 0.35:
                    self._terrain[y, x] = TerrainType.OCEAN.value
                elif e < 0.4:
                    self._terrain[y, x] = TerrainType.BEACH.value
                elif e < 0.5:
                    if m < 0.25:
                        self._terrain[y, x] = TerrainType.DESERT.value
                    elif m < 0.4:
                        self._terrain[y, x] = TerrainType.SHRUBLAND.value
                    elif m < 0.55:
                        self._terrain[y, x] = TerrainType.GRASSLAND.value
                    else:
                        self._terrain[y, x] = TerrainType.TEMPERATE_FOREST.value
                elif e < 0.65:
                    if t > 20:
                        self._terrain[y, x] = TerrainType.TROPICAL_FOREST.value
                    elif t > 10:
                        self._terrain[y, x] = TerrainType.TEMPERATE_FOREST.value
                    else:
                        self._terrain[y, x] = TerrainType.BOREAL_FOREST.value
                elif e < 0.8:
                    self._terrain[y, x] = TerrainType.HILLS.value
                else:
                    self._terrain[y, x] = TerrainType.MOUNTAINS.value

                # Add vegetation based on terrain
                terrain = TerrainType(self._terrain[y, x])
                if terrain in (TerrainType.GRASSLAND, TerrainType.SAVANNA):
                    self._vegetation[y, x] = rng.random() * 0.4 + 0.3
                elif terrain in (TerrainType.TEMPERATE_FOREST, TerrainType.TROPICAL_FOREST, TerrainType.BOREAL_FOREST):
                    self._vegetation[y, x] = rng.random() * 0.5 + 0.4

                # Aquifer level
                self._aquifer[y, x] = rng.random() * 0.5 + 0.3

    # -------------------------------------------------------------------------
    # State Lock
    # -------------------------------------------------------------------------

    def state_lock(self) -> RLock:
        """Acquire the world state lock."""
        return self._lock

    def __enter__(self) -> World:
        self._lock.acquire()
        return self

    def __exit__(self, *args: Any) -> None:
        self._lock.release()

    # -------------------------------------------------------------------------
    # Tick System
    # -------------------------------------------------------------------------

    @property
    def tick(self) -> int:
        return self._tick_engine.tick

    @property
    def year(self) -> int:
        return self._tick_engine.year

    @property
    def season(self) -> str:
        return self._tick_engine.season

    @property
    def tick_engine(self) -> TickEngine:
        return self._tick_engine

    @property
    def protocol(self) -> MetaProtocol | None:
        return self._protocol

    @property
    def reputation(self) -> ReputationNetwork | None:
        return self._reputation

    @property
    def language(self) -> LanguageEmergence | None:
        return self._language

    @property
    def norms(self) -> EmergentNorms | None:
        return self._norms

    @property
    def economy(self) -> EmergentEconomy | None:
        return self._economy

    @property
    def evolution(self) -> EvolutionEngine | None:
        return self._evolution

    def tick_once(self) -> bool:
        """Execute one tick."""
        return self._tick_engine.tick_once()

    def run(self, max_ticks: int | None = None) -> int:
        """Run the simulation."""
        return self._tick_engine.run(max_ticks=max_ticks)

    def pause(self) -> None:
        self._tick_engine.pause()

    def resume(self) -> None:
        self._tick_engine.resume()

    def seek(self, tick: int) -> None:
        self._tick_engine.seek(tick)

    async def run_tick_async(self, tick: int) -> None:
        """
        Execute a single simulation tick (async version for SimulationEngine).

        This runs all tick phases in order.
        """
        # Update tick engine
        self._tick_engine.tick = tick

        # Run all tick phases
        for phase in TickEngine.TICK_PHASES:
            handler = self._on_tick_phase(phase)
            try:
                result = handler(tick)
                if hasattr(result, '__await__'):
                    await result
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------

    def register_agent(self, agent: Agent) -> None:
        """Register an agent in the world."""
        with self._lock:
            if agent.entity_id in self._agents:
                raise ValueError(f"Agent already registered: {agent.entity_id}")
            self._agents[agent.entity_id] = agent
            self._agent_positions[agent.entity_id] = agent.position
            self._chunk_manager.register_agent(
                agent.entity_id, agent.position.x, agent.position.y
            )
            # Create behavioral genome for evolution
            if self._evolution is not None:
                self._evolution.create_genome(
                    agent_id=agent.entity_id,
                    initial_type="random",
                )
            # Assign to ethnic group (handle both Agent types)
            if self._ethnicity_manager is not None:
                ethnic_groups = self._ethnicity_manager.get_active_ethnic_groups()
                if ethnic_groups:
                    # Assign to a random ethnic group based on position or randomly
                    target_ethnic = ethnic_groups[self._rng.integers(len(ethnic_groups))]
                    self._ethnicity_manager.register_agent(agent.entity_id, target_ethnic.ethnic_id)
                    # Generate physical traits based on ethnic background (if Agent supports it)
                    if hasattr(agent, 'generate_physical_traits'):
                        agent.generate_physical_traits(ethnicity=target_ethnic.short_name.lower())
                    if hasattr(agent, 'ethnic_id'):
                        agent.ethnic_id = target_ethnic.ethnic_id
            # Assign to settlement if in range
            if self._settlement_manager is not None:
                settlement = self._settlement_manager.get_settlement_at(agent.position)
                if settlement:
                    self._settlement_manager.assign_agent(agent.entity_id, settlement.settlement_id)

    def remove_agent(self, entity_id: EntityID) -> None:
        """Remove an agent from the world."""
        with self._lock:
            agent = self._agents.pop(entity_id, None)
            if agent is not None:
                pos = self._agent_positions.pop(entity_id, None)
                if pos is not None:
                    self._chunk_manager.unregister_agent(entity_id)
                # Remove behavioral genome
                if self._evolution is not None:
                    self._evolution.remove_genome(entity_id)

    def move_agent(self, entity_id: EntityID, new_pos: Pos2D) -> None:
        """Move an agent to a new position."""
        with self._lock:
            old_pos = self._agent_positions.get(entity_id)
            if old_pos is None:
                raise ValueError(f"Agent not found: {entity_id}")
            self._agent_positions[entity_id] = new_pos
            agent = self._agents.get(entity_id)
            if agent is not None:
                agent.position = new_pos
            self._chunk_manager.move_agent(
                entity_id, old_pos.x, old_pos.y, new_pos.x, new_pos.y
            )

    def get_agent(self, entity_id: EntityID) -> Agent | None:
        """Get an agent by ID."""
        return self._agents.get(entity_id)

    def get_agents_near(
        self, pos: Pos2D, radius: float
    ) -> Iterator[tuple[Agent, float]]:
        """
        Get all agents within radius, with distance.

        Uses chunk-based spatial index for efficient queries.
        Yields (agent, distance) tuples.
        """
        # Get candidate agents from nearby chunks
        agent_ids = self._chunk_manager.get_agents_in_radius(
            pos.x, pos.y, radius
        )
        radius_sq = radius * radius

        with self._lock:
            # Get actual positions from our tracking dict
            for eid, _approx_x, _approx_y in agent_ids:
                # Use approximate position from chunk for quick filter
                # Then get exact position from our tracking
                exact_pos = self._agent_positions.get(eid)
                if exact_pos is None:
                    continue

                dx = exact_pos.x - pos.x
                dy = exact_pos.y - pos.y
                dist_sq = dx * dx + dy * dy
                if dist_sq <= radius_sq:
                    agent = self._agents.get(eid)
                    if agent is not None:
                        yield (agent, (dist_sq) ** 0.5)

    def get_agents_in_radius(self, pos: Pos2D, radius: float) -> list[Agent]:
        """
        Get all agents within radius (simple interface for protocol deliberation).
        Returns a list of Agent objects, excluding the position's own agent.
        """
        return [agent for agent, _ in self.get_agents_near(pos, radius)]

    def get_all_agents(self) -> list[Agent]:
        """Get all agents (snapshot)."""
        with self._lock:
            return list(self._agents.values())

    def get_agent_count(self) -> int:
        """Get total agent count."""
        return len(self._agents)

    # -------------------------------------------------------------------------
    # Terrain and Geography
    # -------------------------------------------------------------------------

    def get_terrain(self, x: int, y: int) -> TerrainType:
        """Get terrain type at position."""
        if not self._in_bounds(x, y):
            return TerrainType.DEEP_OCEAN
        return TerrainType(self._terrain[y, x])  # type: ignore

    def get_elevation(self, x: int, y: int) -> float:
        """Get elevation at position (meters)."""
        if not self._in_bounds(x, y):
            return 0.0
        return float(self._elevation[y, x])

    def get_temperature(self, x: int, y: int) -> float:
        """Get temperature at position (Celsius)."""
        if not self._in_bounds(x, y):
            return 15.0
        return float(self._temperature[y, x])

    def get_humidity(self, x: int, y: int) -> float:
        """Get humidity at position (0-1)."""
        if not self._in_bounds(x, y):
            return 0.5
        return float(self._humidity[y, x])

    def get_vegetation(self, x: int, y: int) -> float:
        """Get vegetation cover at position (0-1)."""
        if not self._in_bounds(x, y):
            return 0.0
        return float(self._vegetation[y, x])

    def is_land(self, x: int, y: int) -> bool:
        """Check if position is land (not water)."""
        return self.get_terrain(x, y).is_land

    def is_water(self, x: int, y: int) -> bool:
        """Check if position is water."""
        return self.get_terrain(x, y).is_water

    def is_passable(self, x: int, y: int) -> bool:
        """Check if position is passable (not water or mountains)."""
        t = self.get_terrain(x, y)
        return t.is_land and t != TerrainType.HIGH_MOUNTAINS

    def get_water_proximity(self, x: int, y: int) -> float:
        """
        Calculate water proximity (0-1 scale).

        Returns:
            1.0 if position is water
            0.0 if no water within 100 tiles
            Linear interpolation between (water=1.0, far=0.0)
        """
        if self.is_water(int(x), int(y)):
            return 1.0

        # Find nearest water
        nearest = self.find_nearest_water(int(x), int(y), max_distance=100)
        if nearest is None:
            return 0.0

        # Calculate distance
        dx = nearest.x - x
        dy = nearest.y - y
        distance = (dx * dx + dy * dy) ** 0.5

        # Convert to proximity (1/distance, normalized)
        if distance <= 1:
            return 1.0
        return max(0.0, 1.0 - distance / 100.0)

    def _in_bounds(self, x: int, y: int) -> bool:
        """Check if position is within world bounds."""
        return 0 <= x < self._config.world.width and 0 <= y < self._config.world.height

    def set_terrain(self, x: int, y: int, terrain: TerrainType) -> None:
        """Set terrain type at position."""
        if self._in_bounds(x, y):
            self._terrain[y, x] = terrain.value

    def set_elevation(self, x: int, y: int, elevation: float) -> None:
        """Set elevation at position."""
        if self._in_bounds(x, y):
            self._elevation[y, x] = elevation

    # -------------------------------------------------------------------------
    # Signal Bus
    # -------------------------------------------------------------------------

    @property
    def signal_bus(self) -> SignalBus:
        return self._signal_bus

    @property
    def science(self) -> ScienceEngine:
        """Unified science engine (physics, chemistry, biology, ecology)."""
        return self._science

    # === NEW: Enhanced System Getters ===

    @property
    def causal_engine(self) -> UnifiedCausalEngine | None:
        """Unified causal engine for domain coupling."""
        return self._causal_engine

    @property
    def functional_science(self) -> FunctionalScienceEngine | None:
        """Functional science engine for real scientific calculations."""
        return self._functional_science

    @property
    def emergence_layer(self) -> TrueEmergenceLayer | None:
        """True emergence layer for spontaneous pattern formation."""
        return self._emergence_layer

    @property
    def nexus(self) -> CausalPropagationEngine | None:
        """NEXUS: 原生涌现核心引擎 - 单一因果链驱动"""
        return self._nexus

    @property
    def butterfly_system(self) -> HistoricalButterflySystem | None:
        """Historical butterfly system for tracking uniqueness."""
        return self._butterfly_system

    @property
    def optimizer(self) -> PerformanceOptimizer | None:
        """Performance optimizer for tracking and improving performance."""
        return self._optimizer

    def publish_signal(self, signal: Signal, priority: int = 2) -> None:
        """Publish a signal to the ambient signal bus."""
        self._signal_bus.publish(signal, priority)
        self._stats["signals_published"] += 1

    def subscribe(
        self,
        agent_id: EntityID,
        signal_types: SignalType,
        position: Pos2D,
        radius: float,
        callback: Callable[[Signal], None],
        priority: int = 0,
    ) -> Signal:
        """Subscribe an agent to signals."""
        return self._signal_bus.subscribe(
            agent_id=agent_id,
            signal_types=signal_types,
            position=position,
            perception_radius=radius,
            callback=callback,
            priority=priority,
        )

    # -------------------------------------------------------------------------
    # Event Logging
    # -------------------------------------------------------------------------

    def log_event(
        self,
        event_type: str,
        subject_id: EntityID | None = None,
        object_id: EntityID | None = None,
        position: Pos2D | None = None,
        priority: EventPriority = EventPriority.NORMAL,
        data: dict[str, Any] | None = None,
        cause_id: str | None = None,
        narrative: str = "",
    ) -> Event:
        """Log a significant event."""
        # Convert string to EventType if possible, store original string in metadata
        event_meta = [("event_type_str", event_type)]
        if isinstance(event_type, str):
            try:
                event_enum_name = event_type.upper().replace(" ", "_")
                event_type = EventType[event_enum_name]
            except KeyError:
                event_type = EventType.CUSTOM

        metadata = frozenset(
            list(event_meta) + (list(data.items()) if data else [])
        )
        event = Event(
            tick=self._tick_engine.tick,
            event_type=event_type,
            priority=priority,
            position=position,
            subject_id=subject_id,
            object_id=object_id,
            cause_id=cause_id,
            description=narrative,
            metadata=metadata,
        )
        self._event_log.log(event)
        self._stats["events_logged"] += 1
        return event

    def get_events_near(self, pos: Pos2D, radius: int = 100) -> list[Event]:
        """Get recent events near a position."""
        return self._event_log.get_by_tick(self._tick_engine.tick)

    def get_entity_history(self, entity_id: EntityID) -> list[Event]:
        """Get all events involving an entity."""
        return self._event_log.get_by_entity(entity_id)

    def get_causal_chain(self, event_id: str) -> list[Event]:
        """Trace the causal chain of an event."""
        return self._event_log.get_causal_chain(event_id)

    # -------------------------------------------------------------------------
    # Organizations
    # -------------------------------------------------------------------------

    def create_organization(
        self,
        name: str,
        org_type: OrganizationType,
        founder_id: EntityID,
        position: Pos2D | None = None,
        founding_members: list[EntityID] | None = None,
    ) -> Organization:
        """Create a new organization."""
        org = Organization(
            org_id=new_entity_id(),
            name=name,
            org_type=org_type,
            founding_tick=self._tick_engine.tick,
            founding_position=position or Pos2D(0, 0),
            leader_id=founder_id,
            founding_members=frozenset(founding_members or [founder_id]),
            ideology="",
        )
        with self._lock:
            self._organizations[org.org_id] = org
        self.log_event(
            event_type=f"org_founded_{org_type.name.lower()}",
            subject_id=founder_id,
            object_id=org.org_id,
            position=position,
            priority=EventPriority.HIGH,
            data={"org_name": name, "org_type": org_type.name},
            narrative=f"{name} was founded by {founder_id[:8]}",
        )
        return org

    def get_organization(self, org_id: EntityID) -> Organization | None:
        """Get an organization by ID."""
        return self._organizations.get(org_id)

    def get_organizations_near(
        self, pos: Pos2D, radius: float
    ) -> Iterator[Organization]:
        """Get all organizations near a position."""
        with self._lock:
            for org in self._organizations.values():
                if org.territory is None:
                    continue
                if org.territory.contains(pos):
                    yield org

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    def get_relationship(
        self, agent_a: EntityID, agent_b: EntityID
    ) -> dict[str, Any] | None:
        """Get the relationship between two agents."""
        key = (min(agent_a, agent_b), max(agent_a, agent_b))
        return self._relationships.get(key)

    def set_relationship(
        self,
        agent_a: EntityID,
        agent_b: EntityID,
        trust: float | None = None,
        conflict: float | None = None,
        debt: float | None = None,
        affiliation: float | None = None,
    ) -> None:
        """Set or update a relationship between two agents."""
        key = (min(agent_a, agent_b), max(agent_a, agent_b))
        if key not in self._relationships:
            self._relationships[key] = {
                "familiarity": 0.0,
                "trust": 0.0,
                "conflict": 0.0,
                "debt": 0.0,
                "affiliation": 0.0,
                "interactions": 0,
                "last_interaction_tick": 0,
            }
        rel = self._relationships[key]
        if trust is not None:
            rel["trust"] = max(0.0, min(1.0, trust))
        if conflict is not None:
            rel["conflict"] = max(0.0, min(1.0, conflict))
        if debt is not None:
            rel["debt"] = max(0.0, debt)
        if affiliation is not None:
            rel["affiliation"] = max(0.0, min(1.0, affiliation))
        rel["last_interaction_tick"] = self._tick_engine.tick
        rel["interactions"] += 1

    # -------------------------------------------------------------------------
    # Spatial Queries
    # -------------------------------------------------------------------------

    def find_nearest_land(self, x: int, y: int, max_distance: int = 50) -> Pos2D | None:
        """Find the nearest land tile from a position."""
        for r in range(max_distance + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    nx, ny = x + dx, y + dy
                    if self._in_bounds(nx, ny) and self.is_land(nx, ny):
                        return Pos2D(nx, ny)
        return None

    def find_spawn_point(self) -> Pos2D:
        """Find a suitable spawn point for a new agent."""
        candidates = []
        h, w = self._config.world.height, self._config.world.width

        for y in range(h):
            for x in range(w):
                terrain = self.get_terrain(x, y)
                if terrain in (TerrainType.GRASSLAND, TerrainType.SAVANNA, TerrainType.TEMPERATE_FOREST):
                    candidates.append(Pos2D(x, y))

        if candidates:
            return self._rng.choice(candidates)
        return Pos2D(w // 2, h // 2)

    def find_nearest_water(self, x: int, y: int, max_distance: int = 50) -> Pos2D | None:
        """Find the nearest water tile from a position."""
        for r in range(max_distance + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    nx, ny = x + dx, y + dy
                    if self._in_bounds(nx, ny) and self.is_water(nx, ny):
                        return Pos2D(nx, ny)
        return None

    def get_path_distance(self, start: Pos2D, end: Pos2D) -> float:
        """Compute approximate path distance (A* would be ideal)."""
        # Simple Euclidean with terrain penalty
        dx = abs(end.x - start.x)
        dy = abs(end.y - start.y)
        base_dist = (dx * dx + dy * dy) ** 0.5
        # Add terrain penalty for non-grassland
        for x in range(min(start.x, end.x), max(start.x, end.x) + 1):
            for y in range(min(start.y, end.y), max(start.y, end.y) + 1):
                if self._in_bounds(x, y):
                    t = self.get_terrain(x, y)
                    base_dist *= (t.movement_cost ** 0.1)
        return base_dist

    def get_neighbors(self, x: int, y: int, diagonals: bool = True) -> list[Pos2D]:
        """Get neighboring positions."""
        neighbors = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                if not diagonals and (dx != 0 and dy != 0):
                    continue
                nx, ny = x + dx, y + dy
                if self._in_bounds(nx, ny) and self.is_passable(nx, ny):
                    neighbors.append(Pos2D(nx, ny))
        return neighbors

    # -------------------------------------------------------------------------
    # Tick Phase Handlers
    # -------------------------------------------------------------------------

    # Phase dispatch table - maps phase names to handler methods
    _PHASE_HANDLERS: dict[str, str] = {
        "WORLD_UPDATE": "_phase_world_update",
        "ECOLOGY": "_phase_ecology",
        "AGENT_PERCEPTION": "_phase_agent_perception",
        "AGENT_DECISION": "_phase_agent_decision",
        "AGENT_ACTION": "_phase_agent_action",
        "SOCIAL": "_phase_social",
        "ECONOMY": "_phase_economy",
        "POLITICAL": "_phase_political",
        "CULTURE": "_phase_culture",
        "DISASTERS": "_phase_disasters",
        "HISTORY": "_phase_history",
        "METRICS": "_phase_metrics",
        "EMERGENCE_SYSTEMS": "_phase_emergence_systems",
    }

    def _on_tick_phase(self, phase: str) -> Callable[[int], None]:
        """Create a tick phase handler using dispatch table."""
        handler_name = self._PHASE_HANDLERS.get(phase)
        if handler_name is None:
            return lambda tick: None

        handler_method = getattr(self, handler_name, None)
        if handler_method is None:
            return lambda tick: None

        return handler_method

    def _get_action_energy_cost(self, agent: Agent, action: Any) -> float:
        """
        Calculate energy cost for an action based on physics.
        Uses physics engine for realistic energy calculations.
        """
        base_cost = 0.05  # Base energy cost for any action

        # Physics-based movement cost
        if action in ("wander", "explore", "move_to_water", "flee", "seek_shelter"):
            # Distance moved (approximate)
            if action == "wander":
                distance = 2.5  # Average distance for wander
            elif action == "explore":
                distance = 5.5  # Average distance for explore
            elif action == "move_to_water":
                distance = 1.0  # One step
            elif action in ("flee", "seek_shelter"):
                distance = 3.0  # Moderate distance for defensive actions
            else:
                distance = 1.0

            # Apply terrain cost
            terrain = self.get_terrain(agent.x, agent.y)
            terrain_cost_map = {
                "WATER": 3.0,      # Swimming is hard
                "DEEP_WATER": 5.0,  # Very hard
                "HILLS": 2.0,       # Hiking uphill
                "MOUNTAIN": 3.0,    # Mountain climbing
                "FOREST": 1.5,      # Dense vegetation
                "DESERT": 1.8,      # Hot and sandy
                "SWAMP": 2.5,       # Difficult terrain
                "GRASSLAND": 1.0,   # Easy
                "PLAINS": 1.0,      # Easy
                "BEACH": 1.2,       # Moderate
                "SCRUBLAND": 1.3,   # Moderate
            }
            terrain_multiplier = terrain_cost_map.get(terrain.name, 1.0)

            # Temperature affects movement efficiency
            temp_multiplier = 1.0
            if self._science is not None:
                temp = self._science.physics.ambient_temperature
                # Too cold or too hot reduces efficiency
                if temp < 273.15:  # Below freezing
                    temp_multiplier = 2.0  # Hypothermia
                elif temp < 283.15:  # Cold
                    temp_multiplier = 1.5
                elif temp > 313.15:  # Hot
                    temp_multiplier = 1.5
                elif temp > 323.15:  # Very hot
                    temp_multiplier = 2.0  # Heat exhaustion

            # Calculate movement cost using physics (E = mgh approximation)
            # Simplified: E = base_cost * distance * terrain * temperature
            movement_cost = base_cost * distance * terrain_multiplier * temp_multiplier
            return movement_cost

        elif action in ("gather_food", "gather_resource"):
            # Gathering costs energy based on terrain and vegetation
            terrain = self.get_terrain(agent.x, agent.y)
            veg = self.get_vegetation(agent.x, agent.y)

            # High vegetation = more effort to gather
            gather_cost = base_cost * (1.0 + veg * 0.5)
            return gather_cost

        elif action == "rest":
            # Resting recovers energy, no cost
            return 0.0

        elif action == "idle":
            # Idle has minimal cost
            return base_cost * 0.2

        elif isinstance(action, dict):
            # Social interactions have moderate cost
            action_type = action.get("type", "")
            if action_type in ("interact", "help", "trade", "communicate"):
                return base_cost * 0.5
            elif action_type == "attack":
                return base_cost * 2.0  # Combat is expensive
            elif action_type == "help":
                return base_cost * 1.5  # Helping costs energy

        # Default action cost
        return base_cost

    def _phase_world_update(self, tick: int) -> None:
        """Update world state."""
        # Process signals
        self._signal_bus.process_signals(tick)

        # Update climate
        if self._climate_system is not None:
            self._climate_system.update(tick, self._temperature, self._humidity)

        # Update hydrology
        if self._hydrology_system is not None:
            self._hydrology_system.update(
                tick,
                self._terrain,
                self._elevation,
                self._aquifer,
            )

        # Update science engine (physics, chemistry, biology, ecology)
        if self._science is not None:
            # Propagate environment conditions to science engine
            avg_temp = float(np.mean(self._temperature)) + 273.15  # Convert to Kelvin
            self._science.physics.ambient_temperature = avg_temp
            self._science.physics.ambient_pressure = 101325.0  # Standard pressure

            # Propagate agent activity to science engine (aggregate energy consumption)
            agents = self.get_all_agents()
            total_energy_consumed = 0.0
            total_food_consumed = 0.0
            for agent in agents:
                if agent.is_alive:
                    # Aggregate energy consumption from agent movement and actions
                    energy_rate = 0.01 * (1.0 - agent.energy)  # More hungry = more energy needed
                    total_energy_consumed += energy_rate

                    # Aggregate food consumption
                    if agent.hunger > 0.5:
                        total_food_consumed += (agent.hunger - 0.5) * 0.1

            # Update science with aggregated data
            self._science.propagate_cross_domain(
                'energy_consumption',
                value=total_energy_consumed / max(1, len(agents)),
                physics=avg_temp,
                chemistry=total_food_consumed,
                biology=len(agents) / (self._config.world.width * self._config.world.height / 10000),
            )

            # Update science simulation
            self._science.update(tick, dt=1.0)

            # Propagate science results back to environment
            # Ecosystem regeneration based on ecological efficiency
            eco_result = self._science.propagate_cross_domain('vegetation_growth')
            if eco_result.get('ecology'):
                # Increase vegetation based on ecological conditions
                growth_factor = min(0.01, eco_result['ecology'] * 0.001)
                for y in range(min(50, self._config.world.height)):
                    for x in range(min(50, self._config.world.width)):
                        if not self._terrain[y, x].is_water:
                            self._vegetation[y, x] = min(1.0, self._vegetation[y, x] + growth_factor)

            # Resource regeneration based on chemistry (nutrient cycling)
            chem_result = self._science.propagate_cross_domain('nutrient_cycling')
            if chem_result.get('chemistry'):
                # Slight regeneration of food resources
                regen = chem_result['chemistry'] * 0.0001
                for agent in agents:
                    if agent.is_alive and agent.hunger > 0.3:
                        # Find nearby vegetation for food
                        px, py = int(agent.position.x), int(agent.position.y)
                        if 0 <= py < self._config.world.height and 0 <= px < self._config.world.width:
                            veg = self._vegetation[py, px]
                            if veg > 0.3:
                                # Ecology provides food regeneration
                                agent.hunger = max(0, agent.hunger - regen * veg)

        self._stats["ticks_run"] = tick

    def _phase_ecology(self, tick: int) -> None:
        """Process ecological systems."""
        if self._ecosystem is not None:
            self._ecosystem.update(tick, self._vegetation, self._terrain)

    # Tick phase sampling rates (ticks between processing per tier)
    _AGENT_TIER_RATES: dict[str, int] = {
        "l1_core": 10,        # L1_CORE: every 10 ticks
        "l2_functional": 10,  # L2_FUNCTIONAL: every 10 ticks
        "l3_background": 15, # L3_BACKGROUND: every 15 ticks (increased for more interactions)
    }

    # Performance tuning: limit neighbor perception to avoid O(n²) behavior
    _MAX_PERCEIVED_AGENTS = 3   # Maximum agents to perceive per tick per agent
    _PERCEPTION_RADIUS_SAMPLE = 0.05  # Sample 5% of neighbors to limit work
    # Batch size for processing agents (larger = fewer iterations, better cache)
    _PERCEPTION_BATCH_SIZE = 200
    # Parallel perception: fixed worker pool size, not per-agent threads
    _PERCEPTION_WORKERS = 4  # Fixed worker threads for perception
    _AGENT_RADIUS = 5.0  # Reduced from 15.0 for performance — tighter perception range

    def _phase_agent_perception(self, tick: int) -> None:
        """
        Agents perceive signals, nearby agents, terrain, and resources.

        We sample agents based on tier so L1_CORE agents are most active.
        Each sampled agent builds a perception snapshot for decision-making.
        """
        agents = self.get_all_agents()
        if not agents:
            return

        # Sample agents based on tier for perception
        # Hash-based sampling: spread agents evenly across rate ticks to avoid spikes
        sampled = []
        tick_mod = tick % 100  # Use modulo 100 to keep tick_mod in reasonable range
        for agent in agents:
            if not agent.is_alive:
                continue
            rate = self._AGENT_TIER_RATES.get(agent.tier.value, 20)
            agent_slot = (hash(agent.entity_id) // 16) % rate
            if agent_slot == tick_mod % rate:
                sampled.append(agent)

        if not sampled:
            return

        # Always use optimized sequential processing
        self._optimized_perception(sampled, tick)

    def _optimized_perception(self, agents: list, tick: int) -> None:
        """
        Optimized perception: batch query all nearby agents from chunks first,
        then process each agent's perception without per-agent spatial queries.
        """
        radius = self._AGENT_RADIUS
        radius_sq = radius * radius

        # Pre-fetch all agent positions and objects under single lock
        agent_positions: dict[str, Pos2D] = {}
        agents_dict: dict[str, Agent] = {}
        with self._lock:
            for agent in agents:
                agent_positions[agent.entity_id] = agent.position
                agents_dict[agent.entity_id] = agent

        # Batch query: collect all nearby agents from chunks (no lock needed - read only)
        # This is the main cost: ~560 agents * ~100 candidates = 56K checks
        all_nearby: dict[str, list[tuple[Agent, float]]] = {}

        for agent in agents:
            pos = agent_positions[agent.entity_id]
            # Get candidate IDs from chunk manager
            candidate_ids = self._chunk_manager.get_agents_in_radius(
                pos.x, pos.y, radius
            )
            nearby = []
            for eid, _approx_x, _approx_y in candidate_ids:
                # Use pre-fetched positions (avoid redundant dict lookup)
                exact_pos = agent_positions.get(eid)
                if exact_pos is None:
                    continue
                dx = exact_pos.x - pos.x
                dy = exact_pos.y - pos.y
                dist_sq = dx * dx + dy * dy
                if dist_sq <= radius_sq:
                    # Use pre-fetched agent dict (avoid redundant dict lookup)
                    agent_obj = agents_dict.get(eid)
                    if agent_obj is not None:
                        nearby.append((agent_obj, (dist_sq) ** 0.5))
            all_nearby[agent.entity_id] = nearby

        # Process each agent's perception (no lock needed)
        for agent in agents:
            nearby_list = all_nearby.get(agent.entity_id, [])
            # Cache nearby agents for decision phase (avoids duplicate spatial query)
            agent._nearby_agents = nearby_list
            self._do_perception(agent, tick, nearby_list)

    def _do_perception(self, agent: Agent, tick: int, nearby_list: list) -> None:
        """Process perception for a single agent (no lock required)."""
        agent.last_perception_tick = tick
        perceived = []

        # Sample subset of nearby agents to limit work
        sample_size = min(self._MAX_PERCEIVED_AGENTS, len(nearby_list))
        if nearby_list:
            indices = self._rng.integers(0, len(nearby_list), size=sample_size)
            for i in indices:
                nearby, dist = nearby_list[i]
                if nearby.entity_id != agent.entity_id and nearby.is_alive:
                    rel = self.get_relationship(agent.entity_id, nearby.entity_id)
                    trust = rel.get("trust", 0.0) if rel else 0.0
                    perceived.append(("agent", nearby.entity_id, dist, trust))

        # Perceive environment (no lock needed - numpy array reads)
        terrain = self.get_terrain(agent.x, agent.y)
        perceived.append(("terrain", terrain.name, 0, 0.0))
        elev = self.get_elevation(agent.x, agent.y)
        perceived.append(("elevation", elev, 0, 0.0))
        temp = self.get_temperature(agent.x, agent.y)
        perceived.append(("temperature", temp, 0, 0.0))
        humidity = self.get_humidity(agent.x, agent.y)
        perceived.append(("humidity", humidity, 0, 0.0))
        veg = self.get_vegetation(agent.x, agent.y)
        perceived.append(("vegetation", veg, 0, 0.0))

        agent._perceived = perceived

    def _phase_agent_decision(self, tick: int) -> None:
        """
        Agents make decisions based on perception.

        Decision logic by tier:
        - L1_CORE: Full LLM deliberation (placeholder - requires API key)
        - L2_FUNCTIONAL: Rule-based with social considerations
        - L3_BACKGROUND: Simple survival-driven rules

        Decisions are stored as pending actions on the agent.
        """
        agents = self.get_all_agents()
        if not agents:
            return

        # Sample agents based on tier for decision-making
        # Hash-based sampling: spread agents evenly across rate ticks
        sampled = []
        tick_mod = tick % 100
        for agent in agents:
            if not agent.is_alive:
                continue
            rate = self._AGENT_TIER_RATES.get(agent.tier.value, 20)
            agent_slot = (hash(agent.entity_id) // 16) % rate
            if agent_slot == tick_mod % rate:
                sampled.append(agent)

        for agent in sampled:
            # Get perception from previous phase
            getattr(agent, "_perceived", None)

            # === NEXUS: 原生涌现决策增强 ===
            # 获取因果上下文
            causal_context = {}
            if self._nexus is not None:
                causal_context = self._nexus.get_causal_context(agent.entity_id)

            # 获取或创建人性化决策器
            if self._nexus is not None and agent.entity_id not in self._agent_decision_makers:
                self._agent_decision_makers[agent.entity_id] = HumanDecisionMaker(
                    agent.entity_id, self._rng
                )
            decision_maker = self._agent_decision_makers.get(agent.entity_id)

            # UNIFIED DECISION: All agents use protocol deliberation exclusively
            # Protocol deliberation uses cached _nearby_agents to avoid expensive spatial queries
            # This ensures traces are created for all agent-to-agent interactions
            if self._protocol is not None:
                decision = self._protocol.deliberate(agent, tick)
                if decision:
                    agent.current_goal = decision.get("goal", "interact")
                    agent.goal_priority = decision.get("priority", 0.5)

                    # === NEXUS: 人性化决策扭曲 ===
                    if decision_maker is not None:
                        # 将协议决策选项传给人性化决策器进行扭曲
                        options = [agent.current_goal]
                        chosen, score = decision_maker.decide_action(
                            options, {"beliefs": getattr(agent, "beliefs", [])}, causal_context
                        )
                        agent.goal_priority = score  # 人性化决策影响优先级

                    receiver_id = decision.get("receiver_id", "")
                    if receiver_id:
                        # Has a receiver - create protocol action
                        agent._pending_action = {
                            "type": "protocol",
                            "signal": decision.get("signal", "interact"),
                            "receiver_id": receiver_id,
                            "content": decision.get("content", {}),
                            "interpretation": decision.get("interpretation", ""),
                        }
                    else:
                        # No receiver - execute local action
                        agent._pending_action = decision.get("action", "idle")
                    agent.last_decision_tick = tick
                    self._stats["decisions_made"] = self._stats.get("decisions_made", 0) + 1
            else:
                # No protocol system - should not happen in normal operation
                # Log warning and skip decision
                import logging
                logging.getLogger(__name__).warning(
                    f"No protocol system available for agent {agent.entity_id}"
                )

    # =========================================================================
    # DEPRECATED: These methods are kept for reference but are NO LONGER USED.
    # All agent decisions now go through MetaProtocol.deliberate() exclusively.
    # =========================================================================

    def _make_decision(
        self,
        agent: Agent,
        perceived: list[tuple[str, Any, float, float]] | None,
        tick: int,
    ) -> dict[str, Any] | None:
        """
        [DEPRECATED] Use MetaProtocol.deliberate() instead.

        This method is no longer called. Protocol deliberation provides
        richer, emergent behavior through:
        - Emotional decision-making
        - Game theory (tit-for-tat, cooperation, defection)
        - Science modulation (environment affects behavior)
        - Cultural influences
        - Reciprocity and debt tracking
        """
        return None

    def _l1_decision(
        self,
        agent: Agent,
        perceived: list[tuple[str, Any, float, float]] | None,
        nearby_agents: list[tuple],
        tick: int,
    ) -> dict[str, Any]:
        """[DEPRECATED] Use MetaProtocol.deliberate() instead."""
        return {"goal": "deprecated", "priority": 0.0, "action": "idle"}

    def _llm_deliberate(
        self,
        agent: Agent,
        tick: int,
    ) -> dict[str, Any] | None:
        """
        [DEPRECATED] LLM deliberation is now handled by MetaProtocol.deliberate()
        for L1 agents with cognitive manager.
        """
        return None

    def _l2_decision(
        self,
        agent: Agent,
        perceived: list[tuple[str, Any, float, float]] | None,
        nearby_agents: list[tuple],
        tick: int,
    ) -> dict[str, Any]:
        """[DEPRECATED] Use MetaProtocol.deliberate() instead."""
        return {"goal": "deprecated", "priority": 0.0, "action": "idle"}

    def _l3_decision(
        self,
        agent: Agent,
        perceived: list[tuple[str, Any, float, float]] | None,
        nearby_agents: list[tuple],
        tick: int,
    ) -> dict[str, Any]:
        """[DEPRECATED] Use MetaProtocol.deliberate() instead."""
        return {"goal": "deprecated", "priority": 0.0, "action": "idle"}

    # =========================================================================
    # End of deprecated methods
    # =========================================================================

    def _phase_agent_action(self, tick: int) -> None:
        """
        Agents execute their pending actions.

        Actions include: movement, resource gathering, social interaction,
        trading, and resting.
        """
        agents = self.get_all_agents()
        if not agents:
            return

        for agent in agents:
            if not agent.is_alive:
                continue

            # Only act if we have a pending action from decision phase
            pending = getattr(agent, "_pending_action", None)
            if pending is None:
                continue

            try:
                # Extract action info for NEXUS causal event
                action_description = ""
                if isinstance(pending, str):
                    action_description = pending
                elif isinstance(pending, dict):
                    action_description = pending.get("signal", pending.get("type", "unknown"))

                # === NEXUS: Emit causal events ===
                if self._nexus is not None and action_description:
                    # Calculate causal magnitude based on action type and agent state
                    wealth = getattr(agent, "wealth", 100.0)
                    magnitude = 0.3 + (wealth / 100.0) * 0.2

                    # High-impact actions get higher magnitude
                    high_impact_actions = {
                        "threat", "conflict", "betrayal", "war", "scarcity_conflict",
                        "desperation", "revenge", "aggress", "exploit", "extortion",
                        "demand_from", "defame"
                    }
                    if action_description in high_impact_actions:
                        magnitude = 0.6 + magnitude * 0.3  # Boost high-impact events

                    # Determine affected domains
                    affected_domains = {CausalDomain.SOCIAL}
                    if action_description in ("gather_food", "move_to_water", "gather_resource"):
                        affected_domains.add(CausalDomain.ECONOMICS)
                    elif action_description in ("help", "share", "gift", "cooperate", "env_cooperate"):
                        affected_domains.add(CausalDomain.ECONOMICS)
                        affected_domains.add(CausalDomain.PSYCHOLOGICAL)
                    elif action_description in high_impact_actions:
                        affected_domains.add(CausalDomain.PSYCHOLOGICAL)
                        affected_domains.add(CausalDomain.ECONOMICS)

                    # Emit causal event
                    self._nexus.emit_agent_action(
                        agent_id=agent.entity_id,
                        action_description=action_description,
                        effect_description=f"Agent {agent.name} performs {action_description}",
                        magnitude=magnitude,
                        domains=affected_domains,
                    )

                # Handle protocol-based actions (from MetaProtocol deliberation)
                if isinstance(pending, dict) and pending.get("type") == "protocol":
                    self._execute_protocol_action(agent, pending, tick)
                else:
                    self._execute_action(agent, pending, tick)

                # Record action with evolution engine
                if self._evolution is not None:
                    self._record_agent_action(agent, pending, tick)

            except Exception:
                # Log but don't stop simulation
                pass

            # Update needs
            self._update_agent_needs(agent, tick)

            # Clear pending action
            agent._pending_action = None

    # Mapping from action strings to GeneType names for evolution tracking
    _ACTION_GENE_TYPE_MAP = {
        "idle": "REST",
        "rest": "REST",
        "wander": "WANDER",
        "explore": "EXPLORE",
        "gather_food": "GATHER",
        "move_to_water": "MOVE",
        "gather_resource": "GATHER",
        "interact": "GREET",
        "initiate_trade": "TRADE",
        # Social actions
        "help": "HELP",
        "share": "SHARE",
        "exchange": "EXCHANGE",
        "cooperate": "COOPERATE",
        "gift": "GIVE",
        "request": "REQUEST",
        "follow": "FOLLOW",
        "protect": "PROTECT",
        "teach": "TEACH",
        "learn": "LEARN",
        "build": "BUILD",
        "negotiate": "NEGOTIATE",
    }

    def _record_agent_action(
        self, agent: Agent, action: Any, tick: int
    ) -> None:
        """Record an agent action with the evolution engine."""
        if self._evolution is None:
            return

        # Extract action type from action
        if isinstance(action, str):
            action_type = action
        elif isinstance(action, dict):
            action_type = action.get("type", "interact")
            if action_type == "protocol":
                # For protocol actions, extract the signal as the action type
                signal = action.get("signal", "interact")
                # Also check for social action types embedded in protocol
                goal = action.get("goal", "")
                if goal in ("help", "share", "exchange", "cooperate", "gift"):
                    action_type = goal
                elif signal in self._ACTION_GENE_TYPE_MAP:
                    action_type = signal
                else:
                    action_type = signal.upper() if signal else "INTERACT"
        else:
            action_type = "interact"

        # Map to GeneType name
        gene_type_name = self._ACTION_GENE_TYPE_MAP.get(action_type, action_type.upper())

        # Generate a gene hash for this action type
        gene_hash = f"{agent.entity_id}_{action_type}_{tick}"

        # Determine success based on action outcome
        # Rest always succeeds
        # Movement succeeds if agent is alive
        # Social actions succeed if relationship was updated
        success = agent.is_alive
        fitness_delta = 0.1 if success else -0.1

        # Record the action
        self._evolution.record_action(
            agent_id=agent.entity_id,
            gene_hash=gene_hash,
            gene_type=gene_type_name,
            success=success,
            fitness_delta=fitness_delta,
            tick=tick,
        )

    def _execute_action(
        self, agent: Agent, action: Any, tick: int
    ) -> None:
        """Execute a single action for an agent."""
        # Get physics-based energy cost for the action
        energy_cost = self._get_action_energy_cost(agent, action)

        if action == "idle":
            # Do nothing
            return

        elif action == "rest":
            # Recover energy (physics-based recovery rate)
            recovery_rate = 0.15
            if self._science is not None:
                # Temperature affects recovery (too hot/cold = slower recovery)
                temp = self._science.physics.ambient_temperature
                if temp < 288.15 or temp > 303.15:
                    recovery_rate *= 0.7  # 30% slower in extreme temperatures
            agent.energy = min(1.0, agent.energy + recovery_rate)
            agent.remember(
                "rest",
                {"location": (agent.x, agent.y)},
                importance=0.3,
                tick=tick,
            )

        elif action == "wander":
            # Random movement
            dx = self._rng.integers(-3, 4)
            dy = self._rng.integers(-3, 4)
            new_x = max(0, min(self._config.world.width - 1, agent.x + dx))
            new_y = max(0, min(self._config.world.height - 1, agent.y + dy))
            if self.is_passable(new_x, new_y):
                self.move_agent(agent.entity_id, Pos2D(new_x, new_y))
                agent.energy -= energy_cost  # Physics-based energy cost

        elif action == "explore":
            # Move toward unexplored area
            dx = self._rng.integers(-5, 6)
            dy = self._rng.integers(-5, 6)
            new_x = max(0, min(self._config.world.width - 1, agent.x + dx))
            new_y = max(0, min(self._config.world.height - 1, agent.y + dy))
            if self.is_passable(new_x, new_y):
                self.move_agent(agent.entity_id, Pos2D(new_x, new_y))
                agent.energy -= energy_cost * 1.5  # Exploration costs more energy
                terrain = self.get_terrain(new_x, new_y)
                self.log_event(
                    "exploration",
                    subject_id=agent.entity_id,
                    position=Pos2D(new_x, new_y),
                    priority=EventPriority.LOW,
                    narrative=f"{agent.name} explores {terrain.name}",
                )

        elif action == "gather_food":
            # Gather food from current location
            veg = self.get_vegetation(agent.x, agent.y)
            if veg > 0.1:
                gathered = veg * 0.5
                # Apply chemistry-based nutrient value (higher quality food = more satisfying)
                if self._science is not None:
                    nutrient_factor = self._science.chemistry.get_nutrient_value("food")
                    gathered *= (0.8 + nutrient_factor * 0.4)  # 0.8 to 1.2 multiplier
                agent.hunger = max(0.0, agent.hunger - gathered)
                # Add to inventory
                resource_type = "food"
                items = dict(agent.inventory.items)
                items[resource_type] = items.get(resource_type, 0.0) + gathered
                agent.inventory.items = items
                agent.energy -= energy_cost
            else:
                # Wander to find food
                action = "wander"
                self._execute_action(agent, action, tick)

        elif action == "move_to_water":
            # Find nearest water and move toward it
            target = self.find_nearest_water(agent.x, agent.y)
            if target:
                dx = target.x - agent.x
                dy = target.y - agent.y
                dist = (dx * dx + dy * dy) ** 0.5
                if dist > 0:
                    # Move one step toward water
                    step_x = int(dx / dist)
                    step_y = int(dy / dist)
                    new_x = max(0, min(self._config.world.width - 1, agent.x + step_x))
                    new_y = max(0, min(self._config.world.height - 1, agent.y + step_y))
                    if self.is_passable(new_x, new_y):
                        self.move_agent(agent.entity_id, Pos2D(new_x, new_y))
                        agent.energy -= energy_cost
                        # Drink if at water
                        if self.is_water(new_x, new_y):
                            agent.thirst = max(0.0, agent.thirst - 0.5)
                            # Chemistry: water quality affects hydration
                            if self._science is not None:
                                water_quality = self._science.chemistry.get_nutrient_value("water")
                                agent.thirst = max(0.0, agent.thirst - water_quality * 0.2)
                            agent.remember(
                                "drink",
                                {"location": (new_x, new_y)},
                                importance=0.4,
                                tick=tick,
                            )
            else:
                # No water found, wander
                self._execute_action(agent, "wander", tick)

        elif action == "gather_resource":
            # Gather whatever resource is available
            terrain = self.get_terrain(agent.x, agent.y)
            gathered = 0.1 * agent.skills.get("crafting", 0.5)
            resource_map = {
                "FOREST": "wood",
                "GRASSLAND": "food",
                "SCRUBLAND": "herbs",
                "HILLS": "stone",
                "PLAINS": "food",
            }
            resource = resource_map.get(terrain.name, "materials")
            items = dict(agent.inventory.items)
            items[resource] = items.get(resource, 0.0) + gathered
            agent.inventory.items = items
            agent.energy -= (0.05 + energy_cost)

        elif isinstance(action, dict) and action.get("type") == "interact":
            # Social interaction with another agent
            target_id = action.get("target")
            if target_id:
                target = self.get_agent(target_id)
                if target and target.is_alive:
                    # Create or update relationship
                    self.set_relationship(
                        agent.entity_id,
                        target_id,
                        trust=0.1,
                        affiliation=0.1,
                    )
                    # Log the interaction
                    self.log_event(
                        "social_interaction",
                        subject_id=agent.entity_id,
                        object_id=target_id,
                        priority=EventPriority.LOW,
                        narrative=f"{agent.name} interacts with {target.name}",
                    )
                    agent.remember(
                        "interact",
                        {"other": target_id[:8], "goal": agent.current_goal},
                        importance=0.4,
                        tick=tick,
                    )
                    # Record interaction for evolution
                    if self._evolution is not None:
                        self._evolution.process_interaction(
                            agent.entity_id,
                            target_id,
                            interaction_type="interact",
                            outcome={"success": True, "fitness_delta": 0.05},
                            tick=tick,
                        )
                    # Small energy cost
                    agent.energy -= 0.02

        elif action == "initiate_trade":
            # Look for a nearby agent to trade with
            nearby = list(self.get_agents_near(agent.position, 10.0))
            if nearby:
                target, dist = nearby[self._rng.integers(len(nearby))]
                if target.is_alive and target.entity_id != agent.entity_id:
                    self.set_relationship(
                        agent.entity_id,
                        target.entity_id,
                        affiliation=0.05,
                    )
                    self.log_event(
                        "trade_proposal",
                        subject_id=agent.entity_id,
                        object_id=target.entity_id,
                        priority=EventPriority.LOW,
                        narrative=f"{agent.name} proposes trade with {target.name}",
                    )

        elif isinstance(action, dict) and action.get("type") == "help":
            # Help another agent (e.g., share knowledge, assist in tasks)
            target_id = action.get("target")
            if target_id:
                target = self.get_agent(target_id)
                if target and target.is_alive:
                    # Update relationship positively
                    self.set_relationship(
                        agent.entity_id,
                        target_id,
                        trust=0.15,
                        affiliation=0.1,
                    )
                    self.log_event(
                        "help",
                        subject_id=agent.entity_id,
                        object_id=target_id,
                        priority=EventPriority.LOW,
                        narrative=f"{agent.name} helps {target.name}",
                    )
                    # Energy cost for helping
                    agent.energy -= 0.05
                    # Record interaction for evolution
                    if self._evolution is not None:
                        self._evolution.process_interaction(
                            agent.entity_id,
                            target_id,
                            interaction_type="help",
                            outcome={"success": True, "fitness_delta": 0.1},
                            tick=tick,
                        )

        elif isinstance(action, dict) and action.get("type") == "share":
            # Share resources with another agent
            target_id = action.get("target")
            if target_id:
                target = self.get_agent(target_id)
                if target and target.is_alive:
                    # Share some resources
                    shared_items = dict(agent.inventory.items)
                    shared_amount = 0.0
                    for resource, amount in shared_items.items():
                        if amount > 0.5:
                            share_amt = amount * 0.2
                            shared_items[resource] -= share_amt
                            shared_amount += share_amt
                            break
                    agent.inventory.items = shared_items
                    agent.energy -= 0.03
                    # Update relationship
                    self.set_relationship(
                        agent.entity_id,
                        target_id,
                        trust=0.1,
                        affiliation=0.15,
                    )
                    self.log_event(
                        "share",
                        subject_id=agent.entity_id,
                        object_id=target_id,
                        priority=EventPriority.LOW,
                        narrative=f"{agent.name} shares resources with {target.name}",
                    )
                    # Record interaction for evolution
                    if self._evolution is not None:
                        self._evolution.process_interaction(
                            agent.entity_id,
                            target_id,
                            interaction_type="share",
                            outcome={"success": True, "fitness_delta": 0.1},
                            tick=tick,
                        )

        elif isinstance(action, dict) and action.get("type") == "exchange":
            # Exchange/gift with another agent
            target_id = action.get("target")
            if target_id:
                target = self.get_agent(target_id)
                if target and target.is_alive:
                    # Create a reciprocal relationship
                    self.set_relationship(
                        agent.entity_id,
                        target_id,
                        trust=0.1,
                        affiliation=0.1,
                        debt=0.5,  # Creates a debt expectation
                    )
                    self.log_event(
                        "exchange",
                        subject_id=agent.entity_id,
                        object_id=target_id,
                        priority=EventPriority.LOW,
                        narrative=f"{agent.name} exchanges with {target.name}",
                    )
                    agent.energy -= 0.02
                    # Record interaction for evolution
                    if self._evolution is not None:
                        self._evolution.process_interaction(
                            agent.entity_id,
                            target_id,
                            interaction_type="exchange",
                            outcome={"success": True, "fitness_delta": 0.1},
                            tick=tick,
                        )

        elif isinstance(action, dict) and action.get("type") == "cooperate":
            # Cooperate with another agent on a shared goal
            target_id = action.get("target")
            if target_id:
                target = self.get_agent(target_id)
                if target and target.is_alive:
                    # Cooperate creates stronger bonds
                    self.set_relationship(
                        agent.entity_id,
                        target_id,
                        trust=0.2,
                        affiliation=0.2,
                    )
                    self.log_event(
                        "cooperate",
                        subject_id=agent.entity_id,
                        object_id=target_id,
                        priority=EventPriority.LOW,
                        narrative=f"{agent.name} cooperates with {target.name}",
                    )
                    agent.energy -= 0.04
                    # Record interaction for evolution
                    if self._evolution is not None:
                        self._evolution.process_interaction(
                            agent.entity_id,
                            target_id,
                            interaction_type="cooperate",
                            outcome={"success": True, "fitness_delta": 0.15},
                            tick=tick,
                        )

        else:
            # Unknown action, just rest
            self._execute_action(agent, "rest", tick)

    def _execute_protocol_action(self, agent: Agent, action: dict, tick: int) -> None:
        """
        Execute a protocol-based action, creating a Trace.
        This is the bridge between deliberation and trace-based interaction.
        """
        if self._protocol is None:
            return

        signal = action.get("signal", "interact")
        receiver_id = action.get("receiver_id", "")
        content = action.get("content", {})
        interpretation = action.get("interpretation", "")

        if not receiver_id:
            return  # Need a receiver for protocol actions

        # Create the trace
        trace = self._protocol.initiate(
            actor=agent,
            signal=signal,
            receiver_id=receiver_id,
            content=content,
            interpretation=interpretation,
        )

        # Record language usage
        if self._language is not None:
            self._language.record_usage(
                signal=signal,
                sender_id=agent.entity_id,
                receiver_id=receiver_id,
                interpreted_meaning=interpretation or signal,
                accepted=False,
                tick=tick,
                trace_id=trace.trace_id,
            )

        # Check the receiver's response
        target = self.get_agent(receiver_id)
        if target and target.is_alive and self._protocol is not None:
            # Receiver interprets and responds
            interp = self._protocol.interpret(target, trace)

            # Decide whether to accept
            should_accept = interp.get("should_respond", False)
            trust = interp.get("trust", 0.5)

            # Personality influences acceptance - more lenient for social interactions
            if hasattr(target, 'agreeableness'):
                if target.agreeableness > 0.4 or trust > 0.5:
                    should_accept = True
                elif target.agreeableness > 0.3 and trust > 0.3:
                    should_accept = True  # Sometimes accept with moderate values

            if should_accept:
                trace.accepted = True
                # Execute the trace effects
                exchanges, _ = self._protocol.execute(trace)
                for exchange in exchanges:
                    if self._economy is not None:
                        self._economy.process_exchange(exchange)

                # Update relationships
                self.set_relationship(
                    agent.entity_id, receiver_id,
                    trust=min(1.0, (trust or 0.5) + 0.1),
                    affiliation=0.05,
                )

            # Record reputation observations
            if self._reputation is not None:
                self._reputation.record_from_trace(trace)

        # Record protocol interaction for evolution
        if self._evolution is not None:
            self._evolution.process_interaction(
                agent.entity_id,
                receiver_id,
                interaction_type=f"protocol_{signal}",
                outcome={
                    "success": trace.accepted,
                    "fitness_delta": 0.1 if trace.accepted else 0.0,
                },
                tick=tick,
            )

        # Log as event
        self.log_event(
            f"protocol_{signal}",
            subject_id=agent.entity_id,
            object_id=receiver_id,
            position=agent.position,
            priority=EventPriority.LOW if trace.accepted else EventPriority.LOW,
            narrative=f"{agent.name} -> {target.name if target else receiver_id[:8]}: {signal} ({'accepted' if trace.accepted else 'declined'})",
        )

    def _update_agent_needs(self, agent: Agent, tick: int) -> None:
        """Update an agent's basic needs each tick."""
        # Hunger and thirst increase over time
        agent.hunger = min(1.0, agent.hunger + 0.002)
        agent.thirst = min(1.0, agent.thirst + 0.003)
        # Energy regenerates slowly when not acting
        if agent.energy < 1.0:
            agent.energy = min(1.0, agent.energy + 0.01)

        # Death from extreme needs
        if agent.hunger >= 1.0 or agent.thirst >= 1.0:
            agent.health -= 0.05
        if agent.health <= 0:
            self._agent_die(agent, tick, cause="starvation" if agent.hunger >= 1.0 else "dehydration")
            return

        # Migration check: if resources are scarce, agent may migrate
        self._check_migration(agent, tick)

        # Age
        if tick > 0 and tick % 360 == 0:  # Every year
            agent.attributes.age += 1

    def _check_migration(self, agent: Agent, tick: int) -> None:
        """
        Check if agent should migrate to find better resources.

        Migration is triggered when:
        1. Local resources are depleted (vegetation < threshold)
        2. Agent is struggling (health < threshold)
        3. High population density in current area
        """
        if not agent.is_alive:
            return

        # Only migrate occasionally (every 50 ticks)
        if tick % 50 != hash(agent.entity_id) % 50:
            return

        # Check local vegetation
        veg = self.get_vegetation(agent.x, agent.y)
        water = self.get_water_proximity(agent.x, agent.y)

        # Migration thresholds
        LOW_VEGETATION = 0.1
        LOW_WATER = 0.2
        STRUGGLING_HEALTH = 0.5

        should_migrate = False
        reason = ""

        if veg < LOW_VEGETATION:
            should_migrate = True
            reason = "low_vegetation"
        elif water < LOW_WATER:
            should_migrate = True
            reason = "low_water"
        elif agent.health < STRUGGLING_HEALTH and veg < 0.3:
            should_migrate = True
            reason = "struggling"

        if not should_migrate:
            return

        # Find a better location
        new_pos = self._find_migration_destination(agent, reason)

        if new_pos is not None:
            # Move to new location
            old_pos = agent.position
            self.move_agent(agent.entity_id, new_pos)

            # Log migration event
            if tick % 100 == 0:  # Don't log every migration
                self.log_event(
                    "agent_migration",
                    subject_id=agent.entity_id,
                    position=new_pos,
                    priority=EventPriority.LOW,
                    narrative=f"{agent.name} migrated ({reason}) from ({old_pos.x:.0f},{old_pos.y:.0f}) to ({new_pos.x:.0f},{new_pos.y:.0f})",
                )

    def _find_migration_destination(self, agent: Agent, reason: str) -> Pos2D | None:
        """
        Find a suitable destination for agent migration.

        Searches in expanding radius until a good location is found.
        """
        current_x, current_y = agent.x, agent.y
        max_radius = 50
        step = 10

        best_pos = None
        best_score = -float('inf')

        for radius in range(step, max_radius + 1, step):
            # Sample positions in a ring at this radius
            samples = [
                (current_x + radius, current_y),
                (current_x - radius, current_y),
                (current_x, current_y + radius),
                (current_x, current_y - radius),
                (current_x + radius * 0.7, current_y + radius * 0.7),
                (current_x - radius * 0.7, current_y + radius * 0.7),
                (current_x + radius * 0.7, current_y - radius * 0.7),
                (current_x - radius * 0.7, current_y - radius * 0.7),
            ]

            for x, y in samples:
                # Check bounds
                if x < 0 or x >= self._config.world.width or y < 0 or y >= self._config.world.height:
                    continue

                # Score this position
                veg = self.get_vegetation(x, y)
                water = self.get_water_proximity(x, y)
                elevation = self.get_elevation(x, y)

                # Calculate score based on migration reason
                if reason == "low_vegetation":
                    score = veg * 2.0 + water
                elif reason == "low_water":
                    score = water * 2.0 + veg
                else:  # struggling
                    score = veg + water + (1.0 - elevation / 100.0)

                # Prefer slightly elevated areas (less likely to flood)
                if elevation > 5:
                    score += 0.2

                if score > best_score:
                    best_score = score
                    best_pos = Pos2D(x=float(x), y=float(y))

            # If we found a good position, stop searching
            if best_score > 0.3:
                break

        return best_pos

    def _agent_die(self, agent: Agent, tick: int, cause: str = "unknown") -> None:
        """Handle agent death."""
        # Determine death narrative based on cause
        narratives = {
            "starvation": f"{agent.name} died of starvation",
            "dehydration": f"{agent.name} died of thirst",
            "age": f"{agent.name} died of old age",
            "conflict": f"{agent.name} died in conflict",
            "disease": f"{agent.name} died from disease",
            "unknown": f"{agent.name} has died",
        }

        self.log_event(
            "agent_death",
            subject_id=agent.entity_id,
            position=agent.position,
            priority=EventPriority.NORMAL,
            narrative=narratives.get(cause, narratives["unknown"]),
            details={"cause": cause, "age": getattr(agent, 'age', 0)},
        )

        # Record death in butterfly effect system for historical tracking
        if self._butterfly_effect is not None:
            self._butterfly_effect.record_micro_event(
                agent_id=agent.entity_id,
                action=f"death_{cause}",
                magnitude=1.0,
                context={"domain": "biology", "cause": cause},
            )

        self.remove_agent(agent.entity_id)

    def _phase_social(self, tick: int) -> None:
        """Process social interactions, reputation, and emergent norms."""
        # Try to form organizations periodically
        if tick % 20 == 0:
            self._try_form_organizations(tick)

        if self._org_manager is not None:
            self._org_manager.update(tick)

        # Process protocol traces
        if self._protocol is not None and tick % 10 == 0:
            self._protocol.process_tick(tick)

        # Spread reputation through gossip (L1 agents gossip more)
        if self._reputation is not None and tick % 15 == 0:
            agents = self.get_all_agents()
            gossipers = [a.entity_id for a in agents if a.is_alive and a.tier.value == "l1_core"]
            self._reputation.spread(tick, gossipers)

        # Detect emergent norms periodically
        if self._norms is not None and tick % 50 == 0:
            self._norms.analyze_traces(tick)

        # Process pending protocol traces for this tick
        if self._protocol is not None:
            for trace in self._protocol._pending_traces:
                if trace.tick == tick:
                    exchanges, _ = self._protocol.execute(trace)
                    for ex in exchanges:
                        if self._economy is not None:
                            self._economy.process_exchange(ex)

        # Self-Evolution: Process cultural transmission and evolution periodically
        if self._evolution is not None and tick % 10 == 0:
            self._phase_evolution(tick)

    def _try_form_organizations(self, tick: int) -> None:
        """Try to form new organizations based on agent clustering."""
        agents = self.get_all_agents()
        if len(agents) < 10:
            return

        rng = self._rng

        # Build a spatial index for clustering
        # For large populations, use grid-based clustering
        grid_size = 20  # 20x20 tile grid cells
        grid: dict[tuple[int, int], list[str]] = {}
        for agent in agents:
            gx = agent.x // grid_size
            gy = agent.y // grid_size
            key = (gx, gy)
            if key not in grid:
                grid[key] = []
            grid[key].append(agent.entity_id)

        # For each grid cell with enough agents, try to form an organization
        for (_gx, _gy), members in grid.items():
            if len(self._organizations) >= 50:
                break

            if len(members) >= 3 and rng.random() < 0.2:
                founder_id = rng.choice(members)
                founder = self.get_agent(founder_id)
                if founder is None:
                    continue

                org_type = rng.choice([OrganizationType.TRIBE, OrganizationType.CLAN, OrganizationType.GUILD])
                name_prefix = rng.choice(['The', 'Ancient', 'New', 'Silver', 'Golden'])
                name_suffix = rng.choice(['Clan', 'Guild', 'People', 'Family', 'Order'])
                org_name = f"{name_prefix} {name_suffix}"

                founding_members = [eid for eid in members[:6] if self.get_agent(eid) is not None]

                org = self.create_organization(
                    name=org_name,
                    org_type=org_type,
                    founder_id=founder_id,
                    position=founder.position,
                    founding_members=founding_members,
                )
                # Register members
                for mid in founding_members:
                    agent = self.get_agent(mid)
                    if agent and org.org_id not in agent.organization_ids:
                        agent.organization_ids.append(org.org_id)
                # Boost relationships among members
                for i, eid1 in enumerate(founding_members):
                    for eid2 in founding_members[i + 1:]:
                        self.set_relationship(eid1, eid2, affiliation=0.4, trust=0.2)

    def _phase_economy(self, tick: int) -> None:
        """Process economic transactions and detect emergent markets."""
        if self._market_system is not None:
            self._market_system.update(tick)
        if self._production_system is not None:
            self._production_system.update(tick)

        # Emergent economy: detect trade patterns and markets periodically
        if self._economy is not None and tick % 25 == 0:
            self._economy.detect_trade_patterns()
            self._economy.detect_markets()
            self._economy.detect_currency()

    def _phase_political(self, tick: int) -> None:
        """Process political and governance systems."""
        if self._governance is not None:
            self._governance.update(tick)

    def _phase_culture(self, tick: int) -> None:
        """Process cultural and linguistic systems."""
        if self._belief_system is not None:
            self._belief_system.update(tick)
        if self._ritual_system is not None:
            self._ritual_system.update(tick)
        if self._art_system is not None:
            self._art_system.update(tick)
        if self._language_system is not None:
            self._language_system.update(tick)

    def _phase_disasters(self, tick: int) -> None:
        """Process natural disasters and their cross-domain effects."""
        if self._disaster_system is not None:
            # Get disasters from this tick
            old_count = len(self._disaster_system._active_disasters)
            self._disaster_system.update(tick, self)
            new_disasters = self._disaster_system._active_disasters[old_count:]

            # Propagate disaster effects to cross-domain systems
            for disaster in new_disasters:
                self._propagate_disaster_effects(disaster, tick)

    def _propagate_disaster_effects(self, disaster: Any, tick: int) -> None:
        """Propagate disaster effects to social, economic, and institutional domains."""
        disaster_type = getattr(disaster, 'disaster_type', 'unknown')
        magnitude = getattr(disaster, 'magnitude', 1.0)
        casualties = getattr(disaster, 'casualties', 0)

        # 1. Propagate to Butterfly Effect System
        if self._butterfly_effect is not None:
            # Record as a major historical event
            context = {
                "domain": "disaster",
                "magnitude": magnitude,
                "type": disaster_type,
            }
            self._butterfly_effect.record_micro_event(
                agent_id="DISASTER",
                action=f"{disaster_type}_magnitude_{magnitude:.1f}",
                magnitude=magnitude * 2.0,  # Disasters have high impact
                context=context,
            )

        # 2. Propagate to Domain Coupling Engine
        if self._domain_coupling is not None:
            from ambientsaga.emergence.full_domain_coupling import Domain

            # Map disaster type to affected domains
            domain_mapping = {
                "plague": (Domain.BIOLOGY, Domain.MEDICINE, Domain.ECONOMICS, Domain.SOCIOLOGY),
                "earthquake": (Domain.PHYSICS, Domain.ECONOMICS, Domain.POLITICS),
                "flood": (Domain.ECOLOGY, Domain.ECONOMICS, Domain.SOCIOLOGY),
                "famine": (Domain.ECONOMICS, Domain.SOCIOLOGY, Domain.POLITICS),
                "fire": (Domain.ECOLOGY, Domain.ECONOMICS),
                "drought": (Domain.ECOLOGY, Domain.ECONOMICS, Domain.SOCIOLOGY),
            }

            affected_domains = domain_mapping.get(disaster_type, (Domain.ECONOMICS,))
            for domain in affected_domains:
                self._domain_coupling.update_domain_state(
                    domain,
                    f"{disaster_type}_severity",
                    magnitude
                )

        # 3. Propagate to Institutional Emergence
        if self._institutional_emergence is not None:
            # Major disasters can trigger institutional formation
            if magnitude >= 2.0 and casualties > 10:
                # Record disaster as a catalyst for institutional emergence
                self._institutional_emergence.record_crisis_event(
                    event_type=disaster_type,
                    severity=magnitude,
                    tick=tick,
                    casualties=casualties,
                )

        # 4. Propagate to Causal Engine
        if self._causal_engine is not None:
            # Check if record_causal_event exists
            if hasattr(self._causal_engine, 'record_causal_event'):
                self._causal_engine.record_causal_event(
                    source_type="disaster",
                    source_id=getattr(disaster, 'disaster_id', 'unknown'),
                    target_type="population",
                    effect_type="mortality",
                    magnitude=magnitude * casualties * 0.01,
                    tick=tick,
                )

        # 5. Propagate to Social Systems (via event log)
        if hasattr(self, '_event_log') and self._event_log is not None:
            if hasattr(self._event_log, 'log_event'):
                self._event_log.log_event(
                    event_type=f"DISASTER_{disaster_type.upper()}",
                    tick=tick,
                    subject_id="DISASTER",
                    details={
                        "type": disaster_type,
                        "magnitude": magnitude,
                        "casualties": casualties,
                        "narrative": getattr(disaster, 'narrative', f'A {disaster_type} occurred'),
                    },
                )

    def _phase_history(self, tick: int) -> None:
        """Record historical events."""
        # Event logging is done on-demand
        pass

    def _phase_evolution(self, tick: int) -> None:
        """
        Process self-evolution: cultural transmission and genome management.

        This phase handles:
        - Cultural transmission (agents learning from each other)
        - Genome aging and fitness evaluation
        - Emergence detection
        - Reproduction (offspring creation)
        """
        if self._evolution is None:
            return

        # Perform evolution tick
        self._evolution.evolve_tick(tick)

        # Process cultural transmission from recent interactions
        agents = self.get_all_agents()
        for agent in agents:
            if not agent.is_alive:
                continue

            # Check for interactions with nearby agents (cultural learning)
            nearby = list(self.get_agents_near(agent.position, 10.0))
            for other, _dist in nearby[:3]:  # Limit to top 3 nearby
                if other.entity_id == agent.entity_id or not other.is_alive:
                    continue

                # Get relationship context
                rel = self.get_relationship(agent.entity_id, other.entity_id)
                if rel is None:
                    continue

                trust = rel.get("trust", 0.0)
                affiliation = rel.get("affiliation", 0.0)

                # High-trust interactions enable cultural learning
                if trust > 0.3 or affiliation > 0.2:
                    # Process this as a cultural interaction
                    self._evolution.process_interaction(
                        agent.entity_id,
                        other.entity_id,
                        interaction_type="social",
                        outcome={
                            "success": trust > 0.5,
                            "fitness_delta": trust * 0.1,
                        },
                        tick=tick,
                    )

        # Handle reproduction periodically
        if tick % 50 == 0:
            self._handle_evolution_reproduction(tick)

        # Print emergence report every 500 ticks
        if tick % 500 == 0 and tick > 0:
            self._evolution.print_emergence_report()

    def _handle_evolution_reproduction(self, tick: int) -> None:
        """
        Handle agent reproduction based on evolution fitness.

        Agents with high fitness may reproduce, creating offspring with
        inherited and mutated behavioral genomes.
        """
        if self._evolution is None:
            return

        agents = self.get_all_agents()
        if len(agents) < 10:
            return

        # Get current population size
        population = len(agents)

        # Check which agents should reproduce
        reproducing_agents: list[tuple[str, str | None]] = []
        for agent in agents:
            if not agent.is_alive:
                continue

            should_reproduce, mate_id = self._evolution.should_reproduce(
                agent.entity_id,
                population,
            )
            if should_reproduce:
                reproducing_agents.append((agent.entity_id, mate_id))
                population += 1  # Track potential offspring

        # Create offspring for reproducing agents
        for parent1_id, parent2_id in reproducing_agents[:10]:  # Limit offspring per tick
            try:
                offspring_id, offspring_genome = self._evolution.create_offspring(
                    parent1_id,
                    parent2_id,
                )

                # Create new agent with inherited genome
                parent = self.get_agent(parent1_id)
                if parent is None:
                    continue

                # Spawn offspring near parent
                from ambientsaga.types import Pos2D
                offset_x = self._rng.integers(-5, 6)
                offset_y = self._rng.integers(-5, 6)
                new_pos = Pos2D(
                    max(0, min(self._config.world.width - 1, parent.x + offset_x)),
                    max(0, min(self._config.world.height - 1, parent.y + offset_y)),
                )

                # Create offspring agent
                from ambientsaga.agents.agent import Agent
                offspring_agent = Agent(
                    entity_id=offspring_id,
                    name=f"{parent.name}'s child",
                    position=new_pos,
                    tier=parent.tier,
                    attributes=parent.attributes,
                )

                # Inherit some personality traits with variation
                offspring_agent.honesty_humility = self._clamp(
                    parent.honesty_humility + self._rng.uniform(-0.1, 0.1), 0, 1
                )
                offspring_agent.emotionality = self._clamp(
                    parent.emotionality + self._rng.uniform(-0.1, 0.1), 0, 1
                )
                offspring_agent.extraversion = self._clamp(
                    parent.extraversion + self._rng.uniform(-0.1, 0.1), 0, 1
                )
                offspring_agent.agreeableness = self._clamp(
                    parent.agreeableness + self._rng.uniform(-0.1, 0.1), 0, 1
                )
                offspring_agent.conscientiousness = self._clamp(
                    parent.conscientiousness + self._rng.uniform(-0.1, 0.1), 0, 1
                )
                offspring_agent.openness = self._clamp(
                    parent.openness + self._rng.uniform(-0.1, 0.1), 0, 1
                )

                # Register the offspring
                if self.register_agent(offspring_agent):
                    # Log the birth
                    self.log_event(
                        "agent_birth",
                        subject_id=offspring_id,
                        object_id=parent1_id,
                        position=new_pos,
                        priority=EventPriority.LOW,
                        narrative=f"{offspring_agent.name} was born to {parent.name}",
                    )
            except Exception:
                # Reproduction failed, continue with other agents
                pass

    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """Clamp a value between min and max."""
        return max(min_val, min(max_val, value))

    def _phase_metrics(self, tick: int) -> None:
        """Collect metrics."""
        if tick % self._config.research.metrics_interval == 0:
            pass  # Metrics collected by research subsystem

    def _phase_emergence_systems(self, tick: int) -> None:
        """
        Run enhanced emergence and causal systems.

        This phase runs all the new systems that enable true emergence:
        1. Unified Causal Engine - domain coupling
        2. Functional Science Engine - actual scientific calculations
        3. True Emergence Layer - spontaneous pattern formation
        4. Historical Butterfly System - historical uniqueness
        5. Performance Optimizer - performance tracking
        """
        import sys
        # Skip if not enough ticks have passed (efficiency)
        if tick % 10 != 0:
            return

        # 1. Run Unified Causal Engine (domain coupling)
        if self._causal_engine is not None:
            self._causal_engine.process_cross_domain_effects(tick)

        # 2. Run Functional Science Engine (scientific calculations)
        if self._functional_science is not None:
            self._functional_science.update(tick)

        # 3. Run True Emergence Layer (spontaneous patterns)
        if self._emergence_layer is not None:
            try:
                _ = self._emergence_layer.get_statistics()
            except Exception as e:
                print(f"[ERROR in _emergence_layer] {type(e).__name__}: {e}", file=sys.stderr, flush=True)

        # 4. Historical Butterfly System
        if self._butterfly_system is not None:
            try:
                self._butterfly_system.update(tick)
            except Exception as e:
                print(f"[ERROR in _butterfly_system.update] {type(e).__name__}: {e}", file=sys.stderr, flush=True)

        # 5. Performance tracking
        if self._optimizer is not None:
            try:
                self._optimizer.record_tick_time(tick, 0.001)  # Placeholder
            except Exception as e:
                print(f"[ERROR in _optimizer.record_tick_time] {type(e).__name__}: {e}", file=sys.stderr, flush=True)

        # === ULTIMATE EMERGENCE: Full Domain Systems ===

        # 6. Butterfly Effect System
        if self._butterfly_effect is not None:
            try:
                self._butterfly_effect.update(tick)
            except Exception as e:
                print(f"[ERROR in _butterfly_effect.update] {type(e).__name__}: {e}", file=sys.stderr, flush=True)

        # 7. Full Domain Coupling Engine (all scientific domains)
        if self._domain_coupling is not None:
            try:
                self._domain_coupling.process_delayed_couplings()
                self._update_domain_states(tick)
            except Exception as e:
                print(f"[ERROR in _domain_coupling] {type(e).__name__}: {e}", file=sys.stderr, flush=True)

        # 8. Institutional Emergence Engine (law, government, religion, class)
        if self._institutional_emergence is not None:
            self._institutional_emergence.update(tick)

    def _update_domain_states(self, tick: int) -> None:
        """Update domain coupling states from world state."""
        if self._domain_coupling is None:
            return


        # Update PHYSICS domain
        if self._temperature is not None:
            avg_temp = float(np.mean(self._temperature))
            self._domain_coupling.update_domain_state(Domain.PHYSICS, "temperature", avg_temp)

        # Update BIOLOGY/ECOLOGY based on agent population
        agent_count = self.get_agent_count()
        self._domain_coupling.update_domain_state(Domain.BIOLOGY, "population", float(agent_count))
        self._domain_coupling.update_domain_state(Domain.ECOLOGY, "population", float(agent_count))

        # Update ECONOMICS based on market activity
        if self._economy is not None:
            exchange_count = len(getattr(self._economy, '_exchange_history', []))
            self._domain_coupling.update_domain_state(Domain.ECONOMICS, "market_activity", float(exchange_count))

        # Update SOCIAL based on relationship count
        self._domain_coupling.update_domain_state(Domain.SOCIOLOGY, "social_connections", float(len(self._relationships)))

    # -------------------------------------------------------------------------
    # Save/Load
    # -------------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        """Save world state to file."""
        with self._lock:
            snapshot = WorldSnapshot(
                version="0.1.0",
                tick=self._tick_engine.tick,
                config=self._config.to_dict(),
                agent_states=[],
                organization_states=[],
                chunk_states=[],
                market_states={},
                climate_state={},
                event_count=self._event_log.get_event_count(),
            )

        with open(path, "wb") as f:
            f.write(msgspec.msgpack.encode(snapshot))

    def load(self, path: str | Path) -> None:
        """Load world state from file."""
        with open(path, "rb") as f:
            snapshot = msgspec.msgpack.decode(f, type=WorldSnapshot)

        with self._lock:
            self._tick_engine.seek(snapshot.tick)

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get world statistics."""
        # Get NEXUS stats
        nexus_stats = {}
        if self._nexus is not None:
            try:
                nexus_stats = self._nexus.get_statistics()
            except Exception:
                nexus_stats = {"error": "NEXUS stats unavailable"}

        return {
            "tick": self._tick_engine.tick,
            "year": self.year,
            "season": self.season,
            "calendar": self._tick_engine.get_calendar_string(),
            "agents": {
                "total": len(self._agents),
            },
            "organizations": {
                "total": len(self._organizations),
            },
            "relationships": {
                "total": len(self._relationships),
            },
            "events_logged": self._stats["events_logged"],
            "signals_published": self._stats["signals_published"],
            "protocol": self._get_protocol_stats(),
            "nexus": nexus_stats,
            "chunk_stats": self._chunk_manager.get_stats(),
            "signal_bus_stats": self._signal_bus.get_stats(),
            "tick_performance": self._tick_engine.get_performance_stats(),
        }

    def _get_protocol_stats(self) -> dict:
        """Get stats from emergent protocol systems."""
        stats = {}
        if self._protocol is not None:
            stats["traces"] = len(self._protocol._traces)
            stats["pending_traces"] = len(self._protocol._pending_traces)
            stats["summary"] = self._protocol.get_summary()
        if self._reputation is not None:
            stats["reputation"] = self._reputation.get_summary()
        if self._language is not None:
            stats["language"] = self._language.get_vocabulary_stats()
        if self._norms is not None:
            stats["norms"] = self._norms.get_summary()
        if self._economy is not None:
            stats["economy"] = self._economy.get_aggregate_stats()
        if self._evolution is not None:
            stats["evolution"] = self._evolution.get_statistics()
        return stats

    def get_summary(self) -> str:
        """Get a human-readable world summary."""
        stats = self.get_stats()
        pstats = stats.get("protocol", {})
        evo_stats = pstats.get("evolution", {})
        stats.get("nexus", {})

        # Get NEXUS stats
        nexus_info = ""
        if self._nexus is not None:
            try:
                ns = self._nexus.get_statistics()
                nexus_info = (
                    f"  NEXUS Events: {ns.get('total_events', 0):,}\n"
                    f"  NEXUS Propagations: {ns.get('total_propagations', 0):,}\n"
                    f"  NEXUS Cascades: {ns.get('total_cascades', 0):,}\n"
                    f"  Butterfly Effects: {ns.get('total_butterflies', 0):,}\n"
                    f"  Emerged Institutions: {ns.get('emerged_institutions', 0):,}"
                )
            except Exception:
                nexus_info = "  NEXUS: active"

        return (
            f"AmbientSaga World\n"
            f"  Tick: {stats['tick']} ({stats['calendar']})\n"
            f"  Agents: {stats['agents']['total']:,}\n"
            f"  Organizations: {stats['organizations']['total']:,}\n"
            f"  Relationships: {stats['relationships']['total']:,}\n"
            f"  Events: {stats['events_logged']:,}\n"
            f"  Protocol Traces: {pstats.get('traces', 0):,}\n"
            f"  Reputation views: {pstats.get('reputation', {}).get('agents_with_views', 0)}\n"
            f"  Language signals: {pstats.get('language', {}).get('total_signals', 0)}\n"
            f"  Norms: {pstats.get('norms', {}).get('total_norms', 0)}\n"
            f"  Economy exchanges: {pstats.get('economy', {}).get('total_exchanges', 0)}\n"
            f"  Evolution Genomes: {evo_stats.get('population_size', 0):,}\n"
            f"  Evolution Gen: {evo_stats.get('generation', 0):,}\n"
            f"  Emergent Institutions: {pstats.get('norms', {}).get('total_norms', 0)}\n"
            f"  Chunks: {stats['chunk_stats']['total_chunks']}\n"
            + (f"\n{nexus_info}" if nexus_info else "")
        )

    def __repr__(self) -> str:
        return (
            f"World({self._config.world.width}x{self._config.world.height}, "
            f"tick={self._tick_engine.tick}, "
            f"agents={len(self._agents)}, "
            f"orgs={len(self._organizations)})"
        )
