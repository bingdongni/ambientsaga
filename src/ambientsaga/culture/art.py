"""
Art system — creative expression, aesthetics, and cultural production.

This module implements:
- Art: creative works with aesthetic value
- ArtForm: categories of artistic expression
- Artist: agents who produce art
- Artistic Movement: shared aesthetic style
- Aesthetic Value: cultural standards of beauty
- Patronage: economic support for art

Key design goals:
1. Art reflects cultural identity and values
2. Art influences social attitudes and beliefs
3. Artists can achieve fame and influence
4. Artistic movements create cultural shifts
5. Patronage systems support artistic production
6. Art creates economic value and trade
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING, Any
from dataclasses import dataclass, field
from enum import Enum, auto
import hashlib

from ambientsaga.config import CultureConfig
from ambientsaga.types import EntityID, Pos2D, new_entity_id

if TYPE_CHECKING:
    from ambientsaga.world.state import World


# ---------------------------------------------------------------------------
# Art Types
# ---------------------------------------------------------------------------


class ArtForm(Enum):
    """Categories of artistic expression."""

    NARRATIVE = auto()      # Stories, myths, epics
    VISUAL = auto()         # Painting, sculpture, architecture
    MUSICAL = auto()        # Song, dance, rhythm
    PERFORMATIVE = auto()   # Theater, ceremony, ritual
    CRAFTSMANSHIP = auto()  # Pottery, weaving, metalwork
    POETIC = auto()         # Poetry, verse, song lyrics
    ORAL = auto()           # Oral traditions, folklore


class AestheticStandard(Enum):
    """Standards of beauty and aesthetic value."""

    NATURALISTIC = auto()   # Imitation of nature
    ABSTRACT = auto()       # Non-representational
    SYMBOLIC = auto()       # Meaning through symbols
    HARMONIOUS = auto()     # Balance and proportion
    EXPRESSIVE = auto()     # Emotional intensity
    FUNCTIONAL = auto()     # Beauty through utility


# ---------------------------------------------------------------------------
# Artwork
# ---------------------------------------------------------------------------


@dataclass
class Artwork:
    """A creative work produced by an agent."""

    artwork_id: str
    title: str
    art_form: ArtForm
    creator_id: EntityID
    creation_tick: int
    description: str  # Textual description/summary
    aesthetic_score: float  # 0-1, artistic quality
    cultural_significance: float  # 0-1, cultural impact
    influenced_by: list[str] = field(default_factory=list)  # Other artwork IDs
    aesthetic_standards: list[AestheticStandard] = field(default_factory=list)
    patronage_id: str = ""  # Patron who funded it
    copies_sold: int = 0
    copies_owned: int = 0
    influence_spread: float = 0.0  # How widely it's known
    historical_value: float = 0.0  # Increases over time

    def appreciate(self, tick: int) -> None:
        """Artwork appreciates in value over time."""
        age = tick - self.creation_tick
        # Historical value grows logarithmically with age
        self.historical_value = min(1.0, self.historical_value + age * 0.0001)
        # Influence spread grows with copies
        self.influence_spread = min(1.0, self.copies_owned / 100.0)


@dataclass
class ArtisticMovement:
    """A shared aesthetic style among artists."""

    movement_id: str
    name: str
    founding_tick: int
    founder_id: EntityID
    aesthetic_standards: list[AestheticStandard]
    key_themes: list[str]
    associated_artworks: list[str] = field(default_factory=list)
    followers: set[EntityID] = field(default_factory=set)
    influence: float = 0.5  # 0-1
    peak_tick: int = 0  # When it was most influential
    decline_rate: float = 0.0  # How fast influence fades

    def is_in_decline(self, tick: int) -> bool:
        """Check if the movement is in decline."""
        return tick - self.peak_tick > 500 and self.decline_rate > 0.5


@dataclass
class Patron:
    """A patron who supports artists."""

    patron_id: str
    agent_id: EntityID
    patron_type: str  # "individual", "institution", "state"
    aesthetic_preferences: list[AestheticStandard] = field(default_factory=list)
    budget: float = 0.0
    spending_rate: float = 0.1  # Fraction of budget spent per year
    supported_artists: list[str] = field(default_factory=list)  # Artist agent IDs
    total_invested: float = 0.0


# ---------------------------------------------------------------------------
# ArtSystem
# ---------------------------------------------------------------------------


class ArtSystem:
    """
    Manages art, artistic expression, and cultural production.

    The ArtSystem:
    1. Tracks artwork creation and appreciation
    2. Manages artistic movements
    3. Handles patronage and economic support
    4. Processes cultural influence through art
    5. Generates aesthetic trends
    """

    def __init__(
        self,
        config: CultureConfig | None = None,
        seed: int = 42,
    ) -> None:
        self._config = config or CultureConfig()
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # All artworks
        self._artworks: dict[str, Artwork] = {}

        # All artistic movements
        self._movements: dict[str, ArtisticMovement] = {}

        # All patrons
        self._patrons: dict[str, Patron] = {}

        # Famous artworks (high influence)
        self._famous_artworks: list[str] = []

        # Aesthetic trends
        self._current_trends: list[AestheticStandard] = list(AestheticStandard)

    # -------------------------------------------------------------------------
    # Artwork Creation
    # -------------------------------------------------------------------------

    def create_artwork(
        self,
        creator_id: EntityID,
        title: str,
        art_form: ArtForm,
        description: str,
        tick: int,
        aesthetic_score: float = 0.5,
        patronage_id: str = "",
        influenced_by: list[str] | None = None,
    ) -> str:
        """Create a new artwork."""
        artwork_id = new_entity_id()

        # Calculate cultural significance based on influences
        cultural_sig = aesthetic_score
        if influenced_by:
            for ref_id in influenced_by:
                ref = self._artworks.get(ref_id)
                if ref:
                    cultural_sig = max(cultural_sig, ref.cultural_significance * 0.5)

        # Determine aesthetic standards from art form
        standards = self._get_standards_for_form(art_form)

        artwork = Artwork(
            artwork_id=artwork_id,
            title=title,
            art_form=art_form,
            creator_id=creator_id,
            creation_tick=tick,
            description=description,
            aesthetic_score=aesthetic_score,
            cultural_significance=cultural_sig,
            influenced_by=influenced_by or [],
            aesthetic_standards=standards,
            patronage_id=patronage_id,
        )

        self._artworks[artwork_id] = artwork

        # Track famous works
        if aesthetic_score > 0.7:
            self._famous_artworks.append(artwork_id)
            if len(self._famous_artworks) > 100:
                self._famous_artworks = self._famous_artworks[-100:]

        return artwork_id

    def _get_standards_for_form(self, art_form: ArtForm) -> list[AestheticStandard]:
        """Get default aesthetic standards for an art form."""
        mapping = {
            ArtForm.NARRATIVE: [AestheticStandard.SYMBOLIC, AestheticStandard.EXPRESSIVE],
            ArtForm.VISUAL: [AestheticStandard.NATURALISTIC, AestheticStandard.HARMONIOUS],
            ArtForm.MUSICAL: [AestheticStandard.EXPRESSIVE, AestheticStandard.HARMONIOUS],
            ArtForm.PERFORMATIVE: [AestheticStandard.EXPRESSIVE, AestheticStandard.SYMBOLIC],
            ArtForm.CRAFTSMANSHIP: [AestheticStandard.FUNCTIONAL, AestheticStandard.HARMONIOUS],
            ArtForm.POETIC: [AestheticStandard.SYMBOLIC, AestheticStandard.ABSTRACT],
            ArtForm.ORAL: [AestheticStandard.SYMBOLIC, AestheticStandard.EXPRESSIVE],
        }
        return mapping.get(art_form, [AestheticStandard.HARMONIOUS])

    def get_artwork_value(
        self,
        artwork_id: str,
        tick: int,
    ) -> float:
        """Calculate the current value of an artwork."""
        artwork = self._artworks.get(artwork_id)
        if artwork is None:
            return 0.0

        # Base value = aesthetic * cultural significance
        base_value = artwork.aesthetic_score * artwork.cultural_significance

        # Historical appreciation
        age = tick - artwork.creation_tick
        age_multiplier = 1.0 + age * 0.001

        # Scarcity (fewer copies = more valuable)
        scarcity = 1.0 / (1.0 + artwork.copies_sold * 0.1)

        # Influence bonus
        influence_bonus = artwork.influence_spread * 0.3

        return base_value * age_multiplier * scarcity + influence_bonus

    def copy_artwork(
        self,
        artwork_id: str,
        new_owner_id: EntityID,
    ) -> bool:
        """Create a copy of an artwork (e.g., reproduction, retelling)."""
        artwork = self._artworks.get(artwork_id)
        if artwork is None:
            return False

        artwork.copies_sold += 1
        artwork.copies_owned += 1
        artwork.influence_spread = min(1.0, artwork.influence_spread + 0.01)

        return True

    # -------------------------------------------------------------------------
    # Artistic Movements
    # -------------------------------------------------------------------------

    def create_movement(
        self,
        founder_id: EntityID,
        name: str,
        tick: int,
        themes: list[str],
        standards: list[AestheticStandard] | None = None,
    ) -> str:
        """Create a new artistic movement."""
        movement_id = new_entity_id()

        movement = ArtisticMovement(
            movement_id=movement_id,
            name=name,
            founding_tick=tick,
            founder_id=founder_id,
            aesthetic_standards=standards or [AestheticStandard.HARMONIOUS],
            key_themes=themes,
            followers={founder_id},
            influence=0.1,
            peak_tick=tick,
        )

        self._movements[movement_id] = movement
        return movement_id

    def join_movement(
        self,
        agent_id: EntityID,
        movement_id: str,
    ) -> bool:
        """An artist joins an artistic movement."""
        movement = self._movements.get(movement_id)
        if movement is None or movement.is_in_decline(self._rng.integers(0, 10000)):
            return False

        movement.followers.add(agent_id)
        movement.influence = min(1.0, movement.influence + 0.02)
        return True

    def get_movement_style(self, movement_id: str) -> list[AestheticStandard]:
        """Get the aesthetic style of a movement."""
        movement = self._movements.get(movement_id)
        if movement is None:
            return []
        return movement.aesthetic_standards

    # -------------------------------------------------------------------------
    # Patronage
    # -------------------------------------------------------------------------

    def register_patron(
        self,
        agent_id: EntityID,
        patron_type: str = "individual",
        budget: float = 1000.0,
    ) -> str:
        """Register a patron."""
        patron_id = new_entity_id()
        patron = Patron(
            patron_id=patron_id,
            agent_id=agent_id,
            patron_type=patron_type,
            budget=budget,
        )
        self._patrons[patron_id] = patron
        return patron_id

    def commission_artwork(
        self,
        patron_id: str,
        artist_id: EntityID,
        description: str,
        art_form: ArtForm,
        tick: int,
        payment: float,
    ) -> str | None:
        """Commission a new artwork."""
        patron = self._patrons.get(patron_id)
        if patron is None or patron.budget < payment:
            return None

        patron.budget -= payment
        patron.total_invested += payment

        artwork_id = self.create_artwork(
            creator_id=artist_id,
            title=f"Commissioned Work ({patron.patron_type})",
            art_form=art_form,
            description=description,
            tick=tick,
            aesthetic_score=0.5,
            patronage_id=patron_id,
        )

        patron.supported_artists.append(artist_id)
        return artwork_id

    # -------------------------------------------------------------------------
    # Cultural Influence
    # -------------------------------------------------------------------------

    def get_cultural_influence(
        self,
        agent_id: EntityID,
        tick: int,
    ) -> float:
        """Calculate an agent's cultural influence through art."""
        agent_artworks = [
            a for a in self._artworks.values()
            if a.creator_id == agent_id
        ]

        if not agent_artworks:
            return 0.0

        total_value = sum(
            self.get_artwork_value(a.artwork_id, tick)
            for a in agent_artworks
        )

        return min(1.0, total_value / 100.0)

    # -------------------------------------------------------------------------
    # Update
    # -------------------------------------------------------------------------

    def update(self, tick: int) -> None:
        """Update art system each tick."""
        # Artworks appreciate over time
        for artwork in self._artworks.values():
            artwork.appreciate(tick)

        # Movements rise and fall
        for movement in self._movements.values():
            if movement.influence > 0.7 and movement.peak_tick == movement.founding_tick:
                movement.peak_tick = tick

            # Natural influence decay
            if tick - movement.peak_tick > 200:
                movement.decline_rate += 0.0001
                movement.influence *= (1.0 - movement.decline_rate)

    def get_stats(self) -> dict[str, Any]:
        """Get art system statistics."""
        artworks_by_form = {}
        for artwork in self._artworks.values():
            f = artwork.art_form.name
            artworks_by_form[f] = artworks_by_form.get(f, 0) + 1

        return {
            "total_artworks": len(self._artworks),
            "total_movements": len(self._movements),
            "total_patrons": len(self._patrons),
            "famous_artworks": len(self._famous_artworks),
            "artworks_by_form": artworks_by_form,
            "total_copies": sum(a.copies_sold for a in self._artworks.values()),
        }
