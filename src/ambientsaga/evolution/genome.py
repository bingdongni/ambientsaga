"""
Behavioral Genome — The Evolvable Behavioral Program

Each agent has a GENOME that defines its behavior. The genome is a tree of genes,
where genes can be:
- PRIMITIVE: Atomic actions (MOVE, EXCHANGE, BUILD, etc.)
- CONDITIONAL: If-then-else based on perception
- SEQUENCE: Do A, then B, then C
- PARALLEL: Do A and B simultaneously
- LOOP: Repeat behavior N times

The genome evolves through mutation and crossover, allowing agents to develop
novel behaviors over time.

Key Insight: The genome is NOT the agent's identity - it's a behavioral strategy
that can be copied, mutated, and selected upon. Two agents with different genomes
can have the same identity, just different behaviors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional
import hashlib
import random


class GeneType(Enum):
    """Types of genes in the behavioral genome."""

    # Primitives (leaf nodes)
    MOVE = auto()
    REST = auto()
    EAT = auto()
    DRINK = auto()
    BUILD = auto()
    EXCHANGE = auto()
    ATTACK = auto()
    FLEE = auto()
    FOLLOW = auto()
    GATHER = auto()
    CRAFT = auto()
    TEACH = auto()
    LEARN = auto()
    REPRODUCE = auto()
    DIE = auto()

    # Composites (branch nodes)
    SEQUENCE = auto()      # Execute children in order
    PARALLEL = auto()      # Execute children simultaneously
    CONDITIONAL = auto()   # If condition then child1 else child2
    LOOP = auto()          # Repeat child N times
    RANDOM = auto()        # Execute random child
    PRIORITY = auto()       # Try first child, if fails try next

    # Sensory
    PERCEIVE = auto()      # Gather perception data
    MEMORIZE = auto()      # Store information
    RECALL = auto()         # Retrieve stored information

    # Social
    GREET = auto()          # Initiate friendly contact
    TRADE = auto()          # Exchange resources
    SHARE = auto()          # Give resources to others
    PUNISH = auto()         # Penalize bad behavior
    REWARD = auto()         # Reward good behavior
    NEGOTIATE = auto()      # Bargain for agreement
    DECLARE = auto()        # Make public announcement
    PROPOSE = auto()        # Suggest joint action

    # Meta (for evolution)
    COPY_STRATEGY = auto()  # Copy another agent's behavior
    INNOVATE = auto()       # Create novel behavior


class ConditionType(Enum):
    """Conditions for CONDITIONAL genes."""

    IF_SEE_AGENT = auto()
    IF_SEE_FOOD = auto()
    IF_LOW_ENERGY = auto()
    IF_LOW_WATER = auto()
    IF_IN_DANGER = auto()
    IF_HAS_RESOURCE = auto()
    IF_SEES_STRANGER = auto()
    IF_FRIEND_NEARBY = auto()
    IF_ENEMY_NEARBY = auto()
    IF_OWNER_NEARBY = auto()
    IF_TOOL_NEARBY = auto()
    IF_SHELTER_NEARBY = auto()
    IF_TIRED = auto()
    IF_LONELY = auto()
    IF_HAS_SURPLUS = auto()
    IF_PARTNER_NEARBY = auto()
    IF_CHILD_NEARBY = auto()
    IF_LANDMARK_NEARBY = auto()
    IF_TERRITORY_BORDER = auto()
    IF_RICH = auto()
    IF_POOR = auto()
    IF_SICK = auto()
    IF_INJURED = auto()


@dataclass
class Gene:
    """Base class for all genes in the behavioral genome."""

    gene_type: GeneType
    parameters: dict[str, Any] = field(default_factory=dict)
    children: list[Gene] = field(default_factory=list)
    fitness_score: float = 0.0  # Accumulated fitness from execution history
    execution_count: int = 0   # Number of times this gene was executed
    success_count: int = 0     # Number of successful executions
    innovation_time: int = 0   # Tick when this gene was first created

    def size(self) -> int:
        """Return the total number of genes in this subtree."""
        return 1 + sum(child.size() for child in self.children)

    def depth(self) -> int:
        """Return the depth of this gene in the tree."""
        if not self.children:
            return 1
        return 1 + max(child.depth() for child in self.children)

    def copy(self) -> Gene:
        """Create a deep copy of this gene."""
        new_gene = Gene(
            gene_type=self.gene_type,
            parameters=self.parameters.copy(),
            fitness_score=self.fitness_score,
            execution_count=self.execution_count,
            success_count=self.success_count,
            innovation_time=self.innovation_time,
        )
        new_gene.children = [child.copy() for child in self.children]
        return new_gene

    def get_hash(self) -> str:
        """Get a unique hash for this gene (for crossover tracking)."""
        content = f"{self.gene_type.name}:{self.parameters}:{[c.get_hash() for c in self.children]}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def to_string(self, indent: int = 0) -> str:
        """Create a human-readable string representation."""
        prefix = "  " * indent
        params_str = f"({', '.join(f'{k}={v}' for k, v in self.parameters.items())})" if self.parameters else ""
        child_str = ""
        if self.children:
            child_str = "\n" + "\n".join(c.to_string(indent + 1) for c in self.children)
        return f"{prefix}{self.gene_type.name}{params_str}{child_str}"

    def record_execution(self, success: bool) -> None:
        """Record that this gene was executed."""
        self.execution_count += 1
        if success:
            self.success_count += 1

    def get_success_rate(self) -> float:
        """Get the success rate of this gene."""
        if self.execution_count == 0:
            return 0.5  # Default optimistic rate
        return self.success_count / self.execution_count

    def get_fitness(self) -> float:
        """Get the normalized fitness of this gene."""
        return self.fitness_score / max(1, self.execution_count)


@dataclass
class PrimitiveGene(Gene):
    """A primitive gene representing a single atomic action."""

    def __init__(
        self,
        action: GeneType,
        parameters: Optional[dict[str, Any]] = None,
    ):
        # Validate that this is a primitive type
        if action not in {
            GeneType.MOVE, GeneType.REST, GeneType.EAT, GeneType.DRINK,
            GeneType.BUILD, GeneType.EXCHANGE, GeneType.ATTACK, GeneType.FLEE,
            GeneType.FOLLOW, GeneType.GATHER, GeneType.CRAFT, GeneType.TEACH,
            GeneType.LEARN, GeneType.REPRODUCE, GeneType.DIE,
            GeneType.GREET, GeneType.TRADE, GeneType.SHARE, GeneType.PUNISH,
            GeneType.REWARD, GeneType.NEGOTIATE, GeneType.DECLARE, GeneType.PROPOSE,
            GeneType.PERCEIVE, GeneType.MEMORIZE, GeneType.RECALL,
            GeneType.COPY_STRATEGY, GeneType.INNOVATE,
        }:
            raise ValueError(f"{action} is not a primitive gene type")
        super().__init__(gene_type=action, parameters=parameters or {})


@dataclass
class ConditionalGene(Gene):
    """A conditional gene that executes different children based on a condition."""

    condition: ConditionType = ConditionType.IF_SEE_AGENT
    threshold: float = 0.5  # Threshold for numeric conditions

    def __init__(
        self,
        condition: ConditionType,
        then_child: Optional[Gene] = None,
        else_child: Optional[Gene] = None,
    ):
        super().__init__(
            gene_type=GeneType.CONDITIONAL,
            parameters={"condition": condition.name, "threshold": self.threshold},
        )
        if then_child:
            self.children.append(then_child)
        if else_child:
            self.children.append(else_child)

    def evaluate_condition(self, perception: dict) -> bool:
        """Evaluate if the condition is met given current perception."""
        cond = self.condition

        # Helper to get perception value
        def get_val(key: str, default: Any = 0) -> Any:
            return perception.get(key, default)

        if cond == ConditionType.IF_SEE_AGENT:
            return get_val("nearby_agents", 0) > 0
        elif cond == ConditionType.IF_SEE_FOOD:
            return get_val("food_nearby", 0) > 0
        elif cond == ConditionType.IF_LOW_ENERGY:
            return get_val("energy", 1.0) < self.threshold
        elif cond == ConditionType.IF_LOW_WATER:
            return get_val("water", 1.0) < self.threshold
        elif cond == ConditionType.IF_IN_DANGER:
            return get_val("danger_level", 0) > self.threshold
        elif cond == ConditionType.IF_HAS_RESOURCE:
            return get_val("resource_count", 0) >= self.threshold
        elif cond == ConditionType.IF_SEES_STRANGER:
            return get_val("strangers_nearby", 0) > 0
        elif cond == ConditionType.IF_FRIEND_NEARBY:
            return get_val("friends_nearby", 0) > 0
        elif cond == ConditionType.IF_ENEMY_NEARBY:
            return get_val("enemies_nearby", 0) > 0
        elif cond == ConditionType.IF_OWNER_NEARBY:
            return get_val("owners_nearby", 0) > 0
        elif cond == ConditionType.IF_TOOL_NEARBY:
            return get_val("tools_nearby", 0) > 0
        elif cond == ConditionType.IF_SHELTER_NEARBY:
            return get_val("shelter_nearby", 0) > 0
        elif cond == ConditionType.IF_TIRED:
            return get_val("energy", 1.0) < 0.3
        elif cond == ConditionType.IF_LONELY:
            return get_val("social_connections", 0) < 2
        elif cond == ConditionType.IF_HAS_SURPLUS:
            return get_val("surplus", 0) > self.threshold
        elif cond == ConditionType.IF_PARTNER_NEARBY:
            return get_val("partner_nearby", False)
        elif cond == ConditionType.IF_CHILD_NEARBY:
            return get_val("children_nearby", 0) > 0
        elif cond == ConditionType.IF_LANDMARK_NEARBY:
            return get_val("landmark_distance", float('inf')) < 50
        elif cond == ConditionType.IF_TERRITORY_BORDER:
            return get_val("at_border", False)
        elif cond == ConditionType.IF_RICH:
            return get_val("wealth", 0) > get_val("avg_wealth", 1.0)
        elif cond == ConditionType.IF_POOR:
            return get_val("wealth", 0) < get_val("avg_wealth", 1.0) * 0.5
        elif cond == ConditionType.IF_SICK:
            return get_val("health", 1.0) < 0.7
        elif cond == ConditionType.IF_INJURED:
            return get_val("health", 1.0) < 0.5

        return False


@dataclass
class SequenceGene(Gene):
    """A sequence gene that executes children in order."""

    def __init__(self, children: Optional[list[Gene]] = None):
        super().__init__(gene_type=GeneType.SEQUENCE, children=children or [])


@dataclass
class CompositeGene(Gene):
    """A composite gene that executes multiple children in a specific way."""

    execution_mode: str = "sequence"  # sequence, parallel, priority, random

    def __init__(
        self,
        gene_type: GeneType,
        children: Optional[list[Gene]] = None,
        execution_mode: str = "sequence",
    ):
        if gene_type not in {GeneType.SEQUENCE, GeneType.PARALLEL, GeneType.RANDOM, GeneType.PRIORITY}:
            raise ValueError(f"{gene_type} is not a composite gene type")
        super().__init__(
            gene_type=gene_type,
            parameters={"mode": execution_mode},
            children=children or [],
        )


@dataclass
class BehaviorGenome:
    """
    The complete behavioral genome of an agent.

    The genome consists of:
    - genes: A list of root-level genes (strategy components)
    - memory: Evolvable memory that stores learned associations
    - cultural_heritage: ID of the agent this was copied from (for tracking lineage)
    - generation: How many copies away from the original genome
    - innovation_counter: Unique ID for each innovation (gene creation event)

    The genome is executed by running each root gene in order.
    Each gene returns a success/failure status that affects fitness.
    """

    genes: list[Gene] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)  # Evolvable memory
    cultural_heritage: Optional[str] = None  # Agent ID this was copied from
    generation: int = 0
    innovation_counter: int = 0
    total_fitness: float = 0.0
    age: int = 0  # Number of ticks this genome has existed

    # Genome-level statistics
    total_executions: int = 0
    total_successes: int = 0

    # Track which behaviors are unique to this lineage
    unique_innovations: set[str] = field(default_factory=set)

    def size(self) -> int:
        """Total number of genes in this genome."""
        return sum(gene.size() for gene in self.genes)

    def depth(self) -> int:
        """Maximum depth of any gene in this genome."""
        if not self.genes:
            return 0
        return max(gene.depth() for gene in self.genes)

    def copy(self) -> BehaviorGenome:
        """Create a deep copy of this genome."""
        return BehaviorGenome(
            genes=[gene.copy() for gene in self.genes],
            memory=self.memory.copy(),
            cultural_heritage=None,  # Reset heritage on copy
            generation=self.generation + 1,
            innovation_counter=self.innovation_counter,
            total_fitness=0.0,  # Reset fitness on copy
            age=0,
            unique_innovations=self.unique_innovations.copy(),
        )

    def next_innovation_id(self) -> str:
        """Generate a unique ID for the next innovation."""
        self.innovation_counter += 1
        return f"innov_{self.innovation_counter}"

    def record_execution(self, gene_hash: str, success: bool, fitness_delta: float) -> None:
        """Record the execution of a gene."""
        self.total_executions += 1
        if success:
            self.total_successes += 1
        self.total_fitness += fitness_delta

        # Propagate fitness to ancestor genes
        self._propagate_fitness(fitness_delta)

    def _propagate_fitness(self, delta: float) -> None:
        """Propagate fitness changes up the gene tree."""
        for gene in self.genes:
            gene.fitness_score += delta * 0.9  # Slight decay for ancestors

    def get_average_fitness(self) -> float:
        """Get the average fitness per execution."""
        if self.total_executions == 0:
            return 0.5  # Default optimistic
        return self.total_fitness / self.total_executions

    def get_success_rate(self) -> float:
        """Get the overall success rate of this genome."""
        if self.total_executions == 0:
            return 0.5
        return self.total_successes / self.total_executions

    def to_string(self) -> str:
        """Create a human-readable string representation."""
        lines = [
            f"Genome(gen={self.generation}, age={self.age}, "
            f"fitness={self.get_average_fitness():.3f}, "
            f"size={self.size()}, depth={self.depth()})",
        ]
        for i, gene in enumerate(self.genes):
            lines.append(f"  [{i}] {gene.to_string(2)}")
        return "\n".join(lines)

    def get_all_genes(self) -> list[Gene]:
        """Get all genes in the genome as a flat list (for mutation selection)."""
        result = []
        for gene in self.genes:
            self._collect_genes(gene, result)
        return result

    def _collect_genes(self, gene: Gene, result: list[Gene]) -> None:
        """Recursively collect all genes."""
        result.append(gene)
        for child in gene.children:
            self._collect_genes(child, result)

    def get_gene_by_hash(self, gene_hash: str) -> Optional[Gene]:
        """Find a gene by its hash."""
        for gene in self.get_all_genes():
            if gene.get_hash() == gene_hash:
                return gene
        return None

    def evolve_age(self) -> None:
        """Increment the age of this genome."""
        self.age += 1

        # Apply age-based fitness penalty (genomes decay over time if not used)
        if self.age > 1000 and self.total_executions < self.age * 0.5:
            self.total_fitness *= 0.999  # Slight decay


# =============================================================================
# Genome Factory — Creates initial random genomes
# =============================================================================

class GenomeFactory:
    """Factory for creating initial random genomes."""

    # Primitive actions available to all agents
    PRIMITIVE_ACTIONS = [
        GeneType.MOVE, GeneType.REST, GeneType.GATHER, GeneType.EAT,
        GeneType.DRINK, GeneType.EXCHANGE, GeneType.GREET, GeneType.SHARE,
        GeneType.FLEE, GeneType.BUILD, GeneType.FOLLOW, GeneType.CRAFT,
        GeneType.PERCEIVE, GeneType.MEMORIZE, GeneType.RECALL,
    ]

    # Social behaviors (more complex)
    SOCIAL_ACTIONS = [
        GeneType.TRADE, GeneType.NEGOTIATE, GeneType.PROPOSE,
        GeneType.TEACH, GeneType.LEARN, GeneType.REWARD, GeneType.PUNISH,
    ]

    # Innovation actions
    INNOVATION_ACTIONS = [
        GeneType.COPY_STRATEGY, GeneType.INNOVATE,
    ]

    @classmethod
    def create_random_genome(
        cls,
        min_size: int = 5,
        max_size: int = 20,
        complexity_bias: float = 0.3,
        social_bias: float = 0.2,
        rng: Optional[random.Random] = None,
    ) -> BehaviorGenome:
        """Create a random genome with specified parameters.

        Args:
            min_size: Minimum number of genes
            max_size: Maximum number of genes
            complexity_bias: Probability of creating composite genes (0-1)
            social_bias: Probability of including social behaviors
            rng: Random number generator
        """
        if rng is None:
            rng = random.Random()

        genome = BehaviorGenome()

        target_size = rng.randint(min_size, max_size)
        current_size = 0

        while current_size < target_size:
            # Decide what type of gene to create
            r = rng.random()

            if r < complexity_bias and current_size > 2:
                # Create a composite gene
                gene = cls._create_random_composite(rng, complexity_bias, social_bias)
            else:
                # Create a primitive gene
                gene = cls._create_random_primitive(rng, social_bias)

            genome.genes.append(gene)
            current_size += gene.size()

        return genome

    @classmethod
    def _create_random_primitive(
        cls,
        rng: random.Random,
        social_bias: float,
    ) -> Gene:
        """Create a random primitive gene."""
        if rng.random() < social_bias:
            actions = cls.SOCIAL_ACTIONS + cls.PRIMITIVE_ACTIONS
        else:
            actions = cls.PRIMITIVE_ACTIONS

        action = rng.choice(actions)
        params = cls._random_parameters(action, rng)

        return PrimitiveGene(action, params)

    @classmethod
    def _create_random_composite(
        cls,
        rng: random.Random,
        complexity_bias: float,
        social_bias: float,
    ) -> Gene:
        """Create a random composite gene."""
        # Choose composite type
        composite_types = [
            GeneType.SEQUENCE,
            GeneType.CONDITIONAL,
            GeneType.RANDOM,
            GeneType.PRIORITY,
        ]
        composite_type = rng.choice(composite_types)

        if composite_type == GeneType.CONDITIONAL:
            # Create conditional gene
            condition = rng.choice(list(ConditionType))
            threshold = rng.uniform(0.1, 0.9)

            # Create then/else branches
            then_child = cls._create_random_primitive(rng, social_bias)
            else_child = cls._create_random_primitive(rng, social_bias)

            gene = ConditionalGene(condition, then_child, else_child)
            gene.parameters["threshold"] = threshold
            return gene

        else:
            # Create sequence/random/priority gene
            num_children = rng.randint(2, 4)
            children = []
            for _ in range(num_children):
                if rng.random() < complexity_bias:
                    child = cls._create_random_composite(rng, complexity_bias, social_bias)
                else:
                    child = cls._create_random_primitive(rng, social_bias)
                children.append(child)

            return CompositeGene(composite_type, children)

    @classmethod
    def _random_parameters(cls, action: GeneType, rng: random.Random) -> dict[str, Any]:
        """Generate random parameters for an action."""
        params = {}

        if action == GeneType.MOVE:
            params = {"direction": rng.choice(["north", "south", "east", "west", "random"])}
        elif action == GeneType.GATHER:
            params = {"resource_type": rng.choice(["food", "water", "wood", "stone"])}
        elif action == GeneType.EXCHANGE:
            params = {"give_resource": rng.choice(["food", "water"]), "amount": rng.randint(1, 5)}
        elif action == GeneType.SHARE:
            params = {"amount": rng.randint(1, 3)}
        elif action == GeneType.BUILD:
            params = {"structure_type": rng.choice(["shelter", "tool", "storage"])}
        elif action == GeneType.CRAFT:
            params = {"item_type": rng.choice(["tool", "weapon", "container"])}
        elif action == GeneType.TEACH:
            params = {"topic": rng.choice(["survival", "social", "craft"])}
        elif action == GeneType.LEARN:
            params = {"topic": rng.choice(["survival", "social", "craft"])}

        return params

    @classmethod
    def create_minimal_genome(cls) -> BehaviorGenome:
        """Create a minimal genome with just basic survival behaviors."""
        genome = BehaviorGenome()

        # Basic perceive -> move -> gather sequence
        perceive = PrimitiveGene(GeneType.PERCEIVE)
        move = PrimitiveGene(GeneType.MOVE)
        gather = PrimitiveGene(GeneType.GATHER)
        eat = PrimitiveGene(GeneType.EAT)

        sequence = SequenceGene([perceive, move, gather, eat])
        genome.genes.append(sequence)

        return genome

    @classmethod
    def create_social_genome(cls, rng: Optional[random.Random] = None) -> BehaviorGenome:
        """Create a genome biased towards social behaviors."""
        if rng is None:
            rng = random.Random()

        return cls.create_random_genome(
            min_size=8,
            max_size=25,
            complexity_bias=0.4,
            social_bias=0.6,
            rng=rng,
        )
