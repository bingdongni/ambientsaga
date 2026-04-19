"""
Social Network System - Relationships, reputation, and social dynamics.

Features:
- Multi-dimensional relationships: trust, affiliation, debt, respect
- Reputation tracking: what agents are known for
- Social network analysis: centrality, clustering, influence
- Group dynamics: coalition formation, collective action
- Conflict and cooperation: dispute resolution, alliance building

Academic value:
- Social network topology evolution
- Reputation formation mechanisms
- Emergence of hierarchy and leadership
- Collective behavior patterns

Engineering value:
- Efficient relationship queries
- Incremental network updates
- Scalable social computation
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
# Social Types
# ============================================================================

class RelationshipType(Enum):
    """Types of relationships."""
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    BEST_FRIEND = "best_friend"
    ROMANTIC = "romantic"
    FAMILY = "family"
    RIVAL = "rival"
    ENEMY = "enemy"
    MENTOR = "mentor"
    STUDENT = "student"
    TRADE_PARTNER = "trade_partner"
    COWORKER = "coworker"
    COMMANDER = "commander"
    FOLLOWER = "follower"


class ReputationType(Enum):
    """What an agent can be known for."""
    SKILLFUL = "skillful"          # Good at something
    KIND = "kind"                   # Generous, helpful
    HONEST = "honest"               # Truthful, trustworthy
    FUNNY = "funny"                 # Entertaining
    WISE = "wise"                   # Knowledgeable
    STRONG = "strong"               # Physically powerful
    WEALTHY = "wealthy"             # Has resources
    BEAUTIFUL = "beautiful"        # Attractive
    CREATIVE = "creative"           # Artistic
    LEADERS = "leader"              # Good leader
    DEVOUT = "devout"               # Religious
    MYSTERIOUS = "mysterious"       # Hard to read
    DANGEROUS = "dangerous"         # Threatening
    CRAFTY = "crafty"               # Cunning, clever
    LAZY = "lazy"                   # Unmotivated
    CRUEL = "cruel"                 # Mean-spirited
    STUPID = "stupid"               # Unintelligent
    UNRELIABLE = "unreliable"       # Breaks promises
    DRUNKARD = "drunkard"           # Addicted to alcohol
    THIEF = "thief"                 # Steals things


class SocialAction(Enum):
    """Actions that affect relationships."""
    GIVE_GIFT = "give_gift"
    HELP = "help"
    RECEIVE_HELP = "receive_help"
    SHARE_FOOD = "share_food"
    HEAL = "heal"
    TRADE_FAIR = "trade_fair"
    TELL_SECRET = "tell_secret"
    COMPLIMENT = "compliment"
    INVITE = "invite"
    PRAISE = "praise"
    DEFEND = "defend"
    TRUST = "trust"

    # Negative actions
    INSULT = "insult"
    IGNORE = "ignore"
    CHEAT = "cheat"
    STEAL = "steal"
    LIE = "lie"
    BETRAY = "betray"
    ATTACK = "attack"
    CURSE = "curse"
    SPREAD_RUMOR = "spread_rumor"


@dataclass
class Relationship:
    """
    Multi-dimensional relationship between two agents.
    """
    agent_a: str
    agent_b: str

    # Core dimensions
    trust: float = 0.0        # -1 to 1, belief in reliability
    affiliation: float = 0.0  # -1 to 1, similarity/connection
    respect: float = 0.0     # -1 to 1, perceived value
    familiarity: float = 0.0  # 0 to 1, how well known

    # Derived relationship type
    relationship_type: RelationshipType = RelationshipType.STRANGER

    # Social debt (positive = owes, negative = owed)
    debt: float = 0.0

    # Interaction history
    interaction_count: int = 0
    last_interaction_tick: int = 0
    positive_interactions: int = 0
    negative_interactions: int = 0

    # Memory of specific interactions
    memorable_events: list[str] = field(default_factory=list)

    def compute_type(self) -> RelationshipType:
        """Determine the relationship type from dimensions."""
        if self.trust > 0.7 and self.affiliation > 0.5:
            if self.familiarity > 0.8:
                return RelationshipType.BEST_FRIEND
            return RelationshipType.FRIEND
        elif self.trust < -0.5:
            return RelationshipType.ENEMY
        elif self.trust < -0.2:
            return RelationshipType.RIVAL
        elif self.affiliation > 0.3 and self.familiarity > 0.3:
            return RelationshipType.ACQUAINTANCE
        return RelationshipType.STRANGER

    def update_type(self) -> None:
        """Update relationship type."""
        self.relationship_type = self.compute_type()

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "trust": self.trust,
            "affiliation": self.affiliation,
            "respect": self.respect,
            "familiarity": self.familiarity,
            "debt": self.debt,
            "type": self.relationship_type.value,
            "interactions": self.interaction_count,
        }


@dataclass
class Reputation:
    """Agent's reputation in the community."""
    agent_id: str

    # Reputation tags (0-1 strength)
    tags: dict[ReputationType, float] = field(default_factory=dict)

    # Aggregate scores
    overall_standing: float = 0.5  # 0-1, general reputation
    trustworthiness: float = 0.5   # 0-1, can be trusted
    usefulness: float = 0.5         # 0-1, has valuable skills
    danger_level: float = 0.0       # 0-1, threat to others

    # Rumors and stories about this agent
    rumors: list[dict] = field(default_factory=list)

    # Who knows this reputation
    known_by: set[str] = field(default_factory=set)

    def add_tag(self, tag: ReputationType, strength: float) -> None:
        """Add or update a reputation tag."""
        current = self.tags.get(tag, 0.0)
        self.tags[tag] = max(current, strength)

        # Update aggregates
        self._recompute()

    def _recompute(self) -> None:
        """Recompute aggregate scores."""
        # Overall = weighted average of positive tags
        positive = sum(
            v for t, v in self.tags.items()
            if t not in (ReputationType.DANGEROUS, ReputationType.CRUEL,
                        ReputationType.UNRELIABLE, ReputationType.THIEF)
        )
        if self.tags:
            self.overall_standing = positive / len(self.tags)

        # Trustworthiness based on honest/kind/unreliable tags
        honest = self.tags.get(ReputationType.HONEST, 0.5)
        kind = self.tags.get(ReputationType.KIND, 0.5)
        unreliable = self.tags.get(ReputationType.UNRELIABLE, 0.0)
        self.trustworthiness = (honest + kind + (1 - unreliable)) / 3

        # Usefulness based on skills and wealth
        skillful = self.tags.get(ReputationType.SKILLFUL, 0.5)
        wise = self.tags.get(ReputationType.WISE, 0.5)
        wealthy = self.tags.get(ReputationType.WEALTHY, 0.0)
        self.usefulness = (skillful + wise + wealthy * 0.5) / 2.5

        # Danger based on negative tags
        dangerous = self.tags.get(ReputationType.DANGEROUS, 0.0)
        cruel = self.tags.get(ReputationType.CRUEL, 0.0)
        thief = self.tags.get(ReputationType.THIEF, 0.0)
        self.danger_level = min(1.0, dangerous + cruel * 0.7 + thief * 0.5)


@dataclass
class SocialEvent:
    """A social event that affects relationships."""
    tick: int
    action: SocialAction
    actor_id: str
    target_id: str
    context: str = ""
    impact_trust: float = 0.0
    impact_affiliation: float = 0.0
    witnessed_by: list[str] = field(default_factory=list)


# ============================================================================
# Social Network Manager
# ============================================================================

class SocialNetwork:
    """
    Manages all social relationships and reputation.

    Features:
    - Efficient relationship queries
    - Social action processing
    - Reputation updates
    - Network analysis
    """

    def __init__(self, world: World):
        self.world = world
        self._relationships: dict[tuple[str, str], Relationship] = {}
        self._reputations: dict[str, Reputation] = {}
        self._social_events: list[SocialEvent] = []
        self._social_graph: dict[str, set[str]] = defaultdict(set)

        # Action impact mappings
        self._action_impacts = self._build_action_impacts()

    def _build_action_impacts(self) -> dict[SocialAction, tuple[float, float]]:
        """Build mapping of social actions to relationship impacts."""
        return {
            # Positive actions
            SocialAction.GIVE_GIFT: (0.15, 0.10),
            SocialAction.HELP: (0.20, 0.15),
            SocialAction.SHARE_FOOD: (0.15, 0.20),
            SocialAction.HEAL: (0.25, 0.10),
            SocialAction.TRADE_FAIR: (0.10, 0.05),
            SocialAction.TELL_SECRET: (0.20, 0.15),
            SocialAction.COMPLIMENT: (0.08, 0.10),
            SocialAction.INVITE: (0.10, 0.10),
            SocialAction.PRAISE: (0.12, 0.08),
            SocialAction.DEFEND: (0.25, 0.15),
            SocialAction.TRUST: (0.15, 0.05),

            # Negative actions
            SocialAction.INSULT: (-0.15, -0.10),
            SocialAction.IGNORE: (-0.05, -0.08),
            SocialAction.CHEAT: (-0.30, -0.20),
            SocialAction.STEAL: (-0.40, -0.25),
            SocialAction.LIE: (-0.25, -0.15),
            SocialAction.BETRAY: (-0.50, -0.30),
            SocialAction.ATTACK: (-0.60, -0.30),
            SocialAction.CURSE: (-0.15, -0.10),
            SocialAction.SPREAD_RUMOR: (-0.20, -0.15),
        }

    def get_relationship(
        self,
        agent_a: str,
        agent_b: str,
    ) -> Relationship | None:
        """Get relationship between two agents."""
        key = (min(agent_a, agent_b), max(agent_a, agent_b))
        return self._relationships.get(key)

    def get_or_create_relationship(
        self,
        agent_a: str,
        agent_b: str,
    ) -> Relationship:
        """Get or create a relationship."""
        key = (min(agent_a, agent_b), max(agent_a, agent_b))
        if key not in self._relationships:
            self._relationships[key] = Relationship(
                agent_a=key[0],
                agent_b=key[1],
            )
            self._social_graph[key[0]].add(key[1])
            self._social_graph[key[1]].add(key[0])
        return self._relationships[key]

    def perform_action(
        self,
        actor_id: str,
        action: SocialAction,
        target_id: str,
        context: str = "",
    ) -> None:
        """Process a social action."""
        rel = self.get_or_create_relationship(actor_id, target_id)

        # Get impacts
        impact = self._action_impacts.get(action, (0.0, 0.0))
        trust_impact, affil_impact = impact

        # Apply impacts (with diminishing returns)
        diminishing = max(0.1, 1.0 - rel.interaction_count * 0.01)
        rel.trust += trust_impact * diminishing
        rel.affiliation += affil_impact * diminishing

        # Clamp values
        rel.trust = max(-1.0, min(1.0, rel.trust))
        rel.affiliation = max(-1.0, min(1.0, rel.affiliation))

        # Update interaction count
        rel.interaction_count += 1
        rel.last_interaction_tick = self.world.tick

        # Track positive/negative
        if trust_impact > 0:
            rel.positive_interactions += 1
        elif trust_impact < 0:
            rel.negative_interactions += 1

        # Update relationship type
        rel.update_type()

        # Add memorable event if impact is strong
        if abs(trust_impact) > 0.1:
            rel.memorable_events.append(
                f"[{self.world.tick}] {actor_id} {action.value} {target_id}"
            )
            if len(rel.memorable_events) > 10:
                rel.memorable_events = rel.memorable_events[-10:]

        # Social debt tracking
        if action == SocialAction.GIVE_GIFT:
            rel.debt += 0.3
        elif action == SocialAction.HELP:
            rel.debt += 0.5
        elif action == SocialAction.HEAL:
            rel.debt += 0.8
        elif action == SocialAction.RECEIVE_HELP:  # If target was helped
            rel.debt -= 0.3

        # Record event
        event = SocialEvent(
            tick=self.world.tick,
            action=action,
            actor_id=actor_id,
            target_id=target_id,
            context=context,
            impact_trust=trust_impact,
            impact_affiliation=affil_impact,
        )
        self._social_events.append(event)

    def get_reputation(self, agent_id: str) -> Reputation:
        """Get or create reputation for an agent."""
        if agent_id not in self._reputations:
            self._reputations[agent_id] = Reputation(agent_id=agent_id)
        return self._reputations[agent_id]

    def update_reputation(
        self,
        agent_id: str,
        tag: ReputationType,
        strength: float,
        witnessed_by: list[str] | None = None,
    ) -> None:
        """Update an agent's reputation."""
        rep = self.get_reputation(agent_id)
        rep.add_tag(tag, strength)

        # Update who knows about this
        if witnessed_by:
            rep.known_by.update(witnessed_by)

    def get_agent_relationships(
        self,
        agent_id: str,
        min_trust: float = -1.0,
        relationship_type: RelationshipType | None = None,
    ) -> list[Relationship]:
        """Get all relationships for an agent."""
        results = []
        for rel in self._relationships.values():
            if rel.agent_a == agent_id or rel.agent_b == agent_id:
                if rel.trust >= min_trust:
                    if relationship_type is None or rel.relationship_type == relationship_type:
                        results.append(rel)
        return results

    def get_friends(
        self,
        agent_id: str,
        min_trust: float = 0.3,
    ) -> list[str]:
        """Get list of friends (trusted agents)."""
        friends = []
        for rel in self.get_agent_relationships(agent_id, min_trust=min_trust):
            if rel.relationship_type in (RelationshipType.FRIEND, RelationshipType.BEST_FRIEND):
                friend_id = rel.agent_b if rel.agent_a == agent_id else rel.agent_a
                friends.append(friend_id)
        return friends

    def get_allies(
        self,
        agent_id: str,
    ) -> list[str]:
        """Get allies (high trust + positive affiliation)."""
        allies = []
        for rel in self.get_agent_relationships(agent_id, min_trust=0.4):
            if rel.affiliation > 0.3:
                ally_id = rel.agent_b if rel.agent_a == agent_id else rel.agent_a
                allies.append(ally_id)
        return allies

    def get_rivals(
        self,
        agent_id: str,
    ) -> list[str]:
        """Get rivals and enemies."""
        rivals = []
        for rel in self.get_agent_relationships(agent_id, min_trust=-1.0):
            if rel.trust < -0.2:
                rival_id = rel.agent_b if rel.agent_a == agent_id else rel.agent_a
                rivals.append(rival_id)
        return rivals

    def get_network_stats(self, agent_id: str) -> dict:
        """Get network statistics for an agent."""
        friends = self.get_friends(agent_id)
        allies = self.get_allies(agent_id)
        rivals = self.get_rivals(agent_id)

        # Calculate centrality (simple degree centrality)
        degree = len(self._social_graph.get(agent_id, set()))

        # Clustering coefficient (friends of friends who are also friends)
        neighbors = self._social_graph.get(agent_id, set())
        if len(neighbors) > 1:
            connections = sum(
                1 for n1 in neighbors
                for n2 in neighbors
                if n1 != n2 and n2 in self._social_graph.get(n1, set())
            )
            possible = len(neighbors) * (len(neighbors) - 1)
            clustering = connections / max(1, possible)
        else:
            clustering = 0.0

        return {
            "degree": degree,
            "friends": len(friends),
            "allies": len(allies),
            "rivals": len(rivals),
            "clustering": clustering,
            "trust_sum": sum(
                self.get_relationship(agent_id, n).trust
                for n in neighbors if self.get_relationship(agent_id, n)
            ),
        }

    def process_encounter(
        self,
        agent_a_id: str,
        agent_b_id: str,
        context: str = "met",
    ) -> None:
        """Process an encounter between two agents."""
        rel = self.get_or_create_relationship(agent_a_id, agent_b_id)

        # Increase familiarity on encounter
        rel.familiarity = min(1.0, rel.familiarity + 0.05)

        # Small random trust drift (can go up or down slightly)
        rng = random.Random(agent_a_id + agent_b_id + str(self.world.tick))
        drift = rng.uniform(-0.02, 0.02)
        rel.trust = max(-1.0, min(1.0, rel.trust + drift))

        rel.update_type()

    def form_group(
        self,
        leader_id: str,
        member_ids: list[str],
        group_type: str = "party",
    ) -> dict:
        """Form a group with a leader."""
        # Establish leader-follower relationships
        for member_id in member_ids:
            if member_id == leader_id:
                continue

            rel = self.get_or_create_relationship(leader_id, member_id)
            rel.relationship_type = RelationshipType.COMMANDER
            rel.respect = 0.5
            rel.trust = max(rel.trust, 0.3)

            # Reverse relationship
            rel_rev = self.get_or_create_relationship(member_id, leader_id)
            rel_rev.relationship_type = RelationshipType.FOLLOWER

        return {
            "leader": leader_id,
            "members": member_ids,
            "type": group_type,
            "formed_tick": self.world.tick,
        }

    def resolve_dispute(
        self,
        disputant_a: str,
        disputant_b: str,
        resolution: str,
        arbiter_id: str | None = None,
    ) -> None:
        """Resolve a dispute between two agents."""
        # Both lose trust in each other slightly
        rel = self.get_or_create_relationship(disputant_a, disputant_b)
        rel.trust = max(-1.0, rel.trust - 0.1)

        # If there's an arbiter, both gain some respect for the arbiter
        if arbiter_id:
            for disputant in [disputant_a, disputant_b]:
                arbiter_rel = self.get_or_create_relationship(disputant, arbiter_id)
                arbiter_rel.respect = min(1.0, arbiter_rel.respect + 0.1)

    def spread_information(
        self,
        source_id: str,
        information: str,
        reliability: float,
    ) -> dict:
        """Spread information through the network."""
        # Start with direct contacts
        visited = {source_id}
        queue = list(self._social_graph.get(source_id, set()))
        spread = {}

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # How much does this person trust the source?
            rel = self.get_relationship(source_id, current)
            if rel:
                trust_factor = (rel.trust + 1) / 2  # Convert -1:1 to 0:1
                believability = reliability * trust_factor

                if believability > 0.3:
                    spread[current] = believability

                    # They might spread to their contacts
                    for neighbor in self._social_graph.get(current, set()):
                        if neighbor not in visited:
                            queue.append(neighbor)

        return {
            "source": source_id,
            "reliability": reliability,
            "information": information,
            "spread_to": len(spread),
            "recipients": spread,
        }

    def get_summary(self) -> dict:
        """Get social network summary statistics."""
        rel_types = defaultdict(int)
        for rel in self._relationships.values():
            rel_types[rel.relationship_type.value] += 1

        return {
            "total_relationships": len(self._relationships),
            "relationship_types": dict(rel_types),
            "total_reputations": len(self._reputations),
            "social_events": len(self._social_events),
            "avg_degree": sum(len(v) for v in self._social_graph.values()) / max(1, len(self._social_graph)),
        }


