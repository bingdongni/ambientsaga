"""
Chronicle System - Historical recording, narrative generation, and causal chains.

Features:
- Event recording with rich context
- Narrative generation from events
- Causal chain tracking
- Historical analysis
- Cultural memory preservation

Academic value:
- Emergent narrative patterns
- Causal inference in social systems
- Cultural memory formation
- Historical contingency analysis

Engineering value:
- Efficient event storage
- Narrative generation algorithms
- Timeline reconstruction
"""

from __future__ import annotations

import random
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from collections import defaultdict
from enum import Enum
import time

if TYPE_CHECKING:
    from ambientsaga.agents.agent import Agent
    from ambientsaga.world.state import World


# ============================================================================
# Chronicle Types
# ============================================================================

class EventMagnitude(Enum):
    """How significant is an event."""
    TRIVIAL = 0.2       # Unremarkable daily occurrence
    MINOR = 0.4         # Small local event
    NOTABLE = 0.6       # Memorable local event
    SIGNIFICANT = 0.8   # Regional impact
    HISTORIC = 1.0      # World-changing


class NarrativeType(Enum):
    """Type of narrative generated."""
    EPIC = "epic"               # Heroic, grand
    TRAGEDY = "tragedy"         # Fall, loss
    COMEDY = "comedy"           # Light-hearted
    ROMANCE = "romance"         # Love, relationships
    CONFLICT = "conflict"       # War, dispute
    GROWTH = "growth"           # Development, success
    MYSTERY = "mystery"         # Unknown causes
    REVELATION = "revelation"   # Discovery
    REBIRTH = "rebirth"         # Renewal, return
    FALL = "fall"              # Decline, defeat


@dataclass
class ChronicleEvent:
    """
    A recorded event in history.

    Rich event representation for historical analysis and narrative generation.
    """
    event_id: str
    tick: int

    # Event classification
    category: str  # "social", "political", "economic", "natural", "cultural"
    subcategory: str  # "marriage", "war", "flood", "festival"
    magnitude: EventMagnitude = EventMagnitude.MINOR

    # Participants
    primary_agents: list[str] = field(default_factory=list)  # Main actors
    secondary_agents: list[str] = field(default_factory=list)  # Affected
    organizations: list[str] = field(default_factory=list)  # Groups involved
    location_x: int = 0
    location_y: int = 0

    # Event details
    title: str = ""
    description: str = ""
    outcome: str = ""  # What happened
    impact: dict = field(default_factory=dict)  # Effects

    # Cause and effect
    causes: list[str] = field(default_factory=list)  # event_ids
    effects: list[str] = field(default_factory=list)  # event_ids
    is_root_cause: bool = False

    # Narrative
    narrative_type: NarrativeType = NarrativeType.CONFLICT
    narrative_text: str = ""  # Generated narrative prose

    # Cultural memory
    remembered_by: list[str] = field(default_factory=list)  # agent IDs who know
    cultural_significance: float = 0.5  # How much it's remembered

    # Tags for search/filter
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "event_id": self.event_id,
            "tick": self.tick,
            "category": self.category,
            "subcategory": self.subcategory,
            "magnitude": self.magnitude.value,
            "title": self.title,
            "description": self.description,
            "outcome": self.outcome,
            "primary_agents": self.primary_agents,
            "narrative": self.narrative_text,
            "tags": self.tags,
        }


@dataclass
class ChronicleEntry:
    """
    A single entry in the chronicle (historical record).

    Compressed form of events for long-term storage.
    """
    tick: int
    entry_type: str  # "event", "milestone", "character_note"
    summary: str
    details: dict = field(default_factory=dict)


@dataclass
class HistoricalPeriod:
    """A historical period defined by major characteristics."""
    period_id: str
    name: str
    start_tick: int
    end_tick: int | None = None

    # Characteristics
    description: str = ""
    major_events: list[str] = field(default_factory=list)  # event_ids
    dominant_themes: list[str] = field(default_factory=list)

    # Key figures
    rulers: list[str] = field(default_factory=list)  # agent IDs

    # Population
    population_at_start: int = 0
    population_at_end: int = 0


@dataclass
class StoryArc:
    """A narrative story arc spanning multiple events."""
    arc_id: str
    title: str
    arc_type: NarrativeType

    # Events in this arc
    events: list[str] = field(default_factory=list)  # event_ids

    # Characters
    protagonists: list[str] = field(default_factory=list)
    antagonists: list[str] = field(default_factory=list)

    # Arc structure
    current_phase: str = "rising_action"  # rising, climax, falling, resolution
    tension: float = 0.0  # 0-1

    # Summary
    summary: str = ""
    lessons: list[str] = field(default_factory=list)


# ============================================================================
# Chronicle Manager
# ============================================================================

class Chronicle:
    """
    Manages historical records and narrative generation.

    Features:
    - Event recording with rich metadata
    - Causal chain linking
    - Narrative prose generation
    - Historical period detection
    - Story arc tracking
    - Cultural memory management
    """

    def __init__(self, world: World):
        self.world = world

        # Event storage
        self._events: dict[str, ChronicleEvent] = {}
        self._event_counter: int = 0

        # Chronicle (condensed history)
        self._entries: list[ChronicleEntry] = []

        # Periods
        self._periods: list[HistoricalPeriod] = []
        self._current_period: HistoricalPeriod | None = None

        # Story arcs
        self._story_arcs: dict[str, StoryArc] = {}

        # Narrative templates
        self._templates = self._build_narrative_templates()

        # Statistics
        self._category_counts: dict[str, int] = defaultdict(int)
        self._agent_event_count: dict[str, int] = defaultdict(int)

    def _build_narrative_templates(self) -> dict[str, list[str]]:
        """Build narrative generation templates."""
        return {
            "social.festival": [
                "The people gathered to celebrate {location}. {protagonist} led the festivities.",
                "Under the {season} sky, {location} came alive with {festival_type}. {protagonist} was at the heart of it all.",
                "A great {festival_type} drew people from across the land to {location}.",
            ],
            "social.marriage": [
                "{protagonist} and {antagonist} were joined in union, uniting two families.",
                "In a ceremony witnessed by many, {protagonist} and {antagonist} exchanged vows at {location}.",
                "The marriage of {protagonist} and {antagonist} was celebrated throughout {region}.",
            ],
            "social.birth": [
                "A new life entered the world as {parent} welcomed {child} into their family.",
                "The birth of {child} brought joy to {location}.",
                "{parent} named their newborn {child} under {season} skies.",
            ],
            "social.death": [
                "{protagonist} passed from this world, leaving {location} in mourning.",
                "Death claimed {protagonist} at {location}. Their memory lives on.",
                "The passing of {protagonist} was mourned by all who knew them.",
            ],
            "social.meeting": [
                "{protagonist} encountered {antagonist} at {location}. Neither would forget the meeting.",
                "A fateful encounter between {protagonist} and {antagonist} occurred at {location}.",
                "{protagonist} met {antagonist} under the {season} moon at {location}.",
            ],
            "political.war": [
                "War erupted between {protagonist} and {antagonist}. The flames of conflict consumed the land.",
                "The armies of {protagonist} clashed with those of {antagonist} in a brutal conflict.",
                "Conflict swept through {region} as {protagonist} and {antagonist} waged war.",
            ],
            "political.election": [
                "{protagonist} was chosen by the people to lead at {location}.",
                "The people of {location} elected {protagonist} to positions of authority.",
                "A new era began as {protagonist} took the reins of power at {location}.",
            ],
            "political.revolt": [
                "The people rose up against {protagonist} in revolt at {location}.",
                "Revolution swept through {location} as {antagonist} led the rebellion.",
                "Discontent boiled over into revolt. {protagonist} faced the fury of the masses.",
            ],
            "political.law": [
                "A new law was proclaimed by {protagonist} at {location}.",
                "{protagonist} enacted {law_name} as law of the land.",
                "The decree of {protagonist} changed forever how {region} would be governed.",
            ],
            "economic.trade": [
                "A great trade was made between {protagonist} and {antagonist} at {location}.",
                "Commerce flourished as {protagonist} and {antagonist} exchanged {good} at {location}.",
                "The markets of {location} buzzed with activity as {protagonist} conducted trade.",
            ],
            "economic.famine": [
                "Famine struck {location}, bringing suffering to its people.",
                "Crop failures brought hunger to {location}. {protagonist} struggled to feed the people.",
                "The famine of {location} tested the resolve of all who lived there.",
            ],
            "economic.prosperity": [
                "Times of prosperity came to {location}. The people prospered under {protagonist}'s guidance.",
                "Wealth flowed into {location}, transforming it into a center of commerce.",
                "The people of {location} enjoyed unprecedented prosperity.",
            ],
            "natural.flood": [
                "Waters rose and flooded {location}, reshaping the land.",
                "The great flood of {location} brought devastation and change.",
                "Rivers burst their banks at {location}, inundating the surrounding area.",
            ],
            "natural.drought": [
                "Drought gripped {location}. The land cracked and withered.",
                "No rain fell on {location} for so long. Desperation took hold.",
                "The great drought of {location} forced many to leave their homes.",
            ],
            "natural.earthquake": [
                "The earth shook at {location}, toppling buildings and shattering lives.",
                "A great tremor struck {location}, changing the landscape forever.",
                "The earthquake that struck {location} left nothing untouched.",
            ],
            "natural.plague": [
                "A sickness swept through {location}, claiming many lives.",
                "Disease ravaged {location}. {protagonist} was among those affected.",
                "The plague that swept {location} would be remembered for generations.",
            ],
            "natural.fire": [
                "Fire consumed {location}, leaving ash and ruin in its wake.",
                "Flames devoured {location}. Many lost their homes.",
                "A great conflagration at {location} changed the face of the region.",
            ],
            "cultural.ritual": [
                "The people of {location} gathered for the ancient ritual of {ritual_name}.",
                "{protagonist} led the sacred {ritual_name} ceremony at {location}.",
                "The {ritual_name} ritual at {location} was performed as generations before had done.",
            ],
            "cultural.story": [
                "The tale of {protagonist} was told and retold across {region}.",
                "A new story emerged from {location}: {story_summary}",
                "{protagonist} became the subject of legend in {region}.",
            ],
            "cultural.found": [
                "A new {organization_type} was founded at {location} by {protagonist}.",
                "{protagonist} established the {organization_type} that would shape {region}.",
                "The founding of {organization_type} at {location} marked a new chapter in history.",
            ],
        }

    def record_event(
        self,
        category: str,
        subcategory: str,
        title: str,
        description: str,
        outcome: str = "",
        primary_agents: list[str] | None = None,
        secondary_agents: list[str] | None = None,
        organizations: list[str] | None = None,
        location_x: int = 0,
        location_y: int = 0,
        magnitude: EventMagnitude = EventMagnitude.MINOR,
        impact: dict | None = None,
        tags: list[str] | None = None,
    ) -> ChronicleEvent:
        """Record a significant event in history."""
        self._event_counter += 1
        event_id = f"event_{self._event_counter:06d}"

        # Determine narrative type
        narrative_type = self._infer_narrative_type(category, subcategory, outcome)

        # Generate narrative text
        narrative = self._generate_narrative(
            category, subcategory, title, description, outcome,
            primary_agents or [], organizations or [],
            location_x, location_y,
        )

        event = ChronicleEvent(
            event_id=event_id,
            tick=self.world.tick,
            category=category,
            subcategory=subcategory,
            magnitude=magnitude,
            primary_agents=primary_agents or [],
            secondary_agents=secondary_agents or [],
            organizations=organizations or [],
            location_x=location_x,
            location_y=location_y,
            title=title,
            description=description,
            outcome=outcome,
            impact=impact or {},
            narrative_type=narrative_type,
            narrative_text=narrative,
            tags=tags or [],
        )

        self._events[event_id] = event

        # Update statistics
        self._category_counts[category] += 1
        for agent_id in (primary_agents or []):
            self._agent_event_count[agent_id] += 1

        # Add to chronicle entry
        self._entries.append(ChronicleEntry(
            tick=self.world.tick,
            entry_type="event",
            summary=title,
            details={
                "event_id": event_id,
                "category": category,
                "subcategory": subcategory,
                "magnitude": magnitude.value,
            },
        ))

        # Link to causes (if any)
        self._link_causes(event)

        # Add to story arc if relevant
        self._update_story_arcs(event)

        # Update period
        self._update_period(event)

        return event

    def _infer_narrative_type(
        self,
        category: str,
        subcategory: str,
        outcome: str,
    ) -> NarrativeType:
        """Infer narrative type from event."""
        if subcategory in ("war", "conflict", "revolt"):
            return NarrativeType.CONFLICT
        elif subcategory in ("death", "defeat", "destruction"):
            return NarrativeType.TRAGEDY
        elif subcategory in ("birth", "victory", "festival", "marriage"):
            return NarrativeType.GROWTH
        elif subcategory in ("discovery", "revelation"):
            return NarrativeType.REVELATION
        elif subcategory in ("plague", "famine", "drought"):
            return NarrativeType.TRAGEDY
        elif subcategory in ("rebirth", "reformation"):
            return NarrativeType.REBIRTH
        else:
            return NarrativeType.CONFLICT

    def _generate_narrative(
        self,
        category: str,
        subcategory: str,
        title: str,
        description: str,
        outcome: str,
        primary_agents: list[str],
        organizations: list[str],
        location_x: int,
        location_y: int,
    ) -> str:
        """Generate narrative prose from event."""
        template_key = f"{category}.{subcategory}"

        # Get location name
        location_name = f"coordinates ({location_x}, {location_y})"
        region_name = f"region of ({location_x // 50}, {location_y // 50})"

        # Get agent names
        protagonist = primary_agents[0] if primary_agents else "Unknown"
        antagonist = primary_agents[1] if len(primary_agents) > 1 else "Unknown"

        # Get organization type
        org_type = organizations[0] if organizations else "organization"

        # Get template
        templates = self._templates.get(template_key, self._templates.get(f"{category}.default", [
            "Events at {location} involving {protagonist} shaped the course of history."
        ]))

        template = random.choice(templates)

        # Fill template
        narrative = template.format(
            protagonist=protagonist,
            antagonist=antagonist,
            location=location_name,
            region=region_name,
            season=self.world.season,
            festival_type=subcategory,
            law_name=title,
            good=subcategory,
            parent=protagonist,
            child=antagonist,
            organization_type=org_type,
            ritual_name=subcategory,
            story_summary=description[:50],
        )

        # Add outcome if provided
        if outcome:
            narrative += f" {outcome}"

        return narrative

    def _link_causes(self, event: ChronicleEvent) -> None:
        """Link event to its causes (previous events)."""
        # Look for recent events that might have caused this
        recent_events = [
            e for e in self._events.values()
            if 0 < self.world.tick - e.tick < 50  # Within last 50 ticks
            and e.event_id != event.event_id
        ]

        # Simple heuristic: link to most recent event of same category
        same_category = [
            e for e in recent_events
            if e.category == event.category
        ]

        if same_category and event.magnitude.value >= 0.6:
            cause = max(same_category, key=lambda e: e.tick)
            event.causes.append(cause.event_id)
            cause.effects.append(event.event_id)

            # Mark if this is a chain reaction
            if len(cause.effects) > 3:
                event.is_root_cause = False

    def _update_story_arcs(self, event: ChronicleEvent) -> None:
        """Update ongoing story arcs with this event."""
        if event.magnitude.value < 0.5:
            return

        # Find relevant arc or create new one
        arc_key = f"{event.category}_{event.primary_agents[0] if event.primary_agents else 'unknown'}"

        if arc_key not in self._story_arcs:
            self._story_arcs[arc_key] = StoryArc(
                arc_id=arc_key,
                title=f"The saga of {event.primary_agents[0] if event.primary_agents else 'an unknown figure'}",
                arc_type=event.narrative_type,
                protagonists=event.primary_agents[:3],
            )

        arc = self._story_arcs[arc_key]
        arc.events.append(event.event_id)

        # Update tension
        if event.subcategory in ("war", "revolt", "plague", "disaster"):
            arc.tension = min(1.0, arc.tension + 0.2)
        elif event.subcategory in ("peace", "victory", "festival"):
            arc.tension = max(0.0, arc.tension - 0.15)

    def _update_period(self, event: ChronicleEvent) -> None:
        """Update or create historical periods."""
        # Determine period based on major events
        if event.magnitude == EventMagnitude.HISTORIC:
            # Create new period
            if self._current_period:
                self._current_period.end_tick = event.tick

            self._current_period = HistoricalPeriod(
                period_id=f"period_{len(self._periods)}",
                name=f"The Age of {event.title}",
                start_tick=event.tick,
                major_events=[event.event_id],
            )
            self._periods.append(self._current_period)

        elif self._current_period:
            self._current_period.major_events.append(event.event_id)

    def get_event(self, event_id: str) -> ChronicleEvent | None:
        """Get an event by ID."""
        return self._events.get(event_id)

    def get_events_in_period(
        self,
        start_tick: int,
        end_tick: int | None = None,
    ) -> list[ChronicleEvent]:
        """Get all events in a time period."""
        end = end_tick if end_tick is not None else self.world.tick
        return [
            e for e in self._events.values()
            if start_tick <= e.tick <= end
        ]

    def get_events_by_agent(
        self,
        agent_id: str,
        limit: int = 20,
    ) -> list[ChronicleEvent]:
        """Get events involving an agent."""
        events = [
            e for e in self._events.values()
            if agent_id in e.primary_agents or agent_id in e.secondary_agents
        ]
        events.sort(key=lambda e: e.tick, reverse=True)
        return events[:limit]

    def get_events_by_category(
        self,
        category: str,
        limit: int = 20,
    ) -> list[ChronicleEvent]:
        """Get events by category."""
        events = [e for e in self._events.values() if e.category == category]
        events.sort(key=lambda e: e.tick, reverse=True)
        return events[:limit]

    def get_causal_chain(
        self,
        event_id: str,
        depth: int = 3,
    ) -> list[ChronicleEvent]:
        """Get the causal chain leading to an event."""
        chain = []
        visited = {event_id}

        def traverse(eid: str, d: int):
            if d <= 0:
                return
            event = self._events.get(eid)
            if not event:
                return
            for cause_id in event.causes:
                if cause_id not in visited:
                    visited.add(cause_id)
                    cause = self._events.get(cause_id)
                    if cause:
                        chain.append(cause)
                        traverse(cause_id, d - 1)

        traverse(event_id, depth)
        chain.sort(key=lambda e: e.tick)
        return chain

    def get_recent_history(
        self,
        ticks: int = 100,
    ) -> list[ChronicleEvent]:
        """Get recent events."""
        cutoff = self.world.tick - ticks
        events = [e for e in self._events.values() if e.tick >= cutoff]
        events.sort(key=lambda e: e.tick, reverse=True)
        return events

    def generate_world_history(
        self,
        max_events: int = 50,
    ) -> str:
        """Generate a narrative history of the world."""
        if not self._events:
            return "In the beginning, there was only the world..."

        # Get most significant events
        significant = sorted(
            self._events.values(),
            key=lambda e: e.magnitude.value + len(e.primary_agents) * 0.1,
            reverse=True,
        )[:max_events]

        significant.sort(key=lambda e: e.tick)

        lines = ["=== THE CHRONICLES OF THIS WORLD ===\n"]

        for event in significant:
            lines.append(f"\n[Year {event.tick // 100}, {event.title}]")
            lines.append(f"{event.narrative_text}")

        return "\n".join(lines)

    def get_agent_legacy(self, agent_id: str) -> dict:
        """Get the historical legacy of an agent."""
        events = self.get_events_by_agent(agent_id)

        if not events:
            return {"status": "unknown", "events": 0}

        # Analyze the agent's history
        categories = defaultdict(int)
        for e in events:
            categories[e.category] += 1

        # Find most significant event
        most_significant = max(events, key=lambda e: e.magnitude.value)

        return {
            "agent_id": agent_id,
            "total_events": len(events),
            "categories": dict(categories),
            "first_event_tick": events[-1].tick if events else 0,
            "last_event_tick": events[0].tick if events else 0,
            "most_significant": {
                "tick": most_significant.tick,
                "title": most_significant.title,
                "magnitude": most_significant.magnitude.value,
            },
            "summary": f"{agent_id} appears in {len(events)} historical events, primarily involved in {max(categories, key=categories.get)}.",
        }

    def get_summary(self) -> dict:
        """Get chronicle summary."""
        return {
            "total_events": len(self._events),
            "category_counts": dict(self._category_counts),
            "periods": len(self._periods),
            "story_arcs": len(self._story_arcs),
            "chronicle_entries": len(self._entries),
            "recent_significant": [
                {
                    "tick": e.tick,
                    "title": e.title,
                    "magnitude": e.magnitude.value,
                }
                for e in sorted(
                    self._events.values(),
                    key=lambda e: (e.magnitude.value, e.tick),
                    reverse=True,
                )[:5]
            ],
        }
