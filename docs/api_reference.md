# AmbientSaga API Reference

This document describes the public API design principles and the main public APIs in AmbientSaga.

## Design Principles

### Naming Conventions
- **Classes**: PascalCase (e.g., `World`, `Agent`, `SimulationConfig`)
- **Methods/Properties**: snake_case (e.g., `get_agent`, `tick_once`, `tick_engine`)
- **Constants**: SCREAMING_SNAKE_CASE (e.g., `TICK_PHASES`, `MAX_AGENTS`)
- **Private members**: prefixed with `_` (e.g., `_agents`, `_config`)

### Type Hints
- All public methods MUST have type hints for parameters and return types
- Use `None` for optional parameters with no default
- Use `| None` syntax for optional types (Python 3.10+ compatible)
- Import types from `typing` module when needed (e.g., `Any`, `Callable`)

### Docstrings
- All public classes and methods MUST have docstrings
- Use Google-style docstrings:
  ```python
  def method_name(param: Type, other: Type) -> ReturnType:
      """
      Brief description of what the method does.

      More detailed description if needed.

      Args:
          param: Description of param
          other: Description of other

      Returns:
          Description of return value

      Raises:
          ValueError: When this exception is raised
      """
  ```

### Return Types
- Always specify return types explicitly
- Return `None` when no meaningful return value
- Use `tuple` for multiple return values
- Use `dict` for complex structured returns

---

## Core Classes

### World

The central simulation state manager. All state changes go through this class.

```python
class World:
    """Central simulation state manager."""

    # --- Properties (read-only) ---
    @property
    def tick(self) -> int: ...

    @property
    def year(self) -> int: ...

    @property
    def season(self) -> str: ...

    @property
    def tick_engine(self) -> TickEngine: ...

    @property
    def protocol(self) -> MetaProtocol | None: ...

    @property
    def reputation(self) -> ReputationNetwork | None: ...

    # --- Tick Control ---
    def tick_once(self) -> bool: ...

    def run(self, max_ticks: int | None = None) -> int: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def seek(self, tick: int) -> None: ...

    # --- Agent Management ---
    def register_agent(self, agent: "Agent") -> None: ...

    def remove_agent(self, entity_id: EntityID) -> None: ...

    def get_agent(self, entity_id: EntityID) -> "Agent" | None: ...

    def get_all_agents(self) -> list["Agent"]: ...

    def get_agent_count(self) -> int: ...

    def get_agents_in_radius(
        self, pos: Pos2D, radius: float, filter_func: Callable[["Agent"], bool] | None = None
    ) -> list["Agent"]: ...

    # --- Terrain Access ---
    def get_terrain(self, x: int, y: int) -> TerrainType: ...

    def get_elevation(self, x: int, y: int) -> float: ...

    def get_temperature(self, x: int, y: int) -> float: ...

    def get_humidity(self, x: int, y: int) -> float: ...

    # --- Signal System ---
    def publish_signal(
        self,
        signal_type: SignalType,
        source_pos: Pos2D,
        radius: float,
        intensity: float = 1.0,
        data: dict[str, Any] | None = None,
    ) -> None: ...

    # --- State Persistence ---
    def save(self, path: str | Path) -> None: ...

    @classmethod
    def load(cls, path: str | Path) -> "World": ...

    # --- Summary ---
    def get_summary(self) -> str: ...
```

### Agent

Autonomous agent with cognition and behavior.

```python
@dataclass
class Agent:
    """Autonomous agent with perception, cognition, and action."""

    # --- Core Identity ---
    entity_id: EntityID
    name: str
    tier: AgentTier
    position: Pos2D

    # --- State ---
    health: float  # 0.0 to 1.0
    energy: float  # 0.0 to 1.0
    wealth: float

    # --- Behavior ---
    current_goal: str | None
    goal_priority: float  # 0.0 to 1.0

    # --- Methods ---
    def is_alive(self) -> bool: ...

    def get_perception(self, world: World) -> dict[str, Any]: ...

    def decide(self, perception: dict[str, Any]) -> str: ...

    def act(self, decision: str, world: World) -> bool: ...
```

### Config

Configuration management with presets.

```python
class Config:
    """Unified configuration container."""

    @classmethod
    def from_preset(cls, name: Literal["river_valley", "large", "academic", "exploration"]) -> Config: ...

    @classmethod
    def from_file(cls, path: str | Path) -> Config: ...

    @classmethod
    def from_env(cls) -> Config: ...

    @property
    def simulation(self) -> SimulationConfig: ...

    @property
    def world_config(self) -> WorldConfig: ...

    @property
    def agent_config(self) -> AgentConfig: ...

    def to_dict(self) -> dict[str, Any]: ...

    def save(self, path: str | Path) -> None: ...
```

---

## Subsystem APIs

### ScienceEngine

Unified science framework combining physics, chemistry, biology, and ecology.

```python
class ScienceEngine:
    """Unified science framework."""

    def __init__(self, config: ScienceConfig | None = None) -> None: ...

    @property
    def physics(self) -> PhysicsEngine: ...

    @property
    def chemistry(self) -> ChemistryEngine: ...

    @property
    def biology(self) -> BiologyEngine: ...

    @property
    def ecology(self) -> EcosystemEngine: ...

    def update(self, tick: int) -> dict[str, Any]: ...

    def get_statistics(self) -> dict[str, Any]: ...

    def get_cross_domain_coupling(self) -> dict[str, Any]: ...
```

### EvolutionEngine

Self-evolution system for agents.

```python
class EvolutionEngine:
    """Self-evolution engine for agent behavior."""

    def __init__(self, config: EvolutionConfig, rng: random.Random) -> None: ...

    def create_genome(self, agent_id: EntityID, initial_type: str = "random") -> BehaviorGenome: ...

    def remove_genome(self, agent_id: EntityID) -> None: ...

    def get_genome(self, agent_id: EntityID) -> BehaviorGenome | None: ...

    def record_behavior(
        self, agent_id: EntityID, behavior_type: str, tick: int
    ) -> None: ...

    def evolve_population(self) -> dict[str, Any]: ...

    def get_statistics(self) -> dict[str, Any]: ...
```

### MetaProtocol

Emergent interaction protocol for open-ended agent interactions.

```python
class MetaProtocol:
    """Open-ended interaction protocol."""

    def __init__(
        self, world: World, cognitive_manager: CognitiveManager | None = None
    ) -> None: ...

    def deliberate(self, agent: "Agent", tick: int) -> dict[str, Any] | None: ...

    def interpret(self, actor: "Agent", trace: Trace) -> dict[str, Any]: ...

    def execute(self, trace: Trace) -> tuple[list[Exchange], list[Trace]]: ...
```

### Scenario

User-defined simulation scenario.

```python
@dataclass
class Scenario:
    """User-defined simulation scenario."""

    name: str
    description: str
    difficulty: Literal["peaceful", "easy", "normal", "hard", "extreme"]

    world_params: dict[str, Any]
    terrain_params: dict[str, Any]
    climate_params: dict[str, Any]

    initial_conditions: list[dict[str, Any]]
    events: list[dict[str, Any]]
    victory_conditions: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]: ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scenario: ...
```

---

## Type Aliases

Common type aliases used across the API:

```python
# Entity identifiers
EntityID = str

# Positions
Pos2D = tuple[float, float]
Vector2D = tuple[float, float]

# Enums
AgentTier = Literal["L1_CORE", "L2_FUNCTIONAL", "L3_BACKGROUND", "L4_ECOLOGICAL"]
TerrainType = int  # Enum values
SignalType = int  # Enum values
```

---

## Error Handling

Standard error handling patterns:

```python
# ValueError for invalid arguments
if not (0 <= value <= 1):
    raise ValueError(f"Value must be between 0 and 1, got {value}")

# KeyError for missing entities
agent = self._agents.get(entity_id)
if agent is None:
    raise KeyError(f"Agent not found: {entity_id}")

# RuntimeError for invalid state
if not self._running:
    raise RuntimeError("World is not running")
```

---

## Event Naming

Standardized event names for the event log:

```python
# Agent events
"agent_born"        # Agent created
"agent_died"        # Agent removed
"agent_migrated"    # Agent moved significantly
"agent_goal_changed" # Agent goal updated

# Social events
"trade_executed"    # Exchange completed
"relationship_formed"  # New relationship
"relationship_ended"   # Relationship ended
"organization_formed"  # New organization

# World events
"disaster_struck"   # Natural disaster
"climate_changed"   # Climate shift
"discovery_made"    # Significant discovery

# System events
"snapshot_saved"    # State persisted
"checkpoint_created"  # Recovery point created
```

---

## Deprecation Policy

When deprecating APIs:

1. Mark with `@deprecated` decorator and add deprecation message
2. Keep old API working for at least one minor version
3. Log deprecation warnings
4. Document migration path in changelog

```python
def old_method(self) -> None:
    """Old method - use new_method instead."""
    import warnings
    warnings.warn(
        "old_method is deprecated, use new_method instead",
        DeprecationWarning,
        stacklevel=2,
    )
    self.new_method()
```
