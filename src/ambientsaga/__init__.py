"""
AmbientSaga — Decentralized Perception-Driven Multi-Agent Simulation Engine
for Social-Ecological Co-Evolution

A civilization-scale simulation platform for thousands of AI agents operating
in richly modeled natural and social worlds, designed for academic research,
engineering innovation, and immersive exploration.
"""

__version__ = "0.1.0"
__author__ = "AmbientSaga Team"

from ambientsaga.config import AgentConfig, Config, SimulationConfig, WorldConfig
from ambientsaga.evolution import (
    BehaviorGenome,
    CultureEngine,
    EmergenceDetector,
    EvolutionEngine,
    Gene,
    GeneType,
    MutationType,
    SelectionEngine,
    VariationEngine,
)
from ambientsaga.scenarios import (
    Scenario,
    ScenarioLoader,
    ScenarioRegistry,
    WorldGenerator,
)
from ambientsaga.types import *  # noqa: F403, F405
from ambientsaga.world.signal_bus import SignalBus
from ambientsaga.world.state import World, WorldSnapshot
from ambientsaga.world.tick import TickEngine
from ambientsaga.world.world import ClimateState, TerrainCell, TerrainGenerator, WorldState

__all__ = [
    # Version
    "__version__",
    # Core
    "Config",
    "WorldConfig",
    "AgentConfig",
    "SimulationConfig",
    # Types
    "Pos2D",
    "EntityID",
    "AgentTier",
    "TerrainType",
    "ClimateZone",
    "ResourceType",
    "SignalType",
    "Signal",
    "Event",
    # World
    "World",
    "WorldSnapshot",
    "WorldState",
    "TerrainCell",
    "ClimateState",
    "TerrainGenerator",
    "SignalBus",
    "TickEngine",
    # Evolution
    "BehaviorGenome",
    "Gene",
    "GeneType",
    "VariationEngine",
    "MutationType",
    "SelectionEngine",
    "CultureEngine",
    "EmergenceDetector",
    "EvolutionEngine",
    # Scenarios
    "Scenario",
    "ScenarioRegistry",
    "WorldGenerator",
    "ScenarioLoader",
]
