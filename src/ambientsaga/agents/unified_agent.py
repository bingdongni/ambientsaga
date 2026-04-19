"""
Unified Agent System - Complete Agent Implementation

This module provides a unified Agent class that combines:
- Profile-based identity and attributes
- Direct state management (health, energy, hunger, etc.)
- Multi-layered memory system
- Async decision-making (rule-based, LLM, or hybrid)
- Full integration with the simulation world

Architecture:
- Agent: Core dataclass with all agent state
- AgentProfile: Identity and static attributes
- AgentMemory: Multi-layered memory system
- DecisionSystem: Action selection and execution
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from ambientsaga.types import (
    Belief,
    Decision,
    DecisionType,
    EntityID,
    Inventory,
    Pos2D,
    Relationship,
    ResourceType,
    Signal,
    Tick,
)

# =============================================================================
# Agent Tier
# =============================================================================

class AgentTier(Enum):
    """Agent processing tier - determines how agent decisions are made."""
    L1_CORE = "l1_core"          # Full LLM reasoning, few agents
    L2_FUNCTIONAL = "l2_functional"  # Hybrid: embedding + occasional LLM
    L3_BACKGROUND = "l3_background"  # Rule-based, most agents


class AgentState(Enum):
    """Current state of an agent."""
    ALIVE = "alive"
    DEAD = "dead"
    SLEEPING = "sleeping"
    TRAVELING = "traveling"
    WORKING = "working"
    SOCIALIZING = "socializing"
    CELEBRATING = "celebrating"
    MOURNING = "mourning"


# =============================================================================
# Memory System
# =============================================================================

@dataclass
class MemoryEntry:
    """A single memory entry."""
    tick: Tick
    content: str
    memory_type: str  # "episodic", "semantic", "procedural"
    emotional_valence: float = 0.0  # -1 (negative) to +1 (positive)
    importance: float = 0.5  # 0-1, how memorable
    location: Pos2D | None = None
    entities_involved: list[EntityID] = field(default_factory=list)
    vividness: float = 1.0  # 0-1, fades over time

    def decay(self, factor: float = 0.01) -> None:
        """Apply memory decay."""
        self.vividness = max(0, self.vividness - factor)
        self.importance = max(0, self.importance - factor * 0.5)


@dataclass
class AgentMemory:
    """
    Multi-layered memory system for agents.
    Simulates the way humans store and retrieve memories.
    """
    episodic: list[MemoryEntry] = field(default_factory=list)
    semantic: list[MemoryEntry] = field(default_factory=list)
    procedural: list[MemoryEntry] = field(default_factory=list)
    emotional_tags: dict[str, float] = field(default_factory=dict)

    max_episodic: int = 500
    max_semantic: int = 1000
    max_procedural: int = 200

    def add_memory(self, entry: MemoryEntry) -> None:
        """Add a memory entry."""
        if entry.memory_type == "episodic":
            self.episodic.append(entry)
            if len(self.episodic) > self.max_episodic:
                self._consolidate_episodic()
        elif entry.memory_type == "semantic":
            self.semantic.append(entry)
            if len(self.semantic) > self.max_semantic:
                self.semantic = self.semantic[-self.max_semantic:]
        elif entry.memory_type == "procedural":
            self.procedural.append(entry)
            if len(self.procedural) > self.max_procedural:
                self.procedural = self.procedural[-self.max_procedural:]

    def _consolidate_episodic(self) -> None:
        """Consolidate episodic memories - keep important ones, compress others."""
        scored = sorted(
            self.episodic,
            key=lambda m: m.vividness * m.importance,
            reverse=True
        )
        self.episodic = scored[:self.max_episodic // 2]
        for entry in scored[self.max_episodic // 2:]:
            entry.content = f"[Memory fragment] {entry.content[:50]}..."
            entry.vividness *= 0.3
            self.episodic.append(entry)

    def decay_memories(self, tick: Tick) -> None:
        """Apply time-based decay to all memories."""
        for entry in self.episodic:
            entry.decay()
        self.episodic = [m for m in self.episodic if m.vividness > 0.05]
        self.semantic = [m for m in self.semantic if m.importance > 0.05]

    def recall_recent(self, count: int = 10) -> list[MemoryEntry]:
        """Recall recent episodic memories."""
        return sorted(self.episodic, key=lambda m: m.tick, reverse=True)[:count]

    def recall_emotional(self, valence_threshold: float = 0.5) -> list[MemoryEntry]:
        """Recall emotionally significant memories."""
        return [
            m for m in self.episodic
            if abs(m.emotional_valence) >= valence_threshold
        ]

    def get_fragments(self, count: int = 5) -> list[str]:
        """Get fragmented memory snippets."""
        fragments = [m for m in self.episodic if 0.1 < m.vividness < 0.4]
        if len(fragments) < count:
            fragments = [m for m in self.episodic if m.vividness < 0.6]
        fragments = sorted(fragments, key=lambda m: m.tick, reverse=True)
        return [f"[{m.tick}] ...{m.content}..." for m in fragments[:count]]


# =============================================================================
# Profile and Traits
# =============================================================================

@dataclass
class MoralCharacter:
    """
    Moral character traits that influence agent behavior.
    These traits determine how agents interact ethically with others.
    """
    # Core moral traits
    honesty: float = 0.5          # 0-1: deceptive -> truthful
    empathy: float = 0.5           # 0-1: callous -> empathetic
    altruism: float = 0.5         # 0-1: selfish -> altruistic
    greed: float = 0.5            # 0-1: generous -> greedy
    loyalty: float = 0.5          # 0-1: disloyal -> loyal
    justice: float = 0.5          # 0-1: unfair -> fair
    courage: float = 0.5          # 0-1: cowardly -> brave
    temperance: float = 0.5       # 0-1: impulsive -> temperate

    # Social traits
    hospitality: float = 0.5      # 0-1: inhospitable -> hospitable
    humility: float = 0.5         # 0-1: arrogant -> humble
    forgiveness: float = 0.5       # 0-1: vengeful -> forgiving
    compassion: float = 0.5        # 0-1: cruel -> compassionate

    # Economic traits
    work_ethic: float = 0.5       # 0-1: lazy -> industrious
    thriftiness: float = 0.5      # 0-1: wasteful -> thrifty
    ambition: float = 0.5          # 0-1: content -> ambitious

    def to_dict(self) -> dict[str, float]:
        return {
            "honesty": self.honesty,
            "empathy": self.empathy,
            "altruism": self.altruism,
            "greed": self.greed,
            "loyalty": self.loyalty,
            "justice": self.justice,
            "courage": self.courage,
            "temperance": self.temperance,
            "hospitality": self.hospitality,
            "humility": self.humility,
            "forgiveness": self.forgiveness,
            "compassion": self.compassion,
            "work_ethic": self.work_ethic,
            "thriftiness": self.thriftiness,
            "ambition": self.ambition,
        }

    def get_moral_score(self) -> float:
        """Get overall moral score (higher = more moral)."""
        return (
            self.honesty +
            self.empathy +
            self.altruism +
            (1 - self.greed) +
            self.loyalty +
            self.justice +
            self.courage +
            self.temperance +
            self.hospitality +
            (1 - self.humility) +  # Invert humility (arrogant is worse)
            self.forgiveness +
            self.compassion +
            self.work_ethic +
            self.thriftiness +
            self.ambition
        ) / 15.0

    def will_help(self, target_need: float) -> bool:
        """Decide if this moral character will help based on empathy and altruism."""
        return self.empathy > 0.4 and self.altruism > 0.3

    def will_trade_fairly(self) -> bool:
        """Decide if this moral character will trade fairly."""
        return self.honesty > 0.4 and self.justice > 0.4

    def will_keep_promise(self, trust_level: float) -> bool:
        """Decide if this moral character will keep a promise."""
        return self.loyalty > trust_level


@dataclass
class CulturalBackground:
    """
    Cultural background of an agent.
    This includes ethnicity, nationality, religion, and cultural values.
    """
    ethnicity: str = "unknown"
    nationality: str = "unknown"
    religion: str = "none"
    tribe: str = ""
    clan: str = ""

    # Cultural values (higher = more important)
    value_individualism: float = 0.5    # 0 = collectivist, 1 = individualist
    value_equality: float = 0.5        # 0 = hierarchical, 1 = egalitarian
    value_tradition: float = 0.5      # 0 = progressive, 1 = traditional
    value_competition: float = 0.5    # 0 = cooperative, 1 = competitive
    value_materialism: float = 0.5   # 0 = spiritual, 1 = materialist
    value_nature: float = 0.5         # 0 = mastery over nature, 1 = harmony with nature

    # Cultural practices
    practices: list[str] = field(default_factory=list)  # rituals, customs
    taboos: list[str] = field(default_factory=list)     # forbidden actions
    preferred_foods: list[str] = field(default_factory=list)
    art_style: str = "none"

    # Social structure
    preferred_social_structure: str = " egalitarian"  # egalitarian, hierarchical, authoritarian
    gender_roles: str = "equal"  # equal, patriarchal, matriarchal

    def to_dict(self) -> dict[str, Any]:
        return {
            "ethnicity": self.ethnicity,
            "nationality": self.nationality,
            "religion": self.religion,
            "tribe": self.tribe,
            "clan": self.clan,
            "value_individualism": self.value_individualism,
            "value_equality": self.value_equality,
            "value_tradition": self.value_tradition,
            "value_competition": self.value_competition,
            "value_materialism": self.value_materialism,
            "value_nature": self.value_nature,
            "preferred_social_structure": self.preferred_social_structure,
            "gender_roles": self.gender_roles,
        }

    def cultural_distance(self, other: CulturalBackground) -> float:
        """Calculate cultural distance between two agents (0-1)."""
        if self.ethnicity == other.ethnicity and self.ethnicity != "unknown":
            return 0.0
        if self.religion != other.religion and self.religion != "none" and other.religion != "none":
            return 0.3
        if self.tribe and self.tribe == other.tribe:
            return 0.1

        # Value differences
        value_diff = (
            abs(self.value_individualism - other.value_individualism) +
            abs(self.value_equality - other.value_equality) +
            abs(self.value_tradition - other.value_tradition) +
            abs(self.value_competition - other.value_competition) +
            abs(self.value_materialism - other.value_materialism) +
            abs(self.value_nature - other.value_nature)
        ) / 6.0
        return value_diff


@dataclass
class GeneticTraits:
    """
    Genetic traits inherited from parents.
    These provide a biological foundation for agent characteristics.
    """
    # Physical traits
    height: float = 0.5        # 0 = short, 1 = tall
    strength: float = 0.5       # 0 = weak, 1 = strong
    intelligence: float = 0.5    # 0 = low, 1 = high
    health: float = 0.8        # 0 = frail, 1 = robust
    fertility: float = 0.5     # 0 = infertile, 1 = fertile
    lifespan_potential: float = 0.5  # 0 = short-lived, 1 = long-lived

    # Cognitive traits
    memory_capacity: float = 0.5
    learning_speed: float = 0.5
    creativity: float = 0.5
    perception: float = 0.5

    # Temperament
    aggression: float = 0.3      # 0 = peaceful, 1 = aggressive
    anxiety: float = 0.3       # 0 = calm, 1 = anxious
    sociability: float = 0.5   # 0 = introverted, 1 = extroverted

    # Special traits
    adaptations: list[str] = field(default_factory=list)  # disease resistance, etc.
    disabilities: list[str] = field(default_factory=list)  # inherited conditions

    def to_dict(self) -> dict[str, Any]:
        return {
            "height": self.height,
            "strength": self.strength,
            "intelligence": self.intelligence,
            "health": self.health,
            "fertility": self.fertility,
            "lifespan_potential": self.lifespan_potential,
            "memory_capacity": self.memory_capacity,
            "learning_speed": self.learning_speed,
            "creativity": self.creativity,
            "perception": self.perception,
            "aggression": self.aggression,
            "anxiety": self.anxiety,
            "sociability": self.sociability,
            "adaptations": self.adaptations,
            "disabilities": self.disabilities,
        }

    def get_fitness(self) -> float:
        """Calculate overall genetic fitness (0-1)."""
        return (
            self.health * 0.3 +
            self.strength * 0.1 +
            self.intelligence * 0.2 +
            self.fertility * 0.1 +
            (1 - self.aggression) * 0.15 +
            (1 - self.anxiety) * 0.1 +
            self.sociability * 0.05
        )


@dataclass
class PersonalityTraits:
    """Big Five personality traits plus additional dimensions."""
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5
    dominance: float = 0.5
    religiosity: float = 0.5
    materialism: float = 0.5
    risk_tolerance: float = 0.5
    patience: float = 0.5

    def to_dict(self) -> dict[str, float]:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
            "dominance": self.dominance,
            "religiosity": self.religiosity,
            "materialism": self.materialism,
            "risk_tolerance": self.risk_tolerance,
            "patience": self.patience,
        }


@dataclass
class AgentProfile:
    """Complete profile of an agent with full diversity."""
    agent_id: EntityID
    name: str
    age: int = 25
    gender: str = "unknown"
    tier: AgentTier = AgentTier.L3_BACKGROUND

    # Identity and background
    position: Pos2D = field(default_factory=lambda: Pos2D(0, 0))
    home_position: Pos2D = field(default_factory=lambda: Pos2D(0, 0))

    # Psychological traits
    personality: PersonalityTraits = field(default_factory=PersonalityTraits)
    moral_character: MoralCharacter = field(default_factory=MoralCharacter)
    genetic_traits: GeneticTraits = field(default_factory=GeneticTraits)

    # Cultural background
    cultural_background: CulturalBackground = field(default_factory=CulturalBackground)

    # Skills and abilities
    skills: dict[str, float] = field(default_factory=lambda: {
        "gathering": 0.3, "crafting": 0.3, "social": 0.3,
        "combat": 0.1, "exploration": 0.3, "leadership": 0.1,
        "teaching": 0.1, "healing": 0.1, "trading": 0.2,
    })

    # Relationships and status
    relationships: dict[EntityID, float] = field(default_factory=dict)  # agent_id -> trust
    reputation: float = 0.5
    title: str = ""
    known_for: list[str] = field(default_factory=list)

    # Belonging
    group_id: str = ""           # Current group (tribe, nation, etc.)
    faction_id: str = ""         # Political faction
    alliance_ids: list[str] = field(default_factory=list)  # Allied groups

    # Beliefs and values
    beliefs: list[str] = field(default_factory=list)
    values: list[str] = field(default_factory=list)

    # Basic needs (Maslow)
    needs: dict[str, float] = field(default_factory=lambda: {
        "physiological": 0.7, "safety": 0.7, "belonging": 0.7,
        "esteem": 0.7, "self_actualization": 0.5,
    })

    # Lifecycle
    birth_tick: Tick = 0
    last_action_tick: Tick = 0

    # Legacy and achievements
    achievements: list[str] = field(default_factory=list)
    crimes: list[str] = field(default_factory=list)

    def apply_needs_decay(self) -> None:
        """Apply basic needs decay over time."""
        self.needs["physiological"] = max(0, self.needs["physiological"] - 0.01)
        self.needs["safety"] = max(0, self.needs["safety"] - 0.005)
        self.needs["belonging"] = max(0, self.needs["belonging"] - 0.003)
        self.needs["esteem"] = max(0, self.needs["esteem"] - 0.002)
        self.needs["self_actualization"] = max(0, self.needs["self_actualization"] - 0.001)

    def get_dominant_need(self) -> str:
        """Get the most urgent unsatisfied need."""
        urgent = [(v, k) for k, v in self.needs.items() if v < 0.6]
        if urgent:
            urgent.sort()
            return urgent[0][1]
        return "self_actualization"

    def get_cultural_identity(self) -> str:
        """Get a short cultural identity string."""
        parts = []
        if self.cultural_background.ethnicity != "unknown":
            parts.append(self.cultural_background.ethnicity)
        if self.cultural_background.tribe:
            parts.append(self.cultural_background.tribe)
        if self.cultural_background.religion != "none":
            parts.append(self.cultural_background.religion)
        return "/".join(parts) if parts else "unknown"


class DiversitySystem:
    """
    System for generating diverse agents with unique traits.
    This system creates emergent diversity based on cultural backgrounds,
    genetic variations, and personality distributions.
    """

    # Cultural templates for different ethnicities/regions
    CULTURAL_TEMPLATES = {
        "nomadic": CulturalBackground(
            ethnicity="nomad",
            religion="animism",
            value_tradition=0.7,
            value_individualism=0.3,
            value_equality=0.6,
            practices=["wander", "storytelling", "hospitality"],
            preferred_social_structure=" egalitarian",
        ),
        "agricultural": CulturalBackground(
            ethnicity="farmer",
            religion="earth_worship",
            value_tradition=0.8,
            value_individualism=0.2,
            value_equality=0.7,
            practices=["harvest_ritual", "communal_work", "ancestor_veneration"],
            preferred_social_structure=" hierarchical",
        ),
        "maritime": CulturalBackground(
            ethnicity="sailor",
            religion="sea_god",
            value_tradition=0.5,
            value_individualism=0.6,
            value_equality=0.4,
            practices=["navigation", "trade", "fish_ritual"],
            preferred_social_structure=" egalitarian",
        ),
        "tribal": CulturalBackground(
            ethnicity="tribesman",
            religion="totemism",
            value_tradition=0.9,
            value_individualism=0.1,
            value_equality=0.8,
            practices=["initiation", "totem_ceremony", "hunting_ritual"],
            preferred_social_structure=" egalitarian",
            gender_roles="equal",
        ),
        "civilized": CulturalBackground(
            ethnicity="citizen",
            religion="pantheon",
            value_tradition=0.4,
            value_individualism=0.7,
            value_equality=0.3,
            practices=["philosophy", "art", "architecture"],
            preferred_social_structure=" hierarchical",
        ),
    }

    # Name generators by ethnicity
    NAME_TEMPLATES = {
        "nomad": {
            "first": ["Akil", "Bora", "Cira", "Duna", "Eren", "Fera", "Gala", "Hana", "Ira", "Jara"],
            "last": ["Windwalker", "Starchaser", "Dune Rider", "Sky Keeper", "Fire Dancer"],
        },
        "farmer": {
            "first": ["Ana", "Bo", "Cai", "Dan", "Eva", "Fen", "Greta", "Hans", "Ida", "Jonas"],
            "last": ["Earthsong", "Fieldkeeper", "Harvestmaker", "Plowsharer", "Seedsower"],
        },
        "sailor": {
            "first": ["Mar", "Nere", "Ora", "Pel", "Ria", "Sal", "Tide", "Wav", "Zea", "Cor"],
            "last": ["Stormborn", "Tidesinger", "Anchorheart", "Deckrunner", "Chartmaker"],
        },
        "tribal": {
            "first": ["Ash", "Birch", "Cedar", "Dawn", "Eagle", "Fern", "Ghost", "Hawk", "Ice", "Jade"],
            "last": ["Wolfclaw", "Bearheart", "Elkrunner", "Falconeye", "Oaktongue"],
        },
        "citizen": {
            "first": ["Marcus", "Livia", "Gaius", "Diana", "Quintus", "Aurelia", "Titus", "Lucia", "Decimus", "Fabia"],
            "last": ["Maximus", "Sapiens", "Patricius", "Novus", "Optimus"],
        },
        "default": {
            "first": ["Alex", "Morgan", "Casey", "Jordan", "Taylor", "Riley", "Quinn", "Avery", "Parker", "Sage"],
            "last": ["Walker", "Hunter", "Smith", "Fisher", "Carpenter"],
        },
    }

    RELIGIONS = [
        "none", "monotheism", "polytheism", "animism", "totemism",
        " ancestor_worship", "sun_worship", "earth_worship", "sea_god",
    ]

    @classmethod
    def generate_culture(cls, rng: Any = None) -> CulturalBackground:
        """Generate a random cultural background."""
        if rng is None:
            import random
            rng = random

        template_name = rng.choice(list(cls.CULTURAL_TEMPLATES.keys()))
        template = cls.CULTURAL_TEMPLATES[template_name]

        # Create variation of the template
        culture = CulturalBackground(
            ethnicity=template.ethnicity,
            religion=template.religion if rng.random() > 0.3 else rng.choice(cls.RELIGIONS),
            value_individualism=template.value_individualism + rng.uniform(-0.1, 0.1),
            value_equality=template.value_equality + rng.uniform(-0.1, 0.1),
            value_tradition=template.value_tradition + rng.uniform(-0.1, 0.1),
            value_competition=template.value_competition + rng.uniform(-0.1, 0.1),
            value_materialism=template.value_materialism + rng.uniform(-0.1, 0.1),
            value_nature=template.value_nature + rng.uniform(-0.1, 0.1),
            practices=template.practices.copy() if rng.random() > 0.2 else [],
            preferred_social_structure=template.preferred_social_structure,
            gender_roles=template.gender_roles,
        )

        # Clamp values
        for attr in ["value_individualism", "value_equality", "value_tradition",
                      "value_competition", "value_materialism", "value_nature"]:
            setattr(culture, attr, max(0.0, min(1.0, getattr(culture, attr))))

        return culture

    @classmethod
    def _make_gauss_fn(cls, rng):
        """Create a gaussian function compatible with both random and numpy Generator."""
        if hasattr(rng, 'gauss'):
            return lambda m, s: rng.gauss(m, s)
        elif hasattr(rng, 'normal'):
            return lambda m, s: rng.normal(m, s)
        else:
            return lambda m, s: rng.normalvariate(m, s)

    @classmethod
    def generate_genetic_traits(cls, rng: Any = None) -> GeneticTraits:
        """Generate random genetic traits with some correlation."""
        if rng is None:
            import random
            rng = random

        gauss = cls._make_gauss_fn(rng)

        traits = GeneticTraits(
            height=gauss(0.5, 0.15),
            strength=gauss(0.5, 0.15),
            intelligence=gauss(0.5, 0.15),
            health=gauss(0.7, 0.15),  # Mean higher for viability
            fertility=gauss(0.5, 0.1),
            lifespan_potential=gauss(0.5, 0.1),
            memory_capacity=gauss(0.5, 0.15),
            learning_speed=gauss(0.5, 0.15),
            creativity=gauss(0.5, 0.15),
            perception=gauss(0.5, 0.1),
            aggression=gauss(0.3, 0.15),  # Mean lower for viability
            anxiety=gauss(0.3, 0.15),
            sociability=gauss(0.5, 0.15),
        )

        # Clamp values
        for attr in ["height", "strength", "intelligence", "health", "fertility",
                      "lifespan_potential", "memory_capacity", "learning_speed",
                      "creativity", "perception", "aggression", "anxiety", "sociability"]:
            setattr(traits, attr, max(0.0, min(1.0, getattr(traits, attr))))

        return traits

    @classmethod
    def generate_moral_character(cls, rng: Any = None) -> MoralCharacter:
        """Generate random moral character traits."""
        if rng is None:
            import random
            rng = random

        gauss = cls._make_gauss_fn(rng)

        return MoralCharacter(
            honesty=gauss(0.5, 0.2),
            empathy=gauss(0.5, 0.2),
            altruism=gauss(0.4, 0.2),
            greed=gauss(0.5, 0.2),
            loyalty=gauss(0.5, 0.2),
            justice=gauss(0.5, 0.2),
            courage=gauss(0.5, 0.2),
            temperance=gauss(0.5, 0.2),
            hospitality=gauss(0.5, 0.2),
            humility=gauss(0.5, 0.2),
            forgiveness=gauss(0.5, 0.2),
            compassion=gauss(0.5, 0.2),
            work_ethic=gauss(0.5, 0.2),
            thriftiness=gauss(0.5, 0.2),
            ambition=gauss(0.5, 0.2),
        )

    @classmethod
    def generate_personality(cls, genetic: GeneticTraits = None, rng: Any = None) -> PersonalityTraits:
        """Generate personality traits influenced by genetics."""
        if rng is None:
            import random
            rng = random

        gauss = cls._make_gauss_fn(rng)

        # Personality influenced by genetic traits
        intelligence_factor = genetic.intelligence if genetic else 0.5
        aggression_factor = genetic.aggression if genetic else 0.3

        return PersonalityTraits(
            openness=gauss(0.5 + (intelligence_factor - 0.5) * 0.3, 0.15),
            conscientiousness=gauss(0.5, 0.15),
            extraversion=gauss(0.5 + (genetic.sociability - 0.5) * 0.5 if genetic else 0.5, 0.15),
            agreeableness=gauss(0.5 - (aggression_factor - 0.3) * 0.5 if genetic else 0.5, 0.2),
            neuroticism=gauss(0.3 + (genetic.anxiety - 0.3) * 0.5 if genetic else 0.3, 0.15),
            dominance=gauss(0.5 + (genetic.strength - 0.5) * 0.3 if genetic else 0.5, 0.15),
            religiosity=gauss(0.5, 0.2),
            materialism=gauss(0.5, 0.15),
            risk_tolerance=gauss(0.5, 0.2),
            patience=gauss(0.5, 0.15),
        )

    @classmethod
    def generate_name(cls, culture: CulturalBackground = None, rng: Any = None) -> tuple[str, str]:
        """Generate a name based on cultural background."""
        if rng is None:
            import random
            rng = random

        ethnicity = culture.ethnicity if culture else "default"
        if ethnicity not in cls.NAME_TEMPLATES:
            ethnicity = "default"

        templates = cls.NAME_TEMPLATES[ethnicity]
        first = rng.choice(templates["first"])
        last = rng.choice(templates["last"])

        return first, last

    @classmethod
    def generate_full_profile(
        cls,
        agent_id: str,
        rng: Any = None,
        culture: CulturalBackground = None,
    ) -> AgentProfile:
        """Generate a complete diverse agent profile."""
        if rng is None:
            import random
            rng = random

        # Generate or use provided culture
        if culture is None:
            culture = cls.generate_culture(rng)

        # Generate genetic traits
        genetic = cls.generate_genetic_traits(rng)

        # Generate personality influenced by genetics
        personality = cls.generate_personality(genetic, rng)

        # Generate moral character
        moral = cls.generate_moral_character(rng)

        # Generate name
        first_name, last_name = cls.generate_name(culture, rng)

        # Create skills influenced by genetics and personality
        skills = {
            "gathering": 0.2 + genetic.strength * 0.3 + rng.uniform(-0.1, 0.1),
            "crafting": 0.2 + genetic.intelligence * 0.3 + rng.uniform(-0.1, 0.1),
            "social": 0.2 + personality.extraversion * 0.3 + rng.uniform(-0.1, 0.1),
            "combat": 0.1 + genetic.strength * 0.4 + (1 - personality.agreeableness) * 0.2 + rng.uniform(-0.1, 0.1),
            "exploration": 0.2 + personality.openness * 0.3 + genetic.perception * 0.2 + rng.uniform(-0.1, 0.1),
            "leadership": 0.1 + personality.dominance * 0.3 + genetic.intelligence * 0.2 + rng.uniform(-0.1, 0.1),
            "teaching": 0.1 + genetic.intelligence * 0.3 + personality.agreeableness * 0.2 + rng.uniform(-0.1, 0.1),
            "healing": 0.1 + genetic.intelligence * 0.2 + moral.empathy * 0.3 + rng.uniform(-0.1, 0.1),
            "trading": 0.2 + personality.extraversion * 0.2 + (1 - moral.greed) * 0.2 + rng.uniform(-0.1, 0.1),
        }

        # Clamp skill values
        for skill in skills:
            skills[skill] = max(0.0, min(1.0, skills[skill]))

        # Create profile
        profile = AgentProfile(
            agent_id=agent_id,
            name=f"{first_name} {last_name}",
            personality=personality,
            moral_character=moral,
            genetic_traits=genetic,
            cultural_background=culture,
            skills=skills,
            tier=AgentTier.L3_BACKGROUND,
        )

        return profile


@dataclass
class Goal:
    """A goal that an agent is pursuing."""
    goal_id: str
    description: str
    priority: float = 0.5
    progress: float = 0.0
    deadline: Tick | None = None
    parent_goal: str | None = None
    sub_goals: list[str] = field(default_factory=list)
    abandoned: bool = False

    def update(self, progress_delta: float) -> None:
        self.progress = min(1.0, self.progress + progress_delta)


# =============================================================================
# Main Agent Class
# =============================================================================

@dataclass
class Agent:
    """
    A single agent in the simulation.

    Each agent has:
    - Identity: entity_id, name, profile
    - State: health, energy, hunger, thirst
    - Inventory: resources and wealth
    - Personality: HEXACO traits
    - Memory: multi-layered memory system
    - Decision-making: sync and async methods
    """

    # Identity
    entity_id: EntityID
    name: str
    position: Pos2D
    tier: AgentTier = AgentTier.L3_BACKGROUND
    profile: AgentProfile = field(default_factory=lambda: AgentProfile(
        agent_id="", name="Unnamed"
    ))

    # Physical state
    health: float = 1.0
    energy: float = 1.0
    hunger: float = 0.0
    thirst: float = 0.0

    # Inventory
    inventory: Inventory = field(default_factory=Inventory)
    wealth: float = 100.0

    # HEXACO personality
    honesty_humility: float = 0.5
    emotionality: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    conscientiousness: float = 0.5
    openness: float = 0.5

    # Extended personality
    dominance: float = 0.5
    religiosity: float = 0.5
    materialism: float = 0.5
    risk_tolerance: float = 0.5
    patience: float = 0.5

    # Social
    relationships: dict[EntityID, Relationship] = field(default_factory=dict)
    organization_ids: list[EntityID] = field(default_factory=list)
    reputation: float = 0.0

    # Language
    known_signals: dict[str, str] = field(default_factory=dict)

    # Beliefs
    beliefs: list[Belief] = field(default_factory=list)

    # Goals
    goals: list[Goal] = field(default_factory=list)

    # Decision state
    current_goal: str | None = None
    goal_priority: float = 0.0
    last_decision_tick: int = -1
    last_perception_tick: int = -1

    # Perception
    _perception_radius: float = 5.0
    _pending_signals: list[Signal] = field(default_factory=list)

    # Memory
    memory: AgentMemory = field(default_factory=AgentMemory)
    _episodic_memory_backup: list[dict[str, Any]] = field(default_factory=list)
    _max_episodic_backup: int = 50

    # Skills
    skills: dict[str, float] = field(default_factory=lambda: {
        "strength": 0.5, "intelligence": 0.5, "charisma": 0.5,
        "crafting": 0.5, "agriculture": 0.5, "combat": 0.5,
        "trading": 0.5, "diplomacy": 0.5,
    })

    # LLM config (for L1 agents)
    _llm_config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entity_id:
            raise ValueError("entity_id is required")
        if not self.name:
            self.name = f"Agent_{self.entity_id[:8]}"
        # Sync profile if not set
        if not self.profile.agent_id:
            self.profile.agent_id = self.entity_id
            self.profile.name = self.name
            self.profile.tier = self.tier
            self.profile.position = self.position

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def is_alive(self) -> bool:
        return self.health > 0.0

    @property
    def is_hungry(self) -> bool:
        return self.hunger > 0.5

    @property
    def is_thirsty(self) -> bool:
        return self.thirst > 0.5

    @property
    def perception_radius(self) -> float:
        return self._perception_radius

    @property
    def x(self) -> int:
        return self.position.x

    @property
    def y(self) -> int:
        return self.position.y

    @property
    def id(self) -> EntityID:
        return self.entity_id

    # =========================================================================
    # Memory Methods
    # =========================================================================

    def remember(
        self,
        event_type: str,
        data: dict[str, Any],
        importance: float = 0.5,
        tick: int = 0,
    ) -> None:
        """Record an episodic memory."""
        entry = MemoryEntry(
            tick=tick,
            content=f"{event_type}: {data}",
            memory_type="episodic",
            emotional_valence=0.1 if importance > 0.5 else -0.1,
            importance=importance,
            vividness=1.0,
        )
        self.memory.add_memory(entry)
        # Also add to backup memory for compatibility
        memory = {
            "tick": tick,
            "type": event_type,
            "data": data,
            "importance": importance,
            "time": time.time(),
        }
        self._episodic_memory_backup.append(memory)
        if len(self._episodic_memory_backup) > self._max_episodic_backup:
            self._evict_memory()

    def _evict_memory(self) -> None:
        """Evict least important memory when buffer is full."""
        if not self._episodic_memory_backup:
            return
        self._episodic_memory_backup.sort(key=lambda m: (m["importance"], m["tick"]))
        self._episodic_memory_backup.pop(0)

    def recall_recent(self, n: int = 10) -> list[dict[str, Any]]:
        """Get the N most recent memories."""
        sorted_mem = sorted(self._episodic_memory_backup, key=lambda m: m["tick"], reverse=True)
        return sorted_mem[:n]

    def recall_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """Get memories of a specific type."""
        return [m for m in self._episodic_memory_backup if m["type"] == event_type]

    def get_memory_summary(self, max_entries: int = 20) -> str:
        """Get a text summary of recent memories."""
        recent = self.memory.recall_recent(max_entries)
        if not recent:
            return "No significant memories."
        return "\n".join([f"[Tick {m.tick}] {m.content}" for m in recent])

    # =========================================================================
    # Perception
    # =========================================================================

    def perceive(self, signal: Signal) -> None:
        """Process an incoming signal."""
        self._pending_signals.append(signal)
        self.last_perception_tick = signal.duration

    def get_pending_signals(self) -> list[Signal]:
        """Get and clear pending signals."""
        signals = list(self._pending_signals)
        self._pending_signals.clear()
        return signals

    def update_perception_radius(self, radius: float) -> None:
        """Update the perception radius."""
        self._perception_radius = radius

    # =========================================================================
    # Need Updates
    # =========================================================================

    # Configurable thresholds - will be overridden from config if available
    _SURVIVAL_THRESHOLD = 0.85  # Hunger/thirst threshold for critical survival
    _ENERGY_THRESHOLD = 0.15     # Energy threshold for rest
    _SOCIAL_GOAL_PROBABILITY = 0.35  # Probability of choosing social goal when not critical
    _SOCIAL_ATTRACTION = 0.6     # Probability of moving toward agents

    def _load_emergence_config(self, world: Any) -> None:
        """Load emergence config from world if available."""
        if world is None:
            return
        try:
            config = getattr(world, '_config', None)
            if config and hasattr(config, 'emergence'):
                e = config.emergence
                self._SURVIVAL_THRESHOLD = e.survival_threshold
                self._ENERGY_THRESHOLD = e.energy_threshold
                self._SOCIAL_GOAL_PROBABILITY = e.social_probability
                self._SOCIAL_ATTRACTION = e.social_attraction
                # Store world reference for protocol access
                self._world = world
        except (AttributeError, TypeError):
            pass  # Config not available, use defaults

    def update_needs(self, tick: int, world: Any | None = None) -> None:
        """Update need levels (hunger, thirst, energy, Maslow)."""
        # Load config on first call
        if not hasattr(self, '_config_loaded'):
            self._load_emergence_config(world)
            self._config_loaded = True

        # Basic need decay
        self.hunger = min(1.0, self.hunger + 0.001)
        self.thirst = min(1.0, self.thirst + 0.002)
        self.energy = max(0.0, self.energy - 0.0005)

        # Update profile needs
        self.profile.apply_needs_decay()

        # Get world RNG for random decisions
        rng = None
        if world:
            rng = getattr(world, '_rng', None)
            self._world = world

        # Critical survival needs - use configurable threshold
        if self.hunger > self._SURVIVAL_THRESHOLD:
            self.current_goal = "seek_food"
            self.goal_priority = self.hunger
        elif self.thirst > self._SURVIVAL_THRESHOLD:
            self.current_goal = "seek_water"
            self.goal_priority = self.thirst
        elif self.energy < self._ENERGY_THRESHOLD:
            self.current_goal = "rest"
            self.goal_priority = 1.0 - self.energy
        else:
            # Non-critical: Check for social goals
            # Agents are more likely to interact when needs are moderate
            if rng and rng.random() < self._SOCIAL_GOAL_PROBABILITY:
                social_goals = ["socialize", "trade", "help", "gossip"]
                self.current_goal = rng.choice(social_goals)
                self.goal_priority = 0.4
            else:
                self.current_goal = self.profile.get_dominant_need()
                self.goal_priority = 0.5

    # =========================================================================
    # Decision Making
    # =========================================================================

    def decide_action(self, tick: int, world: Any) -> Decision | None:
        """Synchronous decision making (for rule-based agents)."""
        if not self.is_alive:
            return None

        self.update_needs(tick, world)
        goal = self.current_goal or "wander"
        goal = goal.lower()

        return self._select_action(tick, world, goal)

    def _select_action(
        self, tick: int, world: Any, goal: str
    ) -> Decision | None:
        """Select action based on goal."""
        if goal == "seek_food":
            return self._action_seek_food(tick, world)
        elif goal == "seek_water":
            return self._action_seek_water(tick, world)
        elif goal == "rest":
            return self._action_rest(tick)
        elif goal == "wander":
            return self._action_wander(tick, world)
        elif goal == "socialize":
            return self._action_socialize(tick, world)
        elif goal == "trade":
            return self._action_trade(tick, world)
        elif goal == "work":
            return self._action_work(tick, world)
        elif goal == "explore":
            return self._action_explore(tick, world)
        elif goal == "help":
            return self._action_help(tick, world)
        elif goal == "gossip":
            return self._action_gossip(tick, world)
        else:
            return self._action_wander(tick, world)

    def _action_seek_food(self, tick: int, world: Any) -> Decision:
        """Seek food."""
        from ambientsaga.types import TerrainType
        for x in range(max(0, self.x - 20), min(world._config.world.width, self.x + 20)):
            for y in range(max(0, self.y - 20), min(world._config.world.height, self.y + 20)):
                terrain = world.get_terrain(x, y)
                if terrain in (TerrainType.GRASSLAND, TerrainType.SAVANNA,
                               TerrainType.TROPICAL_FOREST, TerrainType.TEMPERATE_FOREST):
                    dist = ((x - self.x) ** 2 + (y - self.y) ** 2) ** 0.5
                    if dist < self._perception_radius:
                        self.remember("seek_food", {"target": (x, y)}, 0.8, tick)
                        return Decision(
                            tick=tick, agent_id=self.entity_id,
                            decision_type=DecisionType.SEEK_FOOD,
                            target_pos=Pos2D(x, y), expected_utility=self.hunger,
                            algorithm="heuristic",
                        )
        return self._action_wander(tick, world)

    def _action_seek_water(self, tick: int, world: Any) -> Decision:
        """Seek water."""
        for x in range(max(0, self.x - 20), min(world._config.world.width, self.x + 20)):
            for y in range(max(0, self.y - 20), min(world._config.world.height, self.y + 20)):
                terrain = world.get_terrain(x, y)
                if terrain.is_water:
                    self.remember("seek_water", {"found": (x, y)}, 0.9, tick)
                    return Decision(
                        tick=tick, agent_id=self.entity_id,
                        decision_type=DecisionType.SEEK_WATER,
                        target_pos=Pos2D(x, y), expected_utility=self.thirst,
                        algorithm="heuristic",
                    )
        return self._action_wander(tick, world)

    def _action_rest(self, tick: int) -> Decision:
        """Rest to recover energy."""
        self.energy = min(1.0, self.energy + 0.1)
        return Decision(
            tick=tick, agent_id=self.entity_id,
            decision_type=DecisionType.REST, expected_utility=0.5,
            algorithm="rule",
        )

    def _action_wander(self, tick: int, world: Any) -> Decision:
        """Random movement with tendency toward nearby agents."""
        rng = world._rng

        # Check for nearby agents first - move toward them to increase interactions
        nearby = list(world.get_agents_near(self.position, 10.0))
        if nearby and rng.random() < self._SOCIAL_ATTRACTION:  # Configurable attraction
            other, _ = rng.choice(nearby)
            target_x, target_y = other.x, other.y
            # Move one step toward the target
            dx = 1 if target_x > self.x else (-1 if target_x < self.x else 0)
            dy = 1 if target_y > self.y else (-1 if target_y < self.y else 0)
            # Add some randomness
            if rng.random() < 0.3:
                dx += rng.integers(-1, 2)
                dy += rng.integers(-1, 2)
            new_x = max(0, min(world._config.world.width - 1, self.x + dx))
            new_y = max(0, min(world._config.world.height - 1, self.y + dy))
            new_pos = Pos2D(new_x, new_y)
            terrain = world.get_terrain(new_x, new_y)
            if terrain.is_passable:
                self.remember("wander_toward_agent", {"target": other.entity_id[:8], "to": (new_x, new_y)}, 0.1, tick)
                return Decision(
                    tick=tick, agent_id=self.entity_id,
                    decision_type=DecisionType.MOVE_TO, target_pos=new_pos,
                    expected_utility=0.2, algorithm="social",
                )

        # Random movement as fallback
        dx = rng.integers(-2, 3)  # Increased range for more exploration
        dy = rng.integers(-2, 3)
        new_x = max(0, min(world._config.world.width - 1, self.x + dx))
        new_y = max(0, min(world._config.world.height - 1, self.y + dy))
        new_pos = Pos2D(new_x, new_y)
        terrain = world.get_terrain(new_x, new_y)
        if terrain.is_passable:
            self.remember("wander", {"from": (self.x, self.y), "to": (new_x, new_y)}, 0.1, tick)
            return Decision(
                tick=tick, agent_id=self.entity_id,
                decision_type=DecisionType.MOVE_TO, target_pos=new_pos,
                expected_utility=0.1, algorithm="random",
            )
        return Decision(
            tick=tick, agent_id=self.entity_id,
            decision_type=DecisionType.REST, expected_utility=0.1,
            algorithm="rule",
        )

    def _action_socialize(self, tick: int, world: Any) -> Decision:
        """Interact with nearby agents - creates protocol traces."""
        # Look for nearby agents to interact with
        nearby = list(world.get_agents_near(self.position, 5.0))
        if nearby:
            # Choose a random nearby agent
            rng = getattr(world, '_rng', None)
            if rng:
                other, _ = rng.choice(nearby)
            else:
                other, _ = nearby[0]

            # Create a protocol trace for this interaction
            if world._protocol is not None:
                try:
                    # Random social signal
                    signals = ["help", "request", "offer", "gossip", "inform"]
                    signal = rng.choice(signals) if rng else "inform"
                    trace = world._protocol.initiate(
                        actor=self,
                        signal=signal,
                        receiver_id=other.entity_id,
                        content={"type": "social_interaction", "goal": "connect"},
                        interpretation=f"Agent {self.entity_id[:8]} initiated {signal}",
                    )
                    if trace:
                        # Record in agent memory
                        self.remember(f"social:{signal}", {"target": other.entity_id[:8]}, 0.5, tick)
                except Exception:
                    pass  # Protocol interaction failed, continue with decision

            return Decision(
                tick=tick, agent_id=self.entity_id,
                decision_type=DecisionType.SOCIALIZE,
                target_id=other.entity_id, expected_utility=0.4,
                algorithm="protocol",
            )
        # No nearby agents - move toward where agents might be
        return self._action_wander(tick, world)

    def _action_help(self, tick: int, world: Any) -> Decision:
        """Offer help to nearby agents."""
        nearby = list(world.get_agents_near(self.position, 5.0))
        if nearby:
            rng = getattr(world, '_rng', None)
            if rng:
                other, _ = rng.choice(nearby)
            else:
                other, _ = nearby[0]

            # Create protocol trace for help
            if world._protocol is not None:
                try:
                    trace = world._protocol.initiate(
                        actor=self,
                        signal="help",
                        receiver_id=other.entity_id,
                        content={"type": "resource_transfer", "resource": "food", "amount": 1},
                        interpretation=f"Agent {self.entity_id[:8]} offered help",
                    )
                    if trace:
                        self.remember("offered_help", {"to": other.entity_id[:8]}, 0.6, tick)
                except Exception:
                    pass

            return Decision(
                tick=tick, agent_id=self.entity_id,
                decision_type=DecisionType.SOCIALIZE,
                target_id=other.entity_id, expected_utility=0.5,
                algorithm="protocol",
            )
        return self._action_wander(tick, world)

    def _action_gossip(self, tick: int, world: Any) -> Decision:
        """Share information with nearby agents."""
        nearby = list(world.get_agents_near(self.position, 5.0))
        if nearby:
            rng = getattr(world, '_rng', None)
            if rng:
                other, _ = rng.choice(nearby)
            else:
                other, _ = nearby[0]

            # Create protocol trace for gossip
            if world._protocol is not None:
                try:
                    gossip_types = ["location", "resource", "social"]
                    gossip_type = rng.choice(gossip_types) if rng else "social"
                    trace = world._protocol.initiate(
                        actor=self,
                        signal="gossip",
                        receiver_id=other.entity_id,
                        content={"type": "information", "topic": gossip_type},
                        interpretation=f"Agent {self.entity_id[:8]} shared gossip",
                    )
                    if trace:
                        self.remember("gossip", {"with": other.entity_id[:8], "topic": gossip_type}, 0.3, tick)
                except Exception:
                    pass

            return Decision(
                tick=tick, agent_id=self.entity_id,
                decision_type=DecisionType.SOCIALIZE,
                target_id=other.entity_id, expected_utility=0.3,
                algorithm="protocol",
            )
        return self._action_wander(tick, world)

    def _action_trade(self, tick: int, world: Any) -> Decision:
        """Attempt to trade."""
        return Decision(
            tick=tick, agent_id=self.entity_id,
            decision_type=DecisionType.TRADE, expected_utility=0.2,
            algorithm="market",
        )

    def _action_work(self, tick: int, world: Any) -> Decision:
        """Do productive work."""
        skill = max(self.skills, key=lambda s: self.skills[s])
        self.remember("work", {"skill": skill, "level": self.skills[skill]}, 0.3, tick)
        return Decision(
            tick=tick, agent_id=self.entity_id,
            decision_type=DecisionType.WORK, expected_utility=0.3,
            algorithm="skill_based",
        )

    def _action_explore(self, tick: int, world: Any) -> Decision:
        """Explore the world."""
        return Decision(
            tick=tick, agent_id=self.entity_id,
            decision_type=DecisionType.EXPLORE, expected_utility=0.2,
            algorithm="frontier",
        )

    # =========================================================================
    # Action Execution
    # =========================================================================

    def execute_action(self, decision: Decision, world: Any) -> None:
        """Execute a decision."""
        if decision is None:
            return

        self.last_decision_tick = decision.tick

        if decision.decision_type == DecisionType.MOVE_TO and decision.target_pos:
            world.move_agent(self.entity_id, decision.target_pos)
        elif decision.decision_type == DecisionType.SEEK_FOOD:
            if decision.target_pos:
                self._consume_food(world)
            self.hunger = max(0.0, self.hunger - 0.3)
        elif decision.decision_type == DecisionType.SEEK_WATER:
            if decision.target_pos:
                self._consume_water(world)
            self.thirst = max(0.0, self.thirst - 0.4)
        elif decision.decision_type == DecisionType.SOCIALIZE:
            if decision.target_id:
                self._socialize_with(decision.target_id, world)
        elif decision.decision_type == DecisionType.WORK:
            self._do_work(world)
        elif decision.decision_type == DecisionType.TRADE:
            self._do_trade(world)

    def _consume_food(self, world: Any) -> None:
        """Consume food at current location."""
        from ambientsaga.types import TerrainType
        terrain = world.get_terrain(self.x, self.y)
        if terrain in (TerrainType.GRASSLAND, TerrainType.SAVANNA, TerrainType.TROPICAL_FOREST):
            self.inventory.add(ResourceType.FRUIT, 1.0)

    def _consume_water(self, world: Any) -> None:
        """Consume water at current location."""
        terrain = world.get_terrain(self.x, self.y)
        if terrain.is_water:
            self.thirst = 0.0

    def _socialize_with(self, other_id: EntityID, world: Any) -> None:
        """Interact with another agent."""
        world.set_relationship(
            self.entity_id, other_id,
            trust=self.agreeableness * 0.1,
        )
        self.remember(
            "socialize",
            {"with": other_id[:8], "trust_delta": self.agreeableness * 0.1},
            0.4, world.tick,
        )

    def _do_work(self, world: Any) -> None:
        """Perform productive work."""
        skill_level = sum(self.skills.values()) / len(self.skills)
        self.wealth += skill_level * 2.0
        self.energy = max(0.0, self.energy - 0.02)

    def _do_trade(self, world: Any) -> None:
        """Attempt to trade."""
        if self.inventory.total_weight() > 20:
            self.wealth += 5.0

    # =========================================================================
    # Async Decision Making (for LLM agents)
    # =========================================================================

    async def think_async(self, tick: int, context: dict[str, Any]) -> Decision | None:
        """
        Async decision making - can use LLM or advanced reasoning.
        This is called for L1 and L2 agents.
        """
        if not self.is_alive:
            return None

        self.update_needs(tick)

        # Build context for LLM
        prompt_context = self._build_llm_context(tick, context)

        # Use LLM if configured and available
        if self.tier == AgentTier.L1_CORE and self._llm_config:
            return await self._llm_deliberate(prompt_context, tick)
        else:
            # Fall back to rule-based
            goal = self.current_goal or "wander"
            return self._select_action(tick, context.get("world"), goal.lower())

    def _build_llm_context(self, tick: int, context: dict[str, Any]) -> dict[str, Any]:
        """Build rich context for LLM decision making."""
        memory_summary = self.get_memory_summary(10)
        recent_memories = self.memory.recall_recent(5)

        return {
            "agent_id": self.entity_id,
            "name": self.name,
            "position": {"x": self.x, "y": self.y},
            "health": self.health,
            "energy": self.energy,
            "hunger": self.hunger,
            "thirst": self.thirst,
            "wealth": self.wealth,
            "personality": self.profile.personality.to_dict(),
            "current_goal": self.current_goal,
            "goal_priority": self.goal_priority,
            "profile_needs": self.profile.needs,
            "memory_summary": memory_summary,
            "recent_memories": [
                {"tick": m.tick, "content": m.content, "valence": m.emotional_valence}
                for m in recent_memories
            ],
            "tick": tick,
            "world_state": context.get("world_state", {}),
            "nearby_agents": context.get("nearby_agents", []),
            "relationships": list(self.relationships.keys())[:10],
        }

    async def _llm_deliberate(
        self, context: dict[str, Any], tick: int
    ) -> Decision | None:
        """
        LLM-powered deliberation.
        This is a placeholder - in production, this would call the LLM API.
        """
        # Build atmospheric action descriptions based on personality and state
        dominant_need = self.profile.get_dominant_need()

        action_map = {
            "physiological": "forage",
            "safety": "fortify",
            "belonging": "connect",
            "esteem": "create",
            "self_actualization": "reflect",
        }

        action_type = action_map.get(dominant_need, "wander")

        messages = {
            "forage": "Scouring the land for sustenance, driven by hunger.",
            "fortify": "Strengthening defenses, wary of unseen dangers.",
            "connect": "Seeking the warmth of companionship.",
            "create": "Building something meaningful to leave a mark.",
            "reflect": "Pondering the deeper questions of existence.",
            "wander": "Drifting through the world, open to whatever comes.",
        }

        action_type_map = {
            "forage": DecisionType.SEEK_FOOD,
            "fortify": DecisionType.REST,
            "connect": DecisionType.SOCIALIZE,
            "create": DecisionType.WORK,
            "reflect": DecisionType.REST,
            "wander": DecisionType.MOVE_TO,
        }

        # Record the LLM decision
        self.remember(
            f"llm_decision_{action_type}",
            {"reasoning": messages.get(action_type, "")},
            0.6, tick,
        )

        return Decision(
            tick=tick,
            agent_id=self.entity_id,
            decision_type=action_type_map.get(action_type, DecisionType.REST),
            expected_utility=0.5,
            algorithm="llm",
        )

    async def act_async(self, decision: Decision, world: Any) -> None:
        """Async action execution."""
        self.execute_action(decision, world)

    async def tick(self, tick: int, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Main agent tick - think and act.
        This is the primary method called by the simulation engine.
        Returns a dict with results for the simulation engine.
        """
        if context is None:
            context = {}

        # Get world reference
        world = context.get("world")
        if world is None:
            return {"alive": self.is_alive, "action": "idle", "success": True, "priority": 10}

        # Update needs (hunger, thirst, energy) with config
        self.update_needs(tick, world)

        # For L1 agents, use async deliberation; for L2/L3, use sync
        if self.tier == AgentTier.L1_CORE:
            decision = await self.think_async(tick, context)
        else:
            decision = self.decide_action(tick, world)

        if decision is None:
            return {"alive": self.is_alive, "action": "idle", "success": True, "priority": 10}

        # Execute action
        self.execute_action(decision, world)

        # Age
        self.age(1)

        # Record action
        if decision.decision_type != DecisionType.REST:
            self.remember(
                f"action:{decision.decision_type.value}",
                {"tick": tick, "action": decision.decision_type.value},
                0.3,
                tick
            )

        return {
            "alive": self.is_alive,
            "action": decision.decision_type.value,
            "success": True,
            "priority": 10,
        }

    # =========================================================================
    # Aging and Lifecycle
    # =========================================================================

    def age(self, ticks: int = 1) -> None:
        """Age the agent."""
        self.profile.age += ticks
        self.health = max(0.0, self.health - 0.00001 * ticks)

    def die(self) -> None:
        """Mark agent as dead."""
        self.health = 0.0

    # =========================================================================
    # Belief Update
    # =========================================================================

    def update_belief(
        self,
        proposition: str,
        evidence: str,
        confirms: bool,
        strength: float,
        tick: int,
    ) -> None:
        """Update a belief with new evidence."""
        existing = next((b for b in self.beliefs if b.proposition == proposition), None)

        if existing:
            idx = self.beliefs.index(existing)
            self.beliefs[idx] = existing.update(evidence, confirms, strength, tick)
        else:
            belief = Belief(
                proposition=proposition,
                confidence=0.5 if confirms else 0.3,
                source_tick=tick,
                evidence=(evidence,),
                counter_evidence=() if confirms else (evidence,),
                last_updated_tick=tick,
            )
            self.beliefs.append(belief)

    def add_goal(self, description: str, priority: float = 0.5) -> Goal:
        """Add a new goal."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            description=description,
            priority=priority,
        )
        self.goals.append(goal)
        return goal

    def set_belief(self, belief: str) -> None:
        """Set a belief."""
        if belief not in self.profile.beliefs:
            self.profile.beliefs.append(belief)

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent to dict."""
        return {
            "entity_id": str(self.entity_id),
            "name": self.name,
            "position": {"x": self.x, "y": self.y},
            "tier": self.tier.value,
            "health": self.health,
            "energy": self.energy,
            "hunger": self.hunger,
            "thirst": self.thirst,
            "wealth": self.wealth,
            "goals": [g.description for g in self.goals[:5]],
            "memory_count": len(self.memory.episodic),
            "relationships": len(self.relationships),
        }

    def __str__(self) -> str:
        return f"Agent({self.name}, tier={self.tier.value}, pos=({self.x}, {self.y}), health={self.health:.2f})"

    def __repr__(self) -> str:
        return (
            f"Agent(id={self.entity_id[:8]}, tier={self.tier.value}, "
            f"pos=({self.x}, {self.y}), health={self.health:.2f})"
        )


# =============================================================================
# Agent Factory
# =============================================================================

class UnifiedAgentFactory:
    """
    Factory for creating unified agents with consistent initialization.
    """

    NAMES_FIRST = [
        "Aldric", "Brynn", "Cedric", "Diana", "Elena", "Fenris", "Gwendolyn", "Hector",
        "Isolde", "Jasper", "Kira", "Lysander", "Mira", "Nolan", "Ophelia", "Pyrus",
        "Quinn", "Rowena", "Silas", "Thalia", "Uri", "Vesper", "Wren", "Xander",
        "Yara", "Zephyr", "Aria", "Bodhi", "Calla", "Dorian", "Eira", "Florian",
    ]

    NAMES_SECOND = [
        "of the Mountain", "of the River", "of the Valley", "of the Shore",
        "the Wanderer", "the Builder", "the Hunter", "the Healer", "the Smith",
        "the Trader", "the Scholar", "the Warrior", "the Farmer", "the Shepherd",
    ]

    def __init__(self, world: Any) -> None:
        self.world = world
        self._name_used: set[str] = set()
        self._agent_index = 0

    def create_agent(
        self,
        tier: AgentTier,
        position: Pos2D | None = None,
        name: str | None = None,
        seed: int | None = None,
        culture: CulturalBackground | None = None,
    ) -> Agent:
        """Create a new unified agent with full diversity."""
        rng = np.random.default_rng(seed or self._agent_index)
        self._agent_index += 1

        # Generate entity ID
        from ambientsaga.types import new_entity_id
        entity_id = new_entity_id()

        # Generate full diverse profile using DiversitySystem
        profile = DiversitySystem.generate_full_profile(
            agent_id=entity_id,
            rng=rng,
            culture=culture,
        )

        # Override with provided values
        if name:
            profile.name = name
        profile.age = rng.integers(18 * 360, 60 * 360)
        profile.gender = rng.choice(["male", "female", "other"])
        profile.tier = tier
        if position:
            profile.position = position
            profile.home_position = position
        else:
            profile.position = self._find_suitable_position(rng)
            profile.home_position = profile.position

        # Create agent
        agent = Agent(
            entity_id=entity_id,
            name=profile.name,
            position=profile.position,
            tier=tier,
            profile=profile,
            _perception_radius=self._get_tier_radius(tier),
        )

        # Set initial wealth influenced by genetic traits and skills
        base_wealth = 50.0 + profile.genetic_traits.intelligence * 50
        agent.wealth = rng.uniform(base_wealth, base_wealth + 150.0)

        # Initialize skills
        self._initialize_skills(agent, rng, tier)

        return agent

    def spawn_population(
        self,
        n: int,
        tier_distribution: dict[AgentTier, int] | None = None,
    ) -> list[Agent]:
        """Spawn a population of agents."""
        if tier_distribution is None:
            cfg = self.world._config.agents
            tier_distribution = {
                AgentTier.L1_CORE: cfg.tier1_count,
                AgentTier.L2_FUNCTIONAL: cfg.tier2_count,
                AgentTier.L3_BACKGROUND: cfg.tier3_count,
            }

        agents: list[Agent] = []
        for tier, count in tier_distribution.items():
            for _ in range(count):
                agent = self.create_agent(tier)
                agents.append(agent)
                self.world.register_agent(agent)

        return agents

    def _generate_name(self, rng: np.random.Generator) -> str:
        """Generate a unique name."""
        for _ in range(100):
            first = rng.choice(self.NAMES_FIRST)
            second = rng.choice(self.NAMES_SECOND)
            name = f"{first} {second}"
            if name not in self._name_used:
                self._name_used.add(name)
                return name
        return f"Agent_{rng.integers(10000, 99999)}"

    def _find_suitable_position(self, rng: np.random.Generator) -> Pos2D:
        """Find a suitable spawn position on land."""
        w = self.world._config.world.width
        h = self.world._config.world.height

        for _ in range(1000):
            x = int(rng.integers(0, w))
            y = int(rng.integers(0, h))
            if self.world.is_passable(x, y):
                return Pos2D(x, y)

        return Pos2D(w // 2, h // 2)

    def _get_tier_radius(self, tier: AgentTier) -> float:
        """Get default perception radius for a tier."""
        cfg = self.world._config.agents
        if tier == AgentTier.L1_CORE:
            return cfg.max_perception_radius_tier1
        elif tier == AgentTier.L2_FUNCTIONAL:
            return cfg.max_perception_radius_tier2
        elif tier == Tier.L3_BACKGROUND:
            return cfg.max_perception_radius_tier3
        return 1.0

    def _initialize_skills(
        self, agent: Agent, rng: np.random.Generator, tier: AgentTier
    ) -> None:
        """Initialize skills based on tier and randomness."""
        tier_order = {AgentTier.L1_CORE: 3, AgentTier.L2_FUNCTIONAL: 2, AgentTier.L3_BACKGROUND: 1}
        tier_num = tier_order.get(tier, 2)
        tier_bonus = (tier_num - 2) * 0.05
        for skill in agent.skills:
            agent.skills[skill] = rng.uniform(0.3, 0.7) + tier_bonus


# Alias for backward compatibility
Tier = AgentTier
