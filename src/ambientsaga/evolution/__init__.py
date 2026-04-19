"""
Evolution Module — Self-Evolution and Emergence System for AmbientSaga

This module provides a framework for emergent behavior and self-organization,
where intelligent agents can develop, share, and evolve their behavioral strategies
WITHOUT hardcoded social institutions.

Core Philosophy:
- Agents are defined by their BEHAVIORAL GENOMES, not hardcoded rules
- Genomes are evolved through variation (mutation + crossover)
- Successful behaviors spread through cultural transmission
- Complex social institutions emerge from simple evolving behaviors

Key Concepts:
- GENOME: A behavioral program that defines how an agent acts
- GENE: A node in the behavioral tree (primitive or composite)
- MUTATION: Random changes to a genome
- CROSSOVER: Exchange of genes between genomes
- CULTURAL TRANSMISSION: Agents copy successful strategies from others
- EMERGENCE: New patterns/structures arising from evolved behaviors
"""

from __future__ import annotations

from .culture import CultureEngine
from .emergence import EmergenceDetector
from .engine import EvolutionConfig, EvolutionEngine
from .genome import (
    BehaviorGenome,
    CompositeGene,
    ConditionalGene,
    Gene,
    GeneType,
    GenomeFactory,
    PrimitiveGene,
    SequenceGene,
)
from .selection import FitnessFunction, SelectionEngine
from .variation import MutationOperator, MutationType, VariationEngine

__all__ = [
    "Gene",
    "GeneType",
    "PrimitiveGene",
    "ConditionalGene",
    "SequenceGene",
    "CompositeGene",
    "BehaviorGenome",
    "GenomeFactory",
    "VariationEngine",
    "MutationOperator",
    "MutationType",
    "SelectionEngine",
    "FitnessFunction",
    "CultureEngine",
    "EmergenceDetector",
    "EvolutionEngine",
    "EvolutionConfig",
]
