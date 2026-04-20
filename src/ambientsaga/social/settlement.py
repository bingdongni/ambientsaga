"""
Settlement System — Managing settlements, villages, cities, and territorial control.

Settlements are the physical manifestations of social organization:
- Villages: Small groups of agents living together
- Towns: Larger settlements with specialized roles
- Cities: Major population centers with complex governance
- Metropolises: Large urban areas with advanced infrastructure

Key features:
- Population management
- Territorial boundaries
- Building construction and upgrades
- Resource production and storage
- Defense capabilities
- Cultural identity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import numpy as np

from ambientsaga.types import (
    BoundingBox,
    EntityID,
    Inventory,
    Pos2D,
    ResourceType,
    Tick,
)

if TYPE_CHECKING:
    from ambientsaga.world.state import World


class SettlementType(Enum):
    """Types of settlements by size and complexity."""

    HAMLET = auto()       # Very small (5-20 agents)
    VILLAGE = auto()      # Small (20-100 agents)
    TOWN = auto()         # Medium (100-500 agents)
    CITY = auto()         # Large (500-2000 agents)
    METROPOLIS = auto()   # Very large (2000+ agents)

    @property
    def population_range(self) -> tuple[int, int]:
        """Typical population range for this settlement type."""
        ranges = {
            SettlementType.HAMLET: (5, 20),
            SettlementType.VILLAGE: (20, 100),
            SettlementType.TOWN: (100, 500),
            SettlementType.CITY: (500, 2000),
            SettlementType.METROPOLIS: (2000, 50000),
        }
        return ranges[self]

    @property
    def max_buildings(self) -> int:
        """Maximum number of buildings for this settlement type."""
        counts = {
            SettlementType.HAMLET: 10,
            SettlementType.VILLAGE: 50,
            SettlementType.TOWN: 200,
            SettlementType.CITY: 1000,
            SettlementType.METROPOLIS: 5000,
        }
        return counts[self]


class BuildingType(Enum):
    """Types of buildings that can be constructed."""

    # Basic
    HUT = auto()              # Simple shelter
    STOREHOUSE = auto()        # Resource storage
    WELL = auto()              # Water source
    FIRE_PIT = auto()          # Cooking/heating

    # Agricultural
    BARN = auto()              # Crop storage
    MILL = auto()              # Grain processing
    SMITHY = auto()            # Metal working

    # Social
    MEETING_HALL = auto()      # Community gathering
    SHRINE = auto()            # Religious worship
    SCHOOL = auto()            # Education

    # Defense
    PALISADE = auto()          # Wooden walls
    WATCHTOWER = auto()        # Surveillance
    BARRACKS = auto()          # Military housing

    # Commerce
    MARKET = auto()            # Trading area
    TAVERN = auto()            # Social hub
    INN = auto()              # Traveler accommodation

    # Advanced
    TEMPLE = auto()            # Major religious building
    GRANARY = auto()           # Large food storage
    FORGE = auto()             # Advanced metalwork
    LIBRARY = auto()           # Knowledge storage

    @property
    def base_cost(self) -> dict[ResourceType, float]:
        """Base resource cost to build this structure."""
        costs = {
            BuildingType.HUT: {ResourceType.WOOD: 10},
            BuildingType.STOREHOUSE: {ResourceType.WOOD: 20, ResourceType.STONE: 10},
            BuildingType.WELL: {ResourceType.STONE: 30},
            BuildingType.FIRE_PIT: {ResourceType.STONE: 5},
            BuildingType.BARN: {ResourceType.WOOD: 30, ResourceType.STONE: 10},
            BuildingType.MILL: {ResourceType.WOOD: 40, ResourceType.STONE: 20},
            BuildingType.SMITHY: {ResourceType.STONE: 30, ResourceType.IRON_ORE: 10},
            BuildingType.MEETING_HALL: {ResourceType.WOOD: 50, ResourceType.STONE: 30},
            BuildingType.SHRINE: {ResourceType.STONE: 40},
            BuildingType.SCHOOL: {ResourceType.WOOD: 30, ResourceType.STONE: 20},
            BuildingType.PALISADE: {ResourceType.WOOD: 60},
            BuildingType.WATCHTOWER: {ResourceType.WOOD: 30, ResourceType.STONE: 20},
            BuildingType.BARRACKS: {ResourceType.WOOD: 40, ResourceType.STONE: 20},
            BuildingType.MARKET: {ResourceType.WOOD: 30},
            BuildingType.TAVERN: {ResourceType.WOOD: 40, ResourceType.STONE: 10},
            BuildingType.INN: {ResourceType.WOOD: 50, ResourceType.STONE: 15},
            BuildingType.TEMPLE: {ResourceType.STONE: 100},
            BuildingType.GRANARY: {ResourceType.WOOD: 40, ResourceType.STONE: 20},
            BuildingType.FORGE: {ResourceType.STONE: 50, ResourceType.IRON_ORE: 20, ResourceType.COAL: 10},
            BuildingType.LIBRARY: {ResourceType.WOOD: 30, ResourceType.STONE: 40},
        }
        return costs.get(self, {})

    @property
    def population_bonus(self) -> int:
        """Population capacity bonus from this building."""
        bonuses = {
            BuildingType.HUT: 5,
            BuildingType.MEETING_HALL: 10,
            BuildingType.BARRACKS: 20,
            BuildingType.MARKET: 15,
        }
        return bonuses.get(self, 2)

    @property
    def production_bonus(self) -> dict[str, float]:
        """Production bonuses provided by this building."""
        bonuses = {
            BuildingType.MILL: {"grain": 0.2},
            BuildingType.SMITHY: {"metal": 0.3},
            BuildingType.FORGE: {"metal": 0.5, "tools": 0.3},
            BuildingType.MARKET: {"trade": 0.3},
            BuildingType.TAVERN: {"social": 0.2},
        }
        return bonuses.get(self, {})


@dataclass
class Building:
    """A building within a settlement."""

    building_id: EntityID
    building_type: BuildingType
    position: Pos2D
    constructed_tick: Tick
    condition: float = 1.0  # 0-1, building health
    level: int = 1           # Upgrade level
    assigned_residents: list[EntityID] = field(default_factory=list)

    def upgrade(self) -> bool:
        """Attempt to upgrade this building."""
        if self.level >= 5:
            return False
        self.level += 1
        self.condition = 1.0
        return True

    def damage(self, amount: float) -> bool:
        """Apply damage to the building. Returns True if destroyed."""
        self.condition = max(0.0, self.condition - amount)
        return self.condition <= 0.0

    def repair(self, amount: float) -> None:
        """Repair the building."""
        self.condition = min(1.0, self.condition + amount)


@dataclass
class Settlement:
    """
    A settlement - a physical location where agents live and interact.

    Settlements provide:
    - Security through numbers and defense structures
    - Economic benefits through trade and specialization
    - Cultural identity through shared traditions
    - Resource sharing and storage
    """

    settlement_id: EntityID
    name: str
    settlement_type: SettlementType
    position: Pos2D
    territory: BoundingBox

    # Population
    population: int = 0
    residents: list[EntityID] = field(default_factory=list)
    population_growth_rate: float = 0.01  # Per tick

    # Buildings
    buildings: list[Building] = field(default_factory=list)
    building_slots: int = 10  # Max buildings based on type

    # Resources
    inventory: Inventory = field(default_factory=Inventory)
    treasury: float = 0.0    # Shared wealth

    # Culture
    culture_ids: set[str] = field(default_factory=set)  # Ethic groups present
    primary_culture: str = ""
    shared_beliefs: list[str] = field(default_factory=list)
    customs: tuple[str, ...] = field(default_factory=tuple)

    # Governance
    governance_type: str = "tribal"  # "tribal", "chiefdom", "democratic", "monarchy"
    leader_id: EntityID | None = None
    council_members: list[EntityID] = field(default_factory=list)

    # Defense
    defense_level: float = 0.5  # 0-1
    garrison_size: int = 0
    fortification_level: int = 0

    # Status
    founded_tick: Tick = 0
    prosperity: float = 0.5  # 0-1, overall health
    happiness: float = 0.5   # 0-1, resident satisfaction
    is_abandoned: bool = False

    # Statistics
    total_trades: int = 0
    total_festivals: int = 0
    historical_events: list[dict] = field(default_factory=list)

    @property
    def capacity(self) -> int:
        """Maximum population the settlement can support."""
        base = self.settlement_type.population_range[1]
        building_bonus = sum(b.building_type.population_bonus for b in self.buildings)
        return min(base, self.population + building_bonus)

    @property
    def defense_strength(self) -> float:
        """Overall defense capability."""
        base = self.defense_level
        fort = self.fortification_level * 0.2
        garrison = min(1.0, self.garrison_size / 50)
        return min(1.0, base + fort + garrison * 0.3)

    def can_grow(self) -> bool:
        """Check if settlement can accommodate more residents."""
        return self.population < self.capacity and not self.is_abandoned

    def add_resident(self, agent_id: EntityID) -> bool:
        """Add a new resident. Returns True if successful."""
        if not self.can_grow():
            return False
        if agent_id not in self.residents:
            self.residents.append(agent_id)
            self.population += 1
        return True

    def remove_resident(self, agent_id: EntityID) -> bool:
        """Remove a resident."""
        if agent_id in self.residents:
            self.residents.remove(agent_id)
            self.population = max(0, self.population - 1)
            return True
        return False

    def add_building(self, building: Building) -> bool:
        """Add a building. Returns True if successful."""
        if len(self.buildings) >= self.building_slots:
            return False
        self.buildings.append(building)
        self.building_slots = min(
            self.building_slots + 1,
            self.settlement_type.max_buildings
        )
        return True

    def get_production_bonus(self, category: str) -> float:
        """Get total production bonus for a category."""
        total = 0.0
        for building in self.buildings:
            bonuses = building.building_type.production_bonus
            if category in bonuses:
                total += bonuses[category]
        return total

    def update_prosperity(self, economic_growth: float, social_stability: float) -> None:
        """Update settlement prosperity based on recent events."""
        # Weighted average of factors
        self.prosperity = (
            self.prosperity * 0.7 +
            economic_growth * 0.2 +
            social_stability * 0.1
        )
        self.prosperity = max(0.0, min(1.0, self.prosperity))

    def record_event(self, event_type: str, description: str, tick: Tick) -> None:
        """Record a historical event."""
        self.historical_events.append({
            "type": event_type,
            "description": description,
            "tick": tick,
        })
        # Keep only recent events
        if len(self.historical_events) > 100:
            self.historical_events = self.historical_events[-100:]


class SettlementManager:
    """
    Manages all settlements in the world.

    Responsibilities:
    - Create and destroy settlements
    - Track settlement population and growth
    - Manage territorial boundaries
    - Handle settlement conflicts
    - Coordinate settlement interactions
    """

    def __init__(self, world: World, seed: int = 42) -> None:
        self.world = world
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Settlement registry
        self._settlements: dict[EntityID, Settlement] = {}

        # Agent to settlement mapping
        self._agent_settlements: dict[EntityID, EntityID] = {}

        # Territory map: settlement_id -> set of positions
        self._territory: dict[EntityID, set[Pos2D]] = {}

        # Settlement name generator
        self._name_generators = self._initialize_name_generators()

    def _initialize_name_generators(self) -> dict[str, list[str]]:
        """Initialize settlement name parts by culture."""
        return {
            "default": ["Village", "Town", "Fort", "Haven", "Crossing", "Glen"],
            "tribal": ["Camp", "Ridge", "Shore", "Grove", "Meadow", "Peak"],
            "nordic": ["By", "Havn", "heim", "gard", "stead", "wick"],
            "mediterranean": ["polis", "burg", "ton", "ville", "stadt"],
            "eastern": ["Zhou", "Cheng", "Fu", "Zhen", "Sui", "Lu"],
        }

    def create_settlement(
        self,
        position: Pos2D,
        settlement_type: SettlementType,
        culture_id: str = "default",
        name: str | None = None,
    ) -> Settlement:
        """Create a new settlement."""
        import uuid

        settlement_id = uuid.uuid4().hex[:16]
        if name is None:
            name = self._generate_name(settlement_type, culture_id)

        # Calculate territory based on settlement type
        size = settlement_type.population_range[1] // 10
        territory = BoundingBox(
            min_x=position.x - size,
            min_y=position.y - size,
            max_x=position.x + size,
            max_y=position.y + size,
        )

        settlement = Settlement(
            settlement_id=settlement_id,
            name=name,
            settlement_type=settlement_type,
            position=position,
            territory=territory,
            culture_ids={culture_id},
            primary_culture=culture_id,
            founded_tick=self.world.current_tick if hasattr(self.world, 'current_tick') else 0,
        )

        self._settlements[settlement_id] = settlement
        self._territory[settlement_id] = set()
        self._update_territory(settlement)

        return settlement

    def _generate_name(self, settlement_type: SettlementType, culture_id: str) -> str:
        """Generate a settlement name based on type and culture."""
        prefixes = ["", "New ", "Old ", "High ", "Low "]
        suffixes = self._name_generators.get(culture_id, self._name_generators["default"])

        prefix = self._rng.choice(prefixes)
        suffix = self._rng.choice(suffixes)

        return f"{prefix}{settlement_type.name.title()} {suffix}"

    def _update_territory(self, settlement: Settlement) -> None:
        """Update the territory positions for a settlement."""
        positions = set()
        for x in range(settlement.territory.min_x, settlement.territory.max_x + 1):
            for y in range(settlement.territory.min_y, settlement.territory.max_y + 1):
                pos = Pos2D(x, y)
                if self.world.is_valid_position(pos):
                    positions.add(pos)
        self._territory[settlement.settlement_id] = positions

    def get_settlement_at(self, position: Pos2D) -> Settlement | None:
        """Get settlement that contains this position."""
        for settlement in self._settlements.values():
            if settlement.territory.contains(position):
                return settlement
        return None

    def get_nearest_settlement(self, position: Pos2D, max_distance: float = float('inf')) -> Settlement | None:
        """Find the nearest settlement to a position."""
        nearest = None
        nearest_dist = max_distance

        for settlement in self._settlements.values():
            if settlement.is_abandoned:
                continue
            dist = position.euclidean_distance(settlement.position)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = settlement

        return nearest

    def get_settlements_in_radius(self, position: Pos2D, radius: float) -> list[Settlement]:
        """Get all settlements within radius of a position."""
        result = []
        for settlement in self._settlements.values():
            if settlement.is_abandoned:
                continue
            if position.euclidean_distance(settlement.position) <= radius:
                result.append(settlement)
        return result

    def register_resident(self, agent_id: EntityID, settlement_id: EntityID) -> bool:
        """Register an agent as a resident of a settlement."""
        if settlement_id not in self._settlements:
            return False

        settlement = self._settlements[settlement_id]
        if not settlement.add_resident(agent_id):
            return False

        self._agent_settlements[agent_id] = settlement_id
        return True

    def unregister_resident(self, agent_id: EntityID) -> bool:
        """Unregister an agent from their settlement."""
        if agent_id not in self._agent_settlements:
            return False

        settlement_id = self._agent_settlements[agent_id]
        settlement = self._settlements.get(settlement_id)
        if settlement:
            settlement.remove_resident(agent_id)

        del self._agent_settlements[agent_id]
        return True

    def get_agent_settlement(self, agent_id: EntityID) -> Settlement | None:
        """Get the settlement an agent belongs to."""
        settlement_id = self._agent_settlements.get(agent_id)
        if settlement_id:
            return self._settlements.get(settlement_id)
        return None

    def get_all_settlements(self) -> list[Settlement]:
        """Get all settlements."""
        return list(self._settlements.values())

    def get_active_settlements(self) -> list[Settlement]:
        """Get all non-abandoned settlements."""
        return [s for s in self._settlements.values() if not s.is_abandoned]

    def abandon_settlement(self, settlement_id: EntityID) -> None:
        """Mark a settlement as abandoned."""
        settlement = self._settlements.get(settlement_id)
        if settlement:
            settlement.is_abandoned = True
            # Unregister all residents
            for agent_id in list(settlement.residents):
                self.unregister_resident(agent_id)

    def merge_settlements(self, settlement1_id: EntityID, settlement2_id: EntityID) -> Settlement | None:
        """Merge two settlements into one."""
        s1 = self._settlements.get(settlement1_id)
        s2 = self._settlements.get(settlement2_id)
        if not s1 or not s2:
            return None

        # Keep the larger settlement
        if s1.population < s2.population:
            s1, s2 = s2, s1

        # Transfer residents
        for agent_id in s2.residents:
            self._agent_settlements[agent_id] = s1.settlement_id
            if agent_id not in s1.residents:
                s1.residents.append(agent_id)

        s1.population = len(s1.residents)
        s1.culture_ids.update(s2.culture_ids)
        s1.buildings.extend(s2.buildings)

        # Update territory
        s1.territory = BoundingBox(
            min_x=min(s1.territory.min_x, s2.territory.min_x),
            min_y=min(s1.territory.min_y, s2.territory.min_y),
            max_x=max(s1.territory.max_x, s2.territory.max_x),
            max_y=max(s1.territory.max_y, s2.territory.max_y),
        )
        self._update_territory(s1)

        # Remove absorbed settlement
        self.abandon_settlement(s2.settlement_id)

        return s1

    def split_settlement(self, settlement_id: EntityID, split_position: Pos2D) -> tuple[Settlement, Settlement] | None:
        """Split a settlement into two at a position."""
        original = self._settlements.get(settlement_id)
        if not original:
            return None

        # Create two settlements
        s1_type = SettlementType.HAMLET if original.population // 2 <= 20 else SettlementType.VILLAGE
        s2_type = s1_type

        s1 = self.create_settlement(
            position=original.position,
            settlement_type=s1_type,
            culture_id=original.primary_culture,
            name=f"{original.name} (North)",
        )
        s2 = self.create_settlement(
            position=split_position,
            settlement_type=s2_type,
            culture_id=original.primary_culture,
            name=f"{original.name} (South)",
        )

        # Split residents
        half = len(original.residents) // 2
        s1.residents = original.residents[:half]
        s2.residents = original.residents[half:]
        s1.population = len(s1.residents)
        s2.population = len(s2.residents)

        for agent_id in s1.residents:
            self._agent_settlements[agent_id] = s1.settlement_id
        for agent_id in s2.residents:
            self._agent_settlements[agent_id] = s2.settlement_id

        return s1, s2

    def update(self, tick: int) -> None:
        """Update all settlements."""
        for settlement in self._settlements.values():
            self._update_population_growth(settlement, tick)
            self._update_building_conditions(settlement, tick)
            self._check_settlement_status(settlement)

    def _update_population_growth(self, settlement: Settlement, tick: int) -> None:
        """Update settlement population based on growth rate."""
        if settlement.is_abandoned:
            return

        # Base growth rate
        growth = settlement.population_growth_rate

        # Adjust for prosperity
        growth *= settlement.prosperity

        # Adjust for capacity
        if settlement.population >= settlement.capacity:
            growth = 0
        elif settlement.population > settlement.capacity * 0.8:
            growth *= 0.5

        # Apply growth
        if growth > 0 and settlement.can_grow():
            expected = int(settlement.population * growth)
            if expected > 0:
                # Population growth handled by World when agents are born
                pass

    def _update_building_conditions(self, settlement: Settlement, tick: int) -> None:
        """Update building conditions over time."""
        for building in settlement.buildings:
            # Natural decay
            if tick % 100 == 0:
                building.condition = max(0.3, building.condition - 0.01)
            # Weather damage (random)
            if self._rng.random() < 0.001:
                building.damage(0.1)

    def _check_settlement_status(self, settlement: Settlement) -> None:
        """Check and update settlement status."""
        # Abandon if population drops too low
        if settlement.population <= 2 and len(settlement.residents) <= 2:
            # Small chance of abandonment
            if self._rng.random() < 0.1:
                settlement.is_abandoned = True

        # Upgrade type based on population
        self._check_settlement_type(settlement)

    def _check_settlement_type(self, settlement: Settlement) -> None:
        """Check if settlement should be upgraded to a larger type."""
        pop = settlement.population

        current_type = settlement.settlement_type
        new_type = None

        if pop >= SettlementType.METROPOLIS.population_range[0] and current_type != SettlementType.METROPOLIS:
            new_type = SettlementType.METROPOLIS
        elif pop >= SettlementType.CITY.population_range[0] and current_type == SettlementType.TOWN:
            new_type = SettlementType.CITY
        elif pop >= SettlementType.TOWN.population_range[0] and current_type == SettlementType.VILLAGE:
            new_type = SettlementType.TOWN
        elif pop >= SettlementType.VILLAGE.population_range[0] and current_type == SettlementType.HAMLET:
            new_type = SettlementType.VILLAGE

        if new_type:
            settlement.settlement_type = new_type
            settlement.building_slots = new_type.max_buildings

    def get_statistics(self) -> dict[str, Any]:
        """Get settlement statistics."""
        active = self.get_active_settlements()
        return {
            "total_settlements": len(self._settlements),
            "active_settlements": len(active),
            "total_population": sum(s.population for s in active),
            "by_type": {
                stype.name: len([s for s in active if s.settlement_type == stype])
                for stype in SettlementType
            },
            "abandoned_count": len([s for s in self._settlements.values() if s.is_abandoned]),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize settlement manager state."""
        return {
            "settlements": {
                sid: {
                    "name": s.name,
                    "type": s.settlement_type.name,
                    "position": (s.position.x, s.position.y),
                    "population": s.population,
                    "prosperity": s.prosperity,
                    "is_abandoned": s.is_abandoned,
                }
                for sid, s in self._settlements.items()
            },
            "statistics": self.get_statistics(),
        }