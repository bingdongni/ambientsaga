"""
Command-line entry point for AmbientSaga.

Usage:
    python -m ambientsaga run --ticks 1000 --agents 5000 --preset river_valley
    python -m ambientsaga init --world desert --agents 1000
    python -m ambientsaga benchmark --duration 100000
    python -m ambientsaga export-metrics --path results.json
    python -m ambientsaga replay --snapshot snapshot.db
"""

import argparse
import sys
from pathlib import Path

import numpy as np

from ambientsaga.agents import UnifiedAgentFactory as AgentFactory
from ambientsaga.config import Config
from ambientsaga.natural.climate import ClimateSystem
from ambientsaga.scenarios import Scenario, ScenarioLoader, ScenarioRegistry, WorldGenerator
from ambientsaga.types import TerrainType
from ambientsaga.world.state import World

# Web visualization imports (optional - only if visualization enabled)
_visualization_module = None


def handle_scenario_command(args: argparse.Namespace) -> int:
    """Handle scenario CLI commands."""
    registry = ScenarioRegistry()

    if args.action == "list":
        scenarios = registry.list_scenarios()

        if args.tags:
            filter_tags = [t.strip() for t in args.tags.split(",")]
            filtered = []
            for name in scenarios:
                scenario = registry.get(name)
                if scenario and any(tag in scenario.tags for tag in filter_tags):
                    filtered.append(name)
            scenarios = filtered

        print("Available scenarios:")
        print("-" * 50)
        for name in sorted(scenarios):
            scenario = registry.get(name)
            if scenario:
                print(f"\n{name}:")
                print(f"  Difficulty: {scenario.difficulty}")
                print(f"  Tags: {', '.join(scenario.tags)}")
                print(f"  {scenario.description[:70]}...")
        return 0

    elif args.action == "info":
        if not args.name:
            print("Error: --name required for info command")
            return 1

        scenario = registry.get(args.name)
        if not scenario:
            print(f"Unknown scenario: {args.name}")
            return 1

        print(f"\n{'=' * 60}")
        print(f"SCENARIO: {scenario.name}")
        print(f"{'=' * 60}")
        print(f"Author: {scenario.author}")
        print(f"Version: {scenario.version}")
        print(f"Difficulty: {scenario.difficulty}")
        print(f"Tags: {', '.join(scenario.tags)}")
        print(f"\nDescription:\n{scenario.description}")
        print(f"\nDuration: {scenario.duration_ticks if scenario.duration_ticks > 0 else 'Unlimited'} ticks")

        if scenario.world_params:
            print("\nWorld Parameters:")
            for k, v in scenario.world_params.items():
                print(f"  {k}: {v}")

        print(f"\nInitial Conditions: {len(scenario.initial_conditions)}")
        for cond in scenario.initial_conditions[:5]:
            print(f"  - {cond}")

        print(f"\nScheduled Events: {len(scenario.events)}")
        for evt in scenario.events[:5]:
            print(f"  - Tick {evt.get('tick', 0)}: {evt.get('type', 'unknown')}")

        print(f"\nVictory Conditions: {len(scenario.victory_conditions)}")
        for vc in scenario.victory_conditions:
            print(f"  - {vc.get('type', 'unknown')}: {vc.get('value', 'N/A')}")

        return 0

    elif args.action == "create":
        if not args.name or not args.output:
            print("Error: --name and --output required for create command")
            return 1

        scenario = Scenario(name=args.name)
        ScenarioLoader.save(scenario, args.output)
        print(f"Created scenario at: {args.output}")
        print("\nEdit the scenario file to customize:")
        print("  - Initial conditions (population, resources, structures)")
        print("  - Scheduled events (disasters, migrations, discoveries)")
        print("  - Victory conditions (goals to achieve)")
        return 0

    elif args.action == "run":
        if not args.name:
            print("Error: --name required for run command")
            return 1

        # Load and run the scenario
        scenario = registry.get(args.name)
        if not scenario:
            print(f"Unknown scenario: {args.name}")
            return 1

        print(f"Running scenario: {scenario.name}")
        print(f"Description: {scenario.description}")

        # Create config and apply scenario
        config = Config.from_preset("river_valley")
        world_gen = WorldGenerator(config)
        world_gen.apply_scenario(scenario)

        print("Generating world...")
        world = world_gen.generate()

        print(f"World generated: {config.simulation.world.width}x{config.simulation.world.height}")
        print(f"Total agents: {world.get_agent_count()}")

        # Run the simulation
        ticks = scenario.duration_ticks if scenario.duration_ticks > 0 else 1000
        print(f"\nRunning simulation for {ticks} ticks...")

        from datetime import datetime
        start = datetime.now()

        for tick in range(ticks):
            world.tick_once()

            if tick % 100 == 0:
                elapsed = (datetime.now() - start).total_seconds()
                tps = (tick + 1) / elapsed if elapsed > 0 else 0
                print(f"  Tick {tick:>8} | Agents: {world.get_agent_count():>6} | {tps:>6.1f} ticks/s")

        print("\nSimulation complete!")
        print(f"Final population: {world.get_agent_count()}")

        return 0

    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="ambientsaga",
        description="AmbientSaga — Decentralized Perception-Driven Multi-Agent Simulation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m ambientsaga run --ticks 10000 --agents 5000 --preset river_valley
  python -m ambientsaga run --ticks 100000 --agents 50000 --preset large
  python -m ambientsaga run --config my_config.json --visualize
  python -m ambientsaga benchmark --duration 50000
  python -m ambientsaga init --agents 1000
  python -m ambientsaga export --path results.json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run command
    run_parser = subparsers.add_parser("run", help="Run a simulation")
    run_parser.add_argument(
        "--ticks", type=int, default=1000, help="Number of ticks to run"
    )
    run_parser.add_argument(
        "--agents", type=int, default=None, help="Number of agents (overrides preset)"
    )
    run_parser.add_argument(
        "--preset",
        choices=["river_valley", "large", "academic", "exploration"],
        default="river_valley",
        help="Configuration preset",
    )
    run_parser.add_argument(
        "--scenario", type=str, help="Scenario name or file path"
    )
    run_parser.add_argument(
        "--config", type=str, help="Path to config JSON file"
    )
    run_parser.add_argument(
        "--visualize", action="store_true", help="Enable visualization"
    )
    run_parser.add_argument(
        "--seed", type=int, help="Random seed for reproducibility"
    )
    run_parser.add_argument(
        "--output", type=str, help="Output path for results"
    )
    run_parser.add_argument(
        "--width", type=int, default=512, help="World width"
    )
    run_parser.add_argument(
        "--height", type=int, default=512, help="World height"
    )
    run_parser.add_argument(
        "--tick-rate", type=float, default=0.0,
        help="Target ticks per second (0=unlimited, default=0)"
    )
    run_parser.add_argument(
        "--fast", action="store_true",
        help="Run at maximum speed (sets tick-rate to 0)"
    )
    run_parser.add_argument(
        "--report", action="store_true",
        help="Generate academic report at end of simulation"
    )
    run_parser.add_argument(
        "--report-format",
        choices=["markdown", "latex", "html", "json"],
        default="markdown",
        help="Academic report format (default: markdown)"
    )
    run_parser.add_argument(
        "--report-output", type=str,
        help="Output path for academic report (default: report.md/html/tex/json)"
    )

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize a new world")
    init_parser.add_argument(
        "--world",
        choices=["river_valley", "archipelago", "pangaea", "island_chain", "desert"],
        default="river_valley",
        help="World type",
    )
    init_parser.add_argument("--agents", type=int, default=1000)
    init_parser.add_argument("--seed", type=int)
    init_parser.add_argument("--output", type=str, default="world.json")

    # benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run benchmark")
    bench_parser.add_argument(
        "--duration", type=int, default=50000, help="Number of ticks"
    )
    bench_parser.add_argument(
        "--agents", type=int, default=10000, help="Number of agents"
    )
    bench_parser.add_argument(
        "--preset", default="academic", help="Configuration preset"
    )
    bench_parser.add_argument(
        "--output", type=str, default="benchmark_results.json"
    )

    # scenario command
    scenario_parser = subparsers.add_parser("scenario", help="Scenario management")
    scenario_parser.add_argument(
        "action",
        choices=["list", "info", "create", "run"],
        default="list",
        help="Scenario action"
    )
    scenario_parser.add_argument(
        "--name", type=str, help="Scenario name"
    )
    scenario_parser.add_argument(
        "--output", type=str, help="Output path for scenario"
    )
    scenario_parser.add_argument(
        "--tags", type=str, help="Comma-separated tags to filter by"
    )

    # export command
    export_parser = subparsers.add_parser("export", help="Export metrics")
    export_parser.add_argument(
        "--path", type=str, required=True, help="Output path"
    )
    export_parser.add_argument(
        "--from-snapshot", type=str, help="Load from snapshot"
    )

    args = parser.parse_args()

    if args.command == "run":
        return run_simulation(args)
    elif args.command == "init":
        return init_world(args)
    elif args.command == "benchmark":
        return run_benchmark(args)
    elif args.command == "export":
        return export_metrics(args)
    elif args.command == "scenario":
        return handle_scenario_command(args)
    else:
        # Default: run simulation
        return run_simulation(args)


def run_simulation(args: argparse.Namespace) -> int:
    """Run a simulation."""
    from ambientsaga.config import Config
    from ambientsaga.natural import TerrainGenerator

    # Create config
    config = Config.from_preset(args.preset)

    if args.config:
        config = Config.from_file(args.config)

    # Apply scenario if specified
    if args.scenario:
        from ambientsaga.scenarios import ScenarioRegistry
        registry = ScenarioRegistry()
        scenario = registry.get(args.scenario)

        if scenario:
            print(f"Loading scenario: {scenario.name}")
            print(f"  {scenario.description[:80]}...")
            print(f"  Difficulty: {scenario.difficulty}")

            # Override duration from scenario if set
            if scenario.duration_ticks > 0:
                args.ticks = scenario.duration_ticks
        else:
            # Try loading from file
            from pathlib import Path
            if Path(args.scenario).exists():
                scenario = ScenarioLoader.from_file(args.scenario)
                print(f"Loading scenario from file: {args.scenario}")
            else:
                print(f"Warning: Scenario '{args.scenario}' not found")

    # Override settings from command line
    if args.agents is not None:
        config.simulation.agents.tier1_count = args.agents // 10
        config.simulation.agents.tier2_count = args.agents // 10
        config.simulation.agents.tier3_count = args.agents - args.agents // 10 - args.agents // 10

    if args.seed is not None:
        config.simulation.world.seed = args.seed

    config.simulation.world.width = args.width
    config.simulation.world.height = args.height

    if args.visualize:
        config.simulation.visualization.enabled = True
        config.simulation.visualization.renderer_type = "canvas"

    print("Initializing AmbientSaga world...")
    print(f"  World: {config.simulation.world.width}x{config.simulation.world.height}")
    print(f"  Agents: {config.simulation.agents.total_agents}")
    print(f"  Preset: {args.preset}")
    print(f"  Seed: {config.simulation.world.seed}")
    print(f"  Visualization: {config.simulation.visualization.enabled}")

    # Create world
    world = World(config)

    # Generate terrain
    terrain_gen = TerrainGenerator(
        config.simulation.world,
        config.simulation.terrain,
    )
    terrain_data = terrain_gen.generate()

    # Apply terrain to world
    world._terrain = terrain_data["terrain"]
    world._elevation = terrain_data["elevation"]
    world._soil = terrain_data["soil"]

    # Initialize climate system (temperature, humidity)
    climate = ClimateSystem(
        config.simulation.climate,
        config.simulation.world.width,
        config.simulation.world.height,
        config.simulation.world.seed,
    )
    # Create latitude array
    lat_range = np.linspace(-90, 90, config.simulation.world.height)
    latitude = np.tile(lat_range[:, np.newaxis], (1, config.simulation.world.width))
    climate.initialize(world._elevation, latitude)
    world._temperature = climate._temperature
    world._humidity = climate._humidity

    # Generate initial vegetation based on climate and terrain
    world._vegetation = np.zeros((config.simulation.world.height, config.simulation.world.width), dtype=np.float64)
    for y in range(config.simulation.world.height):
        for x in range(config.simulation.world.width):
            terrain = TerrainType(world._terrain[y, x])
            world._temperature[y, x]
            humid = world._humidity[y, x]
            # Simple vegetation model
            if terrain.is_water:
                veg = 0.0
            elif terrain in {TerrainType.DESERT, TerrainType.DESERT_SCRUB}:
                veg = 0.1
            elif terrain in {TerrainType.GRASSLAND, TerrainType.SAVANNA}:
                veg = 0.6 + 0.3 * humid
            elif terrain.is_forest:
                veg = 0.7 + 0.2 * humid
            else:
                veg = 0.3 + 0.4 * humid
            world._vegetation[y, x] = veg

    # Populate chunks
    for y in range(0, config.simulation.world.height, config.simulation.world.chunk_size):
        for x in range(0, config.simulation.world.width, config.simulation.world.chunk_size):
            chunk = world._chunk_manager.get_or_create_chunk(
                x // config.simulation.world.chunk_size,
                y // config.simulation.world.chunk_size,
            )
            # Copy terrain data to chunk
            for cy in range(chunk.size):
                for cx in range(chunk.size):
                    wx = x + cx
                    wy = y + cy
                    if (wx < config.simulation.world.width and
                        wy < config.simulation.world.height):
                        chunk.terrain[cy, cx] = int(terrain_data["terrain"][wy, wx])
                        chunk.elevation[cy, cx] = float(terrain_data["elevation"][wy, wx])

    # Spawn agents
    print("Spawning agents...")
    factory = AgentFactory(world)
    agents = factory.spawn_population(n=config.simulation.agents.total_agents)
    print(f"  Spawned {len(agents)} agents")

    # Start web visualization server if enabled
    web_server = None
    if config.simulation.visualization.enabled:
        try:
            from ambientsaga.visualization.web_server import StandaloneWebServer, WebServer
            web_host = config.simulation.visualization.web_host
            web_port = config.simulation.visualization.web_port

            # Try WebSocket server first (real-time updates)
            try:
                web_server = WebServer(
                    world,
                    config.simulation.visualization,
                    host=web_host,
                    port=web_port,
                )
                if web_server.start():
                    print(f"  Web dashboard: http://{web_host}:{web_port}")
                    print(f"  WebSocket: ws://{web_host}:{web_port}")
                else:
                    raise RuntimeError("WebServer.start() returned False")
            except Exception as ws_err:
                # Fall back to standalone HTTP server (polling mode)
                print(f"  WebSocket server unavailable ({ws_err}), using polling mode")
                web_server = StandaloneWebServer(
                    world,
                    config.simulation.visualization,
                    host=web_host,
                    port=web_port,
                )
                if not web_server.start():
                    print(f"  Warning: Could not start web server on port {web_port}")
                    web_server = None
                else:
                    print(f"  Web dashboard (polling): http://{web_host}:{web_port}")
        except Exception as e:
            print(f"  Warning: Could not start visualization: {e}")
            web_server = None

    # Configure tick rate
    tick_rate = args.tick_rate if args.tick_rate else 0.0
    if args.fast:
        tick_rate = 0.0
    world.tick_engine.set_tick_rate(tick_rate)

    # Run simulation
    mode = "unlimited" if tick_rate == 0.0 else f"{tick_rate} ticks/s"
    print(f"\nRunning simulation for {args.ticks} ticks [{mode}]...")
    if web_server:
        print("  (Press Ctrl+C to stop early, visualization available at http://localhost:8765)\n")
    else:
        print("  (Press Ctrl+C to stop early)\n")

    try:
        from datetime import datetime
        start = datetime.now()
        render_interval = config.simulation.visualization.render_every_n_ticks
        last_render = -render_interval  # Force first render

        for tick in range(args.ticks):
            world.tick_once()

            # Broadcast world state to web clients periodically
            if web_server and (tick - last_render) >= render_interval:
                web_server.broadcast_world_update()
                last_render = tick

            elapsed = (datetime.now() - start).total_seconds()
            tps = (tick + 1) / elapsed if elapsed > 0 else 0
            print(
                f"  Tick {tick:>8} | "
                f"{world.tick_engine.get_calendar_string():<25} | "
                f"Agents: {world.get_agent_count():>6} | "
                f"{tps:>6.1f} ticks/s"
            )

            if tick > 0 and tick % config.simulation.autosave_interval == 0:
                world.save(config.simulation.autosave_path)

    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user.")

    # Print final summary
    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)
    print(world.get_summary())
    print()

    # Save output if requested
    if args.output:
        world.save(args.output)
        print(f"World saved to: {args.output}")

    # Generate academic report if requested
    if args.report:
        from ambientsaga.config import ResearchConfig
        from ambientsaga.research.metrics import MetricsCollector

        print("\nGenerating academic report...")
        research_config = ResearchConfig()
        metrics = MetricsCollector(world, research_config)

        # Collect metrics at regular intervals
        sample_interval = max(1, args.ticks // 100)
        for tick in range(0, args.ticks + 1, sample_interval):
            metrics.collect(tick)

        if len(metrics) > 0:
            report = metrics.generate_academic_report(
                title=f"AmbientSaga Simulation Report — {args.preset}",
                authors=["AmbientSaga Research Team"],
            )

            # Determine output path
            report_path = args.report_output
            if not report_path:
                ext = args.report_format
                report_path = f"ambientsaga_report.{ext}"

            # Save report
            report.save(report_path, args.report_format)
            print(f"Academic report saved to: {report_path}")
            print(f"  Format: {args.report_format}")
            print(f"  Sections: {len(report.sections)}")
            print(f"  Tables: {len(report.tables)}")
        else:
            print("Warning: No metrics collected, skipping report generation")

    # Cleanup web server
    if web_server:
        web_server.stop()

    return 0


def init_world(args: argparse.Namespace) -> int:
    """Initialize a new world configuration."""
    print(f"Initializing world: {args.world}")
    print(f"  Agents: {args.agents}")

    config = Config.from_preset("river_valley")
    if args.agents:
        config.simulation.agents.tier1_count = args.agents // 10
        config.simulation.agents.tier2_count = args.agents // 10
        config.simulation.agents.tier3_count = args.agents - args.agents // 10 - args.agents // 10

    if args.seed:
        config.simulation.world.seed = args.seed

    output_path = Path(args.output)
    config.save(output_path)
    print(f"Configuration saved to: {output_path}")
    return 0


def run_benchmark(args: argparse.Namespace) -> int:
    """Run a benchmark simulation."""
    import json
    from datetime import datetime

    from ambientsaga.config import Config
    from ambientsaga.natural import TerrainGenerator
    from ambientsaga.research.metrics import MetricsCollector

    print("Running benchmark...")
    print(f"  Duration: {args.duration} ticks")
    print(f"  Agents: {args.agents}")

    config = Config.from_preset("academic")
    config.simulation.agents.tier1_count = max(10, args.agents // 20)
    config.simulation.agents.tier2_count = max(50, args.agents // 5)
    config.simulation.agents.tier3_count = args.agents - config.simulation.agents.tier1_count - config.simulation.agents.tier2_count

    world = World(config)

    # Generate terrain
    terrain_gen = TerrainGenerator(config.simulation.world, config.simulation.terrain)
    terrain_data = terrain_gen.generate()
    world._terrain = terrain_data["terrain"]
    world._elevation = terrain_data["elevation"]
    world._soil = terrain_data["soil"]

    # Spawn agents
    factory = AgentFactory(world)
    factory.spawn_population(n=config.simulation.agents.total_agents)

    # Setup metrics
    metrics = MetricsCollector(world, config.simulation.research)

    print("Starting benchmark...")
    start = datetime.now()
    last_report = 0

    for tick in range(args.duration):
        world.tick_once()

        if tick % config.simulation.research.metrics_interval == 0:
            metrics.collect(tick)

        if tick - last_report >= 5000:
            elapsed = (datetime.now() - start).total_seconds()
            tps = (tick + 1) / elapsed if elapsed > 0 else 0
            print(f"  Tick {tick}/{args.duration} | {tps:.1f} ticks/s | Pop: {world.get_agent_count()}")
            last_report = tick

    # Save results
    elapsed = (datetime.now() - start).total_seconds()
    results = {
        "duration_ticks": args.duration,
        "total_agents": config.simulation.agents.total_agents,
        "elapsed_seconds": elapsed,
        "avg_ticks_per_second": args.duration / elapsed,
        "metrics": metrics.get_summary(),
    }

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nBenchmark complete. Results saved to: {args.output}")
    print(f"  Total time: {elapsed:.1f}s")
    print(f"  Avg TPS: {args.duration / elapsed:.1f}")
    return 0


def export_metrics(args: argparse.Namespace) -> int:
    """Export metrics from a simulation."""
    print(f"Exporting metrics to: {args.path}")
    print("Note: Run a simulation first, then export from the running world.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
