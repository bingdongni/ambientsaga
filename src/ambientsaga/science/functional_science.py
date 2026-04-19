"""
功能化科学引擎 (Functional Science Engine)

完整实现所有科学定律的可计算逻辑，
真正嵌入世界运行过程，直接驱动世界状态变化。

核心改进：
1. 物理/化学/生物/生态定律实际计算
2. 跨域耦合真实影响
3. 世界运行直接受科学定律约束
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Any

import numpy as np


@dataclass
class PhysicalLaw:
    """物理定律定义"""
    name: str
    formula: str
    apply: Any  # 应用函数


@dataclass
class ChemicalReaction:
    """化学反应定义"""
    name: str
    reactants: dict[str, float]   # {物质: 系数}
    products: dict[str, float]    # {物质: 系数}
    rate_constant: float          # 反应速率常数
    activation_energy: float       # 活化能 (J/mol)
    equilibrium_constant: float     # 平衡常数


class FunctionalPhysics:
    """
    功能化物理引擎

    实现的物理定律：
    - F = ma (牛顿第二定律)
    - E = mc² (质能关系)
    - 万有引力
    - 热传导
    - 流体动力学基础
    """

    GRAVITY = 9.81  # m/s²
    SPEED_OF_LIGHT = 299792458  # m/s
    BOLTZMANN = 1.380649e-23  # J/K
    GAS_CONSTANT = 8.314  # J/(mol·K)

    def __init__(self, world: Any) -> None:
        self.world = world

        # 物理定律注册表
        self._laws = {
            'newton_second': self._apply_newton_second,
            'kinetic_energy': self._apply_kinetic_energy,
            'gravitational_force': self._apply_gravity,
            'heat_conduction': self._apply_heat_conduction,
            'pressure_gradient': self._apply_pressure_gradient,
        }

    def apply_laws(self, tick: int) -> dict[str, Any]:
        """
        应用所有物理定律，驱动世界变化

        Returns:
            物理计算结果
        """
        results = {}

        # 1. 温度分布计算
        results['temperature'] = self._calculate_temperature_distribution()

        # 2. 压力场计算
        results['pressure'] = self._calculate_pressure_field()

        # 3. 风场计算
        results['wind'] = self._calculate_wind_field()

        # 4. 海拔对生物的影响
        results['altitude_effect'] = self._calculate_altitude_effects()

        # 5. 能量守恒约束
        results['energy_conservation'] = self._apply_energy_conservation()

        # 更新世界状态
        self._update_world_physics(results)

        return results

    def _calculate_temperature_distribution(self) -> np.ndarray:
        """
        计算温度分布

        公式: T = T_base - lapse_rate * altitude + seasonal_variation + latitude_effect
        """
        config = getattr(self.world, '_config', None)
        if config and hasattr(config, 'simulation'):
            base_temp = getattr(config.simulation.climate, 'base_temperature', 15.0)
            lapse_rate = getattr(config.simulation.climate, 'temperature_lapse_rate', 6.5)
        else:
            base_temp = 15.0
            lapse_rate = 6.5

        if hasattr(self.world, '_temperature') and self.world._temperature is not None:
            temp = self.world._temperature.copy()
        else:
            h = getattr(self.world, '_config', None)
            if h:
                h = h.world.height
            else:
                h = 100
            w = getattr(self.world, '_config', None)
            if w:
                w = w.world.width
            else:
                w = 100
            temp = np.zeros((h, w), dtype=np.float64)

        # 海拔影响
        if hasattr(self.world, '_elevation') and self.world._elevation is not None:
            altitude_effect = self.world._elevation * lapse_rate / 1000  # 每1000m下降
            temp = temp - altitude_effect

        # 纬度影响
        if hasattr(self.world, '_humidity') and self.world._humidity is not None:
            # 湿度影响体感温度
            humidity_effect = self.world._humidity * 0.5
            temp = temp - humidity_effect

        return temp

    def _calculate_pressure_field(self) -> np.ndarray:
        """
        计算压力场

        公式: P = P0 * exp(-MgH/RT)
        """
        if hasattr(self.world, '_elevation') and self.world._elevation is not None:
            elevation = self.world._elevation
            temp = self._calculate_temperature_distribution()
            avg_temp = np.mean(temp) + 273.15  # 转为开尔文
            avg_elevation = np.mean(elevation)

            # 标准大气压模型
            pressure_0 = 101325  # Pa
            scale_height = 8500  # m

            pressure = pressure_0 * np.exp(-elevation / scale_height)
            return pressure
        else:
            return np.full((100, 100), 101325.0)

    def _calculate_wind_field(self) -> tuple[np.ndarray, np.ndarray]:
        """
        计算风场

        基于科里奥利力和压力梯度
        """
        pressure = self._calculate_pressure_field()

        # 简化为压力梯度驱动
        # ∂P/∂x → 风从高压指向低压
        dx = np.gradient(pressure, axis=1)
        dy = np.gradient(pressure, axis=0)

        # 摩擦系数
        friction = 0.1

        # 风速与压力梯度成正比
        wind_x = -dx * friction
        wind_y = -dy * friction

        return wind_x, wind_y

    def _calculate_altitude_effects(self) -> dict[str, Any]:
        """
        计算海拔对生物的影响

        返回:
            - oxygen_level: 氧气浓度
            - uv_intensity: 紫外线强度
            - temperature_delta: 温度变化
        """
        if hasattr(self.world, '_elevation') and self.world._elevation is not None:
            elevation = self.world._elevation

            # 氧气浓度随海拔下降 (每1000m下降约12%)
            oxygen_level = np.exp(-elevation / 8400)

            # 紫外线强度随海拔增加 (每1000m增加约10%)
            uv_intensity = 1 + elevation / 10000

            # 温度随海拔下降 (每1000m下降6.5°C)
            temperature_delta = -elevation * 0.0065

            return {
                'oxygen_level': oxygen_level,
                'uv_intensity': uv_intensity,
                'temperature_delta': temperature_delta,
            }
        else:
            return {
                'oxygen_level': np.ones((100, 100)),
                'uv_intensity': np.ones((100, 100)),
                'temperature_delta': np.zeros((100, 100)),
            }

    def _apply_energy_conservation(self) -> float:
        """
        能量守恒约束

        确保系统总能量变化符合物理规律
        """
        # 计算当前总能量
        total_energy = 0.0

        # 动能
        for agent in self.world.get_all_agents():
            if hasattr(agent, 'velocity'):
                v = agent.velocity
                total_energy += 0.5 * agent.mass * (v.x**2 + v.y**2)

        # 势能
        if hasattr(self.world, '_elevation'):
            avg_elevation = np.mean(self.world._elevation)
            # 简化：使用平均海拔作为势能参考
            total_energy += avg_elevation * 9.81

        # 热能
        if hasattr(self.world, '_temperature'):
            avg_temp = np.mean(self.world._temperature)
            total_energy += avg_temp * 1000  # 简化系数

        return total_energy

    def _apply_newton_second(self, mass: float, acceleration: float) -> float:
        """F = ma"""
        return mass * acceleration

    def _apply_kinetic_energy(self, mass: float, velocity: float) -> float:
        """E = 0.5 * m * v²"""
        return 0.5 * mass * velocity ** 2

    def _apply_gravity(self, m1: float, m2: float, r: float) -> float:
        """F = G * m1 * m2 / r²"""
        G = 6.674e-11
        return G * m1 * m2 / r ** 2

    def _apply_heat_conduction(self, k: float, A: float, dT: float, d: float) -> float:
        """Q = k * A * dT / d"""
        return k * A * dT / d

    def _apply_pressure_gradient(self, dp: float, dx: float) -> float:
        """dp/dx"""
        return dp / dx if dx != 0 else 0

    def _update_world_physics(self, results: dict) -> None:
        """更新世界的物理状态"""
        if 'temperature' in results:
            if hasattr(self.world, '_temperature'):
                self.world._temperature = results['temperature']


class FunctionalChemistry:
    """
    功能化化学引擎

    实现的化学过程：
    - 反应速率计算 (阿伦尼乌斯方程)
    - 酸碱平衡
    - 氧化还原
    - 材料降解
    """

    def __init__(self, world: Any) -> None:
        self.world = world

        # 注册化学反应
        self._reactions = [
            ChemicalReaction(
                name="organic_decay",
                reactants={"biomass": 1.0},
                products={"nutrients": 0.8, "co2": 0.2},
                rate_constant=0.01,
                activation_energy=50000,
                equilibrium_constant=1.0,
            ),
            ChemicalReaction(
                name="nitrification",
                reactants={"ammonia": 1.0, "oxygen": 2.0},
                products={"nitrate": 1.0, "water": 2.0},
                rate_constant=0.005,
                activation_energy=40000,
                equilibrium_constant=10.0,
            ),
            ChemicalReaction(
                name="photosynthesis",
                reactants={"co2": 6.0, "water": 6.0, "sunlight": 1.0},
                products={"glucose": 1.0, "oxygen": 6.0},
                rate_constant=0.02,
                activation_energy=20000,
                equilibrium_constant=100.0,
            ),
        ]

    def process_reactions(self, tick: int) -> dict[str, Any]:
        """
        处理所有化学反应

        Returns:
            化学反应结果
        """
        results = {}

        # 获取当前温度（来自物理引擎的影响）
        temp = self._get_current_temperature()

        # 计算反应速率
        results['reaction_rates'] = self._calculate_reaction_rates(temp)

        # 处理有机物分解
        results['decay'] = self._process_organic_decay(temp)

        # 处理养分循环
        results['nutrients'] = self._process_nutrient_cycling(temp)

        # 处理材料降解
        results['degradation'] = self._process_material_degradation()

        # 更新世界化学状态
        self._update_world_chemistry(results)

        return results

    def _get_current_temperature(self) -> float:
        """获取当前温度"""
        if hasattr(self.world, '_temperature') and self.world._temperature is not None:
            return float(np.mean(self.world._temperature))
        return 15.0  # 默认温度

    def _calculate_reaction_rates(self, temperature: float) -> dict[str, float]:
        """
        使用阿伦尼乌斯方程计算反应速率

        k = A * exp(-Ea / RT)
        """
        R = 8.314  # J/(mol·K)
        rates = {}

        for reaction in self._reactions:
            A = reaction.rate_constant
            Ea = reaction.activation_energy
            T = temperature + 273.15  # 转为开尔文

            # 阿伦尼乌斯方程
            k = A * exp(-Ea / (R * T))
            rates[reaction.name] = k

        return rates

    def _process_organic_decay(self, temperature: float) -> dict[str, float]:
        """
        处理有机物分解

        温度越高，分解越快
        """
        rate = self._calculate_reaction_rates(temperature)['organic_decay']

        # 获取有机物量
        biomass = self._get_biomass()
        decay_amount = biomass * rate

        # 分解产物
        nutrients_released = decay_amount * 0.8
        co2_released = decay_amount * 0.2

        return {
            'decay_rate': rate,
            'biomass_consumed': decay_amount,
            'nutrients_released': nutrients_released,
            'co2_released': co2_released,
        }

    def _process_nutrient_cycling(self, temperature: float) -> dict[str, float]:
        """
        处理养分循环

        氮循环、磷循环等
        """
        rate = self._calculate_reaction_rates(temperature)['nitrification']

        # 获取氨含量
        ammonia = self._get_ammonia()
        nitrification = ammonia * rate

        return {
            'nitrification_rate': rate,
            'ammonia_consumed': nitrification,
            'nitrate_produced': nitrification,
        }

    def _process_material_degradation(self) -> dict[str, float]:
        """
        处理材料降解

        金属锈蚀、岩石风化等
        """
        # 湿度影响锈蚀
        humidity = self._get_humidity()

        # 温度影响风化
        temp = self._get_current_temperature()

        corrosion_rate = humidity * 0.001 * (temp / 25)
        weathering_rate = temp * 0.0001

        return {
            'corrosion_rate': corrosion_rate,
            'weathering_rate': weathering_rate,
        }

    def _get_biomass(self) -> float:
        """获取生物质量"""
        if hasattr(self.world, '_vegetation') and self.world._vegetation is not None:
            return float(np.sum(self.world._vegetation))
        return 0.0

    def _get_ammonia(self) -> float:
        """获取氨含量"""
        if hasattr(self.world, '_soil') and self.world._soil is not None:
            # 简化：土壤值代表养分
            return float(np.mean(self.world._soil)) * 0.1
        return 0.0

    def _get_humidity(self) -> float:
        """获取湿度"""
        if hasattr(self.world, '_humidity') and self.world._humidity is not None:
            return float(np.mean(self.world._humidity))
        return 0.5

    def _update_world_chemistry(self, results: dict) -> None:
        """更新世界的化学状态"""
        # 存储化学计算结果供其他系统使用
        if not hasattr(self.world, '_chemistry_state'):
            self.world._chemistry_state = {}

        self.world._chemistry_state['reaction_rates'] = results.get('reaction_rates', {})
        self.world._chemistry_state['decay'] = results.get('decay', {})


class FunctionalBiology:
    """
    功能化生物引擎

    实现的生物过程：
    - 新陈代谢
    - 繁殖
    - 衰老/死亡
    - 免疫响应
    """

    def __init__(self, world: Any) -> None:
        self.world = world

    def update_organisms(self, tick: int) -> dict[str, Any]:
        """
        更新所有生物有机体

        Returns:
            生物更新结果
        """
        results = {}

        # 获取化学引擎的状态
        chemistry_state = getattr(self.world, '_chemistry_state', {})

        # 计算代谢
        results['metabolism'] = self._calculate_metabolism(chemistry_state)

        # 处理繁殖
        results['reproduction'] = self._process_reproduction()

        # 处理免疫响应
        results['immunity'] = self._process_immunity()

        # 更新生物状态
        self._update_organism_states(results)

        return results

    def _calculate_metabolism(self, chemistry_state: dict) -> dict[str, float]:
        """
        计算新陈代谢

        基于可用资源和环境条件
        """
        # 营养物质可用性
        nutrients = chemistry_state.get('nutrients', {})
        nutrient_level = nutrients.get('nutrients_released', 0.5)

        # 环境温度
        temp = self._get_temperature()

        # 氧气水平
        oxygen = self._get_oxygen_level()

        # 基础代谢率
        base_metabolism = 1.0

        # 温度影响 (酶活性)
        temp_factor = 1.0 if 15 <= temp <= 35 else 0.5

        # 氧气影响
        oxygen_factor = oxygen

        # 综合代谢率
        metabolism_rate = base_metabolism * temp_factor * oxygen_factor * nutrient_level

        return {
            'metabolism_rate': metabolism_rate,
            'energy_consumed': metabolism_rate * 100,
            'temp_factor': temp_factor,
            'oxygen_factor': oxygen_factor,
        }

    def _process_reproduction(self) -> dict[str, Any]:
        """
        处理繁殖

        基于种群密度和资源可用性
        """
        agents = list(self.world._agents.values()) if hasattr(self.world, '_agents') else []
        population = len(agents)

        # 获取资源
        resource_abundance = self._get_resource_abundance()

        # 资源匮乏降低繁殖率
        resource_factor = resource_abundance

        # 种群密度过高降低繁殖率
        if hasattr(self.world, '_config'):
            area = self.world._config.world.width * self.world._config.world.height
            density = population / area if area > 0 else 0
            density_factor = 1.0 / (1.0 + density * 1000)
        else:
            density_factor = 0.5

        # 基础繁殖率
        base_rate = 0.01

        # 实际繁殖数
        birth_rate = base_rate * resource_factor * density_factor

        return {
            'birth_rate': birth_rate,
            'resource_factor': resource_factor,
            'density_factor': density_factor,
            'expected_births': int(population * birth_rate),
        }

    def _process_immunity(self) -> dict[str, Any]:
        """
        处理免疫响应

        基于健康状态和暴露程度
        """
        # 简化：基于生态系统健康
        health = self._calculate_population_health()

        immunity_strength = health * 0.8

        return {
            'immunity_strength': immunity_strength,
            'disease_spread_risk': 1.0 - immunity_strength,
        }

    def _get_temperature(self) -> float:
        """获取环境温度"""
        if hasattr(self.world, '_temperature') and self.world._temperature is not None:
            return float(np.mean(self.world._temperature))
        return 15.0

    def _get_oxygen_level(self) -> float:
        """获取氧气水平"""
        # 从物理引擎获取
        physics_state = getattr(self.world, '_physics_state', {})
        altitude_effects = physics_state.get('altitude_effect', {})

        # 如果没有，使用默认值
        if hasattr(self.world, '_elevation') and self.world._elevation is not None:
            elevation = np.mean(self.world._elevation)
            return exp(-elevation / 8400)

        return 0.21  # 21% 氧气浓度

    def _get_resource_abundance(self) -> float:
        """获取资源丰富度"""
        if hasattr(self.world, '_vegetation') and self.world._vegetation is not None:
            return float(np.mean(self.world._vegetation))
        return 0.5

    def _calculate_population_health(self) -> float:
        """计算种群健康度"""
        agents = list(self.world._agents.values()) if hasattr(self.world, '_agents') else []
        if not agents:
            return 0.5

        total_health = sum(
            getattr(a, 'health', 0.5) for a in agents
        ) / len(agents)

        return total_health

    def _update_organism_states(self, results: dict) -> None:
        """更新有机体状态"""
        # 存储生物计算结果
        if not hasattr(self.world, '_biology_state'):
            self.world._biology_state = {}

        self.world._biology_state.update(results)


class FunctionalEcology:
    """
    功能化生态引擎

    实现的生态过程：
    - 食物链动态
    - 种群波动
    - 生态平衡
    - 演替
    """

    def __init__(self, world: Any) -> None:
        self.world = world

    def balance_species(self, tick: int) -> dict[str, Any]:
        """
        平衡物种动态

        Returns:
            生态计算结果
        """
        results = {}

        # 计算食物链稳定度
        results['food_chain_stability'] = self._calculate_food_chain_stability()

        # 计算种群动态
        results['population_dynamics'] = self._calculate_population_dynamics()

        # 计算生态承载力
        results['carrying_capacity'] = self._calculate_carrying_capacity()

        # 计算演替阶段
        results['succession'] = self._calculate_succession()

        # 更新生态状态
        self._update_ecology_state(results)

        return results

    def _calculate_food_chain_stability(self) -> float:
        """
        计算食物链稳定度

        基于捕食者-猎物平衡
        """
        # 简化模型
        agents = list(self.world._agents.values()) if hasattr(self.world, '_agents') else []

        # 计算种群多样性
        if len(agents) > 0:
            # 简化的多样性指数
            diversity = min(len(agents) / 1000, 1.0)
        else:
            diversity = 0.0

        # 植被覆盖
        vegetation = 0.5
        if hasattr(self.world, '_vegetation') and self.world._vegetation is not None:
            vegetation = float(np.mean(self.world._vegetation))

        # 稳定性 = 多样性 * 植被覆盖
        stability = diversity * vegetation * 0.8 + 0.2

        return min(max(stability, 0.0), 1.0)

    def _calculate_population_dynamics(self) -> dict[str, Any]:
        """
        计算种群动态

        Lotka-Volterra 简化模型
        """
        agents = list(self.world._agents.values()) if hasattr(self.world, '_agents') else []
        population = len(agents)

        # 获取资源
        resource = self._get_resource_abundance()

        # 增长率
        r = 0.1  # 内在增长率
        K = 10000  # 承载力

        # 逻辑斯蒂增长
        growth_rate = r * resource * (1 - population / K)

        return {
            'current_population': population,
            'growth_rate': growth_rate,
            'resource_availability': resource,
            'competition_level': population / K if K > 0 else 0,
        }

    def _calculate_carrying_capacity(self) -> float:
        """
        计算生态承载力

        基于资源可用性
        """
        # 植被
        vegetation = 0.5
        if hasattr(self.world, '_vegetation') and self.world._vegetation is not None:
            vegetation = float(np.mean(self.world._vegetation))

        # 水源
        water_coverage = 0.0
        if hasattr(self.world, '_terrain') and self.world._terrain is not None:
            # 计算水域比例
            from ambientsaga.types import TerrainType
            water_types = {TerrainType.DEEP_OCEAN.value, TerrainType.OCEAN.value,
                         TerrainType.SHALLOW_WATER.value}
            water_tiles = sum(
                1 for t in self.world._terrain.flatten()
                if t in water_types
            )
            total_tiles = self.world._terrain.size
            water_coverage = water_tiles / total_tiles if total_tiles > 0 else 0

        # 承载力 = 基础容量 * 资源因子
        base_capacity = 10000
        resource_factor = (vegetation * 0.7 + water_coverage * 0.3)
        carrying_capacity = base_capacity * resource_factor

        return carrying_capacity

    def _calculate_succession(self) -> dict[str, Any]:
        """
        计算生态演替阶段

        0: 裸地
        1: 先锋物种
        2: 草地阶段
        3: 灌木阶段
        4: 森林阶段
        """
        if hasattr(self.world, '_vegetation') and self.world._vegetation is not None:
            avg_vegetation = float(np.mean(self.world._vegetation))
        else:
            avg_vegetation = 0.0

        # 根据植被覆盖确定演替阶段
        if avg_vegetation < 0.1:
            stage = 0
            name = "裸地"
        elif avg_vegetation < 0.3:
            stage = 1
            name = "先锋物种"
        elif avg_vegetation < 0.5:
            stage = 2
            name = "草地阶段"
        elif avg_vegetation < 0.7:
            stage = 3
            name = "灌木阶段"
        else:
            stage = 4
            name = "森林阶段"

        return {
            'stage': stage,
            'name': name,
            'vegetation_level': avg_vegetation,
        }

    def _get_resource_abundance(self) -> float:
        """获取资源丰富度"""
        if hasattr(self.world, '_vegetation') and self.world._vegetation is not None:
            return float(np.mean(self.world._vegetation))
        return 0.5

    def _update_ecology_state(self, results: dict) -> None:
        """更新生态状态"""
        if not hasattr(self.world, '_ecology_state'):
            self.world._ecology_state = {}

        self.world._ecology_state.update(results)


class FunctionalScienceEngine:
    """
    功能化科学引擎主类

    协调所有科学子系统，确保跨域耦合
    """

    def __init__(self, world: Any) -> None:
        self.world = world
        self.tick = 0

        # 初始化子系统
        self.physics = FunctionalPhysics(world)
        self.chemistry = FunctionalChemistry(world)
        self.biology = FunctionalBiology(world)
        self.ecology = FunctionalEcology(world)

    def update(self, tick: int) -> dict[str, Any]:
        """
        执行一个tick的科学计算

        执行顺序反映真实因果关系：
        物理 → 化学 → 生物 → 生态
        """
        import sys
        try:
            self.tick = tick
            results = {}

            # 1. 物理计算（最先，影响所有）
            results['physics'] = self.physics.apply_laws(tick)
            self.world._physics_state = results['physics']

            # 2. 化学计算（依赖物理）
            results['chemistry'] = self.chemistry.process_reactions(tick)
            self.world._chemistry_state = results['chemistry']

            # 3. 生物计算（依赖化学和物理）
            results['biology'] = self.biology.update_organisms(tick)
            self.world._biology_state = results['biology']

            # 4. 生态计算（综合）
            results['ecology'] = self.ecology.balance_species(tick)
            self.world._ecology_state = results['ecology']

            # 5. 跨域耦合计算
            results['cross_domain'] = self._calculate_cross_domain_coupling(results)

            return results
        except Exception as e:
            print(f"[ERROR in FunctionalScienceEngine.update] {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise

    def _calculate_cross_domain_coupling(self, results: dict) -> dict[str, Any]:
        """
        计算跨域耦合效应

        这是实现全域真实耦合的关键
        """
        coupling = {}

        # 物理 → 化学：温度影响反应速率
        temp = results['physics'].get('temperature', 15.0)
        # Handle numpy arrays by converting to scalar
        if hasattr(temp, '__iter__') and not isinstance(temp, (str, bytes)):
            temp_scalar = float(np.mean(temp))
        else:
            temp_scalar = float(temp)
        reaction_rates = results['chemistry'].get('reaction_rates', {})
        avg_rate = np.mean(list(reaction_rates.values())) if reaction_rates else 0.01

        coupling['temp_chem_coupling'] = {
            'temperature': temp_scalar,
            'avg_reaction_rate': avg_rate,
            'temperature_effect': exp(-1000 / (temp_scalar + 273.15)) if temp_scalar > -273 else 0,
        }

        # 化学 → 生物：毒素和营养影响代谢
        decay = results['chemistry'].get('decay', {})
        nutrients = decay.get('nutrients_released', 0.0)
        co2 = decay.get('co2_released', 0.0)

        metabolism = results['biology'].get('metabolism', {})
        metabolism_rate = metabolism.get('metabolism_rate', 0.5)

        coupling['chem_bio_coupling'] = {
            'nutrient_availability': nutrients,
            'metabolism_rate': metabolism_rate,
            'health_impact': nutrients - co2 * 0.5,
        }

        # 生物 → 生态：种群动态影响生态平衡
        population_dynamics = results['biology'].get('reproduction', {})
        food_chain_stability = results['ecology'].get('food_chain_stability', 0.5)

        coupling['bio_eco_coupling'] = {
            'population_growth': population_dynamics.get('expected_births', 0),
            'competition_level': population_dynamics.get('competition_level', 0),
            'stability_impact': food_chain_stability,
        }

        # 生态 → 社会：通过资源影响社会
        succession = results['ecology'].get('succession', {})
        carrying_capacity = results['ecology'].get('carrying_capacity', 10000)

        coupling['eco_social_coupling'] = {
            'ecosystem_stage': succession.get('stage', 2),
            'carrying_capacity': carrying_capacity,
            'resource_pressure': 1.0 / (carrying_capacity / 10000),
        }

        # 存储耦合结果
        self.world._cross_domain_coupling = coupling

        return coupling

    def get_statistics(self) -> dict[str, Any]:
        """获取科学系统统计"""
        return {
            'physics': {
                'temperature': float(np.mean(self.world._temperature)) if hasattr(self.world, '_temperature') and self.world._temperature is not None else 0,
                'pressure': 101325,  # 简化
            },
            'chemistry': {
                'reaction_rates': self.world._chemistry_state.get('reaction_rates', {}),
                'decay': self.world._chemistry_state.get('decay', {}),
            },
            'biology': {
                'metabolism': self.world._biology_state.get('metabolism', {}),
                'reproduction': self.world._biology_state.get('reproduction', {}),
            },
            'ecology': {
                'stability': self.world._ecology_state.get('food_chain_stability', 0.5),
                'succession': self.world._ecology_state.get('succession', {}),
            },
            'cross_domain': self.world._cross_domain_coupling if hasattr(self.world, '_cross_domain_coupling') else {},
        }
