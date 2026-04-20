"""
Agent Appearance and Race System — Physical traits and racial characteristics.

This module defines the physical appearance system for agents:
- Racial traits (inheritable characteristics)
- Appearance features (observable traits)
- Physical attributes that affect social interactions
- Trait inheritance during reproduction

Key features:
- Heritable physical traits with variation
- Appearance descriptions for narrative
- Physical trait effects on gameplay (optional)
- Racial diversity tracking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import numpy as np


class SkinTone(Enum):
    """Skin tone categories."""

    PALE = auto()         # Very light
    FAIR = auto()         # Light
    MEDIUM_LIGHT = auto() # Light-medium
    MEDIUM = auto()       # Medium
    MEDIUM_DARK = auto()  # Medium-dark
    DARK = auto()         # Dark
    DARK_BROWN = auto()   # Very dark
    BLACK = auto()        # Deep black

    @property
    def tone_value(self) -> float:
        """Numeric value for tone (0-1)."""
        values = {
            SkinTone.PALE: 0.1,
            SkinTone.FAIR: 0.25,
            SkinTone.MEDIUM_LIGHT: 0.4,
            SkinTone.MEDIUM: 0.5,
            SkinTone.MEDIUM_DARK: 0.65,
            SkinTone.DARK: 0.8,
            SkinTone.DARK_BROWN: 0.9,
            SkinTone.BLACK: 1.0,
        }
        return values[self]


class HairColor(Enum):
    """Hair color categories."""

    BLACK = auto()
    DARK_BROWN = auto()
    BROWN = auto()
    LIGHT_BROWN = auto()
    AUBURN = auto()
    RED = auto()
    BLONDE = auto()
    LIGHT_BLONDE = auto()
    WHITE = auto()
    GREY = auto()


class EyeColor(Enum):
    """Eye color categories."""

    BLACK = auto()
    DARK_BROWN = auto()
    BROWN = auto()
    HAZEL = auto()
    GREEN = auto()
    BLUE = auto()
    GREY = auto()
    AMBER = auto()


class BuildType(Enum):
    """Body build types."""

    SLENDER = auto()
    ATHLETIC = auto()
    AVERAGE = auto()
    STOCKY = auto()
    HEAVY = auto()

    @property
    def strength_modifier(self) -> float:
        """Modifier to strength-based actions."""
        modifiers = {
            BuildType.SLENDER: 0.9,
            BuildType.ATHLETIC: 1.2,
            BuildType.AVERAGE: 1.0,
            BuildType.STOCKY: 1.1,
            BuildType.HEAVY: 0.9,
        }
        return modifiers[self]


class HeightType(Enum):
    """Height categories."""

    VERY_SHORT = auto()
    SHORT = auto()
    AVERAGE = auto()
    TALL = auto()
    VERY_TALL = auto()

    @property
    def height_modifier(self) -> float:
        """Modifier to height-based actions."""
        modifiers = {
            HeightType.VERY_SHORT: 0.8,
            HeightType.SHORT: 0.9,
            HeightType.AVERAGE: 1.0,
            HeightType.TALL: 1.1,
            HeightType.VERY_TALL: 1.2,
        }
        return modifiers[self]


@dataclass
class PhysicalTraits:
    """
    Physical appearance traits for an agent.

    These traits are:
    - Largely inherited from parents
    - Visible to other agents
    - Used for narrative descriptions
    - Potentially affect social interactions
    """

    # Basic appearance
    skin_tone: SkinTone = SkinTone.MEDIUM
    hair_color: HairColor = HairColor.BROWN
    eye_color: EyeColor = EyeColor.BROWN
    build: BuildType = BuildType.AVERAGE
    height: HeightType = HeightType.AVERAGE

    # Detailed features
    hair_style: str = "natural"  # "straight", "curly", "braided", etc.
    facial_features: tuple[str, ...] = field(default_factory=tuple)  # "brows", "nose", etc.
    distinctive_marks: tuple[str, ...] = field(default_factory=tuple)  # "scar", "tattoo", "birthmark"

    # Age-related appearance
    hair_grey_probability: float = 0.0  # 0-1, probability of grey hair based on age
    wrinkles: float = 0.0               # 0-1, age-related skin texture
    apparent_age: int = 25              # How old they appear (may differ from actual age)

    # Health indicators
    posture: float = 0.8  # 0-1, how upright/posture
    fitness: float = 0.5  # 0-1, physical fitness level
    vitality: float = 0.8  # 0-1, overall health appearance

    def get_description(self, include_details: bool = True) -> str:
        """Generate a human-readable appearance description."""
        parts = []

        # Basic build and height
        parts.append(f"{self.build.name.lower()} build")
        parts.append(f"{self.height.name.lower()} stature")

        # Colors
        parts.append(f"{self.skin_tone.name.lower()} skin")
        parts.append(f"{self.hair_color.name.lower().replace('_', ' ')} hair")
        parts.append(f"{self.eye_color.name.lower()} eyes")

        # Age appearance
        if self.apparent_age < 20:
            parts.append("youthful")
        elif self.apparent_age > 40:
            parts.append("weathered")
            if self.hair_grey_probability > 0.3:
                parts.append("grey-haired")

        # Distinctive features
        if self.distinctive_marks:
            parts.append(f"with {', '.join(self.distinctive_marks)}")

        # Fitness
        if self.fitness > 0.8:
            parts.append("athletic-looking")
        elif self.fitness < 0.3:
            parts.append("frail")

        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "skin_tone": self.skin_tone.name,
            "hair_color": self.hair_color.name,
            "eye_color": self.eye_color.name,
            "build": self.build.name,
            "height": self.height.name,
            "hair_style": self.hair_style,
            "facial_features": list(self.facial_features),
            "distinctive_marks": list(self.distinctive_marks),
            "apparent_age": self.apparent_age,
            "fitness": self.fitness,
            "vitality": self.vitality,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PhysicalTraits:
        """Deserialize from dictionary."""
        return cls(
            skin_tone=SkinTone[data.get("skin_tone", "MEDIUM")],
            hair_color=HairColor[data.get("hair_color", "BROWN")],
            eye_color=EyeColor[data.get("eye_color", "BROWN")],
            build=BuildType[data.get("build", "AVERAGE")],
            height=HeightType[data.get("height", "AVERAGE")],
            hair_style=data.get("hair_style", "natural"),
            facial_features=tuple(data.get("facial_features", [])),
            distinctive_marks=tuple(data.get("distinctive_marks", [])),
            apparent_age=data.get("apparent_age", 25),
            fitness=data.get("fitness", 0.5),
            vitality=data.get("vitality", 0.8),
        )


class PhysicalTraitGenerator:
    """
    Generates physical traits for agents.

    Supports:
    - Random generation based on ethnic background
    - Inheritance from parents
    - Mutation/variation
    - Regional variation
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Regional/racial trait distributions
        self._trait_distributions = self._initialize_distributions()

    def _initialize_distributions(self) -> dict[str, dict[str, Any]]:
        """Initialize trait probability distributions by region/ethnicity."""
        return {
            "default": {
                "skin_tones": [SkinTone.FAIR, SkinTone.MEDIUM_LIGHT, SkinTone.MEDIUM],
                "hair_colors": [HairColor.BROWN, HairColor.DARK_BROWN, HairColor.BLONDE],
                "eye_colors": [EyeColor.BROWN, EyeColor.HAZEL, EyeColor.GREEN],
                "builds": [BuildType.AVERAGE, BuildType.ATHLETIC],
                "heights": [HeightType.AVERAGE, HeightType.TALL],
            },
            "northern": {
                "skin_tones": [SkinTone.PALE, SkinTone.FAIR],
                "hair_colors": [HairColor.BLONDE, HairColor.LIGHT_BLONDE, HairColor.RED, HairColor.DARK_BROWN],
                "eye_colors": [EyeColor.BLUE, EyeColor.GREY, EyeColor.GREEN],
                "builds": [BuildType.ATHLETIC, BuildType.STOCKY, BuildType.AVERAGE],
                "heights": [HeightType.TALL, HeightType.VERY_TALL, HeightType.AVERAGE],
            },
            "southern": {
                "skin_tones": [SkinTone.MEDIUM_DARK, SkinTone.DARK, SkinTone.DARK_BROWN],
                "hair_colors": [HairColor.BLACK, HairColor.DARK_BROWN],
                "eye_colors": [EyeColor.BROWN, EyeColor.DARK_BROWN, EyeColor.BLACK],
                "builds": [BuildType.SLENDER, BuildType.AVERAGE],
                "heights": [HeightType.AVERAGE, HeightType.SHORT, HeightType.TALL],
            },
            "desert": {
                "skin_tones": [SkinTone.MEDIUM_DARK, SkinTone.DARK, SkinTone.DARK_BROWN, SkinTone.MEDIUM],
                "hair_colors": [HairColor.BLACK, HairColor.DARK_BROWN],
                "eye_colors": [EyeColor.BROWN, EyeColor.DARK_BROWN, EyeColor.HAZEL],
                "builds": [BuildType.SLENDER, BuildType.ATHLETIC],
                "heights": [HeightType.AVERAGE, HeightType.SHORT],
            },
            "tropical": {
                "skin_tones": [SkinTone.DARK, SkinTone.DARK_BROWN, SkinTone.MEDIUM_DARK],
                "hair_colors": [HairColor.BLACK, HairColor.DARK_BROWN],
                "eye_colors": [EyeColor.BROWN, EyeColor.DARK_BROWN, EyeColor.BLACK],
                "builds": [BuildType.ATHLETIC, BuildType.SLENDER, BuildType.AVERAGE],
                "heights": [HeightType.AVERAGE, HeightType.TALL, HeightType.SHORT],
            },
            "coastal": {
                "skin_tones": [SkinTone.MEDIUM_LIGHT, SkinTone.MEDIUM, SkinTone.MEDIUM_DARK],
                "hair_colors": [HairColor.BROWN, HairColor.LIGHT_BROWN, HairColor.BLONDE, HairColor.RED],
                "eye_colors": [EyeColor.BROWN, EyeColor.GREEN, EyeColor.BLUE, EyeColor.HAZEL],
                "builds": [BuildType.ATHLETIC, BuildType.AVERAGE],
                "heights": [HeightType.AVERAGE, HeightType.TALL],
            },
        }

    def generate(
        self,
        ethnicity: str = "default",
        region: str | None = None,
    ) -> PhysicalTraits:
        """Generate random physical traits based on ethnic/regional background."""
        # Determine distribution to use
        dist_key = region if region and region in self._trait_distributions else ethnicity
        if dist_key not in self._trait_distributions:
            dist_key = "default"

        dist = self._trait_distributions[dist_key]

        # Generate traits based on distribution
        skin_tone = self._rng.choice(dist["skin_tones"])
        hair_color = self._rng.choice(dist["hair_colors"])
        eye_color = self._rng.choice(dist["eye_colors"])
        build = self._rng.choice(dist["builds"])
        height = self._rng.choice(dist["heights"])

        return PhysicalTraits(
            skin_tone=skin_tone,
            hair_color=hair_color,
            eye_color=eye_color,
            build=build,
            height=height,
        )

    def inherit(
        self,
        parent1_traits: PhysicalTraits,
        parent2_traits: PhysicalTraits | None = None,
        mutation_rate: float = 0.1,
    ) -> PhysicalTraits:
        """
        Create traits by inheriting from parents.

        Traits are blended with possible mutations.
        """
        if parent2_traits is None:
            parent2_traits = parent1_traits

        # Helper to pick from parents (with mutation)
        def pick(parent1: Any, parent2: Any, options: list[Any] | None = None) -> Any:
            if self._rng.random() < mutation_rate and options:
                return self._rng.choice(options)
            return parent1 if self._rng.random() < 0.5 else parent2

        # Helper for numeric traits
        def blend(p1_val: float, p2_val: float, mutate: float = 0.1) -> float:
            base = (p1_val + p2_val) / 2
            if self._rng.random() < mutation_rate:
                base *= self._rng.uniform(1 - mutate, 1 + mutate)
            return base

        # Blend each trait
        new_traits = PhysicalTraits(
            skin_tone=pick(parent1_traits.skin_tone, parent2_traits.skin_tone),
            hair_color=pick(parent1_traits.hair_color, parent2_traits.hair_color),
            eye_color=pick(parent1_traits.eye_color, parent2_traits.eye_color),
            build=pick(parent1_traits.build, parent2_traits.build),
            height=pick(parent1_traits.height, parent2_traits.height),
            hair_style=parent1_traits.hair_style,  # Inherit style
            facial_features=parent1_traits.facial_features,
            distinctive_marks=parent1_traits.distinctive_marks,
            apparent_age=18,  # Newborn starts young
            fitness=0.5,
            vitality=1.0,  # Newborns start with full vitality
        )

        # Blend continuous traits
        new_traits.fitness = blend(parent1_traits.fitness, parent2_traits.fitness)

        return new_traits

    def add_distinctive_mark(
        self,
        traits: PhysicalTraits,
        mark_type: str,
        description: str,
    ) -> PhysicalTraits:
        """Add a distinctive mark to existing traits."""
        marks = list(traits.distinctive_marks) + [f"{mark_type}:{description}"]
        return PhysicalTraits(
            skin_tone=traits.skin_tone,
            hair_color=traits.hair_color,
            eye_color=traits.eye_color,
            build=traits.build,
            height=traits.height,
            hair_style=traits.hair_style,
            facial_features=traits.facial_features,
            distinctive_marks=tuple(marks),
            apparent_age=traits.apparent_age,
            fitness=traits.fitness,
            vitality=traits.vitality,
        )

    def age_traits(self, traits: PhysicalTraits, years: int) -> PhysicalTraits:
        """Age physical traits over time."""
        # Update apparent age
        new_apparent_age = traits.apparent_age + years

        # Grey hair probability increases with age
        if new_apparent_age > 30:
            grey_prob = min(1.0, (new_apparent_age - 30) / 50)
        else:
            grey_prob = 0.0

        # Wrinkles increase with age
        new_wrinkles = min(1.0, max(0.0, (new_apparent_age - 40) / 40))

        # Vitality decreases with age
        new_vitality = max(0.3, traits.vitality - years * 0.005)

        # Posture may decrease with age
        new_posture = max(0.5, traits.posture - years * 0.003)

        return PhysicalTraits(
            skin_tone=traits.skin_tone,
            hair_color=traits.hair_color,
            eye_color=traits.eye_color,
            build=traits.build,
            height=traits.height,
            hair_style=traits.hair_style,
            facial_features=traits.facial_features,
            distinctive_marks=traits.distinctive_marks,
            hair_grey_probability=grey_prob,
            wrinkles=new_wrinkles,
            apparent_age=new_apparent_age,
            posture=new_posture,
            fitness=traits.fitness,
            vitality=new_vitality,
        )


class RacialDiversityTracker:
    """
    Tracks racial diversity across the population.

    Provides metrics on:
    - Diversity indices
    - Trait distributions
    - Integration levels
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.Generator(np.random.PCG64(seed))
        self._trait_records: list[dict[str, Any]] = []

    def record_population(
        self,
        agents: list[dict[str, Any]],
        tick: int,
    ) -> None:
        """Record population traits for diversity analysis."""
        record = {
            "tick": tick,
            "count": len(agents),
            "skin_tone_dist": self._calculate_distribution(agents, "skin_tone"),
            "eye_color_dist": self._calculate_distribution(agents, "eye_color"),
            "build_dist": self._calculate_distribution(agents, "build"),
            "height_dist": self._calculate_distribution(agents, "height"),
        }
        self._trait_records.append(record)

        # Keep only recent records
        if len(self._trait_records) > 100:
            self._trait_records = self._trait_records[-100:]

    def _calculate_distribution(
        self,
        agents: list[dict[str, Any]],
        trait_key: str,
    ) -> dict[str, float]:
        """Calculate trait distribution in population."""
        if not agents:
            return {}

        counts: dict[str, int] = {}
        for agent in agents:
            trait = agent.get(trait_key, "UNKNOWN")
            counts[trait] = counts.get(trait, 0) + 1

        total = sum(counts.values())
        return {k: v / total for k, v in counts.items()}

    def calculate_diversity_index(self, agents: list[dict[str, Any]]) -> float:
        """
        Calculate Simpson's Diversity Index (0-1).

        0 = no diversity (all same)
        1 = maximum diversity (uniform distribution)
        """
        if not agents:
            return 0.0

        # Calculate based on skin tone as proxy
        counts: dict[str, int] = {}
        for agent in agents:
            skin = agent.get("skin_tone", "UNKNOWN")
            counts[skin] = counts.get(skin, 0) + 1

        total = sum(counts.values())
        if total <= 1:
            return 0.0

        # Simpson's Diversity Index
        sum_squares = sum((count / total) ** 2 for count in counts.values())
        return 1.0 - sum_squares

    def get_statistics(self) -> dict[str, Any]:
        """Get diversity statistics."""
        if not self._trait_records:
            return {"status": "no_data"}

        latest = self._trait_records[-1]
        return {
            "current_population": latest["count"],
            "skin_tone_distribution": latest["skin_tone_dist"],
            "eye_color_distribution": latest["eye_color_dist"],
            "build_distribution": latest["build_dist"],
            "height_distribution": latest["height_dist"],
            "recorded_ticks": len(self._trait_records),
        }
