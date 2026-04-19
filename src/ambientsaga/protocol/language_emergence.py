"""
Language Emergence — shared signals arise from repeated interaction.

Language is not predefined. Agents invent and use signals, and when multiple
agents converge on the same interpretation, a shared vocabulary emerges.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class SignalUsage:
    """Record of a signal being used in an interaction."""
    signal: str
    sender_id: str
    receiver_id: str
    interpreted_meaning: str
    accepted: bool
    tick: int
    trace_id: str


class LanguageEmergence:
    """
    Tracks signal usage and detects shared vocabulary.
    When agents consistently use the same signal with the same meaning,
    a shared language emerges.
    """

    def __init__(self) -> None:
        # signal -> {meaning -> count}
        self._vocabulary: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        # signal -> total use count
        self._signal_counts: dict[str, int] = defaultdict(int)
        # agent_id -> {signal -> meaning}
        self._agent_signatures: dict[str, dict[str, str]] = defaultdict(dict)
        # Signal creation log: signal -> first_usage_tick
        self._signal_origins: dict[str, tuple[str, int]] = {}
        # Usage history
        self._usage_history: list[SignalUsage] = []
        self._max_history = 100_000

    def record_usage(self, signal: str, sender_id: str, receiver_id: str,
                     interpreted_meaning: str, accepted: bool, tick: int,
                     trace_id: str) -> None:
        """Record a signal being used."""
        usage = SignalUsage(
            signal=signal, sender_id=sender_id, receiver_id=receiver_id,
            interpreted_meaning=interpreted_meaning, accepted=accepted,
            tick=tick, trace_id=trace_id,
        )
        self._usage_history.append(usage)
        if len(self._usage_history) > self._max_history:
            self._usage_history = self._usage_history[-self._max_history // 2:]

        # Track vocabulary: signal is associated with this meaning
        self._vocabulary[signal][interpreted_meaning] += 1
        self._signal_counts[signal] += 1

        # Track agent's personal vocabulary
        self._agent_signatures[sender_id][signal] = interpreted_meaning

        # Track signal origin (who invented it first)
        if signal not in self._signal_origins:
            self._signal_origins[signal] = (sender_id, tick)

    def invent_signal(self, agent_id: str, meaning: str, tick: int,
                     rng: random.Random | None = None) -> str:
        """
        Agent invents a new signal. Most of the time they reuse existing signals
        (social learning). Occasionally they create new ones.
        """
        if rng is None:
            rng = random.Random(tick + hash(agent_id))

        # 75% chance: reuse existing signal with same meaning
        for sig, meanings in self._vocabulary.items():
            if meaning in meanings and meanings[meaning] >= 3:
                if rng.random() < 0.75:
                    return sig

        # 20% chance: reuse existing signal (any meaning)
        if self._vocabulary:
            existing = list(self._vocabulary.keys())
            if rng.random() < 0.20:
                return rng.choice(existing)

        # 5% chance: create a new signal
        # Generate a descriptive signal name
        parts = meaning.lower().split()
        if len(parts) >= 2:
            new_signal = parts[0][:4] + "_" + parts[1][:4] + "_" + str(tick % 1000)
        else:
            new_signal = parts[0][:6] + "_" + str(tick % 1000) if parts else f"sig_{tick % 10000}"
        return new_signal

    def get_shared_signals(self, threshold: float = 0.5,
                           min_agents: int = 3) -> dict[str, str]:
        """
        Get signals that are shared by multiple agents with consistent meaning.
        threshold: minimum share of agents using the signal
        Returns {signal: dominant_meaning}
        """
        recent = self._usage_history[-5000:]
        if len(recent) < 20:
            return {}

        # Count signal-meaning pairs
        signal_meaning: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        signal_agents: dict[str, set[str]] = defaultdict(set)

        for usage in recent:
            signal_meaning[usage.signal][usage.interpreted_meaning] += 1
            signal_agents[usage.signal].add(usage.sender_id)

        shared = {}
        for signal, agents in signal_agents.items():
            if len(agents) < min_agents:
                continue
            # Check if one meaning dominates
            meanings = signal_meaning[signal]
            if not meanings:
                continue
            dominant = max(meanings.items(), key=lambda x: x[1])
            total = sum(meanings.values())
            share = dominant[1] / total
            if share >= threshold and dominant[1] >= 3:
                shared[signal] = dominant[0]

        return shared

    def get_signal_evolution(self, signal: str) -> list[dict]:
        """Get the evolution of a signal's meaning over time."""
        usages = [u for u in self._usage_history if u.signal == signal]
        if not usages:
            return []

        # Group by time periods
        if not usages:
            return []

        min_tick = min(u.tick for u in usages)
        max_tick = max(u.tick for u in usages)
        period = max(1, (max_tick - min_tick) // 5)

        periods = []
        for i in range(5):
            period_start = min_tick + i * period
            period_end = period_start + period
            period_usages = [u for u in usages if period_start <= u.tick < period_end]
            if period_usages:
                meanings = defaultdict(int)
                for u in period_usages:
                    meanings[u.interpreted_meaning] += 1
                dominant = max(meanings.items(), key=lambda x: x[1])
                periods.append({
                    "period": i,
                    "tick_range": (period_start, period_end),
                    "dominant_meaning": dominant[0],
                    "dominant_count": dominant[1],
                    "total_usages": len(period_usages),
                    "acceptance_rate": sum(1 for u in period_usages if u.accepted) / len(period_usages),
                })
        return periods

    def get_vocabulary_stats(self) -> dict:
        """Get language statistics."""
        shared = self.get_shared_signals(0.5, 3)
        return {
            "total_signals": len(self._signal_counts),
            "total_usages": len(self._usage_history),
            "shared_signals": len(shared),
            "shared_vocabulary": shared,
            "newest_signals": sorted(self._signal_origins.items(), key=lambda x: -x[1][1])[:5],
            "top_signals": sorted(self._signal_counts.items(), key=lambda x: -x[1])[:10],
        }

    def update_agent_signals(self, agent, signal: str, meaning: str) -> None:
        """Update an agent's known_signals dict."""
        known = getattr(agent, 'known_signals', {})
        known[signal] = meaning
        agent.known_signals = known
