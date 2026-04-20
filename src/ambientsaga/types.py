"""
Type definitions for AmbientSaga.

This module defines all core data types used throughout the simulation engine.
All types are immutable (frozen) where possible to ensure thread-safety and
prevent accidental mutation. Mutable types are used only where performance
is critical and mutation is controlled.

Types are organized into:
- Primitives: Basic building blocks (Pos2D, EntityID, etc.)
- World types: Terrain, climate, resources, etc.
- Agent types: Tiers, attributes, cognition
- Event types: Signals, events, causal chains
- System types: Configuration types are in config.py
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    Union,
)

# TypeAlias was added in Python 3.10
# For Python 3.9, we need to use typing_extensions or just use plain strings
try:
    from typing import TypeAlias  # Python 3.10+
except ImportError:
    try:
        from typing import TypeAlias  # Python 3.9 with typing_extensions
    except ImportError:
        # Fallback for Python 3.9 without typing_extensions
        TypeAlias = str  # type: ignore

import numpy as np
import numpy.typing as npt

# ---------------------------------------------------------------------------
# Numeric Types
# ---------------------------------------------------------------------------

# Note: AgentTier is defined in agents.core to avoid circular imports
# Import it here for convenient access when needed:
#   from ambientsaga.types import AgentTier
# Or use the agents.core module directly:
#   from ambientsaga.agents.core import AgentTier

FloatArray: TypeAlias = npt.NDArray[np.float64]
IntArray: TypeAlias = npt.NDArray[np.int32]
BoolArray: TypeAlias = npt.NDArray[np.bool_]
ByteArray: TypeAlias = npt.NDArray[np.uint8]

ScalarFloat = Union[float, np.floating[Any]]  # noqa: UP007
ScalarInt = Union[int, np.integer[Any]]  # noqa: UP007

# Simulation time
Tick: TypeAlias = int  # Discrete simulation tick counter
EntityID: TypeAlias = str  # Unique identifier for entities


# ---------------------------------------------------------------------------
# Spatial Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, order=True)
class Pos2D:
    """
    Immutable 2D position in world coordinates.

    Positions use world tile coordinates (not pixels or real-world km).
    The origin (0, 0) is at the southwest corner of the world.
    """

    x: int
    y: int

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError(f"Position coordinates must be non-negative, got ({self.x}, {self.y})")

    def manhattan_distance(self, other: Pos2D) -> int:
        """Manhattan distance to another position."""
        return abs(self.x - other.x) + abs(self.y - other.y)

    def euclidean_distance(self, other: Pos2D) -> float:
        """Euclidean distance to another position."""
        dx = self.x - other.x
        dy = self.y - other.y
        return (dx * dx + dy * dy) ** 0.5

    def chebyshev_distance(self, other: Pos2D) -> int:
        """Chebyshev (max) distance to another position."""
        return max(abs(self.x - other.x), abs(self.y - other.y))

    def within_radius(self, other: Pos2D, radius: float) -> bool:
        """Check if other position is within Euclidean radius of this position."""
        return self.euclidean_distance(other) <= radius

    def within_chunk(self, chunk_size: int) -> tuple[int, int]:
        """Get the chunk coordinates this position belongs to."""
        return (self.x // chunk_size, self.y // chunk_size)

    def neighbors(
        self, include_diagonals: bool = True
    ) -> Iterator[Pos2D]:
        """Iterate over neighboring positions."""
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if include_diagonals:
            deltas.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
        for dx, dy in deltas:
            yield Pos2D(self.x + dx, self.y + dy)

    def clamp(self, min_x: int, max_x: int, min_y: int, max_y: int) -> Pos2D:
        """Return position clamped within bounds."""
        return Pos2D(
            max(min_x, min(max_x, self.x)),
            max(min_y, min(max_y, self.y)),
        )

    def __add__(self, other: Pos2D) -> Pos2D:
        return Pos2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Pos2D) -> Pos2D:
        return Pos2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: int | float) -> Pos2D:
        return Pos2D(int(self.x * scalar), int(self.y * scalar))

    def __iter__(self) -> Iterator[int]:
        return iter((self.x, self.y))


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box in world coordinates."""

    min_x: int
    min_y: int
    max_x: int
    max_y: int

    def contains(self, pos: Pos2D) -> bool:
        return (self.min_x <= pos.x <= self.max_x) and (self.min_y <= pos.y <= self.max_y)

    @property
    def width(self) -> int:
        return self.max_x - self.min_x + 1

    @property
    def height(self) -> int:
        return self.max_y - self.min_y + 1

    @property
    def center(self) -> Pos2D:
        return Pos2D((self.min_x + self.max_x) // 2, (self.min_y + self.max_y) // 2)


@dataclass(frozen=True)
class Rectangle:
    """Axis-aligned rectangle."""

    x: int
    y: int
    width: int
    height: int

    @property
    def bounding_box(self) -> BoundingBox:
        return BoundingBox(
            self.x, self.y, self.x + self.width - 1, self.y + self.height - 1
        )


# ---------------------------------------------------------------------------
# Entity Types
# ---------------------------------------------------------------------------


def new_entity_id() -> EntityID:
    """Generate a new unique entity ID."""
    return uuid.uuid4().hex[:16]


# ---------------------------------------------------------------------------
# World Types
# ---------------------------------------------------------------------------


class TerrainType(Enum):
    """Terrain biome types."""

    DEEP_OCEAN = auto()
    OCEAN = auto()
    SHALLOW_WATER = auto()
    BEACH = auto()
    DESERT = auto()
    DESERT_SCRUB = auto()
    GRASSLAND = auto()
    SAVANNA = auto()
    SHRUBLAND = auto()
    TEMPERATE_FOREST = auto()
    TROPICAL_FOREST = auto()
    BOREAL_FOREST = auto()
    RAINFOREST = auto()
    TUNDRA = auto()
    MARSH = auto()
    SWAMP = auto()
    HILLS = auto()
    MOUNTAINS = auto()
    HIGH_MOUNTAINS = auto()
    PLATEAU = auto()
    CAVE = auto()  # Underground, accessible from mountains

    @property
    def is_land(self) -> bool:
        return self not in {
            TerrainType.DEEP_OCEAN,
            TerrainType.OCEAN,
            TerrainType.SHALLOW_WATER,
            TerrainType.BEACH,
        }

    @property
    def is_water(self) -> bool:
        return self in {
            TerrainType.SHALLOW_WATER,
            TerrainType.OCEAN,
            TerrainType.DEEP_OCEAN,
        }

    @property
    def is_forest(self) -> bool:
        return self in {
            TerrainType.TEMPERATE_FOREST,
            TerrainType.TROPICAL_FOREST,
            TerrainType.BOREAL_FOREST,
            TerrainType.RAINFOREST,
        }

    @property
    def is_mountain(self) -> bool:
        return self in {
            TerrainType.MOUNTAINS,
            TerrainType.HIGH_MOUNTAINS,
            TerrainType.PLATEAU,
        }

    @property
    def movement_cost(self) -> float:
        """Multiplier for movement speed through this terrain."""
        costs = {
            TerrainType.DEEP_OCEAN: float("inf"),
            TerrainType.OCEAN: float("inf"),
            TerrainType.SHALLOW_WATER: 3.0,
            TerrainType.BEACH: 1.2,
            TerrainType.DESERT: 1.5,
            TerrainType.DESERT_SCRUB: 1.3,
            TerrainType.GRASSLAND: 1.0,
            TerrainType.SAVANNA: 1.1,
            TerrainType.SHRUBLAND: 1.2,
            TerrainType.TEMPERATE_FOREST: 1.5,
            TerrainType.TROPICAL_FOREST: 1.8,
            TerrainType.BOREAL_FOREST: 1.6,
            TerrainType.RAINFOREST: 2.0,
            TerrainType.MARSH: 2.0,
            TerrainType.SWAMP: 2.5,
            TerrainType.HILLS: 1.4,
            TerrainType.MOUNTAINS: 2.5,
            TerrainType.HIGH_MOUNTAINS: 4.0,
            TerrainType.PLATEAU: 1.3,
            TerrainType.CAVE: 1.0,
        }
        return costs[self]


class Vector2D:
    """2D vector for movement and physics."""

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y

    def __add__(self, other: Vector2D) -> Vector2D:
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2D) -> Vector2D:
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2D:
        return Vector2D(self.x * scalar, self.y * scalar)

    def magnitude(self) -> float:
        return (self.x * self.x + self.y * self.y) ** 0.5

    def normalized(self) -> Vector2D:
        mag = self.magnitude()
        if mag == 0:
            return Vector2D(0, 0)
        return Vector2D(self.x / mag, self.y / mag)


class ClimateZone(Enum):
    """Climate zones of the world."""

    TROPICAL = auto()
    SUBTROPICAL = auto()
    TEMPERATE = auto()
    CONTINENTAL = auto()
    POLAR = auto()
    ARID = auto()
    TROPICAL_DESERT = auto()


class SoilType(Enum):
    """Soil type classifications."""

    ROCK = auto()
    ALLUVIAL = auto()
    LOAM = auto()
    SAND = auto()
    CLAY = auto()
    SILT = auto()
    PEAT = auto()
    CHALK = auto()


class MineralType(Enum):
    """Mineral and ore types for mining."""

    IRON_ORE = auto()
    COPPER_ORE = auto()
    GOLD_ORE = auto()
    SILVER_ORE = auto()
    TIN_ORE = auto()
    COAL = auto()
    SALT = auto()
    FLINT = auto()
    CLAY = auto()
    LIMESTONE = auto()
    SULFUR = auto()
    GEMSTONES = auto()


class BiomeType(Enum):
    """Biome type classifications."""

    DEEP_SEA = auto()
    MARINE = auto()
    LITTORAL = auto()
    SANDY_SHORE = auto()
    DESERT = auto()
    XERISCAPE = auto()
    GRASSLAND = auto()
    SAVANNA_BIOME = auto()
    TEMPERATE_FOREST_BIOME = auto()
    TAIGA = auto()
    TROPICAL_FOREST_BIOME = auto()
    RAINFOREST_BIOME = auto()
    WETLAND = auto()
    SWAMP_BIOME = auto()
    HIGHLAND = auto()
    ALPINE = auto()
    HIGHPLAIN = auto()
    HILLSIDE = auto()
    UNDERGROUND = auto()


class Biome(Enum):
    """Biome classification matching world engine biomes."""

    DEEP_SEA = auto()
    MARINE = auto()
    LITTORAL = auto()
    SANDY_SHORE = auto()
    DESERT = auto()
    XERISCAPE = auto()
    GRASSLAND = auto()
    SAVANNA_BIOME = auto()
    TEMPERATE_FOREST_BIOME = auto()
    TAIGA = auto()
    TROPICAL_FOREST_BIOME = auto()
    RAINFOREST_BIOME = auto()
    WETLAND = auto()
    SWAMP_BIOME = auto()
    HIGHLAND = auto()
    ALPINE = auto()
    HIGHPLAIN = auto()
    HILLSIDE = auto()
    UNDERGROUND = auto()


class ClimateType(Enum):
    """Climate zones."""

    TROPICAL = auto()
    SUBTROPICAL = auto()
    MEDITERRANEAN = auto()
    TEMPERATE = auto()
    CONTINENTAL = auto()
    SUBARCTIC = auto()
    ARCTIC = auto()
    SEMI_ARID = auto()
    ARID = auto()


class Season(Enum):
    """Seasonal cycles."""

    SPRING = auto()
    SUMMER = auto()
    AUTUMN = auto()
    WINTER = auto()


class ResourceType(Enum):
    """Types of resources available in the world.

    Note: This enum includes both resource source locations (e.g., HUNTING_GROUNDS)
    and actual resources (e.g., FOOD, WATER). Code should use the actual resource
    names for inventory and trade.
    """

    # Core resources (actual resources)
    FOOD = auto()
    WATER = auto()
    WOOD = auto()
    STONE = auto()

    # Processed materials
    TOOLS = auto()
    WEAPONS = auto()
    CLOTHING = auto()
    COPPER = auto()
    IRON = auto()
    GOLD = auto()

    # Natural resources (source locations)
    HUNTING_GROUNDS = auto()
    FISHING_WATERS = auto()
    GRAIN_FIELD = auto()
    FRUIT_TREES = auto()
    ROOTS_TUBERS = auto()
    FLORA = auto()
    MINERALS = auto()
    FERTILE_SOIL = auto()

    # Raw materials
    CLAY = auto()
    FIBER = auto()
    FLAX = auto()
    COTTON = auto()

    # Ores
    COPPER_ORE = auto()
    TIN_ORE = auto()
    IRON_ORE = auto()
    COAL = auto()
    SILVER_ORE = auto()
    GEMSTONES = auto()

    # Trade goods
    SALT = auto()
    SPICES = auto()
    FUR = auto()
    HONEY = auto()
    HERBS = auto()

    # Energy
    HOT_SPRING = auto()  # Geothermal

    @property
    def is_food(self) -> bool:
        return self in {
            ResourceType.FOOD,
            ResourceType.HUNTING_GROUNDS,
            ResourceType.FISHING_WATERS,
            ResourceType.GRAIN_FIELD,
            ResourceType.FRUIT_TREES,
            ResourceType.ROOTS_TUBERS,
            ResourceType.FLORA,
        }

    @property
    def is_mineral(self) -> bool:
        return self in {
            ResourceType.COPPER,
            ResourceType.TIN_ORE,
            ResourceType.IRON,
            ResourceType.COAL,
            ResourceType.GOLD,
            ResourceType.SILVER_ORE,
            ResourceType.GEMSTONES,
            ResourceType.STONE,
            ResourceType.CLAY,
            ResourceType.MINERALS,
        }

    @property
    def base_value(self) -> float:
        """Base trade value of this resource."""
        values = {
            # Core resources
            ResourceType.FOOD: 1.0,
            ResourceType.WATER: 0.5,
            ResourceType.WOOD: 1.0,
            ResourceType.STONE: 1.5,
            # Processed materials
            ResourceType.TOOLS: 10.0,
            ResourceType.WEAPONS: 20.0,
            ResourceType.CLOTHING: 8.0,
            ResourceType.COPPER: 15.0,
            ResourceType.IRON: 25.0,
            ResourceType.GOLD: 100.0,
            # Source locations (lower value as they're locations, not actual resources)
            ResourceType.HUNTING_GROUNDS: 2.0,
            ResourceType.FISHING_WATERS: 2.0,
            ResourceType.GRAIN_FIELD: 1.5,
            ResourceType.FRUIT_TREES: 1.5,
            ResourceType.ROOTS_TUBERS: 1.0,
            ResourceType.FLORA: 0.8,
            ResourceType.MINERALS: 5.0,
            ResourceType.FERTILE_SOIL: 1.0,
            # Raw materials
            ResourceType.CLAY: 0.5,
            ResourceType.FIBER: 0.8,
            ResourceType.FLAX: 1.0,
            ResourceType.COTTON: 1.2,
            # Ores
            ResourceType.COPPER_ORE: 5.0,
            ResourceType.TIN_ORE: 5.0,
            ResourceType.IRON_ORE: 8.0,
            ResourceType.COAL: 3.0,
            ResourceType.SILVER_ORE: 15.0,
            ResourceType.GEMSTONES: 25.0,
            # Trade goods
            ResourceType.SALT: 4.0,
            ResourceType.SPICES: 12.0,
            ResourceType.FUR: 6.0,
            ResourceType.HONEY: 2.0,
            ResourceType.HERBS: 3.0,
            # Energy
            ResourceType.HOT_SPRING: 2.0,
        }
        return values.get(self, 1.0)


@dataclass(frozen=True)
class Tile:
    """
    A single tile in the world grid.

    Each tile has terrain, climate, resources, and owner information.
    """

    position: Pos2D
    terrain: TerrainType
    elevation: int  # 0-100
    climate: ClimateType
    fertility: float  # 0.0-1.0
    water_access: float  # 0.0-1.0
    resources: frozenset[ResourceType]
    owner_id: EntityID | None = None
    settlement_id: EntityID | None = None
    population: int = 0
    development_level: float = 0.0  # 0.0-1.0

    @property
    def is_habitable(self) -> bool:
        return self.terrain.is_land and self.terrain != TerrainType.CAVE

    @property
    def movement_cost(self) -> float:
        return self.terrain.movement_cost


@dataclass(frozen=True)
class MineralDeposit:
    """A mineral deposit at a world position."""

    position: Pos2D
    mineral_type: MineralType
    richness: float  # 0.0-1.0
    depth: float  # meters below surface
    remaining: float  # units remaining

    def extraction_difficulty(self) -> float:
        return self.depth * 0.1 + (1.0 - self.richness) * 0.5


@dataclass(frozen=True)
class ResourceNode:
    """
    A resource node in the world (renewable or non-renewable).
    """

    position: Pos2D
    resource_type: ResourceType
    capacity: float  # total capacity
    regeneration_rate: float  # per tick (0 if non-renewable)
    current_amount: float
    quality: float  # 0.0-1.0

    def extract(self, amount: float) -> float:
        actual = min(amount, self.current_amount)
        self.current_amount -= actual
        return actual

    def regenerate(self) -> None:
        if self.regeneration_rate > 0:
            self.current_amount = min(self.capacity, self.current_amount + self.regeneration_rate)


@dataclass()
class WorldMap:
    """
    The world map containing all tiles and terrain data.

    Uses numpy arrays for efficient spatial queries.
    """

    width: int
    height: int
    tiles: npt.NDArray[np.object_]  # 2D array of Tile
    terrain_grid: npt.NDArray[np.int8]  # Terrain type indices
    elevation_grid: npt.NDArray[np.float32]  # Elevation data
    climate_grid: npt.NDArray[np.int8]  # Climate type indices

    def __post_init__(self) -> None:
        if self.terrain_grid.shape != (self.height, self.width):
            raise ValueError("Terrain grid dimensions must match world dimensions")
        if self.elevation_grid.shape != (self.height, self.width):
            raise ValueError("Elevation grid dimensions must match world dimensions")
        if self.climate_grid.shape != (self.height, self.width):
            raise ValueError("Climate grid dimensions must match world dimensions")

    def get_tile(self, pos: Pos2D) -> Tile | None:
        if not self.is_valid_position(pos):
            return None
        return self.tiles[pos.y, pos.x]

    def is_valid_position(self, pos: Pos2D) -> bool:
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def get_tiles_in_rect(self, bbox: BoundingBox) -> list[Tile]:
        """Get all tiles within a bounding box."""
        tiles = []
        for y in range(max(0, bbox.min_y), min(self.height, bbox.max_y + 1)):
            for x in range(max(0, bbox.min_x), min(self.width, bbox.max_x + 1)):
                tile = self.tiles[y, x]
                if tile is not None:
                    tiles.append(tile)
        return tiles

    def get_tiles_in_radius(self, center: Pos2D, radius: float) -> list[Tile]:
        """Get all tiles within Euclidean radius of a center point."""
        tiles = []
        r = int(radius) + 1
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                pos = Pos2D(center.x + dx, center.y + dy)
                if self.is_valid_position(pos) and center.within_radius(pos, radius):
                    tile = self.tiles[pos.y, pos.x]
                    if tile is not None:
                        tiles.append(tile)
        return tiles

    def get_terrain_at(self, pos: Pos2D) -> TerrainType | None:
        if not self.is_valid_position(pos):
            return None
        return TerrainType(self.terrain_grid[pos.y, pos.x])

    def update_tile(self, pos: Pos2D, tile: Tile) -> None:
        if self.is_valid_position(pos):
            self.tiles[pos.y, pos.x] = tile


# ---------------------------------------------------------------------------
# Agent Types
# ---------------------------------------------------------------------------


# Agent types are defined in agents.core to avoid circular imports
# This ensures AgentTier is consistent across the codebase


class Attribute(Enum):
    """Agent attribute dimensions."""

    STRENGTH = auto()
    INTELLIGENCE = auto()
    CHARISMA = auto()
    WISDOM = auto()
    DEXTERITY = auto()
    ENDURANCE = auto()
    PERCEPTION = auto()
    CREATIVITY = auto()
    PATIENCE = auto()
    COURAGE = auto()
    JUST = auto()  # Sense of justice
    GREED = auto()
    COMPASSION = auto()
    PRIDE = auto()
    ENVY = auto()
    TEMPERANCE = auto()


@dataclass(frozen=True)
class AgentAttributes:
    """An agent's fixed attributes (personality, appearance, etc.)."""

    name: str
    age: int
    gender: str
    attributes: frozenset[tuple[Attribute, float]]  # attribute -> value 0.0-1.0
    culture_id: str
    native_language: str
    appearance: str  # Brief description
    personality_summary: str  # Brief personality summary
    backstory: str  # Backstory/memories
    talents: frozenset[str]
    flaws: frozenset[str]
    ambition: str
    fear: str
    secret: str | None = None

    def get_attribute(self, attr: Attribute) -> float:
        for a, v in self.attributes:
            if a == attr:
                return v
        return 0.5  # Default

    def get_dominant_attribute(self) -> Attribute:
        return max(self.attributes, key=lambda x: x[1])[0]


# ---------------------------------------------------------------------------
# Signal / Event Types
# ---------------------------------------------------------------------------


class SignalType(Enum):
    """Types of signals agents can perceive."""

    # Environmental
    WEATHER_CHANGE = auto()
    NATURAL_DISASTER = auto()
    SEASON_CHANGE = auto()
    RESOURCE_DEPLETION = auto()
    RESOURCE_ABUNDANCE = auto()

    # Social
    TRADE_OPPORTUNITY = auto()
    CONFLICT_WARNING = auto()
    FESTIVAL_ANNOUNCEMENT = auto()
    GOVERNANCE_PROPOSAL = auto()
    DIPLOMATIC_MESSAGE = auto()
    RUMOR = auto()
    GRIEF = auto()  # Death notice
    BIRTH = auto()
    WEDDING = auto()
    DISCOVERY = auto()  # New resource/technology

    # Personal
    HUNGER = auto()
    THIRST = auto()
    INJURY = auto()
    ILLNESS = auto()
    LONELINESS = auto()
    CELEBRATION = auto()


@dataclass(frozen=True)
class Signal:
    """
    A signal (perceivable event) in the world.

    Signals are the raw data that agents perceive before filtering.
    """

    signal_type: SignalType
    position: Pos2D
    tick: int
    source_id: EntityID | None
    intensity: float  # 0.0-1.0
    content: str  # Human-readable description
    metadata: frozenset[tuple[str, Any]]  # Additional data


class EventType(Enum):
    """Types of events in the world."""

    # Birth & Death
    BIRTH = auto()
    DEATH = auto()
    MURDER = auto()

    # Social
    MARRIAGE = auto()
    DIVORCE = auto()
    FRIENDSHIP_FORMED = auto()
    FRIENDSHIP_ENDED = auto()
    RIVALRY_FORMED = auto()
    TRADE = auto()
    GIFT = auto()
    FESTIVAL = auto()

    # Conflict
    BATTLE = auto()
    SIEGE = auto()
    TREATY = auto()
    DECLARATION_OF_WAR = auto()

    # Governance
    LAW_PASSED = auto()
    REBELLION = auto()
    ELECTION = auto()
    CROWNING = auto()
    ABDICATION = auto()

    # Discovery
    RESOURCE_DISCOVERED = auto()
    TECHNOLOGY_DISCOVERED = auto()
    LAND_CLAIMED = auto()
    SETTLEMENT_FOUNDED = auto()
    SETTLEMENT_ABANDONED = auto()

    # Natural
    DROUGHT = auto()
    FLOOD = auto()
    EARTHQUAKE = auto()
    PLAGUE = auto()
    FAMINE = auto()
    METEOR = auto()

    # Cultural
    RELIGION_FOUNDED = auto()
    PROPHECY_SPOKEN = auto()
    ART_CREATED = auto()
    LANGUAGE_EMERGED = auto()
    STORY_TOLD = auto()

    # Cognitive
    DECISION_MADE = auto()
    BELIEF_CHANGED = auto()
    MEMORY_FORMED = auto()
    PLAN_CONCEIVED = auto()

    # Custom/Simulation events
    CUSTOM = auto()
    EXPLORATION = auto()
    SOCIAL_INTERACTION = auto()
    TRADE_PROPOSAL = auto()
    AGENT_DEATH = auto()


class EventPriority(Enum):
    """Event priority for processing."""

    CRITICAL = 0  # Disaster, death
    HIGH = 1  # Conflict, major transactions
    NORMAL = 2  # Most events
    LOW = 3  # Minor interactions


@dataclass(frozen=True)
class Event:
    """
    A simulation event that occurred in the world.

    Events are the fundamental unit of history and causality tracking.
    """

    event_type: EventType
    tick: int
    position: Pos2D | None
    subject_id: EntityID | None
    object_id: EntityID | None
    cause_id: str | None  # Causal chain ID
    description: str
    priority: EventPriority
    metadata: frozenset[tuple[str, Any]]
    impact_radius: float = 0.0  # 0 = local only

    def __post_init__(self) -> None:
        if self.cause_id is None:
            object.__setattr__(self, 'cause_id', uuid.uuid4().hex)


@dataclass(frozen=True)
class CausalChain:
    """A causal chain linking related events."""

    chain_id: str
    events: tuple[Event, ...]  # Ordered by tick
    summary: str  # AI-generated summary of the chain


# ---------------------------------------------------------------------------
# Organization Types
# ---------------------------------------------------------------------------


class OrganizationType(Enum):
    """Types of organizations."""

    FAMILY = auto()
    CLAN = auto()
    TRIBE = auto()
    BAND = auto()
    GUILD = auto()
    MERCHANT_COMPANY = auto()
    RELIGIOUS_ORDER = auto()
    MILITARY_FORCE = auto()
    KINGDOM = auto()
    EMPIRE = auto()
    REPUBLIC = auto()
    CITY_STATE = auto()
    DEMOCRACY = auto()
    TRIBAL_COUNCIL = auto()
    SECRET_SOCIETY = auto()


class OrganizationRank(Enum):
    """Ranks within organizations."""

    MEMBER = 0
    ELDER = 1
    CAPTAIN = 2
    COMMANDER = 3
    COUNCILOR = 4
    MINISTER = 5
    VIZIER = 6
    NOBLE = 7
    ROYAL = 8
    MONARCH = 9


@dataclass
class Organization:
    """
    An organization (clan, guild, kingdom, etc.).
    """

    org_id: EntityID
    name: str
    org_type: OrganizationType
    founding_tick: int
    founding_position: Pos2D
    leader_id: EntityID | None = None
    parent_org_id: EntityID | None = None  # For nested orgs (e.g., guilds in kingdom)
    territory: BoundingBox | None = None
    founding_members: frozenset[EntityID] = field(default_factory=frozenset)
    ideology: str = ""  # Brief description of beliefs/goals
    treasury: float = 0.0
    population: int = 0
    reputation: float = 0.5  # 0.0-1.0
    stability: float = 0.5  # 0.0-1.0
    culture_ids: frozenset[str] = field(default_factory=frozenset)
    language_ids: frozenset[str] = field(default_factory=frozenset)

    def is_member(self, agent_id: EntityID) -> bool:
        return agent_id in self.founding_members

    def total_members(self) -> int:
        return len(self.founding_members) + self.population


# ---------------------------------------------------------------------------
# Cognitive / Decision Types
# ---------------------------------------------------------------------------


class DecisionType(Enum):
    """Types of decisions agents make."""

    # Survival
    SEEK_FOOD = auto()
    SEEK_WATER = auto()
    REST = auto()
    SEEK_SHELTER = auto()
    FLEE = auto()
    FIGHT = auto()

    # Social
    TRADE = auto()
    GIFT = auto()
    BEG = auto()
    RECRUIT = auto()
    JOIN = auto()  # Join organization
    LEAVE = auto()

    # Communication
    SPEAK = auto()
    PERSUADE = auto()
    DECEIVE = auto()
    GOSSIP = auto()
    WRITE = auto()

    # Governance
    PROPOSE = auto()
    VOTE = auto()
    REBEL = auto()
    FORGIVE = auto()
    PUNISH = auto()

    # Cultural
    WORSHIP = auto()
    PRAY = auto()
    TEACH = auto()
    LEARN = auto()
    CREATE_ART = auto()
    SPREAD_CULTURE = auto()

    # Cognitive
    DELIBERATE = auto()  # Deep reasoning
    REFLECT = auto()  # Self-examination
    PLAN = auto()  # Long-term planning

    # Movement
    MOVE_TO = auto()
    MIGRATE = auto()
    EXPLORE = auto()


@dataclass(frozen=True)
class Decision:
    """An agent's decision."""

    decision_id: EntityID
    agent_id: EntityID | None
    tick: int
    decision_type: DecisionType
    target_id: EntityID | None
    target_pos: Pos2D | None
    reasoning: str  # Why this decision was made
    action: str  # What action was taken
    outcome: str  # What happened as a result
    context_summary: str  # Brief summary of the situation


# ---------------------------------------------------------------------------
# Belief & Culture Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Belief:
    """A belief held by an agent or culture."""

    belief_id: EntityID
    category: str  # e.g., "theology", "morality", "nature"
    content: str  # The belief statement
    strength: float  # 0.0-1.0
    source: str  # How this belief was formed
    tick_formed: int
    supporting_memories: tuple[str, ...]
    contradicting_memories: tuple[str, ...]


@dataclass(frozen=True)
class CulturalValue:
    """A cultural value of a society."""

    value_id: EntityID
    name: str
    description: str
    importance: float  # 0.0-1.0
    exceptions: tuple[str, ...]  # When this value can be violated


@dataclass(frozen=True)
class Ritual:
    """A cultural ritual."""

    ritual_id: EntityID
    name: str
    description: str
    frequency: str  # e.g., "annual", "weekly", "lunar"
    participants_min: int
    participants_max: int
    requirements: frozenset[str]  # e.g., "fire", "music", "food"
    meaning: str  # What the ritual represents


@dataclass(frozen=True)
class ArtForm:
    """A form of art or creative expression."""

    art_id: EntityID
    name: str
    medium: str  # e.g., "painting", "music", "story", "sculpture"
    description: str
    cultural_origin: str
    complexity: float  # 0.0-1.0


# ---------------------------------------------------------------------------
# Language Types
# ---------------------------------------------------------------------------


@dataclass()
class Language:
    """A language or dialect."""

    language_id: str
    name: str
    family: str  # Language family
    vocabulary_size: int
    speakers: set[EntityID]
    dialect_of: str | None  # Parent language if dialect
    key_features: tuple[str, ...]
    common_words: dict[str, str]  # word -> meaning
    grammar_rules: tuple[str, ...]
    script_type: str  # e.g., "none", "alphabetic", "logographic"


@dataclass(frozen=True)
class Meme:
    """A cultural meme (idea, phrase, story) that spreads."""

    meme_id: EntityID
    content: str
    origin_agent_id: EntityID | None
    origin_tick: int
    origin_position: Pos2D
    spread_count: int = 0
    mutation_rate: float = 0.1  # How often the meme mutates
    variants: frozenset[str] = field(default_factory=frozenset)  # Mutations

    def mutate(self) -> Meme:
        """Create a mutated version of this meme."""
        import random
        words = self.content.split()
        if len(words) <= 1:
            return self
        idx = random.randint(0, len(words) - 1)
        new_words = words[:]
        new_words[idx] = "____"
        mutated = " ".join(new_words)
        return Meme(
            meme_id=new_entity_id(),
            content=mutated,
            origin_agent_id=self.origin_agent_id,
            origin_tick=self.origin_tick,
            origin_position=self.origin_position,
            spread_count=0,
            mutation_rate=self.mutation_rate,
            variants=frozenset(list(self.variants) + [self.content]),
        )


# ---------------------------------------------------------------------------
# Technology Types
# ---------------------------------------------------------------------------


class TechCategory(Enum):
    """Categories of technology."""

    TOOLS = auto()
    AGRICULTURE = auto()
    ANIMAL_HUSBANDRY = auto()
    METALLURGY = auto()
    ARCHITECTURE = auto()
    MEDICINE = auto()
    NAVIGATION = auto()
    WARFARE = auto()
    WRITING = auto()
    MATHEMATICS = auto()
    ASTRONOMY = auto()
    MAGIC = auto()  # Magical practices


@dataclass(frozen=True)
class Technology:
    """A technology or knowledge."""

    tech_id: EntityID
    name: str
    description: str
    category: TechCategory
    prerequisites: frozenset[EntityID]  # Other techs needed first
    discovery_chance: float  # Base chance per tick
    unlocked_by: frozenset[EntityID]  # Who discovered it
    tick_discovered: int
    applications: tuple[str, ...]  # How this tech can be used


# ---------------------------------------------------------------------------
# Trade / Economy Types
# ---------------------------------------------------------------------------


@dataclass()
class Inventory:
    """An agent's inventory of resources."""

    items: dict[ResourceType, float] = field(default_factory=dict)
    max_capacity: float = 100.0

    def add(self, resource: ResourceType, amount: float) -> float:
        """Add resource, return amount actually added."""
        current = self.items.get(resource, 0.0)
        space = self.max_capacity - current
        added = min(amount, space)
        self.items[resource] = current + added
        return added

    def remove(self, resource: ResourceType, amount: float) -> float:
        """Remove resource, return amount actually removed."""
        current = self.items.get(resource, 0.0)
        removed = min(amount, current)
        self.items[resource] = current - removed
        return removed

    def has(self, resource: ResourceType, amount: float = 0.0) -> bool:
        return self.items.get(resource, 0.0) >= amount

    def total_weight(self) -> float:
        return sum(self.items.values())

    def is_full(self) -> bool:
        return self.total_weight() >= self.max_capacity


@dataclass()
class Market:
    """A local market for trade."""

    market_id: EntityID
    position: Pos2D
    tick: int
    price_index: dict[ResourceType, float]  # Relative to base value
    supply: dict[ResourceType, float]
    demand: dict[ResourceType, float]
    active_trades: list[EntityID] = field(default_factory=list)

    def get_price(self, resource: ResourceType) -> float:
        return resource.base_value * self.price_index.get(resource, 1.0)

    def adjust_price(self, resource: ResourceType, factor: float) -> None:
        current = self.price_index.get(resource, 1.0)
        self.price_index[resource] = max(0.1, min(10.0, current * factor))


@dataclass()
class Relationship:
    """A relationship between two agents."""

    agent_a: EntityID
    agent_b: EntityID
    trust: float = 0.5  # 0.0-1.0
    respect: float = 0.5
    affection: float = 0.5
    history: tuple[str, ...] = field(default_factory=tuple)  # Event summaries
    interactions_count: int = 0
    last_interaction_tick: int = 0

    def record_interaction(self, tick: int, event: str) -> None:
        self.history = self.history + (event,)
        self.interactions_count += 1
        self.last_interaction_tick = tick


@dataclass()
class Transaction:
    """A trade transaction."""

    transaction_id: EntityID
    tick: int
    seller_id: EntityID
    buyer_id: EntityID
    resource: ResourceType
    amount: float
    price_per_unit: float
    location: Pos2D
    successful: bool = True


# ---------------------------------------------------------------------------
# Narrative Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NarrativeArc:
    """A narrative arc (story line) tracked through events."""

    arc_id: EntityID
    name: str
    arc_type: str  # e.g., "tragedy", "hero's journey", "political intrigue"
    participants: frozenset[EntityID]
    events: tuple[Event, ...]
    themes: tuple[str, ...]
    status: str  # "active", "completed", "abandoned"
    significance: float  # 0.0-1.0


@dataclass(frozen=True)
class HistoricalRecord:
    """A historical record or chronicle entry."""

    record_id: EntityID
    tick: int
    title: str
    content: str
    author_id: EntityID | None
    source_agent_ids: frozenset[EntityID]
    verified: bool = False


# ---------------------------------------------------------------------------
# Spatial Partitioning
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Chunk:
    """A spatial chunk for efficient queries."""

    chunk_x: int
    chunk_y: int
    tile_positions: frozenset[Pos2D]
    agent_ids: frozenset[EntityID]
    organization_ids: frozenset[EntityID]
    resource_nodes: frozenset[str]  # IDs
