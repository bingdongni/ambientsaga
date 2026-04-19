"""
Benchmark module — performance testing and profiling.

Benchmarks the simulation at various scales to identify bottlenecks
and validate scaling properties.
"""

from __future__ import annotations

import time
import json
import gc
from dataclasses import dataclass
from typing import Callable
from pathlib import Path

from ambientsaga.config import Config
from ambientsaga.world.state import World
from ambientsaga.agents import AgentFactory
from ambientsaga.natural import TerrainGenerator


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    name: str
    agents: int
    world_size: tuple[int, int]
    ticks: int
    elapsed_seconds: float
    ticks_per_second: float
    memory_mb: float
    peak_memory_mb: float
    agent_update_ms: float
    world_update_ms: float
    signal_update_ms: float
    event_log_ms: float
    phase_times: dict[str, float]


class Benchmark:
    """
    Performance benchmarking suite.

    Runs the simulation at various scales and measures:
    - Throughput (ticks per second)
    - Memory usage
    - Per-phase timing
    - Scaling behavior
    """

    def __init__(self) -> None:
        self.results: list[BenchmarkResult] = []

    def run(
        self,
        name: str,
        agents: int,
        world_size: tuple[int, int],
        ticks: int,
        preset: str = "academic",
    ) -> BenchmarkResult:
        """Run a single benchmark."""
        import tracemalloc

        gc.collect()
        tracemalloc.start()

        config = Config.from_preset(preset)
        config.simulation.world.width = world_size[0]
        config.simulation.world.height = world_size[1]
        config.simulation.agents.tier1_count = max(1, agents // 20)
        config.simulation.agents.tier2_count = max(5, agents // 5)
        config.simulation.agents.tier3_count = (
            agents - config.simulation.agents.tier1_count
            - config.simulation.agents.tier2_count
        )

        world = World(config)

        # Generate terrain
        terrain_gen = TerrainGenerator(
            config.simulation.world, config.simulation.terrain
        )
        terrain_data = terrain_gen.generate()
        world._terrain = terrain_data["terrain"]
        world._elevation = terrain_data["elevation"]

        # Spawn agents
        factory = AgentFactory(world)
        factory.spawn_population(n=agents)

        # Benchmark loop
        phase_times: dict[str, float] = {p: 0.0 for p in world._tick_engine.TICK_PHASES}

        start = time.perf_counter()
        for tick in range(ticks):
            tick_start = time.perf_counter()

            world.tick_once()

            tick_end = time.perf_counter()
            for phase in world._tick_engine.TICK_PHASES:
                phase_times[phase] += tick_end - tick_start

        elapsed = time.perf_counter() - start

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result = BenchmarkResult(
            name=name,
            agents=agents,
            world_size=world_size,
            ticks=ticks,
            elapsed_seconds=elapsed,
            ticks_per_second=ticks / elapsed,
            memory_mb=current / 1024 / 1024,
            peak_memory_mb=peak / 1024 / 1024,
            agent_update_ms=phase_times.get("AGENT_DECISION", 0) * 1000,
            world_update_ms=phase_times.get("WORLD_UPDATE", 0) * 1000,
            signal_update_ms=phase_times.get("AGENT_PERCEPTION", 0) * 1000,
            event_log_ms=phase_times.get("HISTORY", 0) * 1000,
            phase_times={k: v * 1000 for k, v in phase_times.items()},
        )

        self.results.append(result)
        return result

    def run_scaling_study(
        self,
        agent_counts: list[int] = [100, 500, 1000, 5000, 10000],
        world_size: tuple[int, int] = (256, 256),
        ticks: int = 1000,
    ) -> list[BenchmarkResult]:
        """Run a scaling study across different agent counts."""
        results = []
        for n in agent_counts:
            print(f"Benchmarking {n} agents...")
            result = self.run(
                name=f"scaling_{n}",
                agents=n,
                world_size=world_size,
                ticks=ticks,
            )
            results.append(result)
            print(f"  TPS: {result.ticks_per_second:.1f}, Memory: {result.peak_memory_mb:.1f} MB")
            gc.collect()
        return results

    def save_results(self, path: str | Path) -> None:
        """Save benchmark results to JSON."""
        data = []
        for r in self.results:
            data.append({
                "name": r.name,
                "agents": r.agents,
                "world_size": r.world_size,
                "ticks": r.ticks,
                "elapsed_seconds": r.elapsed_seconds,
                "ticks_per_second": r.ticks_per_second,
                "memory_mb": r.memory_mb,
                "peak_memory_mb": r.peak_memory_mb,
                "agent_update_ms": r.agent_update_ms,
                "world_update_ms": r.world_update_ms,
                "phase_times": r.phase_times,
            })
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


def run_quick_benchmark() -> BenchmarkResult:
    """Run a quick benchmark to verify the system works."""
    bench = Benchmark()
    result = bench.run(
        name="quick_benchmark",
        agents=100,
        world_size=(128, 128),
        ticks=100,
    )
    return result


if __name__ == "__main__":
    result = run_quick_benchmark()
    print(f"TPS: {result.ticks_per_second:.1f}")
    print(f"Memory: {result.peak_memory_mb:.1f} MB")
