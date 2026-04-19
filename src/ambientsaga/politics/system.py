"""
Political System - Governance, laws, power, and conflict.

Features:
- Government structures: monarchy, democracy, theocracy, anarchy
- Laws and enforcement: legislation, courts, punishment
- Power dynamics: authority, legitimacy, revolution
- Conflict resolution: negotiation, mediation, war
- Institution building: organizations, bureaucracy

Academic value:
- Political evolution patterns
- Law emergence and enforcement
- Power transition dynamics
- Collective action theory

Engineering value:
- Policy propagation
- Efficient law lookup
- Conflict resolution algorithms
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ambientsaga.world.state import World


# ============================================================================
# Political Types
# ============================================================================

class GovernmentType(Enum):
    """Types of government."""
    ANARCHY = "anarchy"           # No central authority
    TRIBAL = "tribal"             # Small scale, leader-based
    MONARCHY = "monarchy"         # Single ruler
    ARISTOCRACY = "aristocracy"  # Rule by elite
    OLIGARCHY = "oligarchy"      # Rule by few
    DEMOCRACY = "democracy"      # Rule by people
    THEOCRACY = "theocracy"      # Rule by religious authority
    REPUBLIC = "republic"         # Elected representatives
    CONFEDERATION = "confederation"  # League of states


class LawType(Enum):
    """Categories of laws."""
    PROPERTY = "property"         # Ownership rights
    VIOLENCE = "violence"         # Prohibition on harm
    TRADE = "trade"              # Commerce regulations
    FAMILY = "family"             # Marriage, children
    RELIGION = "religion"         # Spiritual practices
    JUSTICE = "justice"           # Legal procedures
    TAX = "tax"                   # Revenue collection
    MILITARY = "military"         # Defense duties
    SPEECH = "speech"             # Expression limits
    MOVEMENT = "movement"         # Travel restrictions


class AuthorityLevel(Enum):
    """Levels of authority."""
    LOCAL = "local"       # Village/neighborhood
    REGIONAL = "regional"  # Province/region
    NATIONAL = "national"  # Country
    RELIGIOUS = "religious"  # Spiritual
    MILITARY = "military"  # Armed forces


@dataclass
class Law:
    """A law or rule."""
    law_id: str
    name: str
    description: str
    law_type: LawType
    severity: float = 0.5  # 0-1, how serious violation is
    penalty: str = "fine"  # fine, imprisonment, exile, death
    penalty_severity: float = 0.5
    enforcement: float = 0.5  # 0-1, how strictly enforced

    # Applicability
    applies_to: list[str] = field(default_factory=lambda: ["all"])  # roles, groups
    region: str = "all"

    # Meta
    created_tick: int = 0
    created_by: str = ""
    vote_passed: float = 0.5  # 0-1, consensus level

    # Effectiveness tracking
    violation_count: int = 0
    enforcement_count: int = 0


@dataclass
class Authority:
    """A position of authority."""
    authority_id: str
    title: str  # "King", "Mayor", "Judge"
    level: AuthorityLevel
    holder_id: str | None = None

    # Power scope
    scope: str = "all"  # region, organization
    jurisdiction: list[str] = field(default_factory=lambda: ["all"])

    # Authority powers
    can_make_laws: bool = False
    can_enforce_laws: bool = False
    can_collect_taxes: bool = False
    can_declare_war: bool = False
    can_pardon: bool = False

    # Term limits
    term_length: int = 0  # 0 = lifetime
    election_interval: int = 0  # 0 = not elected

    # Succession
    succession_type: str = "hereditary"  # hereditary, election, appointment

    # Current holder
    appointed_by: str | None = None
    started_term: int = 0


@dataclass
class Policy:
    """A government policy or decree."""
    policy_id: str
    name: str
    description: str

    # Policy content
    rules: list[str] = field(default_factory=list)  # rule descriptions
    resource_changes: dict[str, float] = field(default_factory=dict)  # tax rates, etc

    # Implementation
    enacted_tick: int = 0
    enacted_by: str = ""
    expires_tick: int | None = None

    # Scope
    scope: str = "all"  # who/what it applies to
    region: str = "all"

    # Effectiveness
    compliance_rate: float = 0.5
    effectiveness: float = 0.5  # 0-1, achieving goals


@dataclass
class Institution:
    """A political institution."""
    institution_id: str
    name: str
    institution_type: str  # "court", "bureaucracy", "military", "religious"

    # Structure
    authorities: list[str] = field(default_factory=list)  # authority IDs
    members: list[str] = field(default_factory=list)  # agent IDs

    # Function
    purpose: str = ""
    functions: list[str] = field(default_factory=list)

    # Resources
    treasury: float = 0.0
    resources: dict[str, float] = field(default_factory=dict)

    # Location
    location_x: int = 0
    location_y: int = 0


@dataclass
class PoliticalEvent:
    """A political event."""
    tick: int
    event_type: str  # "law_passed", "election", "war_declared", "revolt"
    description: str

    # Participants
    actors: list[str] = field(default_factory=list)  # agent IDs

    # Outcome
    outcome: dict = field(default_factory=dict)

    # Significance
    impact: float = 0.5  # 0-1, how major


# ============================================================================
# Political System
# ============================================================================

class PoliticalSystem:
    """
    Manages all political structures and processes.

    Features:
    - Law creation and enforcement
    - Authority and power structures
    - Policy implementation
    - Conflict and war resolution
    """

    def __init__(self, world: World):
        self.world = world

        # Political structures
        self._laws: dict[str, Law] = {}
        self._authorities: dict[str, Authority] = {}
        self._institutions: dict[str, Institution] = {}
        self._policies: dict[str, Policy] = {}
        self._political_events: list[PoliticalEvent] = []

        # Government state
        self._government_type: GovernmentType = GovernmentType.TRIBAL
        self._ruler_id: str | None = None
        self._succession_tension: float = 0.0  # 0-1, revolution risk

        # Initialize default laws
        self._setup_default_laws()

    def _setup_default_laws(self) -> None:
        """Initialize basic laws."""
        default_laws = [
            Law(
                law_id="no_murder",
                name="Murder Prohibition",
                description="Killing another person is forbidden",
                law_type=LawType.VIOLENCE,
                severity=1.0,
                penalty="death",
                penalty_severity=1.0,
                enforcement=0.8,
            ),
            Law(
                law_id="no_theft",
                name="Theft Prohibition",
                description="Taking others' property is forbidden",
                law_type=LawType.PROPERTY,
                severity=0.7,
                penalty="fine",
                penalty_severity=0.5,
                enforcement=0.7,
            ),
            Law(
                law_id="no_assault",
                name="Assault Prohibition",
                description="Violent harm to others is forbidden",
                law_type=LawType.VIOLENCE,
                severity=0.6,
                penalty="imprisonment",
                penalty_severity=0.5,
                enforcement=0.6,
            ),
            Law(
                law_id="property_rights",
                name="Property Rights",
                description="Ownership of property is protected",
                law_type=LawType.PROPERTY,
                severity=0.8,
                penalty="fine",
                penalty_severity=0.4,
                enforcement=0.7,
            ),
            Law(
                law_id="fair_trade",
                name="Fair Trade",
                description="Honest dealing in commerce required",
                law_type=LawType.TRADE,
                severity=0.4,
                penalty="fine",
                penalty_severity=0.3,
                enforcement=0.5,
            ),
        ]

        for law in default_laws:
            self._laws[law.law_id] = law

    def get_law(self, law_id: str) -> Law | None:
        """Get a law by ID."""
        return self._laws.get(law_id)

    def get_laws_by_type(self, law_type: LawType) -> list[Law]:
        """Get all laws of a type."""
        return [l for l in self._laws.values() if l.law_type == law_type]

    def create_law(
        self,
        name: str,
        description: str,
        law_type: LawType,
        created_by: str,
        severity: float = 0.5,
        penalty: str = "fine",
        penalty_severity: float = 0.5,
    ) -> Law:
        """Create a new law."""
        law_id = f"law_{len(self._laws)}"
        law = Law(
            law_id=law_id,
            name=name,
            description=description,
            law_type=law_type,
            severity=severity,
            penalty=penalty,
            penalty_severity=penalty_severity,
            created_tick=self.world.tick,
            created_by=created_by,
        )
        self._laws[law_id] = law

        self._political_events.append(PoliticalEvent(
            tick=self.world.tick,
            event_type="law_passed",
            description=f"Law created: {name}",
            actors=[created_by],
            impact=severity,
        ))

        return law

    def get_authority(self, authority_id: str) -> Authority | None:
        """Get an authority by ID."""
        return self._authorities.get(authority_id)

    def create_authority(
        self,
        title: str,
        level: AuthorityLevel,
        holder_id: str | None = None,
    ) -> Authority:
        """Create a new authority."""
        authority_id = f"authority_{len(self._authorities)}"
        authority = Authority(
            authority_id=authority_id,
            title=title,
            level=level,
            holder_id=holder_id,
            started_term=self.world.tick,
        )
        self._authorities[authority_id] = authority

        if holder_id:
            self._ruler_id = holder_id

        return authority

    def grant_authority(
        self,
        authority_id: str,
        agent_id: str,
        granted_by: str | None = None,
    ) -> bool:
        """Grant authority to an agent."""
        authority = self._authorities.get(authority_id)
        if not authority:
            return False

        authority.holder_id = agent_id
        authority.appointed_by = granted_by
        authority.started_term = self.world.tick

        return True

    def get_ruler(self) -> str | None:
        """Get current ruler."""
        return self._ruler_id

    def set_ruler(self, agent_id: str) -> None:
        """Set the ruler."""
        self._ruler_id = agent_id
        # Create ruler authority if doesn't exist
        if not any(a.holder_id == agent_id for a in self._authorities.values()):
            self.create_authority(
                title="Ruler",
                level=AuthorityLevel.NATIONAL,
                holder_id=agent_id,
            )

    def can_make_law(self, agent_id: str) -> bool:
        """Check if agent can make laws."""
        # Check if they hold law-making authority
        for auth in self._authorities.values():
            if auth.holder_id == agent_id and auth.can_make_laws:
                return True
        # Ruler can always make laws
        if agent_id == self._ruler_id:
            return True
        return False

    def can_enforce_law(self, agent_id: str) -> bool:
        """Check if agent can enforce laws."""
        for auth in self._authorities.values():
            if auth.holder_id == agent_id and auth.can_enforce_laws:
                return True
        if agent_id == self._ruler_id:
            return True
        return False

    def enforce_law(
        self,
        law_id: str,
        violator_id: str,
        enforcer_id: str,
    ) -> dict:
        """Enforce a law against a violator."""
        law = self._laws.get(law_id)
        if not law:
            return {"success": False, "reason": "Law not found"}

        law.violation_count += 1
        law.enforcement_count += 1

        # Calculate penalty
        penalty_amount = 0.0
        if law.penalty == "fine":
            # Get violator's wealth (would need world reference)
            penalty_amount = 50 * law.penalty_severity
        elif law.penalty == "imprisonment":
            duration = int(100 * law.penalty_severity)
            return {
                "success": True,
                "penalty": "imprisonment",
                "duration": duration,
                "law": law.name,
            }
        elif law.penalty == "exile":
            return {
                "success": True,
                "penalty": "exile",
                "law": law.name,
            }
        elif law.penalty == "death":
            return {
                "success": True,
                "penalty": "death",
                "law": law.name,
            }

        return {
            "success": True,
            "penalty": "fine",
            "amount": penalty_amount,
            "law": law.name,
        }

    def enact_policy(
        self,
        name: str,
        description: str,
        enacted_by: str,
        rules: list[str] | None = None,
        resource_changes: dict[str, float] | None = None,
    ) -> Policy:
        """Enact a new policy."""
        policy_id = f"policy_{len(self.policies)}"
        policy = Policy(
            policy_id=policy_id,
            name=name,
            description=description,
            rules=rules or [],
            resource_changes=resource_changes or {},
            enacted_tick=self.world.tick,
            enacted_by=enacted_by,
        )
        self._policies[policy_id] = policy

        self._political_events.append(PoliticalEvent(
            tick=self.world.tick,
            event_type="policy_enacted",
            description=f"Policy enacted: {name}",
            actors=[enacted_by],
            impact=0.4,
        ))

        return policy

    @property
    def policies(self) -> dict[str, Policy]:
        """Get all policies."""
        return self._policies

    def create_institution(
        self,
        name: str,
        institution_type: str,
        purpose: str,
        location_x: int = 0,
        location_y: int = 0,
    ) -> Institution:
        """Create a new institution."""
        institution_id = f"institution_{len(self._institutions)}"
        institution = Institution(
            institution_id=institution_id,
            name=name,
            institution_type=institution_type,
            purpose=purpose,
            location_x=location_x,
            location_y=location_y,
        )
        self._institutions[institution_id] = institution

        self._political_events.append(PoliticalEvent(
            tick=self.world.tick,
            event_type="institution_created",
            description=f"Institution founded: {name}",
            impact=0.6,
        ))

        return institution

    def declare_war(
        self,
        aggressor_id: str,
        target_id: str,
        reason: str = "",
    ) -> dict:
        """Declare war."""
        event = PoliticalEvent(
            tick=self.world.tick,
            event_type="war_declared",
            description=f"War declared: {aggressor_id} vs {target_id}. Reason: {reason}",
            actors=[aggressor_id, target_id],
            outcome={"reason": reason},
            impact=1.0,
        )
        self._political_events.append(event)

        return {
            "success": True,
            "aggressor": aggressor_id,
            "target": target_id,
            "reason": reason,
        }

    def start_revolt(
        self,
        rebel_ids: list[str],
        reason: str,
    ) -> dict:
        """Start a revolt against current authority."""
        if not self._ruler_id:
            return {"success": False, "reason": "No ruler to revolt against"}

        # Calculate revolt strength
        revolt_strength = len(rebel_ids) / 10  # More rebels = stronger

        # Increase succession tension
        self._succession_tension = min(1.0, self._succession_tension + revolt_strength)

        event = PoliticalEvent(
            tick=self.world.tick,
            event_type="revolt_started",
            description=f"Revolt against {self._ruler_id}. Reason: {reason}",
            actors=rebel_ids + [self._ruler_id],
            outcome={"revolt_strength": revolt_strength},
            impact=revolt_strength,
        )
        self._political_events.append(event)

        return {
            "success": True,
            "revolt_strength": revolt_strength,
            "current_tension": self._succession_tension,
        }

    def resolve_revolt(
        self,
        revolters: list[str],
        success: bool,
    ) -> dict:
        """Resolve a revolt."""
        if success:
            # New ruler from revolters
            new_ruler = random.choice(revolters)
            self.set_ruler(new_ruler)
            self._succession_tension = 0.0
            outcome = "revolters_won"
        else:
            # Revolters suppressed
            self._succession_tension = max(0, self._succession_tension - 0.3)
            outcome = "revolters_defeated"

        event = PoliticalEvent(
            tick=self.world.tick,
            event_type="revolt_resolved",
            description=f"Revolt resolved: {outcome}",
            actors=revolters,
            outcome={"result": outcome},
            impact=0.8,
        )
        self._political_events.append(event)

        return {"success": True, "outcome": outcome}

    def negotiate_peace(
        self,
        party_a: str,
        party_b: str,
        terms: dict,
    ) -> dict:
        """Negotiate peace between parties."""
        event = PoliticalEvent(
            tick=self.world.tick,
            event_type="peace_treaty",
            description=f"Peace negotiated between {party_a} and {party_b}",
            actors=[party_a, party_b],
            outcome=terms,
            impact=0.7,
        )
        self._political_events.append(event)

        return {"success": True, "terms": terms}

    def get_political_summary(self) -> dict:
        """Get political system summary."""
        return {
            "government_type": self._government_type.value,
            "ruler": self._ruler_id,
            "laws_count": len(self._laws),
            "authorities_count": len(self._authorities),
            "institutions_count": len(self._institutions),
            "policies_count": len(self._policies),
            "political_events_count": len(self._political_events),
            "succession_tension": self._succession_tension,
            "recent_events": [
                {"tick": e.tick, "type": e.event_type, "desc": e.description}
                for e in self._political_events[-10:]
            ],
        }


# ============================================================================
# Political Analysis
# ============================================================================

def analyze_power_distribution(world: World) -> dict:
    """Analyze power distribution in the world."""
    if not hasattr(world, '_political_system'):
        return {"status": "not initialized"}

    ps = world._political_system

    # Count authority holders by level
    level_counts = defaultdict(int)
    for auth in ps._authorities.values():
        if auth.holder_id:
            level_counts[auth.level.value] += 1

    return {
        "government_type": ps._government_type.value,
        "total_authorities": len(ps._authorities),
        "authority_by_level": dict(level_counts),
        "has_ruler": ps._ruler_id is not None,
        "revolt_risk": ps._succession_tension,
    }


def evaluate_legitimacy(world: World, ruler_id: str) -> float:
    """Evaluate ruler legitimacy (0-1)."""
    if not hasattr(world, '_political_system'):
        return 0.5

    ps = world._political_system

    # Based on how they came to power and support
    legitimacy = 0.5

    # Check if they have authority
    for auth in ps._authorities.values():
        if auth.holder_id == ruler_id:
            legitimacy += 0.2

    # Reduce for high succession tension
    legitimacy -= ps._succession_tension * 0.3

    return max(0.0, min(1.0, legitimacy))
