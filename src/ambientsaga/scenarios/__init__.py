"""
User-defined scenario system for AmbientSaga.

Scenarios allow users to define custom simulation configurations with:
- Custom world parameters
- Starting conditions
- Event triggers
- Win/ending conditions

Example usage:
    from ambientsaga.scenarios import Scenario, WorldGenerator

    # Define a custom scenario
    scenario = Scenario(
        name="volcano_outbreak",
        description="A volcanic eruption devastates the landscape",
        world_params={"width": 256, "height": 256},
        initial_conditions=[
            {"type": "population", "count": 500, "tier": "L1"},
            {"type": "population", "count": 5000, "tier": "L3"},
            {"type": "resource", "name": "food", "amount": 10000},
        ],
        events=[
            {"tick": 100, "type": "volcanic_eruption", "x": 128, "y": 128, "magnitude": 8.0},
        ],
        victory_conditions=[
            {"type": "population_min", "value": 100},
            {"type": "time_limit", "ticks": 1000},
        ],
    )

    # Apply scenario to simulation
    world_gen = WorldGenerator(config)
    world_gen.apply_scenario(scenario)
    world = world_gen.generate()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from pathlib import Path

__all__ = [
    "Scenario",
    "ScenarioRegistry",
    "WorldGenerator",
    "ScenarioLoader",
]


# ---------------------------------------------------------------------------
# Scenario Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class InitialCondition:
    """Base class for initial conditions."""
    pass


@dataclass
class PopulationCondition(InitialCondition):
    """Population starting condition."""
    count: int = 100
    tier: Literal["L1", "L2", "L3", "L4"] = "L3"
    spread: Literal["random", "coastal", "river", "clustered"] = "random"
    cluster_x: int | None = None
    cluster_y: int | None = None
    cluster_radius: float = 10.0


@dataclass
class ResourceCondition(InitialCondition):
    """Resource deposit starting condition."""
    name: str = "food"
    amount: float = 1000.0
    x: int | None = None
    y: int | None = None
    spread: float = 5.0


@dataclass
class StructureCondition(InitialCondition):
    """Structure (building) starting condition."""
    structure_type: str = "settlement"
    x: int = 0
    y: int = 0
    size: int = 10
    population: int = 0


@dataclass
class TerrainCondition(InitialCondition):
    """Terrain modification condition."""
    x: int = 0
    y: int = 0
    width: int = 10
    height: int = 10
    terrain_type: str = "grassland"


@dataclass
class ScenarioEvent:
    """Event that occurs during the scenario."""
    tick: int = 0
    event_type: str = ""
    x: int = 0
    y: int = 0
    magnitude: float = 1.0
    duration: int = 0
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class VictoryCondition:
    """Condition for winning/completing the scenario."""
    condition_type: str = ""
    value: Any = None
    comparison: Literal["gte", "lte", "eq", "gt", "lt"] = "gte"

    def check(self, world: Any) -> bool:
        """Check if condition is met."""
        if self.condition_type == "population_min":
            return world.get_agent_count() >= self.value
        elif self.condition_type == "population_max":
            return world.get_agent_count() <= self.value
        elif self.condition_type == "time_limit":
            return world.tick >= self.value
        elif self.condition_type == "organization_count":
            return len(world._organizations) >= self.value
        elif self.condition_type == "research_complete":
            return self.value in world._completed_research
        return True


@dataclass
class Scenario:
    """
    User-defined simulation scenario.

    A scenario defines:
    - World parameters (size, terrain, climate)
    - Initial conditions (population, resources, structures)
    - Scheduled events (disasters, discoveries, migrations)
    - Victory conditions (goals to achieve)
    - Metadata (author, difficulty, tags)
    """

    # Core metadata
    name: str = "custom_scenario"
    description: str = ""
    author: str = "Anonymous"
    version: str = "1.0.0"
    difficulty: Literal["peaceful", "easy", "normal", "hard", "extreme"] = "normal"
    tags: list[str] = field(default_factory=list)

    # World parameters (None = use default/preset)
    world_params: dict[str, Any] = field(default_factory=dict)
    terrain_params: dict[str, Any] = field(default_factory=dict)
    climate_params: dict[str, Any] = field(default_factory=dict)

    # Initial conditions
    initial_conditions: list[dict[str, Any]] = field(default_factory=list)

    # Scheduled events
    events: list[dict[str, Any]] = field(default_factory=list)

    # Victory/defeat conditions
    victory_conditions: list[dict[str, Any]] = field(default_factory=list)
    defeat_conditions: list[dict[str, Any]] = field(default_factory=list)

    # Scenario duration
    duration_ticks: int = 0  # 0 = unlimited

    def __post_init__(self) -> None:
        """Convert dict conditions to proper dataclasses."""
        self._parse_conditions()

    def _parse_conditions(self) -> None:
        """Parse dict conditions into dataclasses."""
        parsed_conditions = []

        for cond in self.initial_conditions:
            cond_type = cond.get("type", "")
            if cond_type == "population":
                parsed_conditions.append(PopulationCondition(
                    count=cond.get("count", 100),
                    tier=cond.get("tier", "L3"),
                    spread=cond.get("spread", "random"),
                    cluster_x=cond.get("cluster_x"),
                    cluster_y=cond.get("cluster_y"),
                    cluster_radius=cond.get("cluster_radius", 10.0),
                ))
            elif cond_type == "resource":
                parsed_conditions.append(ResourceCondition(
                    name=cond.get("name", "food"),
                    amount=cond.get("amount", 1000.0),
                    x=cond.get("x"),
                    y=cond.get("y"),
                    spread=cond.get("spread", 5.0),
                ))
            elif cond_type == "structure":
                parsed_conditions.append(StructureCondition(
                    structure_type=cond.get("structure_type", "settlement"),
                    x=cond.get("x", 0),
                    y=cond.get("y", 0),
                    size=cond.get("size", 10),
                    population=cond.get("population", 0),
                ))
            elif cond_type == "terrain":
                parsed_conditions.append(TerrainCondition(
                    x=cond.get("x", 0),
                    y=cond.get("y", 0),
                    width=cond.get("width", 10),
                    height=cond.get("height", 10),
                    terrain_type=cond.get("terrain_type", "grassland"),
                ))
            else:
                # Store unknown conditions as-is
                parsed_conditions.append(cond)

        self._parsed_conditions = parsed_conditions

        # Parse events
        self._parsed_events = []
        for evt in self.events:
            self._parsed_events.append(ScenarioEvent(
                tick=evt.get("tick", 0),
                event_type=evt.get("type", ""),
                x=evt.get("x", 0),
                y=evt.get("y", 0),
                magnitude=evt.get("magnitude", 1.0),
                duration=evt.get("duration", 0),
                params=evt.get("params", {}),
            ))

        # Parse victory conditions
        self._victory_conditions = []
        for vc in self.victory_conditions:
            self._victory_conditions.append(VictoryCondition(
                condition_type=vc.get("type", ""),
                value=vc.get("value"),
                comparison=vc.get("comparison", "gte"),
            ))

    def to_dict(self) -> dict[str, Any]:
        """Serialize scenario to dict."""
        return {
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "difficulty": self.difficulty,
            "tags": self.tags,
            "world_params": self.world_params,
            "terrain_params": self.terrain_params,
            "climate_params": self.climate_params,
            "initial_conditions": self.initial_conditions,
            "events": self.events,
            "victory_conditions": self.victory_conditions,
            "defeat_conditions": self.defeat_conditions,
            "duration_ticks": self.duration_ticks,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scenario:
        """Create scenario from dict."""
        return cls(
            name=data.get("name", "custom_scenario"),
            description=data.get("description", ""),
            author=data.get("author", "Anonymous"),
            version=data.get("version", "1.0.0"),
            difficulty=data.get("difficulty", "normal"),
            tags=data.get("tags", []),
            world_params=data.get("world_params", {}),
            terrain_params=data.get("terrain_params", {}),
            climate_params=data.get("climate_params", {}),
            initial_conditions=data.get("initial_conditions", []),
            events=data.get("events", []),
            victory_conditions=data.get("victory_conditions", []),
            defeat_conditions=data.get("defeat_conditions", []),
            duration_ticks=data.get("duration_ticks", 0),
        )


# ---------------------------------------------------------------------------
# Scenario Registry
# ---------------------------------------------------------------------------


class ScenarioRegistry:
    """
    Registry of built-in and user scenarios.

    Provides discovery, loading, and management of scenarios.
    """

    def __init__(self) -> None:
        self._scenarios: dict[str, type[Scenario]] = {}
        self._load_builtin_scenarios()

    def _load_builtin_scenarios(self) -> None:
        """Load built-in scenario types."""
        # Import here to avoid circular imports
        from ambientsaga.scenarios.presets import (
            VOLCANO_OUTBREAK,
            GREAT_FLOOD,
            GOLDEN_AGE,
            COLONIZATION,
            ICE_AGE,
        )
        self.register(VOLCANO_OUTBREAK)
        self.register(GREAT_FLOOD)
        self.register(GOLDEN_AGE)
        self.register(COLONIZATION)
        self.register(ICE_AGE)

    def register(self, scenario_class: type[Scenario]) -> None:
        """Register a scenario class."""
        # Use the scenario's name attribute (with underscores) for lookup
        instance = scenario_class()
        self._scenarios[instance.name.lower()] = scenario_class

    def get(self, name: str) -> Scenario | None:
        """Get a scenario by name."""
        name_lower = name.lower()
        if name_lower in self._scenarios:
            return self._scenarios[name_lower]()
        return None

    def list_scenarios(self) -> list[str]:
        """List all registered scenario names."""
        return list(self._scenarios.keys())

    def list_by_tag(self, tag: str) -> list[str]:
        """List scenarios with a specific tag."""
        result = []
        for name, cls in self._scenarios.items():
            instance = cls()
            if tag in instance.tags:
                result.append(name)
        return result


# ---------------------------------------------------------------------------
# World Generator with Scenario Support
# ---------------------------------------------------------------------------


class WorldGenerator:
    """
    World generator with scenario support.

    Generates worlds based on configuration and applies scenario modifications.
    """

    def __init__(self, config: Any) -> None:
        self.config = config
        self._scenario: Scenario | None = None
        self._generated_terrain: dict[str, Any] | None = None

    def apply_scenario(self, scenario: Scenario) -> None:
        """Apply a scenario to the generator."""
        self._scenario = scenario

        # Override config with scenario params
        if scenario.world_params:
            for key, value in scenario.world_params.items():
                if hasattr(self.config.simulation.world, key):
                    setattr(self.config.simulation.world, key, value)

        if scenario.terrain_params:
            for key, value in scenario.terrain_params.items():
                if hasattr(self.config.simulation.terrain, key):
                    setattr(self.config.simulation.terrain, key, value)

        if scenario.climate_params:
            for key, value in scenario.climate_params.items():
                if hasattr(self.config.simulation.climate, key):
                    setattr(self.config.simulation.climate, key, value)

    def generate(self) -> Any:
        """Generate a world with scenario modifications."""
        from ambientsaga.world.state import World
        from ambientsaga.natural.terrain import TerrainGenerator
        from ambientsaga.natural.climate import ClimateSystem
        import numpy as np

        # Create base world
        world = World(self.config)

        # Generate terrain with scenario modifications
        terrain_gen = TerrainGenerator(
            self.config.simulation.world,
            self.config.simulation.terrain,
        )
        terrain_data = terrain_gen.generate()
        self._generated_terrain = terrain_data

        # Apply terrain modifications from scenario
        if self._scenario:
            self._apply_terrain_conditions(world, terrain_data)

        # Apply terrain to world
        world._terrain = terrain_data["terrain"]
        world._elevation = terrain_data["elevation"]
        world._soil = terrain_data["soil"]

        # Initialize climate
        climate = ClimateSystem(
            self.config.simulation.climate,
            self.config.simulation.world.width,
            self.config.simulation.world.height,
            self.config.simulation.world.seed,
        )
        lat_range = np.linspace(-90, 90, self.config.simulation.world.height)
        latitude = np.tile(lat_range[:, np.newaxis], (1, self.config.simulation.world.width))
        climate.initialize(world._elevation, latitude)
        world._temperature = climate._temperature
        world._humidity = climate._humidity

        # Apply initial conditions from scenario
        if self._scenario:
            self._apply_initial_conditions(world)

        return world

    def _apply_terrain_conditions(self, world: Any, terrain_data: dict) -> None:
        """Apply terrain modifications from scenario."""
        from ambientsaga.types import TerrainType

        terrain_map = {
            "water": TerrainType.DEEP_OCEAN,
            "shallow_water": TerrainType.SHALLOW_WATER,
            "beach": TerrainType.BEACH,
            "plains": TerrainType.PLAINS,
            "grassland": TerrainType.GRASSLAND,
            "forest": TerrainType.DECIDUOUS_FOREST,
            "mountain": TerrainType.MOUNTAIN,
            "desert": TerrainType.DESERT,
        }

        for cond in self._scenario._parsed_conditions:
            if isinstance(cond, TerrainCondition):
                terrain_type = terrain_map.get(cond.terrain_type, TerrainType.GRASSLAND)
                x1 = max(0, cond.x)
                y1 = max(0, cond.y)
                x2 = min(terrain_data["terrain"].shape[1], cond.x + cond.width)
                y2 = min(terrain_data["terrain"].shape[0], cond.y + cond.height)

                for y in range(y1, y2):
                    for x in range(x1, x2):
                        terrain_data["terrain"][y, x] = terrain_type.value

    def _apply_initial_conditions(self, world: Any) -> None:
        """Apply initial conditions from scenario."""
        from ambientsaga.agents import UnifiedAgentFactory as AgentFactory
        from ambientsaga.types import TerrainType
        import numpy as np

        agents_spawned = []

        for cond in self._scenario._parsed_conditions:
            if isinstance(cond, PopulationCondition):
                # Spawn population
                factory = AgentFactory(world)
                agents = factory.spawn_population(n=cond.count)

                # Apply spread strategy
                if cond.spread == "clustered" and cond.cluster_x is not None:
                    # Move agents toward cluster center
                    for agent in agents:
                        import random
                        angle = random.uniform(0, 2 * 3.14159)
                        dist = random.expovariate(1.0 / cond.cluster_radius)
                        new_x = cond.cluster_x + dist * np.cos(angle)
                        new_y = cond.cluster_y + dist * np.sin(angle)
                        agent.position.x = np.clip(new_x, 0, world._config.world.width - 1)
                        agent.position.y = np.clip(new_y, 0, world._config.world.height - 1)

                agents_spawned.extend(agents)

            elif isinstance(cond, ResourceCondition):
                # Place resource deposit
                x = cond.x if cond.x is not None else np.random.randint(0, world._config.world.width)
                y = cond.y if cond.y is not None else np.random.randint(0, world._config.world.height)

                if not hasattr(world, "_resource_deposits"):
                    world._resource_deposits = []

                world._resource_deposits.append({
                    "name": cond.name,
                    "x": x,
                    "y": y,
                    "amount": cond.amount,
                    "spread": cond.spread,
                })

            elif isinstance(cond, StructureCondition):
                # Create structure
                if not hasattr(world, "_structures"):
                    world._structures = []

                world._structures.append({
                    "type": cond.structure_type,
                    "x": cond.x,
                    "y": cond.y,
                    "size": cond.size,
                    "population": cond.population,
                })

    def get_scheduled_events(self) -> list[ScenarioEvent]:
        """Get events scheduled by the scenario."""
        if self._scenario:
            return self._scenario._parsed_events
        return []


# ---------------------------------------------------------------------------
# Scenario Loader
# ---------------------------------------------------------------------------


class ScenarioLoader:
    """
    Loader for scenario files.

    Supports loading scenarios from JSON, Python modules, or URLs.
    """

    @staticmethod
    def from_file(path: str | Path) -> Scenario:
        """Load scenario from file."""
        import json

        path = Path(path)
        if path.suffix == ".json":
            with open(path) as f:
                data = json.load(f)
            return Scenario.from_dict(data)
        elif path.suffix == ".py":
            # Import Python scenario module
            import importlib.util
            spec = importlib.util.spec_from_file_location("scenario", path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "SCENARIO"):
                    return module.SCENARIO
            raise ValueError(f"Python scenario file must define SCENARIO: {path}")

        raise ValueError(f"Unsupported scenario file type: {path.suffix}")

    @staticmethod
    def from_url(url: str) -> Scenario:
        """Load scenario from URL."""
        import urllib.request
        import json

        with urllib.request.urlopen(url) as response:
            data = json.load(response)
        return Scenario.from_dict(data)

    @staticmethod
    def save(scenario: Scenario, path: str | Path) -> None:
        """Save scenario to file."""
        import json

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(scenario.to_dict(), f, indent=2)


# ---------------------------------------------------------------------------
# CLI Integration
# ---------------------------------------------------------------------------


def register_scenario_cli(subparsers: Any) -> None:
    """Register scenario commands with CLI parser."""
    scenario_parser = subparsers.add_parser("scenario", help="Scenario commands")

    scenario_subparsers = scenario_parser.add_subparsers(dest="scenario_command")

    # List scenarios
    list_parser = scenario_subparsers.add_parser("list", help="List available scenarios")
    list_parser.add_argument("--tag", help="Filter by tag")

    # Info about a scenario
    info_parser = scenario_subparsers.add_parser("info", help="Show scenario details")
    info_parser.add_argument("name", help="Scenario name")

    # Create new scenario
    create_parser = scenario_subparsers.add_parser("create", help="Create new scenario")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--output", required=True)
    create_parser.add_argument("--template", default="blank")


def handle_scenario_command(args: Any) -> int:
    """Handle scenario CLI commands."""
    if args.scenario_command == "list":
        registry = ScenarioRegistry()
        scenarios = registry.list_scenarios()

        if args.tag:
            scenarios = registry.list_by_tag(args.tag)

        print("Available scenarios:")
        for name in scenarios:
            scenario = registry.get(name)
            if scenario:
                print(f"  {name}: {scenario.description[:60]}...")
        return 0

    elif args.scenario_command == "info":
        registry = ScenarioRegistry()
        scenario = registry.get(args.name)

        if not scenario:
            print(f"Unknown scenario: {args.name}")
            return 1

        print(f"=== {scenario.name} ===")
        print(f"Author: {scenario.author}")
        print(f"Version: {scenario.version}")
        print(f"Difficulty: {scenario.difficulty}")
        print(f"Tags: {', '.join(scenario.tags)}")
        print(f"\nDescription:\n{scenario.description}")
        print(f"\nDuration: {scenario.duration_ticks} ticks")
        print(f"\nInitial Conditions: {len(scenario.initial_conditions)}")
        print(f"Events: {len(scenario.events)}")
        print(f"Victory Conditions: {len(scenario.victory_conditions)}")
        return 0

    elif args.scenario_command == "create":
        scenario = Scenario(name=args.name)
        ScenarioLoader.save(scenario, args.output)
        print(f"Created scenario at: {args.output}")
        return 0

    return 0
