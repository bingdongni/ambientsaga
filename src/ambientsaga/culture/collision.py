"""
Cultural Collision and Emergence System.

Handles the emergent dynamics when different cultures encounter each other:
- Cultural encounter detection
- Cultural collision and conflict
- Cultural adaptation and synthesis
- Cultural innovation
- Cultural dominance and resistance
- Syncretism and cultural merging
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    pass


class CollisionType(Enum):
    """Types of cultural collision."""
    PEACEFUL_TRADE = auto()
    CULTURAL_EXCHANGE = auto()
    CULTURAL_CONFLICT = auto()
    CULTURAL_DOMINANCE = auto()
    CULTURAL_RESISTANCE = auto()
    CULTURAL_SYNTHESIS = auto()
    CULTURAL_DIFFUSION = auto()
    CULTURAL_ASSIMILATION = auto()


@dataclass
class CulturalEncounter:
    """An encounter between agents from different cultures."""
    encounter_id: str
    agent_a_id: str
    agent_b_id: str
    culture_a: str  # culture identifier
    culture_b: str  # culture identifier
    position: tuple[int, int]
    tick: int
    collision_type: CollisionType
    outcome: str = ""
    cultural_exchange: dict[str, Any] = field(default_factory=dict)
    conflict_level: float = 0.0  # 0-1
    resolved: bool = False


@dataclass
class CulturalSynthesis:
    """A new cultural element synthesized from multiple cultures."""
    synthesis_id: str
    source_cultures: list[str]
    source_beliefs: list[str]
    new_proposition: str
    tick_created: int
    adoption_count: int = 0
    stability: float = 0.5  # Will it persist?
    description: str = ""


@dataclass
class CulturalConflict:
    """A conflict between cultural elements."""
    conflict_id: str
    culture_a: str
    culture_b: str
    conflicting_beliefs: tuple[str, str]
    tick_started: int
    intensity: float = 0.5
    resolution_type: str = ""  # "dominance", "synthesis", "partition", "persistence"
    resolved: bool = False
    tick_resolved: int | None = None


@dataclass
class CulturalDiffusion:
    """Cultural element spreading between groups."""
    diffusion_id: str
    source_culture: str
    target_culture: str
    element: str  # belief, norm, practice, etc.
    tick_started: int
    spread_rate: float = 0.0
    penetration_level: float = 0.0  # How deeply it penetrated
    resistance_met: float = 0.0  # How much resistance encountered


class CulturalCollisionSystem:
    """
    Manages cultural encounters, collisions, and emergence.

    This system handles:
    1. Detecting cultural encounters when agents from different cultures meet
    2. Processing cultural collision (trade, exchange, conflict)
    3. Detecting and resolving cultural conflicts
    4. Facilitating cultural synthesis when compatible elements merge
    5. Tracking cultural diffusion and adoption
    6. Modeling cultural dominance and resistance
    """

    def __init__(self, seed: int = 42):
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Cultural encounters
        self._encounters: list[CulturalEncounter] = []
        self._next_encounter_id = 0

        # Cultural syntheses
        self._syntheses: list[CulturalSynthesis] = []
        self._next_synthesis_id = 0

        # Cultural conflicts
        self._conflicts: list[CulturalConflict] = []
        self._next_conflict_id = 0

        # Cultural diffusion
        self._diffusions: list[CulturalDiffusion] = []
        self._next_diffusion_id = 0

        # Culture tracking: culture_id -> agent_ids
        self._culture_agents: dict[str, set[str]] = {}

        # Culture definitions
        self._cultures: dict[str, dict[str, Any]] = {}

        # Statistics
        self._stats = {
            "total_encounters": 0,
            "peaceful_encounters": 0,
            "conflict_encounters": 0,
            "syntheses": 0,
            "assimilations": 0,
            "resistances": 0,
        }

    def register_culture(self, culture_id: str, culture_data: dict[str, Any]) -> None:
        """Register a culture with its characteristics."""
        self._cultures[culture_id] = culture_data

    def register_agent_culture(self, agent_id: str, culture_id: str) -> None:
        """Register an agent's cultural affiliation."""
        if culture_id not in self._culture_agents:
            self._culture_agents[culture_id] = set()
        self._culture_agents[culture_id].add(agent_id)

    def detect_encounter(
        self,
        agent_a_id: str,
        agent_b_id: str,
        culture_a: str,
        culture_b: str,
        position: tuple[int, int],
        tick: int,
    ) -> CulturalEncounter | None:
        """Detect a cultural encounter between two agents."""
        if culture_a == culture_b:
            return None  # Same culture, not a cross-cultural encounter

        # Calculate cultural similarity
        similarity = self._calculate_cultural_similarity(culture_a, culture_b)

        # Determine collision type based on similarity and random chance
        collision_type = self._determine_collision_type(similarity)

        encounter = CulturalEncounter(
            encounter_id=f"enc_{self._next_encounter_id}",
            agent_a_id=agent_a_id,
            agent_b_id=agent_b_id,
            culture_a=culture_a,
            culture_b=culture_b,
            position=position,
            tick=tick,
            collision_type=collision_type,
            conflict_level=max(0.0, 1.0 - similarity),
        )

        self._encounters.append(encounter)
        self._next_encounter_id += 1
        self._stats["total_encounters"] += 1

        if collision_type in (CollisionType.CULTURAL_CONFLICT, CollisionType.CULTURAL_DOMINANCE):
            self._stats["conflict_encounters"] += 1
        else:
            self._stats["peaceful_encounters"] += 1

        return encounter

    def _calculate_cultural_similarity(self, culture_a: str, culture_b: str) -> float:
        """Calculate similarity between two cultures."""
        c_a = self._cultures.get(culture_a, {})
        c_b = self._cultures.get(culture_b, {})

        if not c_a or not c_b:
            return 0.5  # Unknown cultures

        similarity = 0.0
        factors = 0

        # Compare values
        values_a = set(c_a.get("values", []))
        values_b = set(c_b.get("values", []))
        if values_a or values_b:
            values_similarity = len(values_a & values_b) / max(len(values_a | values_b), 1)
            similarity += values_similarity
            factors += 1

        # Compare practices
        practices_a = set(c_a.get("practices", []))
        practices_b = set(c_b.get("practices", []))
        if practices_a or practices_b:
            practices_similarity = len(practices_a & practices_b) / max(len(practices_a | practices_b), 1)
            similarity += practices_similarity
            factors += 1

        # Compare taboos
        taboos_a = set(c_a.get("taboos", []))
        taboos_b = set(c_b.get("taboos", []))
        if taboos_a or taboos_b:
            # Taboo overlap is less important (shared taboos might indicate similar fears)
            taboo_overlap = len(taboos_a & taboos_b)
            taboo_similarity = taboo_overlap / max(len(taboos_a | taboos_b), 1)
            similarity += taboo_similarity
            factors += 1

        return similarity / max(factors, 1)

    def _determine_collision_type(self, similarity: float) -> CollisionType:
        """Determine the type of collision based on cultural similarity."""
        roll = self._rng.random()

        if similarity > 0.7:
            if roll < 0.6:
                return CollisionType.CULTURAL_EXCHANGE
            elif roll < 0.9:
                return CollisionType.CULTURAL_DIFFUSION
            else:
                return CollisionType.PEACEFUL_TRADE
        elif similarity > 0.4:
            if roll < 0.3:
                return CollisionType.CULTURAL_EXCHANGE
            elif roll < 0.5:
                return CollisionType.CULTURAL_DIFFUSION
            elif roll < 0.7:
                return CollisionType.CULTURAL_CONFLICT
            elif roll < 0.9:
                return CollisionType.CULTURAL_SYNTHESIS
            else:
                return CollisionType.PEACEFUL_TRADE
        else:
            if roll < 0.2:
                return CollisionType.CULTURAL_CONFLICT
            elif roll < 0.4:
                return CollisionType.CULTURAL_DOMINANCE
            elif roll < 0.6:
                return CollisionType.CULTURAL_RESISTANCE
            elif roll < 0.8:
                return CollisionType.CULTURAL_ASSIMILATION
            else:
                return CollisionType.CULTURAL_SYNTHESIS

    def process_encounter(self, encounter: CulturalEncounter) -> dict[str, Any]:
        """Process a cultural encounter and determine its outcome."""
        result: dict[str, Any] = {
            "encounter_id": encounter.encounter_id,
            "collision_type": encounter.collision_type.name,
            "success": False,
            "exchanges": [],
            "new_beliefs": [],
            "conflicts": [],
        }

        if encounter.collision_type == CollisionType.PEACEFUL_TRADE:
            # Simple resource exchange, minimal cultural impact
            result["success"] = True
            result["cultural_impact"] = 0.1

        elif encounter.collision_type == CollisionType.CULTURAL_EXCHANGE:
            # Agents exchange cultural elements
            result["success"] = True
            result["cultural_impact"] = 0.5
            result["exchanges"] = self._simulate_cultural_exchange(
                encounter.culture_a, encounter.culture_b
            )

        elif encounter.collision_type == CollisionType.CULTURAL_CONFLICT:
            # Create a cultural conflict
            conflict = self._create_conflict(encounter)
            result["success"] = True
            result["cultural_impact"] = 0.8
            result["conflict_id"] = conflict.conflict_id

        elif encounter.collision_type == CollisionType.CULTURAL_DOMINANCE:
            # One culture dominates the other
            result["success"] = True
            result["cultural_impact"] = 0.7
            result["dominant_culture"] = self._rng.choice([encounter.culture_a, encounter.culture_b])

        elif encounter.collision_type == CollisionType.CULTURAL_RESISTANCE:
            # The weaker culture resists assimilation
            result["success"] = True
            result["cultural_impact"] = 0.3
            result["resistance_strength"] = self._rng.uniform(0.5, 1.0)
            self._stats["resistances"] += 1

        elif encounter.collision_type == CollisionType.CULTURAL_SYNTHESIS:
            # Create a new synthesized cultural element
            synthesis = self._create_synthesis(encounter)
            if synthesis:
                result["success"] = True
                result["cultural_impact"] = 0.9
                result["synthesis_id"] = synthesis.synthesis_id
                self._stats["syntheses"] += 1

        elif encounter.collision_type == CollisionType.CULTURAL_DIFFUSION:
            # Cultural elements spread between cultures
            result["success"] = True
            result["cultural_impact"] = 0.4
            result["diffusions"] = self._simulate_diffusion(
                encounter.culture_a, encounter.culture_b
            )

        elif encounter.collision_type == CollisionType.CULTURAL_ASSIMILATION:
            # One agent adopts the other's culture
            result["success"] = True
            result["cultural_impact"] = 0.6
            result["assimilated_agent"] = self._rng.choice([encounter.agent_a_id, encounter.agent_b_id])
            result["new_culture"] = self._rng.choice([encounter.culture_a, encounter.culture_b])
            self._stats["assimilations"] += 1

        encounter.resolved = True
        encounter.outcome = str(result)
        return result

    def _simulate_cultural_exchange(
        self, culture_a: str, culture_b: str
    ) -> list[dict[str, Any]]:
        """Simulate cultural exchange between two cultures."""
        c_a = self._cultures.get(culture_a, {})
        c_b = self._cultures.get(culture_b, {})

        exchanges = []

        # Exchange values
        values_a = c_a.get("values", [])
        values_b = c_b.get("values", [])
        if values_a and values_b:
            exchange = {
                "type": "values",
                "from_a": self._rng.choice(values_a) if values_a else None,
                "from_b": self._rng.choice(values_b) if values_b else None,
            }
            exchanges.append(exchange)

        # Exchange practices
        practices_a = c_a.get("practices", [])
        practices_b = c_b.get("practices", [])
        if practices_a and practices_b:
            exchange = {
                "type": "practices",
                "from_a": self._rng.choice(practices_a) if practices_a else None,
                "from_b": self._rng.choice(practices_b) if practices_b else None,
            }
            exchanges.append(exchange)

        return exchanges

    def _create_conflict(self, encounter: CulturalEncounter) -> CulturalConflict:
        """Create a cultural conflict from an encounter."""
        c_a = self._cultures.get(encounter.culture_a, {})
        c_b = self._cultures.get(encounter.culture_b, {})

        # Find conflicting beliefs
        set(c_a.get("taboos", []))
        set(c_b.get("taboos", []))

        # Find common taboos that conflict (same taboo, different meanings?)
        conflicting_beliefs: tuple[str, str] = ("taboo_conflict", "taboo_conflict")

        conflict = CulturalConflict(
            conflict_id=f"conflict_{self._next_conflict_id}",
            culture_a=encounter.culture_a,
            culture_b=encounter.culture_b,
            conflicting_beliefs=conflicting_beliefs,
            tick_started=encounter.tick,
            intensity=encounter.conflict_level,
        )

        self._conflicts.append(conflict)
        self._next_conflict_id += 1

        return conflict

    def _create_synthesis(self, encounter: CulturalEncounter) -> CulturalSynthesis | None:
        """Create a new cultural synthesis from an encounter."""
        c_a = self._cultures.get(encounter.culture_a, {})
        c_b = self._cultures.get(encounter.culture_b, {})

        # Get cultural elements to synthesize
        values_a = c_a.get("values", [])
        values_b = c_b.get("values", [])

        if not values_a and not values_b:
            return None

        # Select elements to combine
        source_values = []
        if values_a:
            source_values.append(self._rng.choice(values_a))
        if values_b:
            source_values.append(self._rng.choice(values_b))

        # Create new proposition by combining elements
        new_proposition = self._synthesize_proposition(source_values)

        synthesis = CulturalSynthesis(
            synthesis_id=f"synth_{self._next_synthesis_id}",
            source_cultures=[encounter.culture_a, encounter.culture_b],
            source_beliefs=source_values,
            new_proposition=new_proposition,
            tick_created=encounter.tick,
            description=f"Synthesis of {', '.join(source_values)}",
        )

        self._syntheses.append(synthesis)
        self._next_synthesis_id += 1

        return synthesis

    def _synthesize_proposition(self, elements: list[str]) -> str:
        """Create a synthesized proposition from cultural elements."""
        if len(elements) < 2:
            return elements[0] if elements else ""

        # Simple synthesis by combining element names
        connectors = [" and ", " with ", " of ", " through "]
        connector = self._rng.choice(connectors)

        return connector.join(elements)

    def _simulate_diffusion(
        self, source_culture: str, target_culture: str
    ) -> list[CulturalDiffusion]:
        """Simulate cultural diffusion between cultures."""
        c_source = self._cultures.get(source_culture, {})
        self._cultures.get(target_culture, {})

        diffusions = []

        # Diffuse values
        values_source = c_source.get("values", [])
        if values_source:
            element = self._rng.choice(values_source)
            diffusion = CulturalDiffusion(
                diffusion_id=f"diff_{self._next_diffusion_id}",
                source_culture=source_culture,
                target_culture=target_culture,
                element=element,
                tick_started=0,
                spread_rate=self._rng.uniform(0.1, 0.5),
            )
            diffusions.append(diffusion)
            self._diffusions.append(diffusion)
            self._next_diffusion_id += 1

        return diffusions

    def resolve_conflict(
        self, conflict_id: str, resolution_type: str, tick: int
    ) -> CulturalConflict | None:
        """Resolve a cultural conflict."""
        conflict = next(
            (c for c in self._conflicts if c.conflict_id == conflict_id),
            None
        )

        if conflict is None:
            return None

        conflict.resolved = True
        conflict.tick_resolved = tick
        conflict.resolution_type = resolution_type

        return conflict

    def get_culture_size(self, culture_id: str) -> int:
        """Get the number of agents in a culture."""
        return len(self._culture_agents.get(culture_id, set()))

    def get_culture_dominance(self, culture_id: str) -> float:
        """Get the dominance of a culture as a fraction of total agents."""
        total_agents = sum(len(agents) for agents in self._culture_agents.values())
        if total_agents == 0:
            return 0.0
        return len(self._culture_agents.get(culture_id, set())) / total_agents

    def update(self, tick: int) -> None:
        """Update the collision system each tick."""
        # Update diffusion spread rates
        for diffusion in self._diffusions:
            if diffusion.spread_rate > 0:
                # Spread rate decreases over time (saturation)
                diffusion.spread_rate *= 0.999
                # Penetration increases
                diffusion.penetration_level = min(
                    1.0, diffusion.penetration_level + diffusion.spread_rate * 0.1
                )

        # Update synthesis stability
        for synthesis in self._syntheses:
            if synthesis.adoption_count > 10:
                synthesis.stability = min(1.0, synthesis.stability + 0.01)
            elif synthesis.adoption_count < 2:
                synthesis.stability *= 0.99

        # Resolve old unresolved conflicts
        for conflict in self._conflicts:
            if not conflict.resolved and tick - conflict.tick_started > 100:
                # Auto-resolve with persistence
                self.resolve_conflict(conflict.conflict_id, "persistence", tick)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about cultural collision and emergence."""
        active_conflicts = [c for c in self._conflicts if not c.resolved]
        active_diffusions = [d for d in self._diffusions if d.spread_rate > 0.01]

        return {
            "total_encounters": self._stats["total_encounters"],
            "peaceful_encounters": self._stats["peaceful_encounters"],
            "conflict_encounters": self._stats["conflict_encounters"],
            "active_conflicts": len(active_conflicts),
            "total_syntheses": len(self._syntheses),
            "successful_syntheses": sum(1 for s in self._syntheses if s.stability > 0.5),
            "active_diffusions": len(active_diffusions),
            "assimilations": self._stats["assimilations"],
            "resistances": self._stats["resistances"],
            "cultures": {
                culture_id: self.get_culture_dominance(culture_id)
                for culture_id in self._culture_agents
            },
            "most_dominant_culture": max(
                self._culture_agents.keys(),
                key=lambda c: self.get_culture_size(c),
                default=None
            ),
        }
