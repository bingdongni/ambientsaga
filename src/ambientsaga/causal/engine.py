"""
Unified Causal Engine - 统一因果引擎

实现全域动态耦合，所有领域通过因果传导链相互影响。
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional, List
from enum import Enum

if TYPE_CHECKING:
    from ambientsaga.world.state import World


class CausalityStrength(Enum):
    """因果强度等级"""
    NEGLIGIBLE = 0.01
    WEAK = 0.1
    MODERATE = 0.3
    STRONG = 0.6
    CRITICAL = 1.0


@dataclass
class CausalLink:
    """因果链节点"""
    source_domain: str  # 来源领域 (physics, chemistry, biology, ecology, economics, sociology, etc.)
    target_domain: str  # 目标领域
    mechanism: str  # 传导机制
    strength: CausalityStrength = CausalityStrength.MODERATE
    enabled: bool = True

    def apply(self, source_value: float, coupling_factor: float = 1.0) -> float:
        """应用因果传导"""
        if not self.enabled:
            return 0.0
        return source_value * self.strength.value * coupling_factor


@dataclass
class CausationEvent:
    """因果事件"""
    source_domain: str
    target_domain: str
    source_value: float
    propagation: float
    tick: int
    metadata: dict[str, Any] = field(default_factory=dict)


class UnifiedCausalEngine:
    """
    统一因果引擎

    实现所有领域之间的动态耦合：
    - Physics → Chemistry (温度影响反应)
    - Chemistry → Biology (代谢和能量)
    - Biology → Ecology (种群动态)
    - Ecology → Economics (资源可用性)
    - Economics → Sociology (财富分配)
    - Sociology → Politics (权力结构)
    - Politics → Culture (意识形态)
    - Culture → Psychology (价值观)
    - 以及所有反向耦合

    传导链：
    Input(领域A变化) → 检测变化 → 计算因果强度 → 传播到下游领域 → 触发响应
    """

    def __init__(self, world: "World") -> None:
        self.world = world
        self._links: list[CausalLink] = []
        self._domain_states: dict[str, float] = {
            "physics": 1.0,
            "chemistry": 1.0,
            "biology": 1.0,
            "ecology": 1.0,
            "economics": 1.0,
            "sociology": 1.0,
            "politics": 1.0,
            "culture": 1.0,
            "psychology": 1.0,
        }
        self._causation_events: list[CausationEvent] = []
        self._coupling_history: list[dict[str, float]] = []
        self._initialize_links()

    def _initialize_links(self) -> None:
        """初始化预设的因果链"""
        # Physics → Chemistry
        self._links.append(CausalLink(
            source_domain="physics",
            target_domain="chemistry",
            mechanism="temperature_affects_reaction_rate",
            strength=CausalityStrength.STRONG,
        ))

        # Chemistry → Biology
        self._links.append(CausalLink(
            source_domain="chemistry",
            target_domain="biology",
            mechanism="metabolic_energy_transfer",
            strength=CausalityStrength.STRONG,
        ))

        # Biology → Ecology
        self._links.append(CausalLink(
            source_domain="biology",
            target_domain="ecology",
            mechanism="population_dynamics",
            strength=CausalityStrength.MODERATE,
        ))

        # Ecology → Economics
        self._links.append(CausalLink(
            source_domain="ecology",
            target_domain="economics",
            mechanism="resource_availability",
            strength=CausalityStrength.STRONG,
        ))

        # Economics → Sociology
        self._links.append(CausalLink(
            source_domain="economics",
            target_domain="sociology",
            mechanism="wealth_distribution_social_stratification",
            strength=CausalityStrength.MODERATE,
        ))

        # Sociology → Politics
        self._links.append(CausalLink(
            source_domain="sociology",
            target_domain="politics",
            mechanism="social_movements_power_structures",
            strength=CausalityStrength.MODERATE,
        ))

        # Politics → Culture
        self._links.append(CausalLink(
            source_domain="politics",
            target_domain="culture",
            mechanism="institutional_legitimacy",
            strength=CausalityStrength.WEAK,
        ))

        # Culture → Psychology
        self._links.append(CausalLink(
            source_domain="culture",
            target_domain="psychology",
            mechanism="cultural_values_individual_beliefs",
            strength=CausalityStrength.WEAK,
        ))

        # Reverse links
        self._links.append(CausalLink(
            source_domain="culture",
            target_domain="politics",
            mechanism="ideology_affects_governance",
            strength=CausalityStrength.WEAK,
        ))

        self._links.append(CausalLink(
            source_domain="economics",
            target_domain="ecology",
            mechanism="economic_activity_environmental_impact",
            strength=CausalityStrength.MODERATE,
        ))

    def get_causal_links(self, source_domain: Optional[str] = None, target_domain: Optional[str] = None) -> List[CausalLink]:
        """获取因果链"""
        links = self._links
        if source_domain:
            links = [l for l in links if l.source_domain == source_domain]
        if target_domain:
            links = [l for l in links if l.target_domain == target_domain]
        return links

    def add_causal_link(self, link: CausalLink) -> None:
        """添加新的因果链"""
        self._links.append(link)

    def remove_causal_link(self, source_domain: str, target_domain: str) -> bool:
        """移除因果链"""
        for i, link in enumerate(self._links):
            if link.source_domain == source_domain and link.target_domain == target_domain:
                self._links.pop(i)
                return True
        return False

    def update_domain_state(self, domain: str, value: float) -> None:
        """更新领域状态"""
        old_value = self._domain_states.get(domain, 1.0)
        self._domain_states[domain] = value

        # 检测变化并传播
        if abs(old_value - value) > 0.01:
            self._propagate_change(domain, value - old_value)

    def _propagate_change(self, source_domain: str, delta: float) -> None:
        """传播领域变化到下游"""
        for link in self._links:
            if link.source_domain == source_domain and link.enabled:
                # 计算传播值
                propagation = delta * link.strength.value

                # 更新目标领域
                if link.target_domain in self._domain_states:
                    self._domain_states[link.target_domain] += propagation

                # 记录因果事件
                event = CausationEvent(
                    source_domain=source_domain,
                    target_domain=link.target_domain,
                    source_value=delta,
                    propagation=propagation,
                    tick=self.world.tick if hasattr(self.world, 'tick') else 0,
                    metadata={
                        "mechanism": link.mechanism,
                        "strength": link.strength.name,
                    }
                )
                self._causation_events.append(event)

    def get_domain_state(self, domain: str) -> float:
        """获取领域状态"""
        return self._domain_states.get(domain, 1.0)

    def get_coupling_factor(self, domain1: str, domain2: str) -> float:
        """获取两个领域之间的耦合因子"""
        for link in self._links:
            if ((link.source_domain == domain1 and link.target_domain == domain2) or
                (link.source_domain == domain2 and link.target_domain == domain1)):
                return link.strength.value
        return 0.0

    def get_causation_events(self, lookback: int = 100) -> list[CausationEvent]:
        """获取最近的因果事件"""
        return self._causation_events[-lookback:]

    def process_cross_domain_effects(self, tick: int) -> None:
        """
        处理跨领域效应 - 每个tick调用

        这个方法整合所有领域的状态变化并传播因果效应。
        """
        # 从世界状态中提取物理状态
        if hasattr(self.world, '_temperature') and self.world._temperature is not None:
            avg_temp = float(self.world._temperature.mean())
            # 将温度映射到 physics 状态
            temp_factor = (avg_temp - 250) / 100  # 归一化
            self.update_domain_state("physics", temp_factor)

        # 从生态系统中提取状态
        if hasattr(self.world, '_vegetation') and self.world._vegetation is not None:
            avg_veg = float(self.world._vegetation.mean())
            self.update_domain_state("ecology", avg_veg)

        # 从经济系统中提取状态
        if hasattr(self.world, '_economy') and self.world._economy is not None:
            # 从 emergent economy 中提取状态
            econ_state = getattr(self.world._economy, '_aggregate_state', {})
            if econ_state:
                self.update_domain_state("economics", econ_state.get("activity", 0.5))

        # 从社会系统中提取状态
        agent_count = self.world.get_agent_count() if hasattr(self.world, 'get_agent_count') else 0
        if agent_count > 0:
            # 基于人口计算社会学状态
            social_factor = min(1.0, agent_count / 1000)
            self.update_domain_state("sociology", social_factor)

        # 记录耦合历史
        self._coupling_history.append(self._domain_states.copy())

        # 保持历史记录在合理范围内
        if len(self._coupling_history) > 1000:
            self._coupling_history = self._coupling_history[-500:]

    def get_statistics(self) -> dict[str, Any]:
        """获取因果系统统计"""
        return {
            "total_links": len(self._links),
            "enabled_links": len([l for l in self._links if l.enabled]),
            "causation_events_count": len(self._causation_events),
            "domain_states": self._domain_states.copy(),
            "strongest_coupling": self._get_strongest_coupling(),
        }

    def _get_strongest_coupling(self) -> dict[str, float]:
        """获取最强的耦合"""
        strongest = None
        max_strength = 0
        for link in self._links:
            if link.strength.value > max_strength:
                max_strength = link.strength.value
                strongest = {
                    "source": link.source_domain,
                    "target": link.target_domain,
                    "strength": link.strength.value,
                    "mechanism": link.mechanism,
                }
        return strongest or {}
