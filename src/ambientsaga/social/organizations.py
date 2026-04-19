"""
Organization Manager — manages organizations, institutions, and social structures.

Organizations:
- Families, clans, tribes
- Guilds, corporations
- Religions, political parties
- Trade networks

Institutions:
- Property rights
- Legal systems
- Marriage customs
- Religious doctrines
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING
from dataclasses import dataclass

from ambientsaga.types import EntityID, Organization, OrganizationType, Pos2D

if TYPE_CHECKING:
    from ambientsaga.world.state import World


@dataclass
class Institution:
    """An institution — a set of rules governing social behavior."""

    institution_id: EntityID
    name: str
    description: str
    rules: tuple[str, ...]  # The rules that define this institution
    enforcement_level: float  # 0-1, how strongly enforced
    legitimacy: float  # 0-1, how accepted by the population
    established_tick: int = 0
    founder_id: EntityID | None = None

    def update(self, tick: int, legitimacy_change: float) -> None:
        """Update institution state."""
        self.legitimacy = max(0.0, min(1.0, self.legitimacy + legitimacy_change))


class OrganizationManager:
    """
    Manages organizations and institutions.

    Key responsibilities:
    - Create and track organizations
    - Manage organization membership
    - Track organizational hierarchy
    - Manage institutional rules and legitimacy
    """

    def __init__(self, world: "World", seed: int = 42) -> None:
        self.world = world
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Organization registry
        self._organizations: dict[EntityID, Organization] = {}

        # Membership: org_id -> set of member agent IDs
        self._membership: dict[EntityID, set[EntityID]] = {}

        # Hierarchy: org_id -> parent org_id
        self._hierarchy: dict[EntityID, EntityID] = {}

        # Institutions
        self._institutions: dict[EntityID, Institution] = {}

        # Initialize default institutions
        self._initialize_default_institutions()

    def _initialize_default_institutions(self) -> None:
        """Create default institutions for the world."""
        # Property rights (basic)
        self._institutions["property_rights"] = Institution(
            institution_id="property_rights",
            name="Property Rights",
            description="The right to own and control resources",
            rules=(
                "Agents may claim unowned resources",
                "Claims are respected by others",
                "Resources may be traded or inherited",
            ),
            enforcement_level=0.7,
            legitimacy=0.8,
        )

        # Basic social contract
        self._institutions["social_contract"] = Institution(
            institution_id="social_contract",
            name="Social Contract",
            description="Basic rules of social coexistence",
            rules=(
                "No unprovoked violence",
                "Promise-keeping is expected",
                "Mutual aid in times of need",
            ),
            enforcement_level=0.5,
            legitimacy=0.9,
        )

    def create_organization(
        self,
        org_type: OrganizationType,
        name: str,
        founder_id: EntityID,
        position: Pos2D | None = None,
    ) -> Organization:
        """Create a new organization."""
        from ambientsaga.types import new_entity_id

        org = Organization(
            org_id=new_entity_id(),
            name=name,
            org_type=org_type,
            founded_tick=self.world.tick,
            founder_id=founder_id,
            leader_id=founder_id,
            territory=None,
        )

        self._organizations[org.org_id] = org
        self._membership[org.org_id] = {founder_id}
        self.world._organizations[org.org_id] = org

        return org

    def join_organization(self, org_id: EntityID, agent_id: EntityID) -> bool:
        """Add an agent to an organization."""
        if org_id not in self._organizations:
            return False
        self._membership[org_id].add(agent_id)
        self._organizations[org_id].population = len(self._membership[org_id])
        return True

    def leave_organization(self, org_id: EntityID, agent_id: EntityID) -> bool:
        """Remove an agent from an organization."""
        if org_id not in self._membership:
            return False
        self._membership[org_id].discard(agent_id)
        self._organizations[org_id].population = len(self._membership[org_id])
        return True

    def get_organization(self, org_id: EntityID) -> Organization | None:
        """Get an organization by ID."""
        return self._organizations.get(org_id)

    def get_organizations_of_type(
        self, org_type: OrganizationType
    ) -> list[Organization]:
        """Get all organizations of a specific type."""
        return [
            org for org in self._organizations.values()
            if org.org_type == org_type
        ]

    def get_member_count(self, org_id: EntityID) -> int:
        """Get the number of members in an organization."""
        return len(self._membership.get(org_id, set()))

    def get_agent_organizations(self, agent_id: EntityID) -> list[Organization]:
        """Get all organizations an agent belongs to."""
        result: list[Organization] = []
        for org_id, members in self._membership.items():
            if agent_id in members:
                org = self._organizations.get(org_id)
                if org:
                    result.append(org)
        return result

    def update(self, tick: int) -> None:
        """Update organization state for the tick."""
        # Update organization treasuries
        for org in self._organizations.values():
            # Collect dues from members
            if org.population > 0:
                # Simple: each member pays 1 unit per year
                annual_dues = 1.0
                org.treasury += org.population * annual_dues / 360

        # Update institution legitimacy
        for institution in self._institutions.values():
            # Legitimacy slowly drifts toward 0.5
            drift = 0.001 * (0.5 - institution.legitimacy)
            institution.update(tick, drift)

    def create_institution(
        self,
        name: str,
        description: str,
        rules: tuple[str, ...],
        founder_id: EntityID,
    ) -> Institution:
        """Create a new institution."""
        from ambientsaga.types import new_entity_id

        institution = Institution(
            institution_id=new_entity_id(),
            name=name,
            description=description,
            rules=rules,
            enforcement_level=0.5,
            legitimacy=0.5,
            established_tick=self.world.tick,
            founder_id=founder_id,
        )
        self._institutions[institution.institution_id] = institution
        return institution

    def get_institution(self, institution_id: str) -> Institution | None:
        """Get an institution by ID."""
        return self._institutions.get(institution_id)

    def get_all_institutions(self) -> list[Institution]:
        """Get all institutions."""
        return list(self._institutions.values())

    def get_stats(self) -> dict:
        """Get organization statistics."""
        by_type: dict[str, int] = {}
        for org in self._organizations.values():
            name = org.org_type.name
            by_type[name] = by_type.get(name, 0) + 1

        return {
            "total_organizations": len(self._organizations),
            "by_type": by_type,
            "total_institutions": len(self._institutions),
            "total_memberships": sum(len(m) for m in self._membership.values()),
        }
