"""
Distributed Reputation Network — gossip-based reputation propagation.

Reputation is not a single global score. Every agent has their own opinion
about others, formed from direct experience and gossip. Reputation spreads
through the social network like a diffusion process.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ambientsaga.agents.agent import Agent


@dataclass
class ReputationObservation:
    """A single observation about an agent's behavior."""
    observer_id: str
    target_id: str
    behavior: str         # What was observed ("helped", "defrauded", etc.)
    valence: float        # -1 (negative) to +1 (positive)
    confidence: float    # How confident is the observer (based on directness)
    tick: int
    trace_id: str | None = None

    @property
    def weight(self) -> float:
        """Effective weight = valence * confidence"""
        return self.valence * self.confidence


@dataclass
class ReputationView:
    """What one agent believes about another."""
    score: float         # Weighted reputation (-1 to 1)
    confidence: float    # How certain (0 to 1)
    observations: list[ReputationObservation] = field(default_factory=list)
    last_update: int = 0

    def update(self, obs: ReputationObservation, decay: float = 0.98) -> None:
        """Update view with a new observation."""
        # Decay existing confidence
        self.confidence *= decay

        # Add new observation weight
        w = obs.weight
        total_weight = self.confidence + abs(w)
        if total_weight > 0:
            self.score = (self.score * self.confidence + w) / total_weight
        self.confidence = min(1.0, self.confidence + abs(w) * 0.3)
        self.observations.append(obs)
        self.last_update = obs.tick

        # Keep only recent observations
        if len(self.observations) > 20:
            self.observations = self.observations[-20:]


class ReputationNetwork:
    """
    Distributed reputation system where each agent maintains their own
    opinions about others. Reputation spreads through gossip.
    """

    def __init__(self, world) -> None:
        self.world = world
        # agent_id -> {target_id -> ReputationView}
        self._views: dict[str, dict[str, ReputationView]] = defaultdict(dict)
        # Transmission log: (speaker_id, listener_id, about_id) for tracking info flow
        self._transmission_log: list[tuple[str, str, str, int]] = []
        self._max_transmissions = 100_000

        # Gossip cache: gossip agents share what they know
        self._gossip_cache: dict[str, list[ReputationObservation]] = defaultdict(list)

    def observe(self, observer_id: str, target_id: str, behavior: str,
                valence: float, tick: int, trace_id: str | None = None) -> None:
        """
        Record an observation of an agent's behavior.
        This is the primary way reputation is created.
        """
        obs = ReputationObservation(
            observer_id=observer_id,
            target_id=target_id,
            behavior=behavior,
            valence=max(-1.0, min(1.0, valence)),
            confidence=1.0,  # Direct observation = full confidence
            tick=tick,
            trace_id=trace_id,
        )

        # Update the observer's view of the target
        if target_id not in self._views[observer_id]:
            self._views[observer_id][target_id] = ReputationView(score=0.0, confidence=0.0)
        self._views[observer_id][target_id].update(obs)

        # Also cache for gossip
        self._gossip_cache[observer_id].append(obs)
        if len(self._gossip_cache[observer_id]) > 50:
            self._gossip_cache[observer_id] = self._gossip_cache[observer_id][-50:]

    def spread(self, tick: int, gossip_agents: list[str]) -> None:
        """
        Gossip agents share what they know with each other.
        This is how reputation propagates through the network.
        """
        if len(gossip_agents) < 2:
            return

        rng = random.Random(tick + 7777)
        rng.shuffle(gossip_agents)

        for i, gossip_id in enumerate(gossip_agents):
            if i >= 5:  # Limit gossip per tick
                break

            # Find gossip partners (agents who know this agent)
            partner_id = gossip_agents[(i + 1) % len(gossip_agents)]

            # Gossip agent shares what they know about others
            cache = self._gossip_cache.get(gossip_id, [])

            # Share most recent observations
            for obs in cache[-3:]:
                if obs.target_id == partner_id:
                    continue  # Don't share observations about the listener

                # Create a copy with reduced confidence (hearsay)
                hearsay = ReputationObservation(
                    observer_id=obs.observer_id,
                    target_id=obs.target_id,
                    behavior=obs.behavior,
                    valence=obs.valence,
                    confidence=obs.confidence * 0.6,  # Reduce for hearsay
                    tick=obs.tick,
                    trace_id=obs.trace_id,
                )

                # Update listener's view
                if hearsay.target_id not in self._views[partner_id]:
                    self._views[partner_id][ hearsay.target_id] = ReputationView(score=0.0, confidence=0.0)
                self._views[partner_id][ hearsay.target_id].update(hearsay, decay=0.95)

                # Log transmission
                self._transmission_log.append((gossip_id, partner_id, hearsay.target_id, tick))
                if len(self._transmission_log) > self._max_transmissions:
                    self._transmission_log = self._transmission_log[-self._max_transmissions // 2:]

    def get_reputation(self, agent_id: str, target_id: str) -> tuple[float, float]:
        """
        Get agent's reputation of target (score, confidence).
        Returns (0.0, 0.0) if no information.
        """
        view = self._views.get(agent_id, {}).get(target_id)
        if view is None:
            return 0.0, 0.0
        return view.score, view.confidence

    def get_all_reputations(self, agent_id: str) -> dict[str, tuple[float, float]]:
        """Get all reputation views for an agent."""
        return {
            target: (view.score, view.confidence)
            for target, view in self._views.get(agent_id, {}).items()
        }

    def get_social_network(self, agent_id: str, depth: int = 2) -> dict:
        """
        Get an agent's social network (who knows whom).
        Returns a graph representation.
        """
        visited = {agent_id}
        frontier = {agent_id}
        network: dict[str, list[str]] = defaultdict(list)

        for _ in range(depth):
            next_frontier = set()
            for a_id in frontier:
                views = self._views.get(a_id, {})
                for target_id, view in views.items():
                    if view.confidence > 0.3:  # Only significant relationships
                        network[a_id].append(target_id)
                        if target_id not in visited:
                            visited.add(target_id)
                            next_frontier.add(target_id)
            frontier = next_frontier

        return dict(network)

    def get_most_trusted(self, agent_id: str, limit: int = 5) -> list[tuple[str, float]]:
        """Get the most trusted agents according to agent_id's view."""
        views = self._views.get(agent_id, {})
        scored = [(t, v.score) for t, v in views.items() if v.confidence > 0.2]
        return sorted(scored, key=lambda x: -x[1])[:limit]

    def get_most_reputable(self, limit: int = 10) -> list[tuple[str, float]]:
        """
        Get globally most reputable agents (by aggregate reputation).
        This is NOT a central score — it's computed from all observations.
        """
        # Aggregate all observations per target
        target_scores: dict[str, list[float]] = defaultdict(list)
        for observer_id, views in self._views.items():
            for target_id, view in views.items():
                if view.confidence > 0.3:
                    target_scores[target_id].append(view.score)

        if not target_scores:
            return []

        # Average across all observers
        avg_scores = [(t, sum(sc) / len(sc)) for t, sc in target_scores.items()]
        return sorted(avg_scores, key=lambda x: -x[1])[:limit]

    def record_from_trace(self, trace) -> None:
        """
        Create reputation observations from a protocol trace.
        Called after each trace is processed.
        """
        if not trace.receiver_id:
            return  # Broadcast — less reliable

        if trace.accepted:
            # Positive: receiver accepted the interaction
            self.observe(
                trace.receiver_id, trace.actor_id,
                f"accepted_{trace.signal}",
                valence=0.3 + trace.language_shared * 0.3,
                tick=trace.tick, trace_id=trace.trace_id,
            )
        else:
            # Neutral or negative
            self.observe(
                trace.receiver_id, trace.actor_id,
                f"ignored_{trace.signal}",
                valence=-0.1,
                tick=trace.tick, trace_id=trace.trace_id,
            )

        # Record the exchange
        if trace.accepted and trace.content.get("type") == "resource_transfer":
            self.observe(
                trace.receiver_id, trace.actor_id,
                "received_resource",
                valence=0.2,
                tick=trace.tick, trace_id=trace.trace_id,
            )
            self.observe(
                trace.actor_id, trace.receiver_id,
                "gifted_resource",
                valence=0.1,
                tick=trace.tick, trace_id=trace.trace_id,
            )

    def get_summary(self) -> dict:
        """Get summary statistics."""
        total_views = sum(len(v) for v in self._views.values())
        return {
            "agents_with_views": len(self._views),
            "total_reputation_views": total_views,
            "total_transmissions": len(self._transmission_log),
            "most_reputable": self.get_most_reputable(5),
        }
