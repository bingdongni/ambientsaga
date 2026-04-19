"""
Institutional Emergence System — 制度深度涌现。

从微观交互中自发涌现宏观制度：
- Emergent Law（习惯法）
- Emergent Government（政府/政权）
- Emergent Religion（宗教/信仰）
- Emergent Class（阶级/阶层）
- Emergent Organization（组织）
"""

from __future__ import annotations

import random
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ambientsaga.world.state import World


class InstitutionType(Enum):
    """制度类型"""
    CUSTOM = "custom"           # 习惯/规范
    LAW = "law"                 # 法律
    GOVERNMENT = "government"    # 政府
    RELIGION = "religion"       # 宗教
    CLASS = "class"             # 阶级
    ORGANIZATION = "organization"  # 组织
    CULTURE = "culture"         # 文化
    LANGUAGE = "language"       # 语言


@dataclass
class EmergentLaw:
    """涌现的法律/习惯"""
    law_id: str
    name: str
    description: str
    violations: int = 0
    enforcements: int = 0
    compliance_rate: float = 0.0
    origin_tick: int = 0
    supporters: set[str] = field(default_factory=set)  # agent_ids
    content: dict = field(default_factory=dict)

    def calculate_legitimacy(self) -> float:
        """计算合法性"""
        if self.enforcements == 0:
            return 0.5
        return min(1.0, self.enforcements / max(1, self.violations + 1))


@dataclass
class EmergentGovernment:
    """涌现的政府"""
    government_id: str
    name: str
    government_type: str  # monarchy, democracy, theocracy, etc.

    leaders: set[str] = field(default_factory=set)  # agent_ids
    followers: set[str] = field(default_factory=set)
    authority: float = 0.5  # 权威度
    legitimacy: float = 0.5  # 合法性

    # 政策
    policies: list[dict] = field(default_factory=list)

    # 统治范围
    territory: list[tuple[int, int]] = field(default_factory=list)  # (x, y)

    # 稳定性
    stability: float = 0.5
    dissent_level: float = 0.0

    def calculate_strength(self) -> float:
        """计算政府强度"""
        return self.authority * self.legitimacy * (len(self.leaders) + len(self.followers) * 0.5)

    def process_dissent(self) -> bool:
        """处理不满，返回是否稳定"""
        self.stability = max(0.0, 1.0 - self.dissent_level)
        return self.stability > 0.3


@dataclass
class EmergentReligion:
    """涌现的宗教"""
    religion_id: str
    name: str

    # 信仰体系
    beliefs: list[str] = field(default_factory=list)
    rituals: list[str] = field(default_factory=list)
    taboos: list[str] = field(default_factory=list)

    # 成员
    followers: set[str] = field(default_factory=set)
    priests: set[str] = field(default_factory=set)

    # 强度
    orthodoxy: float = 0.5  # 正统性
    influence: float = 0.3  # 影响力

    # 共享解释
    shared_narratives: list[str] = field(default_factory=list)

    def calculate_cohesion(self) -> float:
        """计算宗教凝聚力"""
        return len(self.followers) * self.orthodoxy * self.influence / 100


@dataclass
class EmergentClass:
    """涌现的阶级"""
    class_id: str
    name: str
    class_type: str  # upper, middle, lower, untouchable, etc.

    # 成员
    members: set[str] = field(default_factory=set)

    # 资源控制
    controlled_resources: dict[str, float] = field(default_factory=dict)
    resource_share: float = 0.0  # 占总资源的比例

    # 流动性
    mobility_rate: float = 0.0  # 阶级流动性
    inter_class_marriages: int = 0

    # 阶级意识
    class_consciousness: float = 0.0
    class_solidarity: float = 0.0

    def calculate_class_power(self) -> float:
        """计算阶级力量"""
        resource_power = self.resource_share * 2
        solidarity_power = self.class_solidarity * len(self.members) / 100
        return resource_power + solidarity_power


@dataclass
class EmergentOrganization:
    """涌现的组织"""
    org_id: str
    name: str
    org_type: str  # guild, union, club, secret society, etc.

    # 成员
    founders: set[str] = field(default_factory=set)
    members: set[str] = field(default_factory=set)
    leadership: set[str] = field(default_factory=set)

    # 资源
    treasury: float = 0.0
    assets: dict[str, float] = field(default_factory=dict)

    # 目标
    goals: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)

    # 规则
    rules: list[str] = field(default_factory=list)
    membership_requirements: dict = field(default_factory=dict)

    # 声望
    reputation: float = 0.5
    age: int = 0


@dataclass
class EmergentCulture:
    """涌现的文化"""
    culture_id: str
    name: str
    origin_tick: int = 0

    # 价值观
    values: list[str] = field(default_factory=list)
    norms: list[str] = field(default_factory=list)
    taboos: list[str] = field(default_factory=list)

    # 符号
    symbols: list[str] = field(default_factory=list)
    stories: list[str] = field(default_factory=list)

    # 语言元素
    shared_vocabulary: dict[str, str] = field(default_factory=dict)  # word -> meaning

    # 载体
    carriers: set[str] = field(default_factory=set)


@dataclass
class InstitutionalEmergenceEngine:
    """
    制度涌现引擎。

    核心机制：
    1. 习惯法：从反复出现的违约模式中涌现
    2. 政府：从权威积累和追随者网络中涌现
    3. 宗教：从共享解释和仪式中涌现
    4. 阶级：从资源差异和群体认同中涌现
    5. 组织：从共同目标和协作中涌现
    6. 文化：从共享价值观和符号中涌现
    """

    def __init__(self, world: World):
        self.world = world

        # 所有涌现的制度
        self.emergent_laws: dict[str, EmergentLaw] = {}
        self.emergent_governments: dict[str, EmergentGovernment] = {}
        self.emergent_religions: dict[str, EmergentReligion] = {}
        self.emergent_classes: dict[str, EmergentClass] = {}
        self.emergent_organizations: dict[str, EmergentOrganization] = {}
        self.emergent_cultures: dict[str, EmergentCulture] = {}

        # 行为历史（用于模式识别）
        self.behavior_history: list[dict] = []
        self.violation_patterns: dict[str, int] = defaultdict(int)
        self.cooperation_patterns: dict[str, int] = defaultdict(int)

        # 权威积累
        self.authority_accumulation: dict[str, float] = defaultdict(float)

        # 资源分配历史
        self.resource_history: list[dict] = []

        # 统计
        self.tick_count = 0

    # ==================== 习惯法涌现 ====================

    def detect_legal_norm(self, tick: int) -> EmergentLaw | None:
        """从行为模式中检测习惯法"""
        if len(self.behavior_history) < 50:
            return None

        # 分析最近的违规模式
        recent_violations = [e for e in self.behavior_history[-50:] if e.get("is_violation")]

        if len(recent_violations) < 5:
            return None

        # 检测反复出现的违规类型
        violation_types = Counter(e.get("violation_type") for e in recent_violations)

        for violation_type, count in violation_types.items():
            if count >= 3:  # 至少出现3次
                law_name = f"Prohibition_of_{violation_type}"

                # 检查是否已存在
                existing = [l for l in self.emergent_laws.values() if law_name in l.name]
                if existing:
                    return None

                law = EmergentLaw(
                    law_id=str(uuid.uuid4()),
                    name=law_name,
                    description=f"Social prohibition against {violation_type} behavior",
                    violations=count,
                    origin_tick=tick
                )

                self.emergent_laws[law.law_id] = law
                return law

        return None

    def record_violation(self, agent_id: str, violation_type: str, tick: int) -> None:
        """记录违规行为"""
        self.behavior_history.append({
            "agent_id": agent_id,
            "violation_type": violation_type,
            "is_violation": True,
            "tick": tick
        })

        self.violation_patterns[violation_type] += 1

        # 更新相关法律
        for law in self.emergent_laws.values():
            if violation_type in law.name:
                law.violations += 1

    def record_enforcement(self, agent_id: str, law_id: str, tick: int) -> None:
        """记录执法行为"""
        if law_id in self.emergent_laws:
            self.emergent_laws[law_id].enforcements += 1
            self.emergent_laws[law_id].supporters.add(agent_id)

    def check_compliance(self, agent_id: str, action_type: str) -> bool:
        """检查是否合规"""
        for law in self.emergent_laws.values():
            if action_type in law.name:
                return random.random() < law.compliance_rate
        return True

    # ==================== 政府涌现 ====================

    def detect_government_emergence(self, tick: int) -> EmergentGovernment | None:
        """检测政府涌现"""
        # 查找权威积累最多的agent
        if not self.authority_accumulation:
            return None

        sorted_agents = sorted(
            self.authority_accumulation.items(),
            key=lambda x: x[1],
            reverse=True
        )

        if len(sorted_agents) < 3:
            return None

        # 找到权威远超他人的agent
        top_agent, top_authority = sorted_agents[0]
        if len(sorted_agents) > 1:
            second_authority = sorted_agents[1][1]
        else:
            second_authority = 0

        # 如果最高权威者比第二名高出50%以上，可能形成政府
        if top_authority > second_authority * 1.5 and top_authority > 50:

            # 检查是否已有政府
            existing = [g for g in self.emergent_governments.values()
                       if top_agent in g.leaders]
            if existing:
                return None

            government = EmergentGovernment(
                government_id=str(uuid.uuid4()),
                name=f"Government_of_{top_agent[:8]}",
                government_type="emergent_monarchy" if top_authority > 100 else "emergent_leadership",
                leaders={top_agent},
                authority=min(1.0, top_authority / 200),
                origin_tick=tick
            )

            self.emergent_governments[government.government_id] = government
            return government

        return None

    def accumulate_authority(self, agent_id: str, amount: float) -> None:
        """积累权威"""
        self.authority_accumulation[agent_id] += amount

    def add_follower(self, government_id: str, agent_id: str) -> None:
        """添加追随者"""
        if government_id in self.emergent_governments:
            gov = self.emergent_governments[government_id]
            if agent_id not in gov.leaders:
                gov.followers.add(agent_id)

                # 增加政府权威
                gov.authority = min(1.0, gov.authority + 0.01)

    def form_alliance(self, agent1_id: str, agent2_id: str) -> str | None:
        """形成联盟（可能导致新政府）"""
        # 检查是否应该形成新政府
        alliance_strength = 0

        if agent1_id in self.authority_accumulation:
            alliance_strength += self.authority_accumulation[agent1_id]
        if agent2_id in self.authority_accumulation:
            alliance_strength += self.authority_accumulation[agent2_id]

        if alliance_strength > 80:
            government = EmergentGovernment(
                government_id=str(uuid.uuid4()),
                name=f"Alliance_{agent1_id[:6]}_{agent2_id[:6]}",
                government_type="emergent_council",
                leaders={agent1_id, agent2_id},
                authority=alliance_strength / 200,
                origin_tick=self.world.tick
            )
            self.emergent_governments[government.government_id] = government
            return government.government_id

        return None

    # ==================== 宗教涌现 ====================

    def detect_religion_emergence(self, tick: int) -> EmergentReligion | None:
        """检测宗教涌现"""
        # 查找共享解释最多的模式
        if len(self.behavior_history) < 100:
            return None

        recent_interactions = self.behavior_history[-100:]

        # 查找有共同反应的agent群体
        agent_responses = defaultdict(list)
        for event in recent_interactions:
            if event.get("response"):
                agent_responses[event.get("agent_id", "")].append(event["response"])

        # 找最常见的响应模式
        all_responses = []
        for responses in agent_responses.values():
            all_responses.extend(responses)

        if len(all_responses) < 10:
            return None

        response_counts = Counter(all_responses)
        most_common = response_counts.most_common(3)

        if most_common[0][1] >= 5:  # 至少5人有相同反应
            religion = EmergentReligion(
                religion_id=str(uuid.uuid4()),
                name=f"Faith_of_{most_common[0][0]}",
                beliefs=[f"Belief in {most_common[0][0]}"],
                rituals=[f"Ritual practice of {most_common[0][0]}"],
                origin_tick=tick
            )
            self.emergent_religions[religion.religion_id] = religion
            return religion

        return None

    def add_follower_to_religion(self, religion_id: str, agent_id: str) -> None:
        """添加信徒"""
        if religion_id in self.emergent_religions:
            religion = self.emergent_religions[religion_id]
            religion.followers.add(agent_id)

            # 增加影响力
            religion.influence = min(1.0, len(religion.followers) / 100)

    def add_shared_narrative(self, religion_id: str, narrative: str) -> None:
        """添加共享叙事"""
        if religion_id in self.emergent_religions:
            self.emergent_religions[religion_id].shared_narratives.append(narrative)
            self.emergent_religions[religion_id].orthodoxy = min(1.0,
                self.emergent_religions[religion_id].orthodoxy + 0.01)

    # ==================== 阶级涌现 ====================

    def detect_class_formation(self, tick: int) -> EmergentClass | None:
        """检测阶级形成"""
        if len(self.resource_history) < 20:
            return None

        # 分析资源分配
        recent = self.resource_history[-20:]

        # 找出资源最多的群体
        top_agents = set()
        bottom_agents = set()

        agent_resources = defaultdict(list)
        for record in recent:
            for agent_id, amount in record.get("allocations", {}).items():
                agent_resources[agent_id].append(amount)

        avg_resources = {aid: sum(amounts)/len(amounts) for aid, amounts in agent_resources.items()}

        if len(avg_resources) < 10:
            return None

        sorted_agents = sorted(avg_resources.items(), key=lambda x: x[1], reverse=True)

        # 最高10%
        top_n = max(1, len(sorted_agents) // 10)
        for agent_id, _ in sorted_agents[:top_n]:
            top_agents.add(agent_id)

        # 最低10%
        for agent_id, _ in sorted_agents[-top_n:]:
            bottom_agents.add(agent_id)

        # 如果差距足够大
        if sorted_agents:
            top_avg = sum(r for _, r in sorted_agents[:top_n]) / top_n
            bottom_avg = sum(r for _, r in sorted_agents[-top_n:]) / top_n
            inequality_ratio = top_avg / max(0.01, bottom_avg)

            if inequality_ratio > 3.0:  # 差距超过3倍
                upper_class = EmergentClass(
                    class_id=str(uuid.uuid4()),
                    name="Emergent_Upper_Class",
                    class_type="upper",
                    members=top_agents,
                    resource_share=top_avg / (top_avg + bottom_avg),
                    origin_tick=tick
                )

                lower_class = EmergentClass(
                    class_id=str(uuid.uuid4()),
                    name="Emergent_Lower_Class",
                    class_type="lower",
                    members=bottom_agents,
                    resource_share=bottom_avg / (top_avg + bottom_avg),
                    origin_tick=tick
                )

                self.emergent_classes[upper_class.class_id] = upper_class
                self.emergent_classes[lower_class.class_id] = lower_class

                return upper_class

        return None

    def record_resource_allocation(self, allocations: dict[str, float], tick: int) -> None:
        """记录资源分配"""
        self.resource_history.append({
            "tick": tick,
            "allocations": allocations.copy()
        })

    def calculate_class_consciousness(self, class_id: str) -> None:
        """计算阶级意识"""
        if class_id not in self.emergent_classes:
            return

        cls = self.emergent_classes[class_id]

        # 阶级意识 = 同类成员互动频率 / 与其他阶级互动频率
        in_class_interactions = 0
        cross_class_interactions = 0

        for event in self.behavior_history[-50:]:
            agent = event.get("agent_id")
            other = event.get("other_id")

            if agent in cls.members:
                if other in cls.members:
                    in_class_interactions += 1
                elif other:
                    cross_class_interactions += 1

        if cross_class_interactions > 0:
            cls.class_consciousness = min(1.0,
                in_class_interactions / (in_class_interactions + cross_class_interactions))

    # ==================== 组织涌现 ====================

    def detect_organization_formation(self, tick: int) -> EmergentOrganization | None:
        """检测组织形成"""
        # 查找频繁协作的agent群体
        if len(self.behavior_history) < 30:
            return None

        # 分析协作模式
        agent_pairs = Counter()
        for event in self.behavior_history[-50:]:
            if event.get("is_cooperation"):
                a1 = event.get("agent_id", "")
                a2 = event.get("other_id", "")
                if a1 and a2:
                    pair = tuple(sorted([a1, a2]))
                    agent_pairs[pair] += 1

        # 找最稳定的合作关系
        stable_pairs = [(pair, count) for pair, count in agent_pairs.items() if count >= 3]

        if len(stable_pairs) >= 3:
            # 提取成员
            members = set()
            for pair, _ in stable_pairs:
                members.add(pair[0])
                members.add(pair[1])

            if len(members) >= 3:
                org = EmergentOrganization(
                    org_id=str(uuid.uuid4()),
                    name=f"Emergent_Organization_{tick}",
                    org_type="emergent_guild",
                    founders=members,
                    members=members.copy(),
                    origin_tick=tick
                )

                self.emergent_organizations[org.org_id] = org
                return org

        return None

    def grow_organization(self, org_id: str, new_member: str) -> None:
        """组织增长"""
        if org_id in self.emergent_organizations:
            org = self.emergent_organizations[org_id]
            org.members.add(new_member)
            org.reputation = min(1.0, org.reputation + 0.01)

    # ==================== 文化涌现 ====================

    def detect_culture_emergence(self, tick: int) -> EmergentCulture | None:
        """检测文化涌现"""
        if len(self.behavior_history) < 50:
            return None

        # 查找共同行为模式
        agent_behaviors = defaultdict(lambda: defaultdict(int))

        for event in self.behavior_history[-50:]:
            agent = event.get("agent_id", "")
            behavior = event.get("behavior_type", "unknown")
            agent_behaviors[agent][behavior] += 1

        # 找共同行为
        if len(agent_behaviors) < 5:
            return None

        # 跨agent统计
        behavior_counts = Counter()
        for behaviors in agent_behaviors.values():
            for behavior in behaviors:
                behavior_counts[behavior] += 1

        # 至少3个agent都有的行为
        shared_behaviors = [b for b, count in behavior_counts.items()
                          if count >= 3]

        if shared_behaviors:
            culture = EmergentCulture(
                culture_id=str(uuid.uuid4()),
                name=f"Culture_{shared_behaviors[0]}",
                values=[f"Value of {shared_behaviors[0]}"],
                norms=[f"Norm: {shared_behaviors[0]}"],
                origin_tick=tick
            )

            self.emergent_cultures[culture.culture_id] = culture
            return culture

        return None

    def spread_culture(self, culture_id: str, new_carrier: str) -> None:
        """文化传播"""
        if culture_id in self.emergent_cultures:
            self.emergent_cultures[culture_id].carriers.add(new_carrier)

    # ==================== 危机响应 ====================

    def record_crisis_event(
        self,
        event_type: str,
        severity: float,
        tick: int,
        casualties: int = 0,
    ) -> None:
        """
        记录危机事件，用于触发制度涌现。

        危机事件（如瘟疫、饥荒、自然灾害）可以触发制度的形成，
        如医疗制度、福利制度、紧急政府等。
        """
        crisis_record = {
            "type": event_type,
            "severity": severity,
            "tick": tick,
            "casualties": casualties,
        }
        self.behavior_history.append(crisis_record)

        # 严重危机可以立即触发某些制度的形成
        if severity >= 3.0:
            self._check_crisis_institution_formation(event_type, severity, tick, casualties)

    def _check_crisis_institution_formation(
        self,
        event_type: str,
        severity: float,
        tick: int,
        casualties: int,
    ) -> None:
        """检查危机是否触发新制度形成"""
        agents = self.world.get_all_agents()
        alive_agents = [a for a in agents if a.is_alive]

        if len(alive_agents) < 5:
            return

        # 根据危机类型检查是否形成相应制度
        if event_type == "plague" and severity >= 2.0:
            # 瘟疫可能触发医疗/卫生制度
            self._check_medical_institution(tick, alive_agents)

        elif event_type == "famine" and severity >= 2.0:
            # 饥荒可能触发福利/救助制度
            self._check_welfare_institution(tick, alive_agents)

        elif event_type == "conflict" and severity >= 2.0:
            # 冲突可能触发政府/法律制度
            self._check_government_emergence(tick)

    def _check_medical_institution(self, tick: int, agents: list) -> None:
        """检查是否形成医疗制度"""
        # 检查是否已有医疗制度
        for org in self.emergent_organizations.values():
            if "medical" in org.name.lower() or "health" in org.name.lower():
                return

        # 查找有医疗知识的agent (通过技能或职业)
        healers = []
        for agent in agents:
            skills = getattr(agent, 'skills', {})
            if 'healing' in skills or 'medicine' in skills:
                healers.append(agent)

        if len(healers) >= 2:
            # 形成医疗组织
            org = EmergentOrganization(
                org_id=str(uuid.uuid4()),
                name="Emergency Medical Corps",
                org_type="medical",
                founding_members={a.entity_id for a in healers[:5]},
                purpose="Provide medical assistance during crises",
            )
            self.emergent_organizations[org.org_id] = org

    def _check_welfare_institution(self, tick: int, agents: list) -> None:
        """检查是否形成福利制度"""
        # 检查是否已有福利制度
        for org in self.emergent_organizations.values():
            if "welfare" in org.name.lower() or "relief" in org.name.lower():
                return

        # 检查是否有资源的agent愿意分享
        generous_agents = [a for a in agents if getattr(a, 'wealth', 100) > 150]

        if len(generous_agents) >= 3:
            # 形成福利组织
            org = EmergentOrganization(
                org_id=str(uuid.uuid4()),
                name="Relief and Welfare Association",
                org_type="welfare",
                founding_members={a.entity_id for a in generous_agents[:5]},
                purpose="Provide assistance during famines and crises",
            )
            self.emergent_organizations[org.org_id] = org

    # ==================== 主循环 ====================

    def update(self, tick: int) -> None:
        """更新制度涌现系统"""
        self.tick_count = tick

        # 定期检测新制度
        detection_interval = 50

        if tick % detection_interval == 0:
            # 检测法律
            self.detect_legal_norm(tick)

            # 检测政府
            self.detect_government_emergence(tick)

            # 检测宗教
            self.detect_religion_emergence(tick)

            # 检测阶级
            self.detect_class_formation(tick)

            # 检测组织
            self.detect_organization_formation(tick)

            # 检测文化
            self.detect_culture_emergence(tick)

        # 更新现有制度的稳定性
        self._update_institution_stability()

        # 限制历史长度
        if len(self.behavior_history) > 1000:
            self.behavior_history = self.behavior_history[-500:]
        if len(self.resource_history) > 500:
            self.resource_history = self.resource_history[-250:]

    def _update_institution_stability(self) -> None:
        """更新制度稳定性"""

        # 政府稳定性
        for gov in self.emergent_governments.values():
            if self.tick_count - gov.origin_tick > 100:
                # 随时间增加权威消耗
                gov.authority *= 0.999
                gov.stability = gov.authority * gov.legitimacy

        # 宗教凝聚力
        for religion in self.emergent_religions.values():
            if religion.followers:
                religion.orthodoxy = min(1.0,
                    len(religion.priests) / len(religion.followers) * 2)

        # 阶级意识
        for cls in self.emergent_classes.values():
            self.calculate_class_consciousness(cls.class_id)

    def record_behavior(self, agent_id: str, behavior: str, response: str = "",
                       is_violation: bool = False, other_id: str = "",
                       is_cooperation: bool = False) -> None:
        """记录行为（供模式识别使用）"""
        self.behavior_history.append({
            "agent_id": agent_id,
            "behavior_type": behavior,
            "response": response,
            "is_violation": is_violation,
            "other_id": other_id,
            "is_cooperation": is_cooperation,
            "tick": self.world.tick
        })

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "total_institutions": (
                len(self.emergent_laws) +
                len(self.emergent_governments) +
                len(self.emergent_religions) +
                len(self.emergent_classes) +
                len(self.emergent_organizations) +
                len(self.emergent_cultures)
            ),
            "emergent_laws": len(self.emergent_laws),
            "emergent_governments": len(self.emergent_governments),
            "emergent_religions": len(self.emergent_religions),
            "emergent_classes": len(self.emergent_classes),
            "emergent_organizations": len(self.emergent_organizations),
            "emergent_cultures": len(self.emergent_cultures),
            "behavior_history_length": len(self.behavior_history),
            "top_authorities": sorted(
                self.authority_accumulation.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "violation_patterns": dict(
                sorted(self.violation_patterns.items(),
                      key=lambda x: x[1], reverse=True)[:5]
            ),
        }

    def get_all_institutions(self) -> list[dict]:
        """获取所有制度"""
        institutions = []

        for law in self.emergent_laws.values():
            institutions.append({
                "type": "law",
                "id": law.law_id,
                "name": law.name,
                "legitimacy": law.calculate_legitimacy(),
            })

        for gov in self.emergent_governments.values():
            institutions.append({
                "type": "government",
                "id": gov.government_id,
                "name": gov.name,
                "strength": gov.calculate_strength(),
                "leaders": len(gov.leaders),
                "followers": len(gov.followers),
            })

        for religion in self.emergent_religions.values():
            institutions.append({
                "type": "religion",
                "id": religion.religion_id,
                "name": religion.name,
                "followers": len(religion.followers),
                "cohesion": religion.calculate_cohesion(),
            })

        for cls in self.emergent_classes.values():
            institutions.append({
                "type": "class",
                "id": cls.class_id,
                "name": cls.name,
                "members": len(cls.members),
                "power": cls.calculate_class_power(),
            })

        for org in self.emergent_organizations.values():
            institutions.append({
                "type": "organization",
                "id": org.org_id,
                "name": org.name,
                "members": len(org.members),
                "reputation": org.reputation,
            })

        for culture in self.emergent_cultures.values():
            institutions.append({
                "type": "culture",
                "id": culture.culture_id,
                "name": culture.name,
                "carriers": len(culture.carriers),
            })

        return institutions
