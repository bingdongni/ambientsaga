"""
Ecology Engine — Ecosystem Dynamics and Interactions

Provides a simplified but principled ecology simulation:
- Food chains and food webs
- Trophic levels and energy transfer
- Nutrient cycles (carbon, nitrogen, phosphorus)
- Population dynamics (predator-prey, competition)
- Ecosystem succession
- Biomes and habitats

Ecology emerges from biology (ecosystem dynamics).
Human social systems emerge from ecology (resource constraints).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum


class TrophicLevel(Enum):
    """Trophic levels in an ecosystem."""
    PRODUCER = "producer"  # Plants, algae (primary production)
    PRIMARY_CONSUMER = "primary_consumer"  # Herbivores
    SECONDARY_CONSUMER = "secondary_consumer"  # Carnivores (eat herbivores)
    TERTIARY_CONSUMER = "tertiary_consumer"  # Top predators
    DECOMPOSER = "decomposer"  # Fungi, bacteria
    DETRITIVORE = "detritivore"  # Eat dead matter


@dataclass
class Species:
    """A species in an ecosystem."""
    species_id: str
    name: str
    trophic_level: TrophicLevel

    # Population
    population: int = 0
    carrying_capacity: int = 1000  # Environment's limit

    # Reproduction
    reproduction_rate: float = 0.1  # Per individual per year
    gestation_period: int = 0  # Days
    clutch_size: int = 1
    age_at_maturity: int = 365  # Days

    # Survival
    natural_mortality: float = 0.01  # Per individual per year
    predation_rate: float = 0.0  # How much this species is predated
    disease_rate: float = 0.001

    # Energy
    energy_efficiency: float = 0.1  # How efficiently converts food to biomass
    daily_food_requirement: float = 1.0  # kg/day
    biomass_per_individual: float = 1.0  # kg

    # Diet (for consumers)
    diet: dict[str, float] = field(default_factory=dict)  # species_id -> proportion

    # Habitat
    habitat_types: list[str] = field(default_factory=list)
    temperature_range: tuple[float, float] = (-20, 40)  # Celsius
    humidity_range: tuple[float, float] = (0, 1)  # 0-1

    def get_biomass(self) -> float:
        """Get total biomass of species."""
        return self.population * self.biomass_per_individual

    def get_food_requirement(self) -> float:
        """Get total daily food requirement."""
        return self.population * self.daily_food_requirement

    def can_survive(self, temperature: float, humidity: float) -> bool:
        """Check if conditions are survivable."""
        min_temp, max_temp = self.temperature_range
        min_hum, max_hum = self.humidity_range
        return min_temp <= temperature <= max_temp and min_hum <= humidity <= max_hum


@dataclass
class Population:
    """A population of a species in a location."""
    population_id: str
    species: Species
    location: tuple[int, int]  # Grid cell
    population_size: int = 0

    # Dynamics
    birth_rate: float = 0.0
    death_rate: float = 0.0
    immigration_rate: float = 0.0
    emigration_rate: float = 0.0

    # Age structure
    juveniles: int = 0
    adults: int = 0
    seniors: int = 0

    # Health
    avg_health: float = 1.0
    disease_prevalence: float = 0.0

    def get_total_individuals(self) -> int:
        return self.juveniles + self.adults + self.seniors

    def get_growth_rate(self) -> float:
        """Calculate intrinsic growth rate."""
        births = self.birth_rate + self.immigration_rate
        deaths = self.death_rate + self.emigration_rate
        return births - deaths


@dataclass
class FoodChain:
    """A food chain connecting species."""
    chain_id: str
    species: list[Species]  # Ordered from producer to top predator
    energy_transfer_efficiency: float = 0.1  # 10% typical

    def get_trophic_position(self, species: Species) -> int:
        """Get trophic position (1 = producer)."""
        try:
            return self.species.index(species) + 1
        except ValueError:
            return 0

    def get_prey(self, species: Species) -> list[Species]:
        """Get prey species."""
        pos = self.get_trophic_position(species)
        if pos > 1 and pos <= len(self.species):
            return [self.species[pos - 2]]  # Previous level
        return []

    def get_predators(self, species: Species) -> list[Species]:
        """Get predator species."""
        pos = self.get_trophic_position(species)
        if 0 < pos < len(self.species):
            return [self.species[pos]]  # Next level
        return []


@dataclass
class NutrientCycle:
    """A nutrient cycle (carbon, nitrogen, phosphorus, etc.)."""
    cycle_id: str
    name: str

    # Reservoirs (pools)
    reservoirs: dict[str, float] = field(default_factory=dict)  # name -> amount (Pg for carbon)

    # Fluxes (movements between reservoirs)
    fluxes: dict[str, float] = field(default_factory=dict)  # "reservoir1->reservoir2" -> flux rate

    # Residence times
    residence_times: dict[str, float] = field(default_factory=dict)  # name -> years

    # Perturbations
    human_perturbation: float = 0.0  # Anthropogenic changes

    def get_concentration(self, reservoir: str) -> float:
        """Get concentration in reservoir."""
        return self.reservoirs.get(reservoir, 0.0)

    def add_flux(
        self,
        source: str,
        sink: str,
        rate: float,
    ) -> None:
        """Add a flux between reservoirs."""
        key = f"{source}->{sink}"
        self.fluxes[key] = self.fluxes.get(key, 0.0) + rate

    def update(self, dt: float = 1.0) -> dict:
        """Update nutrient cycle."""
        changes = {}

        # Update reservoirs based on fluxes
        for flux_key, rate in self.fluxes.items():
            source, sink = flux_key.split("->")
            amount = rate * dt * (1 - self.human_perturbation)

            if source in self.reservoirs and sink in self.reservoirs:
                self.reservoirs[source] -= amount
                self.reservoirs[sink] += amount
                changes[flux_key] = amount

        # Ensure non-negative
        for reservoir in self.reservoirs:
            if self.reservoirs[reservoir] < 0:
                self.reservoirs[reservoir] = 0

        return changes


@dataclass
class Habitat:
    """A habitat/ecosystem."""
    habitat_id: str
    name: str
    biome: str  # desert, forest, grassland, etc.
    location: tuple[int, int]  # Grid position
    size: float = 1.0  # km^2

    # Environment
    temperature: float = 20.0  # Celsius
    humidity: float = 0.5  # 0-1
    precipitation: float = 1.0  # m/year
    altitude: float = 0.0  # m
    primary_productivity: float = 1000.0  # gC/m^2/year

    # Resources
    resources: dict[str, float] = field(default_factory=dict)
    carrying_capacity: int = 1000  # Total individuals

    # Species
    populations: dict[str, Population] = field(default_factory=dict)

    # Health
    biodiversity_index: float = 0.0  # 0-1
    ecosystem_health: float = 1.0  # 0-1

    def get_total_population(self) -> int:
        """Get total population across all species."""
        return sum(p.population_size for p in self.populations.values())

    def get_biomass(self) -> float:
        """Get total biomass."""
        total = 0.0
        for pop in self.populations.values():
            total += pop.population_size * pop.species.biomass_per_individual
        return total

    def update(self, dt: float = 1.0) -> dict:
        """Update habitat state."""
        # Update primary productivity based on environment
        temp_factor = max(0, 1 - abs(self.temperature - 25) / 25)
        water_factor = min(1, self.precipitation / 2)  # Optimal at 2m/year
        self.primary_productivity *= (temp_factor * water_factor + 0.1)

        # Update biodiversity
        if self.populations:
            species_count = len([p for p in self.populations.values() if p.population_size > 0])
            self.biodiversity_index = min(1.0, species_count / 10)

        # Update ecosystem health
        health_factors = [
            self.biodiversity_index,
            temp_factor,
            water_factor,
        ]
        self.ecosystem_health = sum(health_factors) / len(health_factors)

        return {
            "primary_productivity": self.primary_productivity,
            "biodiversity": self.biodiversity_index,
            "health": self.ecosystem_health,
        }


@dataclass
class Ecosystem:
    """A complete ecosystem."""
    ecosystem_id: str
    name: str

    # Components
    habitats: dict[str, Habitat] = field(default_factory=dict)
    species: dict[str, Species] = field(default_factory=dict)
    food_chains: list[FoodChain] = field(default_factory=list)
    nutrient_cycles: dict[str, NutrientCycle] = field(default_factory=dict)

    # Interactions
    predation_events: list[tuple[int, str, str, int]] = field(default_factory=list)  # tick, pred, prey, count

    def get_species_in_habitat(self, habitat_id: str) -> list[Species]:
        """Get all species in a habitat."""
        habitat = self.habitats.get(habitat_id)
        if not habitat:
            return []
        return [pop.species for pop in habitat.populations.values()]

    def simulate_predation(
        self,
        predator: Species,
        prey: Species,
        predation_rate: float,
    ) -> tuple[int, float]:
        """Simulate predation event, return (kills, biomass_transferred)."""
        # Number of kills
        max_prey = prey.population
        max_predations = int(predator.population * predation_rate)
        kills = min(max_prey, max_predations)

        # Update populations
        prey.population -= kills
        predator.population += int(kills * predator.energy_efficiency)

        # Energy transfer
        biomass = kills * prey.biomass_per_individual * predator.energy_efficiency

        return kills, biomass


class EcosystemEngine:
    """
    Ecosystem simulation engine.

    Provides ecological systems and dynamics.
    Couples with:
    - Physics: Energy flow, thermodynamics
    - Chemistry: Nutrient cycles, pollution
    - Biology: Population dynamics, species
    - Social: Resource use, land use
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

        # Global ecosystems
        self.ecosystems: dict[str, Ecosystem] = {}
        self.global_cycles: dict[str, NutrientCycle] = {}

        # Statistics
        self.total_biomass = 0.0
        self.primary_productivity = 0.0
        self.biodiversity = 0.0
        self.predation_events = 0

        # Initialize nutrient cycles
        self._init_nutrient_cycles()

    def _init_nutrient_cycles(self) -> None:
        """Initialize global nutrient cycles."""

        # Carbon cycle
        carbon = NutrientCycle(
            cycle_id="carbon",
            name="Carbon Cycle",
        )
        carbon.reservoirs = {
            "atmosphere": 850.0,  # Pg C
            "terrestrial_biosphere": 2500.0,
            "ocean_surface": 1000.0,
            "ocean_deep": 38000.0,
            "geosphere": 100000000.0,
        }
        carbon.fluxes = {
            "atmosphere->terrestrial_biosphere": 120.0,  # Photosynthesis
            "terrestrial_biosphere->atmosphere": 120.0,  # Respiration
            "atmosphere->ocean_surface": 92.0,  # Gas exchange
            "ocean_surface->atmosphere": 90.0,
            "ocean_surface->ocean_deep": 100.0,  # Thermohaline
            "terrestrial_biosphere->geosphere": 0.5,  # Burial
        }
        self.global_cycles["carbon"] = carbon

        # Nitrogen cycle
        nitrogen = NutrientCycle(
            cycle_id="nitrogen",
            name="Nitrogen Cycle",
        )
        nitrogen.reservoirs = {
            "atmosphere": 3900000.0,  # Tg N
            "terrestrial_biosphere": 12000.0,
            "soils": 170000.0,
            "oceans": 650000.0,
        }
        nitrogen.fluxes = {
            "atmosphere->terrestrial_biosphere": 413.0,  # N fixation
            "atmosphere->soils": 30.0,  # Deposition
            "terrestrial_biosphere->atmosphere": 519.0,  # Denitrification
            "soils->terrestrial_biosphere": 1000.0,  # Uptake
            "oceans->atmosphere": 40.0,
        }
        self.global_cycles["nitrogen"] = nitrogen

        # Water cycle
        water = NutrientCycle(
            cycle_id="water",
            name="Water Cycle",
        )
        water.reservoirs = {
            "oceans": 1350000000.0,  # km^3
            "ice": 24340000.0,
            "groundwater": 23400000.0,
            "lakes": 176400.0,
            "rivers": 2120.0,
            "atmosphere": 12900.0,
            "biosphere": 1120.0,
        }
        water.fluxes = {
            "oceans->atmosphere": 434.0,  # Evaporation
            "ice->atmosphere": 7.0,
            "lakes->atmosphere": 70.0,
            "rivers->atmosphere": 45.0,
            "atmosphere->oceans": 398.0,  # Precipitation
            "atmosphere->ice": 7.0,
            "atmosphere->lakes": 108.0,
            "atmosphere->rivers": 43.0,
            "biosphere->atmosphere": 12.0,  # Transpiration
        }
        self.global_cycles["water"] = water

        # Phosphorus cycle
        phosphorus = NutrientCycle(
            cycle_id="phosphorus",
            name="Phosphorus Cycle",
        )
        phosphorus.reservoirs = {
            "geosphere": 30000000000.0,  # Tg P
            "soils": 300000.0,
            "terrestrial_biosphere": 3000.0,
            "oceans": 90000.0,
            "sediments": 30000000000.0,
        }
        phosphorus.fluxes = {
            "geosphere->soils": 5.0,  # Weathering
            "soils->terrestrial_biosphere": 30.0,  # Uptake
            "terrestrial_biosphere->soils": 28.0,  # Decomposition
            "soils->oceans": 2.0,  # Erosion
            "oceans->sediments": 2.0,  # Burial
        }
        self.global_cycles["phosphorus"] = phosphorus

    def create_ecosystem(self, ecosystem_id: str, name: str) -> Ecosystem:
        """Create a new ecosystem."""
        eco = Ecosystem(ecosystem_id=ecosystem_id, name=name)
        self.ecosystems[ecosystem_id] = eco
        return eco

    def create_habitat(
        self,
        ecosystem_id: str,
        habitat_id: str,
        biome: str,
        location: tuple[int, int],
    ) -> Habitat:
        """Create a habitat in an ecosystem."""
        if ecosystem_id not in self.ecosystems:
            self.create_ecosystem(ecosystem_id, ecosystem_id)

        eco = self.ecosystems[ecosystem_id]
        habitat = Habitat(
            habitat_id=habitat_id,
            name=habitat_id,
            biome=biome,
            location=location,
        )
        eco.habitats[habitat_id] = habitat
        return habitat

    def create_species(
        self,
        ecosystem_id: str,
        species_id: str,
        name: str,
        trophic_level: TrophicLevel,
        population: int = 100,
    ) -> Species:
        """Create a species in an ecosystem."""
        if ecosystem_id not in self.ecosystems:
            self.create_ecosystem(ecosystem_id, ecosystem_id)

        eco = self.ecosystems[ecosystem_id]
        species = Species(
            species_id=species_id,
            name=name,
            trophic_level=trophic_level,
            population=population,
        )
        eco.species[species_id] = species
        return species

    def update(self, tick: int, dt: float = 1.0) -> dict:
        """Update all ecosystems."""
        global_changes = {}

        # Update global nutrient cycles
        for cycle_id, cycle in self.global_cycles.items():
            changes = cycle.update(dt)
            global_changes[cycle_id] = changes

        # Update all ecosystems
        for eco in self.ecosystems.values():
            self._update_ecosystem(eco, tick, dt)

        # Calculate global statistics
        self._calculate_statistics()

        return global_changes

    def _update_ecosystem(self, eco: Ecosystem, tick: int, dt: float) -> None:
        """Update a single ecosystem."""
        # Update habitats
        for habitat in eco.habitats.values():
            habitat.update(dt)

            # Update populations
            for pop in habitat.populations.values():
                # Apply logistic growth
                K = pop.species.carrying_capacity
                N = pop.population_size
                r = pop.species.reproduction_rate

                # Logistic growth with density dependence
                growth = r * N * (1 - N / K) * dt

                # Apply mortality
                mortality = pop.species.natural_mortality * N * dt
                if pop.disease_prevalence > 0:
                    mortality += pop.disease_prevalence * N * dt * 0.1

                # Apply to population
                new_pop = max(0, int(N + growth - mortality))
                pop.population_size = new_pop

                # Update age structure
                if pop.species.age_at_maturity > 0:
                    maturity_ratio = 365 / pop.species.age_at_maturity
                    pop.juveniles = int(new_pop * min(1, maturity_ratio))
                    pop.adults = int(new_pop * (1 - min(1, maturity_ratio)))
                    pop.seniors = 0

        # Simulate predation
        self._simulate_predation(eco, tick, dt)

        # Update food chains
        for chain in eco.food_chains:
            self._update_food_chain(chain, dt)

    def _simulate_predation(self, eco: Ecosystem, tick: int, dt: float) -> None:
        """Simulate predation in an ecosystem."""
        for chain in eco.food_chains:
            for i, predator in enumerate(chain.species):
                if predator.trophic_level == TrophicLevel.PRODUCER:
                    continue

                # Find prey
                prey_list = chain.get_prey(predator)
                for prey in prey_list:
                    if prey.population <= 0 or predator.population <= 0:
                        continue

                    # Predation rate depends on predator and prey populations
                    rate = min(predator.predation_rate, prey.population / predator.population)
                    kills, biomass = eco.simulate_predation(
                        predator, prey, rate * dt
                    )

                    if kills > 0:
                        eco.predation_events.append((tick, predator.species_id, prey.species_id, kills))
                        self.predation_events += kills

    def _update_food_chain(self, chain: FoodChain, dt: float) -> None:
        """Update a food chain."""
        # Calculate energy transfer between trophic levels
        for i in range(len(chain.species) - 1):
            producer = chain.species[i]
            consumer = chain.species[i + 1]

            if producer.population <= 0:
                continue

            # Energy available to consumer
            producer_biomass = producer.get_biomass()
            energy_available = producer_biomass * chain.energy_transfer_efficiency

            # Consumer's food requirement
            food_required = consumer.get_food_requirement()

            # If not enough food, consumer population decreases
            if energy_available < food_required:
                consumer.population = int(consumer.population * 0.95)
            else:
                # Consumer population stable or growing
                pass

    def _calculate_statistics(self) -> None:
        """Calculate global ecological statistics."""
        total_pop = 0
        total_biomass = 0.0
        species_count = 0

        for eco in self.ecosystems.values():
            for habitat in eco.habitats.values():
                total_pop += habitat.get_total_population()
                total_biomass += habitat.get_biomass()
            species_count += len(eco.species)

        self.total_biomass = total_biomass
        self.biodiversity = species_count / max(1, sum(len(e.species) for e in self.ecosystems.values()))

    def get_global_carbon_balance(self) -> dict:
        """Get global carbon balance."""
        carbon = self.global_cycles.get("carbon")
        if not carbon:
            return {}

        return {
            "atmosphere": carbon.reservoirs.get("atmosphere", 0),
            "terrestrial": carbon.reservoirs.get("terrestrial_biosphere", 0),
            "ocean": carbon.reservoirs.get("ocean_surface", 0) + carbon.reservoirs.get("ocean_deep", 0),
            "human_perturbation": carbon.human_perturbation,
        }

    def apply_human_impact(
        self,
        co2_emissions: float,
        deforestation_rate: float,
        pollution_rate: float,
    ) -> None:
        """Apply human impacts to ecosystems."""
        # Update carbon cycle
        carbon = self.global_cycles.get("carbon")
        if carbon:
            # Add CO2 to atmosphere
            carbon.reservoirs["atmosphere"] += co2_emissions
            carbon.reservoirs["terrestrial_biosphere"] -= deforestation_rate
            carbon.human_perturbation = min(1.0, carbon.human_perturbation + 0.01)

        # Update nitrogen cycle
        nitrogen = self.global_cycles.get("nitrogen")
        if nitrogen:
            # Fertilizer use increases nitrogen flux
            nitrogen.fluxes["atmosphere->soils"] += pollution_rate

    def get_statistics(self) -> dict:
        """Get ecology statistics."""
        return {
            "ecosystems": len(self.ecosystems),
            "habitats": sum(len(e.habitats) for e in self.ecosystems.values()),
            "species": sum(len(e.species) for e in self.ecosystems.values()),
            "total_biomass": self.total_biomass,
            "biodiversity": self.biodiversity,
            "predation_events": self.predation_events,
            "carbon_balance": self.get_global_carbon_balance(),
        }


# =============================================================================
# Coupling constants
# =============================================================================

# Ecology-Human coupling
HUMAN_ECOLOGICAL_FOOTPRINT = 1.7  # global hectares per person
EARTH_CARRYING_CAPACITY = 12000000000  # humans
BIODIVERSITY_THRESHOLD = 0.3  # Below this, ecosystem collapses

# Ecology-Economy coupling
ECOSYSTEM_SERVICE_VALUE = 33000000  # $ per year globally
RESOURCE_DEPLETION_RATE = 0.01  # Per year
POLLUTION_EXTERNALITY = 0.1  # Cost multiplier
