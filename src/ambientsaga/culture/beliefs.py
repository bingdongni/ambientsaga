"""
Belief system — worldviews, values, and cultural identity.

This module implements the belief and worldview layer of the simulation:
- Belief: a held proposition about the world
- Worldview: a collection of beliefs forming a coherent view
- Value: a principle that guides behavior
- Cultural Identity: group-level beliefs and values
- Norm: a social expectation derived from beliefs
- Taboo: a forbidden behavior based on belief

Key design goals:
1. Beliefs are probabilistic and can be revised
2. Worldviews create cultural coherence
3. Values are abstract principles, not specific rules
4. Cultural identity binds groups together
5. Norms emerge from shared beliefs
6. Taboos are deeply held and hard to change
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import numpy as np

from ambientsaga.config import CultureConfig
from ambientsaga.types import EntityID, new_entity_id

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Belief Types
# ---------------------------------------------------------------------------


class BeliefCategory(Enum):
    """Categories of beliefs."""

    METAPHYSICAL = auto()   # Supernatural, existential
    MORAL = auto()          # Right and wrong
    EPISTEMIC = auto()      # Knowledge and truth
    PRACTICAL = auto()      # How to achieve goals
    SOCIAL = auto()         # About relationships and society
    COSMOLOGICAL = auto()  # Origins and purpose of the universe


class BeliefStrength(Enum):
    """Strength levels for beliefs."""

    WEAK = 0.2
    MODERATE = 0.5
    STRONG = 0.75
    ABSOLUTE = 1.0


# ---------------------------------------------------------------------------
# Belief
# ---------------------------------------------------------------------------


@dataclass
class Belief:
    """A belief held by an agent."""

    belief_id: str  # Unique identifier
    category: BeliefCategory
    proposition: str  # The actual belief statement
    strength: float  # 0-1, how strongly held
    source: str  # How the belief was acquired
    tick_acquired: int = 0
    evidence: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    is_taboo: bool = False

    def __post_init__(self) -> None:
        self.strength = max(0.0, min(1.0, self.strength))

    def revise(self, evidence: str, strength_change: float) -> bool:
        """
        Revise belief based on new evidence.

        Returns True if the belief changed significantly.
        """
        if strength_change > 0:
            self.evidence.append(evidence)
        else:
            self.counter_evidence.append(evidence)

        old_strength = self.strength
        self.strength = max(0.0, min(1.0, self.strength + strength_change))

        return abs(self.strength - old_strength) > 0.05

    def generate_hash(self) -> str:
        """Generate a content hash for matching similar beliefs."""
        content = f"{self.category.name}:{self.proposition}"
        return hashlib.md5(content.encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Value
# ---------------------------------------------------------------------------


@dataclass
class Value:
    """An abstract principle that guides behavior."""

    value_id: str
    name: str  # e.g., "loyalty", "freedom", "hierarchy"
    description: str
    polarity: float  # -1 to 1, how positively it's viewed
    priority: int  # Higher = more important in conflicts
    cultural_origin: str = ""


# ---------------------------------------------------------------------------
# Cultural Norm
# ---------------------------------------------------------------------------


@dataclass
class Norm:
    """A social expectation derived from shared beliefs."""

    norm_id: str
    description: str
    category: BeliefCategory
    punishment_severity: float  # 0-1, how harshly violators are punished
    enforcement_rate: float  # 0-1, how consistently enforced
    associated_values: list[str] = field(default_factory=list)
    is_taboo: bool = False


# ---------------------------------------------------------------------------
# Cultural Identity
# ---------------------------------------------------------------------------


@dataclass
class CulturalIdentity:
    """Group-level cultural identity."""

    identity_id: str
    name: str
    shared_beliefs: dict[str, float] = field(default_factory=dict)  # belief_hash -> strength
    shared_values: list[str] = field(default_factory=list)  # value IDs
    norms: list[str] = field(default_factory=list)  # norm IDs
    taboos: list[str] = field(default_factory=list)  # taboo belief IDs
    founding_tick: int = 0
    member_count: int = 0
    cultural_coherence: float = 1.0  # 0-1, how much members agree

    def get_belief_consensus(self, belief_hash: str) -> float | None:
        """Get the consensus level for a belief (0-1)."""
        return self.shared_beliefs.get(belief_hash)


# ---------------------------------------------------------------------------
# BeliefSystem
# ---------------------------------------------------------------------------


class BeliefSystem:
    """
    Manages beliefs, values, and cultural identity across all agents.

    The BeliefSystem:
    1. Tracks belief propagation and revision
    2. Manages cultural identity formation
    3. Generates social norms from shared beliefs
    4. Handles belief conflicts and resolutions
    5. Tracks cultural evolution over time
    """

    def __init__(
        self,
        config: CultureConfig | None = None,
        seed: int = 42,
    ) -> None:
        self._config = config or CultureConfig()
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # All beliefs indexed by ID
        self._beliefs: dict[str, Belief] = {}

        # All values
        self._values: dict[str, Value] = {}

        # All norms
        self._norms: dict[str, Norm] = {}

        # Cultural identities
        self._identities: dict[str, CulturalIdentity] = {}

        # Agent beliefs: agent_id -> list of belief IDs
        self._agent_beliefs: dict[EntityID, list[str]] = {}

        # Initialize core values
        self._initialize_core_values()

    def _initialize_core_values(self) -> None:
        """Initialize the core value set."""
        core_values = [
            Value("loyalty", "Loyalty", "Commitment to group and relationships", 0.8, 5),
            Value("freedom", "Freedom", "Individual autonomy and choice", 0.7, 6),
            Value("hierarchy", "Hierarchy", "Respect for authority and order", 0.6, 4),
            Value("equality", "Equality", "Fairness and equal treatment", 0.7, 5),
            Value("reciprocity", "Reciprocity", "Mutual benefit in exchanges", 0.9, 7),
            Value("reciprocity_neg", "Reciprocity (Negative)", "Punishment for those who harm", 0.85, 6),
            Value("property", "Property Rights", "Ownership of resources and goods", 0.8, 5),
            Value("hospitality", "Hospitality", "Welcoming guests and strangers", 0.7, 4),
            Value("piety", "Piety", "Devotion to the divine/supernatural", 0.6, 5),
            Value("honor", "Honor", "Reputation and personal integrity", 0.8, 6),
            Value("justice", "Justice", "Fair treatment and accountability", 0.85, 7),
            Value("solidarity", "Solidarity", "Unity within the group", 0.9, 6),
            Value("progress", "Progress", "Improvement and advancement", 0.7, 4),
            Value("tradition", "Tradition", "Preserving ancestral ways", 0.65, 4),
            Value("curiosity", "Curiosity", "Seeking knowledge and understanding", 0.7, 3),
        ]

        for value in core_values:
            self._values[value.value_id] = value

    # -------------------------------------------------------------------------
    # Agent Belief Management
    # -------------------------------------------------------------------------

    def agent_acquires_belief(
        self,
        agent_id: EntityID,
        proposition: str,
        category: BeliefCategory,
        strength: float = 0.5,
        source: str = "social",
        is_taboo: bool = False,
    ) -> str:
        """Agent acquires a new belief."""
        belief_id = new_entity_id()
        belief = Belief(
            belief_id=belief_id,
            category=category,
            proposition=proposition,
            strength=strength,
            source=source,
            tick_acquired=0,  # Set by caller
            is_taboo=is_taboo,
        )

        self._beliefs[belief_id] = belief
        self._agent_beliefs.setdefault(agent_id, []).append(belief_id)

        return belief_id

    def agent_revises_belief(
        self,
        agent_id: EntityID,
        belief_id: str,
        evidence: str,
        strength_change: float,
    ) -> bool:
        """Revise an agent's belief."""
        belief = self._beliefs.get(belief_id)
        if belief is None:
            return False

        return belief.revise(evidence, strength_change)

    def get_agent_beliefs(
        self,
        agent_id: EntityID,
        category: BeliefCategory | None = None,
        min_strength: float = 0.0,
    ) -> list[Belief]:
        """Get an agent's beliefs, optionally filtered."""
        belief_ids = self._agent_beliefs.get(agent_id, [])
        beliefs = [self._beliefs[bid] for bid in belief_ids if bid in self._beliefs]

        if category is not None:
            beliefs = [b for b in beliefs if b.category == category]
        if min_strength > 0:
            beliefs = [b for b in beliefs if b.strength >= min_strength]

        return beliefs

    # -------------------------------------------------------------------------
    # Belief Propagation
    # -------------------------------------------------------------------------

    def propagate_belief(
        self,
        source_agent_id: EntityID,
        target_agent_id: EntityID,
        belief_id: str,
        similarity: float,  # 0-1, how similar the agents are
    ) -> float:
        """
        Propagate a belief from one agent to another.

        Returns the resulting belief strength in the target agent.
        """
        source_belief = self._beliefs.get(belief_id)
        if source_belief is None:
            return 0.0

        # Check if target already has this belief
        target_beliefs = self._agent_beliefs.get(target_agent_id, [])
        existing_ids = [bid for bid in target_beliefs if bid in self._beliefs]
        existing = next(
            (bid for bid in existing_ids
             if self._beliefs[bid].proposition == source_belief.proposition
             and self._beliefs[bid].category == source_belief.category),
            None
        )

        # Propagation strength based on source strength and similarity
        base_strength = source_belief.strength * similarity * 0.7

        if existing:
            # Revise existing belief
            belief = self._beliefs[existing]
            belief.revise(f"social propagation from {source_agent_id}", base_strength * 0.1)
            return belief.strength
        else:
            # Create new belief
            new_id = self.agent_acquires_belief(
                target_agent_id,
                source_belief.proposition,
                source_belief.category,
                base_strength,
                source=f"propagated from {source_agent_id}",
                is_taboo=source_belief.is_taboo,
            )
            return base_strength

    # -------------------------------------------------------------------------
    # Cultural Identity
    # -------------------------------------------------------------------------

    def create_cultural_identity(
        self,
        name: str,
        founding_tick: int,
        founding_members: list[EntityID],
    ) -> str:
        """Create a new cultural identity from a founding group."""
        identity_id = new_entity_id()

        # Collect shared beliefs from founding members
        shared_beliefs: dict[str, float] = {}
        belief_counts: dict[str, int] = {}

        for member_id in founding_members:
            beliefs = self.get_agent_beliefs(member_id)
            for belief in beliefs:
                bh = belief.generate_hash()
                shared_beliefs[bh] = shared_beliefs.get(bh, 0.0) + belief.strength
                belief_counts[bh] = belief_counts.get(bh, 0) + 1

        # Only include beliefs shared by at least 50% of members
        threshold = len(founding_members) // 2
        final_beliefs = {
            bh: strength / belief_counts[bh]
            for bh, strength in shared_beliefs.items()
            if belief_counts[bh] >= threshold
        }

        # Calculate cultural coherence
        coherence = len(final_beliefs) / max(1, len(shared_beliefs))

        identity = CulturalIdentity(
            identity_id=identity_id,
            name=name,
            shared_beliefs=final_beliefs,
            founding_tick=founding_tick,
            member_count=len(founding_members),
            cultural_coherence=coherence,
        )

        self._identities[identity_id] = identity
        return identity_id

    def update_cultural_identity(self, identity_id: str) -> None:
        """Update a cultural identity based on current member beliefs."""
        identity = self._identities.get(identity_id)
        if identity is None:
            return

        # Recalculate shared beliefs
        belief_totals: dict[str, float] = {}
        belief_counts: dict[str, int] = {}

        for belief_id, belief in self._beliefs.items():
            bh = belief.generate_hash()
            belief_totals[bh] = belief_totals.get(bh, 0.0) + belief.strength
            belief_counts[bh] = belief_counts.get(bh, 0) + 1

        # Average belief strength
        for bh in belief_totals:
            belief_totals[bh] /= belief_counts[bh]

        identity.shared_beliefs = belief_totals
        identity.cultural_coherence = len(belief_totals) / max(1, len(self._beliefs))

    # -------------------------------------------------------------------------
    # Norm Generation
    # -------------------------------------------------------------------------

    def generate_norms(self, identity_id: str) -> list[Norm]:
        """Generate social norms from a cultural identity's beliefs."""
        identity = self._identities.get(identity_id)
        if identity is None:
            return []

        norms = []
        for bh, strength in identity.shared_beliefs.items():
            if strength < 0.7:  # Only strong beliefs generate norms
                continue

            # Find the actual belief
            belief = next(
                (b for b in self._beliefs.values() if b.generate_hash() == bh),
                None
            )
            if belief is None:
                continue

            # Create a norm from strong moral/social beliefs
            if belief.category in (BeliefCategory.MORAL, BeliefCategory.SOCIAL):
                norm_id = new_entity_id()
                norm = Norm(
                    norm_id=norm_id,
                    description=f"Members should {belief.proposition.lower()}",
                    category=belief.category,
                    punishment_severity=strength * 0.8,
                    enforcement_rate=0.5,
                    is_taboo=belief.is_taboo or strength > 0.9,
                )
                self._norms[norm_id] = norm
                norms.append(norm)

        return norms

    # -------------------------------------------------------------------------
    # Update
    # -------------------------------------------------------------------------

    def update(self, tick: int) -> None:
        """Update belief system each tick."""
        # Believers may gain/lose strength over time
        for belief in self._beliefs.values():
            # Taboos slowly strengthen, non-taboos slowly decay toward 0.5
            if belief.is_taboo:
                belief.strength = min(1.0, belief.strength * 1.001)
            else:
                decay = 1.0 - abs(belief.strength - 0.5) * 0.001
                belief.strength = 0.5 + (belief.strength - 0.5) * decay

    def get_belief_diversity(self) -> float:
        """Get the diversity of beliefs across all agents (0-1)."""
        if not self._beliefs:
            return 0.0

        total_belief_types = len({b.category for b in self._beliefs.values()})
        return min(1.0, total_belief_types / len(BeliefCategory))

    def get_stats(self) -> dict[str, Any]:
        """Get belief system statistics."""
        category_counts = {}
        for belief in self._beliefs.values():
            cat = belief.category.name
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "total_beliefs": len(self._beliefs),
            "total_values": len(self._values),
            "total_norms": len(self._norms),
            "total_identities": len(self._identities),
            "beliefs_by_category": category_counts,
            "taboo_count": sum(1 for b in self._beliefs.values() if b.is_taboo),
            "belief_diversity": self.get_belief_diversity(),
        }
