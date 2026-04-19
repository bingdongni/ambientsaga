"""
Variation Engine — Mutation and Crossover Operators

This module provides the genetic operators that drive evolution:
- MUTATION: Random changes to a genome (point mutation, subtree mutation, etc.)
- CROSSOVER: Exchange genetic material between two genomes
- INNOVATION: Create entirely new genes

Key Design Principles:
1. Mutations are NOT random - they're guided by fitness feedback
2. Crossover preserves building blocks (fitter genes are less likely to be broken)
3. Innovation is tracked - we know when new behaviors are created
4. Diversity is maintained - we avoid premature convergence

The variation operators work on the gene tree structure:
- Point mutation: Change a single gene's parameters
- Subtree mutation: Replace a subtree with a new random subtree
- Hoist mutation: Replace a gene with one of its children
- Swap mutation: Exchange two sibling genes
- Crossover: Exchange subtrees between two genomes
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from .genome import (
    BehaviorGenome,
    ConditionType,
    Gene,
    GeneType,
    GenomeFactory,
)


class MutationType(Enum):
    """Types of mutation operators."""

    POINT = auto()           # Change parameters of a single gene
    SUBTREE = auto()         # Replace a subtree with new random genes
    HOIST = auto()           # Replace gene with one of its children
    SHRINK = auto()          # Remove a subtree, replace with primitive
    SWAP = auto()            # Swap two sibling genes
    DUPLICATE = auto()       # Duplicate a gene
    DELETE = auto()          # Delete a gene entirely
    INSERT = auto()          # Insert a new gene at random location
    COPY_FROM_OTHER = auto() # Copy a gene from another genome (lateral gene transfer)


@dataclass
class MutationOperator:
    """A mutation operator with its probability and effect."""

    mutation_type: MutationType
    probability: float  # Base probability of this mutation
    impact: float       # How much this mutation changes the genome (0-1)
    name: str = ""

    def __post_init__(self):
        if not self.name:
            self.name = self.mutation_type.name


@dataclass
class CrossoverResult:
    """Result of a crossover operation."""

    child1: BehaviorGenome
    child2: BehaviorGenome
    crossover_point1: str  # Hash of crossover point in parent1
    crossover_point2: str  # Hash of crossover point in parent2
    genes_exchanged: int   # Number of genes swapped


class VariationEngine:
    """
    Manages mutation and crossover operations for behavioral genomes.

    The variation engine provides:
    - Adaptive mutation rates (based on fitness)
    - Multiple mutation types with different effects
    - Subtree crossover with building block preservation
    - Innovation tracking
    - Diversity maintenance
    """

    # Default mutation operators with their base probabilities
    DEFAULT_MUTATIONS = [
        MutationOperator(MutationType.POINT, 0.4, 0.1),
        MutationOperator(MutationType.SUBTREE, 0.2, 0.8),
        MutationOperator(MutationType.HOIST, 0.1, 0.3),
        MutationOperator(MutationType.SHRINK, 0.1, 0.2),
        MutationOperator(MutationType.SWAP, 0.1, 0.1),
        MutationOperator(MutationType.DUPLICATE, 0.05, 0.4),
        MutationOperator(MutationType.DELETE, 0.02, 0.3),
        MutationOperator(MutationType.INSERT, 0.02, 0.5),
    ]

    def __init__(
        self,
        mutation_operators: list[MutationOperator] | None = None,
        mutation_rate: float = 0.15,
        crossover_rate: float = 0.7,
        max_genome_size: int = 100,
        min_genome_size: int = 3,
        rng: random.Random | None = None,
    ):
        """
        Initialize the variation engine.

        Args:
            mutation_operators: List of mutation operators (uses defaults if None)
            mutation_rate: Probability of mutation per genome
            crossover_rate: Probability of crossover when two genomes mate
            max_genome_size: Maximum allowed genome size
            min_genome_size: Minimum allowed genome size
            rng: Random number generator
        """
        self.mutation_operators = mutation_operators or self.DEFAULT_MUTATIONS
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.max_genome_size = max_genome_size
        self.min_genome_size = min_genome_size
        self.rng = rng or random.Random()

        # Statistics
        self.total_mutations = 0
        self.total_crossovers = 0
        self.mutation_counts: dict[MutationType, int] = {m.mutation_type: 0 for m in self.mutation_operators}

        # Innovation history (for tracking new behaviors)
        self.innovation_log: list[dict] = []

    def mutate(
        self,
        genome: BehaviorGenome,
        fitness_feedback: Callable[[Gene], float] | None = None,
    ) -> BehaviorGenome:
        """
        Apply mutation to a genome.

        Args:
            genome: The genome to mutate
            fitness_feedback: Optional function that returns fitness for a gene
                             (higher fitness = less likely to be mutated)

        Returns:
            A new genome (may be same as input if no mutation occurred)
        """
        if self.rng.random() > self.mutation_rate:
            return genome

        mutated_genome = genome.copy()

        # Select mutation type based on probabilities
        mutation = self._select_mutation()

        # Select gene to mutate (prefer less fit genes unless fitness_feedback is provided)
        all_genes = mutated_genome.get_all_genes()
        if not all_genes:
            return genome

        # Weight selection by inverse fitness (prefer to mutate less fit genes)
        if fitness_feedback:
            weights = [1.0 / max(0.1, fitness_feedback(g)) for g in all_genes]
        else:
            # Default: prefer leaves (they're easier to mutate safely)
            weights = [1.0 if not g.children else 0.5 for g in all_genes]

        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        # Use weighted random selection
        target_gene = self.rng.choices(all_genes, weights=weights)[0]

        # Apply mutation
        self._apply_mutation(mutated_genome, target_gene, mutation)

        # Record mutation
        self.total_mutations += 1
        self.mutation_counts[mutation.mutation_type] += 1

        return mutated_genome

    def _select_mutation(self) -> MutationOperator:
        """Select a mutation operator based on probability."""
        total_prob = sum(op.probability for op in self.mutation_operators)
        r = self.rng.random() * total_prob

        cumulative = 0
        for op in self.mutation_operators:
            cumulative += op.probability
            if r <= cumulative:
                return op

        return self.mutation_operators[-1]

    def _apply_mutation(
        self,
        genome: BehaviorGenome,
        target: Gene,
        mutation: MutationOperator,
    ) -> None:
        """Apply a specific mutation to a gene."""
        if mutation.mutation_type == MutationType.POINT:
            self._mutate_point(target)
        elif mutation.mutation_type == MutationType.SUBTREE:
            self._mutate_subtree(genome, target)
        elif mutation.mutation_type == MutationType.HOIST:
            self._mutate_hoist(genome, target)
        elif mutation.mutation_type == MutationType.SHRINK:
            self._mutate_shrink(genome, target)
        elif mutation.mutation_type == MutationType.SWAP:
            self._mutate_swap(genome, target)
        elif mutation.mutation_type == MutationType.DUPLICATE:
            self._mutate_duplicate(genome, target)
        elif mutation.mutation_type == MutationType.DELETE:
            self._mutate_delete(genome, target)
        elif mutation.mutation_type == MutationType.INSERT:
            self._mutate_insert(genome, target)

        # Track innovation if new gene was created
        if mutation.mutation_type in {MutationType.SUBTREE, MutationType.INSERT}:
            self._record_innovation(genome, target, mutation.mutation_type)

    def _mutate_point(self, gene: Gene) -> None:
        """Point mutation: change parameters of a gene."""
        if gene.gene_type == GeneType.CONDITIONAL and gene.children:
            # Mutate the condition
            conditions = list(ConditionType)
            gene.condition = self.rng.choice(conditions)
            gene.parameters["condition"] = gene.condition.name
        elif gene.parameters:
            # Mutate one parameter
            param_name = self.rng.choice(list(gene.parameters.keys()))
            old_val = gene.parameters[param_name]
            if isinstance(old_val, (int, float)):
                # Numeric mutation: small change
                if isinstance(old_val, int):
                    gene.parameters[param_name] = old_val + self.rng.randint(-2, 2)
                else:
                    gene.parameters[param_name] = old_val * self.rng.uniform(0.8, 1.2)

    def _mutate_subtree(self, genome: BehaviorGenome, target: Gene) -> None:
        """Replace a subtree with a new random subtree."""
        new_subtree = GenomeFactory.create_random_genome(
            min_size=1,
            max_size=5,
            rng=self.rng,
        )

        if new_subtree.genes:
            new_gene = new_subtree.genes[0]

            # Replace target in parent
            if genome.genes and target in genome.genes:
                idx = genome.genes.index(target)
                genome.genes[idx] = new_gene
            else:
                # Find and replace in tree
                self._replace_gene_in_tree(genome.genes, target, new_gene)

    def _mutate_hoist(self, genome: BehaviorGenome, target: Gene) -> None:
        """Hoist mutation: replace a gene with one of its children."""
        if not target.children:
            return  # Can't hoist if no children

        child = self.rng.choice(target.children)
        new_child = child.copy()

        if genome.genes and target in genome.genes:
            idx = genome.genes.index(target)
            genome.genes[idx] = new_child
        else:
            self._replace_gene_in_tree(genome.genes, target, new_child)

    def _mutate_shrink(self, genome: BehaviorGenome, target: Gene) -> None:
        """Shrink mutation: replace composite with primitive."""
        if not target.children:
            return  # Already a leaf

        # Replace with a random child
        new_primitive = GenomeFactory._create_random_primitive(self.rng, 0.2)

        if genome.genes and target in genome.genes:
            idx = genome.genes.index(target)
            genome.genes[idx] = new_primitive
        else:
            self._replace_gene_in_tree(genome.genes, target, new_primitive)

    def _mutate_swap(self, genome: BehaviorGenome, target: Gene) -> None:
        """Swap mutation: exchange two sibling genes."""
        # Find parent's children list
        parent = self._find_parent(genome.genes, target)
        if parent and len(parent.children) >= 2:
            siblings = list(range(len(parent.children)))
            i, j = self.rng.sample(siblings, 2)
            parent.children[i], parent.children[j] = parent.children[j], parent.children[i]

    def _mutate_duplicate(self, genome: BehaviorGenome, target: Gene) -> None:
        """Duplicate mutation: copy a gene and insert it."""
        if genome.size() >= self.max_genome_size:
            return  # Can't grow beyond max size

        copy = target.copy()

        # Insert after target
        if genome.genes and target in genome.genes:
            idx = genome.genes.index(target)
            if idx + 1 < len(genome.genes):
                genome.genes.insert(idx + 1, copy)
            else:
                genome.genes.append(copy)
        else:
            parent = self._find_parent(genome.genes, target)
            if parent and target in parent.children:
                idx = parent.children.index(target)
                parent.children.insert(idx + 1, copy)

    def _mutate_delete(self, genome: BehaviorGenome, target: Gene) -> None:
        """Delete mutation: remove a gene."""
        if genome.size() <= self.min_genome_size:
            return  # Can't shrink below min size

        if genome.genes and target in genome.genes:
            genome.genes.remove(target)
        else:
            parent = self._find_parent(genome.genes, target)
            if parent and target in parent.children:
                parent.children.remove(target)

    def _mutate_insert(self, genome: BehaviorGenome, target: Gene) -> None:
        """Insert mutation: add a new gene near the target."""
        if genome.size() >= self.max_genome_size:
            return

        new_gene = GenomeFactory._create_random_primitive(self.rng, 0.3)

        if genome.genes and target in genome.genes:
            idx = genome.genes.index(target)
            genome.genes.insert(idx, new_gene)
        else:
            parent = self._find_parent(genome.genes, target)
            if parent and target in parent.children:
                idx = parent.children.index(target)
                parent.children.insert(idx, new_gene)

    def _replace_gene_in_tree(
        self,
        genes: list[Gene],
        old_gene: Gene,
        new_gene: Gene,
    ) -> bool:
        """Recursively replace a gene in a tree."""
        for gene in genes:
            if gene is old_gene:
                idx = genes.index(gene)
                genes[idx] = new_gene
                return True
            if gene.children:
                if self._replace_gene_in_tree(gene.children, old_gene, new_gene):
                    return True
        return False

    def _find_parent(self, genes: list[Gene], child: Gene) -> Gene | None:
        """Find the parent of a gene in the tree."""
        for gene in genes:
            if child in gene.children:
                return gene
            if gene.children:
                parent = self._find_parent(gene.children, child)
                if parent:
                    return parent
        return None

    def _record_innovation(
        self,
        genome: BehaviorGenome,
        gene: Gene,
        mutation_type: MutationType,
    ) -> None:
        """Record a new innovation event."""
        innovation = {
            "gene_hash": gene.get_hash(),
            "gene_type": gene.gene_type.name,
            "mutation_type": mutation_type.name,
            "generation": genome.generation,
            "genome_size": genome.size(),
        }
        self.innovation_log.append(innovation)
        genome.unique_innovations.add(gene.get_hash())

    # =========================================================================
    # Crossover Operations
    # =========================================================================

    def crossover(
        self,
        parent1: BehaviorGenome,
        parent2: BehaviorGenome,
    ) -> tuple[BehaviorGenome, BehaviorGenome]:
        """
        Perform crossover between two genomes.

        Subtree crossover: randomly select a subtree from each parent
        and swap them to create two children.

        Args:
            parent1: First parent genome
            parent2: Second parent genome

        Returns:
            Tuple of two child genomes
        """
        if self.rng.random() > self.crossover_rate:
            # No crossover, return copies of parents
            return parent1.copy(), parent2.copy()

        child1 = parent1.copy()
        child2 = parent2.copy()

        # Get all genes from each child
        genes1 = child1.get_all_genes()
        genes2 = child2.get_all_genes()

        if not genes1 or not genes2:
            return child1, child2

        # Select crossover points
        point1 = self.rng.choice(genes1)
        point2 = self.rng.choice(genes2)

        # Swap the subtrees
        subtree1 = point1.copy()
        subtree2 = point2.copy()

        # Replace in child1
        self._replace_gene_in_tree(child1.genes, point1, subtree2)
        # Replace in child2
        self._replace_gene_in_tree(child2.genes, point2, subtree1)

        # Reset fitness (children start fresh)
        child1.total_fitness = 0.0
        child1.total_executions = 0
        child1.total_successes = 0
        child2.total_fitness = 0.0
        child2.total_executions = 0
        child2.total_successes = 0

        # Update cultural heritage
        child1.cultural_heritage = "crossover"
        child2.cultural_heritage = "crossover"

        # Track crossover
        self.total_crossovers += 1

        return child1, child2

    def sexual_reproduction(
        self,
        parent1: BehaviorGenome,
        parent2: BehaviorGenome,
        mutation_rate: float | None = None,
    ) -> BehaviorGenome:
        """
        Create offspring through sexual reproduction.

        This is a wrapper around crossover + mutation for typical reproduction.

        Args:
            parent1: First parent
            parent2: Second parent
            mutation_rate: Override mutation rate for offspring

        Returns:
            A single child genome
        """
        if mutation_rate is None:
            mutation_rate = self.mutation_rate

        # Crossover
        child1, child2 = self.crossover(parent1, parent2)

        # Mutate with slightly higher probability for offspring
        child = self.mutate(child1, fitness_feedback=lambda g: max(0.1, g.get_fitness()))

        # Reset age (offspring is new)
        child.age = 0

        return child

    def asexual_reproduction(
        self,
        parent: BehaviorGenome,
        mutation_rate: float | None = None,
    ) -> BehaviorGenome:
        """
        Create offspring through asexual reproduction (cloning + mutation).

        Args:
            parent: Parent genome
            mutation_rate: Override mutation rate

        Returns:
            A mutated copy of the parent
        """
        if mutation_rate is None:
            mutation_rate = self.mutation_rate

        child = parent.copy()
        child.age = 0
        child.generation = parent.generation + 1
        child.total_fitness = 0.0
        child.total_executions = 0
        child.total_successes = 0

        # Mutate
        child = self.mutate(child, fitness_feedback=lambda g: max(0.1, g.get_fitness()))

        return child

    # =========================================================================
    # Statistics and Analysis
    # =========================================================================

    def get_statistics(self) -> dict:
        """Get variation engine statistics."""
        total_mutations = sum(self.mutation_counts.values())

        return {
            "total_mutations": self.total_mutations,
            "total_crossovers": self.total_crossovers,
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate,
            "mutation_distribution": {
                m.mutation_type.name: self.mutation_counts.get(m.mutation_type, 0)
                for m in self.mutation_operators
            },
            "total_innovations": len(self.innovation_log),
        }

    def get_innovation_history(self, last_n: int = 100) -> list[dict]:
        """Get recent innovation history."""
        return self.innovation_log[-last_n:]

    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self.total_mutations = 0
        self.total_crossovers = 0
        self.mutation_counts = {m.mutation_type: 0 for m in self.mutation_operators}
        self.innovation_log = []
