"""
Built-in scenario presets for AmbientSaga.

These scenarios provide interesting starting conditions for the simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ambientsaga.scenarios import Scenario

# ---------------------------------------------------------------------------
# Disaster Scenarios
# ---------------------------------------------------------------------------

@dataclass
class VolcanoOutbreak(Scenario):
    """Volcanic eruption scenario - survival after disaster."""

    name: str = "volcano_outbreak"
    description: str = (
        "A massive volcanic eruption devastates the central region. "
        "Survivors must rebuild civilization from the ashes while dealing "
        "with ash clouds, cooling temperatures, and fertile volcanic soil."
    )
    difficulty: str = "hard"
    tags: list = field(default_factory=lambda: ["disaster", "survival", "volcano"])

    world_params: dict = field(default_factory=lambda: {
        "width": 512,
        "height": 512,
        "seed": None,
    })

    terrain_params: dict = field(default_factory=lambda: {
        "mountain_fraction": 0.25,
        "lake_fraction": 0.01,
    })

    initial_conditions: list = field(default_factory=lambda: [
        {"type": "population", "count": 500, "tier": "L1", "spread": "coastal"},
        {"type": "population", "count": 5000, "tier": "L3", "spread": "coastal"},
        {"type": "terrain", "x": 240, "y": 240, "width": 32, "height": 32, "terrain_type": "mountain"},
    ])

    events: list = field(default_factory=lambda: [
        {"tick": 50, "type": "volcanic_eruption", "x": 256, "y": 256, "magnitude": 9.0},
        {"tick": 52, "type": "earthquake", "x": 256, "y": 256, "magnitude": 7.5},
        {"tick": 100, "type": "famine", "magnitude": 0.5},
    ])

    victory_conditions: list = field(default_factory=lambda: [
        {"type": "population_min", "value": 200},
        {"type": "time_limit", "ticks": 500},
    ])

    duration_ticks: int = 500


@dataclass
class GreatFlood(Scenario):
    """Flood disaster scenario - coastal catastrophe."""

    name: str = "great_flood"
    description: str = (
        "Rising waters threaten low-lying settlements. Agents must "
        "decide between evacuation, building defenses, or adapting "
        "to the new coastline."
    )
    difficulty: str = "normal"
    tags: list = field(default_factory=lambda: ["disaster", "flood", "climate"])

    world_params: dict = field(default_factory=lambda: {
        "width": 512,
        "height": 512,
        "seed": None,
    })

    terrain_params: dict = field(default_factory=lambda: {
        "sea_level": 0.40,  # Higher sea level
        "lake_fraction": 0.05,
        "river_count": 20,
    })

    initial_conditions: list = field(default_factory=lambda: [
        {"type": "population", "count": 800, "tier": "L1", "spread": "river"},
        {"type": "population", "count": 8000, "tier": "L3", "spread": "river"},
    ])

    events: list = field(default_factory=lambda: [
        {"tick": 100, "type": "sea_level_rise", "magnitude": 0.15},
        {"tick": 150, "type": "tsunami", "x": 256, "y": 100, "magnitude": 8.0},
        {"tick": 200, "type": "flood", "x": 256, "y": 256, "magnitude": 0.7},
    ])

    victory_conditions: list = field(default_factory=lambda: [
        {"type": "population_min", "value": 500},
        {"type": "organization_count", "value": 5},
    ])

    duration_ticks: int = 600


# ---------------------------------------------------------------------------
# Civilization Scenarios
# ---------------------------------------------------------------------------

@dataclass
class GoldenAge(Scenario):
    """Prosperous civilization scenario."""

    name: str = "golden_age"
    description: str = (
        "A thriving civilization at its peak. Watch as trade networks "
        "expand, arts flourish, and institutions evolve. The challenge "
        "is sustaining this golden age through changing times."
    )
    difficulty: str = "peaceful"
    tags: list = field(default_factory=lambda: ["civilization", "culture", "peaceful"])

    world_params: dict = field(default_factory=lambda: {
        "width": 512,
        "height": 512,
        "seed": 42,  # Fixed seed for reproducibility
    })

    terrain_params: dict = field(default_factory=lambda: {
        "sea_level": 0.35,
        "mountain_fraction": 0.10,
        "forest_fraction": 0.45,
    })

    initial_conditions: list = field(default_factory=lambda: [
        {"type": "population", "count": 1000, "tier": "L1", "spread": "coastal"},
        {"type": "population", "count": 2000, "tier": "L2", "spread": "coastal"},
        {"type": "population", "count": 7000, "tier": "L3", "spread": "coastal"},
        {"type": "resource", "name": "food", "amount": 50000},
        {"type": "resource", "name": "stone", "amount": 30000},
        {"type": "resource", "name": "metal", "amount": 10000},
    ])

    events: list = field(default_factory=lambda: [
        {"tick": 500, "type": "population_boom", "magnitude": 1.5},
        {"tick": 1000, "type": "innovation_surge", "params": {"fields": ["agriculture", "metallurgy"]}},
    ])

    victory_conditions: list = field(default_factory=lambda: [
        {"type": "organization_count", "value": 20},
        {"type": "population_min", "value": 15000},
    ])

    duration_ticks: int = 2000


@dataclass
class Colonization(Scenario):
    """Colonization scenario - clash of cultures."""

    name: str = "colonization"
    description: str = (
        "A powerful civilization expands into new territories, "
        "encountering indigenous populations. Complex interactions "
        "between cultures, technology levels, and values emerge."
    )
    difficulty: str = "hard"
    tags: list = field(default_factory=lambda: ["history", "culture", "conflict"])

    world_params: dict = field(default_factory=lambda: {
        "width": 512,
        "height": 512,
        "seed": None,
    })

    terrain_params: dict = field(default_factory=lambda: {
        "sea_level": 0.35,
        "mountain_fraction": 0.12,
        "forest_fraction": 0.50,
    })

    initial_conditions: list = field(default_factory=lambda: [
        # Indigenous population - spread across land
        {"type": "population", "count": 300, "tier": "L1", "spread": "random"},
        {"type": "population", "count": 5000, "tier": "L3", "spread": "random"},
        # Colonizers arrive on coast
        {"type": "population", "count": 100, "tier": "L1", "spread": "clustered", "cluster_x": 450, "cluster_y": 256},
        {"type": "population", "count": 500, "tier": "L2", "spread": "clustered", "cluster_x": 450, "cluster_y": 256},
    ])

    events: list = field(default_factory=lambda: [
        {"tick": 100, "type": "migration", "x": 450, "y": 256, "magnitude": 200, "params": {"source": "outside"}},
        {"tick": 300, "type": "epidemic", "magnitude": 0.4},
        {"tick": 500, "type": "technology_spread", "params": {"from_tier": "L1", "to_tier": "L3"}},
    ])

    victory_conditions: list = field(default_factory=lambda: [
        {"type": "population_min", "value": 3000},
        {"type": "organization_count", "value": 10},
    ])

    duration_ticks: int = 1000


# ---------------------------------------------------------------------------
# Climate Scenarios
# ---------------------------------------------------------------------------

@dataclass
class IceAge(Scenario):
    """Ice age scenario - survival in harsh conditions."""

    name: str = "ice_age"
    description: str = (
        "Global temperatures drop dramatically as a new ice age begins. "
        "Agents must adapt to expanding glaciers, changing sea levels, "
        "and shifting ecosystems."
    )
    difficulty: str = "extreme"
    tags: list = field(default_factory=lambda: ["climate", "survival", "extreme"])

    world_params: dict = field(default_factory=lambda: {
        "width": 512,
        "height": 512,
        "seed": None,
    })

    climate_params: dict = field(default_factory=lambda: {
        "base_temperature": -5.0,  # Much colder
        "equator_temperature": 20.0,
        "poles_temperature": -40.0,
    })

    terrain_params: dict = field(default_factory=lambda: {
        "sea_level": 0.30,  # Lower due to ice
        "mountain_fraction": 0.15,
        "forest_fraction": 0.30,  # Less forest
    })

    initial_conditions: list = field(default_factory=lambda: [
        {"type": "population", "count": 500, "tier": "L1", "spread": "coastal"},
        {"type": "population", "count": 5000, "tier": "L3", "spread": "coastal"},
    ])

    events: list = field(default_factory=lambda: [
        {"tick": 100, "type": "temperature_drop", "magnitude": -15.0, "duration": 200},
        {"tick": 150, "type": "sea_level_change", "magnitude": -0.1},
        {"tick": 300, "type": "glacier_advance", "x": 256, "y": 50, "magnitude": 50},
        {"tick": 400, "type": "food_shortage", "magnitude": 0.6},
    ])

    victory_conditions: list = field(default_factory=lambda: [
        {"type": "population_min", "value": 100},
        {"type": "time_limit", "ticks": 800},
    ])

    duration_ticks: int = 800


# ---------------------------------------------------------------------------
# Sandbox Scenarios
# ---------------------------------------------------------------------------

@dataclass
class EmptyWorld(Scenario):
    """Empty world for sandbox experimentation."""

    name: str = "empty_world"
    description: str = (
        "A blank slate world with minimal starting conditions. "
        "Perfect for sandbox experimentation or custom scenario building."
    )
    difficulty: str = "peaceful"
    tags: list = field(default_factory=lambda: ["sandbox", "minimal"])

    world_params: dict = field(default_factory=lambda: {
        "width": 256,
        "height": 256,
        "seed": None,
    })

    terrain_params: dict = field(default_factory=lambda: {
        "sea_level": 0.40,
        "mountain_fraction": 0.10,
        "forest_fraction": 0.35,
    })

    initial_conditions: list = field(default_factory=lambda: [
        {"type": "population", "count": 50, "tier": "L1", "spread": "random"},
    ])

    events: list = field(default_factory=lambda: [])

    victory_conditions: list = field(default_factory=lambda: [])

    duration_ticks: int = 0  # Unlimited


@dataclass
class CustomScenario(Scenario):
    """Template for creating custom scenarios."""

    name: str = "custom"
    description: str = "User-defined custom scenario"

    world_params: dict = field(default_factory=dict)
    terrain_params: dict = field(default_factory=dict)
    climate_params: dict = field(default_factory=dict)
    initial_conditions: list = field(default_factory=list)
    events: list = field(default_factory=list)
    victory_conditions: list = field(default_factory=list)
    defeat_conditions: list = field(default_factory=list)
    duration_ticks: int = 0


# Aliases for registry
VOLCANO_OUTBREAK = VolcanoOutbreak
GREAT_FLOOD = GreatFlood
GOLDEN_AGE = GoldenAge
COLONIZATION = Colonization
ICE_AGE = IceAge
EMPTY_WORLD = EmptyWorld
CUSTOM = CustomScenario


# ---------------------------------------------------------------------------
# Scenario Export
# ---------------------------------------------------------------------------

ALL_PRESETS = {
    "volcano_outbreak": VOLCANO_OUTBREAK,
    "great_flood": GREAT_FLOOD,
    "golden_age": GOLDEN_AGE,
    "colonization": COLONIZATION,
    "ice_age": ICE_AGE,
    "empty_world": EMPTY_WORLD,
}
