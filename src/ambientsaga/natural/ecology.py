"""
Ecosystem simulation system.

Models:
- Species populations (producers, consumers, decomposers)
- Food webs and trophic levels
- Biogeochemical cycles (carbon, nitrogen, phosphorus)
- Ecological succession
- Invasive species dynamics
- Carrying capacity and population dynamics
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ambientsaga.config import EcologyConfig
from ambientsaga.types import TerrainType

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Species
# ---------------------------------------------------------------------------


@dataclass
class Species:
    """A species in the ecosystem."""

    species_id: str
    name: str
    trophic_level: int  # 0=producer, 1=herbivore, 2=carnivore, 3=top predator
    diet: tuple[str, ...]  # Types of food consumed
    habitat: list[TerrainType]  # Suitable habitats
    reproduction_rate: float  # Per-capita reproduction per year
    mortality_rate: float  # Base mortality per year
    carrying_capacity: float  # Max population per unit area
    migration_enabled: bool = True
    keystone: bool = False  # Disproportionate ecosystem impact

    def __post_init__(self) -> None:
        # Validate trophic level
        if self.trophic_level < 0 or self.trophic_level > 3:
            raise ValueError(f"Invalid trophic level: {self.trophic_level}")


class Ecosystem:
    """
    Ecosystem simulation.

    Tracks species populations across the world and models:
    - Population dynamics (birth, death, migration)
    - Food web relationships (predator-prey)
    - Biogeochemical cycles (carbon, nitrogen)
    - Ecological succession
    - Invasive species
    """

    def __init__(
        self, config: EcologyConfig, width: int, height: int, seed: int = 42
    ) -> None:
        self.config = config
        self.width = width
        self.height = height
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Species registry
        self._species: dict[str, Species] = {}
        self._population: dict[str, np.ndarray] = {}  # species_id -> [H, W] population

        # Biogeochemical cycles
        self._carbon: np.ndarray | None = None  # g C/m² in vegetation
        self._nitrogen: np.ndarray | None = None  # g N/m² in soil
        self._phosphorus: np.ndarray | None = None  # g P/m² in soil

        # Succession state
        self._succession_stage: np.ndarray | None = None  # 0-10

        # Initialize species
        self._initialize_species()

    def _initialize_species(self) -> None:
        """Initialize the species pool."""
        # Producers (trophic level 0)
        self._add_species(
            Species(
                species_id="grass",
                name="Grass",
                trophic_level=0,
                diet=(),
                habitat=[TerrainType.GRASSLAND, TerrainType.SAVANNA],
                reproduction_rate=2.0,
                mortality_rate=0.1,
                carrying_capacity=500.0,
            )
        )
        self._add_species(
            Species(
                species_id="forest",
                name="Forest",
                trophic_level=0,
                diet=(),
                habitat=[
                    TerrainType.TEMPERATE_FOREST,
                    TerrainType.TROPICAL_FOREST,
                    TerrainType.BOREAL_FOREST,
                    TerrainType.RAINFOREST,
                ],
                reproduction_rate=0.3,
                mortality_rate=0.02,
                carrying_capacity=300.0,
            )
        )
        self._add_species(
            Species(
                species_id="phytoplankton",
                name="Phytoplankton",
                trophic_level=0,
                diet=(),
                habitat=[TerrainType.SHALLOW_WATER],
                reproduction_rate=10.0,
                mortality_rate=0.5,
                carrying_capacity=1000.0,
            )
        )

        # Primary consumers (trophic level 1)
        self._add_species(
            Species(
                species_id="rabbit",
                name="Rabbit",
                trophic_level=1,
                diet=("grass",),
                habitat=[
                    TerrainType.GRASSLAND,
                    TerrainType.SAVANNA,
                    TerrainType.DESERT_SCRUB,
                ],
                reproduction_rate=3.0,
                mortality_rate=0.3,
                carrying_capacity=50.0,
            )
        )
        self._add_species(
            Species(
                species_id="deer",
                name="Deer",
                trophic_level=1,
                diet=("grass", "forest"),
                habitat=[
                    TerrainType.TEMPERATE_FOREST,
                    TerrainType.GRASSLAND,
                    TerrainType.SAVANNA,
                ],
                reproduction_rate=0.5,
                mortality_rate=0.15,
                carrying_capacity=20.0,
            )
        )
        self._add_species(
            Species(
                species_id="fish",
                name="Fish",
                trophic_level=1,
                diet=("phytoplankton",),
                habitat=[TerrainType.SHALLOW_WATER],
                reproduction_rate=2.0,
                mortality_rate=0.2,
                carrying_capacity=200.0,
            )
        )

        # Secondary consumers (trophic level 2)
        self._add_species(
            Species(
                species_id="wolf",
                name="Wolf",
                trophic_level=2,
                diet=("rabbit", "deer"),
                habitat=[
                    TerrainType.TEMPERATE_FOREST,
                    TerrainType.BOREAL_FOREST,
                    TerrainType.GRASSLAND,
                ],
                reproduction_rate=0.3,
                mortality_rate=0.1,
                carrying_capacity=5.0,
                keystone=True,
            )
        )
        self._add_species(
            Species(
                species_id="hawk",
                name="Hawk",
                trophic_level=2,
                diet=("rabbit", "snake"),
                habitat=[
                    TerrainType.GRASSLAND,
                    TerrainType.SAVANNA,
                    TerrainType.HILLS,
                    TerrainType.DESERT,
                ],
                reproduction_rate=0.4,
                mortality_rate=0.1,
                carrying_capacity=3.0,
            )
        )

        # Tertiary consumers (trophic level 3)
        self._add_species(
            Species(
                species_id="lion",
                name="Lion",
                trophic_level=3,
                diet=("deer", "rabbit"),
                habitat=[TerrainType.SAVANNA, TerrainType.GRASSLAND],
                reproduction_rate=0.2,
                mortality_rate=0.05,
                carrying_capacity=2.0,
                keystone=True,
            )
        )

        # Decomposers (trophic level 4, implicit)
        self._add_species(
            Species(
                species_id="bacteria",
                name="Decomposer Bacteria",
                trophic_level=0,  # Treat as producer for simplicity
                diet=(),
                habitat=[t for t in TerrainType if t.is_land],
                reproduction_rate=20.0,
                mortality_rate=0.1,
                carrying_capacity=10000.0,
            )
        )

    def _add_species(self, species: Species) -> None:
        """Register a species and initialize its population map."""
        self._species[species.species_id] = species
        self._population[species.species_id] = np.zeros(
            (self.height, self.width), dtype=np.float64
        )

    def initialize(
        self,
        terrain: np.ndarray,
        vegetation: np.ndarray,
    ) -> None:
        """Initialize ecosystem from terrain."""
        H, W = terrain.shape

        # Initialize biogeochemical cycles
        self._carbon = np.zeros((H, W), dtype=np.float64)
        self._nitrogen = np.zeros((H, W), dtype=np.float64)
        self._phosphorus = np.zeros((H, W), dtype=np.float64)
        self._succession_stage = np.zeros((H, W), dtype=np.float64)

        # Seed populations based on terrain
        for y in range(H):
            for x in range(W):
                t = TerrainType(terrain[y, x])

                # Grass
                if t in [TerrainType.GRASSLAND, TerrainType.SAVANNA]:
                    self._population["grass"][y, x] = self._rng.uniform(100, 400)
                    self._carbon[y, x] = self._rng.uniform(200, 800)
                    self._succession_stage[y, x] = 5.0

                # Forest
                elif t.is_forest:
                    self._population["forest"][y, x] = self._rng.uniform(50, 250)
                    self._carbon[y, x] = self._rng.uniform(500, 2000)
                    self._succession_stage[y, x] = 8.0

                # Aquatic
                elif t == TerrainType.SHALLOW_WATER:
                    self._population["phytoplankton"][y, x] = self._rng.uniform(
                        100, 800
                    )

                # Initialize soil nutrients
                self._nitrogen[y, x] = self._rng.uniform(1, 10)  # g N/m²
                self._phosphorus[y, x] = self._rng.uniform(0.1, 2)  # g P/m²

        # Initialize animal populations
        for species_id in ["rabbit", "deer", "fish", "wolf", "hawk", "lion"]:
            if species_id in self._population:
                for y in range(H):
                    for x in range(W):
                        species = self._species[species_id]
                        if TerrainType(terrain[y, x]) in species.habitat:
                            if self._rng.random() < 0.1:
                                self._population[species_id][y, x] = self._rng.uniform(
                                    0, species.carrying_capacity * 0.5
                                )

    def update(
        self,
        tick: int,
        vegetation: np.ndarray,
        terrain: np.ndarray,
        temperature: np.ndarray,
    ) -> None:
        """
        Update ecosystem for one tick.

        Process:
        1. Update plant populations (production)
        2. Update consumer populations (lotka-volterra dynamics)
        3. Update biogeochemical cycles
        4. Update succession
        5. Handle extinctions and invasions
        """
        H, W = terrain.shape

        # Per-tick rates (convert from annual)
        dt = 1.0 / 365.0

        # Update each species
        for species_id, species in self._species.items():
            pop = self._population[species_id]

            for y in range(H):
                for x in range(W):
                    if TerrainType(terrain[y, x]) not in species.habitat:
                        pop[y, x] *= 0.95  # Slow die-off
                        continue

                    current = pop[y, x]
                    if current <= 0:
                        continue

                    # Base growth rate
                    r = species.reproduction_rate * dt

                    # Carrying capacity
                    K = species.carrying_capacity

                    # Temperature effect on growth
                    temp = temperature[y, x]
                    if temp < 0 or temp > 40:
                        r *= 0.1  # Stress
                    elif 15 < temp < 30:
                        r *= 1.2  # Optimal

                    # For herbivores: food availability
                    if species.trophic_level == 1:
                        # Find food species
                        food_total = 0.0
                        for food_id in species.diet:
                            if food_id in self._population:
                                food_total += self._population[food_id][y, x]
                        if food_total > 0:
                            r *= min(1.0, food_total / 100.0)
                        else:
                            r *= 0.1  # Starvation

                    # For carnivores: prey availability
                    elif species.trophic_level >= 2:
                        prey_total = 0.0
                        for prey_id in species.diet:
                            if prey_id in self._population:
                                prey_total += self._population[prey_id][y, x]
                        if prey_total > 0:
                            r *= min(1.0, prey_total / 20.0) * 0.5
                        else:
                            r *= 0.05  # Hard to hunt without prey

                    # Logistic growth with harvesting
                    # dN/dt = r*N*(1 - N/K)
                    growth = r * current * (1.0 - current / K)

                    # Mortality
                    mortality = species.mortality_rate * dt * current

                    # Update
                    pop[y, x] = max(0.0, current + growth - mortality)

                    # Migration (diffusion)
                    if species.migration_enabled and self._rng.random() < 0.01:
                        self._migrate(species_id, x, y, terrain)

            # Trophic cascade for keystone species
            if species.keystone and species.trophic_level == 2:
                # Wolves reduce deer, which allows forest regrowth
                wolf_pop = self._population[species_id]
                if "deer" in self._population and "forest" in self._population:
                    deer_pop = self._population["deer"]
                    forest_pop = self._population["forest"]
                    avg_wolves = float(np.mean(wolf_pop))
                    if avg_wolves > 1.0:
                        # Wolves keep deer in check → forest recovers
                        for y in range(H):
                            for x in range(W):
                                if TerrainType(terrain[y, x]) in [
                                    TerrainType.TEMPERATE_FOREST,
                                    TerrainType.SAVANNA,
                                ]:
                                    if deer_pop[y, x] > 10:
                                        forest_pop[y, x] *= 1.001  # Slow forest regrowth

        # Update biogeochemical cycles
        if self.config.carbon_cycle_enabled:
            self._update_carbon_cycle(vegetation, temperature, terrain)

        if self.config.nitrogen_cycle_enabled:
            self._update_nitrogen_cycle(vegetation, terrain)

        # Update ecological succession
        if self.config.succession_enabled:
            self._update_succession(terrain, vegetation)

    def _migrate(
        self, species_id: str, x: int, y: int, terrain: np.ndarray
    ) -> None:
        """Migrate a species to an adjacent tile."""
        H, W = terrain.shape
        species = self._species[species_id]
        pop = self._population[species_id]

        # Random direction
        dx, dy = self._rng.integers(-1, 2, size=2)
        nx, ny = x + dx, y + dy
        if 0 <= nx < W and 0 <= ny < H:
            if TerrainType(terrain[ny, nx]) in species.habitat:
                amount = pop[y, x] * 0.05  # 5% migrates
                pop[y, x] -= amount
                pop[ny, nx] += amount

    def _update_carbon_cycle(
        self, vegetation: np.ndarray, temperature: np.ndarray, terrain: np.ndarray
    ) -> None:
        """Update carbon sequestration and release."""
        if self._carbon is None:
            return
        H, W = terrain.shape

        for y in range(H):
            for x in range(W):
                t = TerrainType(terrain[y, x])
                if not t.is_land:
                    continue

                veg = vegetation[y, x] if vegetation is not None else 0.5

                # Photosynthesis (carbon uptake)
                if t.is_forest:
                    photosynthesis = veg * 5.0 * (temperature[y, x] / 25.0)
                elif t in [TerrainType.GRASSLAND, TerrainType.SAVANNA]:
                    photosynthesis = veg * 2.0 * (temperature[y, x] / 25.0)
                else:
                    photosynthesis = 0.0

                # Respiration (carbon release)
                respiration = float(self._carbon[y, x]) * 0.01

                # Fire release
                fire_release = 0.0
                if t.is_forest and self._rng.random() < 0.0001:  # Fire probability
                    fire_release = float(self._carbon[y, x]) * 0.5

                self._carbon[y, x] += photosynthesis - respiration - fire_release
                self._carbon[y, x] = max(0.0, self._carbon[y, x])

    def _update_nitrogen_cycle(self, vegetation: np.ndarray, terrain: np.ndarray) -> None:
        """Update nitrogen fixation and cycling."""
        if self._nitrogen is None:
            return
        H, W = terrain.shape

        for y in range(H):
            for x in range(W):
                t = TerrainType(terrain[y, x])
                if not t.is_land:
                    continue

                # Biological nitrogen fixation (by legumes, etc.)
                if t in [TerrainType.GRASSLAND, TerrainType.SAVANNA]:
                    fixation = 0.01  # g N/m²/year
                elif t.is_forest:
                    fixation = 0.005
                else:
                    fixation = 0.001

                # Deposition from atmosphere
                deposition = 0.005

                # Denitrification (loss)
                if float(self._nitrogen[y, x]) > 5.0:
                    denitrification = float(self._nitrogen[y, x]) * 0.001
                else:
                    denitrification = 0.0

                self._nitrogen[y, x] += fixation + deposition - denitrification
                self._nitrogen[y, x] = max(0.0, self._nitrogen[y, x])

    def _update_succession(self, terrain: np.ndarray, vegetation: np.ndarray) -> None:
        """Update ecological succession stages."""
        if self._succession_stage is None:
            return
        H, W = terrain.shape

        for y in range(H):
            for x in range(W):
                t = TerrainType(terrain[y, x])
                stage = self._succession_stage[y, x]

                # Succession progress based on time since disturbance
                if stage < 10.0:
                    if t.is_forest:
                        self._succession_stage[y, x] += 0.01  # Progress toward climax
                    elif t in [TerrainType.GRASSLAND, TerrainType.SAVANNA]:
                        self._succession_stage[y, x] += 0.005
                    else:
                        self._succession_stage[y, x] += 0.001

                # Climax community
                self._succession_stage[y, x] = min(10.0, stage)

    def get_biodiversity(self, x: int, y: int) -> float:
        """Get biodiversity index (Simpson's Diversity Index) at a position."""
        H, W = terrain.shape
        populations: list[float] = []

        for species_id, pop in self._population.items():
            if 0 <= y < H and 0 <= x < W:
                populations.append(float(pop[y, x]))

        if not populations:
            return 0.0

        total = sum(populations)
        if total <= 0:
            return 0.0

        # Simpson's Diversity Index
        sum_sq = sum((p / total) ** 2 for p in populations if p > 0)
        return 1.0 - sum_sq

    def get_total_biomass(self) -> float:
        """Get total ecosystem biomass."""
        total = 0.0
        for species_id, pop in self._population.items():
            species = self._species[species_id]
            # Approximate biomass: trophic level determines individual size
            mass_factor = 10.0 ** species.trophic_level  # 10x per level
            total += float(np.sum(pop)) * mass_factor
        return total

    def get_species_count(self) -> int:
        """Get number of species in the ecosystem."""
        return len(self._species)

    def get_population(self, species_id: str, x: int, y: int) -> float:
        """Get population of a species at a position."""
        if species_id not in self._population:
            return 0.0
        return float(self._population[species_id][y, x])

    def get_stats(self) -> dict:
        """Get ecosystem statistics."""
        stats = {
            "species_count": self.get_species_count(),
            "total_biomass": self.get_total_biomass(),
        }

        # Carbon budget
        if self._carbon is not None:
            stats["total_carbon_g_m2"] = float(np.mean(self._carbon))
            stats["total_vegetation_carbon"] = float(np.sum(self._carbon))

        # Biodiversity
        if self._succession_stage is not None:
            stats["avg_succession_stage"] = float(np.mean(self._succession_stage))

        # Population totals
        for species_id in list(self._species.keys())[:10]:  # Top 10 species
            if species_id in self._population:
                stats[f"pop_{species_id}"] = float(np.sum(self._population[species_id]))

        return stats
