"""
Science Module — Unified Scientific Disciplines for AmbientSaga

This module provides a comprehensive scientific framework that integrates:
- Physics: Movement, forces, energy, momentum, thermodynamics
- Chemistry: Substances, reactions, compounds, molecular dynamics
- Biology: Reproduction, genetics, metabolism, evolution
- Ecology: Food chains, energy flow, nutrient cycles, ecosystem dynamics
- Earth Science: Geological processes, atmosphere, hydrology
- Medicine: Health, disease, immunity
- Psychology: Cognition, emotion, behavior
- Sociology: Group dynamics, culture, institutions
- Economics: Markets, trade, wealth creation
- Political Science: Governance, power, institutions

All disciplines are coupled through a unified physics substrate:
- Energy conservation
- Mass conservation
- Information flow
- Entropy dynamics

Key Principles:
1. All phenomena emerge from quantum/physical substrate
2. Chemistry emerges from physics (atomic interactions)
3. Biology emerges from chemistry (molecular systems)
4. Ecology emerges from biology (ecosystem dynamics)
5. Social systems emerge from biology (human behavior)
6. Economic systems emerge from social systems (exchange)
7. Political systems emerge from social systems (power)

This is a simplified but principled approximation, not a full simulation.
"""

from __future__ import annotations

from .physics import PhysicsEngine, Vector3D, Force, Energy, Momentum
from .chemistry import ChemistryEngine, Substance, Reaction, Compound
from .biology import BiologyEngine, Organism, Genome, Metabolism, ReproductionSystem
from .ecology import EcosystemEngine, Ecosystem, FoodChain, NutrientCycle, TrophicLevel
from .systems import ScienceEngine, ScientificLaw, CouplingRelation
from .functional_science import (
    FunctionalScienceEngine,
    FunctionalPhysics,
    FunctionalChemistry,
    FunctionalBiology,
    FunctionalEcology,
    PhysicalLaw,
    ChemicalReaction,
)

__all__ = [
    # Physics
    "PhysicsEngine",
    "Vector3D",
    "Force",
    "Energy",
    "Momentum",
    # Chemistry
    "ChemistryEngine",
    "Substance",
    "Reaction",
    "Compound",
    # Biology
    "BiologyEngine",
    "Organism",
    "Genome",
    "Metabolism",
    "ReproductionSystem",
    # Ecology
    "EcosystemEngine",
    "Ecosystem",
    "FoodChain",
    "NutrientCycle",
    "TrophicLevel",
    # Unified
    "ScienceEngine",
    "ScientificLaw",
    "CouplingRelation",
    # Functional Science (New)
    "FunctionalScienceEngine",
    "FunctionalPhysics",
    "FunctionalChemistry",
    "FunctionalBiology",
    "FunctionalEcology",
    "PhysicalLaw",
    "ChemicalReaction",
]
