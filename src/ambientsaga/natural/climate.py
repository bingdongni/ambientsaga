"""
Climate and atmospheric simulation system.

Models:
- Temperature (latitude, altitude, season, ocean current effects)
- Precipitation (orographic, convective, frontal)
- Wind systems (trade winds, monsoons, local)
- Seasonal cycles
- Climate change and El Nino effects
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ambientsaga.config import ClimateConfig
from ambientsaga.types import ClimateZone, Season

if TYPE_CHECKING:
    pass


class ClimateSystem:
    """
    Atmospheric climate simulation.

    Computes temperature, precipitation, and wind for each tile
    based on geography, season, and climate dynamics.
    """

    def __init__(self, config: ClimateConfig, world_width: int, world_height: int, seed: int = 42) -> None:
        self.config = config
        self.width = world_width
        self.height = world_height
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Climate state arrays
        self._temperature: np.ndarray | None = None
        self._humidity: np.ndarray | None = None
        self._precipitation: np.ndarray | None = None
        self._wind_x: np.ndarray | None = None
        self._wind_y: np.ndarray | None = None
        self._cloud_cover: np.ndarray | None = None

        # Season tracking
        self._season_length = config.season_length_ticks
        self._el_nino_active = False
        self._el_nino_duration = 0

        # Baseline climate (computed once)
        self._baseline_temperature: np.ndarray | None = None
        self._baseline_precipitation: np.ndarray | None = None

    def initialize(
        self,
        elevation: np.ndarray,
        latitude: np.ndarray,
    ) -> None:
        """
        Initialize climate fields from terrain data.

        Args:
            elevation: [H, W] elevation in meters
            latitude: [H, W] latitude in degrees (-90 to 90)
        """
        H, W = elevation.shape
        self._temperature = np.zeros((H, W), dtype=np.float64)
        self._humidity = np.zeros((H, W), dtype=np.float64)
        self._precipitation = np.zeros((H, W), dtype=np.float64)
        self._wind_x = np.zeros((H, W), dtype=np.float64)
        self._wind_y = np.zeros((H, W), dtype=np.float64)
        self._cloud_cover = np.zeros((H, W), dtype=np.float64)

        self._baseline_temperature = np.zeros((H, W), dtype=np.float64)
        self._baseline_precipitation = np.zeros((H, W), dtype=np.float64)

        for y in range(H):
            for x in range(W):
                lat = latitude[y, x]
                elev = elevation[y, x]

                # Baseline temperature: latitude + altitude effect
                base_temp = self._compute_baseline_temperature(lat, elev)
                self._baseline_temperature[y, x] = base_temp
                self._temperature[y, x] = base_temp

                # Baseline precipitation
                base_precip = self._compute_baseline_precipitation(lat, elev)
                self._baseline_precipitation[y, x] = base_precip
                self._precipitation[y, x] = base_precip

                # Baseline humidity
                self._humidity[y, x] = self._compute_baseline_humidity(lat, elev, base_precip)

    def _compute_baseline_temperature(self, latitude: float, elevation: float) -> float:
        """
        Compute baseline temperature based on latitude and elevation.

        Uses:
        - Equator = warmest, poles = coldest
        - Lapse rate: -6.5°C per 1000m
        """
        # Normalize latitude to [-1, 1]
        lat_norm = latitude / 90.0

        # Equatorial temperature
        equator_temp = self.config.equator_temperature
        pole_temp = self.config.poles_temperature

        # Temperature decreases from equator to poles
        lat_temp = equator_temp - (equator_temp - pole_temp) * abs(lat_norm)

        # Altitude effect
        altitude_temp = -self.config.temperature_lapse_rate * (elevation / 1000.0)

        return lat_temp + altitude_temp

    def _compute_baseline_precipitation(self, latitude: float, elevation: float) -> float:
        """
        Compute baseline annual precipitation.

        Higher near equator (ITCZ), lower in subtropics (horse latitudes),
        moderate in mid-latitudes, low at poles.
        """
        lat_norm = abs(latitude / 90.0)  # Distance from equator

        # ITCZ (near equator) is wet
        # Horse latitudes (around 30°) are dry
        # Mid-latitudes (around 45-60°) are moderate
        # Polar regions are dry
        if lat_norm < 0.15:
            base = 2000.0  # Tropical rainforest
        elif lat_norm < 0.30:
            base = 800.0  # Tropical dry / monsoon
        elif lat_norm < 0.45:
            base = 600.0  # Desert fringe
        elif lat_norm < 0.65:
            base = 1200.0  # Temperate / monsoon
        elif lat_norm < 0.80:
            base = 400.0  # Subarctic
        else:
            base = 100.0  # Polar

        # Orographic effect: mountains are wetter on windward side
        if elevation > 500:
            base *= 1.0 + (elevation / 5000.0)

        return base

    def _compute_baseline_humidity(
        self, latitude: float, elevation: float, precipitation: float
    ) -> float:
        """Compute baseline humidity (0-1)."""
        base = self.config.humidity_base

        # Higher humidity near equator and poles, lower in deserts
        lat_norm = abs(latitude / 90.0)
        if lat_norm < 0.3:
            base += 0.2
        elif lat_norm > 0.7:
            base += 0.1
        else:
            base -= 0.1

        # Elevation reduces humidity
        base -= elevation / 20000.0

        # Higher humidity where it rains more
        base += (precipitation / 2000.0) * 0.3

        return max(0.0, min(1.0, base))

    def update(
        self,
        tick: int,
        temperature: np.ndarray,
        humidity: np.ndarray,
    ) -> None:
        """
        Update climate for the current tick.

        Applies seasonal variations, El Nino effects, and weather randomness.
        """
        if self._baseline_temperature is None:
            return

        H, W = temperature.shape
        season_index = (tick % (self._season_length * 4)) // self._season_length
        season = Season(season_index + 1)  # 1=SPRING, etc.

        # El Nino check
        if self._el_nino_duration > 0:
            self._el_nino_duration -= 1
        elif self._rng.random() < self.config.el_nino_probability:
            self._el_nino_active = True
            self._el_nino_duration = self._season_length * 2  # 2 years

        # Hemisphere: assume northern hemisphere for now
        hemisphere = 1

        for y in range(H):
            for x in range(W):
                base = self._baseline_temperature[y, x]

                # Seasonal variation (±15°C)
                season_mod = season.temperature_modifier(hemisphere) - 1.0
                seasonal_temp = base + season_mod * 15.0

                # Diurnal variation (±5°C, simplified)
                tick_in_day = tick % 24
                diurnal = 5.0 * np.sin((tick_in_day - 6) / 24.0 * 2 * np.pi)
                final_temp = seasonal_temp + diurnal

                # El Nino effect: global temperature +1°C, drought in some areas
                if self._el_nino_active:
                    final_temp += 1.0

                # Random weather fluctuation (±3°C)
                weather_noise = self._rng.normal(0, 1.0)
                final_temp += weather_noise

                temperature[y, x] = final_temp

                # Update humidity
                base_humidity = self._baseline_precipitation[y, x] / 3000.0
                # Seasonal humidity variation
                if season == Season.RAIN:
                    humidity_mod = 0.2
                elif season == Season.DRY:
                    humidity_mod = -0.2
                else:
                    humidity_mod = 0.0

                humidity[y, x] = max(
                    0.0,
                    min(1.0, base_humidity + humidity_mod + self._rng.uniform(-0.05, 0.05))
                )

                # Update precipitation (simplified)
                precip = self._baseline_precipitation[y, x]
                if season == Season.SPRING or season == Season.AUTUMN:
                    precip *= 1.0 + self._rng.uniform(-0.2, 0.2)
                elif season == Season.SUMMER:
                    precip *= 1.0 + self._rng.uniform(-0.3, 0.3)
                else:  # WINTER
                    # Cold air holds less moisture
                    temp = temperature[y, x]
                    if temp < 0:
                        precip *= 0.3  # Snow
                    else:
                        precip *= 1.0 + self._rng.uniform(-0.2, 0.2)

                self._precipitation[y, x] = max(0.0, precip)

    def get_climate_zone(self, latitude: float, temperature: float, precipitation: float) -> ClimateZone:
        """Determine Köppen-inspired climate zone."""
        if temperature >= 18:
            if precipitation > 2000:
                return ClimateZone.TROPICAL
            elif precipitation < 500:
                return ClimateZone.DRY_TROPICAL
            else:
                return ClimateZone.TROPICAL
        elif temperature >= -3:
            if precipitation > 1000:
                return ClimateZone.TEMPERATE
            elif precipitation < 500:
                return ClimateZone.DRY_CONTINENTAL
            else:
                return ClimateZone.TEMPERATE
        elif temperature >= -30:
            return ClimateZone.COLD_CONTINENTAL
        else:
            return ClimateZone.POLAR

    def get_wind(
        self, x: int, y: int, season_index: int
    ) -> tuple[float, float]:
        """Get wind vector (vx, vy) at a position for a season."""
        # Trade winds: easterly near equator
        lat_norm = (y / self.height - 0.5) * 2  # -1 to 1

        vx = -5.0  # Easterly trade winds
        vy = 0.0

        # Westerlies in mid-latitudes
        if 0.3 < abs(lat_norm) < 0.6:
            vx = 5.0  # Westerly

        # Polar easterlies
        if abs(lat_norm) > 0.7:
            vx = -3.0

        # Monsoon reversal (if enabled)
        if self.config.monsoon_enabled:
            if abs(lat_norm) < 0.3:
                # Summer: wet monsoon from ocean
                if season_index == 1:  # Summer (NH)
                    vy = 3.0
                    vx = 2.0
                elif season_index == 3:  # Winter (NH)
                    vy = -2.0
                    vx = -1.0

        # Add turbulence
        vx += self._rng.normal(0, 0.5)
        vy += self._rng.normal(0, 0.5)

        return (vx, vy)

    def get_season_name(self, tick: int) -> str:
        """Get the current season name."""
        season_index = (tick % (self._season_length * 4)) // self._season_length
        return Season(season_index + 1).name

    def is_el_nino(self) -> bool:
        """Check if El Nino is currently active."""
        return self._el_nino_active
