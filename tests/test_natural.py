"""
Tests for natural world systems.
"""

from __future__ import annotations

import pytest
import numpy as np

from ambientsaga.config import TerrainConfig, ClimateConfig, EcologyConfig, DisasterConfig, WorldConfig
from ambientsaga.types import TerrainType
from ambientsaga.natural.terrain import TerrainGenerator
from ambientsaga.natural.climate import ClimateSystem
from ambientsaga.natural.ecology import Ecosystem, Species
from ambientsaga.natural.disaster import DisasterSystem


class TestTerrainGenerator:
    """Terrain generation tests."""

    def test_terrain_config_defaults(self):
        """Test terrain config default values."""
        config = TerrainConfig()
        # Check expected default values
        assert config.sea_level == 0.35
        assert config.mountain_fraction == 0.15
        assert config.forest_fraction == 0.40

    def test_terrain_types(self):
        """Test that terrain types are properly defined."""
        # Check that key terrain types exist
        assert TerrainType.DEEP_OCEAN is not None
        assert TerrainType.OCEAN is not None
        assert TerrainType.BEACH is not None
        assert TerrainType.DESERT is not None
        assert TerrainType.GRASSLAND is not None
        assert TerrainType.SHRUBLAND is not None
        assert TerrainType.TEMPERATE_FOREST is not None
        assert TerrainType.TROPICAL_FOREST is not None
        assert TerrainType.BOREAL_FOREST is not None
        assert TerrainType.MOUNTAINS is not None
        assert TerrainType.HILLS is not None
        assert TerrainType.SAVANNA is not None
        assert TerrainType.TUNDRA is not None
        assert TerrainType.SWAMP is not None
        assert TerrainType.MARSH is not None

    def test_terrain_properties(self):
        """Test terrain type properties."""
        # Water types
        assert TerrainType.DEEP_OCEAN.is_water
        assert TerrainType.OCEAN.is_water
        assert TerrainType.SHALLOW_WATER.is_water

        # Land types
        for t in [TerrainType.GRASSLAND, TerrainType.DESERT, TerrainType.TEMPERATE_FOREST]:
            assert t.is_land

        # Forest types
        for t in [TerrainType.TEMPERATE_FOREST, TerrainType.TROPICAL_FOREST]:
            assert t.is_forest

        # Mountain types
        for t in [TerrainType.MOUNTAINS, TerrainType.HIGH_MOUNTAINS, TerrainType.PLATEAU]:
            assert t.is_mountain

    def test_terrain_generation_size(self):
        """Test terrain generation produces correct dimensions."""
        world_config = WorldConfig(width=128, height=128, seed=42)
        terrain_config = TerrainConfig()
        gen = TerrainGenerator(world_config, terrain_config)
        result = gen.generate()

        assert result["terrain"].shape == (128, 128)
        assert result["elevation"].shape == (128, 128)
        assert result["soil"].shape == (128, 128)

    def test_terrain_generation_values(self):
        """Test terrain generation produces valid values."""
        world_config = WorldConfig(width=64, height=64, seed=123)
        terrain_config = TerrainConfig()
        gen = TerrainGenerator(world_config, terrain_config)
        result = gen.generate()

        terrain = result["terrain"]
        elevation = result["elevation"]
        soil = result["soil"]

        # Elevation should be non-negative (in meters)
        assert elevation.min() >= 0

        # Terrain values should be valid enum values
        unique_terrains = set(terrain.flatten())
        assert len(unique_terrains) > 0

        # Soil should be non-negative integers
        assert soil.min() >= 0


class TestClimateSystem:
    """Climate system tests."""

    def test_climate_system_creation(self):
        """Test climate system initialization."""
        config = ClimateConfig()
        climate = ClimateSystem(config, world_width=256, world_height=256, seed=42)
        assert climate._rng is not None

    def test_climate_initialization(self):
        """Test climate initialization."""
        config = ClimateConfig()
        climate = ClimateSystem(config, world_width=128, world_height=128, seed=42)

        elevation = np.zeros((128, 128), dtype=np.float64)
        elevation[64:, :] = 0.5  # Northern half is elevated

        # Create latitude array
        lat_range = np.linspace(-90, 90, 128)
        latitude = np.tile(lat_range[:, np.newaxis], (1, 128))

        climate.initialize(elevation, latitude)

        assert climate._temperature is not None
        assert climate._humidity is not None


class TestEcosystem:
    """Ecosystem tests."""

    def test_ecosystem_creation(self):
        """Test ecosystem initialization."""
        config = EcologyConfig()
        eco = Ecosystem(config, width=256, height=256, seed=42)
        assert eco.get_species_count() > 0

    def test_species_count(self):
        """Test that ecosystem starts with species."""
        config = EcologyConfig()
        eco = Ecosystem(config, width=128, height=128, seed=42)
        # Should have producers, consumers, decomposers
        assert eco.get_species_count() >= 5

    def test_ecosystem_initialization(self):
        """Test ecosystem population initialization."""
        config = EcologyConfig()
        eco = Ecosystem(config, width=64, height=64, seed=42)

        terrain = np.full((64, 64), TerrainType.GRASSLAND.value, dtype=np.int32)
        vegetation = np.full((64, 64), 0.7, dtype=np.float64)

        eco.initialize(terrain, vegetation)

        # Should have grass population
        grass_pop = eco.get_population("grass", 32, 32)
        assert grass_pop >= 0


class TestDisasterSystem:
    """Natural disaster system tests."""

    def test_disaster_system_creation(self):
        """Test disaster system initialization."""
        config = DisasterConfig()
        disaster = DisasterSystem(config, width=256, height=256, seed=42)
        assert disaster._rng is not None

    def test_disaster_types(self):
        """Test that disaster types are available."""
        config = DisasterConfig()
        disaster = DisasterSystem(config, width=256, height=256, seed=42)

        terrain = np.zeros((256, 256), dtype=np.int32)
        elevation = np.zeros((256, 256), dtype=np.float64)
        disaster.initialize(terrain, elevation)

        # Run for many ticks
        stats = disaster.get_stats()
        assert stats["total_disasters"] == 0

    def test_disaster_stats(self):
        """Test disaster statistics."""
        config = DisasterConfig()
        disaster = DisasterSystem(config, width=128, height=128, seed=42)

        stats = disaster.get_stats()
        assert "total_disasters" in stats
        assert stats["total_disasters"] == 0

    def test_disaster_dimensions(self):
        """Test disaster system dimensions."""
        config = DisasterConfig()
        disaster = DisasterSystem(config, width=256, height=256, seed=42)

        assert disaster.width == 256
        assert disaster.height == 256
