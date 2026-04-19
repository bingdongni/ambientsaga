"""
AmbientSaga - AI Natural World and AI Social World Simulation

An ambitious project to simulate a world with thousands of AI agents
living in a natural world and social world, built with atmospheric
programming principles.

Architecture:
- World Engine: Terrain, climate, resources, natural events
- Agent System: Unified Agent with rule-based, semi-LLM, and full-LLM reasoning
- Simulation Engine: Tick-driven, batch-processed, event-driven
- Visualization: Real-time 3D/2D rendering with WebSocket streaming
- Evolution System: Self-evolution through behavioral genomes

Academic value: Social simulation, emergent behavior, AI agents
Engineering value: Scalable concurrent systems, distributed simulation
"""

from __future__ import annotations

import asyncio

from ambientsaga.agents import (
    AgentRegistry,
    AgentTier,
    UnifiedAgentFactory,
)
from ambientsaga.config import Config
from ambientsaga.simulation import SimulationEngine
from ambientsaga.world import World

__version__ = "0.1.0"


class AmbientSaga:
    """
    Main simulation orchestrator.
    Connects all systems and provides the primary API for running the simulation.
    """

    def __init__(self, config: Config | None = None):
        self.config = config or Config.from_preset("river_valley")
        self.world = World(self.config)

        # Calculate max_agents from tier counts
        agent_cfg = self.config.agent_config
        max_agents = (
            agent_cfg.tier1_count +
            agent_cfg.tier2_count +
            agent_cfg.tier3_count +
            getattr(agent_cfg, 'tier4_count', 0)
        )
        self.agent_registry = AgentRegistry(max_agents=max_agents * 2)

        self.simulation = SimulationEngine(
            self.config.simulation,
            self.world,
            self.agent_registry
        )

        # Agent factory for unified agents
        self.agent_factory = UnifiedAgentFactory(self.world)

        self._running = False
        self._spawned_initial_agents = False

    async def spawn_agents(self, count: int) -> int:
        """Spawn initial agents into the world using the unified factory."""
        spawned = 0

        # Use the unified agent factory - ensure minimum counts for meaningful simulation
        tier_distribution = {
            AgentTier.L1_CORE: max(1, int(count * 0.01)),      # Top 1% LLM agents (minimum 1)
            AgentTier.L2_FUNCTIONAL: max(2, int(count * 0.04)),  # Next 4% semi-LLM (minimum 2)
            AgentTier.L3_BACKGROUND: count - max(1, int(count * 0.01)) - max(2, int(count * 0.04)),  # Rest
        }

        # Create agents via factory
        agents = []
        for tier, tier_count in tier_distribution.items():
            for _ in range(tier_count):
                agent = self.agent_factory.create_agent(tier)
                agents.append(agent)
                # Register to world (creates behavioral genome)
                self.world.register_agent(agent)
                # Register to agent registry
                self.agent_registry.register(agent)
                spawned += 1

        return spawned

    async def initialize(self) -> None:
        """Initialize the simulation."""
        await self.simulation.initialize()

        if not self._spawned_initial_agents:
            count = await self.spawn_agents(self.config.simulation.total_agents)
            self._spawned_initial_agents = True
            print(f"Spawned {count} initial agents")
            print(f"  - L1 (LLM): {self.agent_registry.count_by_tier(AgentTier.L1_CORE)}")
            print(f"  - L2 (Semi-LLM): {self.agent_registry.count_by_tier(AgentTier.L2_FUNCTIONAL)}")
            print(f"  - L3 (Rule-based): {self.agent_registry.count_by_tier(AgentTier.L3_BACKGROUND)}")

    async def run(self, max_ticks: int | None = None) -> None:
        """Run the simulation."""
        if max_ticks:
            self.config.simulation.max_ticks = max_ticks

        await self.initialize()

        print("\nStarting AmbientSaga simulation...")
        print(f"  World: {self.config.world_config.width}x{self.config.world_config.height}")
        print(f"  Agents: {self.config.simulation.total_agents}")
        print(f"  Ticks/sec: {self.config.simulation.ticks_per_second or 'unlimited'}")
        print(f"  Max ticks: {self.config.simulation.max_ticks or 'unlimited'}")

        await self.simulation.run()

    async def shutdown(self) -> None:
        """Shutdown the simulation gracefully."""
        await self.simulation.shutdown()
        self._running = False

    def get_world_info(self) -> dict:
        """Get information about the current world state."""
        return {
            "tick": self.simulation.state.tick,
            "world_size": f"{self.config.world_config.width}x{self.config.world_config.height}",
            "agents": self.agent_registry.get_stats(),
            "climate": {
                "season": self.world.season,
                "year": self.world.year,
            },
            "evolution": self.world.evolution.get_statistics() if self.world.evolution else None,
        }

    def get_summary(self) -> str:
        """Get a human-readable world summary."""
        return self.world.get_summary()


def main():
    """Main entry point for the CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="AmbientSaga - AI Natural World and AI Social World Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m ambientsaga                    # Run with defaults (10K agents)
  python -m ambientsaga --agents 10000     # Spawn 10,000 agents
  python -m ambientsaga --ticks 5000       # Run for 5000 ticks
  python -m ambientsaga --visualize       # Enable visualization
  python -m ambientsaga --seed 42          # Set random seed
  python -m ambientsaga --profile tiny    # Use tiny profile (100 agents)
        """
    )

    parser.add_argument(
        "--agents", "-a",
        type=int,
        default=None,
        help="Number of agents to spawn (default: from config)"
    )
    parser.add_argument(
        "--ticks", "-t",
        type=int,
        default=None,
        help="Maximum ticks to run (default: unlimited)"
    )
    parser.add_argument(
        "--world-size", "-w",
        type=int,
        default=None,
        help="World width and height (square)"
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--speed", "-sp",
        type=float,
        default=None,
        help="Simulation speed multiplier"
    )
    parser.add_argument(
        "--visualize", "-v",
        action="store_true",
        help="Enable visualization"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8761,
        help="WebSocket visualization port (default: 8761)"
    )
    parser.add_argument(
        "--profile",
        choices=["tiny", "small", "medium", "large", "xlarge"],
        default="medium",
        help="Pre-configured simulation profile"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without running"
    )

    args = parser.parse_args()

    # Load config from preset
    config = Config.from_preset("river_valley")

    # Apply profile presets for CLI overrides
    profile_presets = {
        "tiny": {"agents": 100, "world_size": 64},
        "small": {"agents": 500, "world_size": 128},
        "medium": {"agents": 5000, "world_size": 256},
        "large": {"agents": 20000, "world_size": 512},
        "xlarge": {"agents": 100000, "world_size": 1024},
    }

    if args.profile in profile_presets:
        preset = profile_presets[args.profile]
    else:
        preset = profile_presets["medium"]

    # Apply CLI overrides
    if args.agents:
        config.simulation.total_agents = args.agents
    else:
        config.simulation.total_agents = preset["agents"]

    if args.world_size:
        config.world_config.width = args.world_size
        config.world_config.height = args.world_size
    else:
        config.world_config.width = preset["world_size"]
        config.world_config.height = preset["world_size"]

    if args.seed is not None:
        config.world_config.seed = args.seed

    if args.ticks:
        config.simulation.max_ticks = args.ticks

    if args.speed:
        config.simulation.ticks_per_second = args.speed

    # Dry run - just validate
    if args.dry_run:
        print("Configuration validated successfully:")
        print(f"  World: {config.world_config.width}x{config.world_config.height}, seed={config.world_config.seed}")
        print(f"  Agents: {config.simulation.total_agents}")
        print(f"  Ticks/sec: {config.simulation.ticks_per_second or 'unlimited'}")
        print(f"  Max ticks: {config.simulation.max_ticks or 'unlimited'}")
        print(f"  Visualize: {args.visualize}")
        return

    # Create and run simulation
    print(f"\n{'='*60}")
    print(f"  AmbientSaga v{__version__}")
    print(f"{'='*60}")

    sim = AmbientSaga(config)

    try:
        asyncio.run(sim.run(max_ticks=args.ticks))
    except KeyboardInterrupt:
        print("\nShutting down...")
        asyncio.run(sim.shutdown())
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
