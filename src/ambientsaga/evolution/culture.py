"""
Culture Engine — Cultural Transmission and Strategy Sharing

This module handles the SOCIAL LEARNING component of evolution:
- Agents can OBSERVE other agents and COPY their successful behaviors
- Cultural transmission spreads successful strategies through the population
- Cultural evolution happens on a faster timescale than genetic evolution
- Novel ideas can spread rapidly through cultural channels

Key Concepts:
- OBSERVATION: An agent watches another agent's actions
- EVALUATION: The observer judges if the behavior is worth copying
- COPY: The observer adopts the behavior
- TEACHING: An agent actively shares its strategy
- IMITATION: Copying a successful peer's behavior
- INNOVATION: Creating a genuinely new behavior

The culture engine enables:
1. Vertical transmission: Parents teach children
2. Horizontal transmission: Peers learn from each other
3. Oblique transmission: Young learn from older non-parents
4. Cultural norms: Shared behaviors that spread through the population
5. Cultural institutions: Emergent social structures from cultural patterns
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict

from .genome import BehaviorGenome, Gene
from .variation import VariationEngine


@dataclass
class CulturalPattern:
    """
    A cultural pattern represents a behavior or idea that spreads through culture.

    Cultural patterns emerge from:
    - Successful individual innovations
    - Shared social norms
    - Common survival strategies
    - Emergent social institutions

    Patterns have:
    - name: Descriptive name (auto-generated)
    - gene_hashes: The genes that make up this pattern
    - frequency: How many agents have adopted this pattern
    - origin_tick: When this pattern first appeared
    - spread_rate: How fast it's spreading
    - stability: How stable this pattern is across generations
    """

    pattern_id: str
    gene_hashes: set[str]
    frequency: int = 0
    origin_tick: int = 0
    total_adopters: int = 0
    current_adopters: int = 0
    spread_rate: float = 0.0
    stability: float = 1.0  # How often it survives reproduction
    name: str = ""

    # Cultural metadata
    behavioral_components: list[str] = field(default_factory=list)
    social_context: str = ""  # "exchange", "cooperation", "competition", etc.


@dataclass
class CulturalEvent:
    """An event in the cultural history of the population."""

    event_type: str  # "observation", "copy", "teaching", "innovation", "norm_emergence"
    tick: int
    agent_id: str
    target_agent_id: Optional[str]
    pattern_id: Optional[str]
    gene_hash: Optional[str]
    success: bool
    details: dict = field(default_factory=dict)


class CultureEngine:
    """
    Manages cultural transmission between agents.

    The culture engine provides:
    - Observation and imitation
    - Teaching and learning
    - Cultural pattern tracking
    - Emergent norm detection
    - Cultural institution emergence

    Cultural evolution happens through:
    1. High-fidelity copying (exact copy of a gene)
    2. Selective copying (copy only successful parts)
    3. Blending (combine parts from multiple sources)
    4. Innovation (create new variations)
    """

    def __init__(
        self,
        variation_engine: Optional[VariationEngine] = None,
        observation_probability: float = 0.3,
        teaching_probability: float = 0.1,
        learning_probability: float = 0.5,
        imitation_bias: float = 0.8,
        prestige_bias: float = 0.3,
        cultural_mutation_rate: float = 0.05,
        rng: Optional[random.Random] = None,
    ):
        """
        Initialize the culture engine.

        Args:
            variation_engine: Engine for genetic variation
            observation_probability: Probability an agent observes another
            teaching_probability: Probability a successful agent teaches others
            learning_probability: Probability an observer copies what they see
            imitation_bias: Preference for copying peers vs. elites
            prestige_bias: Preference for copying successful agents
            cultural_mutation_rate: Rate of mutation during cultural transmission
            rng: Random number generator
        """
        self.variation_engine = variation_engine or VariationEngine(rng=rng)
        self.observation_probability = observation_probability
        self.teaching_probability = teaching_probability
        self.learning_probability = learning_probability
        self.imitation_bias = imitation_bias
        self.prestige_bias = prestige_bias
        self.cultural_mutation_rate = cultural_mutation_rate
        self.rng = rng or random.Random()

        # Cultural patterns (emergent behaviors that spread)
        self.patterns: dict[str, CulturalPattern] = {}

        # Cultural history (for analysis)
        self.cultural_events: list[CulturalEvent] = []

        # Norm tracking (emergent social expectations)
        self.emergent_norms: dict[str, float] = defaultdict(float)
        self.norm_frequency: dict[str, list[int]] = defaultdict(list)

        # Statistics
        self.total_observations = 0
        self.total_copies = 0
        self.total_teaching = 0
        self.total_innovations = 0

    def observe_and_learn(
        self,
        observer_genome: BehaviorGenome,
        observed_genome: BehaviorGenome,
        observed_success: float,
        observed_id: str,
        observer_id: str,
        tick: int,
        interaction_context: Optional[str] = None,
        require_success: bool = True,
    ) -> Optional[BehaviorGenome]:
        """
        An agent observes another agent and may learn from them.

        Args:
            observer_genome: Genome of the observing agent
            observed_genome: Genome of the observed agent
            observed_success: How successful the observed agent is (0-1)
            observed_id: ID of the observed agent
            observer_id: ID of the observing agent
            tick: Current simulation tick
            interaction_context: Context of the interaction
            require_success: If True, only copy when success is high enough.
                           If False, record observation but don't require success for copying.

        Returns:
            New genome if learning occurred, None otherwise
        """
        if self.rng.random() > self.observation_probability:
            return None

        self.total_observations += 1

        # If require_success is True, only copy when observed_success is high
        # If require_success is False, always try to copy with normal probability
        copy_probability = self.learning_probability if require_success else self.learning_probability * 0.8

        # Decide what to copy
        if self.rng.random() < self.imitation_bias:
            # Imitation: copy a random successful gene from observed
            return self._imitation(
                observer_genome,
                observed_genome,
                observed_success,
                observer_id,
                observed_id,
                tick,
                interaction_context,
                copy_probability=copy_probability,
            )
        else:
            # Selective copying: only copy genes that seem successful
            return self._selective_copying(
                observer_genome,
                observed_genome,
                observed_success,
                observer_id,
                observed_id,
                tick,
                interaction_context,
                copy_probability=copy_probability,
            )

    def _imitation(
        self,
        observer: BehaviorGenome,
        observed: BehaviorGenome,
        observed_success: float,
        observer_id: str,
        observed_id: str,
        tick: int,
        context: Optional[str],
        copy_probability: float = 0.5,
    ) -> Optional[BehaviorGenome]:
        """Copy a random gene from the observed agent."""
        if self.rng.random() > copy_probability:
            return None

        observed_genes = observed.get_all_genes()
        if not observed_genes:
            return None

        # Randomly select a gene to copy
        gene_to_copy = self.rng.choice(observed_genes)
        copied_gene = gene_to_copy.copy()

        # Create new genome with the copied gene
        new_genome = observer.copy()

        # Insert copied gene into the genome
        if len(new_genome.genes) < 5:
            new_genome.genes.append(copied_gene)
        else:
            # Insert at random position
            pos = self.rng.randint(0, len(new_genome.genes))
            new_genome.genes.insert(pos, copied_gene)

        # Cultural mutation (small probability of variation)
        if self.rng.random() < self.cultural_mutation_rate:
            new_genome = self.variation_engine.mutate(new_genome)

        # Record the event
        event = CulturalEvent(
            event_type="imitation",
            tick=tick,
            agent_id=observer_id,
            target_agent_id=observed_id,
            pattern_id=None,
            gene_hash=gene_to_copy.get_hash(),
            success=True,
            details={
                "observed_success": observed_success,
                "context": context or "unknown",
            },
        )
        self.cultural_events.append(event)
        self.total_copies += 1

        # Track pattern if gene is interesting
        self._track_cultural_pattern(gene_to_copy, observer_id, tick, context)

        return new_genome

    def _selective_copying(
        self,
        observer: BehaviorGenome,
        observed: BehaviorGenome,
        observed_success: float,
        observer_id: str,
        observed_id: str,
        tick: int,
        context: Optional[str],
        copy_probability: float = 0.5,
    ) -> Optional[BehaviorGenome]:
        """Only copy genes that are more successful than our own."""
        if self.rng.random() > copy_probability * observed_success:
            return None

        observer_genes = {g.gene_hash(): g for g in observer.get_all_genes()}
        observed_genes = observed.get_all_genes()

        # Find genes in observed that are better than ours
        better_genes = []
        for og in observed_genes:
            obs_hash = og.get_hash()
            if obs_hash in observer_genes:
                our_gene = observer_genes[obs_hash]
                if og.fitness_score > our_gene.fitness_score:
                    better_genes.append(og)
            else:
                # Gene doesn't exist in observer - definitely copy
                better_genes.append(og)

        if not better_genes:
            return None

        # Copy the best gene
        gene_to_copy = max(better_genes, key=lambda g: g.fitness_score)
        copied_gene = gene_to_copy.copy()

        # Create new genome
        new_genome = observer.copy()

        # Replace a random gene with the copied one (or add it)
        if len(new_genome.genes) > 0 and self.rng.random() < 0.5:
            # Replace existing gene
            idx = self.rng.randint(0, len(new_genome.genes) - 1)
            new_genome.genes[idx] = copied_gene
        else:
            # Add new gene
            new_genome.genes.append(copied_gene)

        # Cultural mutation
        if self.rng.random() < self.cultural_mutation_rate:
            new_genome = self.variation_engine.mutate(new_genome)

        # Record event
        event = CulturalEvent(
            event_type="selective_copy",
            tick=tick,
            agent_id=observer_id,
            target_agent_id=observed_id,
            pattern_id=None,
            gene_hash=gene_to_copy.get_hash(),
            success=True,
            details={
                "observed_success": observed_success,
                "genes_copied": 1,
                "context": context or "unknown",
            },
        )
        self.cultural_events.append(event)
        self.total_copies += 1

        # Track pattern
        self._track_cultural_pattern(gene_to_copy, observer_id, tick, context)

        return new_genome

    def teach(
        self,
        teacher_genome: BehaviorGenome,
        teacher_id: str,
        learner_genome: BehaviorGenome,
        learner_id: str,
        tick: int,
        context: Optional[str] = None,
    ) -> Optional[BehaviorGenome]:
        """
        Active teaching: an agent deliberately shares knowledge.

        Unlike passive observation, teaching involves:
        - Selecting the best genes to share
        - Possibly explaining or demonstrating
        - Verifying the learner has copied correctly

        Args:
            teacher_genome: Genome of the teaching agent
            teacher_id: ID of the teacher
            learner_genome: Current genome of the learner
            learner_id: ID of the learner
            tick: Current tick

        Returns:
            New genome for the learner if teaching was successful
        """
        if self.rng.random() > self.teaching_probability:
            return None

        # Teaching is more effective than passive observation
        success_prob = self.learning_probability * 1.5  # Boost for active teaching
        if self.rng.random() > success_prob:
            return None

        self.total_teaching += 1

        # Find the teacher's best genes
        teacher_genes = teacher_genome.get_all_genes()
        if not teacher_genes:
            return None

        # Get best genes (sorted by fitness)
        best_genes = sorted(teacher_genes, key=lambda g: g.get_fitness(), reverse=True)

        # Copy top 1-3 genes
        num_to_copy = self.rng.randint(1, min(3, len(best_genes)))
        genes_to_copy = best_genes[:num_to_copy]

        # Create new genome for learner
        new_genome = learner_genome.copy()

        for gene in genes_to_copy:
            copied_gene = gene.copy()

            # Add to genome
            if len(new_genome.genes) < new_genome.size() + 1:
                pos = self.rng.randint(0, len(new_genome.genes))
                new_genome.genes.insert(pos, copied_gene)

        # Cultural mutation
        if self.rng.random() < self.cultural_mutation_rate:
            new_genome = self.variation_engine.mutate(new_genome)

        # Record event
        event = CulturalEvent(
            event_type="teaching",
            tick=tick,
            agent_id=learner_id,
            target_agent_id=teacher_id,
            pattern_id=None,
            gene_hash=None,
            success=True,
            details={
                "genes_taught": len(genes_to_copy),
                "context": context or "unknown",
            },
        )
        self.cultural_events.append(event)

        # Track cultural pattern
        for gene in genes_to_copy:
            self._track_cultural_pattern(gene, teacher_id, tick, context)

        return new_genome

    def _track_cultural_pattern(
        self,
        gene: Gene,
        agent_id: str,
        tick: int,
        context: Optional[str],
    ) -> None:
        """Track a cultural pattern (emergent behavior)."""
        gene_hash = gene.get_hash()

        # Check if this pattern already exists
        for pattern in self.patterns.values():
            if gene_hash in pattern.gene_hashes:
                pattern.frequency += 1
                pattern.current_adopters += 1
                pattern.total_adopters += 1
                return

        # Create new pattern
        pattern_id = f"pattern_{len(self.patterns)}"
        pattern = CulturalPattern(
            pattern_id=pattern_id,
            gene_hashes={gene_hash},
            origin_tick=tick,
            frequency=1,
            total_adopters=1,
            current_adopters=1,
            name=self._generate_pattern_name(gene),
            behavioral_components=[gene.gene_type.name],
            social_context=context or "general",
        )
        self.patterns[pattern_id] = pattern

    def _generate_pattern_name(self, gene: Gene) -> str:
        """Generate a human-readable name for a pattern."""
        base = gene.gene_type.name.lower()

        if gene.gene_type.name.startswith("IF_"):
            return f"conditional_{gene.condition.name.lower()}" if hasattr(gene, 'condition') else f"conditional_behavior"
        elif gene.children:
            return f"complex_{base}"
        else:
            return f"simple_{base}"

    def record_interaction(
        self,
        agent1_id: str,
        agent2_id: str,
        interaction_type: str,
        outcome: dict,
        tick: int,
    ) -> None:
        """
        Record an interaction for cultural analysis.

        This data is used to detect emergent norms and institutions.
        """
        event = CulturalEvent(
            event_type=interaction_type,
            tick=tick,
            agent_id=agent1_id,
            target_agent_id=agent2_id,
            pattern_id=None,
            gene_hash=None,
            success=outcome.get("success", False),
            details=outcome,
        )
        self.cultural_events.append(event)

        # Update emergent norms based on interaction patterns
        if interaction_type in {"cooperation", "exchange", "sharing", "mutual_aid"}:
            self.emergent_norms["cooperation"] += 1
        elif interaction_type in {"competition", "conflict", "stealing"}:
            self.emergent_norms["competition"] += 1
        elif interaction_type in {"teaching", "learning", "imitation"}:
            self.emergent_norms["knowledge_sharing"] += 1

        # Track norm frequency
        self.norm_frequency[interaction_type].append(tick)

    def detect_emergent_norms(self) -> dict[str, float]:
        """
        Detect emergent social norms from interaction patterns.

        A norm emerges when a behavior pattern becomes consistently observed
        across many agents over time.

        Returns:
            Dictionary of norm name -> strength (0-1)
        """
        norms = {}

        # Calculate norm strength based on recent frequency
        total_interactions = len(self.cultural_events)
        if total_interactions == 0:
            return norms

        recent_events = [
            e for e in self.cultural_events
            if e.tick > (self.cultural_events[-1].tick - 1000)
        ]

        if not recent_events:
            return norms

        # Count by type
        type_counts: dict[str, int] = defaultdict(int)
        for event in recent_events:
            type_counts[event.event_type] += 1

        # Normalize
        for norm_type, count in type_counts.items():
            norms[norm_type] = count / len(recent_events)

        # Detect collective welfare norms (e.g., "social security")
        # These emerge when helping behavior becomes consistent
        helping_events = sum(
            1 for e in recent_events
            if e.event_type in {"teaching", "sharing", "helping"}
        )
        if helping_events / len(recent_events) > 0.1:
            norms["collective_welfare"] = helping_events / len(recent_events)

        return norms

    def detect_emergent_institutions(self) -> list[dict]:
        """
        Detect emergent social institutions from cultural patterns.

        An institution emerges when:
        1. Multiple related cultural patterns cluster together
        2. The cluster provides a coherent function
        3. Agents adopt the cluster together

        Examples:
        - "Trade system": when exchange patterns cluster with reputation
        - "Social security": when sharing patterns cluster with mutual aid
        - "Governance": when leadership patterns cluster with rule-following

        Returns:
            List of detected institutions with metadata
        """
        institutions = []

        # Group patterns by context
        by_context: dict[str, list[CulturalPattern]] = defaultdict(list)
        for pattern in self.patterns.values():
            by_context[pattern.social_context].append(pattern)

        # Detect institutions in each context
        for context, patterns in by_context.items():
            if len(patterns) >= 3:
                # Multiple patterns in same context might form an institution
                avg_frequency = sum(p.frequency for p in patterns) / len(patterns)

                if avg_frequency >= 5:  # Minimum threshold
                    institution = {
                        "name": f"institution_{context}",
                        "context": context,
                        "patterns": [p.pattern_id for p in patterns],
                        "adoption_rate": sum(p.current_adopters for p in patterns),
                        "stability": sum(p.stability for p in patterns) / len(patterns),
                        "emergence_tick": min(p.origin_tick for p in patterns),
                    }
                    institutions.append(institution)

        return institutions

    def get_cultural_statistics(self) -> dict:
        """Get comprehensive cultural statistics."""
        recent_events = [
            e for e in self.cultural_events
            if len(self.cultural_events) > 100
            and e.tick > self.cultural_events[-1].tick - 1000
        ]

        return {
            "total_observations": self.total_observations,
            "total_copies": self.total_copies,
            "total_teaching": self.total_teaching,
            "total_innovations": self.total_innovations,
            "active_patterns": len(self.patterns),
            "emergent_norms": self.detect_emergent_norms(),
            "emergent_institutions": self.detect_emergent_institutions(),
            "recent_events": len(recent_events),
            "copy_rate": self.total_copies / max(1, self.total_observations),
            "teaching_rate": self.total_teaching / max(1, self.total_observations),
        }

    def get_top_patterns(self, top_n: int = 10) -> list[dict]:
        """Get the most common cultural patterns."""
        patterns = list(self.patterns.values())
        patterns.sort(key=lambda p: p.frequency, reverse=True)

        return [
            {
                "id": p.pattern_id,
                "name": p.name,
                "frequency": p.frequency,
                "adopters": p.current_adopters,
                "origin_tick": p.origin_tick,
                "context": p.social_context,
            }
            for p in patterns[:top_n]
        ]

    def reset_culture(self) -> None:
        """Reset cultural tracking (for new simulation runs)."""
        self.patterns.clear()
        self.cultural_events.clear()
        self.emergent_norms.clear()
        self.norm_frequency.clear()
        self.total_observations = 0
        self.total_copies = 0
        self.total_teaching = 0
        self.total_innovations = 0
