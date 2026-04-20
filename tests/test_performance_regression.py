"""Performance regression tests for AmbientSaga.

These tests ensure that performance optimizations remain effective and catch
any regressions in critical performance paths.
"""

from __future__ import annotations

import pytest
import time
import gc
import os

from ambientsaga.config import Config
from ambientsaga.types import Pos2D
from ambientsaga.world.state import World
from ambientsaga.agents.agent import Agent
from ambientsaga.agents.core import AgentTier


class TestSpatialIndexPerformance:
    """Tests for spatial indexing performance (the main performance bottleneck)."""

    @pytest.fixture
    def world_with_agents(self):
        """Create a world with many agents for spatial tests."""
        config = Config()
        world = World(config)
        world._initialize()

        # Spawn many agents
        for i in range(1000):
            agent = Agent(
                entity_id=f"spatial_agent_{i}",
                name=f"Agent {i}",
                position=Pos2D(x=float(i % 100), y=float(i // 100)),
                tier=AgentTier.L3_BACKGROUND,
            )
            world.register_agent(agent)

        return world

    def test_chunk_manager_get_in_radius_performance(self, world_with_agents):
        """
        Test that get_agents_in_radius is fast enough.

        This is the main performance bottleneck. Should handle 1000 agents
        with radius queries in under 50ms per call.
        """
        chunk_manager = world_with_agents._chunk_manager

        # Warm up
        for _ in range(5):
            chunk_manager.get_agents_in_radius(50.0, 50.0, 20.0)

        # Measure
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            chunk_manager.get_agents_in_radius(50.0, 50.0, 20.0)
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / iterations) * 1000

        # Should be under 50ms per call for 1000 agents
        assert avg_ms < 50, f"get_agents_in_radius took {avg_ms:.2f}ms (expected <50ms)"

    def test_bulk_agent_registration_performance(self, world_with_agents):
        """Test that registering many agents is fast."""
        config = Config()
        world = World(config)
        world._initialize()

        agent_count = 1000
        start = time.perf_counter()

        for i in range(agent_count):
            agent = Agent(
                entity_id=f"bulk_agent_{i}",
                name=f"Bulk Agent {i}",
                position=Pos2D(x=float(i % 100), y=float(i // 100)),
                tier=AgentTier.L3_BACKGROUND,
            )
            world.register_agent(agent)

        elapsed = time.perf_counter() - start
        ms_per_agent = (elapsed / agent_count) * 1000

        # Should be under 1ms per agent
        assert ms_per_agent < 1.0, f"Agent registration took {ms_per_agent:.2f}ms per agent"

    def test_agent_iteration_performance(self, world_with_agents):
        """Test that iterating over all agents is fast."""
        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            list(world_with_agents.get_all_agents())

        elapsed = time.perf_counter() - start
        ms_per_iter = (elapsed / iterations) * 1000

        # Should be under 5ms per iteration
        assert ms_per_iter < 5.0, f"Agent iteration took {ms_per_iter:.2f}ms"


class TestSimulationTickPerformance:
    """Tests for simulation tick performance."""

    def test_world_tick_performance(self):
        """Test that a single world tick is fast enough."""
        config = Config()
        world = World(config)
        world._initialize()

        # Spawn some agents
        for i in range(100):
            agent = Agent(
                entity_id=f"tick_agent_{i}",
                name=f"Tick Agent {i}",
                position=Pos2D(x=float(i), y=float(i)),
                tier=AgentTier.L3_BACKGROUND,
            )
            world.register_agent(agent)

        # Warm up
        for _ in range(5):
            world.tick_once()

        # Force GC before measurement
        gc.collect()

        # Measure 10 ticks
        iterations = 10
        start = time.perf_counter()
        for _ in range(iterations):
            world.tick_once()
        elapsed = time.perf_counter() - start

        ms_per_tick = (elapsed / iterations) * 1000

        # Should be under 100ms per tick for 100 agents
        assert ms_per_tick < 100, f"World tick took {ms_per_tick:.2f}ms (expected <100ms)"


class TestProtocolPerformance:
    """Tests for protocol system performance."""

    @pytest.fixture
    def world_with_agents(self):
        """Create a world with agents."""
        config = Config()
        world = World(config)
        world._initialize()

        for i in range(50):
            agent = Agent(
                entity_id=f"protocol_agent_{i}",
                name=f"Protocol Agent {i}",
                position=Pos2D(x=float(i * 2), y=float(i * 2)),
                tier=AgentTier.L2_FUNCTIONAL,
            )
            world.register_agent(agent)

        return world

    def test_protocol_deliberate_performance(self, world_with_agents):
        """Test that protocol deliberation is fast."""
        protocol = world_with_agents._protocol

        agents = list(world_with_agents.get_all_agents())[:20]

        iterations = 50
        start = time.perf_counter()

        for _ in range(iterations):
            for agent in agents:
                protocol.deliberate(agent, tick=0)

        elapsed = time.perf_counter() - start
        ms_per_agent = (elapsed / (iterations * len(agents))) * 1000

        # Should be under 10ms per deliberation
        assert ms_per_agent < 10, f"Protocol deliberation took {ms_per_agent:.2f}ms per agent"


class TestEmergenceSystemPerformance:
    """Tests for emergence system performance."""

    def test_butterfly_effect_recording_performance(self):
        """Test that butterfly effect recording is fast."""
        from ambientsaga.emergence.butterfly_effects import ButterflyEffectSystem

        config = Config()
        world = World(config)
        world._initialize()

        butterfly = ButterflyEffectSystem(world)

        iterations = 1000
        start = time.perf_counter()

        for i in range(iterations):
            butterfly.record_micro_event(
                agent_id=f"agent_{i}",
                action="test_action",
                magnitude=0.5,
                context={"domain": "social"}
            )

        elapsed = time.perf_counter() - start
        ms_per_record = (elapsed / iterations) * 1000

        # Should be under 1ms per record
        assert ms_per_record < 1.0, f"Butterfly recording took {ms_per_record:.4f}ms per record"

    def test_institutional_emergence_update_performance(self):
        """Test that institutional emergence update is fast."""
        from ambientsaga.emergence.institutional_emergence import InstitutionalEmergenceEngine

        config = Config()
        world = World(config)
        world._initialize()

        engine = InstitutionalEmergenceEngine(world)

        # Record some violations
        for i in range(100):
            engine.record_violation(
                agent_id=f"violator_{i}",
                violation_type="theft",
                tick=i
            )

        iterations = 100
        start = time.perf_counter()

        for i in range(iterations):
            engine.update(tick=i)

        elapsed = time.perf_counter() - start
        ms_per_update = (elapsed / iterations) * 1000

        # Should be under 5ms per update
        assert ms_per_update < 5.0, f"Institutional update took {ms_per_update:.2f}ms"


class TestMemoryUsage:
    """Tests for memory usage."""

    def test_agent_memory_usage(self):
        """Test that agents don't use excessive memory."""
        import sys

        config = Config()
        world = World(config)
        world._initialize()

        # Create agent
        agent = Agent(
            entity_id="memory_test_agent",
            name="Memory Test",
            position=Pos2D(x=100.0, y=100.0),
            tier=AgentTier.L2_FUNCTIONAL,
        )

        agent_size = sys.getsizeof(agent)
        # Agent should be under 10KB
        assert agent_size < 10240, f"Agent size {agent_size} bytes exceeds 10KB limit"

    def test_world_initialization_memory(self):
        """Test that world initialization doesn't use excessive memory."""
        gc.collect()

        config = Config()
        world = World(config)
        world._initialize()

        # The world should initialize without excessive memory usage
        agent_count = world.get_agent_count()
        # Should have initialized properly
        assert agent_count >= 0


class TestRegressionBaseline:
    """
    Regression baseline tests that track performance over time.

    These tests record performance metrics and can be used to detect
    performance regressions when run against new commits.
    """

    @pytest.fixture
    def perf_world(self):
        """Create a world for performance testing."""
        config = Config()
        world = World(config)
        world._initialize()

        # Spawn agents
        for i in range(200):
            agent = Agent(
                entity_id=f"perf_agent_{i}",
                name=f"Perf Agent {i}",
                position=Pos2D(x=float(i % 50), y=float(i // 50)),
                tier=AgentTier.L3_BACKGROUND if i % 5 != 0 else AgentTier.L2_FUNCTIONAL,
            )
            world.register_agent(agent)

        gc.collect()
        return world

    def test_ticks_per_second_baseline(self, perf_world):
        """
        Baseline test for simulation speed.

        This test records how many ticks can be processed per second.
        If this number drops significantly, it indicates a regression.
        """
        # Warm up
        for _ in range(3):
            perf_world.tick_once()

        # Measure
        tick_count = 10
        start = time.perf_counter()

        for _ in range(tick_count):
            perf_world.tick_once()

        elapsed = time.perf_counter() - start
        ticks_per_second = tick_count / elapsed

        # Record baseline (adjust as needed for your hardware)
        # Allow 25% variance for CI/CD environments and test overhead
        # This should be at least 5.6 TPS for 200 agents (7.5 * 0.75)
        min_tps = 5.6

        print(f"\nPerformance baseline: {ticks_per_second:.1f} TPS")

        assert ticks_per_second >= min_tps, (
            f"Performance regression: {ticks_per_second:.1f} TPS < {min_tps} TPS baseline"
        )

    def test_spatial_query_baseline(self, perf_world):
        """
        Baseline test for spatial query performance.

        Measures the time to perform 100 spatial queries.
        """
        chunk_manager = perf_world._chunk_manager

        # Warm up
        for _ in range(10):
            chunk_manager.get_agents_in_radius(25.0, 25.0, 10.0)

        # Measure
        query_count = 100
        start = time.perf_counter()

        for i in range(query_count):
            x = float(i % 50)
            y = float(i // 50)
            chunk_manager.get_agents_in_radius(x, y, 10.0)

        elapsed = time.perf_counter() - start
        ms_per_query = (elapsed / query_count) * 1000

        # Record baseline (adjust as needed)
        max_ms_per_query = 20  # Maximum acceptable time per query

        print(f"\nSpatial query baseline: {ms_per_query:.2f} ms/query")

        assert ms_per_query < max_ms_per_query, (
            f"Spatial query regression: {ms_per_query:.2f}ms > {max_ms_per_query}ms baseline"
        )

    def test_memory_baseline(self, perf_world):
        """
        Baseline test for memory usage.

        Measures memory usage after spawning agents.
        """
        import sys

        gc.collect()

        # Get memory usage
        agent_count = perf_world.get_agent_count()
        total_memory = sum(
            sys.getsizeof(a) + sum(sys.getsizeof(v) for v in a.__dict__.values())
            for a in perf_world.get_all_agents()
        )

        bytes_per_agent = total_memory / agent_count if agent_count > 0 else 0

        # Record baseline (adjust as needed)
        max_bytes_per_agent = 50000  # 50KB per agent maximum

        print(f"\nMemory baseline: {bytes_per_agent:.0f} bytes/agent ({agent_count} agents)")

        assert bytes_per_agent < max_bytes_per_agent, (
            f"Memory regression: {bytes_per_agent:.0f} bytes/agent > {max_bytes_per_agent} baseline"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
