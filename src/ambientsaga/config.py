"""
Configuration management for AmbientSaga.

All simulation parameters are centralized here for reproducibility and
experiment control. Every parameter is explicitly typed and validated.

This module follows the principle that configuration is code — every
configurable value has a clear meaning, range, and default.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Dataclass Definitions
# ---------------------------------------------------------------------------


@dataclass
class WorldConfig:
    """Configuration for the physical world dimensions and geography."""

    width: int = 512
    """World width in tiles (X axis)."""

    height: int = 512
    """World height in tiles (Y axis)."""

    tile_size_km: float = 1.0
    """Real-world size of each tile in square kilometers."""

    chunk_size: int = 16
    """Size of spatial chunks for LOD and parallel processing."""

    seed: int | None = None
    """Random seed for reproducible world generation. None = random."""

    @property
    def total_tiles(self) -> int:
        return self.width * self.height

    @property
    def total_km2(self) -> float:
        return self.total_tiles * (self.tile_size_km ** 2)

    def __post_init__(self) -> None:
        if self.seed is None:
            self.seed = secrets.randbelow(2**31)
        if not (64 <= self.width <= 8192):
            raise ValueError(f"width must be between 64 and 8192, got {self.width}")
        if not (64 <= self.height <= 8192):
            raise ValueError(f"height must be between 64 and 8192, got {self.height}")
        if self.chunk_size <= 0 or (self.chunk_size & (self.chunk_size - 1)) != 0:
            raise ValueError(
                f"chunk_size must be a positive power of 2, got {self.chunk_size}"
            )


@dataclass
class TerrainConfig:
    """Configuration for terrain and geological generation."""

    sea_level: float = 0.35
    """Fraction of tiles that are ocean (0.0-1.0)."""

    mountain_fraction: float = 0.15
    """Fraction of land tiles that are mountains."""

    forest_fraction: float = 0.40
    """Fraction of land tiles covered by forest."""

    lake_fraction: float = 0.02
    """Fraction of land tiles that are lakes."""

    river_count: int = 12
    """Number of major rivers to generate."""

    noise_scale_octave1: float = 200.0
    """Large-scale terrain noise wavelength (higher = larger features)."""

    noise_scale_octave2: float = 80.0
    """Medium-scale terrain noise wavelength."""

    noise_scale_octave3: float = 30.0
    """Small-scale terrain noise wavelength."""

    noise_amplitude_ratio: tuple[float, float, float] = (1.0, 0.5, 0.25)
    """Relative amplitude of each noise octave."""

    erosion_iterations: int = 500
    """Number of erosion simulation passes (higher = more realistic)."""

    soil_formation_rate: float = 0.001
    """Rate at which bare rock converts to soil per tick."""

    def __post_init__(self) -> None:
        for name, val in [
            ("sea_level", self.sea_level),
            ("mountain_fraction", self.mountain_fraction),
            ("forest_fraction", self.forest_fraction),
            ("lake_fraction", self.lake_fraction),
        ]:
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be between 0 and 1, got {val}")


@dataclass
class ClimateConfig:
    """Configuration for atmospheric and climate simulation."""

    base_temperature: float = 15.0
    """Mean annual temperature at sea level in Celsius."""

    temperature_lapse_rate: float = 6.5
    """Temperature decrease per 1000m of elevation (C/km)."""

    poles_temperature: float = -20.0
    """Average temperature at poles."""

    equator_temperature: float = 28.0
    """Average temperature at equator."""

    humidity_base: float = 0.6
    """Base atmospheric humidity (0.0-1.0)."""

    wind_base_speed: float = 5.0
    """Base wind speed in m/s."""

    monsoon_enabled: bool = True
    """Whether monsoon seasonal wind reversal is enabled."""

    el_nino_probability: float = 0.05
    """Probability of El Nino event per year."""

    season_length_ticks: int = 360
    """Number of ticks per season (default: 360 ticks = ~6 min real time)."""

    def __post_init__(self) -> None:
        if not -30.0 <= self.base_temperature <= 50.0:
            raise ValueError(
                f"base_temperature must be between -30 and 50, got {self.base_temperature}"
            )


@dataclass
class HydrologyConfig:
    """Configuration for water and hydrological systems."""

    groundwater_capacity: float = 100.0
    """Maximum groundwater storage per tile (mm)."""

    river_erosion_rate: float = 0.01
    """Rate of river bed erosion per flow unit."""

    floodplain_width: int = 3
    """Number of tiles on each side of a river that form the floodplain."""

    lake_evaporation_rate: float = 0.005
    """Daily evaporation rate for inland lakes (fraction of volume)."""

    coastal_salinity_base: float = 35.0
    """Base ocean salinity in g/kg."""

    snowmelt_enabled: bool = True
    """Whether seasonal snowmelt feeds rivers."""

    aquifer_recharge_rate: float = 0.0001
    """Fraction of precipitation that recharge aquifers."""

    flood_return_period: int = 180
    """Average ticks between major flood events."""


@dataclass
class EcologyConfig:
    """Configuration for ecosystem simulation."""

    trophic_efficiency: float = 0.10
    """Energy transfer efficiency between trophic levels (Lindeman efficiency)."""

    max_species_per_tile: int = 8
    """Maximum number of species that can coexist in one tile."""

    plant_regrowth_rate: float = 0.02
    """Fraction of overgrazed vegetation that regrows per tick."""

    carrying_capacity_base: int = 50
    """Base carrying capacity (herbivores per 100 km²)."""

    keystone_species_enabled: bool = True
    """Whether keystone species have disproportionate ecosystem impact."""

    biodiversity_decay_rate: float = 0.001
    """Rate at which species go extinct from habitat loss."""

    invasive_species_enabled: bool = True
    """Whether invasive species can colonize disturbed areas."""

    carbon_cycle_enabled: bool = True
    """Whether carbon sequestration and release is modeled."""

    nitrogen_cycle_enabled: bool = True
    """Whether nitrogen fixation and cycling is modeled."""

    phosphorus_cycle_enabled: bool = True
    """Whether phosphorus weathering cycle is modeled."""

    succession_enabled: bool = True
    """Whether ecological succession is modeled."""

    fire_return_interval: int = 120
    """Average ticks between fire events in fire-prone biomes."""


@dataclass
class DisasterConfig:
    """Configuration for natural disaster systems."""

    earthquake_probability: float = 0.001
    """Probability of major earthquake per tile per year."""

    volcanic_probability: float = 0.0002
    """Probability of volcanic eruption per tile per year."""

    drought_probability: float = 0.005
    """Probability of drought event per region per year."""

    flood_probability: float = 0.008
    """Probability of major flood event per region per year."""

    wildfire_probability: float = 0.003
    """Probability of wildfire per fire-prone tile per year."""

    plague_probability: float = 0.002
    """Probability of plague outbreak per settlement per year."""

    cascade_enabled: bool = True
    """Whether disasters can cascade (earthquake -> tsunami -> plague)."""

    max_cascade_depth: int = 5
    """Maximum depth of disaster cascade chains."""

    recovery_time_multiplier: float = 1.0
    """Multiplier for post-disaster recovery time."""


@dataclass
class AgentConfig:
    """Configuration for agent population and behavior."""

    tier1_count: int = 50
    """Number of L1 Core agents (full LLM reasoning)."""

    tier2_count: int = 500
    """Number of L2 Functional agents (periodic LLM)."""

    tier3_count: int = 9444
    """Number of L3 Background agents (lightweight model)."""

    tier4_count: int = 0
    """Number of L4 Ecological agents (rule-based)."""

    max_perception_radius_tier1: float = 50.0
    """Maximum perception radius for L1 agents (in tiles)."""

    max_perception_radius_tier2: float = 20.0
    """Maximum perception radius for L2 agents."""

    max_perception_radius_tier3: float = 5.0
    """Maximum perception radius for L3 agents."""

    memory_capacity_tier1: int = 1000
    """Maximum episodic memories for L1 agents."""

    memory_capacity_tier2: int = 300
    """Maximum episodic memories for L2 agents."""

    memory_capacity_tier3: int = 50
    """Maximum episodic memories for L3 agents."""

    upgrade_probability: float = 0.01
    """Base probability of L3 agent upgrading per tick when in hotspot."""

    downgrade_probability: float = 0.1
    """Probability of temporary agent downgrade per tick."""

    lifespan_mean: int = 20000
    """Mean agent lifespan in ticks."""

    lifespan_std: int = 5000
    """Standard deviation of agent lifespan."""

    birth_rate: float = 0.0001
    """Base birth rate per eligible agent per tick."""

    def __post_init__(self) -> None:
        total = self.tier1_count + self.tier2_count + self.tier3_count + self.tier4_count
        if total == 0:
            raise ValueError("At least one agent must be configured")
        self._total_agents = total

    @property
    def total_agents(self) -> int:
        return self._total_agents


@dataclass
class CognitionConfig:
    """Configuration for agent cognitive models."""

    need_decay_rate: float = 0.01
    """Base rate at which unmet needs decay (0.0-1.0)."""

    emotional_contagion_strength: float = 0.3
    """How strongly emotions spread through social contact."""

    emotion_decay_base: float = 0.95
    """Base per-tick decay multiplier for emotional intensity."""

    confirmation_bias_strength: float = 0.7
    """Strength of confirmation bias in belief updates."""

    availability_weight: float = 0.3
    """Weight of availability heuristic in probability estimation."""

    loss_aversion_coefficient: float = 2.25
    """Kahneman's loss aversion coefficient (losses weighted this many times more)."""

    overconfidence_factor: float = 1.2
    """Factor by which agents overestimate their own accuracy."""

    deliberation_budget_tier1: int = 8192
    """Max tokens per deliberation for L1 agents."""

    deliberation_budget_tier2: int = 2048
    """Max tokens per deliberation for L2 agents."""

    deliberation_budget_tier3: int = 512
    """Max tokens per deliberation for L3 agents."""

    reflection_threshold: float = 0.7
    """Need satisfaction fraction that triggers reflection."""


@dataclass
class EconomyConfig:
    """Configuration for economic systems."""

    initial_currency_supply: float = 1000000.0
    """Initial money supply in the world."""

    trade_transaction_cost: float = 0.02
    """Fraction of trade value lost as transaction cost."""

    interest_rate_base: float = 0.05
    """Annual base interest rate."""

    interest_rate_volatility: float = 0.02
    """Standard deviation of interest rate changes."""

    wage_minimum: float = 1.0
    """Minimum wage per labor unit."""

    wealth_initial: float = 100.0
    """Initial wealth per agent at world creation."""

    wealth_initial_std: float = 50.0
    """Standard deviation of initial wealth distribution."""

    gini_initial: float = 0.0
    """Initial Gini coefficient (0.0 = perfect equality)."""

    monopoly_threshold: float = 0.5
    """Market share at which an agent is considered monopolistic."""

    price_adjustment_speed: float = 0.1
    """How quickly prices adjust to supply/demand imbalances."""

    labor_productivity_base: float = 1.0
    """Base labor productivity multiplier."""

    technology_productivity_bonus: float = 0.1
    """Productivity bonus per technology level."""


@dataclass
class LLMConfig:
    """Configuration for LLM integration."""

    provider: Literal["anthropic", "openai", "local", "mock"] = "mock"
    """LLM provider to use."""

    model_tier1: str = "claude-opus-4-5"
    """Model for L1 Core agents."""

    model_tier2: str = "claude-sonnet-4-5"
    """Model for L2 Functional agents."""

    model_tier3: str = "claude-haiku-4-5"
    """Model for L3 Background agents (if using LLM)."""

    api_key: str | None = None
    """API key for LLM provider. Falls back to ANTHROPIC_API_KEY env var."""

    base_url: str | None = None
    """Base URL for API endpoint (for proxies/local deployments)."""

    max_retries: int = 3
    """Maximum number of retries for failed API calls."""

    timeout_seconds: int = 30
    """Timeout for LLM API calls."""

    batch_size: int = 50
    """Number of agents to batch in a single LLM call."""

    batch_interval_seconds: float = 1.0
    """Minimum interval between batch LLM calls."""

    cache_enabled: bool = True
    """Whether to cache LLM responses."""

    cache_ttl_seconds: int = 3600
    """TTL for cached LLM responses."""

    temperature_default: float = 0.7
    """Default sampling temperature."""

    temperature_range: tuple[float, float] = (0.0, 2.0)
    """Allowed temperature range for all calls."""

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if self.provider == "mock":
            pass  # No API key needed for mock mode
        elif self.api_key is None:
            raise ValueError(
                f"API key required for provider '{self.provider}'. "
                "Set the ANTHROPIC_API_KEY environment variable or "
                "pass api_key in LLMConfig."
            )


@dataclass
class VisualizationConfig:
    """Configuration for visualization and rendering."""

    enabled: bool = True
    """Whether visualization is enabled."""

    renderer_type: Literal["canvas", "web", "none"] = "canvas"
    """Renderer backend type."""

    fps_target: int = 30
    """Target frames per second for rendering."""

    render_every_n_ticks: int = 10
    """Only render every N simulation ticks."""

    window_width: int = 1280
    """Window width in pixels."""

    window_height: int = 720
    """Window height in pixels."""

    tile_render_size: int = 4
    """Pixels per tile in the default view."""

    show_agent_labels: bool = False
    """Whether to show agent names/IDs on the map."""

    show_signal_overlay: bool = False
    """Whether to overlay active signal propagation."""

    show_network_graph: bool = False
    """Whether to show agent relationship network graph."""

    show_temperature: bool = False
    """Whether to show temperature heatmap."""

    show_biome: bool = True
    """Whether to color tiles by biome type."""

    show_resources: bool = False
    """Whether to show resource distribution."""

    web_port: int = 8765
    """Port for web-based visualization server."""

    web_host: str = "localhost"
    """Host for web-based visualization server."""


@dataclass
class ResearchConfig:
    """Configuration for research and metrics collection."""

    metrics_enabled: bool = True
    """Whether metrics collection is enabled."""

    metrics_interval: int = 100
    """Collect metrics every N ticks."""

    save_snapshots: bool = True
    """Whether to save world state snapshots."""

    snapshot_interval: int = 10000
    """Save snapshot every N ticks."""

    snapshot_dir: Path = field(
        default_factory=lambda: Path.home() / ".ambientsaga" / "snapshots"
    )
    """Directory for saved snapshots."""

    log_events: bool = True
    """Whether to log all significant events."""

    event_log_dir: Path = field(
        default_factory=lambda: Path.home() / ".ambientsaga" / "events"
    )
    """Directory for event logs."""

    trace_causality: bool = True
    """Whether to maintain causal chains between events."""

    benchmark_mode: bool = False
    """Whether to run in benchmark mode (minimal rendering, maximal metrics)."""

    gini_window_size: int = 1000
    """Window size for rolling Gini coefficient calculation."""

    network_sample_size: int = 500
    """Number of agent relationships to sample for network metrics."""


@dataclass
class PoliticalConfig:
    """Configuration for political systems."""

    authority_emergence_threshold: int = 50
    """Minimum population for political institutions to emerge."""

    government_formation_threshold: int = 200
    """Minimum population for formal government to form."""

    election_interval: int = 3600
    """Ticks between elections for democratic governments."""

    coup_threshold: float = 0.3
    """Minimum support for a coup to be attempted."""

    reform_deliberation_ticks: int = 100
    """Minimum ticks for a reform proposal to be voted on."""

    tax_rate_initial: float = 0.1
    """Initial tax rate for new governments."""

    legitimacy_decay_rate: float = 0.001
    """Rate at which legitimacy decays per tick."""

    institutional_learning_rate: float = 0.01
    """Rate at which institutions improve effectiveness over time."""


@dataclass
class CultureConfig:
    """Configuration for cultural systems."""

    belief_spread_rate: float = 0.005
    """Base rate at which beliefs spread between agents."""

    ritual_frequency: float = 0.01
    """Base frequency of cultural rituals per agent per tick."""

    cultural_mobility_rate: float = 0.001
    """Base rate at which agents adopt new cultural practices."""

    dialect_divergence_rate: float = 0.0001
    """Base rate at which dialects diverge."""

    language_contact_threshold: float = 0.2
    """Contact level that triggers linguistic borrowing."""

    art_production_rate: float = 0.002
    """Base rate of art creation per agent per tick."""

    narrative_decay: float = 0.999
    """Per-tick decay multiplier for cultural narratives."""

    cultural_heritages_count: int = 10
    """Number of initial cultural heritage items."""

    myth_formation_threshold: int = 1000
    """Population threshold for myth/legend formation."""


@dataclass
class ScienceConfig:
    """Configuration for unified science systems."""

    enable_physics: bool = True
    """Enable physics simulation."""

    enable_chemistry: bool = True
    """Enable chemistry simulation."""

    enable_biology: bool = True
    """Enable biology simulation."""

    enable_ecology: bool = True
    """Enable ecology simulation."""

    coupling_strength: float = 1.0
    """Strength of cross-domain coupling (0-1)."""

    emergence_detection: bool = True
    """Enable emergent behavior detection."""

    physics_gravity: float = -9.81
    """Gravity in m/s^2."""

    physics_temperature: float = 293.15
    """Ambient temperature in Kelvin."""

    chemistry_reaction_rate: float = 1.0
    """Global reaction rate multiplier."""

    biology_mutation_rate: float = 0.0001
    """Base mutation rate for biology."""

    ecology_trophic_efficiency: float = 0.1
    """Energy transfer efficiency between trophic levels."""


@dataclass
class EmergenceConfig:
    """Configuration for emergent behavior and social dynamics."""

    # World density - agents per 1000 tiles (0.5-5.0 recommended)
    agent_density: float = 2.0
    """Number of agents per 1000 tiles. Higher = more interactions."""

    # Agent interaction probability when not in survival mode
    social_probability: float = 0.35
    """Probability of choosing social goal when survival needs are met."""

    # How much agents move toward each other
    social_attraction: float = 0.6
    """Probability that wandering agents move toward nearby agents."""

    # Protocol vs Rule decision balance
    # 0.0 = pure rules, 1.0 = pure protocol (emergence)
    protocol_weight: float = 0.7
    """Weight of protocol-driven decisions vs rule-based decisions."""

    # World size multiplier (1.0 = default, 0.5 = smaller/denser)
    world_size_multiplier: float = 1.0
    """Multiplier for world dimensions. < 1.0 = smaller, denser world."""

    # Minimum distance for survival focus vs social focus
    survival_threshold: float = 0.85
    """Hunger/thirst threshold for survival mode (overrides social)."""

    energy_threshold: float = 0.15
    """Energy threshold for rest mode (overrides social)."""

    # Agent perception radius for social interactions
    social_perception_radius: float = 10.0
    """How far agents can sense other agents for social behavior."""

    def __post_init__(self) -> None:
        if not (0.1 <= self.agent_density <= 10.0):
            raise ValueError(f"agent_density must be between 0.1 and 10.0, got {self.agent_density}")
        if not (0.0 <= self.social_probability <= 1.0):
            raise ValueError(f"social_probability must be between 0 and 1, got {self.social_probability}")
        if not (0.0 <= self.protocol_weight <= 1.0):
            raise ValueError(f"protocol_weight must be between 0 and 1, got {self.protocol_weight}")
        if not (0.1 <= self.world_size_multiplier <= 4.0):
            raise ValueError(f"world_size_multiplier must be between 0.1 and 4.0, got {self.world_size_multiplier}")


@dataclass
class SimulationConfig:
    """Top-level simulation configuration."""

    world: WorldConfig = field(default_factory=WorldConfig)
    terrain: TerrainConfig = field(default_factory=TerrainConfig)
    climate: ClimateConfig = field(default_factory=ClimateConfig)
    hydrology: HydrologyConfig = field(default_factory=HydrologyConfig)
    ecology: EcologyConfig = field(default_factory=EcologyConfig)
    disaster: DisasterConfig = field(default_factory=DisasterConfig)
    agents: AgentConfig = field(default_factory=AgentConfig)
    cognition: CognitionConfig = field(default_factory=CognitionConfig)
    economy: EconomyConfig = field(default_factory=EconomyConfig)
    political: PoliticalConfig = field(default_factory=PoliticalConfig)
    culture: CultureConfig = field(default_factory=CultureConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)
    research: ResearchConfig = field(default_factory=ResearchConfig)
    science: ScienceConfig = field(default_factory=ScienceConfig)
    emergence: EmergenceConfig = field(default_factory=EmergenceConfig)

    tick_rate: float = 0.0
    """Simulation ticks per second (0 = unlimited/no sleep)."""

    # Alias for tick_rate used by SimulationEngine
    ticks_per_second: float = 0.0

    # Queue and batch sizes for simulation engine
    event_queue_size: int = 100000
    """Maximum size of the event queue."""

    agent_batch_size: int = 100
    """Number of agents to process per batch."""

    snapshot_dir: Path = field(
        default_factory=lambda: Path.home() / ".ambientsaga" / "snapshots"
    )
    """Directory for world snapshots."""

    event_log_dir: Path = field(
        default_factory=lambda: Path.home() / ".ambientsaga" / "event_logs"
    )
    """Directory for event logs."""

    max_ticks: int = 10_000_000
    """Maximum ticks before simulation auto-terminates. 0 = unlimited."""

    warmup_ticks: int = 100
    """Ticks to run before agents begin active decision-making."""

    autosave_interval: int = 50_000
    """Autosave world state every N ticks."""

    autosave_path: Path = field(
        default_factory=lambda: Path.home() / ".ambientsaga" / "autosave.json"
    )
    """Path for autosave files."""

    def __post_init__(self) -> None:
        if self.tick_rate < 0:
            raise ValueError(f"tick_rate must be non-negative, got {self.tick_rate}")
        # Sync ticks_per_second with tick_rate if not explicitly set
        if self.ticks_per_second == 0.0 and self.tick_rate != 0.0:
            self.ticks_per_second = self.tick_rate
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.event_log_dir.mkdir(parents=True, exist_ok=True)
        self.autosave_path.parent.mkdir(parents=True, exist_ok=True)

    def total_agents(self) -> int:
        return self.agents.total_agents

    def agent_density(self) -> float:
        """Agents per square kilometer."""
        return self.total_agents() / self.world.total_km2

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to a dictionary (for JSON export)."""
        import dataclasses

        def _to_dict(obj: Any) -> Any:
            if dataclasses.is_dataclass(obj):
                return {k: _to_dict(v) for k, v in dataclasses.asdict(obj).items()}
            elif isinstance(obj, Path):
                return str(obj)
            elif isinstance(obj, (list, tuple)):
                return [_to_dict(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: _to_dict(v) for k, v in obj.items()}
            else:
                return obj

        return _to_dict(self)


# ---------------------------------------------------------------------------
# Preset Configurations
# ---------------------------------------------------------------------------


def river_valley_config() -> SimulationConfig:
    """
    Recommended starting configuration: a river valley archipelago world
    with high agent density for emergent social behavior.
    Designed for the best balance of complexity, visual appeal,
    and simulation performance on consumer hardware.
    """
    return SimulationConfig(
        world=WorldConfig(width=256, height=256, seed=None),  # Smaller for density
        agents=AgentConfig(
            tier1_count=50,
            tier2_count=500,
            tier3_count=9450,
            max_perception_radius_tier1=20.0,
            max_perception_radius_tier2=10.0,
            max_perception_radius_tier3=5.0,  # Increased for more social interaction
        ),
        terrain=TerrainConfig(
            sea_level=0.30,
            mountain_fraction=0.12,
            forest_fraction=0.45,
            lake_fraction=0.03,
            river_count=15,
            erosion_iterations=200,
        ),
        emergence=EmergenceConfig(
            agent_density=3.0,  # Higher density for more interactions
            social_probability=0.4,  # More social behavior
            social_attraction=0.6,  # Wander toward agents
            protocol_weight=0.7,  # Protocol-driven emergence
            survival_threshold=0.85,  # Higher threshold = less survival focus
        ),
        research=ResearchConfig(
            metrics_interval=50,
            snapshot_interval=10000,
            trace_causality=True,
        ),
    )


def large_civilization_config() -> SimulationConfig:
    """
    Maximum complexity configuration for high-end hardware.
    50,000+ agents with full ecological and social systems.
    """
    return SimulationConfig(
        world=WorldConfig(width=1024, height=1024, seed=None),
        agents=AgentConfig(
            tier1_count=100,
            tier2_count=2000,
            tier3_count=47900,
            max_perception_radius_tier1=60.0,
            max_perception_radius_tier2=25.0,
            max_perception_radius_tier3=5.0,
        ),
        ecology=EcologyConfig(
            biodiversity_decay_rate=0.0005,
            invasive_species_enabled=True,
            carbon_cycle_enabled=True,
            nitrogen_cycle_enabled=True,
        ),
        disaster=DisasterConfig(
            cascade_enabled=True,
            max_cascade_depth=5,
        ),
        research=ResearchConfig(
            metrics_interval=25,
            snapshot_interval=5000,
            trace_causality=True,
        ),
    )


def academic_experiment_config() -> SimulationConfig:
    """
    Configuration optimized for academic research with maximum
    instrumentation and reproducibility features.
    """
    config = river_valley_config()
    config.world.seed = 42  # Deterministic for reproducibility
    config.research.benchmark_mode = True
    config.research.save_snapshots = True
    config.research.snapshot_interval = 5000
    config.visualization.enabled = False
    config.visualization.render_every_n_ticks = 1000
    return config


def interactive_exploration_config() -> SimulationConfig:
    """
    Configuration optimized for interactive exploration with
    beautiful visualization and engaging narrative features.
    """
    return SimulationConfig(
        world=WorldConfig(width=512, height=512, seed=None),
        agents=AgentConfig(
            tier1_count=80,
            tier2_count=1000,
            tier3_count=8920,
        ),
        visualization=VisualizationConfig(
            enabled=True,
            renderer_type="canvas",
            fps_target=60,
            render_every_n_ticks=1,
            show_biome=True,
            show_agent_labels=False,
            show_network_graph=True,
        ),
        research=ResearchConfig(
            metrics_interval=100,
            log_events=True,
            trace_causality=True,
        ),
    )


# ---------------------------------------------------------------------------
# Config Factory
# ---------------------------------------------------------------------------


class Config:
    """
    Unified configuration container with factory methods and validation.

    This class provides a single entry point for all simulation configuration,
    combining dataclass-based configs with factory presets and environment
    variable overrides.

    Example:
        config = Config.from_preset("river_valley")
        config.world.seed = 12345
        config.agents.tier1_count = 100
        world = World(config)
    """

    def __init__(
        self, simulation: SimulationConfig | None = None, **overrides: Any
    ) -> None:
        if simulation is not None:
            self._raw = simulation
        else:
            self._raw = SimulationConfig(**overrides)

    @classmethod
    def from_preset(
        cls, name: Literal["river_valley", "large", "academic", "exploration"]
    ) -> Config:
        """Create configuration from a named preset."""
        presets = {
            "river_valley": river_valley_config,
            "large": large_civilization_config,
            "academic": academic_experiment_config,
            "exploration": interactive_exploration_config,
        }
        if name not in presets:
            raise ValueError(f"Unknown preset: {name}. Available: {list(presets.keys())}")
        return cls(simulation=presets[name]())

    @classmethod
    def from_file(cls, path: str | Path) -> Config:
        """Load configuration from a JSON file."""
        import json

        with open(path) as f:
            data = json.load(f)
        return cls(simulation=SimulationConfig(**data))

    @classmethod
    def from_env(cls) -> Config:
        """Create configuration from environment variables."""
        import json

        overrides: dict[str, Any] = {}

        # Allow overriding via AMBIENTSAGA_CONFIG env var (JSON)
        config_json = os.environ.get("AMBIENTSAGA_CONFIG")
        if config_json:
            try:
                overrides = json.loads(config_json)
            except json.JSONDecodeError:
                pass  # Ignore invalid JSON

        return cls(simulation=SimulationConfig(**overrides))

    @property
    def simulation(self) -> SimulationConfig:
        return self._raw

    @property
    def world_config(self) -> WorldConfig:
        return self._raw.world

    @property
    def agent_config(self) -> AgentConfig:
        return self._raw.agents

    @property
    def terrain_config(self) -> TerrainConfig:
        return self._raw.terrain

    @property
    def climate_config(self) -> ClimateConfig:
        return self._raw.climate

    @property
    def hydrology_config(self) -> HydrologyConfig:
        return self._raw.hydrology

    @property
    def ecology_config(self) -> EcologyConfig:
        return self._raw.ecology

    @property
    def disaster_config(self) -> DisasterConfig:
        return self._raw.disaster

    @property
    def cognition_config(self) -> CognitionConfig:
        return self._raw.cognition

    @property
    def economy_config(self) -> EconomyConfig:
        return self._raw.economy

    @property
    def political_config(self) -> PoliticalConfig:
        return self._raw.political

    @property
    def culture_config(self) -> CultureConfig:
        return self._raw.culture

    @property
    def llm_config(self) -> LLMConfig:
        return self._raw.llm

    @property
    def visualization_config(self) -> VisualizationConfig:
        return self._raw.visualization

    @property
    def research_config(self) -> ResearchConfig:
        return self._raw.research

    @property
    def science_config(self) -> ScienceConfig:
        return self._raw.science

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to a dictionary (for JSON export)."""
        import dataclasses

        def _to_dict(obj: Any) -> Any:
            if dataclasses.is_dataclass(obj):
                return {k: _to_dict(v) for k, v in dataclasses.asdict(obj).items()}
            elif isinstance(obj, Path):
                return str(obj)
            elif isinstance(obj, (list, tuple)):
                return [_to_dict(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: _to_dict(v) for k, v in obj.items()}
            else:
                return obj

        return _to_dict(self._raw)

    def save(self, path: str | Path) -> None:
        """Save configuration to a JSON file."""
        import json

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def __repr__(self) -> str:
        return (
            f"Config(world={self.world_config.width}x{self.world_config.height}, "
            f"agents={self.agent_config.total_agents}, "
            f"tick_rate={self._raw.tick_rate})"
        )
