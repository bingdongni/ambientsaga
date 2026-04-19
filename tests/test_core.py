"""Core tests — tests for the World, Chunk, SignalBus, and TickEngine."""

from __future__ import annotations

import pytest
import numpy as np

from ambientsaga.config import Config
from ambientsaga.types import Pos2D, Signal, SignalType, Event, EventPriority, EntityID
from ambientsaga.world.state import World
from ambientsaga.world.chunk import ChunkManager, Chunk
from ambientsaga.world.signal_bus import SignalBus, SignalSubscription
from ambientsaga.world.tick import TickEngine


class TestChunk:
    """Chunk management tests."""

    def test_chunk_creation(self):
        """Test basic chunk creation."""
        chunk = Chunk(
            chunk_x=0,
            chunk_y=0,
            size=64,
            terrain=np.zeros((64, 64), dtype=np.int32),
            elevation=np.zeros((64, 64), dtype=np.float64),
            temperature=np.zeros((64, 64), dtype=np.float64),
            humidity=np.zeros((64, 64), dtype=np.float64),
            precipitation=np.zeros((64, 64), dtype=np.float64),
            soil_type=np.zeros((64, 64), dtype=np.int32),
            aquifer_storage=np.zeros((64, 64), dtype=np.float64),
            vegetation_cover=np.zeros((64, 64), dtype=np.float64),
        )
        assert chunk.chunk_x == 0
        assert chunk.chunk_y == 0
        assert chunk.size == 64
        assert chunk.terrain.shape == (64, 64)

    def test_chunk_bounding_box(self):
        """Test chunk bounding box calculation."""
        chunk = Chunk(
            chunk_x=1,
            chunk_y=2,
            size=16,
            terrain=np.zeros((16, 16), dtype=np.int32),
            elevation=np.zeros((16, 16), dtype=np.float64),
            temperature=np.zeros((16, 16), dtype=np.float64),
            humidity=np.zeros((16, 16), dtype=np.float64),
            precipitation=np.zeros((16, 16), dtype=np.float64),
            soil_type=np.zeros((16, 16), dtype=np.int32),
            aquifer_storage=np.zeros((16, 16), dtype=np.float64),
            vegetation_cover=np.zeros((16, 16), dtype=np.float64),
        )
        bbox = chunk.bounding_box
        assert bbox == (16, 32, 31, 47)  # (min_x, min_y, max_x, max_y)

    def test_chunk_coordinate_conversion(self):
        """Test coordinate conversion between local and world space."""
        chunk = Chunk(
            chunk_x=2,
            chunk_y=3,
            size=16,
            terrain=np.zeros((16, 16), dtype=np.int32),
            elevation=np.zeros((16, 16), dtype=np.float64),
            temperature=np.zeros((16, 16), dtype=np.float64),
            humidity=np.zeros((16, 16), dtype=np.float64),
            precipitation=np.zeros((16, 16), dtype=np.float64),
            soil_type=np.zeros((16, 16), dtype=np.int32),
            aquifer_storage=np.zeros((16, 16), dtype=np.float64),
            vegetation_cover=np.zeros((16, 16), dtype=np.float64),
        )
        # World to local
        local = chunk.world_to_local(35, 52)
        assert local == (3, 4)  # 35 - 32 = 3, 52 - 48 = 4

        # Local to world
        world = chunk.local_to_world(5, 7)
        assert world == (37, 55)  # 32 + 5 = 37, 48 + 7 = 55


class TestChunkManager:
    """Chunk manager tests."""

    def test_chunk_creation_and_lookup(self):
        """Test chunk creation and lookup."""
        manager = ChunkManager(
            world_width=512,
            world_height=512,
            chunk_size=16,
        )

        # Create chunks
        c00 = manager.get_or_create_chunk(0, 0)
        c10 = manager.get_or_create_chunk(1, 0)
        c01 = manager.get_or_create_chunk(0, 1)

        assert c00.chunk_x == 0
        assert c10.chunk_x == 1
        assert c01.chunk_y == 1
        assert c00 != c10

    def test_chunk_coords(self):
        """Test coordinate conversion."""
        manager = ChunkManager(
            world_width=512,
            world_height=512,
            chunk_size=16,
        )

        # Chunk coords for world positions
        assert manager.get_chunk_coords(0, 0) == (0, 0)
        assert manager.get_chunk_coords(65, 0) == (4, 0)
        assert manager.get_chunk_coords(0, 65) == (0, 4)
        assert manager.get_chunk_coords(65, 65) == (4, 4)

    def test_agent_registration(self):
        """Test agent registration in chunk manager."""
        manager = ChunkManager(
            world_width=512,
            world_height=512,
            chunk_size=16,
        )

        # Register agents
        manager.register_agent("agent_001", 5, 5)
        manager.register_agent("agent_002", 10, 10)

        # Both agents should be in chunk (0,0)
        assert manager.get_chunk_population(0, 0) == 2

        # Unregister agents
        manager.unregister_agent("agent_001")
        manager.unregister_agent("agent_002")
        assert manager.get_chunk_population(0, 0) == 0


class TestSignalBus:
    """Signal bus tests."""

    def test_signal_creation(self):
        """Test signal creation."""
        signal = Signal(
            signal_type=SignalType.DISCOVERY,
            position=Pos2D(100, 100),
            tick=0,
            source_id="test_source",
            intensity=0.8,
            content="Found a new resource",
            metadata=frozenset(),
        )
        assert signal.signal_type == SignalType.DISCOVERY
        assert signal.intensity == 0.8
        assert signal.position == Pos2D(100, 100)

    def test_signal_types(self):
        """Test that all signal types are defined."""
        # Environmental
        assert SignalType.WEATHER_CHANGE is not None
        assert SignalType.NATURAL_DISASTER is not None
        assert SignalType.SEASON_CHANGE is not None

        # Social
        assert SignalType.TRADE_OPPORTUNITY is not None
        assert SignalType.CONFLICT_WARNING is not None
        assert SignalType.DISCOVERY is not None
        assert SignalType.FESTIVAL_ANNOUNCEMENT is not None

        # Personal
        assert SignalType.HUNGER is not None
        assert SignalType.THIRST is not None
        assert SignalType.LONELINESS is not None


class TestTickEngine:
    """Tick engine tests."""

    def test_tick_engine_creation(self):
        """Test tick engine creation."""
        engine = TickEngine(tick_rate=0.0, start_tick=0)
        assert engine.tick == 0

    def test_tick_advancement(self):
        """Test tick advancement."""
        engine = TickEngine(tick_rate=0.0, start_tick=0)

        # Use tick_once for advancement
        engine.tick_once()
        assert engine.tick == 1

        engine.tick_once()
        assert engine.tick == 2

    def test_tick_phases(self):
        """Test tick phases are defined."""
        assert len(TickEngine.TICK_PHASES) > 0
        assert "WORLD_UPDATE" in TickEngine.TICK_PHASES
        assert "AGENT_DECISION" in TickEngine.TICK_PHASES
        assert "METRICS" in TickEngine.TICK_PHASES

    def test_pause_resume(self):
        """Test pause and resume."""
        engine = TickEngine(tick_rate=0.0, start_tick=0)

        engine.pause()
        assert engine.is_paused

        engine.resume()
        assert not engine.is_paused

    def test_seek(self):
        """Test seeking to a specific tick."""
        engine = TickEngine(tick_rate=0.0, start_tick=0)
        engine.seek(100)
        assert engine.tick == 100

    def test_year_calculation(self):
        """Test year and season calculation."""
        engine = TickEngine(tick_rate=0.0, start_tick=0)
        # 1440 ticks = 1 year
        engine.seek(1440)
        assert engine.year == 1
        assert engine.season == "SPRING"


class TestWorld:
    """World system tests."""

    def test_world_creation(self):
        """Test world creation from config."""
        config = Config.from_preset("river_valley")
        world = World(config)
        assert world._config is not None
        assert world.tick_engine is not None

    def test_world_terrain(self):
        """Test terrain access."""
        config = Config.from_preset("river_valley")
        world = World(config)
        # Set valid terrain values
        world._terrain[0, 0] = 6  # GRASSLAND value
        terrain = world.get_terrain(0, 0)
        assert terrain is not None

    def test_world_agent_management(self):
        """Test agent registration."""
        from ambientsaga.agents import Agent
        from ambientsaga.agents.core import AgentTier as CoreAgentTier

        config = Config.from_preset("river_valley")
        world = World(config)

        agent = Agent(
            entity_id="test_agent_001",
            name="Test Agent",
            position=Pos2D(100, 100),
            tier=CoreAgentTier.L3_BACKGROUND,
        )

        world.register_agent(agent)
        assert world.get_agent_count() == 1
        assert world.get_agent("test_agent_001") is agent

    def test_world_properties(self):
        """Test world properties."""
        config = Config.from_preset("river_valley")
        world = World(config)

        assert world.tick_engine is not None
        assert hasattr(world, "protocol")
        assert hasattr(world, "reputation")
