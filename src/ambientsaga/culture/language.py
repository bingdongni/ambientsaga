"""
Language system — communication, dialects, and linguistic evolution.

This module implements:
- Language: a structured communication system
- Dialect: variation within a language
- Vocabulary: word meanings and associations
- Communication: how agents exchange information
- Linguistic evolution: how languages change over time

Key design goals:
1. Languages emerge from population interaction
2. dialects form through geographic/social isolation
3. Vocabulary evolves to reflect environment
4. Communication efficiency affects social coordination
5. Language barriers create cultural divisions
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import numpy as np

from ambientsaga.types import EntityID, Pos2D, new_entity_id

if TYPE_CHECKING:
    from ambientsaga.world.state import World
    from ambientsaga.agents.agent import Agent


# ---------------------------------------------------------------------------
# Language Types
# ---------------------------------------------------------------------------


class LinguisticFamily(Enum):
    """Major language families."""

    NATIVE = auto()      # Original/tribal language
    DERIVED = auto()      # Evolved from another
    CREOLE = auto()       # Mixed language
    TRADE_PIDGIN = auto()  # Simplified trade language


@dataclass
class Vocabulary:
    """
    A vocabulary is a collection of words in a language.

    Each word has:
    - A concept it represents
    - A frequency of use
    - A phonetic form (simplified as a string)
    """

    words: dict[str, dict] = field(default_factory=dict)
    # word -> {concept: str, frequency: float, phonemes: str}

    def add_word(
        self,
        word: str,
        concept: str,
        phonemes: str,
        frequency: float = 0.1,
    ) -> None:
        """Add a word to the vocabulary."""
        self.words[word] = {
            "concept": concept,
            "phonemes": phonemes,
            "frequency": frequency,
            "created_tick": 0,
        }

    def get_word_for_concept(self, concept: str) -> str | None:
        """Get the most frequent word for a concept."""
        candidates = [
            (w, data["frequency"])
            for w, data in self.words.items()
            if data["concept"] == concept
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda x: x[1])[0]

    def get_concept_for_word(self, word: str) -> str | None:
        """Get the concept a word represents."""
        return self.words.get(word, {}).get("concept")

    def merge_vocabulary(self, other: "Vocabulary", rate: float) -> None:
        """
        Merge another vocabulary into this one.

        Rate determines how much to adopt (0-1).
        """
        for word, data in other.words.items():
            if word not in self.words:
                self.add_word(
                    word,
                    data["concept"],
                    data["phonemes"],
                    data["frequency"] * rate,
                )
            else:
                # Take the more frequent version
                if data["frequency"] > self.words[word]["frequency"]:
                    self.words[word] = data.copy()

    def get_size(self) -> int:
        """Get the number of words in the vocabulary."""
        return len(self.words)


# ---------------------------------------------------------------------------
# Dialect
# ---------------------------------------------------------------------------


@dataclass
class Dialect:
    """
    A dialect is a regional/social variation of a language.

    Dialects differ in:
    - Vocabulary (different words for same concepts)
    - Phonology (different sounds/pronunciations)
    - Grammar (different word order/rules)
    - Pragmatics (different social usage)
    """

    dialect_id: str
    name: str
    parent_language_id: str | None  # None for base language
    region: str  # Geographic/social region

    vocabulary: Vocabulary = field(default_factory=Vocabulary)
    phoneme_shifts: dict[str, str] = field(default_factory=dict)
    # Maps base phonemes to dialect-specific ones

    grammar_rules: dict[str, Any] = field(default_factory=dict)
    word_order: str = "SOV"  # Subject-Object-Verb, etc.

    # Statistics
    speaker_count: int = 0
    intelligibility: float = 1.0  # 0-1, mutual intelligibility with parent

    # Evolution
    divergence_rate: float = 0.0001  # Per-tick mutation rate
    last_mutation_tick: int = 0

    def mutate_phoneme(self, base: str) -> str:
        """Apply a phoneme shift mutation."""
        if base in self.phoneme_shifts:
            return self.phoneme_shifts[base]
        return base

    def mutate_vocabulary(self, rng: np.random.Generator) -> None:
        """Introduce new words or change existing ones."""
        if rng.random() > self.divergence_rate:
            return

        words = list(self.vocabulary.words.keys())
        if not words:
            return

        word = rng.choice(words)
        data = self.vocabulary.words[word]

        # Either create a synonym or shift meaning
        if rng.random() < 0.5:
            # Create a synonym (same concept, different form)
            new_word = word + rng.choice(["a", "i", "u", "ta", "ki", "na"])
            self.vocabulary.add_word(
                new_word,
                data["concept"],
                data["phonemes"],
                data["frequency"] * 0.5,
            )
        else:
            # Shift meaning slightly
            data["frequency"] *= rng.uniform(0.8, 1.2)

    def calculate_divergence(self) -> float:
        """
        Calculate how divergent this dialect is from its parent.

        Returns 0 (identical) to 1 (completely different).
        """
        if self.parent_language_id is None:
            return 0.0

        # Based on vocabulary differences
        vocab_diff = len(self.vocabulary.words) * 0.01
        phoneme_diff = len(self.phoneme_shifts) * 0.05
        grammar_diff = len(self.grammar_rules) * 0.02

        return min(1.0, (vocab_diff + phoneme_diff + grammar_diff) / 10.0)


# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------


@dataclass
class Language:
    """
    A language is a complete communication system used by a population.

    Languages contain:
    - Dialects (regional variations)
    - Shared core vocabulary
    - Grammar rules
    - Cultural associations
    """

    language_id: str
    name: str
    family: LinguisticFamily

    # Core vocabulary (shared across dialects)
    core_vocabulary: Vocabulary = field(default_factory=Vocabulary)

    # Dialects
    dialects: dict[str, Dialect] = field(default_factory=dict)
    primary_dialect_id: str | None = None

    # Grammar
    grammar_complexity: float = 0.5  # 0-1
    is_agglutinative: bool = False
    has_tone: bool = False

    # Usage
    speaker_count: int = 0
    total_speakers: int = 0  # Including learners

    # Status
    is_endangered: bool = False
    is_extinct: bool = False

    # Evolution
    age_ticks: int = 0
    ancestor_language_id: str | None = None

    def get_dialect(self, dialect_id: str) -> Dialect | None:
        """Get a dialect by ID."""
        return self.dialects.get(dialect_id)

    def get_or_create_dialect(
        self, region: str, rng: np.random.Generator
    ) -> Dialect:
        """Get or create a dialect for a region."""
        # Check for existing dialect in this region
        for dialect in self.dialects.values():
            if dialect.region == region:
                return dialect

        # Create new dialect
        dialect_id = new_entity_id()
        dialect = Dialect(
            dialect_id=dialect_id,
            name=f"{self.name} ({region})",
            parent_language_id=self.language_id,
            region=region,
            vocabulary=Vocabulary(  # Copy core vocabulary
                words={k: v.copy() for k, v in self.core_vocabulary.words.items()}
            ),
            divergence_rate=self.age_ticks * 0.000001 + 0.0001,
        )

        self.dialects[dialect_id] = dialect

        if self.primary_dialect_id is None:
            self.primary_dialect_id = dialect_id

        return dialect

    def add_concept_word(
        self, concept: str, word: str, phonemes: str, frequency: float
    ) -> None:
        """Add a core vocabulary word for a concept."""
        self.core_vocabulary.add_word(word, concept, phonemes, frequency)

        # Propagate to dialects
        for dialect in self.dialects.values():
            if word not in dialect.vocabulary.words:
                dialect.vocabulary.add_word(word, concept, phonemes, frequency)

    def calculate_mutual_intelligibility(self, other: "Language") -> float:
        """
        Calculate mutual intelligibility between this and another language.

        This is a proxy measure for language distance.
        Returns 0 (completely unintelligible) to 1 (identical).
        """
        if self.language_id == other.language_id:
            return 1.0

        # Compare core vocabularies
        self_words = set(self.core_vocabulary.words.keys())
        other_words = set(other.core_vocabulary.words.keys())

        if not self_words or not other_words:
            return 0.0

        overlap = len(self_words & other_words)
        total = len(self_words | other_words)

        vocab_similarity = overlap / total

        # Grammar similarity
        grammar_similarity = (
            1.0 if self.grammar_complexity == other.grammar_complexity
            else 0.5
        )

        return vocab_similarity * 0.7 + grammar_similarity * 0.3


# ---------------------------------------------------------------------------
# Communication
# ---------------------------------------------------------------------------


@dataclass
class CommunicationEvent:
    """A single act of communication between agents."""

    tick: int
    sender_id: EntityID
    receiver_id: EntityID
    language_id: str
    dialect_id: str

    # Content
    concept: str  # What was communicated
    word_used: str

    # Effectiveness
    understood: bool = True
    comprehension_quality: float = 1.0  # 0-1

    # Context
    context: str = ""  # social, trade, conflict, etc.
    distance: float = 0.0  # Physical distance


@dataclass
class LanguageBarrier:
    """
    A language barrier between two groups.

    Created when mutual intelligibility is low.
    """

    group_a: str  # dialect or language ID
    group_b: str  # dialect or language ID
    barrier_strength: float  # 0-1, how strong the barrier is
    source_language_a: str | None = None
    source_language_b: str | None = None


# ---------------------------------------------------------------------------
# LanguageSystem — the main language manager
# ---------------------------------------------------------------------------


class LanguageSystem:
    """
    Manages all languages and linguistic phenomena in the world.

    Key responsibilities:
    - Create and evolve languages
    - Track dialect formation
    - Handle linguistic communication
    - Manage language birth and death
    - Track linguistic borrowing
    - Measure linguistic diversity

    Linguistic evolution rules:
    - Isolation → dialect divergence
    - Contact → borrowing
    - Prestige → language spread
    - Small population → language extinction
    """

    def __init__(
        self, config: CultureConfig, world: "World", seed: int = 42
    ) -> None:
        self.config = config
        self.world = world
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Languages
        self._languages: dict[str, Language] = {}
        self._primary_language_id: str | None = None

        # Agent language assignments
        self._agent_languages: dict[EntityID, list[str]] = {}  # agent -> language_ids
        self._agent_dialects: dict[EntityID, str] = {}  # agent -> dialect_id

        # Communication history
        self._communication_log: list[CommunicationEvent] = []
        self._communication_by_concept: dict[str, list[int]] = defaultdict(list)

        # Language barriers
        self._barriers: list[LanguageBarrier] = []

        # Statistics
        self._total_communications = 0
        self._total_language_changes = 0
        self._misunderstandings = 0

        # Initialize base language
        self._create_base_language()

    def _create_base_language(self) -> None:
        """Create the initial language for the population."""
        lang = Language(
            language_id=new_entity_id(),
            name="Proto-Language",
            family=LinguisticFamily.NATIVE,
            grammar_complexity=0.3,
        )

        # Add core vocabulary for basic concepts
        core_concepts = [
            ("food", "noma", "n-m"),
            ("water", "waka", "w-k"),
            ("fire", "pira", "p-r"),
            ("person", "homo", "h-m"),
            ("family", "sika", "s-k"),
            ("friend", "amiko", "m-k"),
            ("enemy", "inimiko", "nm-k"),
            ("give", "doni", "d-n"),
            ("take", "preni", "p-r"),
            ("go", "iri", "i-r"),
            ("come", "veni", "v-n"),
            ("see", "vidi", "v-d"),
            ("speak", "diri", "d-r"),
            ("good", "bona", "b-n"),
            ("bad", "malbono", "ml-b"),
            ("big", "grand", "g-r"),
            ("small", "malgrand", "ml-g"),
            ("death", "morto", "m-r"),
            ("life", "vivo", "v-v"),
            ("animal", "bestio", "b-s"),
            ("tree", "arbo", "r-b"),
            ("stone", "petro", "p-t"),
            ("sun", "suno", "s-n"),
            ("moon", "luno", "l-n"),
            ("war", "milito", "m-l-t"),
            ("trade", "komerc", "k-m-r"),
            ("work", "laboro", "l-b-r"),
            ("home", "domo", "d-m"),
        ]

        for concept, word, phonemes in core_concepts:
            lang.add_concept_word(concept, word, phonemes, frequency=0.8)

        self._languages[lang.language_id] = lang
        self._primary_language_id = lang.language_id

        # Create initial dialect
        dialect = lang.get_or_create_dialect("proto", self._rng)
        lang.primary_dialect_id = dialect.dialect_id
        lang.speaker_count = 0

    def assign_language(
        self, agent_id: EntityID, language_id: str, dialect_id: str | None = None
    ) -> None:
        """Assign a language and dialect to an agent."""
        if agent_id not in self._agent_languages:
            self._agent_languages[agent_id] = []

        if language_id not in self._agent_languages[agent_id]:
            self._agent_languages[agent_id].append(language_id)

        lang = self._languages.get(language_id)
        if lang and dialect_id is None:
            # Use primary dialect
            if lang.primary_dialect_id:
                self._agent_dialects[agent_id] = lang.primary_dialect_id
        else:
            self._agent_dialects[agent_id] = dialect_id or ""

        # Update speaker count
        if lang:
            lang.speaker_count += 1
            lang.total_speakers += 1

    def get_agent_language(self, agent_id: EntityID) -> str | None:
        """Get an agent's primary language."""
        langs = self._agent_languages.get(agent_id, [])
        return langs[0] if langs else None

    def get_agent_dialect(self, agent_id: EntityID) -> str | None:
        """Get an agent's dialect."""
        return self._agent_dialects.get(agent_id)

    def communicate(
        self,
        sender_id: EntityID,
        receiver_id: EntityID,
        concept: str,
        context: str = "social",
        tick: int = 0,
    ) -> CommunicationEvent | None:
        """
        Attempt communication between two agents.

        Returns a CommunicationEvent with the result.
        """
        sender_lang = self.get_agent_language(sender_id)
        receiver_lang = self.get_agent_language(receiver_id)

        if sender_lang is None or receiver_lang is None:
            return None

        sender_dialect = self.get_agent_dialect(sender_id)
        receiver_dialect = self.get_agent_dialect(receiver_id)

        # Get language objects
        sender_lang_obj = self._languages.get(sender_lang)
        receiver_lang_obj = self._languages.get(receiver_lang)

        if sender_lang_obj is None or receiver_lang_obj is None:
            return None

        # Find the word for this concept
        word = sender_lang_obj.core_vocabulary.get_word_for_concept(concept)

        if word is None:
            return None

        # Check mutual intelligibility
        intelligibility = sender_lang_obj.calculate_mutual_intelligibility(
            receiver_lang_obj
        )

        # Dialect difference reduces intelligibility
        if sender_dialect != receiver_dialect:
            intelligibility *= 0.8  # Dialect barrier

        # Check comprehension
        sender_agent = self.world.get_agent(sender_id)
        receiver_agent = self.world.get_agent(receiver_id)

        comprehension_quality = intelligibility
        if receiver_agent:
            # Intelligence helps comprehension
            comprehension_quality *= (1.0 + receiver_agent.attributes.intelligence * 0.3)

        understood = self._rng.random() < comprehension_quality

        if not understood:
            self._misunderstandings += 1

        # Get receiver's dialect for the event
        event = CommunicationEvent(
            tick=tick,
            sender_id=sender_id,
            receiver_id=receiver_id,
            language_id=sender_lang,
            dialect_id=sender_dialect or "",
            concept=concept,
            word_used=word if understood else "[unclear]",
            understood=understood,
            comprehension_quality=comprehension_quality,
            context=context,
        )

        self._communication_log.append(event)
        self._total_communications += 1

        # Track concept communication frequency
        self._communication_by_concept[concept].append(tick)

        return event

    def try_language_change(
        self,
        agent_id: EntityID,
        new_language_id: str,
        new_dialect_id: str | None = None,
    ) -> bool:
        """
        Attempt to have an agent switch language.

        Language change requires:
        - Sufficient contact with new language speakers
        - Time to learn (cultural_mobility_rate from config)
        """
        if self._agent_languages.get(agent_id, []) == [new_language_id]:
            return False  # Already speaks this language

        agent = self.world.get_agent(agent_id)
        if agent is None:
            return False

        # Intelligence makes learning easier
        learn_rate = (
            self.config.language_mobility_rate *
            (1.0 + agent.attributes.intelligence * 0.5)
        )

        success = self._rng.random() < learn_rate

        if success:
            old_lang = self.get_agent_language(agent_id)
            if old_lang:
                old_lang_obj = self._languages.get(old_lang)
                if old_lang_obj:
                    old_lang_obj.speaker_count = max(0, old_lang_obj.speaker_count - 1)

            self.assign_language(agent_id, new_language_id, new_dialect_id)
            self._total_language_changes += 1

            # Log language change as cultural event
            self.world.record_event(
                "language_change",
                subject_id=agent_id,
                tick=self.world.tick,
                narrative=f"Agent switched from {old_lang} to {new_language_id}",
            )

        return success

    def create_dialect(
        self,
        language_id: str,
        region: str,
        isolation_factor: float = 0.5,
    ) -> Dialect | None:
        """
        Create a new dialect of a language.

        Isolation factor: 0 (lots of contact) to 1 (complete isolation)
        Higher isolation → faster divergence.
        """
        lang = self._languages.get(language_id)
        if lang is None:
            return None

        dialect = lang.get_or_create_dialect(region, self._rng)

        # Set divergence rate based on isolation
        dialect.divergence_rate = (
            self.config.dialect_divergence_rate * (0.5 + isolation_factor)
        )

        return dialect

    def absorb_language(
        self,
        absorber_lang_id: str,
        absorbed_lang_id: str,
    ) -> bool:
        """
        Have one language absorb another (prestige spread).

        The absorbed language's speakers switch to the absorber.
        """
        absorber = self._languages.get(absorber_lang_id)
        absorbed = self._languages.get(absorbed_lang_id)

        if absorber is None or absorbed is None:
            return False

        # Calculate prestige advantage
        prestige_ratio = absorber.speaker_count / max(1, absorbed.speaker_count)

        if prestige_ratio < 1.5:
            return False  # Not enough prestige advantage

        # Absorb vocabulary
        absorber.core_vocabulary.merge_vocabulary(
            absorbed.core_vocabulary, rate=0.3
        )

        # Mark absorbed language as endangered
        absorbed.is_endangered = True

        return True

    def evolve_dialects(self, tick: int) -> int:
        """Evolve all dialects (mutation, divergence)."""
        mutations = 0

        for lang in self._languages.values():
            if lang.is_extinct:
                continue

            for dialect in lang.dialects.values():
                old_size = dialect.vocabulary.get_size()
                dialect.mutate_vocabulary(self._rng)
                new_size = dialect.vocabulary.get_size()

                if new_size != old_size:
                    mutations += 1

                # Update divergence
                divergence = dialect.calculate_divergence()
                dialect.intelligibility = 1.0 - divergence

            lang.age_ticks += 1

        return mutations

    def update(self, tick: int) -> None:
        """Update language system for the tick."""
        # Evolve dialects
        self.evolve_dialects(tick)

        # Check for language birth/death
        self._check_language_vitality(tick)

        # Occasionally create language barriers
        self._update_barriers()

    def _check_language_vitality(self, tick: int) -> None:
        """Check and update language vitality (birth/death)."""
        # Check endangered languages
        for lang in self._languages.values():
            if lang.is_extinct:
                continue

            if lang.speaker_count < 5:
                lang.is_endangered = True

            if lang.speaker_count == 0 and lang.total_speakers > 0:
                lang.is_extinct = True

    def _update_barriers(self) -> None:
        """Update language barriers based on current state."""
        # Rebuild barriers
        new_barriers: list[LanguageBarrier] = []

        for lang_a in self._languages.values():
            for lang_b in self._languages.values():
                if lang_a.language_id >= lang_b.language_id:
                    continue
                if lang_a.is_extinct or lang_b.is_extinct:
                    continue

                intelligibility = lang_a.calculate_mutual_intelligibility(lang_b)
                barrier_strength = 1.0 - intelligibility

                if barrier_strength > 0.2:
                    new_barriers.append(LanguageBarrier(
                        group_a=lang_a.language_id,
                        group_b=lang_b.language_id,
                        barrier_strength=barrier_strength,
                        source_language_a=lang_a.name,
                        source_language_b=lang_b.name,
                    ))

        self._barriers = new_barriers

    def get_stats(self) -> dict[str, Any]:
        """Get language statistics."""
        return {
            "total_languages": len(self._languages),
            "primary_language": self._primary_language_id,
            "active_languages": sum(
                1 for l in self._languages.values() if not l.is_extinct
            ),
            "total_dialects": sum(
                len(l.dialects) for l in self._languages.values()
            ),
            "endangered_languages": sum(
                1 for l in self._languages.values() if l.is_endangered
            ),
            "extinct_languages": sum(
                1 for l in self._languages.values() if l.is_extinct
            ),
            "total_communications": self._total_communications,
            "total_misunderstandings": self._misunderstandings,
            "misunderstanding_rate": (
                self._misunderstandings / max(1, self._total_communications)
            ),
            "total_language_changes": self._total_language_changes,
            "language_barriers": len(self._barriers),
            "avg_intelligibility": (
                1.0 - sum(b.barrier_strength for b in self._barriers) /
                max(1, len(self._barriers)) if self._barriers else 1.0
            ),
        }
