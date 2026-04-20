"""Social systems package — organizations, relationships, stratification, settlements, ethnicity, race."""

from ambientsaga.social.ethnicity import (
    CulturalTrait,
    CulturalTraitType,
    EthnicConflict,
    EthnicGroup,
    EthnicGroupManager,
    EthnicRelation,
)
from ambientsaga.social.organizations import OrganizationManager
from ambientsaga.social.race import (
    BuildType,
    EyeColor,
    HairColor,
    HeightType,
    PhysicalTraitGenerator,
    PhysicalTraits,
    RacialDiversityTracker,
    SkinTone,
)
from ambientsaga.social.settlement import (
    Building,
    BuildingType,
    Settlement,
    SettlementManager,
    SettlementType,
)
from ambientsaga.social.stratification import (
    ClassPosition,
    HierarchyNode,
    SocialClass,
    SocialStratificationSystem,
    StratificationPattern,
)

__all__ = [
    # Organizations
    "OrganizationManager",
    # Settlements
    "Settlement",
    "SettlementManager",
    "SettlementType",
    "Building",
    "BuildingType",
    # Ethnicity
    "EthnicGroup",
    "EthnicGroupManager",
    "EthnicConflict",
    "CulturalTrait",
    "CulturalTraitType",
    "EthnicRelation",
    # Race/Appearance
    "PhysicalTraits",
    "PhysicalTraitGenerator",
    "RacialDiversityTracker",
    "SkinTone",
    "HairColor",
    "EyeColor",
    "BuildType",
    "HeightType",
    # Stratification
    "SocialStratificationSystem",
    "SocialClass",
    "ClassPosition",
    "HierarchyNode",
    "StratificationPattern",
]
