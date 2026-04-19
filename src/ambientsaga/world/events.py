"""
Natural events - disasters, seasons, and world events.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from ambientsaga.types import Pos2D, Tick


@dataclass
class Disaster:
    """Base class for natural disasters."""
    disaster_type: str
    center: Pos2D
    radius: int
    intensity: float  # 0-1
    duration: int  # ticks
    start_tick: Tick
    effects: dict[str, Any]


class DisasterSystem:
    """System for managing natural disasters."""

    def __init__(self):
        self.active_disasters: list[Disaster] = []
        self.disaster_history: list[Disaster] = []

    def tick(self, tick: Tick) -> list[Disaster]:
        """Update disasters and return active ones."""
        # Check for expired disasters
        self.active_disasters = [
            d for d in self.active_disasters
            if tick < d.start_tick + d.duration
        ]
        return self.active_disasters

    def spawn_disaster(self, disaster_type: str, center: Pos2D, radius: int, intensity: float, duration: int, tick: Tick) -> Disaster:
        """Spawn a new disaster."""
        disaster = Disaster(
            disaster_type=disaster_type,
            center=center,
            radius=radius,
            intensity=intensity,
            duration=duration,
            start_tick=tick,
            effects={}
        )
        self.active_disasters.append(disaster)
        return disaster

    def spawn_flood(self, center: Pos2D, tick: Tick) -> Disaster:
        """Spawn a flood disaster."""
        return self.spawn_disaster(
            disaster_type="flood",
            center=center,
            radius=random.randint(3, 8),
            intensity=random.uniform(0.5, 0.9),
            duration=random.randint(10, 30),
            tick=tick
        )

    def spawn_drought(self, center: Pos2D, tick: Tick) -> Disaster:
        """Spawn a drought disaster."""
        return self.spawn_disaster(
            disaster_type="drought",
            center=center,
            radius=random.randint(10, 20),
            intensity=random.uniform(0.4, 0.8),
            duration=random.randint(30, 60),
            tick=tick
        )

    def spawn_earthquake(self, center: Pos2D, tick: Tick) -> Disaster:
        """Spawn an earthquake disaster."""
        return self.spawn_disaster(
            disaster_type="earthquake",
            center=center,
            radius=random.randint(2, 5),
            intensity=random.uniform(0.6, 1.0),
            duration=random.randint(1, 3),
            tick=tick
        )

    def spawn_wildfire(self, center: Pos2D, tick: Tick) -> Disaster:
        """Spawn a wildfire disaster."""
        return self.spawn_disaster(
            disaster_type="wildfire",
            center=center,
            radius=random.randint(5, 12),
            intensity=random.uniform(0.5, 0.9),
            duration=random.randint(15, 40),
            tick=tick
        )

    def spawn_plague(self, center: Pos2D, tick: Tick) -> Disaster:
        """Spawn a plague/disisease outbreak."""
        return self.spawn_disaster(
            disaster_type="plague",
            center=center,
            radius=random.randint(8, 15),
            intensity=random.uniform(0.3, 0.7),
            duration=random.randint(40, 80),
            tick=tick
        )

    def get_affected_area(self, disaster: Disaster) -> set[Pos2D]:
        """Get all positions affected by a disaster."""
        x, y = disaster.center
        r = disaster.radius
        affected = set()
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    affected.add(Pos2D(x + dx, y + dy))
        return affected

    def get_disaster_severity_at(self, pos: Pos2D) -> float:
        """Get total disaster severity at a position."""
        total = 0.0
        x, y = pos
        for d in self.active_disasters:
            cx, cy = d.center
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if dist <= d.radius:
                # Linear falloff from center
                severity = d.intensity * (1 - dist / d.radius)
                total += severity
        return min(total, 1.0)


class SeasonalEvent:
    """Seasonal event handlers."""

    @staticmethod
    def get_season_name(season: int) -> str:
        """Get season name from number."""
        return ["Spring", "Summer", "Autumn", "Winter"][season % 4]

    @staticmethod
    def get_season_effects(season: int) -> dict[str, Any]:
        """Get effects for a season."""
        effects = {
            0: {  # Spring
                "temperature": +0.1,
                "fertility": +0.2,
                "migration": "north",
            },
            1: {  # Summer
                "temperature": +0.3,
                "water_demand": +0.3,
                "activity": "high",
            },
            2: {  # Autumn
                "harvest": True,
                "migration": "south",
                "activity": "medium",
            },
            3: {  # Winter
                "temperature": -0.3,
                "energy_demand": +0.5,
                "activity": "low",
            },
        }
        return effects.get(season, {})


class EventLog:
    """Event log for tracking world events."""

    def __init__(
        self,
        max_events: int = 100000,
        causal_enabled: bool = True,
    ):
        self._events: list[dict] = []
        self._max_events = max_events
        self._causal_enabled = causal_enabled
        self._event_index: dict[int, list[int]] = {}  # tick -> event indices
        self._entity_index: dict[str, list[int]] = {}   # entity_id -> event indices

    def log(self, event: "Event") -> None:
        """Log an event."""
        # Get event ID
        event_id = getattr(event, "event_id", None)
        if event_id is None:
            event_id = f"event_{len(self._events)}"

        # Build event record
        record = {
            "event_id": event_id,
            "tick": event.tick if hasattr(event, "tick") else 0,
            "event_type": event.event_type if hasattr(event, "event_type") else "unknown",
            "subject_id": event.subject_id if hasattr(event, "subject_id") else None,
            "object_id": event.object_id if hasattr(event, "object_id") else None,
            "position": event.position if hasattr(event, "position") else None,
            "cause_id": getattr(event, "cause_id", None),
            "data": getattr(event, "data", {}),
        }

        # Add to log
        idx = len(self._events)
        self._events.append(record)

        # Index by tick
        tick = record["tick"]
        if tick not in self._event_index:
            self._event_index[tick] = []
        self._event_index[tick].append(idx)

        # Index by entity
        for entity_key in ["subject_id", "object_id"]:
            entity_id = record.get(entity_key)
            if entity_id:
                if entity_id not in self._entity_index:
                    self._entity_index[entity_id] = []
                self._entity_index[entity_id].append(idx)

        # Trim if needed
        if len(self._events) > self._max_events:
            trim_count = len(self._events) - self._max_events
            self._events = self._events[trim_count:]
            # Rebuild index
            self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild event indices."""
        self._event_index.clear()
        self._entity_index.clear()
        for idx, event in enumerate(self._events):
            tick = event["tick"]
            if tick not in self._event_index:
                self._event_index[tick] = []
            self._event_index[tick].append(idx)
            for entity_key in ["subject_id", "object_id"]:
                entity_id = event.get(entity_key)
                if entity_id:
                    if entity_id not in self._entity_index:
                        self._entity_index[entity_id] = []
                    self._entity_index[entity_id].append(idx)

    def get_by_tick(self, tick: int) -> list[dict]:
        """Get events by tick."""
        indices = self._event_index.get(tick, [])
        return [self._events[i] for i in indices]

    def get_by_entity(self, entity_id: str) -> list[dict]:
        """Get events by entity."""
        if entity_id not in self._entity_index:
            return []
        indices = self._entity_index[entity_id]
        return [self._events[i] for i in indices]

    def get_causal_chain(self, event_id: str) -> list[dict]:
        """Get causal chain for an event."""
        if not self._causal_enabled:
            return []
        # Find the event
        start_idx = None
        for idx, event in enumerate(self._events):
            if event["event_id"] == event_id:
                start_idx = idx
                break
        if start_idx is None:
            return []
        # Walk backwards through causes
        chain = []
        current_idx = start_idx
        visited = set()
        while current_idx is not None and current_idx not in visited:
            event = self._events[current_idx]
            chain.append(event)
            visited.add(current_idx)
            # Find cause
            cause_id = event.get("cause_id")
            if cause_id:
                current_idx = None
                for idx, e in enumerate(self._events):
                    if e["event_id"] == cause_id:
                        current_idx = idx
                        break
            else:
                current_idx = None
        return chain

    def get_event_count(self) -> int:
        """Get total event count."""
        return len(self._events)

    def get_all_events(self) -> list[dict]:
        """Get all events."""
        return self._events.copy()