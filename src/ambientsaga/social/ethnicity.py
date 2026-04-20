"""
Ethnic Group System — Managing ethnic groups, cultures, and cultural identities.

Ethnic groups are social groups defined by shared:
- Cultural identity (language, customs, traditions)
- Historical origin and ancestry
- Territory and homeland
- Self-identification

Key features:
- Population tracking by ethnicity
- Cultural trait inheritance
- Inter-ethnic relations
- Cultural evolution
- Ethnic conflict and cooperation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import numpy as np

from ambientsaga.types import BoundingBox, EntityID, Pos2D, Tick

if TYPE_CHECKING:
    from ambientsaga.world.state import World


class EthnicRelation(Enum):
    """Types of relations between ethnic groups."""

    ALLIED = auto()        # Close cooperation
    FRIENDLY = auto()      # Positive relations
    NEUTRAL = auto()       # No particular relation
    DISTANT = auto()        # Limited contact
    HOSTILE = auto()       # Conflict
    SUBJUGATED = auto()    # One group rules over another
    ASSIMILATED = auto()   # One group absorbed into another


class CulturalTraitType(Enum):
    """Categories of cultural traits."""

    LANGUAGE = auto()
    RELIGION = auto()
    DIET = auto()
    CLOTHING = auto()
    HOUSING = auto()
    CRAFTS = auto()
    MUSIC = auto()
    DANCE = auto()
    ART = auto()
    MEDICINE = auto()
    AGRICULTURE = auto()
    GOVERNANCE = auto()
    FAMILY = auto()
    RITES = auto()
    TABOOS = auto()


@dataclass
class CulturalTrait:
    """A specific cultural trait or tradition."""

    trait_id: EntityID
    trait_type: CulturalTraitType
    name: str
    description: str
    adoption_rate: float = 1.0  # How common within the ethnic group
    sacred: bool = False        # Religious/cultural significance
    mutable: bool = True        # Can change over time

    def mutate(self) -> CulturalTrait:
        """Create a mutated version of this trait."""
        import uuid
        return CulturalTrait(
            trait_id=uuid.uuid4().hex[:16],
            trait_type=self.trait_type,
            name=f"Variant of {self.name}",
            description=f"Modified: {self.description}",
            adoption_rate=self.adoption_rate * 0.8,
            sacred=self.sacred,
            mutable=True,
        )


@dataclass
class EthnicGroup:
    """
    An ethnic group with shared cultural identity.

    Ethnic groups are not necessarily political entities - they are
    cultural communities that may span multiple settlements and territories.
    """

    ethnic_id: EntityID
    name: str
    short_name: str  # Abbreviated name (e.g., "Nords", "Romans")

    # Population
    population: int = 0
    population_history: list[tuple[int, int]] = field(default_factory=list)  # (tick, pop)

    # Origin
    origin_tick: Tick = 0
    origin_position: Pos2D | None = None
    origin_story: str = ""  # Origin myth/history

    # Territory
    homeland: BoundingBox | None = None
    current_territory: BoundingBox | None = None
    historical_territories: list[BoundingBox] = field(default_factory=list)

    # Language
    language: str = "common"
    language_family: str = "unknown"
    dialects: list[str] = field(default_factory=list)

    # Culture
    traits: list[CulturalTrait] = field(default_factory=list)
    values: tuple[str, ...] = field(default_factory=tuple)  # Core values
    customs: tuple[str, ...] = field(default_factory=tuple)   # Behavioral customs
    taboos: tuple[str, ...] = field(default_factory=tuple)   # Forbidden behaviors
    oral_traditions: list[str] = field(default_factory=list)  # Stories/myths

    # Physical appearance (descriptive, for narrative purposes)
    appearance_desc: str = ""  # "tall and fair-skinned", "short and dark-haired"
    typical_build: str = ""    # "stocky", "slender", "athletic"
    common_features: tuple[str, ...] = field(default_factory=tuple)

    # Relations
    relations: dict[str, EthnicRelation] = field(default_factory=dict)  # other_ethnic_id -> relation
    alliances: list[str] = field(default_factory=list)  # Allied ethnic IDs
    rivals: list[str] = field(default_factory=list)     # Hostile ethnic IDs

    # Status
    is_extinct: bool = False
    assimilation_progress: dict[str, float] = field(default_factory=dict)  # ethnic_id -> progress (0-1)

    # Statistics
    birth_rate: float = 1.0
    mortality_rate: float = 1.0
    assimilation_rate: float = 0.01  # How fast members assimilate

    def add_trait(self, trait: CulturalTrait) -> None:
        """Add a cultural trait."""
        self.traits.append(trait)

    def get_traits_by_type(self, trait_type: CulturalTraitType) -> list[CulturalTrait]:
        """Get all traits of a specific type."""
        return [t for t in self.traits if t.trait_type == trait_type]

    def get_relation(self, other_ethnic_id: str) -> EthnicRelation:
        """Get relation with another ethnic group."""
        return self.relations.get(other_ethnic_id, EthnicRelation.NEUTRAL)

    def set_relation(self, other_ethnic_id: str, relation: EthnicRelation) -> None:
        """Set relation with another ethnic group."""
        self.relations[other_ethnic_id] = relation

        # Update alliances/rivals lists
        if relation == EthnicRelation.ALLIED:
            if other_ethnic_id not in self.alliances:
                self.alliances.append(other_ethnic_id)
            if other_ethnic_id in self.rivals:
                self.rivals.remove(other_ethnic_id)
        elif relation == EthnicRelation.HOSTILE:
            if other_ethnic_id not in self.rivals:
                self.rivals.append(other_ethnic_id)
            if other_ethnic_id in self.alliances:
                self.alliances.remove(other_ethnic_id)

    def record_population(self, tick: Tick) -> None:
        """Record current population for historical tracking."""
        self.population_history.append((tick, self.population))
        # Keep only recent history
        if len(self.population_history) > 100:
            self.population_history = self.population_history[-100:]

    def update_territory(self, new_territory: BoundingBox | None) -> None:
        """Update current territory and record history."""
        if new_territory:
            self.historical_territories.append(new_territory)
            self.current_territory = new_territory

    def assimilate(self, other_ethnic_id: str, amount: float) -> bool:
        """Attempt to assimilate another ethnic group."""
        current = self.assimilation_progress.get(other_ethnic_id, 0.0)
        current += amount
        self.assimilation_progress[other_ethnic_id] = min(1.0, current)
        return current >= 1.0

    def get_dominance(self) -> float:
        """Calculate ethnic dominance (population + territory)."""
        pop_factor = min(1.0, self.population / 1000)
        return pop_factor


@dataclass
class EthnicConflict:
    """A conflict between ethnic groups."""

    conflict_id: EntityID
    ethnic_a: str
    ethnic_b: str
    conflict_type: str  # "territorial", "cultural", "economic", "religious"
    start_tick: Tick
    intensity: float = 0.5  # 0-1
    resolved: bool = False
    resolution_tick: Tick | None = None
    resolution_type: str = ""  # "conquest", "compromise", "separation", "assimilation"
    casualties: int = 0
    displaced: int = 0


class EthnicGroupManager:
    """
    Manages all ethnic groups in the world.

    Responsibilities:
    - Create and track ethnic groups
    - Manage inter-ethnic relations
    - Handle ethnic conflicts
    - Track cultural evolution
    - Manage assimilation processes
    """

    def __init__(self, world: World, seed: int = 42) -> None:
        self.world = world
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Ethnic group registry
        self._ethnic_groups: dict[EntityID, EthnicGroup] = {}

        # Agent to ethnic group mapping
        self._agent_ethnicity: dict[EntityID, EntityID] = {}

        # Active conflicts
        self._conflicts: dict[EntityID, EthnicConflict] = {}

        # Initialize default ethnic groups based on world configuration
        self._initialize_default_groups()

    def _initialize_default_groups(self) -> None:
        """Create default ethnic groups for the world."""

        # Create 3-5 initial ethnic groups spread across the world
        num_groups = self._rng.integers(3, 6)
        world_width = self.world._config.world.width
        world_height = self.world._config.world.height

        cultural_templates = [
            {
                "name": "Highland Clans",
                "short_name": "Highlanders",
                "language": "highland_tongue",
                "values": ("honor", "strength", "family"),
                "customs": ("wrestling", "feasting", "bardic_tradition"),
                "taboos": ("betrayal", "cowardice"),
                "appearance": "broad-shouldered, fair-skinned",
            },
            {
                "name": "River Folk",
                "short_name": "Riverians",
                "language": "river_speech",
                "values": ("trade", "diplomacy", "craftsmanship"),
                "customs": ("merchant_guilds", "river_festivals", "oral_history"),
                "taboos": ("desecration_of_rivers", "price_gouging"),
                "appearance": "olive-skinned, slender",
            },
            {
                "name": "Forest Tribes",
                "short_name": "Foresters",
                "language": "woodland_tongue",
                "values": ("harmony", "hunting", "elders"),
                "customs": ("animal_masks", "ritual_dances", "herb_lore"),
                "taboos": ("tree_cutting", "unmarried_childbearing"),
                "appearance": "weathered skin, keen-eyed",
            },
            {
                "name": "Desert Wanderers",
                "short_name": "Wanderers",
                "language": "sand_speech",
                "values": ("freedom", "survival", "hospitality"),
                "customs": ("caravans", "star_navigation", "water_sharing"),
                "taboos": ("hoarding_water", "attacking_travelers"),
                "appearance": "tan, wiry",
            },
            {
                "name": "Coastal Islanders",
                "short_name": "Islanders",
                "language": "sea_tongue",
                "values": ("navigation", "fishing", "courage"),
                "customs": ("sailing_races", "fish_festival", "ship_building"),
                "taboos": ("fishing_during_storms", "disrespecting_sea"),
                "appearance": "sun-darkened, sea-weathered",
            },
        ]

        for i, template in enumerate(cultural_templates[:num_groups]):
            import uuid

            ethnic_id = uuid.uuid4().hex[:16]

            # Calculate territory
            center_x = (i + 1) * (world_width // (num_groups + 1))
            center_y = world_height // 2
            size = min(world_width, world_height) // 6

            territory = BoundingBox(
                min_x=max(0, center_x - size),
                min_y=max(0, center_y - size),
                max_x=min(world_width - 1, center_x + size),
                max_y=min(world_height - 1, center_y + size),
            )

            # Create cultural traits
            traits = []
            for trait_type in CulturalTraitType:
                trait = CulturalTrait(
                    trait_id=uuid.uuid4().hex[:16],
                    trait_type=trait_type,
                    name=f"{template['short_name']} {trait_type.name.lower()}",
                    description=f"Traditional {trait_type.name.lower()} practice",
                )
                traits.append(trait)

            ethnic_group = EthnicGroup(
                ethnic_id=ethnic_id,
                name=template["name"],
                short_name=template["short_name"],
                language=template["language"],
                language_family=f"{template['short_name']}_family",
                origin_tick=self.world.current_tick if hasattr(self.world, 'current_tick') else 0,
                origin_position=Pos2D(center_x, center_y),
                origin_story=f"The {template['name']} emerged from the ancient lands.",
                homeland=territory,
                current_territory=territory,
                values=template["values"],
                customs=template["customs"],
                taboos=template["taboos"],
                appearance_desc=template["appearance"],
                traits=traits,
            )

            self._ethnic_groups[ethnic_id] = ethnic_group

    def create_ethnic_group(
        self,
        name: str,
        short_name: str,
        origin_position: Pos2D | None = None,
        language: str = "common",
        parent_ethnic_id: str | None = None,
    ) -> EthnicGroup:
        """Create a new ethnic group, optionally derived from another."""
        import uuid

        ethnic_id = uuid.uuid4().hex[:16]
        origin_tick = self.world.current_tick if hasattr(self.world, 'current_tick') else 0

        ethnic_group = EthnicGroup(
            ethnic_id=ethnic_id,
            name=name,
            short_name=short_name,
            language=language,
            origin_tick=origin_tick,
            origin_position=origin_position,
        )

        # Inherit from parent if specified
        if parent_ethnic_id and parent_ethnic_id in self._ethnic_groups:
            parent = self._ethnic_groups[parent_ethnic_id]
            ethnic_group.language_family = parent.language_family
            ethnic_group.values = parent.values
            ethnic_group.customs = parent.customs
            ethnic_group.taboos = parent.taboos
            ethnic_group.appearance_desc = parent.appearance_desc

            # Create variant traits
            import uuid
            ethnic_group.traits = [
                t.mutate() for t in parent.traits
            ]

        self._ethnic_groups[ethnic_id] = ethnic_group
        return ethnic_group

    def register_agent(self, agent_id: EntityID, ethnic_id: EntityID) -> bool:
        """Register an agent as a member of an ethnic group."""
        if ethnic_id not in self._ethnic_groups:
            return False

        self._agent_ethnicity[agent_id] = ethnic_id
        self._ethnic_groups[ethnic_id].population += 1
        return True

    def unregister_agent(self, agent_id: EntityID) -> bool:
        """Unregister an agent from their ethnic group."""
        if agent_id not in self._agent_ethnicity:
            return False

        ethnic_id = self._agent_ethnicity[agent_id]
        ethnic_group = self._ethnic_groups.get(ethnic_id)
        if ethnic_group:
            ethnic_group.population = max(0, ethnic_group.population - 1)

        del self._agent_ethnicity[agent_id]
        return True

    def get_agent_ethnicity(self, agent_id: EntityID) -> EthnicGroup | None:
        """Get the ethnic group an agent belongs to."""
        ethnic_id = self._agent_ethnicity.get(agent_id)
        if ethnic_id:
            return self._ethnic_groups.get(ethnic_id)
        return None

    def get_ethnic_group(self, ethnic_id: EntityID) -> EthnicGroup | None:
        """Get an ethnic group by ID."""
        return self._ethnic_groups.get(ethnic_id)

    def get_ethnic_group_by_name(self, name: str) -> EthnicGroup | None:
        """Get an ethnic group by name."""
        for ethnic_group in self._ethnic_groups.values():
            if ethnic_group.name.lower() == name.lower():
                return ethnic_group
        return None

    def get_all_ethnic_groups(self) -> list[EthnicGroup]:
        """Get all ethnic groups."""
        return list(self._ethnic_groups.values())

    def get_active_ethnic_groups(self) -> list[EthnicGroup]:
        """Get all non-extinct ethnic groups."""
        return [e for e in self._ethnic_groups.values() if not e.is_extinct]

    def get_dominant_ethnic_group(self) -> EthnicGroup | None:
        """Get the ethnic group with the highest population."""
        return max(
            self._ethnic_groups.values(),
            key=lambda e: e.population if not e.is_extinct else 0,
            default=None
        )

    def get_ethnic_groups_in_territory(self, position: Pos2D, radius: float) -> list[EthnicGroup]:
        """Get ethnic groups with territory near a position."""
        result = []
        for ethnic_group in self._ethnic_groups.values():
            if ethnic_group.is_extinct:
                continue
            territory = ethnic_group.current_territory or ethnic_group.homeland
            if territory and territory.contains(position):
                result.append(ethnic_group)
        return result

    def set_relation(
        self,
        ethnic_a_id: str,
        ethnic_b_id: str,
        relation: EthnicRelation
    ) -> None:
        """Set the relation between two ethnic groups."""
        group_a = self._ethnic_groups.get(ethnic_a_id)
        group_b = self._ethnic_groups.get(ethnic_b_id)

        if group_a and group_b:
            group_a.set_relation(ethnic_b_id, relation)
            # Set reciprocal relation
            reciprocal = {
                EthnicRelation.ALLIED: EthnicRelation.ALLIED,
                EthnicRelation.FRIENDLY: EthnicRelation.FRIENDLY,
                EthnicRelation.NEUTRAL: EthnicRelation.NEUTRAL,
                EthnicRelation.DISTANT: EthnicRelation.DISTANT,
                EthnicRelation.HOSTILE: EthnicRelation.HOSTILE,
                EthnicRelation.SUBJUGATED: EthnicRelation.SUBJUGATED,
                EthnicRelation.ASSIMILATED: EthnicRelation.ASSIMILATED,
            }.get(relation, EthnicRelation.NEUTRAL)
            group_b.set_relation(ethnic_a_id, reciprocal)

    def start_conflict(
        self,
        ethnic_a_id: str,
        ethnic_b_id: str,
        conflict_type: str = "territorial"
    ) -> EthnicConflict:
        """Start a conflict between two ethnic groups."""
        import uuid

        conflict = EthnicConflict(
            conflict_id=uuid.uuid4().hex[:16],
            ethnic_a=ethnic_a_id,
            ethnic_b=ethnic_b_id,
            conflict_type=conflict_type,
            start_tick=self.world.current_tick if hasattr(self.world, 'current_tick') else 0,
        )

        self._conflicts[conflict.conflict_id] = conflict

        # Update relations
        self.set_relation(ethnic_a_id, ethnic_b_id, EthnicRelation.HOSTILE)

        return conflict

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution_type: str,
        winner_id: str | None = None
    ) -> None:
        """Resolve a conflict."""
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            return

        conflict.resolved = True
        conflict.resolution_tick = self.world.current_tick if hasattr(self.world, 'current_tick') else 0
        conflict.resolution_type = resolution_type

        # Update relations based on resolution
        if resolution_type == "conquest" and winner_id:
            loser_id = conflict.ethnic_b if winner_id == conflict.ethnic_a else conflict.ethnic_a
            self.set_relation(winner_id, loser_id, EthnicRelation.SUBJUGATED)
        elif resolution_type == "separation":
            self.set_relation(conflict.ethnic_a, conflict.ethnic_b, EthnicRelation.DISTANT)
        elif resolution_type == "compromise":
            self.set_relation(conflict.ethnic_a, conflict.ethnic_b, EthnicRelation.FRIENDLY)

    def update(self, tick: int) -> None:
        """Update all ethnic groups."""
        # Record population for active groups
        for ethnic_group in self._ethnic_groups.values():
            if not ethnic_group.is_extinct:
                ethnic_group.record_population(tick)

        # Process conflicts
        for conflict in self._conflicts.values():
            if not conflict.resolved:
                self._update_conflict(conflict, tick)

        # Check for extinction
        self._check_extinction()

    def _update_conflict(self, conflict: EthnicConflict, tick: int) -> None:
        """Update a single conflict."""
        # Conflict intensity can change over time
        if tick - conflict.start_tick > 100:
            conflict.intensity = max(0.1, conflict.intensity - 0.01)

    def _check_extinction(self) -> None:
        """Check for and handle ethnic group extinction."""
        for ethnic_group in self._ethnic_groups.values():
            if ethnic_group.is_extinct:
                continue
            if ethnic_group.population <= 0:
                ethnic_group.is_extinct = True
                # Remove from agent registrations
                to_remove = [
                    aid for aid, eid in self._agent_ethnicity.items()
                    if eid == ethnic_group.ethnic_id
                ]
                for aid in to_remove:
                    del self._agent_ethnicity[aid]

    def get_statistics(self) -> dict[str, Any]:
        """Get ethnic group statistics."""
        active = self.get_active_ethnic_groups()
        return {
            "total_groups": len(self._ethnic_groups),
            "active_groups": len(active),
            "total_population": sum(e.population for e in active),
            "dominant_group": self.get_dominant_ethnic_group().name if self.get_dominant_ethnic_group() else None,
            "by_relation": {
                "alliances": sum(1 for e in active if e.alliances),
                "hostile": sum(1 for e in active if e.rivals),
            },
            "active_conflicts": len([c for c in self._conflicts.values() if not c.resolved]),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize ethnic group manager state."""
        return {
            "ethnic_groups": {
                eid: {
                    "name": e.name,
                    "short_name": e.short_name,
                    "population": e.population,
                    "language": e.language,
                    "is_extinct": e.is_extinct,
                }
                for eid, e in self._ethnic_groups.items()
            },
            "statistics": self.get_statistics(),
        }
