"""
Ambient Signal Bus — the core of the event-driven architecture.

The signal bus implements the three paradigm rules:
1. No global access — agents receive only locally perceived signals
2. No centralized dispatch — signals are published, agents subscribe
3. Physical constraints — signals follow propagation, decay, duration rules

This is the most critical performance component of the engine.
"""

from __future__ import annotations

import heapq
import threading
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from ambientsaga.types import EntityID, Pos2D, Signal, SignalType

# Type alias for signal callbacks
SignalCallback: Callable[[Signal], None]  # noqa: F821


@dataclass
class SignalSubscription:
    """A subscription to signal types and/or spatial regions."""

    agent_id: EntityID
    signal_types: SignalType  # Bitmask of subscribed signal types
    position: Pos2D  # Agent's current position
    perception_radius: float  # Maximum signal detection range
    callback: SignalCallback  # noqa: F821
    priority: int = 0  # Higher = processed first
    active: bool = True

    def can_receive(self, signal: Signal) -> bool:
        """Check if this subscription can receive the signal."""
        if not self.active:
            return False
        if not bool(signal.signal_type & self.signal_types):
            return False
        distance = self.position.euclidean_distance(signal.source_pos)
        if distance > self.perception_radius:
            return False
        return True

    def signal_intensity_at(self, signal: Signal) -> float:
        """Compute received signal intensity at this subscription's position."""
        distance = self.position.euclidean_distance(signal.source_pos)
        return signal.at_distance(distance)


class SignalBus:
    """
    The ambient signal bus manages all signal propagation in the world.

    Key design decisions:
    - Lock-free for read-heavy workloads (agents mostly subscribe and read)
    - Lock-free write path using copy-on-write for subscriptions
    - Spatial indexing for fast range queries
    - Priority queue for urgent signal processing
    - Buffered batching for performance

    The signal bus does NOT provide global state access to agents.
    Agents only receive signals they are subscribed to and within range.
    """

    def __init__(self) -> None:
        # Subscriptions indexed by signal type for fast filtering
        self._subscriptions: dict[SignalType, list[SignalSubscription]] = defaultdict(list)

        # All subscriptions for iteration
        self._all_subscriptions: list[SignalSubscription] = []

        # Spatial index: (cx, cy) -> list of subscription indices
        # where cx, cy = position // SPATIAL_GRID_SIZE
        self._spatial_index: dict[tuple[int, int], list[int]] = defaultdict(list)

        # Pending signals (priority queue)
        self._pending_signals: list[tuple[int, Signal]] = []  # (priority, signal)

        # Signal history for research
        self._signal_history: list[Signal] = []
        self._max_history = 100_000

        # Statistics
        self._stats = {
            "signals_published": 0,
            "signals_delivered": 0,
            "signals_expired": 0,
            "subscriptions_created": 0,
            "subscriptions_removed": 0,
        }

        # Lock for thread safety (minimal contention expected)
        self._lock = threading.RLock()

        # Configuration
        self._max_signals_per_tick = 10_000
        self._spatial_grid_size = 32  # Spatial grid cell size in tiles

    # -------------------------------------------------------------------------
    # Subscription Management
    # -------------------------------------------------------------------------

    def subscribe(
        self,
        agent_id: EntityID,
        signal_types: SignalType,
        position: Pos2D,
        perception_radius: float,
        callback: SignalCallback,  # noqa: F821
        priority: int = 0,
    ) -> SignalSubscription:
        """
        Subscribe an agent to signals.

        The agent will receive signals matching `signal_types` that are
        within `perception_radius` of `position`.
        """
        subscription = SignalSubscription(
            agent_id=agent_id,
            signal_types=signal_types,
            position=position,
            perception_radius=perception_radius,
            callback=callback,
            priority=priority,
        )

        with self._lock:
            sub_idx = len(self._all_subscriptions)
            self._all_subscriptions.append(subscription)
            self._subscriptions[signal_types].append(subscription)

            # Spatial index
            spatial_key = self._get_spatial_key(position)
            self._spatial_index[spatial_key].append(sub_idx)

            self._stats["subscriptions_created"] += 1

        return subscription

    def unsubscribe(self, subscription: SignalSubscription) -> None:
        """Remove a subscription from the bus."""
        with self._lock:
            subscription.active = False
            self._stats["subscriptions_removed"] += 1

    def update_position(
        self, agent_id: EntityID, new_position: Pos2D
    ) -> None:
        """Update the position of all subscriptions for an agent."""
        with self._lock:
            for sub in self._all_subscriptions:
                if sub.agent_id == agent_id and sub.active:
                    old_key = self._get_spatial_key(sub.position)
                    new_key = self._get_spatial_key(new_position)
                    if old_key != new_key:
                        sub.position = new_position
                        # Note: spatial index update would be O(n) here
                        # For high-frequency position updates, use a more
                        # sophisticated spatial index

    def update_perception_radius(
        self, agent_id: EntityID, new_radius: float
    ) -> None:
        """Update the perception radius of all subscriptions for an agent."""
        with self._lock:
            for sub in self._all_subscriptions:
                if sub.agent_id == agent_id and sub.active:
                    sub.perception_radius = new_radius

    def _get_spatial_key(self, pos: Pos2D) -> tuple[int, int]:
        """Get spatial grid key for a position."""
        return (pos.x // self._spatial_grid_size, pos.y // self._spatial_grid_size)

    # -------------------------------------------------------------------------
    # Signal Publishing
    # -------------------------------------------------------------------------

    def publish(self, signal: Signal, priority: int = 2) -> None:
        """
        Publish a signal to the bus.

        Signals are queued and processed during the tick processing phase.
        High-priority signals (disasters, attacks) are processed first.
        """
        with self._lock:
            heapq.heappush(self._pending_signals, (priority, signal))
            if len(self._pending_signals) > self._max_signals_per_tick * 2:
                # Emergency: keep only the highest priority signals
                self._pending_signals = heapq.nlargest(
                    self._max_signals_per_tick, self._pending_signals
                )
                heapq.heapify(self._pending_signals)

    def publish_resource_signal(
        self,
        pos: Pos2D,
        resource_type: SignalType,
        intensity: float,
        source_id: EntityID | None = None,
    ) -> None:
        """Convenience method to publish a resource availability signal."""
        signal = Signal(
            signal_type=resource_type,
            source_pos=pos,
            intensity=intensity,
            duration=100,  # Resource signals persist for 100 ticks
            source_id=source_id,
        )
        self.publish(signal, priority=2)

    def publish_threat_signal(
        self,
        pos: Pos2D,
        threat_type: SignalType,
        intensity: float,
        source_id: EntityID | None = None,
    ) -> None:
        """Convenience method to publish a threat signal (high priority)."""
        signal = Signal(
            signal_type=threat_type,
            source_pos=pos,
            intensity=intensity,
            duration=50,
            source_id=source_id,
        )
        self.publish(signal, priority=0)  # CRITICAL priority

    # -------------------------------------------------------------------------
    # Signal Processing
    # -------------------------------------------------------------------------

    def process_signals(self, tick: int) -> int:
        """
        Process all pending signals for the current tick.

        Returns the number of signals delivered.
        """
        delivered = 0

        with self._lock:
            pending = self._pending_signals
            self._pending_signals = []

        # Process signals in priority order
        while pending:
            priority, signal = heapq.heappop(pending)

            # Tick the signal (decay duration)
            signal = signal.tick()
            if signal is None:
                self._stats["signals_expired"] += 1
                continue

            # Store in history
            self._signal_history.append(signal)
            if len(self._signal_history) > self._max_history:
                self._signal_history = self._signal_history[-self._max_history // 2:]

            # Deliver to matching subscriptions
            delivered += self._deliver_signal(signal)

            self._stats["signals_published"] += 1

        self._stats["signals_delivered"] += delivered
        return delivered

    def _deliver_signal(self, signal: Signal) -> int:
        """Deliver a signal to all matching subscriptions."""
        delivered = 0

        # Get relevant subscriptions (those that might be able to receive)
        # Use spatial index to narrow down
        relevant_subs: list[SignalSubscription] = []

        # Check subscriptions by signal type
        for sig_type in SignalType:
            if bool(signal.signal_type & sig_type):
                relevant_subs.extend(self._subscriptions.get(sig_type, []))

        # Also check all subscriptions (for multi-type signals)
        with self._lock:
            for sub in self._all_subscriptions:
                if sub.active and sub not in relevant_subs:
                    if bool(signal.signal_type & sub.signal_types):
                        relevant_subs.append(sub)

        # Remove duplicates
        seen = set()
        unique_subs: list[SignalSubscription] = []
        for sub in relevant_subs:
            sub_id = id(sub)
            if sub_id not in seen:
                seen.add(sub_id)
                unique_subs.append(sub)

        # Sort by priority (higher first)
        unique_subs.sort(key=lambda s: s.priority, reverse=True)

        # Deliver to each matching subscription
        for sub in unique_subs:
            if sub.can_receive(signal):
                intensity = sub.signal_intensity_at(signal)
                if intensity > 0.01:  # Minimum threshold
                    try:
                        sub.callback(signal)
                        delivered += 1
                    except Exception:
                        # Don't let callback errors break signal processing
                        pass

        return delivered

    # -------------------------------------------------------------------------
    # Spatial Queries
    # -------------------------------------------------------------------------

    def get_signals_in_radius(
        self, center: Pos2D, radius: float, signal_type: SignalType | None = None
    ) -> Iterator[Signal]:
        """Iterate over all signals in a radius (for research/visualization)."""
        with self._lock:
            for signal in self._signal_history:
                distance = center.euclidean_distance(signal.source_pos)
                if distance <= radius:
                    if signal_type is None or bool(signal.signal_type & signal_type):
                        yield signal

    def get_signal_density(self, pos: Pos2D, radius: float) -> int:
        """Count signals within a radius."""
        count = 0
        for _ in self.get_signals_in_radius(pos, radius):
            count += 1
        return count

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Get signal bus statistics."""
        return {
            **self._stats,
            "active_subscriptions": sum(
                1 for s in self._all_subscriptions if s.active
            ),
            "pending_signals": len(self._pending_signals),
            "signal_type_counts": {
                st.name: len(subs)
                for st, subs in self._subscriptions.items()
                if len(subs) > 0
            },
        }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self._stats = {
                "signals_published": 0,
                "signals_delivered": 0,
                "signals_expired": 0,
                "subscriptions_created": 0,
                "subscriptions_removed": 0,
            }

    def __len__(self) -> int:
        return len(self._pending_signals)
