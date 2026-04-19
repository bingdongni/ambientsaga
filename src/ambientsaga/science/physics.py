"""
Physics Engine — Physical Laws and Dynamics

Provides a simplified but principled physics simulation:
- Newtonian mechanics: F=ma
- Energy conservation and transformation
- Momentum conservation
- Thermodynamics: heat transfer, entropy
- Fluid dynamics: pressure, flow
- Wave mechanics: propagation, interference

Physics is the foundation of all other sciences.
All physical quantities are tracked and conserved where appropriate.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


@dataclass
class Vector3D:
    """3D vector for physics calculations."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0  # Height/elevation

    def __add__(self, other: Vector3D) -> Vector3D:
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3D) -> Vector3D:
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vector3D:
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vector3D:
        return self.__mul__(scalar)

    @property
    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    @property
    def magnitude_sq(self) -> float:
        return self.x**2 + self.y**2 + self.z**2

    def dot(self, other: Vector3D) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3D) -> Vector3D:
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def normalize(self) -> Vector3D:
        mag = self.magnitude
        if mag < 1e-10:
            return Vector3D(0, 0, 0)
        return self * (1.0 / mag)

    def distance_to(self, other: Vector3D) -> float:
        return (self - other).magnitude

    def angle_to(self, other: Vector3D) -> float:
        """Angle between vectors in radians."""
        dot = self.normalize().dot(other.normalize())
        return math.acos(max(-1.0, min(1.0, dot)))


@dataclass
class Force:
    """A force acting on a body."""
    vector: Vector3D  # Force vector
    source: str = ""  # Source of the force (gravity, friction, etc.)
    tick: int = 0


@dataclass
class Energy:
    """Energy of a system."""
    kinetic: float = 0.0   # Movement energy (0.5 * m * v^2)
    potential: float = 0.0  # Potential energy (m * g * h)
    thermal: float = 0.0   # Heat energy
    chemical: float = 0.0   # Chemical potential energy
    electrical: float = 0.0  # Electrical energy
    radiant: float = 0.0   # Light/radiation energy

    @property
    def total(self) -> float:
        return self.kinetic + self.potential + self.thermal + self.chemical + self.electrical + self.radiant

    def add(self, other: Energy) -> Energy:
        """Add energies."""
        return Energy(
            kinetic=self.kinetic + other.kinetic,
            potential=self.potential + other.potential,
            thermal=self.thermal + other.thermal,
            chemical=self.chemical + other.chemical,
            electrical=self.electrical + other.electrical,
            radiant=self.radiant + other.radiant,
        )

    def transform(self, from_type: str, to_type: str, efficiency: float = 0.9) -> Energy:
        """Transform energy from one form to another."""
        types = ['kinetic', 'potential', 'thermal', 'chemical', 'electrical', 'radiant']
        if from_type not in types or to_type not in types:
            return Energy()

        from_val = getattr(self, from_type)
        converted = from_val * efficiency
        remaining = from_val - converted

        result = Energy()
        setattr(result, from_type, remaining)
        setattr(result, to_type, converted)
        return result


@dataclass
class Momentum:
    """Momentum of a body."""
    linear: Vector3D = field(default_factory=Vector3D)
    angular: Vector3D = field(default_factory=Vector3D)

    @property
    def linear_magnitude(self) -> float:
        return self.linear.magnitude

    @property
    def angular_magnitude(self) -> float:
        return self.angular.magnitude


@dataclass
class PhysicalBody:
    """A physical body with mass, position, velocity, etc."""
    body_id: str
    mass: float  # kg
    position: Vector3D
    velocity: Vector3D = field(default_factory=Vector3D)
    acceleration: Vector3D = field(default_factory=Vector3D)

    # Physical properties
    volume: float = 1.0  # m^3
    density: float = 1000.0  # kg/m^3
    drag_coefficient: float = 0.5
    friction_coefficient: float = 0.3

    # State
    energy: Energy = field(default_factory=Energy)
    momentum: Momentum = field(default_factory=Momentum)
    temperature: float = 293.15  # Kelvin (20°C)
    pressure: float = 101325.0  # Pascals (1 atm)

    # External forces
    forces: list[Force] = field(default_factory=list)

    # Cached
    _radius: float = 1.0

    @property
    def radius(self) -> float:
        """Equivalent radius based on volume."""
        return self._radius or ((3 * self.volume / (4 * math.pi)) ** (1/3))

    @radius.setter
    def radius(self, value: float):
        self._radius = value
        self.volume = (4/3) * math.pi * value**3

    def apply_force(self, force: Force) -> None:
        """Apply a force to the body."""
        self.forces.append(force)

    def apply_impulse(self, impulse: Vector3D) -> None:
        """Apply an impulse (instantaneous change in momentum)."""
        self.momentum.linear = self.momentum.linear + impulse

    def get_net_force(self) -> Vector3D:
        """Calculate net force on body."""
        net = Vector3D(0, 0, 0)
        for f in self.forces:
            net = net + f.vector
        return net

    def update(self, dt: float, gravity: Vector3D = None) -> None:
        """Update physics state."""
        # Apply gravity
        if gravity:
            gravity_force = gravity * self.mass
            self.apply_force(Force(gravity_force, "gravity"))

        # Calculate acceleration from forces (F = ma)
        net = self.get_net_force()
        if self.mass > 0:
            self.acceleration = net * (1.0 / self.mass)

        # Update velocity and position
        self.velocity = self.velocity + self.acceleration * dt

        # Apply drag
        speed = self.velocity.magnitude
        if speed > 0:
            drag = self.velocity.normalize() * (-0.5 * self.drag_coefficient * speed**2)
            self.velocity = self.velocity + drag * dt

        # Update position
        self.position = self.position + self.velocity * dt

        # Calculate kinetic energy (0.5 * m * v^2)
        self.energy.kinetic = 0.5 * self.mass * (self.velocity.magnitude**2)

        # Calculate momentum
        self.momentum.linear = self.velocity * self.mass

        # Clear forces for next frame
        self.forces.clear()


class PhysicsEngine:
    """
    Physics simulation engine.

    Tracks physical laws and dynamics:
    - Newtonian mechanics
    - Energy conservation
    - Momentum conservation
    - Thermodynamics
    - Fluid dynamics

    Couplings:
    - Physics -> Chemistry: Temperature affects reaction rates
    - Physics -> Biology: Physical environment affects organism fitness
    - Physics -> Ecology: Energy flow through food chains
    - Physics -> Social: Physical resources affect social structure
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

        # World physics parameters
        self.gravity = Vector3D(0, 0, -9.81)  # m/s^2
        self.gas_constant = 8.314  # J/(mol·K)
        self.boltzmann_constant = 1.381e-23  # J/K
        self.speed_of_light = 299792458  # m/s

        # Environment
        self.ambient_temperature = 293.15  # Kelvin (20°C)
        self.ambient_pressure = 101325.0  # Pascals
        self.air_density = 1.225  # kg/m^3
        self.water_density = 1000.0  # kg/m^3

        # Bodies in simulation
        self.bodies: dict[str, PhysicalBody] = {}

        # Energy budgets
        self.total_energy: Energy = Energy()
        self.energy_flows: list[tuple[str, str, float]] = []  # source, sink, rate

        # Statistics
        self.tick = 0
        self.total_collisions = 0

    def create_body(
        self,
        body_id: str,
        mass: float,
        position: Vector3D,
        velocity: Vector3D = None,
        radius: float = 1.0,
    ) -> PhysicalBody:
        """Create a physical body."""
        body = PhysicalBody(
            body_id=body_id,
            mass=mass,
            position=position,
            velocity=velocity or Vector3D(),
            _radius=radius,
        )
        body.volume = (4/3) * math.pi * radius**3
        body.density = mass / body.volume
        self.bodies[body_id] = body
        return body

    def remove_body(self, body_id: str) -> None:
        """Remove a body from simulation."""
        if body_id in self.bodies:
            del self.bodies[body_id]

    def update(self, tick: int, dt: float = 1.0) -> None:
        """Update physics simulation."""
        self.tick = tick

        # Update all bodies
        for body in self.bodies.values():
            body.update(dt, self.gravity)

        # Detect and resolve collisions
        self._resolve_collisions()

        # Update energy flows
        self._update_energy_flows()

        # Update total energy
        self._calculate_total_energy()

    def _resolve_collisions(self) -> None:
        """Detect and resolve collisions between bodies."""
        body_list = list(self.bodies.values())
        for i, body1 in enumerate(body_list):
            for body2 in body_list[i + 1:]:
                dist = body1.position.distance_to(body2.position)
                min_dist = body1.radius + body2.radius
                if dist < min_dist:
                    # Collision detected
                    self.total_collisions += 1

                    # Simple elastic collision response
                    normal = (body2.position - body1.position).normalize()
                    rel_vel = body1.velocity - body2.velocity
                    vel_along_normal = rel_vel.dot(normal)

                    # Only resolve if bodies are approaching
                    if vel_along_normal > 0:
                        # Coefficient of restitution
                        e = 0.8  # Bouncy

                        # Calculate impulse
                        j = -(1 + e) * vel_along_normal
                        j /= (1 / body1.mass + 1 / body2.mass)

                        impulse = normal * j

                        # Apply impulse
                        body1.velocity = body1.velocity + impulse * (1 / body1.mass)
                        body2.velocity = body2.velocity - impulse * (1 / body2.mass)

                        # Separate bodies
                        overlap = min_dist - dist
                        separation = normal * (overlap / 2)
                        body1.position = body1.position - separation
                        body2.position = body2.position + separation

    def _update_energy_flows(self) -> None:
        """Update energy flows between bodies."""
        self.energy_flows.clear()

        # Heat transfer based on temperature difference
        for body in self.bodies.values():
            if body.temperature > self.ambient_temperature:
                # Body loses heat to environment
                dt_temp = body.temperature - self.ambient_temperature
                heat_loss = dt_temp * 0.01  # Simplified heat transfer
                body.energy.thermal -= heat_loss
                body.temperature -= heat_loss / (body.mass * 1000)  # Heat capacity approximation
                self.energy_flows.append((body.body_id, "environment", heat_loss))

    def _calculate_total_energy(self) -> None:
        """Calculate total energy in system."""
        self.total_energy = Energy()
        for body in self.bodies.values():
            self.total_energy = self.total_energy.add(body.energy)

    def apply_force_field(
        self,
        field_type: str,
        position: Vector3D,
        magnitude: float,
        radius: float = 10.0,
    ) -> None:
        """Apply a force field (gravity well, electromagnetic, etc.)."""
        for body in self.bodies.values():
            dist = body.position.distance_to(position)
            if dist < radius and dist > 0.1:
                direction = (position - body.position).normalize()
                strength = magnitude * (1 - dist / radius)  # Falloff

                if field_type == "gravity":
                    body.apply_force(Force(direction * strength, "gravity_field"))
                elif field_type == "repulsive":
                    body.apply_force(Force(direction * -strength, "repulsion_field"))
                elif field_type == "tangential":
                    # Cyclic field (like magnetic)
                    tangent = Vector3D(-direction.y, direction.x, 0)
                    body.apply_force(Force(tangent * strength, "tangential_field"))

    def ray_cast(
        self,
        origin: Vector3D,
        direction: Vector3D,
        max_distance: float = 100.0,
    ) -> list[tuple[PhysicalBody, float, Vector3D]]:
        """Ray cast to find intersections with bodies."""
        hits = []
        direction = direction.normalize()

        for body in self.bodies.values():
            # Ray-sphere intersection
            oc = origin - body.position
            a = direction.magnitude_sq
            b = 2 * oc.dot(direction)
            c = oc.magnitude_sq - body.radius**2
            discriminant = b**2 - 4 * a * c

            if discriminant > 0:
                t = (-b - math.sqrt(discriminant)) / (2 * a)
                if 0 < t < max_distance:
                    point = origin + direction * t
                    normal = (point - body.position).normalize()
                    hits.append((body, t, normal))

        # Sort by distance
        hits.sort(key=lambda x: x[1])
        return hits

    def get_statistics(self) -> dict:
        """Get physics statistics."""
        return {
            "bodies": len(self.bodies),
            "total_energy": self.total_energy.total,
            "kinetic_energy": self.total_energy.kinetic,
            "thermal_energy": self.total_energy.thermal,
            "collisions": self.total_collisions,
            "avg_temperature": sum(b.temperature for b in self.bodies.values()) / max(1, len(self.bodies)),
        }


# =============================================================================
# Coupling Constants
# =============================================================================

# Physics-Chemistry coupling
PHYSICS_CHEMISTRY_TEMP_FACTOR = 0.01  # Temperature effect on reaction rates

# Physics-Biology coupling
GRAVITY_BIOLOGY_COST = 0.001  # Energy cost per kg per m/s^2
MOVEMENT_EFFICIENCY = 0.25  # Muscle efficiency

# Physics-Ecology coupling
ENERGY_TRANSFER_EFFICIENCY = 0.1  # Trophic transfer efficiency
RESPIRATION_COST = 0.05  # Energy lost as heat

# Physics-Social coupling
RESOURCE_ACCESSIBILITY = 0.5  # How accessible are resources given physics constraints
TRANSPORT_COST = 1.0  # Energy cost per distance per mass
