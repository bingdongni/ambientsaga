"""Social systems package — organizations, relationships, stratification."""

from ambientsaga.social.organizations import OrganizationManager
from ambientsaga.social.stratification import (
    ClassPosition,
    HierarchyNode,
    SocialClass,
    SocialStratificationSystem,
    StratificationPattern,
)

__all__ = [
    "OrganizationManager",
    "SocialStratificationSystem",
    "SocialClass",
    "ClassPosition",
    "HierarchyNode",
    "StratificationPattern",
]
