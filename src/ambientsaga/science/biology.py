"""
Biology Engine — Life Systems and Dynamics

Provides a simplified but principled biology simulation:
- Genetics: DNA, genes, alleles, inheritance
- Metabolism: Catabolism, anabolism, energy production
- Reproduction: Sexual, asexual, mitosis, meiosis
- Evolution: Selection, mutation, adaptation
- Physiology: Organs, systems, homeostasis

Biology emerges from chemistry (molecular systems).
Ecology emerges from biology (ecosystem dynamics).
Social systems emerge from biology (human behavior).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum


class LifeStage(Enum):
    """Stages of life."""
    EMBRYO = "embryo"
    JUVENILE = "juvenile"
    ADULT = "adult"
    SENESCENT = "senescent"
    DEAD = "dead"


class Sex(Enum):
    """Biological sex."""
    MALE = "male"
    FEMALE = "female"
    HERMAPHRODITE = "hermaphrodite"
    ASEXUAL = "asexual"


@dataclass
class Gene:
    """A single gene."""
    gene_id: str
    chromosome: int  # 0-23 for humans
    position: float  # Position on chromosome (0-1)
    allele1: str  # First allele
    allele2: str  # Second allele
    locus: str  # Gene locus name
    dominance: str = "complete"  # complete, incomplete, codominant

    @property
    def genotype(self) -> tuple[str, str]:
        return (self.allele1, self.allele2)

    @property
    def phenotype(self) -> str:
        """Get expressed phenotype based on dominance."""
        if self.allele1 == self.allele2:
            return self.allele1
        if self.dominance == "dominant":
            return self.allele1 if self.allele1 != "r" else self.allele2
        elif self.dominance == "codominant":
            return f"{self.allele1}/{self.allele2}"
        else:  # recessive
            return self.allele2 if self.allele1 == "R" else self.allele1


@dataclass
class Chromosome:
    """A chromosome."""
    chromosome_id: int  # 1-23, 0 = mitochondrial
    genes: list[Gene] = field(default_factory=list)
    is_sex_chromosome: bool = False
    paternal: bool = True  # From father or mother


@dataclass
class Genome:
    """A complete genome."""
    genome_id: str
    chromosomes: list[Chromosome] = field(default_factory=list)
    mitochondrial_dna: str = ""

    # Traits (derived from genes)
    traits: dict[str, str] = field(default_factory=dict)

    def get_gene(self, locus: str) -> Gene | None:
        """Get a gene by locus."""
        for chrom in self.chromosomes:
            for gene in chrom.genes:
                if gene.locus == locus:
                    return gene
        return None

    def get_trait(self, trait: str) -> str | None:
        """Get a trait value."""
        return self.traits.get(trait)

    def crossover(self, other: Genome, recombination_rate: float = 0.01) -> Genome:
        """Perform meiosis: create gamete with crossover."""
        gamete = Genome(genome_id=f"{self.genome_id}_gamete")
        gamete.mitochondrial_dna = self.mitochondrial_dna  # Always maternal

        for chrom in self.chromosomes:
            # Simple crossover: swap segments with probability
            new_chrom = Chromosome(
                chromosome_id=chrom.chromosome_id,
                is_sex_chromosome=chrom.is_sex_chromosome,
                paternal=not chrom.paternal,  # Random in real meiosis
            )

            # Copy genes with possible recombination
            for gene in chrom.genes:
                if random.random() < recombination_rate:
                    # Crossover with partner chromosome
                    partner = other.get_gene(gene.locus)
                    if partner:
                        new_gene = Gene(
                            gene_id=gene.gene_id,
                            chromosome=gene.chromosome,
                            position=gene.position,
                            allele1=gene.allele1,
                            allele2=partner.allele2,
                            locus=gene.locus,
                            dominance=gene.dominance,
                        )
                        new_chrom.genes.append(new_gene)
                else:
                    new_chrom.genes.append(gene)

            gamete.chromosomes.append(new_chrom)

        return gamete

    def mutate(self, mutation_rate: float = 0.0001) -> Genome:
        """Apply mutations to genome."""
        for chrom in self.chromosomes:
            for gene in chrom.genes:
                if random.random() < mutation_rate:
                    # Point mutation
                    mutations = ["R", "r"]  # Dominant/recessive
                    if random.random() < 0.5:
                        gene.allele1 = random.choice(mutations)
                    else:
                        gene.allele2 = random.choice(mutations)

        return self


@dataclass
class Metabolism:
    """Metabolic system."""
    basal_metabolic_rate: float = 100.0  # Calories/day
    activity_multiplier: float = 1.0

    # Nutrient storage
    carbohydrates: float = 0.0  # g
    proteins: float = 0.0  # g
    fats: float = 0.0  # g

    # Energy
    atp: float = 100.0  # Current ATP
    atp_capacity: float = 200.0  # Max ATP

    # Vitamins/minerals
    vitamins: dict[str, float] = field(default_factory=dict)
    minerals: dict[str, float] = field(default_factory=dict)

    def get_energy_intake(self) -> float:
        """Get daily energy from current nutrients (kcal)."""
        carb_energy = self.carbohydrates * 4
        protein_energy = self.proteins * 4
        fat_energy = self.fats * 9
        return carb_energy + protein_energy + fat_energy

    def get_energy_expenditure(self) -> float:
        """Calculate daily energy expenditure."""
        return self.basal_metabolic_rate * self.activity_multiplier

    def update(self, dt: float = 1.0) -> dict[str, float]:
        """Update metabolism, return energy balance."""
        intake = self.get_energy_intake()
        expenditure = self.get_energy_expenditure() * dt
        balance = intake - expenditure

        # Burn excess, consume stores
        if balance > 0:
            # Store as fat
            excess = balance
            if self.carbohydrates > 0:
                stored = min(excess / 9, self.carbohydrates / 4)
                self.carbohydrates -= stored * 4
                self.fats += stored
                excess -= stored * 9
            if excess > 0:
                self.fats += excess / 9
        else:
            # Burn stores
            deficit = -balance
            if self.fats > 0:
                burned = min(deficit / 9, self.fats)
                self.fats -= burned
                deficit -= burned * 9
            if deficit > 0 and self.carbohydrates > 0:
                burned = min(deficit / 4, self.carbohydrates)
                self.carbohydrates -= burned
                deficit -= burned * 4

        return {
            "intake": intake,
            "expenditure": expenditure,
            "balance": balance,
        }


@dataclass
class ReproductionSystem:
    """Reproductive system."""
    sex: Sex = Sex.ASEXUAL
    fertility: float = 1.0  # 0-1, current fertility
    gestational_period: int = 270  # Days for humans
    clutch_size: int = 1  # Offspring per birth
    max_offspring: int = 10  # Lifetime maximum
    offspring_count: int = 0

    # Sexual reproduction
    mate_preference: dict[str, float] = field(default_factory=dict)
    gestation_timer: int = 0  # Current pregnancy
    gamete_quality: float = 1.0  # 0-1

    def can_reproduce(self, age: int, health: float) -> bool:
        """Check if organism can reproduce."""
        if self.offspring_count >= self.max_offspring:
            return False
        if health < 0.3:
            return False
        if self.fertility < 0.1:
            return False
        # Age limits vary by species
        if age < 10 or age > 50:
            return False
        return True

    def impregnate(self) -> bool:
        """Attempt pregnancy (sexual reproduction)."""
        if self.sex != Sex.FEMALE:
            return False
        if self.gestation_timer > 0:
            return False  # Already pregnant
        if random.random() < self.fertility * self.gamete_quality:
            self.gestation_timer = self.gestational_period
            return True
        return False

    def give_birth(self) -> int:
        """Attempt to give birth, return number of offspring."""
        if self.gestation_timer > 0:
            self.gestation_timer -= 1
            return 0

        offspring = self.clutch_size
        self.offspring_count += offspring
        return offspring


@dataclass
class ImmuneSystem:
    """Immune system."""
    strength: float = 1.0  # 0-1, overall strength
    pathogen_exposure: dict[str, float] = field(default_factory=dict)
    antibodies: dict[str, float] = field(default_factory=dict)
    vaccination_record: list[str] = field(default_factory=list)

    # Disease status
    infected: bool = False
    infection_severity: float = 0.0  # 0-1
    disease_name: str = ""

    def get_infection_risk(self, pathogen_load: float) -> float:
        """Calculate infection risk."""
        if pathogen_load < 0.1:
            return 0.0
        return pathogen_load * (1 - self.strength)

    def infect(self, disease: str, severity: float) -> None:
        """Attempt infection."""
        risk = self.get_infection_risk(severity)
        if random.random() < risk:
            self.infected = True
            self.infection_severity = severity
            self.disease_name = disease

    def heal(self, dt: float = 1.0) -> None:
        """Attempt to heal from infection."""
        if not self.infected:
            return

        # Natural immunity development
        if self.disease_name in self.antibodies:
            self.antibodies[self.disease_name] += dt * 0.1
            if self.antibodies[self.disease_name] > 1.0:
                self.infected = False
                self.infection_severity = 0.0
                self.disease_name = ""
        else:
            # Build immunity slowly
            self.antibodies[self.disease_name] = dt * 0.01 * self.strength

        # Recovery from symptoms
        self.infection_severity = max(0, self.infection_severity - dt * 0.05 * self.strength)
        if self.infection_severity <= 0:
            self.infected = False


@dataclass
class Organism:
    """A living organism."""
    organism_id: str
    species: str
    genome: Genome

    # Identity
    name: str = ""
    age: int = 0  # Days
    sex: Sex = Sex.MALE
    life_stage: LifeStage = LifeStage.JUVENILE

    # Health
    health: float = 1.0  # 0-1
    fitness: float = 1.0  # 0-1, evolutionary fitness
    max_age: int = 36500  # ~100 years

    # Physical
    mass: float = 70.0  # kg
    height: float = 1.7  # m
    metabolic_rate: Metabolism = field(default_factory=Metabolism)

    # Systems
    reproduction: ReproductionSystem = field(default_factory=ReproductionSystem)
    immune_system: ImmuneSystem = field(default_factory=ImmuneSystem)

    # Brain/Cognition
    intelligence: float = 0.5  # 0-1
    learning_rate: float = 0.01

    # Energy
    energy: float = 100.0  # 0-100
    energy_capacity: float = 200.0

    # Status
    is_alive: bool = True
    is_pregnant: bool = False
    gestation_progress: int = 0

    def __post_init__(self):
        if not self.name:
            self.name = f"{self.species}_{self.organism_id[:8]}"

    @property
    def bmi(self) -> float:
        """Body mass index."""
        if self.height <= 0:
            return 0
        return self.mass / (self.height ** 2)

    @property
    def age_years(self) -> float:
        """Age in years."""
        return self.age / 365.0

    def update(self, tick: int, dt: float = 1.0) -> dict:
        """Update organism state."""
        events = []

        # Age
        self.age += int(dt)

        # Update life stage
        if self.age < self.max_age * 0.1:
            self.life_stage = LifeStage.JUVENILE
        elif self.age < self.max_age * 0.8:
            self.life_stage = LifeStage.ADULT
        else:
            self.life_stage = LifeStage.SENESCENT

        # Update metabolism
        metabolism_events = self.metabolic_rate.update(dt)
        events.append(("metabolism", metabolism_events))

        # Update immune system
        if self.immune_system.infected:
            self.immune_system.heal(dt)
            self.health -= self.immune_system.infection_severity * 0.01
            events.append(("disease", {
                "disease": self.immune_system.disease_name,
                "severity": self.immune_system.infection_severity,
            }))

        # Update reproduction
        if self.is_pregnant:
            self.gestation_progress += int(dt)
            events.append(("pregnancy", {"progress": self.gestation_progress}))

        # Natural aging
        if self.life_stage == LifeStage.SENESCENT:
            self.health -= 0.001 * dt

        # Death check
        if self.health <= 0 or self.age >= self.max_age:
            self.die("natural")
            events.append(("death", {"cause": "natural"}))

        # Update fitness
        self._update_fitness()

        return {"organism_id": self.organism_id, "age": self.age, "events": events}

    def _update_fitness(self) -> None:
        """Update evolutionary fitness."""
        # Fitness components
        survival_fitness = self.health
        reproduction_fitness = 1.0 - (self.reproduction.offspring_count / max(1, self.reproduction.max_offspring))
        age_fitness = 1.0 - (self.age / self.max_age)

        # Weighted combination
        self.fitness = (
            0.4 * survival_fitness +
            0.3 * reproduction_fitness +
            0.2 * age_fitness +
            0.1 * self.genome.traits.get("fitness_gene", 0.5)
        )

    def eat(self, food_energy: float) -> None:
        """Consume food."""
        self.energy = min(self.energy_capacity, self.energy + food_energy)

    def work(self, energy_cost: float) -> bool:
        """Perform work, return success."""
        if self.energy >= energy_cost:
            self.energy -= energy_cost
            return True
        return False

    def die(self, cause: str) -> None:
        """Kill the organism."""
        self.is_alive = False
        self.life_stage = LifeStage.DEAD
        self.health = 0.0

    def reproduce(self, partner: Organism = None) -> Organism | None:
        """Attempt reproduction."""
        if not self.is_alive:
            return None
        if not self.reproduction.can_reproduce(self.age, self.health):
            return None

        # Asexual reproduction
        if self.reproduction.sex == Sex.ASEXUAL or partner is None:
            offspring_genome = self.genome.mutate()
            return self._create_offspring(offspring_genome)

        # Sexual reproduction
        if partner.reproduction.sex == Sex.MALE:
            male = partner
            female = self
        elif self.reproduction.sex == Sex.MALE:
            male = self
            female = partner
        else:
            return None  # Need male and female

        # Check female is not already pregnant
        if female.is_pregnant:
            return None

        # Create gametes
        male_gamete = male.genome.crossover(partner.genome)
        female_gamete = female.genome.crossover(partner.genome)

        # Create offspring genome
        offspring_genome = self._combine_genomes(male_gamete, female_gamete)
        offspring_genome = offspring_genome.mutate()

        # Impregnate female
        if female.reproduction.impregnate():
            female.is_pregnant = True
            female.gestation_progress = 0
            return female._create_offspring(offspring_genome)

        return None

    def _create_offspring(self, offspring_genome: Genome) -> Organism:
        """Create an offspring organism."""
        offspring_id = f"{self.organism_id}_offspring_{self.reproduction.offspring_count}"
        offspring = Organism(
            organism_id=offspring_id,
            species=self.species,
            genome=offspring_genome,
            name=f"{self.species}_{offspring_id[:8]}",
            sex=random.choice([Sex.MALE, Sex.FEMALE]),
            mass=self.mass * 0.1,  # Start small
        )
        offspring.reproduction.offspring_count = 0  # Reset for new organism
        return offspring

    def _combine_genomes(self, gamete1: Genome, gamete2: Genome) -> Genome:
        """Combine two gametes into zygote genome."""
        zygote = Genome(genome_id=f"zygote_{random.randint(100000, 999999)}")
        # Simplified: just combine chromosomes from both gametes
        zygote.chromosomes = gamete1.chromosomes + gamete2.chromosomes
        return zygote


class BiologyEngine:
    """
    Biology simulation engine.

    Provides biological systems and dynamics.
    Couples with:
    - Physics: Movement, energy, thermodynamics
    - Chemistry: Metabolism, nutrients
    - Ecology: Population dynamics, food chains
    - Evolution: Genetic algorithms
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

        # Population
        self.organisms: dict[str, Organism] = {}

        # Species database
        self.species: dict[str, dict] = {}
        self._init_species()

        # Statistics
        self.total_births = 0
        self.total_deaths = 0
        self.birth_history: list[tuple[int, str]] = []
        self.death_history: list[tuple[int, str, str]] = []

        # Population dynamics
        self.population_history: list[dict] = []

    def _init_species(self) -> None:
        """Initialize species database."""
        self.species = {
            "human": {
                "name": "Human",
                "max_age": 36500,
                "clutch_size": 1,
                "gestational_period": 270,
                "basal_metabolic_rate": 1500,
                "mass": 70,
                "height": 1.7,
            },
            "deer": {
                "name": "Deer",
                "max_age": 3650,
                "clutch_size": 1,
                "gestational_period": 200,
                "basal_metabolic_rate": 800,
                "mass": 70,
                "height": 1.2,
            },
            "rabbit": {
                "name": "Rabbit",
                "max_age": 1825,
                "clutch_size": 6,
                "gestational_period": 30,
                "basal_metabolic_rate": 200,
                "mass": 2,
                "height": 0.3,
            },
            "wolf": {
                "name": "Wolf",
                "max_age": 3650,
                "clutch_size": 5,
                "gestational_period": 63,
                "basal_metabolic_rate": 1000,
                "mass": 35,
                "height": 0.8,
            },
            "grass": {
                "name": "Grass",
                "max_age": 365,
                "clutch_size": 100,
                "gestational_period": 0,
                "basal_metabolic_rate": 10,
                "mass": 0.1,
                "height": 0.5,
            },
        }

    def create_organism(
        self,
        organism_id: str,
        species: str,
        genome: Genome = None,
        mass: float = None,
        sex: Sex = None,
    ) -> Organism:
        """Create a new organism."""
        if species not in self.species:
            species = "human"  # Default

        species_data = self.species[species]

        # Create genome if not provided
        if genome is None:
            genome = self._create_genome(organism_id, species)

        # Create organism
        organism = Organism(
            organism_id=organism_id,
            species=species,
            genome=genome,
            mass=mass or species_data["mass"],
            height=species_data["height"],
            sex=sex or random.choice([Sex.MALE, Sex.FEMALE]),
        )

        # Set reproduction parameters
        organism.reproduction = ReproductionSystem(
            sex=organism.sex,
            clutch_size=species_data["clutch_size"],
            gestational_period=species_data["gestational_period"],
        )

        # Set metabolism
        organism.metabolic_rate = Metabolism(
            basal_metabolic_rate=species_data["basal_metabolic_rate"],
        )

        self.organisms[organism_id] = organism
        self.total_births += 1
        self.birth_history.append((0, organism_id))

        return organism

    def _create_genome(self, organism_id: str, species: str) -> Genome:
        """Create a new genome for a species."""
        genome = Genome(genome_id=f"{organism_id}_genome")

        # Create chromosomes
        for i in range(23):
            chrom = Chromosome(
                chromosome_id=i + 1,
                is_sex_chromosome=(i == 22),  # Last pair is sex chromosomes
            )

            # Add some genes
            for j in range(random.randint(5, 20)):
                gene = Gene(
                    gene_id=f"gene_{i}_{j}",
                    chromosome=i + 1,
                    position=random.random(),
                    allele1=random.choice(["R", "r"]),
                    allele2=random.choice(["R", "r"]),
                    locus=f"locus_{i}_{j}",
                )
                chrom.genes.append(gene)

            genome.chromosomes.append(chrom)

        return genome

    def remove_organism(self, organism_id: str, cause: str = "unknown") -> None:
        """Remove an organism."""
        if organism_id in self.organisms:
            organism = self.organisms[organism_id]
            organism.die(cause)
            del self.organisms[organism_id]
            self.total_deaths += 1
            self.death_history.append((0, organism_id, cause))

    def update(self, tick: int, dt: float = 1.0) -> dict:
        """Update biology simulation."""
        events = []

        # Update all organisms
        for organism in list(self.organisms.values()):
            if not organism.is_alive:
                continue

            organism_events = organism.update(tick, dt)
            events.append(organism_events)

            # Check for death
            if not organism.is_alive:
                self.total_deaths += 1
                self.death_history.append((tick, organism.organism_id, "natural"))

        # Remove dead organisms
        dead_ids = [oid for oid, org in self.organisms.items() if not org.is_alive]
        for oid in dead_ids:
            del self.organisms[oid]

        # Record population
        if tick % 100 == 0:
            self.population_history.append({
                "tick": tick,
                "population": len(self.organisms),
                "births": self.total_births,
                "deaths": self.total_deaths,
            })

        return {"tick": tick, "events": events}

    def get_population_stats(self) -> dict:
        """Get population statistics."""
        if not self.organisms:
            return {"total": 0}

        ages = [org.age for org in self.organisms.values()]
        healths = [org.health for org in self.organisms.values()]
        fitnesses = [org.fitness for org in self.organisms.values()]

        return {
            "total": len(self.organisms),
            "avg_age": sum(ages) / len(ages),
            "avg_health": sum(healths) / len(healths),
            "avg_fitness": sum(fitnesses) / len(fitnesses),
            "births": self.total_births,
            "deaths": self.total_deaths,
        }

    def get_statistics(self) -> dict:
        """Get biology statistics."""
        return {
            "species": len(self.species),
            "organisms": len(self.organisms),
            "total_births": self.total_births,
            "total_deaths": self.total_deaths,
            "population_stats": self.get_population_stats(),
        }


# =============================================================================
# Coupling with other sciences
# =============================================================================

# Biology-Ecology coupling
HUMAN_CARRYING_CAPACITY = 10000000  # Earth's carrying capacity for humans
POPULATION_GROWTH_RATE = 0.02  # Per year
PREDATION_RATE = 0.1  # Base predation rate

# Biology-Evolution coupling
MUTATION_RATE = 0.0001  # Per gene per generation
SELECTION_COEFFICIENT = 0.01  # Fitness difference for selection
HERITABILITY = 0.5  # How heritable are traits
