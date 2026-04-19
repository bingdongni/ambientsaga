"""
Event Simulation Engine - Comprehensive event system for AmbientSaga

Provides:
- Event scheduling and triggers
- Event chain reactions
- Multi-type event integration (disasters, seasons, social, economic)
- Event consequences and cascading effects
- Historical event analysis

The event engine is designed to be extensible and couples with:
- World: climate, terrain, disasters
- Agents: actions, decisions, social events
- Economy: market events, trade disruptions
- Science: environmental changes, evolutionary events
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ambientsaga.types import Pos2D, Tick
from ambientsaga.world.events import Disaster, DisasterSystem, EventLog


class EventType(Enum):
    """Types of events in the simulation."""
    # Natural events
    DISASTER = "disaster"
    SEASON_CHANGE = "season_change"
    WEATHER_CHANGE = "weather_change"
    CLIMATE_SHIFT = "climate_shift"

    # Biological events
    SPECIES_EXTINCTION = "species_extinction"
    SPECIES_EMERGENCE = "species_emergence"
    POPULATION_BOOM = "population_boom"
    POPULATION_CRASH = "population_crash"
    DISEASE_OUTBREAK = "disease_outbreak"

    # Social events
    CONFLICT = "conflict"
    COOPERATION = "cooperation"
    MIGRATION = "migration"
    SETTLEMENT = "settlement"
    TRADE_NETWORK = "trade_network"

    # Economic events
    RESOURCE_SCARCITY = "resource_scarcity"
    MARKET_FLUCTUATION = "market_fluctuation"
    INNOVATION = "innovation"
    TRADE_ROUTE = "trade_route"

    # Cultural events
    BELIEF_SHIFT = "belief_shift"
    RITUAL = "ritual"
    LANGUAGE_CHANGE = "language_change"

    # Emergent events (from Protocol)
    INSTITUTION_EMERGENCE = "institution_emergence"
    NORM_ESTABLISHMENT = "norm_establishment"
    REPUTATION_CASCADE = "reputation_cascade"

    # Custom
    CUSTOM = "custom"


class EventPriority(Enum):
    """Event priority levels."""
    CRITICAL = 0  # Immediate action required
    HIGH = 1      # Important, process soon
    NORMAL = 2    # Standard priority
    LOW = 3       # Can be delayed
    BACKGROUND = 4  # Informational only


@dataclass
class Event:
    """Base event class."""
    event_id: str
    event_type: EventType
    tick: Tick
    position: Pos2D | None = None

    # Classification
    priority: EventPriority = EventPriority.NORMAL
    source: str = "system"  # system, agent, disaster, social

    # Relationships
    cause_id: str | None = None  # What caused this event
    consequence_ids: list[str] = field(default_factory=list)

    # Effects
    effects: dict[str, Any] = field(default_factory=dict)
    affected_entities: list[str] = field(default_factory=list)

    # Metadata
    duration: int = 1  # How many ticks the event lasts
    intensity: float = 1.0  # 0-1, severity of the event

    # State
    is_active: bool = True
    is_processed: bool = False


@dataclass
class ScheduledEvent:
    """An event scheduled for future execution."""
    event: Event
    trigger_tick: Tick
    conditions: dict[str, Any] = field(default_factory=dict)  # Conditions that must be met


@dataclass
class EventTrigger:
    """Trigger conditions for events."""
    trigger_id: str
    name: str
    event_type: EventType

    # Conditions (all must be true to trigger)
    conditions: dict[str, Any] = field(default_factory=dict)

    # Effects when triggered
    effects: dict[str, Any] = field(default_factory=dict)

    # Scheduling
    cooldown: int = 100  # Ticks between trigger activations
    last_triggered: Tick = -1000

    # State
    is_active: bool = True


class EventSimulationEngine:
    """
    Comprehensive event simulation engine.

    Manages all types of events and their interactions:
    - Natural disasters and seasonal changes
    - Population and ecological events
    - Social and cultural events
    - Economic events
    - Emergent events from Protocol system

    Features:
    - Event scheduling
    - Trigger-based events
    - Chain reactions
    - Cascading effects
    - Event history and analysis
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

        # Event systems
        self.disaster_system = DisasterSystem()

        # Event management
        self.events: dict[str, Event] = {}
        self.active_events: list[str] = []  # Event IDs of active events
        self.event_queue: list[ScheduledEvent] = []

        # Triggers
        self.triggers: dict[str, EventTrigger] = {}
        self._init_default_triggers()

        # Event history
        self.event_log = EventLog(
            max_events=self.config.get("max_events", 100000),
            causal_enabled=True,
        )

        # Statistics
        self.tick = 0
        self.total_events = 0
        self.event_counts: dict[EventType, int] = {}
        self.event_chain_lengths: list[int] = []

        # Event callbacks
        self._callbacks: dict[EventType, list[Callable]] = {}

        # Cascade tracking
        self._cascade_depth = 0
        self._max_cascade_depth = 10

    def _init_default_triggers(self) -> None:
        """Initialize default event triggers."""
        # Drought trigger
        self.triggers["drought_trigger"] = EventTrigger(
            trigger_id="drought_trigger",
            name="Drought Trigger",
            event_type=EventType.DISASTER,
            conditions={"weather": "dry", "duration": 30},
            effects={"type": "drought"},
            cooldown=200,
        )

        # Flood trigger
        self.triggers["flood_trigger"] = EventTrigger(
            trigger_id="flood_trigger",
            name="Flood Trigger",
            event_type=EventType.DISASTER,
            conditions={"weather": "heavy_rain", "duration": 5},
            effects={"type": "flood"},
            cooldown=150,
        )

        # Population boom trigger
        self.triggers["population_boom"] = EventTrigger(
            trigger_id="population_boom",
            name="Population Boom",
            event_type=EventType.POPULATION_BOOM,
            conditions={"population_growth": 0.1},
            cooldown=100,
        )

        # Resource scarcity trigger
        self.triggers["resource_scarcity"] = EventTrigger(
            trigger_id="resource_scarcity",
            name="Resource Scarcity",
            event_type=EventType.RESOURCE_SCARCITY,
            conditions={"resource_level": 0.2},
            cooldown=50,
        )

        # Innovation trigger
        self.triggers["innovation"] = EventTrigger(
            trigger_id="innovation",
            name="Innovation Event",
            event_type=EventType.INNOVATION,
            conditions={"population_size": 100, "tech_level": 0.5},
            cooldown=500,
        )

    def create_event(
        self,
        event_type: EventType,
        tick: Tick,
        position: Pos2D | None = None,
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "system",
        cause_id: str | None = None,
        effects: dict = None,
        duration: int = 1,
        intensity: float = 1.0,
    ) -> Event:
        """Create a new event."""
        event_id = f"evt_{self.total_events}"
        event = Event(
            event_id=event_id,
            event_type=event_type,
            tick=tick,
            position=position,
            priority=priority,
            source=source,
            cause_id=cause_id,
            effects=effects or {},
            duration=duration,
            intensity=intensity,
        )

        self.events[event_id] = event
        self.total_events += 1

        # Update counts
        if event_type not in self.event_counts:
            self.event_counts[event_type] = 0
        self.event_counts[event_type] += 1

        return event

    def schedule_event(
        self,
        event: Event,
        trigger_tick: Tick,
        conditions: dict = None,
    ) -> ScheduledEvent:
        """Schedule an event for future execution."""
        scheduled = ScheduledEvent(
            event=event,
            trigger_tick=trigger_tick,
            conditions=conditions or {},
        )
        self.event_queue.append(scheduled)
        return scheduled

    def add_trigger(self, trigger: EventTrigger) -> None:
        """Add an event trigger."""
        self.triggers[trigger.trigger_id] = trigger

    def register_callback(
        self,
        event_type: EventType,
        callback: Callable[[Event], None],
    ) -> None:
        """Register a callback for an event type."""
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    def trigger_event(
        self,
        event_type: EventType,
        tick: Tick,
        position: Pos2D | None = None,
        cause_id: str | None = None,
        effects: dict = None,
        priority: EventPriority = EventPriority.NORMAL,
        intensity: float = 1.0,
    ) -> Event:
        """Trigger a new event."""
        event = self.create_event(
            event_type=event_type,
            tick=tick,
            position=position,
            priority=priority,
            cause_id=cause_id,
            effects=effects,
            intensity=intensity,
        )

        # Add to active events if immediate
        if priority in [EventPriority.CRITICAL, EventPriority.HIGH]:
            self.active_events.append(event.event_id)

        # Log event
        self.event_log.log(event)

        # Execute callbacks
        if event_type in self._callbacks:
            for callback in self._callbacks[event_type]:
                callback(event)

        # Handle cascade
        if self._cascade_depth < self._max_cascade_depth:
            self._handle_event_consequences(event, tick)

        return event

    def _handle_event_consequences(self, event: Event, tick: Tick) -> None:
        """Handle cascading consequences of an event."""
        self._cascade_depth += 1

        # Define consequence rules
        consequence_rules = {
            EventType.DISASTER: [
                (EventType.MIGRATION, {"radius": 10, "delay": 5}),
                (EventType.POPULATION_CRASH, {"delay": 3}),
                (EventType.RESOURCE_SCARCITY, {"delay": 10}),
            ],
            EventType.POPULATION_BOOM: [
                (EventType.RESOURCE_SCARCITY, {"delay": 20}),
                (EventType.CONFLICT, {"probability": 0.3}),
            ],
            EventType.CONFLICT: [
                (EventType.MIGRATION, {"probability": 0.5}),
                (EventType.BELIEF_SHIFT, {"probability": 0.2}),
            ],
            EventType.COOPERATION: [
                (EventType.TRADE_NETWORK, {"probability": 0.4}),
                (EventType.INSTITUTION_EMERGENCE, {"probability": 0.1}),
            ],
            EventType.RESOURCE_SCARCITY: [
                (EventType.CONFLICT, {"probability": 0.4}),
                (EventType.INNOVATION, {"probability": 0.2}),
                (EventType.MIGRATION, {"probability": 0.3}),
            ],
            EventType.INNOVATION: [
                (EventType.POPULATION_BOOM, {"probability": 0.3}),
                (EventType.TRADE_ROUTE, {"probability": 0.2}),
            ],
        }

        rules = consequence_rules.get(event.event_type, [])
        for consequence_type, params in rules:
            probability = params.get("probability", 1.0)
            if random.random() > probability:
                continue

            delay = params.get("delay", 0)
            new_tick = tick + delay

            self.trigger_event(
                event_type=consequence_type,
                tick=new_tick,
                position=event.position,
                cause_id=event.event_id,
                priority=EventPriority.NORMAL,
                intensity=event.intensity * 0.5,
            )

        self._cascade_depth -= 1

    def spawn_disaster_event(
        self,
        disaster_type: str,
        center: Pos2D,
        tick: Tick,
        intensity: float = 0.7,
        duration: int = 20,
    ) -> tuple[Event, Disaster]:
        """Spawn a disaster event."""
        # Create disaster
        disaster = self.disaster_system.spawn_disaster(
            disaster_type=disaster_type,
            center=center,
            radius=self._get_disaster_radius(disaster_type),
            intensity=intensity,
            duration=duration,
            tick=tick,
        )

        # Create event
        event = self.trigger_event(
            event_type=EventType.DISASTER,
            tick=tick,
            position=center,
            priority=EventPriority.HIGH,
            effects={
                "disaster_type": disaster_type,
                "affected_area": self.disaster_system.get_affected_area(disaster),
                "severity": self.disaster_system.get_disaster_severity_at(center),
            },
            intensity=intensity,
        )

        return event, disaster

    def _get_disaster_radius(self, disaster_type: str) -> int:
        """Get typical radius for a disaster type."""
        radii = {
            "flood": random.randint(3, 8),
            "drought": random.randint(10, 20),
            "earthquake": random.randint(2, 5),
            "wildfire": random.randint(5, 12),
            "plague": random.randint(8, 15),
        }
        return radii.get(disaster_type, 5)

    def check_triggers(self, tick: Tick, context: dict) -> list[Event]:
        """Check and fire any triggered events."""
        triggered_events = []

        for trigger in self.triggers.values():
            if not trigger.is_active:
                continue

            # Check cooldown
            if tick - trigger.last_triggered < trigger.cooldown:
                continue

            # Check conditions
            if self._check_trigger_conditions(trigger.conditions, context):
                trigger.last_triggered = tick

                # Create event
                event = self.trigger_event(
                    event_type=trigger.event_type,
                    tick=tick,
                    effects=trigger.effects,
                    priority=EventPriority.NORMAL,
                )
                triggered_events.append(event)

        return triggered_events

    def _check_trigger_conditions(self, conditions: dict, context: dict) -> bool:
        """Check if trigger conditions are met."""
        for key, value in conditions.items():
            context_value = context.get(key)
            if context_value is None:
                return False

            # Handle different comparison types
            if isinstance(value, dict):
                op = value.get("op", "eq")
                target = value.get("value")

                if op == "gt":
                    if not (context_value > target):
                        return False
                elif op == "lt":
                    if not (context_value < target):
                        return False
                elif op == "gte":
                    if not (context_value >= target):
                        return False
                elif op == "lte":
                    if not (context_value <= target):
                        return False
                else:  # eq
                    if context_value != target:
                        return False
            else:
                if context_value != value:
                    return False

        return True

    def process_scheduled_events(self, tick: Tick) -> list[Event]:
        """Process any scheduled events that are due."""
        due_events = []

        for scheduled in self.event_queue[:]:
            if tick >= scheduled.trigger_tick:
                # Check conditions
                if self._check_trigger_conditions(scheduled.conditions, {}):
                    self.event_queue.remove(scheduled)
                    due_events.append(scheduled.event)
                    self.trigger_event(
                        event_type=scheduled.event.event_type,
                        tick=tick,
                        position=scheduled.event.position,
                        cause_id=scheduled.event.cause_id,
                        effects=scheduled.event.effects,
                        priority=scheduled.event.priority,
                        intensity=scheduled.event.intensity,
                    )

        return due_events

    def update(self, tick: Tick, context: dict = None) -> dict:
        """Update the event simulation."""
        self.tick = tick
        context = context or {}

        results = {
            "events_triggered": 0,
            "disasters_active": len(self.disaster_system.active_disasters),
            "events_in_queue": len(self.event_queue),
        }

        # Process disaster system
        self.disaster_system.tick(tick)

        # Check triggers
        triggered = self.check_triggers(tick, context)
        results["events_triggered"] = len(triggered)

        # Process scheduled events
        self.process_scheduled_events(tick)

        # Update active events
        self._update_active_events(tick)

        return results

    def _update_active_events(self, tick: Tick) -> None:
        """Update status of active events."""
        for event_id in self.active_events[:]:
            event = self.events.get(event_id)
            if event and tick >= event.tick + event.duration:
                event.is_active = False
                self.active_events.remove(event_id)

    def get_events_in_area(self, center: Pos2D, radius: int) -> list[Event]:
        """Get all events in an area."""
        results = []
        for event in self.events.values():
            if event.position is None:
                continue
            dist = math.sqrt(
                (event.position.x - center.x) ** 2 +
                (event.position.y - center.y) ** 2
            )
            if dist <= radius:
                results.append(event)
        return results

    def get_event_history(
        self,
        event_type: EventType = None,
        tick_range: tuple[int, int] = None,
        source: str = None,
    ) -> list[Event]:
        """Get event history with filters."""
        results = []
        for event in self.events.values():
            if event_type and event.event_type != event_type:
                continue
            if tick_range:
                if event.tick < tick_range[0] or event.tick > tick_range[1]:
                    continue
            if source and event.source != source:
                continue
            results.append(event)
        return results

    def get_statistics(self) -> dict:
        """Get event system statistics."""
        return {
            "total_events": self.total_events,
            "active_events": len(self.active_events),
            "events_in_queue": len(self.event_queue),
            "disasters_active": len(self.disaster_system.active_disasters),
            "event_counts": {k.value: v for k, v in self.event_counts.items()},
            "triggered_triggers": sum(1 for t in self.triggers.values() if t.last_triggered > 0),
        }
