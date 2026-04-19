"""
Production system — crafting, farming, mining, building, and resource transformation.

This module handles all production activities in the world:
- Crafting: transforming raw materials into tools/goods
- Farming: agricultural production with seasonal cycles
- Mining: extracting minerals from terrain
- Building: constructing structures and settlements
- Processing: refining raw resources into intermediate goods

Production is organized into WorkSites that agents interact with.
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING, Any
from dataclasses import dataclass, field
from enum import Enum, auto
import random

from ambientsaga.config import EconomyConfig
from ambientsaga.types import (
    EntityID, Pos2D, ResourceType, new_entity_id, TerrainType
)

if TYPE_CHECKING:
    from ambientsaga.world.state import World
    from ambientsaga.agents.agent import Agent


# ---------------------------------------------------------------------------
# Production Types
# ---------------------------------------------------------------------------


class ProductionType(Enum):
    """Types of production activities."""

    GATHERING = auto()       # Basic foraging/hunting
    FARMING = auto()         # Agriculture
    MINING = auto()          # Extracting minerals
    FISHING = auto()         # Water-based food source
    HUNTING = auto()         # Hunting wild animals
    LOGGING = auto()          # Harvesting wood
    QUARRYING = auto()        # Stone extraction
    CRAFTING = auto()         # Manufacturing goods
    BUILDING = auto()         # Construction
    BREEDING = auto()        # Animal husbandry
    PROCESSING = auto()       # Refining/complex production


@dataclass
class Recipe:
    """
    A recipe defines how inputs are transformed into outputs.

    Example: 10 wood + 5 stone → 1 anvil (requires skill: crafting ≥ 0.5)
    """

    recipe_id: str
    name: str
    production_type: ProductionType
    inputs: dict[ResourceType, float]
    outputs: dict[ResourceType, float]
    duration_ticks: int = 10  # Time to complete one production cycle
    base_efficiency: float = 1.0
    required_skills: dict[str, float] = field(default_factory=dict)
    required_terrain: list[TerrainType] = field(default_factory=list)
    required_structures: list[str] = field(default_factory=list)
    labor_required: float = 1.0  # Number of workers
    description: str = ""

    def can_produce(
        self,
        agent: "Agent",
        world: "World",
        inventory: dict[ResourceType, float],
    ) -> bool:
        """Check if an agent can produce this recipe."""
        # Check required skills
        for skill, level in self.required_skills.items():
            if agent.skills.get(skill, 0.0) < level:
                return False

        # Check required inputs
        for resource, amount in self.inputs.items():
            if inventory.get(resource, 0.0) < amount:
                return False

        # Check terrain (if specified)
        if self.required_terrain:
            x, y = int(agent.position.x), int(agent.position.y)
            terrain = TerrainType(world.get_terrain(x, y))
            if terrain not in self.required_terrain:
                return False

        return True

    def get_efficiency(
        self,
        agent: "Agent",
        world: "World",
        bonuses: dict[str, float] | None = None,
    ) -> float:
        """Calculate production efficiency for an agent."""
        eff = self.base_efficiency

        # Skill bonus
        primary_skill = list(self.required_skills.keys())[0] if self.required_skills else None
        if primary_skill:
            skill_level = agent.skills.get(primary_skill, 0.0)
            eff *= (1.0 + skill_level * 0.5)

        # Attribute bonus
        eff *= (1.0 + agent.attributes.intelligence * 0.2)

        # Environmental bonuses
        bonuses = bonuses or {}
        for bonus_name, bonus_value in bonuses.items():
            eff *= (1.0 + bonus_value)

        return min(2.0, eff)  # Cap at 2x efficiency

    def estimate_output(
        self,
        agent: "Agent",
        world: "World",
        input_amounts: dict[ResourceType, float],
    ) -> dict[ResourceType, float]:
        """Estimate output for given inputs and agent."""
        eff = self.get_efficiency(agent, world)

        # Scale outputs based on input availability (limiting factor)
        scale = 1.0
        for resource, required in self.inputs.items():
            available = input_amounts.get(resource, 0.0)
            if required > 0:
                scale = min(scale, available / required)

        return {
            resource: amount * eff * scale
            for resource, amount in self.outputs.items()
        }


# ---------------------------------------------------------------------------
# WorkSite — a location where production occurs
# ---------------------------------------------------------------------------


@dataclass
class WorkSite:
    """
    A physical location where production activities occur.

    WorkSites can be:
    - Natural: fishing spots, hunting grounds, mineral deposits
    - Built: farms, workshops, mines, buildings
    """

    site_id: EntityID
    name: str
    position: Pos2D
    production_type: ProductionType
    capacity: int = 1  # Max workers
    current_workers: int = 0
    worker_ids: list[EntityID] = field(default_factory=list)
    assigned_recipe: Recipe | None = None

    # Depletion state
    max_yield: float = 1000.0
    current_yield: float = 1000.0
    depletion_rate: float = 0.01  # Yield lost per production cycle
    regeneration_rate: float = 0.001  # Yield regenerated per tick

    # Productivity
    productivity_modifier: float = 1.0

    # Ownership
    owner_id: EntityID | None = None
    is_claimed: bool = False

    def is_available(self) -> bool:
        """Check if the site can accept more workers."""
        return self.current_workers < self.capacity

    def add_worker(self, agent_id: EntityID) -> bool:
        """Add a worker to the site."""
        if not self.is_available():
            return False
        self.worker_ids.append(agent_id)
        self.current_workers += 1
        return True

    def remove_worker(self, agent_id: EntityID) -> bool:
        """Remove a worker from the site."""
        if agent_id in self.worker_ids:
            self.worker_ids.remove(agent_id)
            self.current_workers -= 1
            return True
        return False

    def get_productivity(self) -> float:
        """Get current productivity of the site."""
        if self.max_yield <= 0:
            return 0.0
        yield_factor = self.current_yield / self.max_yield
        return self.productivity_modifier * max(0.0, yield_factor)

    def deplete(self, amount: float) -> float:
        """Deplete the site and return actual amount depleted."""
        actual = min(self.current_yield, amount)
        self.current_yield -= actual
        return actual

    def regenerate(self) -> None:
        """Regenerate the site's yield over time."""
        if self.current_yield < self.max_yield:
            self.current_yield = min(
                self.max_yield,
                self.current_yield + self.regeneration_rate
            )


# ---------------------------------------------------------------------------
# Farm — specialized agricultural WorkSite
# ---------------------------------------------------------------------------


@dataclass
class Farm(WorkSite):
    """A farm for agricultural production."""

    crop_type: str = "wheat"
    crop_stage: int = 0  # 0=planted, 1=growing, 2=harvestable, 3=harvested
    growth_ticks: int = 0
    harvest_yield: float = 10.0
    irrigation_level: float = 0.5  # 0-1, affects yield
    fertilizer_level: float = 0.0  # 0-1

    def __post_init__(self) -> None:
        self.production_type = ProductionType.FARMING
        self.capacity = 5

    def plant(self, crop_type: str, seed_quality: float = 0.5) -> None:
        """Plant a crop."""
        self.crop_type = crop_type
        self.crop_stage = 0
        self.growth_ticks = 0
        self.harvest_yield = 10.0 * seed_quality

    def update_growth(self, tick: int) -> bool:
        """Update crop growth. Returns True if harvest is ready."""
        self.growth_ticks += 1

        # Growth stages based on crop type
        growth_period = self._get_growth_period()
        if self.growth_ticks >= growth_period:
            self.crop_stage = 2  # Harvestable
            return True
        elif self.growth_ticks >= growth_period * 0.5:
            self.crop_stage = 1  # Growing

        return False

    def _get_growth_period(self) -> int:
        """Get growth period based on crop type and conditions."""
        base = {
            "wheat": 720,    # ~2 years
            "rice": 540,     # ~1.5 years
            "corn": 630,     # ~1.75 years
            "vegetables": 360,  # ~1 year
            "fruit": 1260,   # ~3.5 years
            "cotton": 900,   # ~2.5 years
        }.get(self.crop_type, 720)

        # Irrigation speeds up growth
        adjusted = base / (1.0 + self.irrigation_level * 0.5)
        return int(adjusted)

    def harvest(self) -> dict[ResourceType, float]:
        """Harvest the crop."""
        if self.crop_stage != 2:
            return {}

        yield_amount = self.harvest_yield * (
            1.0 + self.irrigation_level * 0.3 +
            self.fertilizer_level * 0.5
        )

        self.crop_stage = 3  # Post-harvest
        return {ResourceType.FOOD: yield_amount}


# ---------------------------------------------------------------------------
# Workshop — a building for crafting
# ---------------------------------------------------------------------------


@dataclass
class Workshop(WorkSite):
    """A workshop for crafting and manufacturing."""

    workshop_type: str = "general"
    quality_modifier: float = 1.0
    specializations: list[str] = field(default_factory=list)
    equipment_level: int = 1
    active_recipe: Recipe | None = None
    progress: float = 0.0

    def __post_init__(self) -> None:
        self.production_type = ProductionType.CRAFTING
        self.capacity = 10

    def assign_recipe(self, recipe: Recipe) -> bool:
        """Assign a recipe to this workshop."""
        self.active_recipe = recipe
        self.assigned_recipe = recipe
        self.progress = 0.0
        return True

    def work(self, agent: "Agent", delta_progress: float) -> float:
        """Perform work on the active recipe. Returns accumulated progress."""
        if self.active_recipe is None:
            return 0.0

        # Skill affects progress rate
        skill_bonus = 1.0
        if self.active_recipe.required_skills:
            primary = list(self.active_recipe.required_skills.keys())[0]
            skill_bonus = 1.0 + agent.skills.get(primary, 0.0) * 0.5

        self.progress += delta_progress * skill_bonus * self.quality_modifier

        # Check if complete
        if self.progress >= self.active_recipe.duration_ticks:
            return self.progress

        return 0.0

    def complete_production(
        self, agent: "Agent"
    ) -> dict[ResourceType, float] | None:
        """Complete the current production cycle and return outputs."""
        if self.progress < self.active_recipe.duration_ticks:
            return None

        if self.active_recipe is None:
            return None

        # Calculate output with quality modifier
        outputs: dict[ResourceType, float] = {}
        for resource, amount in self.active_recipe.outputs.items():
            quality = self.quality_modifier * (
                1.0 + agent.skills.get(list(self.active_recipe.required_skills.keys())[0], 0.0) * 0.2
            )
            outputs[resource] = amount * quality

        # Reset
        self.progress = 0.0

        return outputs


# ---------------------------------------------------------------------------
# ProductionSystem — the main production manager
# ---------------------------------------------------------------------------


class ProductionSystem:
    """
    Manages all production activities in the world.

    Responsibilities:
    - Create and manage WorkSites
    - Manage recipes (crafting, farming, mining, building)
    - Process production cycles
    - Track resource transformation chains
    - Manage farm plots and workshops
    """

    def __init__(
        self, config: EconomyConfig, world: "World", seed: int = 42
    ) -> None:
        self.config = config
        self.world = world
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # WorkSites
        self._sites: dict[EntityID, WorkSite] = {}
        self._sites_by_type: dict[ProductionType, list[EntityID]] = {
            pt: [] for pt in ProductionType
        }

        # Farms
        self._farms: dict[EntityID, Farm] = {}

        # Workshops
        self._workshops: dict[EntityID, Workshop] = {}

        # Recipes
        self._recipes: dict[str, Recipe] = {}
        self._build_recipe_database()

        # Statistics
        self._total_produced: dict[ResourceType, float] = {}
        self._production_cycles: int = 0

    def _build_recipe_database(self) -> None:
        """Build the complete recipe database."""
        recipes: list[Recipe] = []

        # --- Basic gathering recipes ---
        recipes.append(Recipe(
            recipe_id="gather_food_plains",
            name="Gather Food (Plains)",
            production_type=ProductionType.GATHERING,
            inputs={},
            outputs={ResourceType.FOOD: 2.0},
            duration_ticks=20,
            base_efficiency=1.0,
            required_terrain=[TerrainType.PLAINS, TerrainType.GRASSLAND, TerrainType.SAVANNA],
            description="Forage for edible plants",
        ))

        recipes.append(Recipe(
            recipe_id="gather_wood_forest",
            name="Gather Wood (Forest)",
            production_type=ProductionType.LOGGING,
            inputs={},
            outputs={ResourceType.WOOD: 3.0},
            duration_ticks=30,
            base_efficiency=1.0,
            required_terrain=[
                TerrainType.TEMPERATE_FOREST, TerrainType.TROPICAL_FOREST,
                TerrainType.BOREAL_FOREST, TerrainType.RAINFOREST
            ],
            description="Harvest wood from trees",
        ))

        recipes.append(Recipe(
            recipe_id="gather_stone_mountain",
            name="Quarry Stone (Mountains)",
            production_type=ProductionType.QUARRYING,
            inputs={},
            outputs={ResourceType.STONE: 2.0},
            duration_ticks=40,
            base_efficiency=1.0,
            required_terrain=[TerrainType.MOUNTAINS, TerrainType.HILLS],
            description="Extract stone from rocky terrain",
        ))

        # --- Fishing ---
        recipes.append(Recipe(
            recipe_id="fishing",
            name="Fishing",
            production_type=ProductionType.FISHING,
            inputs={},
            outputs={ResourceType.FOOD: 4.0},
            duration_ticks=25,
            base_efficiency=1.0,
            required_terrain=[TerrainType.WATER, TerrainType.SHALLOW_WATER],
            description="Catch fish from water bodies",
        ))

        # --- Hunting ---
        recipes.append(Recipe(
            recipe_id="hunting",
            name="Hunting",
            production_type=ProductionType.HUNTING,
            inputs={},
            outputs={ResourceType.FOOD: 6.0, ResourceType.CLOTHING: 1.0},
            duration_ticks=50,
            base_efficiency=0.8,
            required_skills={"survival": 0.2},
            required_terrain=[
                TerrainType.GRASSLAND, TerrainType.TEMPERATE_FOREST,
                TerrainType.SAVANNA, TerrainType.PLAINS, TerrainType.HILLS
            ],
            description="Hunt wild animals for food and materials",
        ))

        # --- Farming ---
        recipes.append(Recipe(
            recipe_id="farm_wheat",
            name="Wheat Farming",
            production_type=ProductionType.FARMING,
            inputs={ResourceType.FOOD: 5.0},  # Seeds
            outputs={ResourceType.FOOD: 15.0},
            duration_ticks=720,
            base_efficiency=1.0,
            required_terrain=[TerrainType.PLAINS, TerrainType.GRASSLAND, TerrainType.HILLS],
            description="Grow wheat crops",
        ))

        recipes.append(Recipe(
            recipe_id="farm_vegetables",
            name="Vegetable Farming",
            production_type=ProductionType.FARMING,
            inputs={ResourceType.FOOD: 3.0},
            outputs={ResourceType.FOOD: 12.0},
            duration_ticks=360,
            base_efficiency=1.0,
            required_terrain=[
                TerrainType.PLAINS, TerrainType.GRASSLAND, TerrainType.SWAMP
            ],
            description="Grow vegetables (faster but lower yield)",
        ))

        # --- Mining ---
        recipes.append(Recipe(
            recipe_id="mine_copper",
            name="Copper Mining",
            production_type=ProductionType.MINING,
            inputs={ResourceType.FOOD: 3.0},
            outputs={ResourceType.COPPER: 2.0},
            duration_ticks=60,
            base_efficiency=0.8,
            required_skills={"mining": 0.3},
            required_terrain=[TerrainType.MOUNTAINS, TerrainType.HILLS],
            description="Extract copper ore",
        ))

        recipes.append(Recipe(
            recipe_id="mine_iron",
            name="Iron Mining",
            production_type=ProductionType.MINING,
            inputs={ResourceType.FOOD: 5.0, ResourceType.TOOLS: 1.0},
            outputs={ResourceType.IRON: 1.5},
            duration_ticks=80,
            base_efficiency=0.6,
            required_skills={"mining": 0.5},
            required_terrain=[TerrainType.MOUNTAINS, TerrainType.HILLS],
            description="Extract iron ore",
        ))

        # --- Crafting ---
        recipes.append(Recipe(
            recipe_id="craft_tools",
            name="Craft Tools",
            production_type=ProductionType.CRAFTING,
            inputs={
                ResourceType.WOOD: 5.0,
                ResourceType.STONE: 3.0,
            },
            outputs={ResourceType.TOOLS: 2.0},
            duration_ticks=40,
            base_efficiency=1.0,
            required_skills={"crafting": 0.3},
            description="Craft basic tools",
        ))

        recipes.append(Recipe(
            recipe_id="craft_weapons",
            name="Craft Weapons",
            production_type=ProductionType.CRAFTING,
            inputs={
                ResourceType.WOOD: 3.0,
                ResourceType.STONE: 5.0,
                ResourceType.TOOLS: 1.0,
            },
            outputs={ResourceType.WEAPONS: 1.0},
            duration_ticks=60,
            base_efficiency=1.0,
            required_skills={"crafting": 0.5, "combat": 0.2},
            description="Craft weapons for hunting and defense",
        ))

        recipes.append(Recipe(
            recipe_id="craft_clothing",
            name="Craft Clothing",
            production_type=ProductionType.CRAFTING,
            inputs={
                ResourceType.CLOTHING: 5.0,
            },
            outputs={ResourceType.CLOTHING: 3.0},
            duration_ticks=30,
            base_efficiency=1.0,
            required_skills={"crafting": 0.2},
            description="Process raw materials into clothing",
        ))

        recipes.append(Recipe(
            recipe_id="smelt_copper",
            name="Smelt Copper",
            production_type=ProductionType.PROCESSING,
            inputs={ResourceType.COPPER: 5.0, ResourceType.WOOD: 3.0},
            outputs={ResourceType.COPPER: 4.0},  # Loss from impurities
            duration_ticks=50,
            base_efficiency=0.8,
            required_skills={"smithing": 0.4},
            description="Smelt copper ore into pure copper",
        ))

        recipes.append(Recipe(
            recipe_id="smelt_iron",
            name="Smelt Iron",
            production_type=ProductionType.PROCESSING,
            inputs={ResourceType.IRON: 5.0, ResourceType.WOOD: 5.0},
            outputs={ResourceType.IRON: 3.5},
            duration_ticks=70,
            base_efficiency=0.7,
            required_skills={"smithing": 0.6},
            description="Smelt iron ore into workable iron",
        ))

        # --- Building ---
        recipes.append(Recipe(
            recipe_id="build_hut",
            name="Build Hut",
            production_type=ProductionType.BUILDING,
            inputs={
                ResourceType.WOOD: 20.0,
                ResourceType.STONE: 10.0,
                ResourceType.CLOTHING: 5.0,
            },
            outputs={"structure_hut": 1.0},
            duration_ticks=200,
            base_efficiency=1.0,
            required_skills={"building": 0.3},
            description="Build a basic hut for shelter",
        ))

        recipes.append(Recipe(
            recipe_id="build_workshop",
            name="Build Workshop",
            production_type=ProductionType.BUILDING,
            inputs={
                ResourceType.WOOD: 40.0,
                ResourceType.STONE: 30.0,
                ResourceType.TOOLS: 3.0,
            },
            outputs={"structure_workshop": 1.0},
            duration_ticks=500,
            base_efficiency=1.0,
            required_skills={"building": 0.5},
            description="Build a workshop for advanced crafting",
        ))

        recipes.append(Recipe(
            recipe_id="build_irrigation",
            name="Build Irrigation",
            production_type=ProductionType.BUILDING,
            inputs={
                ResourceType.STONE: 30.0,
                ResourceType.TOOLS: 2.0,
            },
            outputs={"structure_irrigation": 1.0},
            duration_ticks=400,
            base_efficiency=1.0,
            required_skills={"engineering": 0.4},
            description="Build irrigation to improve farm yield",
        ))

        # --- Animal husbandry ---
        recipes.append(Recipe(
            recipe_id="breed_animals",
            name="Animal Husbandry",
            production_type=ProductionType.BREEDING,
            inputs={ResourceType.FOOD: 10.0},
            outputs={ResourceType.FOOD: 5.0, ResourceType.CLOTHING: 2.0},
            duration_ticks=360,
            base_efficiency=1.0,
            required_terrain=[TerrainType.PLAINS, TerrainType.GRASSLAND],
            description="Raise animals for food and materials",
        ))

        # Register all recipes
        for recipe in recipes:
            self._recipes[recipe.recipe_id] = recipe

    def get_recipe(self, recipe_id: str) -> Recipe | None:
        """Get a recipe by ID."""
        return self._recipes.get(recipe_id)

    def get_recipes_for_type(
        self, production_type: ProductionType
    ) -> list[Recipe]:
        """Get all recipes of a specific production type."""
        return [r for r in self._recipes.values() if r.production_type == production_type]

    def get_available_recipes(
        self, agent: "Agent", inventory: dict[ResourceType, float]
    ) -> list[tuple[Recipe, float]]:
        """Get all recipes an agent can produce, with efficiency scores."""
        results: list[tuple[Recipe, float]] = []
        for recipe in self._recipes.values():
            if recipe.can_produce(agent, self.world, inventory):
                eff = recipe.get_efficiency(agent, self.world)
                results.append((recipe, eff))
        return sorted(results, key=lambda x: -x[1])

    def create_worksite(
        self,
        position: Pos2D,
        production_type: ProductionType,
        name: str,
        capacity: int = 1,
        owner_id: EntityID | None = None,
    ) -> WorkSite:
        """Create a new worksite at a location."""
        site = WorkSite(
            site_id=new_entity_id(),
            name=name,
            position=position,
            production_type=production_type,
            capacity=capacity,
            owner_id=owner_id,
        )

        self._sites[site.site_id] = site
        self._sites_by_type[production_type].append(site.site_id)

        if owner_id:
            site.is_claimed = True

        return site

    def create_farm(
        self,
        position: Pos2D,
        crop_type: str = "wheat",
        owner_id: EntityID | None = None,
    ) -> Farm:
        """Create a new farm."""
        farm = Farm(
            site_id=new_entity_id(),
            name=f"Farm_{crop_type}",
            position=position,
            production_type=ProductionType.FARMING,
            owner_id=owner_id,
        )
        farm.plant(crop_type)

        self._sites[farm.site_id] = farm
        self._farms[farm.site_id] = farm
        self._sites_by_type[ProductionType.FARMING].append(farm.site_id)

        return farm

    def create_workshop(
        self,
        position: Pos2D,
        workshop_type: str = "general",
        owner_id: EntityID | None = None,
    ) -> Workshop:
        """Create a new workshop."""
        workshop = Workshop(
            site_id=new_entity_id(),
            name=f"Workshop_{workshop_type}",
            position=position,
            production_type=ProductionType.CRAFTING,
            workshop_type=workshop_type,
            owner_id=owner_id,
        )

        self._sites[workshop.site_id] = workshop
        self._workshops[workshop.site_id] = workshop
        self._sites_by_type[ProductionType.CRAFTING].append(workshop.site_id)

        return workshop

    def get_worksites_near(
        self, pos: Pos2D, radius: float
    ) -> list[tuple[WorkSite, float]]:
        """Get worksites near a position."""
        results: list[tuple[WorkSite, float]] = []
        for site in self._sites.values():
            dist = pos.euclidean_distance(site.position)
            if dist <= radius:
                results.append((site, dist))
        return sorted(results, key=lambda x: x[1])

    def get_worksite(self, site_id: EntityID) -> WorkSite | None:
        """Get a worksite by ID."""
        return self._sites.get(site_id)

    def discover_worksites(self, tick: int) -> int:
        """
        Discover new natural worksites based on terrain.
        Called periodically to populate the world with natural resources.
        """
        discovered = 0
        w = self.world._config.world.width
        h = self.world._config.world.height

        # Limit discoveries per tick to avoid flooding
        max_per_tick = 5

        for _ in range(max_per_tick):
            x = self._rng.integers(0, w)
            y = self._rng.integers(0, h)
            terrain = TerrainType(self.world.get_terrain(x, y))

            pos = Pos2D(x, y)
            production_type: ProductionType | None = None
            name = ""
            capacity = 1

            if terrain in [TerrainType.WATER, TerrainType.SHALLOW_WATER]:
                if self._rng.random() < 0.001:  # Rare fishing spots
                    production_type = ProductionType.FISHING
                    name = f"Fishing Spot {x},{y}"
                    capacity = 3

            elif terrain in [TerrainType.MOUNTAINS, TerrainType.HILLS]:
                if self._rng.random() < 0.002:
                    if self._rng.random() < 0.5:
                        production_type = ProductionType.QUARRYING
                        name = f"Stone Quarry {x},{y}"
                    else:
                        production_type = ProductionType.MINING
                        mineral = self._rng.choice(["copper", "iron"])
                        name = f"{mineral.title()} Mine {x},{y}"
                    capacity = 5

            elif terrain.is_forest:
                if self._rng.random() < 0.001:
                    production_type = ProductionType.LOGGING
                    name = f"Logging Camp {x},{y}"
                    capacity = 4

            elif terrain in [TerrainType.PLAINS, TerrainType.GRASSLAND]:
                if self._rng.random() < 0.001:
                    production_type = ProductionType.HUNTING
                    name = f"Hunting Grounds {x},{y}"
                    capacity = 3

            if production_type:
                # Check if there's already a nearby worksite
                nearby = self.get_worksites_near(pos, 50.0)
                if len(nearby) >= 3:
                    continue

                site = self.create_worksite(
                    position=pos,
                    production_type=production_type,
                    name=name,
                    capacity=capacity,
                )
                site.max_yield = self._rng.uniform(500, 2000)
                site.current_yield = site.max_yield
                discovered += 1

        return discovered

    def update(self, tick: int) -> None:
        """Update all production systems for the tick."""
        # Regenerate natural worksites
        for site in self._sites.values():
            site.regenerate()

        # Update farms
        for farm in self._farms.values():
            if farm.crop_stage < 2:  # Not yet harvestable
                farm.update_growth(tick)

        # Occasionally discover new worksites
        if tick % 100 == 0:
            self.discover_worksites(tick)

    def work_at_site(
        self,
        agent: "Agent",
        site: WorkSite,
        tick: int,
    ) -> dict[ResourceType, float] | None:
        """
        Have an agent work at a worksite.

        Returns produced resources if any, None otherwise.
        """
        if not site.is_available() and agent.entity_id not in site.worker_ids:
            return None

        # Add worker if not already working
        if agent.entity_id not in site.worker_ids:
            if not site.add_worker(agent.entity_id):
                return None

        # Get the recipe for this production type
        recipes = self.get_recipes_for_type(site.production_type)
        if not recipes:
            return None

        recipe = recipes[0]  # Use first available recipe

        # Calculate production
        productivity = site.get_productivity()
        if productivity <= 0:
            return None

        # Scale output by productivity and agent skill
        eff = recipe.get_efficiency(agent, self.world)
        scale = productivity * eff * 0.1  # Per-tick contribution

        outputs: dict[ResourceType, float] = {}
        for resource, amount in recipe.outputs.items():
            produced = amount * scale
            outputs[resource] = produced

            # Track statistics
            self._total_produced[resource] = self._total_produced.get(resource, 0.0) + produced

        # Deplete the site
        site.deplete(sum(outputs.values()) * 0.1)

        self._production_cycles += 1

        return outputs

    def work_at_farm(
        self,
        agent: "Agent",
        farm: Farm,
        tick: int,
    ) -> dict[ResourceType, float] | None:
        """Have an agent work at a farm."""
        if agent.entity_id not in farm.worker_ids:
            if not farm.add_worker(agent.entity_id):
                return None

        # Check if ready to harvest
        if farm.crop_stage == 2:  # Harvestable
            return farm.harvest()

        # Otherwise, tend to the farm
        farm.update_growth(tick)

        return None

    def get_stats(self) -> dict[str, Any]:
        """Get production statistics."""
        return {
            "total_sites": len(self._sites),
            "total_farms": len(self._farms),
            "total_workshops": len(self._workshops),
            "production_cycles": self._production_cycles,
            "total_produced": dict(self._total_produced),
            "sites_by_type": {
                pt.name: len(site_ids)
                for pt, site_ids in self._sites_by_type.items()
            },
            "avg_productivity": sum(s.get_productivity() for s in self._sites.values()) / max(1, len(self._sites)),
        }
