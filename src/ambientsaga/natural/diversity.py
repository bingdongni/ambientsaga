"""
Natural World Diversity System.

Manages diverse natural environments including:
- Biome types and distributions
- Geological features and formations
- Natural disasters and events
- Resource distribution patterns
- Seasonal variations
- Ecological zones
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import numpy as np
from enum import Enum, auto


class BiomeType(Enum):
    """Types of biomes with distinct characteristics."""
    TROPICAL_RAINFOREST = auto()
    TROPICAL_SEASONAL_FOREST = auto()
    TEMPERATE_RAINFOREST = auto()
    TEMPERATE_DECIDUOUS_FOREST = auto()
    TEMPERATE_GRASSLAND = auto()
    BOREAL_FOREST = auto()
    TUNDRA = auto()
    DESERT = auto()
    XERICSHRUB = auto()
    SAVANNA = auto()
    MARSH = auto()
    WETLAND = auto()
    CORAL_REEF = auto()
    KELP_FOREST = auto()
    ALPINE = auto()
    VOLCANIC = auto()
    GLACIAL = auto()
    COASTAL = auto()
    RIVERINE = auto()


class NaturalEventType(Enum):
    """Types of natural events/disasters."""
    EARTHQUAKE = auto()
    VOLCANIC_ERUPTION = auto()
    TSUNAMI = auto()
    FLOOD = auto()
    DROUGHT = auto()
    WILDFIRE = auto()
    HURRICANE = auto()
    BLIZZARD = auto()
    AVALANCHE = auto()
    LANDSLIDE = auto()
    PLAGUE = auto()
    INVASIVE_SPECIES = auto()
    METEOR_IMPACT = auto()
    SOLAR_FLARE = auto()
    SANDSTORM = auto()


class SeasonType(Enum):
    """Season types."""
    SPRING = auto()
    SUMMER = auto()
    AUTUMN = auto()
    WINTER = auto()
    MONSOON = auto()
    DRY_SEASON = auto()


@dataclass
class Biome:
    """A biome with distinct characteristics."""
    biome_type: BiomeType
    name: str
    description: str
    # Climate characteristics
    temperature_range: tuple[float, float]  # (min, max) in Celsius
    precipitation_range: tuple[float, float]  # (min, max) in mm/year
    seasonality: float  # 0 = none, 1 = extreme
    # Ecological characteristics
    primary_productivity: float  # g C/m²/year
    biodiversity: float  # 0-1 scale
    carrying_capacity: float  # agents per km²
    # Resource yields
    available_resources: dict[str, float]  # resource -> base yield
    # Hazards
    natural_hazards: list[NaturalEventType] = field(default_factory=list)
    # Visual
    color: tuple[int, int, int] = (0, 128, 0)


@dataclass
class GeologicalFeature:
    """A unique geological formation."""
    feature_id: str
    name: str
    feature_type: str  # mountain, canyon, cave, hot_spring, etc.
    position: tuple[int, int]
    size: float
    age: int  # years
    formation_mechanism: str
    active: bool = True
    resources: dict[str, float] = field(default_factory=dict)
    effects: dict[str, Any] = field(default_factory=dict)


@dataclass
class NaturalDisaster:
    """A natural disaster event."""
    disaster_id: str
    event_type: NaturalEventType
    position: tuple[int, int]
    intensity: float  # 0-1
    duration: int  # ticks
    tick: int
    affected_area: float  # radius in tiles
    damages: dict[str, float] = field(default_factory=dict)
    ongoing: bool = True


@dataclass
class EcologicalZone:
    """A distinct ecological zone within the world."""
    zone_id: str
    biome: Biome
    boundaries: list[tuple[int, int]]
    species_composition: dict[str, float]  # species_id -> proportion
    succession_stage: float  # 0-10
    stability: float  # 0-1


class NaturalDiversitySystem:
    """
    Manages natural world diversity including biomes, geological features,
    natural disasters, and ecological zones.

    This system creates emergent natural diversity through:
    - Biome distribution based on latitude and climate
    - Unique geological formations
    - Dynamic natural disaster system
    - Seasonal variations
    - Ecological succession
    """

    # Biome definitions with characteristics
    BIOMES: dict[BiomeType, Biome] = {
        BiomeType.TROPICAL_RAINFOREST: Biome(
            biome_type=BiomeType.TROPICAL_RAINFOREST,
            name="Tropical Rainforest",
            description="Dense, humid forests near the equator with high biodiversity",
            temperature_range=(20, 35),
            precipitation_range=(2000, 10000),
            seasonality=0.1,
            primary_productivity=2000,
            biodiversity=0.95,
            carrying_capacity=100,
            available_resources={"food": 1.0, "wood": 1.0, "herbs": 1.0, "spices": 0.8},
            natural_hazards=[NaturalEventType.FLOOD, NaturalEventType.LANDSLIDE],
            color=(0, 100, 0),
        ),
        BiomeType.TROPICAL_SEASONAL_FOREST: Biome(
            biome_type=BiomeType.TROPICAL_SEASONAL_FOREST,
            name="Tropical Seasonal Forest",
            description="Forests with distinct wet and dry seasons",
            temperature_range=(15, 35),
            precipitation_range=(1000, 2000),
            seasonality=0.5,
            primary_productivity=1500,
            biodiversity=0.8,
            carrying_capacity=80,
            available_resources={"food": 0.8, "wood": 1.0, "fibers": 0.7},
            natural_hazards=[NaturalEventType.DROUGHT, NaturalEventType.WILDFIRE],
            color=(50, 120, 50),
        ),
        BiomeType.TEMPERATE_DECIDUOUS_FOREST: Biome(
            biome_type=BiomeType.TEMPERATE_DECIDUOUS_FOREST,
            name="Temperate Deciduous Forest",
            description="Forests with four distinct seasons and leaf-shedding trees",
            temperature_range=(-10, 30),
            precipitation_range=(500, 1500),
            seasonality=0.8,
            primary_productivity=1200,
            biodiversity=0.7,
            carrying_capacity=60,
            available_resources={"food": 0.8, "wood": 1.0, "game": 0.6, "medicinals": 0.5},
            natural_hazards=[NaturalEventType.WILDFIRE, NaturalEventType.BLIZZARD],
            color=(34, 139, 34),
        ),
        BiomeType.TEMPERATE_GRASSLAND: Biome(
            biome_type=BiomeType.TEMPERATE_GRASSLAND,
            name="Temperate Grassland",
            description="Vast plains with rich soils for agriculture",
            temperature_range=(-20, 35),
            precipitation_range=(250, 750),
            seasonality=0.7,
            primary_productivity=800,
            biodiversity=0.4,
            carrying_capacity=40,
            available_resources={"food": 0.6, "grain": 1.0, "herd_animals": 0.8},
            natural_hazards=[NaturalEventType.DROUGHT, NaturalEventType.HURRICANE],
            color=(154, 205, 50),
        ),
        BiomeType.BOREAL_FOREST: Biome(
            biome_type=BiomeType.BOREAL_FOREST,
            name="Boreal Forest (Taiga)",
            description="Coniferous forests in cold northern regions",
            temperature_range=(-40, 20),
            precipitation_range=(300, 900),
            seasonality=0.9,
            primary_productivity=400,
            biodiversity=0.3,
            carrying_capacity=20,
            available_resources={"wood": 1.0, "fur_bearers": 0.8, "game": 0.5},
            natural_hazards=[NaturalEventType.BLIZZARD, NaturalEventType.AVALANCHE],
            color=(0, 100, 0),
        ),
        BiomeType.TUNDRA: Biome(
            biome_type=BiomeType.TUNDRA,
            name="Tundra",
            description="Cold, treeless regions with permafrost",
            temperature_range=(-50, 10),
            precipitation_range=(100, 300),
            seasonality=1.0,
            primary_productivity=100,
            biodiversity=0.1,
            carrying_capacity=5,
            available_resources={"game": 0.3, "ice": 0.5, "minerals": 0.4},
            natural_hazards=[NaturalEventType.BLIZZARD],
            color=(200, 200, 200),
        ),
        BiomeType.DESERT: Biome(
            biome_type=BiomeType.DESERT,
            name="Desert",
            description="Arid regions with extreme temperature variations",
            temperature_range=(0, 50),
            precipitation_range=(0, 250),
            seasonality=0.3,
            primary_productivity=50,
            biodiversity=0.1,
            carrying_capacity=5,
            available_resources={"minerals": 0.8, "spices": 0.3, "rare_metals": 0.5},
            natural_hazards=[NaturalEventType.DROUGHT, NaturalEventType.SANDSTORM],
            color=(237, 201, 175),
        ),
        BiomeType.SAVANNA: Biome(
            biome_type=BiomeType.SAVANNA,
            name="Savanna",
            description="Grasslands with scattered trees",
            temperature_range=(15, 40),
            precipitation_range=(500, 1200),
            seasonality=0.6,
            primary_productivity=700,
            biodiversity=0.5,
            carrying_capacity=30,
            available_resources={"food": 0.5, "game": 0.7, "herd_animals": 0.9},
            natural_hazards=[NaturalEventType.DROUGHT, NaturalEventType.WILDFIRE],
            color=(180, 160, 100),
        ),
        BiomeType.WETLAND: Biome(
            biome_type=BiomeType.WETLAND,
            name="Wetland",
            description="Water-saturated regions including marshes and swamps",
            temperature_range=(-10, 35),
            precipitation_range=(500, 2000),
            seasonality=0.5,
            primary_productivity=1500,
            biodiversity=0.8,
            carrying_capacity=50,
            available_resources={"food": 0.9, "fish": 1.0, "reeds": 1.0, "medicinals": 0.7},
            natural_hazards=[NaturalEventType.FLOOD, NaturalEventType.PLAGUE],
            color=(0, 128, 128),
        ),
        BiomeType.COASTAL: Biome(
            biome_type=BiomeType.COASTAL,
            name="Coastal",
            description="Shoreline regions with marine influence",
            temperature_range=(5, 30),
            precipitation_range=(500, 2000),
            seasonality=0.5,
            primary_productivity=800,
            biodiversity=0.7,
            carrying_capacity=40,
            available_resources={"fish": 1.0, "salt": 1.0, "shellfish": 1.0, "seaweed": 0.8},
            natural_hazards=[NaturalEventType.TSUNAMI, NaturalEventType.HURRICANE],
            color=(135, 206, 235),
        ),
        BiomeType.RIVERINE: Biome(
            biome_type=BiomeType.RIVERINE,
            name="Riverine",
            description="River and stream corridors",
            temperature_range=(-5, 30),
            precipitation_range=(200, 2000),
            seasonality=0.6,
            primary_productivity=1000,
            biodiversity=0.6,
            carrying_capacity=60,
            available_resources={"fish": 1.0, "freshwater": 1.0, "transport": 0.9},
            natural_hazards=[NaturalEventType.FLOOD],
            color=(30, 144, 255),
        ),
        BiomeType.VOLCANIC: Biome(
            biome_type=BiomeType.VOLCANIC,
            name="Volcanic",
            description="Regions with volcanic activity",
            temperature_range=(-10, 50),
            precipitation_range=(500, 3000),
            seasonality=0.4,
            primary_productivity=200,
            biodiversity=0.2,
            carrying_capacity=10,
            available_resources={"minerals": 1.0, "rare_metals": 1.0, "volcanic_ash": 1.0},
            natural_hazards=[NaturalEventType.VOLCANIC_ERUPTION, NaturalEventType.EARTHQUAKE],
            color=(139, 90, 43),
        ),
        BiomeType.ALPINE: Biome(
            biome_type=BiomeType.ALPINE,
            name="Alpine",
            description="High-elevation mountainous regions above tree line",
            temperature_range=(-30, 20),
            precipitation_range=(300, 1500),
            seasonality=1.0,
            primary_productivity=150,
            biodiversity=0.2,
            carrying_capacity=8,
            available_resources={"minerals": 0.7, "ice": 0.6},
            natural_hazards=[NaturalEventType.AVALANCHE, NaturalEventType.LANDSLIDE],
            color=(180, 180, 200),
        ),
    }

    # Disaster probability weights by biome
    DISASTER_WEIGHTS: dict[BiomeType, dict[NaturalEventType, float]] = {
        BiomeType.TROPICAL_RAINFOREST: {NaturalEventType.FLOOD: 0.3, NaturalEventType.LANDSLIDE: 0.2},
        BiomeType.TROPICAL_SEASONAL_FOREST: {NaturalEventType.DROUGHT: 0.3, NaturalEventType.WILDFIRE: 0.2},
        BiomeType.TEMPERATE_DECIDUOUS_FOREST: {NaturalEventType.WILDFIRE: 0.1, NaturalEventType.BLIZZARD: 0.2},
        BiomeType.TEMPERATE_GRASSLAND: {NaturalEventType.DROUGHT: 0.4, NaturalEventType.HURRICANE: 0.1},
        BiomeType.BOREAL_FOREST: {NaturalEventType.BLIZZARD: 0.3, NaturalEventType.AVALANCHE: 0.2},
        BiomeType.TUNDRA: {NaturalEventType.BLIZZARD: 0.4},
        BiomeType.DESERT: {NaturalEventType.DROUGHT: 0.5, NaturalEventType.SANDSTORM: 0.3},
        BiomeType.SAVANNA: {NaturalEventType.DROUGHT: 0.3, NaturalEventType.WILDFIRE: 0.3},
        BiomeType.WETLAND: {NaturalEventType.FLOOD: 0.4, NaturalEventType.PLAGUE: 0.2},
        BiomeType.COASTAL: {NaturalEventType.TSUNAMI: 0.1, NaturalEventType.HURRICANE: 0.3},
        BiomeType.RIVERINE: {NaturalEventType.FLOOD: 0.5},
        BiomeType.VOLCANIC: {NaturalEventType.VOLCANIC_ERUPTION: 0.2, NaturalEventType.EARTHQUAKE: 0.3},
        BiomeType.ALPINE: {NaturalEventType.AVALANCHE: 0.4, NaturalEventType.LANDSLIDE: 0.2},
    }

    def __init__(self, width: int, height: int, seed: int = 42):
        self.width = width
        self.height = height
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Biome map
        self._biome_map: np.ndarray | None = None

        # Geological features
        self._geological_features: list[GeologicalFeature] = []
        self._next_feature_id = 0

        # Natural disasters
        self._active_disasters: list[NaturalDisaster] = []
        self._disaster_history: list[NaturalDisaster] = []
        self._next_disaster_id = 0

        # Seasonal state
        self._season: SeasonType = SeasonType.SPRING
        self._season_progress: float = 0.0
        self._tick = 0

        # Ecological zones
        self._ecological_zones: list[EcologicalZone] = []

        # Statistics
        self._biome_statistics: dict[BiomeType, dict[str, float]] = {}

    def generate_biome_map(
        self,
        latitude_map: np.ndarray,
        temperature_map: np.ndarray,
        precipitation_map: np.ndarray,
    ) -> np.ndarray:
        """
        Generate a biome map based on climate variables.

        Args:
            latitude_map: Normalized latitude (0-1)
            temperature_map: Temperature in Celsius
            precipitation_map: Precipitation in mm/year

        Returns:
            Array of BiomeType values
        """
        biome_map = np.zeros_like(latitude_map, dtype=object)
        rows, cols = latitude_map.shape

        for i in range(rows):
            for j in range(cols):
                lat = latitude_map[i, j]
                temp = temperature_map[i, j]
                precip = precipitation_map[i, j]

                biome = self._determine_biome(lat, temp, precip)
                biome_map[i, j] = biome

        self._biome_map = biome_map
        self._calculate_biome_statistics()
        return biome_map

    def _determine_biome(
        self, latitude: float, temperature: float, precipitation: float
    ) -> BiomeType:
        """Determine biome type based on climate variables."""
        abs_lat = abs(latitude - 0.5)  # Distance from equator

        # Very hot and wet -> tropical rainforest
        if temperature > 20 and precipitation > 2000:
            return BiomeType.TROPICAL_RAINFOREST

        # Hot and seasonal -> tropical seasonal or savanna
        if temperature > 20:
            if precipitation > 1000:
                return BiomeType.TROPICAL_SEASONAL_FOREST
            return BiomeType.SAVANNA

        # Cold and dry -> tundra or desert
        if temperature < 5:
            if precipitation < 250:
                return BiomeType.DESERT
            if abs_lat > 0.3:  # Far from equator
                return BiomeType.TUNDRA
            return BiomeType.ALPINE

        # Moderate temperatures
        if precipitation < 300:
            return BiomeType.DESERT

        if precipitation > 1500:
            return BiomeType.TEMPERATE_RAINFOREST

        if 750 < precipitation < 1200:
            if temperature > 15:
                return BiomeType.TEMPERATE_GRASSLAND
            return BiomeType.TEMPERATE_DECIDUOUS_FOREST

        # Check for boreal
        if abs_lat > 0.35 and temperature < 10:
            return BiomeType.BOREAL_FOREST

        return BiomeType.TEMPERATE_DECIDUOUS_FOREST

    def _calculate_biome_statistics(self) -> None:
        """Calculate statistics for each biome in the map."""
        if self._biome_map is None:
            return

        biome_counts: dict[BiomeType, int] = {}
        total = 0

        for biome in self._biome_map.flat:
            if biome in biome_counts:
                biome_counts[biome] += 1
            else:
                biome_counts[biome] = 1
            total += 1

        self._biome_statistics = {}
        for biome, count in biome_counts.items():
            self._biome_statistics[biome] = {
                "count": count,
                "percentage": count / total,
            }

    def add_geological_feature(
        self,
        feature_type: str,
        position: tuple[int, int],
        size: float,
        formation_mechanism: str,
    ) -> GeologicalFeature:
        """Add a unique geological feature."""
        feature = GeologicalFeature(
            feature_id=f"geo_{self._next_feature_id}",
            name=self._generate_feature_name(feature_type),
            feature_type=feature_type,
            position=position,
            size=size,
            age=self._rng.integers(0, 10000000),
            formation_mechanism=formation_mechanism,
            active=True,
            resources=self._generate_feature_resources(feature_type),
            effects=self._generate_feature_effects(feature_type),
        )
        self._geological_features.append(feature)
        self._next_feature_id += 1
        return feature

    def _generate_feature_name(self, feature_type: str) -> str:
        """Generate a name for a geological feature."""
        prefixes = {
            "mountain": ["Great", "Iron", "Storm", "Crystal", "Shadow", "Ancient", "Sacred"],
            "canyon": ["Grand", "Deep", "Shadow", "Crystal", "Hidden"],
            "volcano": ["Mount", "Mount", "The", "Ancient", "Black"],
            "cave": ["Dark", "Crystal", "Echoing", "Hidden", "Ancient"],
            "hot_spring": ["Healing", "Hot", "Sacred", "Steaming", "Misty"],
            "river": ["Silver", "Swift", "Ancient", "Winding", "Mighty"],
            "lake": ["Crystal", "Mirror", "Hidden", "Eternal", "Enchanted"],
            "waterfall": ["Thunder", "Silver", "Hidden", "Falling", "Shimmering"],
        }

        suffixes = {
            "mountain": ["Peak", "Mountain", "Range", "Summit", "Mount"],
            "canyon": ["Canyon", "Gorge", "Ravine", "Valley", "Pass"],
            "volcano": ["Volcano", "Cone", "Peak", "Mountain", "Cone"],
            "cave": ["Cave", "Cavern", " Grotto", "Chamber", "Depths"],
            "hot_spring": ["Springs", "Pool", "Waters", "Bath", "Spring"],
            "river": ["River", "Stream", "Brook", "Creek", "Run"],
            "lake": ["Lake", "Pool", "Waters", "Lagoon", "Pond"],
            "waterfall": ["Falls", "Cascade", "Drop", "Veil", "Plunge"],
        }

        p = prefixes.get(feature_type, ["Ancient"])
        s = suffixes.get(feature_type, ["Place"])

        prefix = self._rng.choice(p)
        suffix = self._rng.choice(s)

        if prefix.startswith("The"):
            return f"The {suffix}"

        return f"{prefix} {suffix}"

    def _generate_feature_resources(self, feature_type: str) -> dict[str, float]:
        """Generate resources associated with a geological feature."""
        resources: dict[str, float] = {}

        if feature_type == "mountain":
            resources = {"stone": 1.0, "minerals": 0.8, "rare_metals": 0.5, "fresh_water": 0.3}
        elif feature_type == "volcano":
            resources = {"sulfur": 1.0, "rare_metals": 0.8, "volcanic_ash": 1.0, "geothermal": 1.0}
        elif feature_type == "cave":
            resources = {"minerals": 0.8, "crystals": 0.6, "guano": 0.5}
        elif feature_type == "hot_spring":
            resources = {"thermal_energy": 1.0, "medicinals": 0.7, "minerals": 0.5}
        elif feature_type == "river":
            resources = {"fish": 1.0, "fresh_water": 1.0, "transport": 0.8, "silt": 0.6}
        elif feature_type == "lake":
            resources = {"fish": 0.9, "fresh_water": 1.0, "reed": 0.5}
        elif feature_type == "waterfall":
            resources = {"fresh_water": 1.0, "hydro_power": 0.8, "fish": 0.5}

        return resources

    def _generate_feature_effects(self, feature_type: str) -> dict[str, Any]:
        """Generate effects of a geological feature."""
        effects: dict[str, Any] = {}

        if feature_type == "mountain":
            effects = {"blocks_wind": True, "creates_rain_shadow": True, "defensive_bonus": 0.3}
        elif feature_type == "volcano":
            effects = {"active": False, "fertilizes_soil": True, "danger_zone": 0.2}
        elif feature_type == "hot_spring":
            effects = {"healing_zone": True, "attracts_animals": True, "attracts_agents": True}
        elif feature_type == "river":
            effects = {"trade_route": True, "irrigation_source": True, "food_source": True}
        elif feature_type == "lake":
            effects = {"fresh_water_source": True, "fishing_zone": True, "transport_hub": True}

        return effects

    def process_natural_disaster(
        self,
        disaster_type: NaturalEventType,
        position: tuple[int, int],
        intensity: float,
        tick: int,
    ) -> NaturalDisaster:
        """Process a natural disaster event."""
        # Calculate duration based on type and intensity
        durations = {
            NaturalEventType.EARTHQUAKE: (1, 5),
            NaturalEventType.VOLCANIC_ERUPTION: (10, 30),
            NaturalEventType.TSUNAMI: (2, 8),
            NaturalEventType.FLOOD: (5, 20),
            NaturalEventType.DROUGHT: (50, 200),
            NaturalEventType.WILDFIRE: (5, 30),
            NaturalEventType.HURRICANE: (10, 30),
            NaturalEventType.BLIZZARD: (3, 15),
            NaturalEventType.AVALANCHE: (1, 5),
            NaturalEventType.LANDSLIDE: (1, 5),
            NaturalEventType.PLAGUE: (20, 100),
        }

        duration_range = durations.get(disaster_type, (5, 20))
        duration = self._rng.integers(duration_range[0], duration_range[1])

        # Calculate affected area
        affected_areas = {
            NaturalEventType.EARTHQUAKE: intensity * 50,
            NaturalEventType.VOLCANIC_ERUPTION: intensity * 100,
            NaturalEventType.TSUNAMI: intensity * 80,
            NaturalEventType.FLOOD: intensity * 60,
            NaturalEventType.DROUGHT: intensity * 200,
            NaturalEventType.WILDFIRE: intensity * 40,
            NaturalEventType.HURRICANE: intensity * 150,
            NaturalEventType.BLIZZARD: intensity * 80,
            NaturalEventType.AVALANCHE: intensity * 30,
            NaturalEventType.LANDSLIDE: intensity * 25,
            NaturalEventType.PLAGUE: intensity * 100,
        }

        affected_area = affected_areas.get(disaster_type, 50)

        disaster = NaturalDisaster(
            disaster_id=f"disaster_{self._next_disaster_id}",
            event_type=disaster_type,
            position=position,
            intensity=intensity,
            duration=duration,
            tick=tick,
            affected_area=affected_area,
            damages=self._calculate_disaster_damages(disaster_type, intensity),
            ongoing=True,
        )

        self._active_disasters.append(disaster)
        self._disaster_history.append(disaster)
        self._next_disaster_id += 1

        return disaster

    def _calculate_disaster_damages(
        self, disaster_type: NaturalEventType, intensity: float
    ) -> dict[str, float]:
        """Calculate damages from a disaster."""
        damages: dict[str, float] = {}

        base_damages = {
            NaturalEventType.EARTHQUAKE: {"buildings": 0.8, "population": 0.3, "terrain": 0.2},
            NaturalEventType.VOLCANIC_ERUPTION: {"population": 0.5, "terrain": 0.8, "air_quality": 0.9},
            NaturalEventType.TSUNAMI: {"buildings": 0.9, "population": 0.5, "coastal": 0.9},
            NaturalEventType.FLOOD: {"buildings": 0.7, "crops": 0.8, "population": 0.3},
            NaturalEventType.DROUGHT: {"crops": 0.9, "population": 0.4, "wildlife": 0.6},
            NaturalEventType.WILDFIRE: {"wildlife": 0.7, "forests": 0.8, "air_quality": 0.6},
            NaturalEventType.HURRICANE: {"buildings": 0.8, "crops": 0.6, "coastal": 0.9},
            NaturalEventType.BLIZZARD: {"population": 0.3, "wildlife": 0.4, "crops": 0.3},
            NaturalEventType.AVALANCHE: {"population": 0.4, "wildlife": 0.3},
            NaturalEventType.LANDSLIDE: {"terrain": 0.7, "buildings": 0.5, "population": 0.3},
            NaturalEventType.PLAGUE: {"population": 0.6, "wildlife": 0.5},
        }

        base = base_damages.get(disaster_type, {"population": 0.3})

        for damage_type, base_value in base.items():
            damages[damage_type] = base_value * intensity

        return damages

    def update_season(self, tick: int) -> SeasonType:
        """Update season based on tick."""
        self._tick = tick

        # Season cycle: 1000 ticks = 1 year
        year_progress = (tick % 1000) / 1000.0

        if year_progress < 0.25:
            self._season = SeasonType.SPRING
        elif year_progress < 0.5:
            self._season = SeasonType.SUMMER
        elif year_progress < 0.75:
            self._season = SeasonType.AUTUMN
        else:
            self._season = SeasonType.WINTER

        self._season_progress = year_progress * 4.0 % 1.0

        return self._season

    def get_biome_at(self, x: int, y: int) -> BiomeType | None:
        """Get biome type at a position."""
        if self._biome_map is None:
            return None

        if 0 <= x < self._biome_map.shape[1] and 0 <= y < self._biome_map.shape[0]:
            return self._biome_map[y, x]

        return None

    def get_biome_info(self, biome_type: BiomeType) -> Biome | None:
        """Get detailed information about a biome type."""
        return self.BIOMES.get(biome_type)

    def get_features_in_radius(
        self, x: int, y: int, radius: float
    ) -> list[GeologicalFeature]:
        """Get geological features within a radius."""
        features = []
        for feature in self._geological_features:
            fx, fy = feature.position
            distance = ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5
            if distance <= radius:
                features.append(feature)
        return features

    def get_active_disasters(self) -> list[NaturalDisaster]:
        """Get currently active disasters."""
        return [d for d in self._active_disasters if d.ongoing]

    def get_disasters_in_radius(
        self, x: int, y: int, radius: float
    ) -> list[NaturalDisaster]:
        """Get active disasters affecting a position."""
        disasters = []
        for disaster in self._active_disasters:
            if not disaster.ongoing:
                continue
            dx, dy = disaster.position
            distance = ((x - dx) ** 2 + (y - dy) ** 2) ** 0.5
            if distance <= radius + disaster.affected_area:
                disasters.append(disaster)
        return disasters

    def update(self, tick: int) -> None:
        """Update natural diversity system."""
        # Update seasons
        self.update_season(tick)

        # Update active disasters
        for disaster in self._active_disasters:
            if disaster.ongoing:
                elapsed = tick - disaster.tick
                if elapsed >= disaster.duration:
                    disaster.ongoing = False

        # Remove expired disasters
        self._active_disasters = [d for d in self._active_disasters if d.ongoing]

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the natural diversity system."""
        return {
            "biome_statistics": {
                biome.value: stats for biome, stats in self._biome_statistics.items()
            },
            "geological_features": {
                "total": len(self._geological_features),
                "by_type": self._count_features_by_type(),
            },
            "disasters": {
                "active": len(self.get_active_disasters()),
                "historical": len(self._disaster_history),
            },
            "season": {
                "current": self._season.name,
                "progress": self._season_progress,
            },
        }

    def _count_features_by_type(self) -> dict[str, int]:
        """Count geological features by type."""
        counts: dict[str, int] = {}
        for feature in self._geological_features:
            if feature.feature_type in counts:
                counts[feature.feature_type] += 1
            else:
                counts[feature.feature_type] = 1
        return counts
