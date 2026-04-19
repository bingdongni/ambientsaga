"""
Full Domain Coupling Engine — 跨学科统一因果框架。

Physics → Chemistry → Biology → Ecology → Medicine → Economics → Politics → Law → Culture → Ethics

所有科学定律形成统一的因果网络，一个域的变化会级联传播到所有相关域。
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ambientsaga.world.state import World


class Domain(Enum):
    """科学域"""
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    ECOLOGY = "ecology"
    MEDICINE = "medicine"
    ECONOMICS = "economics"
    POLITICS = "politics"
    LAW = "law"
    CULTURE = "culture"
    ETHICS = "ethics"
    MILITARY = "military"
    RELIGION = "religion"
    PSYCHOLOGY = "psychology"
    SOCIOLOGY = "sociology"


@dataclass
class ScientificLaw:
    """科学定律"""
    law_id: str
    name: str
    domain: Domain
    formula: Callable  # 可计算公式
    description: str
    coupling_strength: float = 1.0  # 耦合强度
    affected_domains: list[Domain] = field(default_factory=list)

    def evaluate(self, context: dict) -> dict:
        """评估定律"""
        try:
            result = self.formula(context)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


@dataclass
class CouplingRule:
    """跨域耦合规则"""
    rule_id: str
    source_domain: Domain
    target_domain: Domain
    transmission_function: Callable
    delay_ticks: int = 0
    decay_factor: float = 0.9
    threshold: float = 0.0

    def should_transmit(self, source_value: float) -> bool:
        return abs(source_value) > self.threshold

    def transmit(self, source_value: float) -> float:
        return self.transmission_function(source_value) * self.decay_factor


@dataclass
class DomainState:
    """域状态"""
    domain: Domain
    values: dict[str, float] = field(default_factory=dict)
    coupling_strengths: dict[Domain, float] = field(default_factory=dict)
    last_update: int = 0


class FullDomainCouplingEngine:
    """
    全学科耦合引擎。

    核心机制：
    1. 每个域维护自己的状态
    2. 域之间通过耦合规则连接
    3. 状态变化通过耦合规则传播到其他域
    4. 使用真实科学公式进行计算
    """

    def __init__(self, world: World):
        self.world = world
        self.domain_states: dict[Domain, DomainState] = {}
        self.laws: dict[Domain, list[ScientificLaw]] = {}
        self.coupling_rules: list[CouplingRule] = []
        self.coupling_history: list[dict] = []
        self._initialize_domains()
        self._initialize_laws()
        self._initialize_coupling_rules()

    def _initialize_domains(self) -> None:
        """初始化所有域"""
        for domain in Domain:
            self.domain_states[domain] = DomainState(domain=domain)

    def _initialize_laws(self) -> None:
        """初始化所有科学定律"""

        # ============ PHYSICS ============
        self.laws[Domain.PHYSICS] = [
            ScientificLaw(
                law_id="newton_gravity",
                name="牛顿引力定律",
                domain=Domain.PHYSICS,
                formula=lambda ctx: ctx.get("mass1", 1) * ctx.get("mass2", 1) /
                                   (ctx.get("distance", 1) ** 2 + 0.001),
                description="F = G * m1 * m2 / r^2",
                coupling_strength=1.0,
                affected_domains=[Domain.ECOLOGY, Domain.ECONOMICS]
            ),
            ScientificLaw(
                law_id="thermodynamics",
                name="热力学定律",
                domain=Domain.PHYSICS,
                formula=lambda ctx: ctx.get("energy", 100) * ctx.get("entropy_factor", 1.0),
                description="能量守恒与熵增",
                coupling_strength=0.8,
                affected_domains=[Domain.CHEMISTRY, Domain.BIOLOGY]
            ),
            ScientificLaw(
                law_id="ideal_gas",
                name="理想气体定律",
                domain=Domain.PHYSICS,
                formula=lambda ctx: (ctx.get("pressure", 1) * ctx.get("volume", 1)) /
                                   (ctx.get("temperature", 273) * 8.314),
                description="PV = nRT",
                coupling_strength=0.7,
                affected_domains=[Domain.CHEMISTRY, Domain.MEDICINE]
            ),
            ScientificLaw(
                law_id="kinetic_energy",
                name="动能定理",
                domain=Domain.PHYSICS,
                formula=lambda ctx: 0.5 * ctx.get("mass", 1) * (ctx.get("velocity", 1) ** 2),
                description="KE = 0.5 * m * v^2",
                coupling_strength=0.6,
                affected_domains=[Domain.ECONOMICS, Domain.MILITARY]
            ),
            ScientificLaw(
                law_id="radiation_decay",
                name="辐射衰减",
                domain=Domain.PHYSICS,
                formula=lambda ctx: ctx.get("initial_radiation", 1) * math.exp(
                    -ctx.get("decay_constant", 0.01) * ctx.get("time", 1)
                ),
                description="N = N0 * e^(-λt)",
                coupling_strength=0.5,
                affected_domains=[Domain.MEDICINE, Domain.BIOLOGY]
            ),
        ]

        # ============ CHEMISTRY ============
        self.laws[Domain.CHEMISTRY] = [
            ScientificLaw(
                law_id="arrhenius",
                name="阿伦尼乌斯方程",
                domain=Domain.CHEMISTRY,
                formula=lambda ctx: ctx.get("rate_constant", 1) * math.exp(
                    -ctx.get("activation_energy", 10000) / (ctx.get("temperature", 298) * 8.314)
                ),
                description="反应速率与温度的关系",
                coupling_strength=0.8,
                affected_domains=[Domain.PHYSICS, Domain.BIOLOGY]
            ),
            ScientificLaw(
                law_id="gibbs_energy",
                name="吉布斯自由能",
                domain=Domain.CHEMISTRY,
                formula=lambda ctx: ctx.get("enthalpy", 0) - ctx.get("temperature", 298) * ctx.get("entropy", 0),
                description="ΔG = ΔH - TΔS",
                coupling_strength=0.7,
                affected_domains=[Domain.PHYSICS, Domain.ECOLOGY]
            ),
            ScientificLaw(
                law_id="henry_law",
                name="亨利定律",
                domain=Domain.CHEMISTRY,
                formula=lambda ctx: ctx.get("partial_pressure", 1) * ctx.get("henry_constant", 0.001),
                description="气体溶解度与分压",
                coupling_strength=0.6,
                affected_domains=[Domain.MEDICINE, Domain.ECOLOGY]
            ),
            ScientificLaw(
                law_id="reaction_equilibrium",
                name="化学平衡",
                domain=Domain.CHEMISTRY,
                formula=lambda ctx: (ctx.get("products", 1) ** ctx.get("product_coeff", 1)) /
                                   (ctx.get("reactants", 1) ** ctx.get("reactant_coeff", 1)),
                description="K = [P]^p / [R]^r",
                coupling_strength=0.7,
                affected_domains=[Domain.BIOLOGY, Domain.ECOLOGY]
            ),
        ]

        # ============ BIOLOGY ============
        self.laws[Domain.BIOLOGY] = [
            ScientificLaw(
                law_id="logistic_growth",
                name="逻辑斯蒂增长",
                domain=Domain.BIOLOGY,
                formula=lambda ctx: ctx.get("growth_rate", 0.1) * ctx.get("population", 100) *
                                   (1 - ctx.get("population", 100) / ctx.get("carrying_capacity", 1000)),
                description="dN/dt = rN(1-N/K)",
                coupling_strength=1.0,
                affected_domains=[Domain.ECOLOGY, Domain.ECONOMICS]
            ),
            ScientificLaw(
                law_id="lotka_volterra",
                name="洛特卡-沃尔泰拉捕食方程",
                domain=Domain.BIOLOGY,
                formula=lambda ctx: {
                    "prey": ctx.get("prey_growth", 1) * ctx.get("prey", 100) - ctx.get("predation_rate", 0.01) * ctx.get("prey", 100) * ctx.get("predator", 10),
                    "predator": ctx.get("predation_rate", 0.01) * ctx.get("prey", 100) * ctx.get("predator", 10) - ctx.get("predator_death", 0.1) * ctx.get("predator", 10)
                },
                description="捕食者-猎物动态",
                coupling_strength=0.9,
                affected_domains=[Domain.ECOLOGY, Domain.ECONOMICS]
            ),
            ScientificLaw(
                law_id="metabolism",
                name="基础代谢率",
                domain=Domain.BIOLOGY,
                formula=lambda ctx: 70 * (ctx.get("body_mass", 70) ** 0.75) *
                                   (ctx.get("temperature_factor", 1.0)),
                description="BMR 与体重的 3/4 幂律",
                coupling_strength=0.8,
                affected_domains=[Domain.ECOLOGY, Domain.MEDICINE]
            ),
            ScientificLaw(
                law_id="hardy_weinberg",
                name="哈迪-温伯格平衡",
                domain=Domain.BIOLOGY,
                formula=lambda ctx: {
                    "p2": ctx.get("allele_freq_p", 0.5) ** 2,
                    "q2": ctx.get("allele_freq_q", 0.5) ** 2,
                    "2pq": 2 * ctx.get("allele_freq_p", 0.5) * ctx.get("allele_freq_q", 0.5)
                },
                description="基因频率平衡",
                coupling_strength=0.5,
                affected_domains=[Domain.ECOLOGY]
            ),
            ScientificLaw(
                law_id="allometric_scaling",
                name="异速生长律",
                domain=Domain.BIOLOGY,
                formula=lambda ctx: ctx.get("base_rate", 1) * (ctx.get("size", 1) ** ctx.get("scaling_exponent", 0.75)),
                description="规模缩放规律",
                coupling_strength=0.6,
                affected_domains=[Domain.ECOLOGY, Domain.ECONOMICS]
            ),
        ]

        # ============ ECOLOGY ============
        self.laws[Domain.ECOLOGY] = [
            ScientificLaw(
                law_id="carrying_capacity",
                name="环境容纳量",
                domain=Domain.ECOLOGY,
                formula=lambda ctx: ctx.get("resource_capacity", 1000) / (1 + ctx.get("current_population", 100)),
                description="K = R / (1 + N)",
                coupling_strength=1.0,
                affected_domains=[Domain.BIOLOGY, Domain.ECONOMICS]
            ),
            ScientificLaw(
                law_id="niche_competition",
                name="生态位竞争",
                domain=Domain.ECOLOGY,
                formula=lambda ctx: 1 - (ctx.get("niche_overlap", 0.5) * ctx.get("competition_coeff", 0.3)),
                description="竞争排斥原理",
                coupling_strength=0.8,
                affected_domains=[Domain.BIOLOGY, Domain.ECONOMICS]
            ),
            ScientificLaw(
                law_id="trophic_transfer",
                name="营养级传递",
                domain=Domain.ECOLOGY,
                formula=lambda ctx: ctx.get("primary_production", 1000) * (0.1 ** ctx.get("trophic_level", 1)),
                description="能量传递效率 ~10%",
                coupling_strength=0.7,
                affected_domains=[Domain.BIOLOGY, Domain.ECONOMICS]
            ),
            ScientificLaw(
                law_id="biodiversity_stability",
                name="生物多样性-稳定性关系",
                domain=Domain.ECOLOGY,
                formula=lambda ctx: 1 - math.exp(-ctx.get("species_richness", 10) * ctx.get("interaction_strength", 0.1)),
                description="多样性提高系统稳定性",
                coupling_strength=0.6,
                affected_domains=[Domain.ECONOMICS, Domain.PSYCHOLOGY]
            ),
            ScientificLaw(
                law_id="nutrient_cycling",
                name="养分循环",
                domain=Domain.ECOLOGY,
                formula=lambda ctx: (ctx.get("input_rate", 10) - ctx.get("output_rate", 5)) * ctx.get("retention_time", 100),
                description="养分平衡",
                coupling_strength=0.7,
                affected_domains=[Domain.CHEMISTRY, Domain.ECONOMICS]
            ),
        ]

        # ============ MEDICINE ============
        self.laws[Domain.MEDICINE] = [
            ScientificLaw(
                law_id="infection_dynamics",
                name="传染病动力学",
                domain=Domain.MEDICINE,
                formula=lambda ctx: {
                    "new_infections": ctx.get("susceptible", 900) * ctx.get("infected", 100) * ctx.get("transmission_rate", 0.0001),
                    "recoveries": ctx.get("infected", 100) * ctx.get("recovery_rate", 0.01),
                    "deaths": ctx.get("infected", 100) * ctx.get("mortality_rate", 0.001)
                },
                description="SIR 模型",
                coupling_strength=1.0,
                affected_domains=[Domain.BIOLOGY, Domain.ECONOMICS, Domain.POLITICS]
            ),
            ScientificLaw(
                law_id="dose_response",
                name="剂量-反应关系",
                domain=Domain.MEDICINE,
                formula=lambda ctx: ctx.get("exposure", 1) / (ctx.get("exposure", 1) + ctx.get("ld50", 100)),
                description="毒物剂量效应",
                coupling_strength=0.8,
                affected_domains=[Domain.CHEMISTRY, Domain.BIOLOGY]
            ),
            ScientificLaw(
                law_id="immunity_booster",
                name="免疫增强",
                domain=Domain.MEDICINE,
                formula=lambda ctx: ctx.get("baseline_immunity", 0.5) + ctx.get("exposure_history", 0) * 0.01,
                description="暴露增加免疫",
                coupling_strength=0.6,
                affected_domains=[Domain.BIOLOGY, Domain.SOCIOLOGY]
            ),
        ]

        # ============ ECONOMICS ============
        self.laws[Domain.ECONOMICS] = [
            ScientificLaw(
                law_id="supply_demand",
                name="供求均衡",
                domain=Domain.ECONOMICS,
                formula=lambda ctx: ctx.get("supply", 100) - ctx.get("demand", 100),
                description="市场出清",
                coupling_strength=1.0,
                affected_domains=[Domain.ECOLOGY, Domain.POLITICS]
            ),
            ScientificLaw(
                law_id="pareto_distribution",
                name="帕累托分布",
                domain=Domain.ECONOMICS,
                formula=lambda ctx: 1 / (ctx.get("income", 1000) ** ctx.get("alpha", 1.5)),
                description="财富分布",
                coupling_strength=0.8,
                affected_domains=[Domain.SOCIOLOGY, Domain.POLITICS]
            ),
            ScientificLaw(
                law_id="marginal_utility",
                name="边际效用递减",
                domain=Domain.ECONOMICS,
                formula=lambda ctx: ctx.get("total_utility", 100) / (1 + ctx.get("quantity", 1) * 0.1),
                description="MU 递减规律",
                coupling_strength=0.7,
                affected_domains=[Domain.PSYCHOLOGY, Domain.SOCIOLOGY]
            ),
            ScientificLaw(
                law_id="compound_interest",
                name="复利增长",
                domain=Domain.ECONOMICS,
                formula=lambda ctx: ctx.get("principal", 1000) * ((1 + ctx.get("rate", 0.05)) ** ctx.get("periods", 10)),
                description="指数增长",
                coupling_strength=0.9,
                affected_domains=[Domain.POLITICS, Domain.ETHICS]
            ),
            ScientificLaw(
                law_id="gdp_growth",
                name="GDP增长模型",
                domain=Domain.ECONOMICS,
                formula=lambda ctx: ctx.get("capital", 1000) ** 0.3 * ctx.get("labor", 100) ** 0.7,
                description="科布-道格拉斯生产函数",
                coupling_strength=0.8,
                affected_domains=[Domain.POLITICS, Domain.SOCIOLOGY]
            ),
        ]

        # ============ POLITICS ============
        self.laws[Domain.POLITICS] = [
            ScientificLaw(
                law_id="power_balance",
                name="权力均衡",
                domain=Domain.POLITICS,
                formula=lambda ctx: sum(ctx.get("power_centers", [1, 1])) / len(ctx.get("power_centers", [1])) if ctx.get("power_centers") else 1,
                description="多极权力平衡",
                coupling_strength=1.0,
                affected_domains=[Domain.MILITARY, Domain.ECONOMICS]
            ),
            ScientificLaw(
                law_id="democratic_stability",
                name="民主稳定性",
                domain=Domain.POLITICS,
                formula=lambda ctx: ctx.get("institutional_trust", 0.5) * ctx.get("economic_growth", 0.02) * ctx.get("social_cohesion", 0.7),
                description="民主质量",
                coupling_strength=0.7,
                affected_domains=[Domain.ECONOMICS, Domain.LAW]
            ),
            ScientificLaw(
                law_id="revolution_threshold",
                name="革命阈值",
                domain=Domain.POLITICS,
                formula=lambda ctx: ctx.get("grievances", 0.3) * ctx.get("mobilization", 0.2) / (ctx.get("state_capacity", 1) + 0.01),
                description="TIC 模型",
                coupling_strength=0.9,
                affected_domains=[Domain.SOCIOLOGY, Domain.ECONOMICS]
            ),
            ScientificLaw(
                law_id="alliance_formation",
                name="联盟形成",
                domain=Domain.POLITICS,
                formula=lambda ctx: ctx.get("common_interest", 0.5) * ctx.get("relative_power", 1.0) / (ctx.get("trust_distance", 1) + 0.1),
                description="联盟博弈",
                coupling_strength=0.8,
                affected_domains=[Domain.MILITARY, Domain.ECONOMICS]
            ),
        ]

        # ============ LAW ============
        self.laws[Domain.LAW] = [
            ScientificLaw(
                law_id="norm_internalization",
                name="规范内化",
                domain=Domain.LAW,
                formula=lambda ctx: ctx.get("enforcement_probability", 0.5) * ctx.get("compliance_history", 0.7),
                description="规范服从度",
                coupling_strength=0.8,
                affected_domains=[Domain.ETHICS, Domain.SOCIOLOGY]
            ),
            ScientificLaw(
                law_id="punishment_deterrence",
                name="惩罚威慑",
                domain=Domain.LAW,
                formula=lambda ctx: 1 - math.exp(-ctx.get("punishment_severity", 0.5) * ctx.get("detection_probability", 0.3)),
                description="威慑效果",
                coupling_strength=0.7,
                affected_domains=[Domain.PSYCHOLOGY, Domain.ETHICS]
            ),
            ScientificLaw(
                law_id="contract_enforcement",
                name="合同执行",
                domain=Domain.LAW,
                formula=lambda ctx: ctx.get("judicial_independence", 0.6) * ctx.get("enforcement_capacity", 0.7),
                description="法治强度",
                coupling_strength=0.9,
                affected_domains=[Domain.ECONOMICS, Domain.POLITICS]
            ),
        ]

        # ============ CULTURE ============
        self.laws[Domain.CULTURE] = [
            ScientificLaw(
                law_id="cultural_diffusion",
                name="文化扩散",
                domain=Domain.CULTURE,
                formula=lambda ctx: ctx.get("contact_rate", 0.1) * ctx.get("cultural_distance", 0.5) * ctx.get("status_differential", 0.3),
                description="文化传播模型",
                coupling_strength=0.8,
                affected_domains=[Domain.SOCIOLOGY, Domain.RELIGION]
            ),
            ScientificLaw(
                law_id="innovation_adoption",
                name="创新采纳",
                domain=Domain.CULTURE,
                formula=lambda ctx: ctx.get("relative_advantage", 0.3) / (1 + math.exp(-ctx.get("time", 10) + ctx.get("critical_mass", 50))),
                description="S型采纳曲线",
                coupling_strength=0.7,
                affected_domains=[Domain.ECONOMICS, Domain.PSYCHOLOGY]
            ),
            ScientificLaw(
                law_id="identity_formation",
                name="认同形成",
                domain=Domain.CULTURE,
                formula=lambda ctx: 1 - math.exp(-ctx.get("shared_experiences", 10) * ctx.get("common_enemies", 0)),
                description="群体认同",
                coupling_strength=0.8,
                affected_domains=[Domain.PSYCHOLOGY, Domain.POLITICS]
            ),
        ]

        # ============ ETHICS ============
        self.laws[Domain.ETHICS] = [
            ScientificLaw(
                law_id="moral_development",
                name="道德发展",
                domain=Domain.ETHICS,
                formula=lambda ctx: ctx.get("education", 0.3) + ctx.get("role_models", 0.2) + ctx.get("social_pressure", 0.1),
                description="道德推理水平",
                coupling_strength=0.7,
                affected_domains=[Domain.PSYCHOLOGY, Domain.LAW]
            ),
            ScientificLaw(
                law_id="altruism_evolution",
                name="利他主义演化",
                domain=Domain.ETHICS,
                formula=lambda ctx: ctx.get("relatedness", 0.5) * ctx.get("benefit", 10) / (ctx.get("cost", 1) + 0.1),
                description="亲缘选择",
                coupling_strength=0.6,
                affected_domains=[Domain.BIOLOGY, Domain.PSYCHOLOGY]
            ),
        ]

        # ============ MILITARY ============
        self.laws[Domain.MILITARY] = [
            ScientificLaw(
                law_id="lanchester_square",
                name="兰彻斯特平方律",
                domain=Domain.MILITARY,
                formula=lambda ctx: (ctx.get("force_alpha", 100) ** 2 - ctx.get("force_beta", 80) ** 2),
                description="战斗力损耗",
                coupling_strength=1.0,
                affected_domains=[Domain.POLITICS, Domain.ECONOMICS]
            ),
            ScientificLaw(
                law_id="technology_advantage",
                name="技术优势",
                domain=Domain.MILITARY,
                formula=lambda ctx: 1 + ctx.get("tech_level", 1) * ctx.get("training_quality", 1),
                description="技术代差",
                coupling_strength=0.8,
                affected_domains=[Domain.ECONOMICS, Domain.POLITICS]
            ),
        ]

        # ============ RELIGION ============
        self.laws[Domain.RELIGION] = [
            ScientificLaw(
                law_id="religious_conversion",
                name="宗教皈依",
                domain=Domain.RELIGION,
                formula=lambda ctx: ctx.get("social_pressure", 0.3) * ctx.get("religious_experience", 0.5) / (ctx.get("counter_pressure", 0.2) + 0.1),
                description="皈依动力学",
                coupling_strength=0.7,
                affected_domains=[Domain.CULTURE, Domain.PSYCHOLOGY]
            ),
            ScientificLaw(
                law_id="secularization",
                name="世俗化",
                domain=Domain.RELIGION,
                formula=lambda ctx: ctx.get("education_level", 0.5) * ctx.get("urbanization", 0.6),
                description="宗教衰退",
                coupling_strength=0.6,
                affected_domains=[Domain.CULTURE, Domain.POLITICS]
            ),
        ]

        # ============ PSYCHOLOGY ============
        self.laws[Domain.PSYCHOLOGY] = [
            ScientificLaw(
                law_id="prospect_theory",
                name="前景理论",
                domain=Domain.PSYCHOLOGY,
                formula=lambda ctx: ctx.get("loss", 100) * 2.25 if ctx.get("is_loss", False) else ctx.get("gain", 100),
                description="损失厌恶",
                coupling_strength=0.9,
                affected_domains=[Domain.ECONOMICS, Domain.ETHICS]
            ),
            ScientificLaw(
                law_id="cognitive_dissonance",
                name="认知失调",
                domain=Domain.PSYCHOLOGY,
                formula=lambda ctx: math.exp(-ctx.get("consonance", 0.5) * ctx.get("importance", 1)),
                description="失调强度",
                coupling_strength=0.7,
                affected_domains=[Domain.CULTURE, Domain.ETHICS]
            ),
            ScientificLaw(
                law_id="social_facilitation",
                name="社会促进",
                domain=Domain.PSYCHOLOGY,
                formula=lambda ctx: 1 + 0.3 * ctx.get("presence_of_others", 1) if ctx.get("task_complexity", 0.5) < 0.5 else 1 - 0.2 * ctx.get("presence_of_others", 1),
                description="他人在场的效应",
                coupling_strength=0.6,
                affected_domains=[Domain.ECONOMICS, Domain.SOCIOLOGY]
            ),
        ]

        # ============ SOCIOLOGY ============
        self.laws[Domain.SOCIOLOGY] = [
            ScientificLaw(
                law_id="social_network_diffusion",
                name="社会网络扩散",
                domain=Domain.SOCIOLOGY,
                formula=lambda ctx: 1 - (1 - ctx.get("adoption_rate", 0.01)) ** (ctx.get("connected_nodes", 10) * ctx.get("network_density", 0.2)),
                description="网络效应",
                coupling_strength=0.9,
                affected_domains=[Domain.CULTURE, Domain.ECONOMICS]
            ),
            ScientificLaw(
                law_id="stratification",
                name="社会分层",
                domain=Domain.SOCIOLOGY,
                formula=lambda ctx: 1 - 1 / (1 + math.exp(-ctx.get("inequality_factor", 0.5) * (ctx.get("resource_access", 0.5) - 0.5))),
                description="阶级形成",
                coupling_strength=0.8,
                affected_domains=[Domain.ECONOMICS, Domain.POLITICS]
            ),
            ScientificLaw(
                law_id="collective_behavior",
                name="集体行为",
                domain=Domain.SOCIOLOGY,
                formula=lambda ctx: ctx.get("contagion", 0.5) * ctx.get("arousal", 0.3) * ctx.get("social_trust", 0.7),
                description="集体行动涌现",
                coupling_strength=0.8,
                affected_domains=[Domain.POLITICS, Domain.MILITARY]
            ),
        ]

    def _initialize_coupling_rules(self) -> None:
        """初始化跨域耦合规则"""

        # PHYSICS → CHEMISTRY
        self.coupling_rules.append(CouplingRule(
            rule_id="temp_chem_rate",
            source_domain=Domain.PHYSICS,
            target_domain=Domain.CHEMISTRY,
            transmission_function=lambda x: x * 0.1,
            delay_ticks=1,
            decay_factor=0.9
        ))

        # PHYSICS → BIOLOGY
        self.coupling_rules.append(CouplingRule(
            rule_id="env_temp_bio",
            source_domain=Domain.PHYSICS,
            target_domain=Domain.BIOLOGY,
            transmission_function=lambda x: x * 0.05,
            delay_ticks=2,
            decay_factor=0.8
        ))

        # CHEMISTRY → BIOLOGY
        self.coupling_rules.append(CouplingRule(
            rule_id="toxin_bio",
            source_domain=Domain.CHEMISTRY,
            target_domain=Domain.BIOLOGY,
            transmission_function=lambda x: -x * 0.3,
            delay_ticks=3,
            decay_factor=0.7
        ))

        # BIOLOGY → ECOLOGY
        self.coupling_rules.append(CouplingRule(
            rule_id="pop_eco",
            source_domain=Domain.BIOLOGY,
            target_domain=Domain.ECOLOGY,
            transmission_function=lambda x: x * 0.2,
            delay_ticks=5,
            decay_factor=0.8
        ))

        # ECOLOGY → ECONOMICS
        self.coupling_rules.append(CouplingRule(
            rule_id="resource_econ",
            source_domain=Domain.ECOLOGY,
            target_domain=Domain.ECONOMICS,
            transmission_function=lambda x: x * 0.15,
            delay_ticks=10,
            decay_factor=0.85
        ))

        # ECONOMICS → POLITICS
        self.coupling_rules.append(CouplingRule(
            rule_id="wealth_pol",
            source_domain=Domain.ECONOMICS,
            target_domain=Domain.POLITICS,
            transmission_function=lambda x: x * 0.1,
            delay_ticks=15,
            decay_factor=0.8
        ))

        # MEDICINE → BIOLOGY
        self.coupling_rules.append(CouplingRule(
            rule_id="health_bio",
            source_domain=Domain.MEDICINE,
            target_domain=Domain.BIOLOGY,
            transmission_function=lambda x: x * 0.2,
            delay_ticks=5,
            decay_factor=0.9
        ))

        # MEDICINE → ECONOMICS
        self.coupling_rules.append(CouplingRule(
            rule_id="pandemic_econ",
            source_domain=Domain.MEDICINE,
            target_domain=Domain.ECONOMICS,
            transmission_function=lambda x: -x * 0.4,
            delay_ticks=10,
            decay_factor=0.7
        ))

        # POLITICS → LAW
        self.coupling_rules.append(CouplingRule(
            rule_id="policy_law",
            source_domain=Domain.POLITICS,
            target_domain=Domain.LAW,
            transmission_function=lambda x: x * 0.3,
            delay_ticks=20,
            decay_factor=0.9
        ))

        # LAW → CULTURE
        self.coupling_rules.append(CouplingRule(
            rule_id="legal_culture",
            source_domain=Domain.LAW,
            target_domain=Domain.CULTURE,
            transmission_function=lambda x: x * 0.1,
            delay_ticks=30,
            decay_factor=0.8
        ))

        # CULTURE → ETHICS
        self.coupling_rules.append(CouplingRule(
            rule_id="norm_ethics",
            source_domain=Domain.CULTURE,
            target_domain=Domain.ETHICS,
            transmission_function=lambda x: x * 0.15,
            delay_ticks=25,
            decay_factor=0.85
        ))

        # ETHICS → PSYCHOLOGY
        self.coupling_rules.append(CouplingRule(
            rule_id="moral_psych",
            source_domain=Domain.ETHICS,
            target_domain=Domain.PSYCHOLOGY,
            transmission_function=lambda x: x * 0.2,
            delay_ticks=10,
            decay_factor=0.9
        ))

        # PSYCHOLOGY → ECONOMICS
        self.coupling_rules.append(CouplingRule(
            rule_id="behavior_econ",
            source_domain=Domain.PSYCHOLOGY,
            target_domain=Domain.ECONOMICS,
            transmission_function=lambda x: x * 0.1,
            delay_ticks=15,
            decay_factor=0.8
        ))

        # SOCIOLOGY → CULTURE
        self.coupling_rules.append(CouplingRule(
            rule_id="social_culture",
            source_domain=Domain.SOCIOLOGY,
            target_domain=Domain.CULTURE,
            transmission_function=lambda x: x * 0.2,
            delay_ticks=20,
            decay_factor=0.85
        ))

        # POLITICS → MILITARY
        self.coupling_rules.append(CouplingRule(
            rule_id="pol_mil",
            source_domain=Domain.POLITICS,
            target_domain=Domain.MILITARY,
            transmission_function=lambda x: x * 0.3,
            delay_ticks=5,
            decay_factor=0.9
        ))

        # MILITARY → ECONOMICS
        self.coupling_rules.append(CouplingRule(
            rule_id="mil_econ",
            source_domain=Domain.MILITARY,
            target_domain=Domain.ECONOMICS,
            transmission_function=lambda x: -x * 0.2,
            delay_ticks=10,
            decay_factor=0.75
        ))

        # RELIGION → CULTURE
        self.coupling_rules.append(CouplingRule(
            rule_id="rel_culture",
            source_domain=Domain.RELIGION,
            target_domain=Domain.CULTURE,
            transmission_function=lambda x: x * 0.25,
            delay_ticks=30,
            decay_factor=0.8
        ))

        # ECOLOGY → MEDICINE
        self.coupling_rules.append(CouplingRule(
            rule_id="eco_med",
            source_domain=Domain.ECOLOGY,
            target_domain=Domain.MEDICINE,
            transmission_function=lambda x: x * 0.1,
            delay_ticks=15,
            decay_factor=0.85
        ))

        # Reverse: ECONOMICS → BIOLOGY (resource stress)
        self.coupling_rules.append(CouplingRule(
            rule_id="econ_bio",
            source_domain=Domain.ECONOMICS,
            target_domain=Domain.BIOLOGY,
            transmission_function=lambda x: -x * 0.05,
            delay_ticks=20,
            decay_factor=0.7
        ))

        # BIOLOGY → PSYCHOLOGY (stress effects)
        self.coupling_rules.append(CouplingRule(
            rule_id="bio_psych",
            source_domain=Domain.BIOLOGY,
            target_domain=Domain.PSYCHOLOGY,
            transmission_function=lambda x: -x * 0.1,
            delay_ticks=5,
            decay_factor=0.8
        ))

        # PSYCHOLOGY → SOCIOLOGY (emotional contagion)
        self.coupling_rules.append(CouplingRule(
            rule_id="psych_social",
            source_domain=Domain.PSYCHOLOGY,
            target_domain=Domain.SOCIOLOGY,
            transmission_function=lambda x: x * 0.15,
            delay_ticks=10,
            decay_factor=0.8
        ))

    def update_domain_state(self, domain: Domain, key: str, value: float) -> None:
        """更新域状态"""
        self.domain_states[domain].values[key] = value
        self.domain_states[domain].last_update = self.world.tick

        # 触发耦合传播
        self._propagate_coupling(domain, key, value)

    def _propagate_coupling(self, source_domain: Domain, key: str, value: float) -> None:
        """传播耦合到其他域"""
        for rule in self.coupling_rules:
            if rule.source_domain == source_domain:
                if rule.should_transmit(value):
                    target_value = rule.transmit(value)

                    # 更新目标域
                    target_state = self.domain_states[rule.target_domain]
                    target_key = f"from_{source_domain.value}_{key}"

                    # 应用延迟（简单实现）
                    if rule.delay_ticks == 0:
                        target_state.values[target_key] = target_value
                    else:
                        # 记录待处理的耦合事件
                        self.coupling_history.append({
                            "source_domain": source_domain.value,
                            "target_domain": rule.target_domain.value,
                            "key": target_key,
                            "value": target_value,
                            "apply_tick": self.world.tick + rule.delay_ticks
                        })

    def process_delayed_couplings(self) -> None:
        """处理延迟耦合"""
        still_pending = []
        for event in self.coupling_history:
            if event["apply_tick"] <= self.world.tick:
                # 应用耦合
                target_domain = Domain(event["target_domain"])
                self.domain_states[target_domain].values[event["key"]] = event["value"]
                self.domain_states[target_domain].last_update = self.world.tick
            else:
                still_pending.append(event)
        self.coupling_history = still_pending

    def evaluate_law(self, domain: Domain, law_id: str, context: dict) -> dict | None:
        """评估特定定律"""
        if domain not in self.laws:
            return None

        for law in self.laws[domain]:
            if law.law_id == law_id:
                result = law.evaluate(context)
                if result["success"]:
                    # 传播到受影响的域
                    for affected_domain in law.affected_domains:
                        self._propagate_coupling(domain, law_id, result["result"])
                return result
        return None

    def get_domain_context(self, domain: Domain) -> dict:
        """获取域上下文"""
        return self.domain_states[domain].values.copy()

    def get_cross_domain_effect(self, source: Domain, target: Domain, key: str) -> float:
        """获取跨域效应"""
        coupling_key = f"from_{source.value}_{key}"
        return self.domain_states[target].values.get(coupling_key, 0.0)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "total_domains": len(Domain),
            "active_domains": sum(1 for d in self.domain_states.values() if d.last_update >= self.world.tick - 10),
            "total_laws": sum(len(laws) for laws in self.laws.values()),
            "total_coupling_rules": len(self.coupling_rules),
            "pending_couplings": len(self.coupling_history),
            "domain_updates": {
                domain.value: len(state.values) for domain, state in self.domain_states.items()
            }
        }
