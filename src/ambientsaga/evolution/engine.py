"""
Evolution Engine — Main Orchestrator for Self-Evolution

The EvolutionEngine ties together all evolution components:
- Genome management
- Variation (mutation + crossover)
- Selection (fitness + survival)
- Cultural transmission
- Emergence detection

The engine runs in two modes:
1. INTEGRATED: Evolution happens within the simulation ticks
2. OFFSPRING: Evolution happens through agent reproduction

Key Features:
- Adaptive evolution parameters
- Multi-objective fitness
- Cultural evolution layer
- Emergence monitoring
- Configurable evolutionary dynamics
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Protocol

from .culture import CultureEngine
from .emergence import EmergenceDetector
from .genome import BehaviorGenome, GenomeFactory
from .selection import SelectionEngine, reproduction_fitness, social_fitness, survival_fitness
from .variation import VariationEngine


class AgentContextProvider(Protocol):
    """Protocol for getting agent context for fitness evaluation."""

    def get_agent_context(self, agent_id: str) -> dict:
        """Get context dict for an agent."""
        ...


@dataclass
class EvolutionEvent:
    """An event in the evolution process."""

    event_type: str  # "birth", "death", "mutation", "crossover", "culture", "emergence"
    tick: int
    agent_id: str
    details: dict = field(default_factory=dict)


@dataclass
class EvolutionConfig:
    """Configuration for the evolution engine."""

    # Population parameters
    population_size: int = 1000
    min_population: int = 100
    max_population: int = 50000

    # Evolutionary parameters
    mutation_rate: float = 0.15
    crossover_rate: float = 0.7
    elitism_rate: float = 0.1

    # Selection parameters
    tournament_size: int = 5
    diversity_threshold: float = 0.3

    # Cultural parameters
    observation_probability: float = 0.3
    teaching_probability: float = 0.1
    learning_probability: float = 0.5
    cultural_mutation_rate: float = 0.05

    # Fitness weights
    survival_weight: float = 0.3
    reproduction_weight: float = 0.3
    social_weight: float = 0.2
    economic_weight: float = 0.2

    # Emergence detection
    novelty_threshold: float = 0.7
    institution_min_agents: int = 5
    institution_min_stability: float = 0.3

    # Reproduction
    reproduction_threshold: float = 0.8  # Fitness threshold for reproduction
    max_offspring_per_generation: int = 100


class EvolutionEngine:
    """
    Main engine for managing evolutionary dynamics.

    The EvolutionEngine provides:
    - Unified evolution management
    - Configurable evolutionary parameters
    - Integration with simulation world
    - Emergence monitoring
    - Cultural evolution
    """

    def __init__(
        self,
        config: EvolutionConfig | None = None,
        rng: random.Random | None = None,
        context_provider: AgentContextProvider | None = None,
    ):
        """
        Initialize the evolution engine.

        Args:
            config: Evolution configuration
            rng: Random number generator
            context_provider: Provider for agent context
        """
        self.config = config or EvolutionConfig()
        self.rng = rng or random.Random()
        self.context_provider = context_provider

        # Core components
        self.variation_engine = VariationEngine(
            mutation_rate=self.config.mutation_rate,
            crossover_rate=self.config.crossover_rate,
            rng=self.rng,
        )

        self.selection_engine = SelectionEngine(
            population_size=self.config.population_size,
            elitism_rate=self.config.elitism_rate,
            tournament_size=self.config.tournament_size,
            diversity_threshold=self.config.diversity_threshold,
            fitness_functions=[
                lambda g, c: survival_fitness(g, c) * self.config.survival_weight,
                lambda g, c: reproduction_fitness(g, c) * self.config.reproduction_weight,
                lambda g, c: social_fitness(g, c) * self.config.social_weight,
            ],
            rng=self.rng,
        )

        self.culture_engine = CultureEngine(
            variation_engine=self.variation_engine,
            observation_probability=self.config.observation_probability,
            teaching_probability=self.config.teaching_probability,
            learning_probability=self.config.learning_probability,
            cultural_mutation_rate=self.config.cultural_mutation_rate,
            rng=self.rng,
        )

        self.emergence_detector = EmergenceDetector(
            novelty_threshold=self.config.novelty_threshold,
            stability_threshold=self.config.institution_min_stability,
            institution_min_agents=self.config.institution_min_agents,
            rng=self.rng,
        )

        # Agent genomes (agent_id -> genome)
        self.genomes: dict[str, BehaviorGenome] = {}

        # Evolution history
        self.events: list[EvolutionEvent] = []
        self.generation = 0

        # Statistics
        self.births = 0
        self.deaths = 0
        self.total_mutations = 0
        self.total_crossovers = 0

    # =========================================================================
    # Genome Management
    # =========================================================================

    def create_genome(
        self,
        agent_id: str,
        initial_type: str = "random",
        parent1: BehaviorGenome | None = None,
        parent2: BehaviorGenome | None = None,
    ) -> BehaviorGenome:
        """
        Create a new genome for an agent.

        Args:
            agent_id: ID of the agent
            initial_type: "random", "minimal", "social", or "inherited"
            parent1: First parent (for sexual reproduction)
            parent2: Second parent (for sexual reproduction)

        Returns:
            New BehaviorGenome
        """
        if initial_type == "random":
            genome = GenomeFactory.create_random_genome(rng=self.rng)
        elif initial_type == "minimal":
            genome = GenomeFactory.create_minimal_genome()
        elif initial_type == "social":
            genome = GenomeFactory.create_social_genome(rng=self.rng)
        elif initial_type == "inherited" and parent1:
            if parent2 and self.rng.random() < self.config.crossover_rate:
                # Sexual reproduction
                genome = self.variation_engine.sexual_reproduction(
                    parent1, parent2, self.config.mutation_rate
                )
            else:
                # Asexual reproduction
                genome = self.variation_engine.asexual_reproduction(
                    parent1, self.config.mutation_rate
                )
        else:
            genome = GenomeFactory.create_random_genome(rng=self.rng)

        self.genomes[agent_id] = genome
        self.births += 1

        # Record birth event
        self.events.append(EvolutionEvent(
            event_type="birth",
            tick=0,
            agent_id=agent_id,
            details={"genome_size": genome.size(), "genome_depth": genome.depth()},
        ))

        return genome

    def get_genome(self, agent_id: str) -> BehaviorGenome | None:
        """Get an agent's genome."""
        return self.genomes.get(agent_id)

    def remove_genome(self, agent_id: str) -> None:
        """Remove an agent's genome (death)."""
        if agent_id in self.genomes:
            del self.genomes[agent_id]
            self.deaths += 1

            self.events.append(EvolutionEvent(
                event_type="death",
                tick=0,
                agent_id=agent_id,
            ))

    # =========================================================================
    # Evolution Steps
    # =========================================================================

    def evolve_tick(self, tick: int) -> None:
        """
        Perform one evolution tick.

        This is called periodically (not every simulation tick).
        It handles:
        - Cultural transmission
        - Selection
        - Emergence detection
        """
        self.generation += 1

        # Age all genomes
        for genome in self.genomes.values():
            genome.evolve_age()

        # Record generation statistics
        context = self._get_population_context()
        self.selection_engine.record_generation(list(self.genomes.values()), context)

        # Detect emergence
        self._detect_emergence(tick)

    def process_interaction(
        self,
        agent1_id: str,
        agent2_id: str,
        interaction_type: str,
        outcome: dict,
        tick: int,
    ) -> None:
        """
        Process an agent interaction for cultural evolution.

        This is called when agents interact, enabling:
        - Observation and learning
        - Teaching
        - Cultural pattern formation
        """
        genome1 = self.get_genome(agent1_id)
        genome2 = self.get_genome(agent2_id)

        if not genome1 or not genome2:
            return

        # Calculate success
        success = outcome.get("success", False)
        fitness_delta = outcome.get("fitness_delta", 0.0)

        # Update fitness based on interaction success
        if success:
            # Record successful interactions for both agents
            for genome in [genome1, genome2]:
                genes = genome.get_all_genes()
                if genes:
                    # Update fitness for a random gene (simplified)
                    gene = self.rng.choice(genes)
                    genome.record_execution(gene.get_hash(), success, fitness_delta)

        # Cultural transmission: agent1 learns from agent2
        # Always call observe_and_learn for observation recording
        # The success flag affects whether copying happens, not whether observation is recorded
        new_genome1 = self.culture_engine.observe_and_learn(
            genome1,
            genome2,
            genome2.get_average_fitness(),
            agent1_id,
            agent2_id,
            tick,
            interaction_type,
            require_success=False,  # Record observations regardless of success
        )

        if new_genome1:
            self.genomes[agent1_id] = new_genome1

        # Record interaction for norm detection
        self.culture_engine.record_interaction(
            agent1_id, agent2_id, interaction_type, outcome, tick
        )

    def record_action(
        self,
        agent_id: str,
        gene_hash: str,
        gene_type: str,
        success: bool,
        fitness_delta: float,
        tick: int,
    ) -> None:
        """
        Record an action taken by an agent.

        This updates the fitness of the gene that was executed.
        """
        genome = self.get_genome(agent_id)
        if not genome:
            return

        genome.record_execution(gene_hash, success, fitness_delta)

        # Track innovation
        self.emergence_detector.track_innovation(
            gene_hash,
            gene_type,
            tick,
        )

    # =========================================================================
    # Reproduction
    # =========================================================================

    def should_reproduce(
        self,
        agent_id: str,
        current_population: int,
    ) -> tuple[bool, str | None]:
        """
        Determine if an agent should reproduce.

        Returns:
            Tuple of (should_reproduce, parent2_id if sexual)
        """
        if current_population >= self.config.max_population:
            return False, None

        genome = self.get_genome(agent_id)
        if not genome:
            return False, None

        # Fitness threshold for reproduction
        fitness = genome.get_average_fitness()
        if fitness < self.config.reproduction_threshold:
            return False, None

        # Population pressure (fewer agents = more reproduction)
        population_factor = self.config.population_size / max(1, current_population)
        reproduction_prob = min(0.5, fitness * population_factor * 0.1)

        if self.rng.random() > reproduction_prob:
            return False, None

        # Find a mate for sexual reproduction (50% chance)
        if self.rng.random() < 0.5 and len(self.genomes) > 1:
            potential_mates = [
                (aid, g.get_average_fitness())
                for aid, g in self.genomes.items()
                if aid != agent_id
            ]
            if potential_mates:
                # Prefer fit mates
                potential_mates.sort(key=lambda x: x[1], reverse=True)
                mate_id = self.rng.choice(potential_mates[:10])[0]
                return True, mate_id

        return True, None

    def create_offspring(
        self,
        parent1_id: str,
        parent2_id: str | None = None,
    ) -> tuple[str, BehaviorGenome]:
        """
        Create an offspring genome.

        Args:
            parent1_id: First parent ID
            parent2_id: Second parent ID (optional, for sexual reproduction)

        Returns:
            Tuple of (offspring_id, offspring_genome)
        """
        parent1 = self.get_genome(parent1_id)
        if not parent1:
            raise ValueError(f"Parent {parent1_id} not found")

        parent2 = self.get_genome(parent2_id) if parent2_id else None

        # Create offspring genome
        offspring_id = f"agent_{len(self.genomes) + self.births}"
        offspring = self.create_genome(
            offspring_id,
            initial_type="inherited",
            parent1=parent1,
            parent2=parent2,
        )

        return offspring_id, offspring

    # =========================================================================
    # Selection
    # =========================================================================

    def select_survivors(
        self,
        current_population: list[str],
        tick: int,
    ) -> list[str]:
        """
        Select which agents survive.

        Args:
            current_population: List of agent IDs
            tick: Current tick

        Returns:
            List of surviving agent IDs
        """
        if len(current_population) <= self.config.min_population:
            return current_population

        genomes = [self.genomes[aid] for aid in current_population if aid in self.genomes]
        context = self._get_population_context()

        survivors = self.selection_engine.select_for_survival(
            genomes,
            [],  # No offspring yet
            context,
        )

        survivor_ids = []
        for genome in survivors:
            for aid, g in self.genomes.items():
                if g is genome:
                    survivor_ids.append(aid)
                    break

        # Remove non-survivors
        survivors_set = set(survivor_ids)
        for aid in current_population:
            if aid not in survivors_set:
                self.remove_genome(aid)

        return survivor_ids

    # =========================================================================
    # Emergence Detection
    # =========================================================================

    def _detect_emergence(self, tick: int) -> None:
        """Detect emergent behaviors and institutions."""
        # Detect behavioral emergence from recent innovations
        self._detect_behaviors_from_innovations(tick)

        # Detect institutional emergence from behaviors (very conservative)
        behaviors = list(self.emergence_detector.emerged_behaviors.values())
        if len(behaviors) < 10:
            return

        # Group behaviors by type and count
        from collections import Counter
        behavior_types = Counter([b.name for b in behaviors])

        # Only create institutions for behaviors that appear multiple times
        # and have been stable (tracked over multiple ticks)
        for bname, count in behavior_types.items():
            if count >= 5:  # Same named behavior appears 5+ times = true pattern
                # Check if we already have this institution
                inst_id = f"institution_{bname}"
                if inst_id not in self.emergence_detector.emerged_institutions:
                    # Get behaviors of this type
                    same_name_behaviors = [b for b in behaviors if b.name == bname]

                    if len(same_name_behaviors) >= 5:
                        institution = self.emergence_detector.detect_institutional_emergence(
                            same_name_behaviors[:10],
                            tick,
                            bname,
                        )

                        if institution:
                            self.events.append(EvolutionEvent(
                                event_type="emergence",
                                tick=tick,
                                agent_id="",
                                details={
                                    "type": "institution",
                                    "name": institution.name,
                                    "id": institution.institution_id,
                                },
                            ))

    def _detect_cross_gene_behaviors(self, tick: int) -> None:
        """Detect emergent behaviors from cross-gene-type patterns."""
        history = self.emergence_detector.gene_innovation_history
        if len(history) < 20:
            return

        # Track co-occurrence of different gene types within short time windows
        recent = history[-200:]
        window_size = 20

        # Find co-occurring gene type pairs
        cooccurrence: dict[tuple[str, str], int] = {}
        for i in range(len(recent) - 1):
            g1_type = recent[i]["gene_type"]
            for j in range(i + 1, min(i + window_size, len(recent))):
                g2_type = recent[j]["gene_type"]
                if g1_type != g2_type:
                    pair = tuple(sorted([g1_type, g2_type]))
                    cooccurrence[pair] = cooccurrence.get(pair, 0) + 1

        # Find strong co-occurrence patterns (pairs that appear together 5+ times)
        strong_pairs = [(pair, count) for pair, count in cooccurrence.items() if count >= 5]
        strong_pairs.sort(key=lambda x: x[1], reverse=True)

        # Check for social/institution-relevant pairs
        [
            p for p in strong_pairs
            if any(g in p for g in ["SHARE", "HELP", "EXCHANGE", "COOPERATE", "GIVE", "GIFT"])
        ]

        # Detect behaviors for strong co-occurring pairs
        for (g1, g2), count in strong_pairs[:10]:
            behavior_id = f"behavior_{g1}_{g2}"

            # Skip if already exists or if it's just a single gene type
            if behavior_id in self.emergence_detector.emerged_behaviors:
                continue
            if g1 == g2:
                continue

            # Get gene hashes for this pair
            g1_hashes = [r["gene_hash"] for r in recent if r["gene_type"] == g1][:3]
            g2_hashes = [r["gene_hash"] for r in recent if r["gene_type"] == g2][:3]
            combined_hashes = g1_hashes + g2_hashes

            if len(combined_hashes) < 2:
                continue

            outcome = {"success": True, "fitness_delta": 0.2}

            behavior = self.emergence_detector.detect_behavioral_emergence(
                gene_cluster=combined_hashes,
                tick=tick,
                execution_context=f"cooccur_{g1}_{g2}",
                outcome=outcome,
            )

            if behavior:
                self.events.append(EvolutionEvent(
                    event_type="behavioral_emergence",
                    tick=tick,
                    agent_id="",
                    details={
                        "type": "cross_gene_behavior",
                        "name": behavior.name,
                        "gene_types": [g1, g2],
                        "cooccurrence_count": count,
                    },
                ))

    def _detect_behaviors_from_innovations(self, tick: int) -> None:
        """Detect emergent behaviors from recent innovation patterns."""
        # First detect cross-gene-type behaviors
        self._detect_cross_gene_behaviors(tick)

        # Get recent innovations
        history = self.emergence_detector.gene_innovation_history
        if len(history) < 10:
            return

        # Look at recent innovations (last 100)
        recent = history[-100:]

        # Group by gene type
        by_type: dict[str, list[dict]] = {}
        for record in recent:
            gene_type = record["gene_type"]
            if gene_type not in by_type:
                by_type[gene_type] = []
            by_type[gene_type].append(record)

        # For each gene type that has multiple innovations, create a behavior
        for gene_type, records in by_type.items():
            if len(records) >= 5:  # At least 5 occurrences
                gene_hashes = [r["gene_hash"] for r in records[:5]]
                outcome = {"success": True, "fitness_delta": 0.1}

                # Check if this behavior already exists
                behavior_id = f"behavior_{gene_type}"
                if behavior_id not in self.emergence_detector.emerged_behaviors:
                    behavior = self.emergence_detector.detect_behavioral_emergence(
                        gene_cluster=gene_hashes,
                        tick=tick,
                        execution_context=f"gene_type_{gene_type}",
                        outcome=outcome,
                    )
                    if behavior:
                        self.events.append(EvolutionEvent(
                            event_type="behavioral_emergence",
                            tick=tick,
                            agent_id="",
                            details={
                                "type": "behavior",
                                "name": behavior.name,
                                "gene_type": gene_type,
                                "count": len(records),
                            },
                        ))

    def get_emergence_report(self) -> dict:
        """Get a comprehensive emergence report."""
        return {
            "summary": self.emergence_detector.get_emergence_summary(),
            "institutions": self.emergence_detector.get_emerged_institutions_summary(),
            "recent_events": self.emergence_detector.get_recent_emergence_events(last_n=20),
            "social_security_like": self.emergence_detector.detect_social_security_like_emergence(),
        }

    # =========================================================================
    # Utility
    # =========================================================================

    def _get_population_context(self) -> dict:
        """Get context for the entire population."""
        genomes = list(self.genomes.values())

        if not genomes:
            return {}

        avg_fitness = sum(g.get_average_fitness() for g in genomes) / len(genomes)
        avg_size = sum(g.size() for g in genomes) / len(genomes)

        return {
            "population_size": len(genomes),
            "avg_fitness": avg_fitness,
            "avg_genome_size": avg_size,
            "generation": self.generation,
        }

    def get_statistics(self) -> dict:
        """Get comprehensive evolution statistics."""
        return {
            "generation": self.generation,
            "population_size": len(self.genomes),
            "births": self.births,
            "deaths": self.deaths,
            "total_mutations": self.total_mutations,
            "total_crossovers": self.total_crossovers,
            "variation_stats": self.variation_engine.get_statistics(),
            "selection_stats": self.selection_engine.get_statistics(),
            "culture_stats": self.culture_engine.get_cultural_statistics(),
            "emergence_summary": self.emergence_detector.get_emergence_summary(),
        }

    def get_genome_info(self, agent_id: str) -> dict | None:
        """Get information about an agent's genome."""
        genome = self.get_genome(agent_id)
        if not genome:
            return None

        return {
            "agent_id": agent_id,
            "size": genome.size(),
            "depth": genome.depth(),
            "fitness": genome.get_average_fitness(),
            "success_rate": genome.get_success_rate(),
            "age": genome.age,
            "generation": genome.generation,
            "cultural_heritage": genome.cultural_heritage,
            "unique_innovations": len(genome.unique_innovations),
        }

    def print_emergence_report(self) -> None:
        """Print a formatted emergence report."""
        report = self.get_emergence_report()

        print("\n" + "=" * 60)
        print("EMERGENCE REPORT")
        print("=" * 60)

        summary = report["summary"]
        print(f"\nTotal Innovations: {summary['total_innovations']}")
        print(f"Total Emergent Behaviors: {summary['total_behaviors']}")
        print(f"Total Emerged Institutions: {summary['total_institutions']}")
        print(f"Innovation Velocity: {summary['innovation_velocity']:.2f}/1000 ticks")

        institutions = report["institutions"]
        if institutions:
            print("\nEmerged Institutions:")
            for inst in institutions:
                print(f"  - {inst['name']} (purpose: {inst['purpose']})")
                print(f"    Origin: tick {inst['origin_tick']}, stability: {inst['stability']:.2f}")

        social_security = report["social_security_like"]
        if social_security:
            print("\n*** SOCIAL SECURITY-LIKE INSTITUTION DETECTED ***")
            print(f"  Institution: {social_security['name']}")
            print(f"  Origin: tick {social_security['origin_tick']}")

        print()

    def reset(self) -> None:
        """Reset the evolution engine."""
        self.genomes.clear()
        self.events.clear()
        self.generation = 0
        self.births = 0
        self.deaths = 0
        self.total_mutations = 0
        self.total_crossovers = 0

        self.variation_engine.reset_statistics()
        self.culture_engine.reset_culture()
        self.emergence_detector.reset()
