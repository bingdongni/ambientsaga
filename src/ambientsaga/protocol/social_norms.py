"""
Emergent Social Norms — customs, rules, and institutions from repeated patterns.

Social norms emerge when the same Trace patterns occur repeatedly:
- Repeated help → reciprocity norm
- Repeated gift → gift economy
- Repeated authority → leadership hierarchy
- Repeated punishment → justice system
- Repeated collective action → organization

No norms are predefined. They crystallize from behavior.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ambientsaga.protocol.interaction import Trace



@dataclass
class Norm:
    """
    An emergent social norm detected from repeated behavior.
    """
    norm_id: str
    name: str                    # Emergent name ("gift_norm", "leader_trust")
    description: str             # What the norm governs
    trigger_pattern: str        # The trace pattern that creates it
    count: int                   # How many times this pattern occurred
    participating_agents: set[str]
    strength: float             # 0-1, how established is this norm
    first_emerged: int          # tick when first detected
    last_observed: int           # tick when last observed
    norm_type: str               # "reciprocity", "hierarchy", "custom", "prohibition"

    @property
    def is_active(self) -> bool:
        return self.strength > 0.3


@dataclass
class Institution:
    """
    A more formalized norm — a persistent structure that enforces behavior.
    Emerges when a norm becomes strong enough to be "expected."
    """
    institution_id: str
    name: str
    type: str           # "leadership", "exchange_system", "dispute_resolution"
    founding_tick: int
    members: set[str]
    rules: list[str]    # Inferred rules from behavior
    stability: float     # 0-1
    norm_id: str | None # Which norm this institution formalized


class EmergentNorms:
    """
    Detects and tracks emergent social norms from Trace patterns.
    """

    def __init__(self, world) -> None:
        self.world = world
        self._norms: dict[str, Norm] = {}
        self._institutions: dict[str, Institution] = {}
        self._norm_counter = 0
        self._inst_counter = 0

        # Pattern detection: track trace sequences
        # sequence_hash -> (trace_ids, tick)
        self._sequences: dict[str, tuple[list[str], int]] = {}

        # Norm emergence thresholds
        self._norm_emergence_threshold = 20   # Pattern repeats N times
        self._institution_threshold = 50      # Norm strengthens to this level

    def analyze_traces(self, tick: int) -> list[Norm]:
        """
        Analyze recent traces and detect emerging norms.
        Called periodically (not every tick for performance).
        """
        recent = self.world._protocol._traces[-500:] if hasattr(self.world, '_protocol') else []
        new_norms = []

        if len(recent) < 20:
            return []

        # Group by signal
        by_signal: dict[str, list[Trace]] = defaultdict(list)
        for t in recent:
            by_signal[t.signal].append(t)

        for signal, traces in by_signal.items():
            if len(traces) < self._norm_emergence_threshold:
                continue

            # Check for consistent pattern
            accepted = [t for t in traces if t.accepted]
            acceptance_rate = len(accepted) / len(traces) if traces else 0

            if acceptance_rate < 0.3:
                continue  # Pattern not stable enough

            # Get participants
            participants = set(t.actor_id for t in traces if t.actor_id)
            participants |= set(t.receiver_id for t in traces if t.receiver_id)

            # Create a norm ID
            norm_id = f"norm_{signal}_{len(self._norms)}"

            # Check if this norm already exists
            existing = None
            for n in self._norms.values():
                if n.trigger_pattern == signal:
                    existing = n
                    break

            if existing:
                # Update existing norm
                existing.count += len(traces)
                existing.participating_agents |= participants
                existing.last_observed = tick
                # Strengthen based on consistency
                existing.strength = min(1.0, existing.strength + acceptance_rate * 0.01)
                # Check for institution formation
                if existing.strength >= 0.7 and existing.count >= self._institution_threshold:
                    self._formalize_norm(existing, tick)
            else:
                # Create new norm
                norm_type = self._classify_norm_type(signal, traces)
                norm = Norm(
                    norm_id=norm_id,
                    name=f"{signal}_norm",
                    description=self._describe_norm(signal, traces),
                    trigger_pattern=signal,
                    count=len(traces),
                    participating_agents=participants,
                    strength=acceptance_rate,
                    first_emerged=tick,
                    last_observed=tick,
                    norm_type=norm_type,
                )
                self._norms[norm_id] = norm
                new_norms.append(norm)
                self._norm_counter += 1

        # Decay inactive norms
        for norm in self._norms.values():
            if tick - norm.last_observed > 100:
                norm.strength *= 0.95

        # Remove dead norms
        dead = [nid for nid, n in self._norms.items() if n.strength < 0.1]
        for did in dead:
            del self._norms[did]

        return new_norms

    def _classify_norm_type(self, signal: str, traces: list) -> str:
        """Classify what type of norm this is based on behavior."""
        has_resource = any(t.content.get("type") == "resource_transfer" for t in traces)
        has_gift = signal in {"gift", "help"}
        has_promise = signal == "promise"
        has_threat = signal == "threat"

        if has_gift and has_resource:
            return "reciprocity"
        elif has_promise:
            return "promise_keeping"
        elif has_threat:
            return "prohibition"
        elif signal in {"inform", "ask"}:
            return "communication"
        elif signal == "accept":
            return "agreement"
        else:
            return "custom"

    def _describe_norm(self, signal: str, traces: list) -> str:
        """Generate a description of the norm."""
        counts = len(traces)
        accepted = sum(1 for t in traces if t.accepted)
        rate = accepted / counts if counts else 0
        return f"{signal} behavior occurs {counts} times with {rate:.0%} acceptance rate"

    def _formalize_norm(self, norm: Norm, tick: int) -> Institution | None:
        """When a norm becomes strong enough, it may formalize into an institution."""
        if norm.norm_id in {i.norm_id for i in self._institutions.values()}:
            return None  # Already formalized

        # Determine institution type
        if norm.norm_type == "reciprocity":
            inst_type = "exchange_system"
            name = f"Exchange Institution #{self._inst_counter}"
        elif norm.norm_type == "promise_keeping":
            inst_type = "dispute_resolution"
            name = f"Trust Institution #{self._inst_counter}"
        elif norm.norm_type == "hierarchy":
            inst_type = "leadership"
            name = f"Leadership Institution #{self._inst_counter}"
        else:
            inst_type = "custom"
            name = f"Custom Institution #{self._inst_counter}"

        institution = Institution(
            institution_id=f"inst_{self._inst_counter}",
            name=name,
            type=inst_type,
            founding_tick=tick,
            members=norm.participating_agents.copy(),
            rules=self._infer_rules(norm),
            stability=norm.strength,
            norm_id=norm.norm_id,
        )
        self._institutions[institution.institution_id] = institution
        self._inst_counter += 1
        return institution

    def _infer_rules(self, norm: Norm) -> list[str]:
        """Infer rules from norm behavior."""
        rules = []
        if norm.norm_type == "reciprocity":
            rules.append("When someone helps you, help them in return")
            rules.append("Gifts create reciprocal obligations")
        elif norm.norm_type == "promise_keeping":
            rules.append("Promises should be fulfilled")
            rules.append("Breaking promises reduces trust")
        elif norm.norm_type == "prohibition":
            rules.append("Do not repeat harmful behavior")
        elif norm.norm_type == "communication":
            rules.append("Information should be shared honestly")
        return rules

    def get_active_norms(self) -> list[Norm]:
        """Get all currently active norms."""
        return [n for n in self._norms.values() if n.is_active]

    def get_institutions(self) -> list[Institution]:
        """Get all formal institutions."""
        return list(self._institutions.values())

    def apply_norm_influence(self, agent, trace: Trace) -> dict:
        """
        Apply normative pressure to an agent's behavior.
        Returns dict with keys like 'should_accept', 'pressure', 'reason'.
        """
        # Find relevant norms
        relevant_norms = [
            n for n in self._norms.values()
            if n.is_active and trace.signal == n.trigger_pattern
        ]

        if not relevant_norms:
            return {}

        # Aggregate normative pressure
        total_pressure = sum(n.strength for n in relevant_norms)
        reasons = [n.description for n in relevant_norms]

        return {
            "pressure": total_pressure,
            "reasons": reasons,
            "norm_count": len(relevant_norms),
            "should_accept": total_pressure > 0.5,
        }

    def get_summary(self) -> dict:
        """Get summary of emergent norms and institutions."""
        active = self.get_active_norms()
        return {
            "total_norms": len(self._norms),
            "active_norms": len(active),
            "institutions": len(self._institutions),
            "norm_types": {nt: sum(1 for n in active if n.norm_type == nt) for nt in
                          ["reciprocity", "promise_keeping", "prohibition", "communication", "custom"]},
            "strongest_norms": [(n.name, n.strength) for n in sorted(active, key=lambda x: -x.strength)[:5]],
        }
