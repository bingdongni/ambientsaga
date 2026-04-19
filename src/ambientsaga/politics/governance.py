"""
Governance and political systems.

This module implements the political layer of the simulation:
- Government: formal political structures and leadership
- Authority: power and legitimacy
- Policy: decisions that affect agent behavior
- Law: rules enforced by institutions
- Institutions: organizations that exercise political power
- Conflict resolution: how political disputes are settled

Key design goals:
1. Political structures emerge from social interactions (bottom-up)
2. Policies affect economic, social, and cultural systems
3. Legitimacy is earned through performance (not arbitrary)
4. Multiple levels of governance can coexist
5. Political change is driven by both internal and external forces
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING, Any
from dataclasses import dataclass, field
from enum import Enum, auto
import random

from ambientsaga.config import PoliticalConfig
from ambientsaga.types import EntityID, Pos2D, new_entity_id

if TYPE_CHECKING:
    from ambientsaga.world.state import World
    from ambientsaga.agents.agent import Agent
    from ambientsaga.social.organizations import Organization


# ---------------------------------------------------------------------------
# Political Types
# ---------------------------------------------------------------------------


class AuthorityType(Enum):
    """Types of political authority."""

    NONE = auto()        # No formal authority
    TRADITIONAL = auto() # Based on custom and tradition
    CHARISMATIC = auto() # Based on personal appeal
    RATIONAL = auto()    # Based on legal-rational rules
    COERCIVE = auto()    # Based on threat of force


class PolicyType(Enum):
    """Categories of policy."""

    TAX = auto()              # Taxation policy
    TRADE = auto()            # Trade and commerce policy
    LAND = auto()             # Land distribution policy
    SECURITY = auto()        # Defense and security policy
    PUBLIC_WORKS = auto()     # Infrastructure investment
    SOCIAL_WELFARE = auto()   # Wealth redistribution
    RELIGIOUS = auto()        # Religious/cultural policy
    ENVIRONMENTAL = auto()    # Resource management
    MILITARY = auto()         # Military organization
    JUDICIAL = auto()         # Justice and dispute resolution
    MIGRATION = auto()        # Population movement
    EDUCATION = auto()        # Knowledge transfer


@dataclass
class Law:
    """
    A law is a rule that can be enforced by institutions.

    Laws have:
    - Scope: what they apply to
    - Enforcement: how violations are detected and punished
    - Legitimacy: how accepted they are by the population
    """

    law_id: str
    name: str
    description: str
    category: LawCategory
    content: str  # Natural language description

    # Enforcement
    enforcement_strength: float = 1.0  # 0-1
    punishment_severity: float = 1.0  # 0-1
    detection_rate: float = 0.5  # 0-1, probability of detection

    # Effectiveness
    compliance_rate: float = 0.8  # 0-1
    legitimacy: float = 0.7  # 0-1, how accepted
    enforcement_cost: float = 1.0  # Resources per tick to enforce

    # Temporal
    enacted_tick: int = 0
    amendment_count: int = 0

    def get_enforcement_effectiveness(self) -> float:
        """Calculate effective enforcement (0-1)."""
        return (
            self.enforcement_strength *
            self.compliance_rate *
            self.detection_rate
        )


class LawCategory(Enum):
    """Categories of law."""

    PROPERTY = auto()      # Ownership rights
    CONTRACT = auto()      # Trade agreements
    CRIMINAL = auto()     # Violence/theft
    FAMILY = auto()        # Kinship rules
    RELIGIOUS = auto()     # Spiritual/ritual
    TORT = auto()          # Wrongs and compensation
    CONSTITUTIONAL = auto()  # Fundamental rules
    ADMINISTRATIVE = auto()  # Bureaucratic rules


# ---------------------------------------------------------------------------
# Policy — government decisions
# ---------------------------------------------------------------------------


@dataclass
class Policy:
    """
    A policy is a government decision that affects agent behavior.

    Policies can be:
    - Fiscal (taxes, spending)
    - Regulatory (rules on behavior)
    - Distributive (who gets what)
    - Constituent (rules about rules)
    """

    policy_id: str
    name: str
    policy_type: PolicyType
    description: str

    # Policy parameters
    tax_rate: float = 0.0      # 0-1, for tax policies
    spending: float = 0.0       # Resource expenditure
    regulation_strength: float = 0.0  # 0-1, how strictly enforced

    # Effects on agents
    wealth_impact: float = 0.0  # Per-tick wealth change
    happiness_impact: float = 0.0
    mobility_impact: float = 0.0  # Movement restriction

    # Political properties
    proposer_id: EntityID | None = None
    enacted_tick: int = 0
    is_active: bool = False

    # Political support
    support_rate: float = 0.5  # Fraction supporting
    opposition_rate: float = 0.2  # Fraction opposing

    # Effectiveness
    implementation_cost: float = 1.0  # Resources per tick
    expected_effectiveness: float = 0.7  # Estimated outcome vs expectation

    def calculate_support(
        self,
        affected_agents: list["Agent"],
    ) -> tuple[float, float]:
        """
        Calculate support and opposition rates.

        Returns (support_rate, opposition_rate).
        """
        if not affected_agents:
            return 0.5, 0.2

        support = 0.0
        opposition = 0.0

        for agent in affected_agents:
            # Wealthy agents oppose high taxes
            if self.tax_rate > 0.1:
                if agent.wealth > 100:
                    opposition += 0.3 * min(1.0, agent.wealth / 1000)
                else:
                    support += 0.2  # Poor benefit from redistribution

            # Social welfare policies
            if self.policy_type == PolicyType.SOCIAL_WELFARE:
                if agent.wealth < 50:
                    support += 0.4
                else:
                    opposition += 0.1

            # Security policies
            if self.policy_type == PolicyType.SECURITY:
                support += 0.2  # Most agents support security

        total = len(affected_agents)
        return support / total, opposition / total


# ---------------------------------------------------------------------------
# Authority — power structures
# ---------------------------------------------------------------------------


@dataclass
class Authority:
    """
    An authority is a position of power held by an agent.

    Authority can be formal (elected/appointed) or informal (respected).
    """

    authority_id: str
    authority_type: AuthorityType
    holder_id: EntityID | None  # Agent holding this authority
    title: str  # e.g., "Chief", "Mayor", "King"

    # Jurisdiction
    scope: str  # "tribal", "village", "regional", "national"
    position: Pos2D
    radius: float = 0.0  # Geographic scope

    # Legitimacy
    legitimacy: float = 0.7  # 0-1, how accepted
    popularity: float = 0.5   # 0-1, current support

    # Power
    coercive_capacity: float = 0.0  # Ability to use force
    economic_capacity: float = 0.0  # Control over resources
    social_capacity: float = 0.0   # Social influence

    # Term
    is_elected: bool = False
    term_ticks: int = 0  # 0 = life tenure
    election_interval: int = 0
    last_election_tick: int = 0

    def get_total_power(self) -> float:
        """Calculate total political power."""
        return (
            self.legitimacy * 0.3 +
            self.popularity * 0.2 +
            self.coercive_capacity * 0.3 +
            self.economic_capacity * 0.1 +
            self.social_capacity * 0.1
        )

    def update_legitimacy(
        self,
        performance_score: float,
        tick: int,
    ) -> None:
        """
        Update legitimacy based on performance.

        Performance score: -1 (disastrous) to +1 (excellent)
        """
        # Legitimacy adjusts slowly toward performance
        delta = (performance_score - self.legitimacy) * 0.01
        self.legitimacy = max(0.0, min(1.0, self.legitimacy + delta))

    def check_term_limit(self, tick: int) -> bool:
        """Check if term limit has been reached."""
        if not self.is_elected or self.term_ticks == 0:
            return False
        return (tick - self.last_election_tick) >= self.term_ticks


# ---------------------------------------------------------------------------
# Institution — organizations that exercise power
# ---------------------------------------------------------------------------


@dataclass
class Institution:
    """
    An institution is a stable organization that exercises political power.

    Institutions persist across individual leaders and provide:
    - Rules and procedures
    - Role definitions
    - Enforcement mechanisms
    - Memory and continuity
    """

    institution_id: str
    name: str
    institution_type: InstitutionType
    position: Pos2D

    # Scope
    jurisdiction: str = "local"  # local, regional, national
    member_count: int = 0
    max_members: int = 100

    # Structure
    authority_ids: list[str] = field(default_factory=list)
    parent_institution_id: str | None = None

    # Resources
    treasury: float = 0.0
    land_holdings: float = 0.0  # sq units

    # Effectiveness
    legitimacy: float = 0.6
    efficiency: float = 0.7  # 0-1, how well it functions

    # Active laws and policies
    law_ids: list[str] = field(default_factory=list)
    policy_ids: list[str] = field(default_factory=list)

    # Creation
    founded_tick: int = 0
    founder_id: EntityID | None = None

    def get_coercive_power(self) -> float:
        """Calculate total coercive power."""
        return self.efficiency * len(self.authority_ids) * 0.1

    def assess_effectiveness(self, tick: int) -> float:
        """
        Assess institutional effectiveness.

        Returns a score from -1 to +1.
        """
        if self.founded_tick == 0:
            return 0.0

        age = max(1, tick - self.founded_tick)

        # New institutions start uncertain
        age_factor = min(1.0, age / 720)  # Mature after 2 years

        # Efficiency and legitimacy combined
        return (self.efficiency * 0.5 + self.legitimacy * 0.5) * age_factor - 0.2


class InstitutionType(Enum):
    """Types of political institutions."""

    TRIBE = auto()           #kinship-based
    COUNCIL = auto()         #deliberative body
    CHIEFTAIN = auto()       #single leader
    KINGDOM = auto()         #monarchical
    REPUBLIC = auto()         #representative
    DEMOCRACY = auto()        #participatory
    THEOCRACY = auto()        #religious authority
    OLIGARCHY = auto()        #rule by few
    BUREAUCRACY = auto()      #administrative
    MILITARY = auto()         #armed forces
    TRIBUNAL = auto()         #judicial
    COUNCIL_OF_ELDERS = auto()  #senior advisors
    GUILD = auto()            #economic association
    CONFEDERATION = auto()    #league of polities


# ---------------------------------------------------------------------------
# Government — the ruling structure
# ---------------------------------------------------------------------------


@dataclass
class Government:
    """
    A government is a specific political regime in power.

    Governments define:
    - Who rules (authority structure)
    - How they rule (laws and policies)
    - What they prioritize (policy agenda)
    """

    government_id: str
    name: str
    institution_id: str  # The institution governing

    # Authority structure
    authority_type: AuthorityType = AuthorityType.TRADITIONAL
    leader_id: EntityID | None = None
    council_ids: list[EntityID] = field(default_factory=list)

    # Active policies
    active_policy_ids: list[str] = field(default_factory=list)
    proposed_policy_ids: list[str] = field(default_factory=list)

    # Active laws
    active_law_ids: list[str] = field(default_factory=list)

    # Resources
    treasury: float = 0.0
    tax_rate: float = 0.1
    public_spending: float = 0.0

    # Political support
    popular_support: float = 0.6  # 0-1
    elite_support: float = 0.5    # 0-1
    institutional_support: float = 0.7

    # Stability
    stability: float = 0.7  # 0-1, how likely to survive
    tenure_ticks: int = 0
    coups_attempted: int = 0
    coups_survived: int = 0

    # Performance
    economic_performance: float = 0.5  # -1 to +1
    social_performance: float = 0.5
    military_performance: float = 0.5

    def get_overall_performance(self) -> float:
        """Calculate overall government performance."""
        return (
            self.economic_performance * 0.4 +
            self.social_performance * 0.4 +
            self.military_performance * 0.2
        )

    def get_survival_probability(self) -> float:
        """Estimate probability of surviving the next tick."""
        base = self.stability
        base *= (1.0 + self.popular_support * 0.2)
        base *= (1.0 + self.institutional_support * 0.2)
        base *= (1.0 + self.tenure_ticks / 1000)  # Older = more stable
        return min(0.99, base)

    def update_from_performance(self, tick: int) -> None:
        """Update government state based on performance."""
        perf = self.get_overall_performance()

        # Support adjusts toward performance
        self.popular_support = self.popular_support * 0.99 + perf * 0.01
        self.popular_support = max(0.0, min(1.0, self.popular_support))

        # Stability adjusts
        if perf < -0.3:
            self.stability *= 0.95  # Poor performance destabilizes
        elif perf > 0.3:
            self.stability = min(1.0, self.stability * 1.01)

        # Tenure increases
        self.tenure_ticks += 1


# ---------------------------------------------------------------------------
# PoliticalSystem — the main political manager
# ---------------------------------------------------------------------------


class PoliticalSystem:
    """
    Manages all political structures in the world.

    Key responsibilities:
    - Create and manage governments
    - Handle policy creation and enactment
    - Process elections and succession
    - Manage institutional evolution
    - Resolve political conflicts
    - Track political events

    Political structures emerge from:
    - Population density (more people → more complex government)
    - Resource surplus (surplus → stratification)
    - External threats (threats → centralization)
    - Cultural values (values → authority types)
    """

    def __init__(
        self, config: PoliticalConfig, world: "World", seed: int = 42
    ) -> None:
        self.config = config
        self.world = world
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Governments
        self._governments: dict[str, Government] = {}
        self._active_government_id: str | None = None

        # Institutions
        self._institutions: dict[str, Institution] = {}
        self._regional_institutions: dict[str, list[str]] = {}  # region_id -> institution_ids

        # Authorities
        self._authorities: dict[str, Authority] = {}

        # Laws
        self._laws: dict[str, Law] = {}
        self._build_fundamental_laws()

        # Policies
        self._policies: dict[str, Policy] = {}
        self._build_standard_policies()

        # Political events
        self._elections: list[dict] = []
        self._reforms: list[dict] = []
        self._conflicts: list[dict] = []

        # Statistics
        self._total_elections = 0
        self._total_coups = 0
        self._total_reforms = 0

    def _build_fundamental_laws(self) -> None:
        """Create the fundamental legal framework."""
        fundamental_laws = [
            Law(
                law_id="property_right",
                name="Property Rights",
                description="Individuals have rights to own and use property",
                category=LawCategory.PROPERTY,
                content="Individuals may own property and resources",
                enacted_tick=0,
            ),
            Law(
                law_id="no_violence",
                name="Prohibition of Unprovoked Violence",
                description="Unprovoked violence against others is prohibited",
                category=LawCategory.CRIMINAL,
                content="Violence against others without justification is prohibited",
                enacted_tick=0,
                enforcement_strength=0.7,
                punishment_severity=0.6,
                detection_rate=0.4,
            ),
            Law(
                law_id="contract_enforcement",
                name="Contract Enforcement",
                description="Agreements between parties must be honored",
                category=LawCategory.CONTRACT,
                content="Trade agreements and contracts are binding",
                enacted_tick=0,
                enforcement_strength=0.5,
                punishment_severity=0.4,
            ),
            Law(
                law_id="kinship_rights",
                name="Kinship Rights",
                description="Family and kinship ties are protected",
                category=LawCategory.FAMILY,
                content="Family relationships grant mutual obligations",
                enacted_tick=0,
                enforcement_strength=0.6,
            ),
        ]

        for law in fundamental_laws:
            self._laws[law.law_id] = law

    def _build_standard_policies(self) -> None:
        """Create standard policy templates."""
        standard_policies = [
            Policy(
                policy_id="flat_tax",
                name="Flat Tax",
                policy_type=PolicyType.TAX,
                description="A uniform tax rate on all income",
                tax_rate=0.1,
            ),
            Policy(
                policy_id="progressive_tax",
                name="Progressive Tax",
                policy_type=PolicyType.TAX,
                description="Higher rates for higher incomes",
                tax_rate=0.15,
            ),
            Policy(
                policy_id="free_trade",
                name="Free Trade",
                policy_type=PolicyType.TRADE,
                description="No restrictions on trade",
                regulation_strength=0.0,
            ),
            Policy(
                policy_id="trade_restrictions",
                name="Trade Restrictions",
                policy_type=PolicyType.TRADE,
                description="Limitations on trade with outsiders",
                regulation_strength=0.5,
            ),
            Policy(
                policy_id="security_policy",
                name="Public Security",
                policy_type=PolicyType.SECURITY,
                description="Maintain internal order and safety",
                spending=5.0,
                implementation_cost=2.0,
            ),
            Policy(
                policy_id="public_works",
                name="Public Works",
                policy_type=PolicyType.PUBLIC_WORKS,
                description="Invest in infrastructure",
                spending=10.0,
                implementation_cost=3.0,
            ),
            Policy(
                policy_id="welfare",
                name="Social Welfare",
                policy_type=PolicyType.SOCIAL_WELFARE,
                description="Redistribute wealth to the poor",
                spending=5.0,
                wealth_impact=1.0,
                happiness_impact=0.1,
                implementation_cost=1.5,
            ),
            Policy(
                policy_id="open_borders",
                name="Open Borders",
                policy_type=PolicyType.MIGRATION,
                description="Free movement of people",
                mobility_impact=1.0,
                regulation_strength=0.0,
            ),
        ]

        for policy in standard_policies:
            self._policies[policy.policy_id] = policy

    # -------------------------------------------------------------------------
    # Institution Management
    # -------------------------------------------------------------------------

    def create_institution(
        self,
        name: str,
        institution_type: InstitutionType,
        position: Pos2D,
        founder_id: EntityID | None = None,
        jurisdiction: str = "local",
    ) -> Institution:
        """Create a new political institution."""
        inst = Institution(
            institution_id=new_entity_id(),
            name=name,
            institution_type=institution_type,
            position=position,
            jurisdiction=jurisdiction,
            founded_tick=self.world.tick,
            founder_id=founder_id,
        )

        self._institutions[inst.institution_id] = inst
        return inst

    def create_government(
        self,
        name: str,
        institution_id: str,
        authority_type: AuthorityType,
        leader_id: EntityID | None = None,
    ) -> Government:
        """Create a new government."""
        govt = Government(
            government_id=new_entity_id(),
            name=name,
            institution_id=institution_id,
            authority_type=authority_type,
            leader_id=leader_id,
        )

        self._governments[govt.government_id] = govt

        if self._active_government_id is None:
            self._active_government_id = govt.government_id

        return govt

    def create_authority(
        self,
        authority_type: AuthorityType,
        holder_id: EntityID | None,
        title: str,
        position: Pos2D,
        scope: str = "local",
    ) -> Authority:
        """Create a new authority position."""
        auth = Authority(
            authority_id=new_entity_id(),
            authority_type=authority_type,
            holder_id=holder_id,
            title=title,
            position=position,
            scope=scope,
        )

        self._authorities[auth.authority_id] = auth
        return auth

    def enact_policy(
        self, policy_id: str, tick: int, proposer_id: EntityID | None = None
    ) -> bool:
        """Enact a policy into law."""
        policy = self._policies.get(policy_id)
        if policy is None:
            return False

        if policy.is_active:
            return False

        policy.is_active = True
        policy.enacted_tick = tick
        policy.proposer_id = proposer_id

        # If there's an active government, add it there
        if self._active_government_id:
            govt = self._governments[self._active_government_id]
            if policy_id not in govt.active_policy_ids:
                govt.active_policy_ids.append(policy_id)

        return True

    def repeal_policy(self, policy_id: str) -> bool:
        """Repeal an active policy."""
        policy = self._policies.get(policy_id)
        if policy is None:
            return False

        policy.is_active = False

        if self._active_government_id:
            govt = self._governments[self._active_government_id]
            if policy_id in govt.active_policy_ids:
                govt.active_policy_ids.remove(policy_id)

        return True

    def enact_law(self, law_id: str, tick: int) -> bool:
        """Enact a law."""
        law = self._laws.get(law_id)
        if law is None:
            return False

        law.enacted_tick = tick

        if self._active_government_id:
            govt = self._governments[self._active_government_id]
            if law_id not in govt.active_law_ids:
                govt.active_law_ids.append(law_id)

        return True

    def propose_reform(
        self,
        name: str,
        proposer_id: EntityID,
        target_policy_id: str | None = None,
        target_law_id: str | None = None,
    ) -> dict:
        """Propose a political reform."""
        reform = {
            "reform_id": new_entity_id(),
            "name": name,
            "proposer_id": proposer_id,
            "target_policy_id": target_policy_id,
            "target_law_id": target_law_id,
            "proposed_tick": self.world.tick,
            "status": "proposed",
            "supporters": [proposer_id],
            "opponents": [],
        }

        self._reforms.append(reform)
        return reform

    # -------------------------------------------------------------------------
    # Political Dynamics
    # -------------------------------------------------------------------------

    def hold_election(
        self,
        government_id: str,
        candidates: list[EntityID],
        tick: int,
    ) -> EntityID | None:
        """Hold an election for government leadership."""
        govt = self._governments.get(government_id)
        if govt is None or not candidates:
            return None

        # Simple voting: weighted by agent wealth (wealthier = more votes)
        votes: dict[EntityID, float] = {c: 0.0 for c in candidates}
        for candidate_id in candidates:
            agent = self.world.get_agent(candidate_id)
            if agent and agent.is_alive:
                # Wealth-based voting weight
                weight = max(1.0, agent.wealth ** 0.3)
                # Random component for unpredictability
                votes[candidate_id] = weight * self._rng.uniform(0.5, 1.5)

        # Winner
        winner_id = max(votes, key=votes.get)
        old_leader = govt.leader_id
        govt.leader_id = winner_id
        govt.tenure_ticks = 0
        govt.last_election_tick = tick

        self._elections.append({
            "tick": tick,
            "government_id": government_id,
            "winner_id": winner_id,
            "candidates": candidates,
            "votes": votes,
            "previous_leader": old_leader,
        })

        self._total_elections += 1
        return winner_id

    def attempt_coup(
        self,
        challenger_id: EntityID,
        target_government_id: str,
        tick: int,
    ) -> bool:
        """
        Attempt a coup against a government.

        Returns True if successful.
        """
        govt = self._governments.get(target_government_id)
        if govt is None:
            return False

        challenger = self.world.get_agent(challenger_id)
        if challenger is None:
            return False

        govt.coups_attempted += 1

        # Coup success probability
        challenger_strength = (
            challenger.attributes.strength * 0.3 +
            challenger.skills.get("combat", 0.0) * 0.3 +
            challenger.wealth / 1000.0 * 0.2 +
            self._rng.uniform(0, 1) * 0.2
        )

        govt_strength = (
            govt.stability * 0.4 +
            govt.popular_support * 0.3 +
            govt.institutional_support * 0.3
        )

        # Popular support makes coups harder
        success_prob = challenger_strength / max(0.1, govt_strength) * 0.3
        success_prob = min(0.8, success_prob)

        if self._rng.random() < success_prob:
            # Successful coup
            govt.leader_id = challenger_id
            govt.tenure_ticks = 0
            govt.stability *= 0.7  # Destabilizing
            govt.popular_support *= 0.8

            self._conflicts.append({
                "type": "coup",
                "tick": tick,
                "challenger_id": challenger_id,
                "previous_leader": govt.leader_id,
                "outcome": "success",
            })
            self._total_coups += 1
            return True

        else:
            # Failed coup
            self._conflicts.append({
                "type": "coup",
                "tick": tick,
                "challenger_id": challenger_id,
                "previous_leader": govt.leader_id,
                "outcome": "failed",
            })
            return False

    def check_reforms(self, tick: int) -> int:
        """Check and resolve pending reforms."""
        resolved = 0

        for reform in self._reforms:
            if reform["status"] != "proposed":
                continue

            age = tick - reform["proposed_tick"]
            if age < 100:  # Minimum deliberation period
                continue

            # Count support
            supporters = len(reform["supporters"])
            opponents = len(reform["opponents"])

            if supporters > opponents * 2 and supporters >= 5:
                # Reform passes
                reform["status"] = "enacted"
                reform["enacted_tick"] = tick

                if reform["target_policy_id"]:
                    self.enact_policy(reform["target_policy_id"], tick)

                self._total_reforms += 1
                resolved += 1

            elif opponents > supporters * 2:
                # Reform rejected
                reform["status"] = "rejected"
                resolved += 1

        return resolved

    def check_elections(self, tick: int) -> int:
        """Check for scheduled elections."""
        triggered = 0

        for govt in self._governments.values():
            if not govt.authority_type == AuthorityType.RATIONAL:
                continue

            if govt.election_interval > 0:
                ticks_since_election = tick - govt.last_election_tick
                if ticks_since_election >= govt.election_interval:
                    # Trigger election
                    candidates = [
                        agent.entity_id
                        for agent in self.world.get_all_agents()
                        if agent.is_alive and agent.wealth > 20
                    ]
                    if candidates:
                        self.hold_election(govt.government_id, candidates, tick)
                        triggered += 1

        return triggered

    # -------------------------------------------------------------------------
    # Policy Effects
    # -------------------------------------------------------------------------

    def apply_policies(self, tick: int) -> None:
        """Apply active policy effects to the world."""
        if self._active_government_id is None:
            return

        govt = self._governments[self._active_government_id]

        # Collect taxes
        total_tax = 0.0
        for agent in self.world.get_all_agents():
            if not agent.is_alive:
                continue

            if govt.tax_rate > 0:
                tax = agent.wealth * govt.tax_rate * 0.001
                agent.wealth -= tax
                total_tax += tax

        govt.treasury += total_tax

        # Apply welfare spending
        welfare_active = any(
            self._policies.get(pid, None) and self._policies[pid].policy_type == PolicyType.SOCIAL_WELFARE
            for pid in govt.active_policy_ids
        )

        if welfare_active:
            poor_agents = [
                a for a in self.world.get_all_agents()
                if a.is_alive and a.wealth < 20
            ]
            if poor_agents and govt.treasury > 0:
                per_person = min(1.0, govt.treasury / max(1, len(poor_agents)))
                for agent in poor_agents:
                    agent.wealth += per_person * 0.5
                govt.treasury -= per_person * len(poor_agents) * 0.5

    # -------------------------------------------------------------------------
    # Political Evolution
    # -------------------------------------------------------------------------

    def check_political_emergence(self, tick: int) -> Institution | None:
        """
        Check if conditions are right for new political institutions.

        Political institutions emerge when:
        - Population exceeds threshold
        - Resource surplus exists
        - Social organization exists
        """
        agents = self.world.get_all_agents()
        alive = [a for a in agents if a.is_alive]

        if len(alive) < 50:
            return None  # Too few people

        # Check if population is dense enough
        if len(alive) < 500:
            return None

        # Check if there's an existing government
        if self._active_government_id is not None:
            return None

        # Create a tribal government
        x = sum(a.position.x for a in alive) / len(alive)
        y = sum(a.position.y for a in alive) / len(alive)
        center_pos = Pos2D(int(x), int(y))

        inst = self.create_institution(
            name="Tribal Council",
            institution_type=InstitutionType.TRIBE,
            position=center_pos,
            jurisdiction="regional",
        )

        govt = self.create_government(
            name="Tribal Government",
            institution_id=inst.institution_id,
            authority_type=AuthorityType.TRADITIONAL,
        )

        # Create a chieftain authority
        leader = max(alive, key=lambda a: a.wealth + a.attributes.charisma * 10)
        self.create_authority(
            authority_type=AuthorityType.TRADITIONAL,
            holder_id=leader.entity_id,
            title="Chief",
            position=leader.position,
            scope="regional",
        )

        return inst

    def update(self, tick: int) -> None:
        """Update political systems for the tick."""
        # Update all governments
        for govt in self._governments.values():
            govt.update_from_performance(tick)

        # Apply policy effects
        self.apply_policies(tick)

        # Check for scheduled elections
        self.check_elections(tick)

        # Check reforms
        self.check_reforms(tick)

        # Check for political emergence
        self.check_political_emergence(tick)

        # Check authority term limits
        for auth in list(self._authorities.values()):
            if auth.check_term_limit(tick):
                auth.holder_id = None  # Vacant position

    def get_stats(self) -> dict[str, Any]:
        """Get political statistics."""
        return {
            "total_governments": len(self._governments),
            "active_government": self._active_government_id,
            "total_institutions": len(self._institutions),
            "total_authorities": len(self._authorities),
            "total_laws": len(self._laws),
            "active_laws": sum(
                1 for l in self._laws.values() if l.enacted_tick > 0
            ),
            "total_policies": len(self._policies),
            "active_policies": sum(
                1 for p in self._policies.values() if p.is_active
            ),
            "total_elections": self._total_elections,
            "total_coups": self._total_coups,
            "total_reforms": self._total_reforms,
            "pending_reforms": sum(
                1 for r in self._reforms if r["status"] == "proposed"
            ),
            "coup_success_rate": (
                sum(1 for c in self._conflicts if c["outcome"] == "success") /
                max(1, self._total_coups)
            ),
        }
