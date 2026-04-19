"""
World engine - terrain generation, climate, resources, and natural events.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

import numpy as np

from ambientsaga.config import WorldConfig
from ambientsaga.types import (
    Biome,
    BiomeType,
    ClimateZone,
    Pos2D,
    ResourceType,
    TerrainType,
    Tick,
)


@dataclass
class TerrainCell:
    """Single terrain cell in the world."""
    x: int
    y: int
    terrain: TerrainType
    biome: Biome
    elevation: float = 0.0
    moisture: float = 0.0
    temperature: float = 0.0
    fertility: float = 0.0
    navigability: float = 1.0  # 0 = impassable, 1 = full speed
    sight_blocking: float = 0.0  # 0 = transparent, 1 = fully opaque
    resource_yield: dict[ResourceType, float] = field(default_factory=dict)


@dataclass
class ClimateState:
    """Current climate state for the world."""
    season: int = 0  # 0=spring, 1=summer, 2=autumn, 3=winter
    season_progress: float = 0.0  # 0.0 to 1.0 within current season
    temperature_modifier: float = 0.0  # global temperature shift
    moisture_modifier: float = 0.0  # global moisture shift
    year: int = 0
    day_of_year: int = 0  # 0-365


@dataclass
class WorldState:
    """Complete state of the world."""
    tick: Tick = 0
    climate: ClimateState = field(default_factory=ClimateState)
    active_disasters: list[str] = field(default_factory=list)
    disaster_history: list[dict] = field(default_factory=list)


class TerrainGenerator:
    """
    Terrain generator - generates terrain, climate, and resources.
    This is the foundation of the natural world layer.
    """

    def __init__(self, config: WorldConfig):
        self.config = config
        self.width = config.width
        self.height = config.height
        self.seed = config.seed

        # World data grids
        self._elevation: np.ndarray = np.zeros((config.height, config.width), dtype=np.float32)
        self._moisture: np.ndarray = np.zeros((config.height, config.width), dtype=np.float32)
        self._temperature: np.ndarray = np.zeros((config.height, config.width), dtype=np.float32)

        # Terrain and biome grids
        self._terrain: np.ndarray = np.zeros((config.height, config.width), dtype=np.int32)
        self._biome: np.ndarray = np.zeros((config.height, config.width), dtype=np.int32)
        self._climate_zone: np.ndarray = np.zeros((config.height, config.width), dtype=np.int32)

        # Resources grid
        self._resources: dict[Pos2D, dict[ResourceType, float]] = {}

        # World state
        self.state = WorldState()

        # Generate the world
        self._generate()

    def _generate(self) -> None:
        """Generate the world terrain and biomes."""
        rng = np.random.default_rng(self.seed)

        # Generate elevation with multiple octaves of noise
        self._elevation = self._generate_noise(rng, self.config.elevation_scale, self.config.elevation_octaves)
        self._moisture = self._generate_noise(rng, self.config.moisture_scale, 4, offset=1000)
        self._temperature = self._generate_temperature(rng)

        # Determine terrain types
        self._terrain = self._classify_terrain()
        self._biome = self._classify_biome()
        self._climate_zone = self._classify_climate_zone()

        # Generate resources
        self._generate_resources(rng)

    def _generate_noise(self, rng: np.random.Generator, scale: float, octaves: int, offset: float = 0) -> np.ndarray:
        """Generate multi-octave noise for terrain features."""
        result = np.zeros((self.height, self.width), dtype=np.float32)

        for octave in range(1, octaves + 1):
            freq = scale * octave
            noise = rng.standard_normal((self.height, self.width))
            # Simple smoothing
            from scipy.ndimage import gaussian_filter
            smoothed = gaussian_filter(noise, sigma=freq / 2)
            result += smoothed / octave

        # Normalize to 0-1
        result = (result - result.min()) / (result.max() - result.min() + 1e-8)
        return result

    def _generate_temperature(self, rng: np.random.Generator) -> np.ndarray:
        """Generate temperature map based on latitude and elevation."""
        lat_factor = np.linspace(1.0, 0.1, self.height).reshape(-1, 1)
        noise = rng.standard_normal((self.height, self.width))
        from scipy.ndimage import gaussian_filter
        noise = gaussian_filter(noise, sigma=5)
        temp = lat_factor * 0.7 + noise * 0.3
        temp -= self._elevation * 0.3  # Higher elevation = colder
        temp = np.clip(temp, 0, 1)
        return temp

    def _classify_terrain(self) -> np.ndarray:
        """Classify terrain types based on elevation and moisture."""
        terrain = np.zeros((self.height, self.width), dtype=np.int32)
        e = self._elevation
        m = self._moisture

        # Deep ocean
        terrain[(e < 0.2) & (m > 0.3)] = TerrainType.DEEP_OCEAN.value
        # Ocean
        terrain[(e < 0.3) & (m > 0.2)] = TerrainType.OCEAN.value
        # Shallow water
        terrain[(e < 0.35) & (m > 0.1)] = TerrainType.SHALLOW_WATER.value
        # Beach
        terrain[(e >= 0.35) & (e < 0.4) & (m > 0.05)] = TerrainType.BEACH.value
        # Desert
        terrain[(e >= 0.4) & (m < 0.15)] = TerrainType.DESERT.value
        terrain[(e >= 0.4) & (m >= 0.15) & (m < 0.25)] = TerrainType.DESERT_SCRUB.value
        # Grassland / Plains
        terrain[(e >= 0.4) & (m >= 0.25) & (m < 0.45)] = TerrainType.GRASSLAND.value
        # Savanna
        terrain[(e >= 0.4) & (m >= 0.45) & (m < 0.6) & (self._temperature > 0.6)] = TerrainType.SAVANNA.value
        # Temperate forest
        terrain[(e >= 0.4) & (m >= 0.55) & (m < 0.7) & (self._temperature > 0.3) & (self._temperature < 0.7)] = TerrainType.TEMPERATE_FOREST.value
        # Boreal forest
        terrain[(e >= 0.4) & (m >= 0.5) & (self._temperature < 0.35)] = TerrainType.BOREAL_FOREST.value
        # Tropical forest
        terrain[(e >= 0.4) & (m >= 0.65) & (self._temperature > 0.7)] = TerrainType.TROPICAL_FOREST.value
        # Rainforest
        terrain[(e >= 0.4) & (m >= 0.8) & (self._temperature > 0.75)] = TerrainType.RAINFOREST.value
        # Marsh/Swamp
        terrain[(e >= 0.35) & (e < 0.5) & (m >= 0.75)] = TerrainType.MARSH.value
        terrain[(e >= 0.5) & (e < 0.6) & (m >= 0.8)] = TerrainType.SWAMP.value
        # Hills
        terrain[(e >= 0.6) & (e < 0.75)] = TerrainType.HILLS.value
        # Mountains
        terrain[(e >= 0.75) & (e < 0.88)] = TerrainType.MOUNTAINS.value
        # High mountains
        terrain[(e >= 0.88)] = TerrainType.HIGH_MOUNTAINS.value
        # Plateau
        terrain[(e >= 0.55) & (e < 0.75) & (m < 0.3)] = TerrainType.PLATEAU.value
        # Cave (special - generated separately)
        terrain[(e < 0.15)] = TerrainType.CAVE.value

        return terrain

    def _classify_biome(self) -> np.ndarray:
        """Classify biomes based on terrain and climate."""
        biome = np.zeros((self.height, self.width), dtype=np.int32)
        t = self._terrain
        temp = self._temperature
        mois = self._moisture

        # Marine biomes
        biome[t == TerrainType.DEEP_OCEAN.value] = BiomeType.DEEP_SEA.value
        biome[t == TerrainType.OCEAN.value] = BiomeType.MARINE.value
        biome[t == TerrainType.SHALLOW_WATER.value] = BiomeType.LITTORAL.value
        biome[t == TerrainType.BEACH.value] = BiomeType.SANDY_SHORE.value

        # Terrestrial biomes
        biome[t == TerrainType.DESERT.value] = BiomeType.DESERT.value
        biome[t == TerrainType.DESERT_SCRUB.value] = BiomeType.XERISCAPE.value
        biome[t == TerrainType.GRASSLAND.value] = BiomeType.GRASSLAND.value
        biome[t == TerrainType.SAVANNA.value] = BiomeType.SAVANNA_BIOME.value
        biome[t == TerrainType.TEMPERATE_FOREST.value] = BiomeType.TEMPERATE_FOREST_BIOME.value
        biome[t == TerrainType.BOREAL_FOREST.value] = BiomeType.TAIGA.value
        biome[t == TerrainType.TROPICAL_FOREST.value] = BiomeType.TROPICAL_FOREST_BIOME.value
        biome[t == TerrainType.RAINFOREST.value] = BiomeType.RAINFOREST_BIOME.value
        biome[t == TerrainType.MARSH.value] = BiomeType.WETLAND.value
        biome[t == TerrainType.SWAMP.value] = BiomeType.SWAMP_BIOME.value
        biome[t == TerrainType.PLATEAU.value] = BiomeType.HIGHPLAIN.value
        biome[t == TerrainType.HILLS.value] = BiomeType.HILLSIDE.value
        biome[t == TerrainType.MOUNTAINS.value] = BiomeType.HIGHLAND.value
        biome[t == TerrainType.HIGH_MOUNTAINS.value] = BiomeType.ALPINE.value
        biome[t == TerrainType.CAVE.value] = BiomeType.UNDERGROUND.value

        return biome

    def _classify_climate_zone(self) -> np.ndarray:
        """Classify climate zones."""
        cz = np.zeros((self.height, self.width), dtype=np.int32)
        temp = self._temperature
        mois = self._moisture

        cz[(temp > 0.75) & (mois > 0.6)] = ClimateZone.TROPICAL.value
        cz[(temp > 0.6) & (temp <= 0.75) & (mois > 0.5)] = ClimateZone.SUBTROPICAL.value
        cz[(temp > 0.45) & (temp <= 0.6) & (mois > 0.4)] = ClimateZone.TEMPERATE.value
        cz[(temp > 0.3) & (temp <= 0.45) & (mois > 0.3)] = ClimateZone.CONTINENTAL.value
        cz[(temp <= 0.3)] = ClimateZone.POLAR.value
        cz[(mois < 0.15)] = ClimateZone.ARID.value
        cz[(temp > 0.7) & (mois < 0.2)] = ClimateZone.TROPICAL_DESERT.value

        return cz

    def _generate_resources(self, rng: np.random.Generator) -> None:
        """Generate initial resource deposits."""
        # Stone - common in hills and mountains
        stone_mask = (self._terrain == TerrainType.HILLS.value) | (self._terrain == TerrainType.MOUNTAINS.value) | (self._terrain == TerrainType.HIGH_MOUNTAINS.value)
        for y in range(self.height):
            for x in range(self.width):
                if stone_mask[y, x] and rng.random() < 0.3:
                    pos = Pos2D(x, y)
                    self._resources[pos] = {ResourceType.STONE: rng.uniform(0.3, 1.0)}

        # Water - rivers and lakes
        water_mask = (self._terrain == TerrainType.OCEAN.value) | (self._terrain == TerrainType.SHALLOW_WATER.value) | (self._terrain == TerrainType.MARSH.value)
        for y in range(self.height):
            for x in range(self.width):
                if water_mask[y, x]:
                    pos = Pos2D(x, y)
                    self._resources[pos] = {ResourceType.WATER: rng.uniform(0.5, 1.0)}

        # Flora - forests and grasslands
        flora_mask = (self._terrain == TerrainType.TEMPERATE_FOREST.value) | (self._terrain == TerrainType.TROPICAL_FOREST.value) | (self._terrain == TerrainType.RAINFOREST.value)
        for y in range(self.height):
            for x in range(self.width):
                if flora_mask[y, x] and rng.random() < 0.4:
                    pos = Pos2D(x, y)
                    self._resources[pos] = {ResourceType.FLORA: rng.uniform(0.4, 1.0)}

        # Minerals - rare, in mountains and caves
        mine_mask = (self._terrain == TerrainType.MOUNTAINS.value) | (self._terrain == TerrainType.HIGH_MOUNTAINS.value) | (self._terrain == TerrainType.CAVE.value)
        for y in range(self.height):
            for x in range(self.width):
                if mine_mask[y, x] and rng.random() < 0.05:
                    pos = Pos2D(x, y)
                    self._resources[pos] = {ResourceType.MINERALS: rng.uniform(0.5, 1.0)}

        # Fertile land - grasslands and savannas
        fertile_mask = (self._terrain == TerrainType.GRASSLAND.value) | (self._terrain == TerrainType.SAVANNA.value)
        for y in range(self.height):
            for x in range(self.width):
                if fertile_mask[y, x] and rng.random() < 0.3:
                    pos = Pos2D(x, y)
                    self._resources[pos] = {ResourceType.FERTILE_SOIL: rng.uniform(0.4, 0.9)}

    async def tick(self, tick: Tick) -> None:
        """Update world state for a single tick."""
        self.state.tick = tick

        # Update seasons (4 ticks per season, ~1 year per 100 ticks if ticks_per_day = 4)
        ticks_per_day = 4  # from config
        ticks_per_year = ticks_per_day * 365
        self.state.climate.year = tick // ticks_per_year
        self.state.climate.day_of_year = (tick // ticks_per_day) % 365
        self.state.climate.season = (self.state.climate.day_of_year // 91) % 4
        self.state.climate.season_progress = (self.state.climate.day_of_year % 91) / 91.0

        # Seasonal temperature modifiers
        season_temp = [0.1, 0.3, -0.1, -0.3][self.state.climate.season]
        self.state.climate.temperature_modifier = season_temp

    def get_terrain_at(self, x: int, y: int) -> TerrainType | None:
        """Get terrain type at coordinates."""
        if not self._in_bounds(x, y):
            return None
        return TerrainType(self._terrain[y, x])

    def get_biome_at(self, x: int, y: int) -> Biome | None:
        """Get biome at coordinates."""
        if not self._in_bounds(x, y):
            return None
        return Biome(self._biome[y, x])

    def get_climate_zone_at(self, x: int, y: int) -> ClimateZone | None:
        """Get climate zone at coordinates."""
        if not self._in_bounds(x, y):
            return None
        return ClimateZone(self._climate_zone[y, x])

    def get_elevation_at(self, x: int, y: int) -> float | None:
        """Get elevation at coordinates."""
        if not self._in_bounds(x, y):
            return None
        return float(self._elevation[y, x])

    def get_temperature_at(self, x: int, y: int) -> float | None:
        """Get temperature at coordinates (with seasonal modifier)."""
        if not self._in_bounds(x, y):
            return None
        base = float(self._temperature[y, x])
        return max(0, min(1, base + self.state.climate.temperature_modifier))

    def get_resources_at(self, x: int, y: int) -> dict[ResourceType, float]:
        """Get resources at coordinates."""
        pos = Pos2D(x, y)
        return self._resources.get(pos, {})

    def get_cell_info(self, x: int, y: int) -> TerrainCell | None:
        """Get complete terrain cell information."""
        if not self._in_bounds(x, y):
            return None
        terrain = TerrainType(self._terrain[y, x])
        biome = Biome(self._biome[y, x])
        return TerrainCell(
            x=x, y=y,
            terrain=terrain,
            biome=biome,
            elevation=float(self._elevation[y, x]),
            moisture=float(self._moisture[y, x]),
            temperature=float(self._temperature[y, x]) + self.state.climate.temperature_modifier,
            navigability=self._get_navigability(terrain),
            sight_blocking=self._get_sight_blocking(terrain),
        )

    def _in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates are within world bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def _get_navigability(self, terrain: TerrainType) -> float:
        """Get navigability for terrain type."""
        navigability_map = {
            TerrainType.DEEP_OCEAN: 0.0,
            TerrainType.OCEAN: 0.0,
            TerrainType.SHALLOW_WATER: 0.3,
            TerrainType.BEACH: 0.8,
            TerrainType.DESERT: 0.9,
            TerrainType.DESERT_SCRUB: 0.8,
            TerrainType.GRASSLAND: 1.0,
            TerrainType.SAVANNA: 1.0,
            TerrainType.TEMPERATE_FOREST: 0.6,
            TerrainType.BOREAL_FOREST: 0.5,
            TerrainType.TROPICAL_FOREST: 0.5,
            TerrainType.RAINFOREST: 0.4,
            TerrainType.MARSH: 0.3,
            TerrainType.SWAMP: 0.3,
            TerrainType.HILLS: 0.5,
            TerrainType.MOUNTAINS: 0.2,
            TerrainType.HIGH_MOUNTAINS: 0.1,
            TerrainType.PLATEAU: 0.7,
            TerrainType.CAVE: 0.4,
        }
        return navigability_map.get(terrain, 0.5)

    def _get_sight_blocking(self, terrain: TerrainType) -> float:
        """Get sight blocking for terrain type."""
        blocking_map = {
            TerrainType.DEEP_OCEAN: 0.0,
            TerrainType.OCEAN: 0.0,
            TerrainType.SHALLOW_WATER: 0.1,
            TerrainType.BEACH: 0.1,
            TerrainType.DESERT: 0.1,
            TerrainType.DESERT_SCRUB: 0.2,
            TerrainType.GRASSLAND: 0.2,
            TerrainType.SAVANNA: 0.3,
            TerrainType.TEMPERATE_FOREST: 0.8,
            TerrainType.BOREAL_FOREST: 0.9,
            TerrainType.TROPICAL_FOREST: 0.9,
            TerrainType.RAINFOREST: 1.0,
            TerrainType.MARSH: 0.6,
            TerrainType.SWAMP: 0.7,
            TerrainType.HILLS: 0.4,
            TerrainType.MOUNTAINS: 0.5,
            TerrainType.HIGH_MOUNTAINS: 0.5,
            TerrainType.PLATEAU: 0.3,
            TerrainType.CAVE: 1.0,
        }
        return blocking_map.get(terrain, 0.3)

    def cells(self) -> Iterator[TerrainCell]:
        """Iterate over all terrain cells."""
        for y in range(self.height):
            for x in range(self.width):
                cell = self.get_cell_info(x, y)
                if cell:
                    yield cell

    def get_terrain_grid(self) -> np.ndarray:
        """Get the terrain grid as numpy array."""
        return self._terrain.copy()

    def get_biome_grid(self) -> np.ndarray:
        """Get the biome grid as numpy array."""
        return self._biome.copy()

    def get_elevation_grid(self) -> np.ndarray:
        """Get the elevation grid as numpy array."""
        return self._elevation.copy()

    def get_temperature_grid(self) -> np.ndarray:
        """Get the temperature grid with seasonal modifier."""
        return self._temperature + self.state.climate.temperature_modifier

    def find_spawn_point(self) -> Pos2D:
        """Find a suitable spawn point for a new agent (grassland or savanna)."""
        rng = np.random.default_rng(self.seed + self.state.tick)
        candidates = []
        for y in range(self.height):
            for x in range(self.width):
                t = TerrainType(self._terrain[y, x])
                if t in (TerrainType.GRASSLAND, TerrainType.SAVANNA, TerrainType.TEMPERATE_FOREST):
                    candidates.append((x, y))
        if candidates:
            return Pos2D(*rng.choice(candidates))
        return Pos2D(self.width // 2, self.height // 2)
