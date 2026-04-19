"""
Causal tracing — trace the causal chains of events in the simulation.

This module enables deep causal analysis of the simulation:
- What caused this event?
- What were the downstream effects?
- Which agent's decision led to this outcome?
- How did a belief propagate through the population?
- What was the butterfly effect of a single action?

This is critical for academic research value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ambientsaga.types import Event


@dataclass
class CausalNode:
    """A node in a causal graph."""

    event: Event
    causes: list[CausalNode]
    effects: list[CausalNode]
    distance: int  # Distance from root event

    @property
    def causal_depth(self) -> int:
        """Maximum depth of this causal chain."""
        if not self.causes:
            return 0
        return 1 + max(c.causal_depth for c in self.causes)


class CausalTracer:
    """
    Traces causal chains through the event history.

    This enables answering questions like:
    - "What caused the fall of Empire X?"
    - "Trace the origins of this cultural belief"
    - "What was the cascading effect of this disaster?"
    - "How did Agent A's decision affect Agent B's wealth?"
    """

    def __init__(self, event_log: Any) -> None:
        self.event_log = event_log

    def trace_back(
        self, event_id: str, max_depth: int = 10
    ) -> CausalNode | None:
        """
        Trace the causal chain leading to an event.

        Args:
            event_id: The event to trace back from
            max_depth: Maximum depth to trace

        Returns:
            CausalNode tree representing the causal chain
        """
        events = self.event_log.get_by_tick_range(0, 10_000_000)
        event_map: dict[str, Event] = {e.event_id: e for e in events}

        def build_node(event_id: str, depth: int) -> CausalNode | None:
            if depth > max_depth:
                return None
            event = event_map.get(event_id)
            if event is None:
                return None

            causes: list[CausalNode] = []
            if event.cause_id:
                cause_node = build_node(event.cause_id, depth + 1)
                if cause_node:
                    causes.append(cause_node)

            return CausalNode(
                event=event,
                causes=causes,
                effects=[],  # Filled in separate pass
                distance=depth,
            )

        return build_node(event_id, 0)

    def trace_forward(
        self, event_id: str, max_depth: int = 10
    ) -> CausalNode | None:
        """
        Trace all effects caused by an event.

        Args:
            event_id: The event to trace effects from
            max_depth: Maximum depth to trace

        Returns:
            CausalNode tree representing the effect chain
        """
        events = self.event_log.get_by_tick_range(0, 10_000_000)
        event_map: dict[str, Event] = {e.event_id: e for e in events}

        def build_node(event_id: str, depth: int) -> CausalNode | None:
            if depth > max_depth:
                return None
            event = event_map.get(event_id)
            if event is None:
                return None

            # Find all events caused by this one
            effects: list[CausalNode] = []
            for eid, e in event_map.items():
                if e.cause_id == event_id:
                    effect_node = build_node(eid, depth + 1)
                    if effect_node:
                        effects.append(effect_node)

            return CausalNode(
                event=event,
                causes=[],  # Filled in separate pass
                effects=effects,
                distance=depth,
            )

        return build_node(event_id, 0)

    def find_responsible_agent(
        self, event_id: str, max_depth: int = 5
    ) -> list[tuple[str, int]]:
        """
        Find agents most responsible for an event (backtrace).

        Returns list of (agent_id, responsibility_score) sorted by score.
        """
        node = self.trace_back(event_id, max_depth)
        if not node:
            return []

        responsibility: dict[str, float] = {}

        def accumulate(node: CausalNode, weight: float) -> None:
            if node.event.subject_id:
                aid = node.event.subject_id
                responsibility[aid] = responsibility.get(aid, 0.0) + weight

            decay = 0.8  # Responsibility decays with distance
            for cause in node.causes:
                accumulate(cause, weight * decay)

        accumulate(node, 1.0)

        return sorted(responsibility.items(), key=lambda x: -x[1])

    def compute_event_impact(
        self, event_id: str, metric: str = "population"
    ) -> float:
        """
        Compute the impact of an event on a specific metric.

        Args:
            event_id: The event to analyze
            metric: The metric to measure impact on

        Returns:
            Estimated impact score
        """
        # Trace forward and measure metric changes
        forward = self.trace_forward(event_id, max_depth=20)
        if not forward:
            return 0.0

        # Count affected events
        affected_count = 0

        def count(node: CausalNode) -> None:
            nonlocal affected_count
            if node.event.event_type:
                affected_count += 1
            for effect in node.effects:
                count(effect)

        count(forward)

        # Simple impact score
        return affected_count * 1.0

    def generate_narrative(self, event_id: str) -> str:
        """
        Generate a human-readable narrative of an event's causal chain.

        This is the most valuable feature for academic storytelling.
        """
        backtrace = self.trace_back(event_id, max_depth=10)
        if not backtrace:
            return "No causal chain found."

        lines = ["=== CAUSAL NARRATIVE ===\n"]

        def format_node(node: CausalNode, indent: int = 0) -> None:
            prefix = "  " * indent
            lines.append(f"{prefix}→ [Tick {node.event.tick}] {node.event.describe()}")

            if node.event.subject_id:
                lines.append(f"{prefix}  Agent: {node.event.subject_id[:16]}")
            if node.event.narrative:
                lines.append(f"{prefix}  \"{node.event.narrative}\"")

            for cause in reversed(node.causes):
                format_node(cause, indent + 1)

        format_node(backtrace)
        lines.append("\n=== END NARRATIVE ===")

        return "\n".join(lines)
