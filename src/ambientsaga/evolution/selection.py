"""
Selection Engine — Fitness Evaluation and Selection Pressure

This module handles:
- Fitness evaluation: How good is a genome?
- Selection: Which genomes survive and reproduce?
- Diversity maintenance: Avoiding premature convergence

Key Design Principles:
1. Fitness is MULTI-OBJECTIVE: survival, reproduction, social status, etc.
2. Selection pressure is ADAPTIVE: higher when population is fit, lower when struggling
3. Diversity is monitored and enforced: we track genetic diversity and enforce minimums
4. Fitness is CONTEXTUAL: what works in one environment may not work in another

The selection system uses a combination of:
- Tournament selection for reproduction
- Fitness-proportionate selection for survival
- Elitism to preserve best genomes
- Diversity pressure to maintain variation
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

from .genome import BehaviorGenome

# =============================================================================
# Fitness Function Protocol
# =============================================================================

class FitnessFunction(Protocol):
    """Protocol for fitness evaluation functions."""

    def __call__(self, genome: BehaviorGenome, context: dict) -> float:
        """
        Evaluate the fitness of a genome.

        Args:
            genome: The genome to evaluate
            context: Environmental context (population, resources, etc.)

        Returns:
            Fitness score (higher is better)
        """
        ...


# =============================================================================
# Selection Operators
# =============================================================================

@dataclass
class SelectionResult:
    """Result of a selection operation."""

    selected: list[BehaviorGenome]
    rejected: list[BehaviorGenome]
    selection_method: str
    statistics: dict


class SelectionEngine:
    """
    Manages selection pressure and genome survival.

    The selection engine provides:
    - Adaptive selection pressure based on population fitness
    - Multiple selection methods (tournament, roulette, elitism)
    - Diversity monitoring and enforcement
    - Environmental fitness functions
    """

    def __init__(
        self,
        population_size: int = 1000,
        elitism_rate: float = 0.1,
        tournament_size: int = 5,
        diversity_threshold: float = 0.3,
        fitness_functions: list[FitnessFunction] | None = None,
        rng: random.Random | None = None,
    ):
        """
        Initialize the selection engine.

        Args:
            population_size: Target population size
            elitism_rate: Fraction of best genomes to preserve (0-1)
            tournament_size: Size of tournament for tournament selection
            diversity_threshold: Minimum acceptable diversity (0-1)
            fitness_functions: List of fitness functions to combine
            rng: Random number generator
        """
        self.population_size = population_size
        self.elitism_rate = elitism_rate
        self.tournament_size = tournament_size
        self.diversity_threshold = diversity_threshold
        self.fitness_functions = fitness_functions or []
        self.rng = rng or random.Random()

        # Statistics
        self.generation = 0
        self.best_fitness_history: list[float] = []
        self.avg_fitness_history: list[float] = []
        self.diversity_history: list[float] = []
        self.extinctions: int = 0

    def evaluate_fitness(
        self,
        genome: BehaviorGenome,
        context: dict,
    ) -> float:
        """
        Evaluate the fitness of a genome using all fitness functions.

        Args:
            genome: The genome to evaluate
            context: Environmental context

        Returns:
            Combined fitness score
        """
        if not self.fitness_functions:
            # Default fitness: based on accumulated fitness
            return genome.get_average_fitness()

        # Combine multiple fitness functions
        scores = []
        for func in self.fitness_functions:
            try:
                score = func(genome, context)
                scores.append(score)
            except Exception:
                pass

        if not scores:
            return genome.get_average_fitness()

        # Use weighted average (geometric mean for better handling of extremes)
        product = 1.0
        for score in scores:
            product *= max(0.01, score)
        return product ** (1.0 / len(scores))

    def select_for_reproduction(
        self,
        population: list[BehaviorGenome],
        num_offspring: int,
        context: dict,
    ) -> list[tuple[BehaviorGenome, BehaviorGenome]]:
        """
        Select parent pairs for reproduction using tournament selection.

        Args:
            population: Current population
            num_offspring: Number of offspring to produce
            context: Environmental context

        Returns:
            List of (parent1, parent2) tuples for reproduction
        """
        if len(population) < 2:
            return []

        pairs = []
        for _ in range(num_offspring):
            # Tournament selection for parent 1
            tournament1 = self.rng.sample(population, min(self.tournament_size, len(population)))
            parent1 = max(tournament1, key=lambda g: self.evaluate_fitness(g, context))

            # Tournament selection for parent 2 (prefer different genomes)
            tournament2 = self.rng.sample(population, min(self.tournament_size, len(population)))
            parent2 = max(tournament2, key=lambda g: self.evaluate_fitness(g, context))

            pairs.append((parent1, parent2))

        return pairs

    def select_for_survival(
        self,
        population: list[BehaviorGenome],
        offspring: list[BehaviorGenome],
        context: dict,
    ) -> list[BehaviorGenome]:
        """
        Select which genomes survive to the next generation.

        Uses elitism to preserve best genomes + fitness-proportionate selection.

        Args:
            population: Current population
            offspring: New offspring genomes
            context: Environmental context

        Returns:
            List of surviving genomes
        """
        # Combine population and offspring
        combined = population + offspring

        if len(combined) <= self.population_size:
            return combined

        # Calculate fitness for all genomes
        fitness_scores = [(g, self.evaluate_fitness(g, context)) for g in combined]

        # Sort by fitness (descending)
        fitness_scores.sort(key=lambda x: x[1], reverse=True)

        # Elitism: preserve top genomes
        num_elites = int(self.population_size * self.elitism_rate)
        elites = [g for g, _ in fitness_scores[:num_elites]]

        # Fill remaining slots with fitness-proportionate selection
        remaining = self.population_size - num_elites

        # Calculate selection probabilities
        total_fitness = sum(score for _, score in fitness_scores)
        if total_fitness <= 0:
            # Fallback to random selection
            survivors = self.rng.sample(combined, self.population_size)
            return survivors

        # Fitness-proportionate selection for remaining slots
        probabilities = [score / total_fitness for _, score in fitness_scores]
        non_elites = [g for g, _ in fitness_scores[num_elites:]]

        if remaining >= len(non_elites):
            survivors = elites + non_elites
        else:
            # Use weighted selection
            selected = self.rng.choices(
                non_elites,
                weights=probabilities[num_elites:],
                k=remaining,
            )
            survivors = elites + selected

        return survivors[:self.population_size]

    def enforce_diversity(
        self,
        population: list[BehaviorGenome],
        min_diversity: float | None = None,
    ) -> list[BehaviorGenome]:
        """
        Enforce minimum diversity in the population.

        If diversity falls below threshold, inject random genomes.

        Args:
            population: Current population
            min_diversity: Override diversity threshold

        Returns:
            Population with enforced diversity
        """
        if min_diversity is None:
            min_diversity = self.diversity_threshold

        current_diversity = self._calculate_diversity(population)

        if current_diversity >= min_diversity:
            return population

        # Diversity is too low - we need to inject variation
        from .genome import GenomeFactory

        num_to_add = int(len(population) * (min_diversity - current_diversity))
        num_to_add = max(1, min(num_to_add, 50))  # Limit injection

        new_genomes = [
            GenomeFactory.create_random_genome(rng=self.rng)
            for _ in range(num_to_add)
        ]

        # Replace some random genomes
        for new_g in new_genomes:
            if population:
                idx = self.rng.randint(0, len(population) - 1)
                population[idx] = new_g

        return population

    def _calculate_diversity(self, population: list[BehaviorGenome]) -> float:
        """
        Calculate genetic diversity of the population.

        Uses genotypic diversity: how different are the genomes?

        Returns:
            Diversity score (0-1, where 1 is maximally diverse)
        """
        if len(population) < 2:
            return 0.0

        # Calculate pairwise distance between genomes
        total_distance = 0.0
        num_comparisons = 0

        for i, g1 in enumerate(population):
            for g2 in population[i + 1:]:
                distance = self._genome_distance(g1, g2)
                total_distance += distance
                num_comparisons += 1

        if num_comparisons == 0:
            return 0.0

        avg_distance = total_distance / num_comparisons

        # Normalize to 0-1 (assuming max distance is ~10)
        return min(1.0, avg_distance / 10.0)

    def _genome_distance(self, g1: BehaviorGenome, g2: BehaviorGenome) -> float:
        """
        Calculate distance between two genomes.

        Uses structural similarity: genes, size, depth, etc.
        """
        distance = 0.0

        # Size difference
        size_diff = abs(g1.size() - g2.size())
        distance += size_diff * 0.1

        # Depth difference
        depth_diff = abs(g1.depth() - g2.depth())
        distance += depth_diff * 0.2

        # Gene type distribution
        genes1 = {g.gene_type for g in g1.get_all_genes()}
        genes2 = {g.gene_type for g in g2.get_all_genes()}
        symmetric_diff = len(genes1 ^ genes2)
        distance += symmetric_diff * 0.3

        # Unique innovations
        shared_innovations = len(g1.unique_innovations & g2.unique_innovations)
        total_innovations = len(g1.unique_innovations | g2.unique_innovations)
        if total_innovations > 0:
            innovation_diff = 1 - (shared_innovations / total_innovations)
            distance += innovation_diff * 0.4

        return distance

    def record_generation(
        self,
        population: list[BehaviorGenome],
        context: dict,
    ) -> None:
        """Record statistics for the current generation."""
        self.generation += 1

        fitness_scores = [self.evaluate_fitness(g, context) for g in population]
        avg_fitness = sum(fitness_scores) / len(fitness_scores) if fitness_scores else 0
        best_fitness = max(fitness_scores) if fitness_scores else 0
        diversity = self._calculate_diversity(population)

        self.best_fitness_history.append(best_fitness)
        self.avg_fitness_history.append(avg_fitness)
        self.diversity_history.append(diversity)

    def get_statistics(self) -> dict:
        """Get selection engine statistics."""
        return {
            "generation": self.generation,
            "best_fitness": self.best_fitness_history[-1] if self.best_fitness_history else 0,
            "avg_fitness": self.avg_fitness_history[-1] if self.avg_fitness_history else 0,
            "current_diversity": self.diversity_history[-1] if self.diversity_history else 0,
            "total_extinctions": self.extinctions,
            "fitness_trend": self._calculate_trend(self.best_fitness_history),
        }

    def _calculate_trend(self, history: list[float]) -> str:
        """Calculate trend direction from history."""
        if len(history) < 10:
            return "insufficient_data"

        recent = history[-10:]
        first_half = sum(recent[:5]) / 5
        second_half = sum(recent[5:]) / 5

        if second_half > first_half * 1.05:
            return "improving"
        elif second_half < first_half * 0.95:
            return "declining"
        else:
            return "stable"


# =============================================================================
# Common Fitness Functions
# =============================================================================

def survival_fitness(genome: BehaviorGenome, context: dict) -> float:
    """
    Fitness based on survival metrics.

    Agents that survive longer and stay healthy get higher fitness.
    """
    age = genome.age
    health = context.get("agent_health", 1.0)
    energy = context.get("agent_energy", 1.0)

    # Longer lifespan is better, but with diminishing returns
    age_fitness = min(1.0, age / 1000.0)

    # Health and energy contribute
    state_fitness = (health + energy) / 2

    return 0.6 * age_fitness + 0.4 * state_fitness


def reproduction_fitness(genome: BehaviorGenome, context: dict) -> float:
    """
    Fitness based on reproductive success.

    Agents that produce more offspring get higher fitness.
    """
    offspring_count = context.get("offspring_count", 0)
    children_alive = context.get("children_alive", 0)

    # More offspring is better
    offspring_fitness = min(1.0, offspring_count / 10.0)

    # Children surviving is even better
    survival_fitness = min(1.0, children_alive / 5.0)

    return 0.5 * offspring_fitness + 0.5 * survival_fitness


def social_fitness(genome: BehaviorGenome, context: dict) -> float:
    """
    Fitness based on social success.

    Agents with more social connections and higher status get higher fitness.
    """
    relationships = context.get("relationship_count", 0)
    reputation = context.get("reputation", 0.5)
    org_membership = context.get("organization_count", 0)

    # Normalize
    relationship_fitness = min(1.0, relationships / 20.0)
    org_fitness = min(1.0, org_membership / 5.0)

    return 0.4 * relationship_fitness + 0.3 * reputation + 0.3 * org_fitness


def economic_fitness(genome: BehaviorGenome, context: dict) -> float:
    """
    Fitness based on economic success.

    Agents with more resources and wealth get higher fitness.
    """
    resources = context.get("resource_count", 0)
    wealth = context.get("wealth", 0)
    surplus = context.get("surplus", 0)

    # Balance between having enough and having surplus
    resource_fitness = min(1.0, resources / 50.0)
    surplus_fitness = min(1.0, surplus / 20.0)

    return 0.6 * resource_fitness + 0.4 * surplus_fitness


def social_security_fitness(genome: BehaviorGenome, context: dict) -> float:
    """
    Fitness for behaviors that contribute to social welfare.

    This is NOT hardcoded social security - it's fitness for:
    - Sharing resources
    - Helping others
    - Building cooperative structures

    Agents that develop these behaviors may spontaneously create
    social security-like institutions over generations.
    """
    sharing_behavior = context.get("sharing_count", 0)
    helping_behavior = context.get("helping_count", 0)
    cooperative_builds = context.get("cooperative_structures", 0)

    # These behaviors indicate tendency toward collective welfare
    sharing_fitness = min(1.0, sharing_behavior / 10.0)
    helping_fitness = min(1.0, helping_behavior / 10.0)
    cooperative_fitness = min(1.0, cooperative_builds / 5.0)

    return (sharing_fitness + helping_fitness + cooperative_fitness) / 3


def environment_fitness(genome: BehaviorGenome, context: dict) -> float:
    """
    Fitness based on environmental adaptation.

    Agents that adapt to their environment get higher fitness.
    """
    env_match = context.get("environment_match", 0.5)
    resource_efficiency = context.get("resource_efficiency", 0.5)

    return 0.5 * env_match + 0.5 * resource_efficiency
