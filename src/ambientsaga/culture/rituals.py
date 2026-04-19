"""
Ritual system — religious practices, ceremonies, and cultural traditions.

This module implements:
- Ritual: a symbolic activity with cultural meaning
- Ceremony: formal ritual with social function
- Tradition: inherited ritual practice
- Religion: organized system of rituals and beliefs
- Myth: narrative that encodes cultural values

Key design goals:
1. Rituals create social cohesion
2. Religious beliefs affect economic/social behavior
3. Rituals can be adaptive or maladaptive
4. New rituals emerge from creative agents
5. Religious institutions can accumulate power
6. Rituals reflect and reinforce cultural identity
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING, Any
from dataclasses import dataclass, field
from enum import Enum, auto

from ambientsaga.config import CultureConfig
from ambientsaga.types import EntityID, Pos2D, new_entity_id

if TYPE_CHECKING:
    from ambientsaga.world.state import World


# ---------------------------------------------------------------------------
# Ritual Types
# ---------------------------------------------------------------------------


class RitualType(Enum):
    """Types of rituals."""

    INDIVIDUAL = auto()    # Personal practice
    FAMILY = auto()        # Family-level
    COMMUNITY = auto()     # Group-level
    SEASONAL = auto()      # Time-based
    LIFE_CYCLE = auto()    # Birth, marriage, death
    CRISIS = auto()        # Response to events
    DIVINE = auto()        # Worship/supplication


class ReligionType(Enum):
    """Types of religious organization."""

    TOTEMIC = auto()        # Nature spirits
    ANCESTOR = auto()       # Honoring the dead
    POLYTHEISTIC = auto()   # Multiple gods
    MONOTHEISTIC = auto()   # Single god
    NATURIST = auto()       # Nature worship
    NONE = auto()           # No organized religion


# ---------------------------------------------------------------------------
# Ritual
# ---------------------------------------------------------------------------


@dataclass
class Ritual:
    """A ritual practice."""

    ritual_id: str
    name: str
    ritual_type: RitualType
    description: str
    frequency: float  # How often (ticks between occurrences)
    duration: int  # How long (in ticks)
    participants_min: int = 1
    participants_max: int = 100
    cost: float = 0.0  # Resources consumed
    benefit: float = 0.0  # Social/symbolic benefit
    required_beliefs: list[str] = field(default_factory=list)  # Belief hashes
    effects: dict[str, float] = field(default_factory=dict)  # Effect -> magnitude
    last_performed: int = -1000
    performed_count: int = 0
    associated_identity: str = ""


@dataclass
class Religion:
    """An organized religious system."""

    religion_id: str
    name: str
    religion_type: ReligionType
    founder_id: EntityID = ""
    founding_tick: int = 0
    deity_names: list[str] = field(default_factory=list)
    core_rituals: list[str] = field(default_factory=list)  # Ritual IDs
    doctrines: list[str] = field(default_factory=list)
    followers: set[EntityID] = field(default_factory=set)
    institutions: list[str] = field(default_factory=list)  # Org IDs
    hierarchy_depth: int = 1  # How many levels of clergy
    texts: list[str] = field(default_factory=list)  # Sacred text content
    influence: float = 0.5  # 0-1, cultural influence


# ---------------------------------------------------------------------------
# RitualSystem
# ---------------------------------------------------------------------------


class RitualSystem:
    """
    Manages rituals, religions, and cultural traditions.

    The RitualSystem:
    1. Tracks ritual performance and effects
    2. Manages religious organizations
    3. Handles religious conversion
    4. Generates new rituals over time
    5. Applies ritual effects on social cohesion and agent behavior
    """

    def __init__(
        self,
        config: CultureConfig | None = None,
        seed: int = 42,
    ) -> None:
        self._config = config or CultureConfig()
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # All rituals
        self._rituals: dict[str, Ritual] = {}

        # All religions
        self._religions: dict[str, Religion] = {}

        # Active ritual participants: ritual_id -> list of agent IDs
        self._active_rituals: dict[str, list[EntityID]] = {}

        # Initialize core rituals
        self._initialize_core_rituals()

    def _initialize_core_rituals(self) -> None:
        """Initialize a set of foundational rituals."""
        core_rituals = [
            Ritual(
                ritual_id="birth_ceremony",
                name="Birth Ceremony",
                ritual_type=RitualType.LIFE_CYCLE,
                description="Welcoming a new member into the community",
                frequency=720,  # ~twice per year (rough estimate)
                duration=10,
                participants_min=3,
                participants_max=20,
                benefit=0.3,
                effects={"social_cohesion": 0.2, "group_bonding": 0.3},
            ),
            Ritual(
                ritual_id="marriage_ceremony",
                name="Marriage Ceremony",
                ritual_type=RitualType.LIFE_CYCLE,
                description="Union of two individuals",
                frequency=180,  # Roughly twice per year
                duration=20,
                participants_min=5,
                participants_max=50,
                cost=50.0,
                benefit=0.5,
                effects={"social_cohesion": 0.4, "alliance_formation": 0.3},
            ),
            Ritual(
                ritual_id="funeral_rite",
                name="Funeral Rite",
                ritual_type=RitualType.LIFE_CYCLE,
                description="Honoring the deceased",
                frequency=365,
                duration=15,
                participants_min=2,
                participants_max=100,
                benefit=0.4,
                effects={"grief_processing": 0.3, "community_support": 0.2},
            ),
            Ritual(
                ritual_id="harvest_festival",
                name="Harvest Festival",
                ritual_type=RitualType.SEASONAL,
                description="Celebrating seasonal abundance",
                frequency=360,
                duration=50,
                participants_min=10,
                participants_max=500,
                cost=100.0,
                benefit=0.6,
                effects={"social_cohesion": 0.5, "cultural_pride": 0.3},
            ),
            Ritual(
                ritual_id="daily_prayer",
                name="Daily Prayer",
                ritual_type=RitualType.DIVINE,
                description="Individual communication with the divine",
                frequency=1,
                duration=5,
                participants_min=1,
                participants_max=1,
                benefit=0.1,
                effects={"individual_meaning": 0.2},
            ),
            Ritual(
                ritual_id="community_gathering",
                name="Community Gathering",
                ritual_type=RitualType.COMMUNITY,
                description="Regular meeting of community members",
                frequency=7,
                duration=30,
                participants_min=5,
                participants_max=100,
                benefit=0.3,
                effects={"social_cohesion": 0.3, "information_sharing": 0.2},
            ),
            Ritual(
                ritual_id="solstice_celebration",
                name="Solstice Celebration",
                ritual_type=RitualType.SEASONAL,
                description="Honoring the sun's cycle",
                frequency=180,
                duration=40,
                participants_min=10,
                participants_max=300,
                cost=80.0,
                benefit=0.5,
                effects={"cultural_identity": 0.3, "seasonal_awareness": 0.2},
            ),
            Ritual(
                ritual_id="coming_of_age",
                name="Coming of Age Ceremony",
                ritual_type=RitualType.LIFE_CYCLE,
                description="Transition to adulthood",
                frequency=2190,  # ~every 6 years
                duration=30,
                participants_min=5,
                participants_max=50,
                cost=30.0,
                benefit=0.4,
                effects={"status_change": 0.5, "social_recognition": 0.3},
            ),
            Ritual(
                ritual_id="oath_ritual",
                name="Oath Ritual",
                ritual_type=RitualType.CRISIS,
                description="Solemn promise with witnesses",
                frequency=365,
                duration=15,
                participants_min=3,
                participants_max=10,
                benefit=0.3,
                effects={"trust_formation": 0.4, "commitment": 0.3},
            ),
            Ritual(
                ritual_id="healing_ritual",
                name="Healing Ritual",
                ritual_type=RitualType.CRISIS,
                description="Seeking supernatural aid for illness",
                frequency=182,
                duration=20,
                participants_min=1,
                participants_max=10,
                cost=10.0,
                benefit=0.2,
                effects={"psychological_comfort": 0.3, "community_support": 0.2},
            ),
        ]

        for ritual in core_rituals:
            self._rituals[ritual.ritual_id] = ritual

    # -------------------------------------------------------------------------
    # Ritual Performance
    # -------------------------------------------------------------------------

    def perform_ritual(
        self,
        ritual_id: str,
        participants: list[EntityID],
        tick: int,
    ) -> bool:
        """
        Perform a ritual with the given participants.

        Returns True if the ritual was performed successfully.
        """
        ritual = self._rituals.get(ritual_id)
        if ritual is None:
            return False

        # Check timing
        if tick - ritual.last_performed < ritual.frequency:
            return False

        # Check participant count
        if not (ritual.participants_min <= len(participants) <= ritual.participants_max):
            return False

        ritual.last_performed = tick
        ritual.performed_count += 1
        self._active_rituals[ritual_id] = participants

        return True

    def can_perform_ritual(
        self,
        ritual_id: str,
        participant_count: int,
        tick: int,
    ) -> bool:
        """Check if a ritual can be performed."""
        ritual = self._rituals.get(ritual_id)
        if ritual is None:
            return False

        time_ok = tick - ritual.last_performed >= ritual.frequency
        count_ok = ritual.participants_min <= participant_count <= ritual.participants_max

        return time_ok and count_ok

    def get_ritual_effect(
        self,
        ritual_id: str,
        effect_name: str,
    ) -> float:
        """Get the magnitude of a ritual's effect."""
        ritual = self._rituals.get(ritual_id)
        if ritual is None:
            return 0.0

        return ritual.effects.get(effect_name, 0.0)

    # -------------------------------------------------------------------------
    # Religion Management
    # -------------------------------------------------------------------------

    def found_religion(
        self,
        founder_id: EntityID,
        name: str,
        religion_type: ReligionType,
        tick: int,
    ) -> str:
        """Found a new religion."""
        religion_id = new_entity_id()
        religion = Religion(
            religion_id=religion_id,
            name=name,
            religion_type=religion_type,
            founder_id=founder_id,
            founding_tick=tick,
            followers={founder_id},
            influence=0.1,
        )

        self._religions[religion_id] = religion
        return religion_id

    def convert_to_religion(
        self,
        agent_id: EntityID,
        religion_id: str,
        conviction: float = 0.5,
    ) -> bool:
        """An agent converts to a religion."""
        religion = self._religions.get(religion_id)
        if religion is None:
            return False

        religion.followers.add(agent_id)
        religion.influence = min(1.0, religion.influence + conviction * 0.01)
        return True

    def leave_religion(
        self,
        agent_id: EntityID,
        religion_id: str,
    ) -> bool:
        """An agent leaves a religion."""
        religion = self._religions.get(religion_id)
        if religion is None:
            return False

        religion.followers.discard(agent_id)
        religion.influence = max(0.0, religion.influence - 0.02)
        return True

    def get_agent_religion(self, agent_id: EntityID) -> Religion | None:
        """Get the religion an agent follows."""
        for religion in self._religions.values():
            if agent_id in religion.followers:
                return religion
        return None

    # -------------------------------------------------------------------------
    # New Rituals
    # -------------------------------------------------------------------------

    def generate_new_ritual(
        self,
        identity_id: str,
        ritual_type: RitualType,
        context: dict[str, Any],
    ) -> str:
        """Generate a new ritual based on cultural context."""
        ritual_id = new_entity_id()

        names = {
            RitualType.INDIVIDUAL: ["Meditation", "Vigil", "Contemplation"],
            RitualType.FAMILY: ["Blessing", "Naming", "Dedication"],
            RitualType.COMMUNITY: ["Gathering", "Council", "Celebration"],
            RitualType.SEASONAL: ["Festival", "Observance", "Festival"],
            RitualType.LIFE_CYCLE: ["Transition", "Rite", "Ceremony"],
            RitualType.CRISIS: ["Purification", "Invocation", "Supplication"],
            RitualType.DIVINE: ["Worship", "Devotion", "Offering"],
        }

        name = self._rng.choice(names.get(ritual_type, ["Ritual"]))

        ritual = Ritual(
            ritual_id=ritual_id,
            name=name,
            ritual_type=ritual_type,
            description=f"A {name.lower()} ritual",
            frequency=self._rng.integers(7, 365),
            duration=self._rng.integers(5, 60),
            participants_min=1,
            participants_max=self._rng.integers(5, 200),
            cost=self._rng.uniform(0, 100),
            benefit=self._rng.uniform(0.1, 0.5),
            effects={
                "social_cohesion": self._rng.uniform(0.1, 0.4),
                "cultural_meaning": self._rng.uniform(0.1, 0.3),
            },
            associated_identity=identity_id,
        )

        self._rituals[ritual_id] = ritual
        return ritual_id

    # -------------------------------------------------------------------------
    # Update
    # -------------------------------------------------------------------------

    def update(self, tick: int) -> None:
        """Update ritual system each tick."""
        # Clean up completed rituals
        for ritual_id in list(self._active_rituals.keys()):
            ritual = self._rituals.get(ritual_id)
            if ritual and tick - ritual.last_performed > ritual.duration:
                self._active_rituals.pop(ritual_id, None)

        # Religious influence slowly changes
        for religion in self._religions.values():
            # More followers = more influence
            target_influence = min(1.0, len(religion.followers) / 100.0)
            religion.influence += (target_influence - religion.influence) * 0.001

    def get_stats(self) -> dict[str, Any]:
        """Get ritual system statistics."""
        rituals_by_type = {}
        for ritual in self._rituals.values():
            t = ritual.ritual_type.name
            rituals_by_type[t] = rituals_by_type.get(t, 0) + 1

        return {
            "total_rituals": len(self._rituals),
            "total_religions": len(self._religions),
            "rituals_by_type": rituals_by_type,
            "total_followers": sum(len(r.followers) for r in self._religions.values()),
            "active_rituals": len(self._active_rituals),
        }
