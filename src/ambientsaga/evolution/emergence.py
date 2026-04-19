"""
Emergence Detector — Identifying Novel Behaviors and Institutions

This module provides tools for detecting emergence:
- GENOTYPIC EMERGENCE: New gene combinations that didn't exist before
- BEHAVIORAL EMERGENCE: New behaviors that arise from gene execution
- SOCIAL EMERGENCE: New social patterns from agent interactions
- INSTITUTIONAL EMERGENCE: New social structures that provide function

Key Concept: EMERGENCE is when the whole becomes greater than the sum of parts.
We detect emergence by tracking:
1. Innovation events (new genes/patterns appear)
2. Pattern clustering (multiple patterns that seem related)
3. Functional coherence (patterns that work together to achieve goals)
4. Stability (patterns that persist across generations)

The emergence detector helps answer questions like:
- When did social security-like behavior first emerge?
- How long did it take for trade to become a norm?
- Which behaviors are most likely to lead to new institutions?
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict
import math


@dataclass
class EmergenceEvent:
    """An event where something emergent was detected."""

    event_type: str  # "genotypic", "behavioral", "social", "institutional"
    tick: int
    description: str
    novelty_score: float  # How novel this emergence is (0-1)
    stability_score: float  # How stable this seems (0-1)
    affected_agents: int  # How many agents this affects
    related_patterns: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class EmergedBehavior:
    """A behavior that has emerged from evolution."""

    behavior_id: str
    name: str
    gene_hashes: set[str]
    origin_tick: int
    first_appearance: Optional[int] = None
    spread_history: list[int] = field(default_factory=list)  # Adoption over time
    stability: float = 1.0  # How often it survives to next generation
    novelty: float = 1.0  # How novel this is
    functionality: str = ""  # What function this serves
    social_context: str = ""  # Where this emerged

    def get_adoption_rate(self) -> float:
        """Calculate adoption rate from history."""
        if len(self.spread_history) < 2:
            return 0.0
        return (self.spread_history[-1] - self.spread_history[0]) / max(1, self.spread_history[0])


@dataclass
class EmergedInstitution:
    """A social institution that has emerged from cultural evolution."""

    institution_id: str
    name: str
    description: str
    origin_tick: int
    constituent_behaviors: list[str] = field(default_factory=list)
    adoption_history: list[int] = field(default_factory=list)
    purpose: str = ""  # What function this institution serves
    complexity: float = 1.0  # How complex the institution is
    stability: float = 1.0  # How stable across generations
    novelty: float = 1.0  # How novel this institution is

    # Institutional properties
    is_voluntary: bool = True  # Can agents opt out?
    is_enforced: bool = False  # Is there punishment for non-compliance?
    has_leadership: bool = False  # Are there designated leaders?
    is_recursive: bool = False  # Can institutions contain sub-institutions?


class EmergenceDetector:
    """
    Detects emergent behaviors and institutions in the simulation.

    The emergence detector tracks:
    1. GENOTYPIC INNOVATIONS: New genes that appear
    2. BEHAVIORAL PATTERNS: Combinations of genes that produce specific behaviors
    3. SOCIAL NORMS: Consistent behavioral patterns across multiple agents
    4. INSTITUTIONS: Stable social structures that provide functions

    Detection methods:
    - Novelty detection: Is this gene/pattern new?
    - Pattern clustering: Do multiple patterns cluster together?
    - Functional analysis: Does this pattern serve a coherent purpose?
    - Stability analysis: Does this persist across generations?
    """

    def __init__(
        self,
        novelty_threshold: float = 0.7,
        stability_threshold: float = 0.5,
        institution_min_agents: int = 5,
        institution_min_stability: float = 0.3,
        rng: Optional[random.Random] = None,
    ):
        """
        Initialize the emergence detector.

        Args:
            novelty_threshold: Minimum novelty to flag as emergent (0-1)
            stability_threshold: Minimum stability to be considered stable
            institution_min_agents: Minimum agents adopting to form institution
            institution_min_stability: Minimum stability for institution
            rng: Random number generator
        """
        self.novelty_threshold = novelty_threshold
        self.stability_threshold = stability_threshold
        self.institution_min_agents = institution_min_agents
        self.institution_min_stability = institution_min_stability
        self.rng = rng or random.Random()

        # Tracking
        self.emergence_events: list[EmergenceEvent] = []
        self.emerged_behaviors: dict[str, EmergedBehavior] = {}
        self.emerged_institutions: dict[str, EmergedInstitution] = {}

        # Historical tracking for analysis
        self.gene_innovation_history: list[dict] = []
        self.behavior_history: list[dict] = []
        self.institution_history: list[dict] = []

        # Statistics
        self.total_innovations = 0
        self.total_behaviors = 0
        self.total_institutions = 0

    # =========================================================================
    # Genotypic Emergence Detection
    # =========================================================================

    def track_innovation(
        self,
        gene_hash: str,
        gene_type: str,
        tick: int,
        parent_hashes: Optional[list[str]] = None,
    ) -> Optional[EmergenceEvent]:
        """
        Track a genetic innovation (new gene or gene combination).

        Args:
            gene_hash: Unique hash of the gene
            gene_type: Type of gene
            tick: When this innovation occurred
            parent_hashes: Hashes of parent genes (for crossover tracking)

        Returns:
            EmergenceEvent if this is a novel innovation
        """
        # Check if this is truly novel (no ancestor in history)
        novelty = self._calculate_novelty(gene_hash, gene_type, parent_hashes)

        if novelty >= self.novelty_threshold:
            event = EmergenceEvent(
                event_type="genotypic",
                tick=tick,
                description=f"New {gene_type} gene innovation",
                novelty_score=novelty,
                stability_score=1.0,  # New innovations start maximally stable
                affected_agents=1,
                metadata={
                    "gene_hash": gene_hash,
                    "gene_type": gene_type,
                    "parent_hashes": parent_hashes or [],
                },
            )
            self.emergence_events.append(event)
            self.total_innovations += 1

            # Track in history
            self.gene_innovation_history.append({
                "tick": tick,
                "gene_hash": gene_hash,
                "gene_type": gene_type,
                "novelty": novelty,
            })

            return event

        return None

    def _calculate_novelty(
        self,
        gene_hash: str,
        gene_type: str,
        parent_hashes: Optional[list[str]],
    ) -> float:
        """
        Calculate how novel a gene is.

        Novelty is based on:
        1. Has this exact gene appeared before? (0 = duplicate, 1 = completely new)
        2. Have similar genes appeared? (higher for rare gene types)
        3. Is this a new combination? (higher for new parent combinations)
        """
        novelty = 0.5  # Base novelty

        # Check if exact gene exists in history
        gene_in_history = any(
            g["gene_hash"] == gene_hash for g in self.gene_innovation_history
        )
        if gene_in_history:
            return 0.0  # Not novel at all

        novelty += 0.2  # Exact novelty bonus

        # Check gene type rarity
        type_count = sum(1 for g in self.gene_innovation_history if g["gene_type"] == gene_type)
        if type_count == 0:
            novelty += 0.2  # First of this type
        else:
            novelty += 0.1 / (1 + type_count)  # Rarer = more novel

        # Check for new combinations
        if parent_hashes:
            for parent in parent_hashes:
                parent_exists = any(
                    parent in g.get("parent_hashes", [])
                    for g in self.gene_innovation_history
                )
                if not parent_exists:
                    novelty += 0.1  # New combination
                    break

        return min(1.0, novelty)

    # =========================================================================
    # Behavioral Emergence Detection
    # =========================================================================

    def detect_behavioral_emergence(
        self,
        gene_cluster: list[str],  # Hashes of genes that execute together
        tick: int,
        execution_context: str,
        outcome: dict,
    ) -> Optional[EmergedBehavior]:
        """
        Detect when a behavioral pattern emerges.

        A behavior emerges when:
        1. Multiple genes execute together consistently
        2. The combination produces a coherent outcome
        3. The behavior persists over time

        Args:
            gene_cluster: Genes that are executing together
            tick: Current tick
            execution_context: Where this is happening
            outcome: Result of the behavior

        Returns:
            EmergedBehavior if this is a new emergent behavior
        """
        if len(gene_cluster) < 1:
            return None

        # Create behavior ID from genes
        if len(gene_cluster) == 1:
            behavior_id = f"behavior_{gene_cluster[0][:20]}"
        else:
            behavior_id = f"behavior_{'_'.join(sorted(gene_cluster)[:3])}"

        # Check if this behavior already exists
        if behavior_id in self.emerged_behaviors:
            behavior = self.emerged_behaviors[behavior_id]
            behavior.spread_history.append(tick)
            return None

        # Check if behavior is coherent (genes work together)
        coherence = self._calculate_behavioral_coherence(gene_cluster)
        if coherence < 0.2:
            return None  # Not coherent enough

        # Calculate novelty
        novelty = self._calculate_behavioral_novelty(gene_cluster)

        # Create emerged behavior
        behavior = EmergedBehavior(
            behavior_id=behavior_id,
            name=self._generate_behavior_name(gene_cluster),
            gene_hashes=set(gene_cluster),
            origin_tick=tick,
            first_appearance=tick,
            spread_history=[tick],
            novelty=novelty,
            functionality=execution_context,
            social_context=execution_context,
        )

        self.emerged_behaviors[behavior_id] = behavior
        self.total_behaviors += 1

        # Record emergence event
        event = EmergenceEvent(
            event_type="behavioral",
            tick=tick,
            description=f"Emergent behavior: {behavior.name}",
            novelty_score=novelty,
            stability_score=1.0,
            affected_agents=1,
            related_patterns=[behavior_id],
            metadata={"gene_count": len(gene_cluster), "context": execution_context},
        )
        self.emergence_events.append(event)

        self.behavior_history.append({
            "tick": tick,
            "behavior_id": behavior_id,
            "name": behavior.name,
            "novelty": novelty,
            "coherence": coherence,
        })

        return behavior

    def _calculate_behavioral_coherence(self, gene_cluster: list[str]) -> float:
        """
        Calculate how coherent a cluster of genes is.

        Coherence is higher when:
        1. Genes are frequently executed together
        2. The combination produces consistent outcomes
        3. The genes are temporally close
        """
        # Simplified: base coherence
        coherence = 0.7

        # More genes = potentially more complex = less coherent (but not too much)
        coherence -= len(gene_cluster) * 0.02

        return max(0.0, min(1.0, coherence))

    def _calculate_behavioral_novelty(self, gene_cluster: list[str]) -> float:
        """Calculate novelty of a behavioral pattern."""
        novelty = 0.5

        # Check how many genes are new
        for gene_hash in gene_cluster:
            gene_in_history = any(
                gene_hash in b.gene_hashes
                for b in self.emerged_behaviors.values()
            )
            if not gene_in_history:
                novelty += 0.1

        return min(1.0, novelty)

    def _generate_behavior_name(self, gene_cluster: list[str]) -> str:
        """Generate a human-readable name for a behavior."""
        # Extract gene types from gene hashes
        # Gene hashes are like "agent_000001_id_REST_12345" or "agent_000001_GATHER_12345"
        gene_types = []
        for gh in gene_cluster:
            # Try to find a known gene type in the hash
            parts = gh.upper().split('_')
            for p in parts:
                if p in ['REST', 'WANDER', 'GATHER', 'EXPLORE', 'EXCHANGE', 'HELP',
                         'SHARE', 'TRADE', 'BUILD', 'FARM', 'HUNT', 'FISH', 'FORAGE',
                         'FIGHT', 'FLEE', 'APPROACH', 'AVOID', 'ATTACK', 'DEFEND',
                         'INFORM', 'TEACH', 'LEARN', 'COPY', 'SIGNAL', 'MIMIC',
                         'CONDITIONAL', 'SEQUENCE', 'LOOP', 'SELECT', 'PRIMITIVE',
                         'MOVE', 'IDLE', 'WORK', 'CRAFT', 'SLEEP', 'EAT', 'DRINK']:
                    gene_types.append(p)
                    break

        if gene_types:
            # Use the most common gene type
            from collections import Counter
            most_common = Counter(gene_types).most_common(1)[0][0]
            return f"{most_common.lower()}_behavior"

        return f"emergent_pattern"

    # =========================================================================
    # Social Norm Emergence Detection
    # =========================================================================

    def detect_social_norm(
        self,
        behavior_pattern: str,
        adoption_rate: float,
        enforcement_level: float,
        tick: int,
    ) -> Optional[dict]:
        """
        Detect when a social norm emerges.

        A norm emerges when:
        1. A behavior pattern is widely adopted (>50% of population)
        2. The behavior is consistent across generations
        3. There may be enforcement (punishment for violation)

        Args:
            behavior_pattern: The behavior pattern that became a norm
            adoption_rate: Fraction of population adopting this behavior
            enforcement_level: Level of punishment for non-compliance (0-1)
            tick: Current tick

        Returns:
            Dict with norm details if a norm emerged
        """
        if adoption_rate < 0.3:
            return None  # Not enough adoption for a norm

        # Calculate norm strength
        strength = adoption_rate * (1 + enforcement_level) / 2

        if strength >= 0.5:
            norm = {
                "pattern": behavior_pattern,
                "adoption_rate": adoption_rate,
                "enforcement_level": enforcement_level,
                "strength": strength,
                "origin_tick": tick,
                "is_emergent": True,
            }

            # Record event
            event = EmergenceEvent(
                event_type="social",
                tick=tick,
                description=f"Social norm emerged: {behavior_pattern}",
                novelty_score=strength,
                stability_score=adoption_rate,
                affected_agents=int(adoption_rate * 1000),
            )
            self.emergence_events.append(event)

            return norm

        return None

    # =========================================================================
    # Institutional Emergence Detection
    # =========================================================================

    def detect_institutional_emergence(
        self,
        related_behaviors: list[EmergedBehavior],
        tick: int,
        context: str,
    ) -> Optional[EmergedInstitution]:
        """
        Detect when a social institution emerges.

        An institution emerges when:
        1. Multiple related behaviors cluster together
        2. The cluster provides a coherent social function
        3. The institution is stable across generations
        4. Agents adopt the institution collectively

        Examples of emergent institutions:
        - Trade systems (exchange behaviors + reputation + contracts)
        - Social welfare (sharing + mutual aid + collective storage)
        - Governance (leadership + rules + enforcement)
        - Marriage/family structures (pair bonding + child-rearing + inheritance)

        Args:
            related_behaviors: Behaviors that might form an institution
            tick: Current tick
            context: Social context

        Returns:
            EmergedInstitution if an institution emerged
        """
        if len(related_behaviors) < 2:
            return None

        # Create institution ID based only on context (not count)
        # This ensures we only create ONE institution per behavior type
        institution_id = f"institution_{context}"
        if institution_id in self.emerged_institutions:
            return None  # Already exists

        # Calculate institutional properties
        avg_stability = sum(b.stability for b in related_behaviors) / len(related_behaviors)
        avg_novelty = sum(b.novelty for b in related_behaviors) / len(related_behaviors)

        # An institution needs reasonable stability
        if avg_stability < self.institution_min_stability:
            return None

        # Create institution
        institution = EmergedInstitution(
            institution_id=institution_id,
            name=self._generate_institution_name(context, related_behaviors),
            description=f"Institution formed from {len(related_behaviors)} behaviors",
            origin_tick=tick,
            constituent_behaviors=[b.behavior_id for b in related_behaviors],
            purpose=context,
            complexity=len(related_behaviors),
            stability=avg_stability,
            novelty=avg_novelty,
            is_voluntary=True,
            is_enforced=False,
        )

        self.emerged_institutions[institution_id] = institution
        self.total_institutions += 1

        # Record emergence event
        event = EmergenceEvent(
            event_type="institutional",
            tick=tick,
            description=f"Institution emerged: {institution.name}",
            novelty_score=avg_novelty,
            stability_score=avg_stability,
            affected_agents=len(related_behaviors) * 10,
            related_patterns=[b.behavior_id for b in related_behaviors],
            metadata={
                "behaviors": len(related_behaviors),
                "purpose": context,
            },
        )
        self.emergence_events.append(event)

        self.institution_history.append({
            "tick": tick,
            "institution_id": institution_id,
            "name": institution.name,
            "complexity": institution.complexity,
            "novelty": institution.novelty,
        })

        return institution

    def _generate_institution_name(
        self,
        context: str,
        behaviors: list[EmergedBehavior],
    ) -> str:
        """Generate a name for an emergent institution."""
        # Map common contexts to human-readable names
        context_names = {
            "exchange": "Trade System",
            "sharing": "Mutual Aid Network",
            "cooperation": "Cooperative Organization",
            "leadership": "Governance Structure",
            "teaching": "Educational Institution",
            "reproduction": "Family Structure",
            "protection": "Defense System",
            "resource": "Resource Management",
        }

        base_name = context_names.get(context, context.title())
        return f"{base_name}_{len(self.emerged_institutions)}"

    # =========================================================================
    # Analysis and Reporting
    # =========================================================================

    def get_emergence_summary(self) -> dict:
        """Get a summary of all emergence events."""
        recent_events = self.emergence_events[-100:]

        return {
            "total_innovations": self.total_innovations,
            "total_behaviors": self.total_behaviors,
            "total_institutions": self.total_institutions,
            "recent_emergence_events": len(recent_events),
            "emergence_rate": len(self.emergence_events) / max(1, self.emergence_events[-1].tick) if self.emergence_events else 0,
            "innovation_velocity": self._calculate_innovation_velocity(),
            "institution_emergence_rate": self.total_institutions / max(1, len(self.behavior_history)),
        }

    def _calculate_innovation_velocity(self) -> float:
        """Calculate how fast innovations are appearing."""
        if len(self.gene_innovation_history) < 10:
            return 0.0

        recent = self.gene_innovation_history[-100:]
        if len(recent) < 2:
            return 0.0

        # Innovations per 1000 ticks
        time_span = recent[-1]["tick"] - recent[0]["tick"]
        if time_span == 0:
            return 0.0

        return len(recent) / time_span * 1000

    def get_recent_emergence_events(
        self,
        event_type: Optional[str] = None,
        last_n: int = 50,
    ) -> list[dict]:
        """Get recent emergence events."""
        events = self.emergence_events[-last_n:]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return [
            {
                "type": e.event_type,
                "tick": e.tick,
                "description": e.description,
                "novelty": e.novelty_score,
                "stability": e.stability_score,
                "affected_agents": e.affected_agents,
            }
            for e in events
        ]

    def get_emerged_institutions_summary(self) -> list[dict]:
        """Get summary of all emerged institutions."""
        return [
            {
                "id": inst.institution_id,
                "name": inst.name,
                "purpose": inst.purpose,
                "complexity": inst.complexity,
                "stability": inst.stability,
                "origin_tick": inst.origin_tick,
                "is_voluntary": inst.is_voluntary,
                "is_enforced": inst.is_enforced,
            }
            for inst in self.emerged_institutions.values()
        ]

    def detect_social_security_like_emergence(self) -> Optional[dict]:
        """
        Specifically detect social security-like emergent institutions.

        This looks for:
        - Sharing patterns
        - Mutual aid patterns
        - Collective resource pooling
        - Age-based or vulnerability-based support
        """
        # Look for institutions with sharing/mutual aid purpose
        for inst in self.emerged_institutions.values():
            if "share" in inst.purpose.lower() or "mutual" in inst.purpose.lower():
                return {
                    "institution_id": inst.institution_id,
                    "name": inst.name,
                    "description": "Social security-like emergent institution detected",
                    "origin_tick": inst.origin_tick,
                    "stability": inst.stability,
                    "behaviors": inst.constituent_behaviors,
                }

        return None

    def reset(self) -> None:
        """Reset all emergence tracking."""
        self.emergence_events.clear()
        self.emerged_behaviors.clear()
        self.emerged_institutions.clear()
        self.gene_innovation_history.clear()
        self.behavior_history.clear()
        self.institution_history.clear()
        self.total_innovations = 0
        self.total_behaviors = 0
        self.total_institutions = 0
