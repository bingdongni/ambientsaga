# AmbientSaga 全域自演化与自进化系统 - 核心重构计划

## 问题诊断

### 当前系统的五大核心缺陷

1. **模块缺乏真实耦合**
   - 各领域模块独立运行，未形成因果传导链
   - 地震仅触发灾害，不影响经济体系
   - 瘟疫仅影响人口，不触发社会规范演化

2. **伪涌现问题**
   - 协议/制度/市场依赖预设信号
   - 宏观结构非真实博弈结果
   - 演化过程规整、缺乏意外性

3. **科学定律为空壳**
   - 仅存在公式字符串
   - 未嵌入世界运行过程
   - 未真正驱动智能体决策

4. **智能体过于理性**
   - 缺乏情绪波动
   - 无认知偏差
   - 无非理性行为

5. **演化路径单一**
   - 缺乏蝴蝶效应
   - 无历史分叉性
   - 多次模拟结果趋同

---

## 重构目标

**彻底摒弃「功能拼装」与「预设规则驱动」模式，转向真实复杂系统的原生自演化内核。**

---

## 核心架构重构

### 1. 统一因果引擎 (UnifiedCausalEngine)

```
所有领域规则通过统一因果引擎耦合：

物理系统 → 化学反应速率 → 生物代谢 → 生态平衡
    ↓              ↓            ↓         ↓
地形侵蚀    材料强度变化    迁徙行为    资源分布
    ↓              ↓            ↓         ↓
经济系统 ←→ 社会动态 ←→ 政治演化 ←→ 文化变迁
    ↑              ↑            ↑         ↑
    └─────────── 反馈回路 ───────────┘
```

### 2. 真实涌现层 (TrueEmergenceLayer)

替代现有 Protocol 系统：

```python
class TrueEmergenceLayer:
    """
    真实涌现引擎 - 从微观交互中自发产生宏观结构
    """

    def process_interaction(self, agent_a, agent_b, interaction):
        """
        处理智能体交互，产生真实涌现效应
        """
        # 1. 记录原始交互
        trace = self.create_trace(agent_a, agent_b, interaction)

        # 2. 提取模式（不是预设信号）
        pattern = self.extract_pattern(trace)

        # 3. 检测涌现
        if self.is_emerging(pattern):
            self.create_institution(pattern)

        # 4. 传播效应
        self.propagate_effects(trace)

    def extract_pattern(self, trace):
        """从交互中提取真实模式，而非预设信号"""
        # 分析行为序列
        # 检测重复模式
        # 识别规范雏形
        # 返回动态信号（而非预设枚举）
```

### 3. 功能科学引擎 (FunctionalScienceEngine)

替代当前空壳科学系统：

```python
class FunctionalScienceEngine:
    """
    功能化科学引擎 - 完整可计算逻辑驱动世界
    """

    def __init__(self):
        self.physics = FunctionalPhysics()
        self.chemistry = FunctionalChemistry()
        self.biology = FunctionalBiology()
        self.ecology = FunctionalEcology()

    def update_world(self, world, tick):
        """
        每tick执行科学计算，驱动世界状态
        """
        # 物理约束
        self.physics.apply_laws(world, tick)

        # 化学反应
        self.chemistry.process_reactions(world, tick)

        # 生物代谢
        self.biology.update_organisms(world, tick)

        # 生态平衡
        self.ecology.balance_species(world, tick)

        # 跨域耦合 - 关键！
        self.cross_domain_coupling(world, tick)

    def cross_domain_coupling(self, world, tick):
        """
        跨域动态耦合 - 形成真实因果链
        """
        # 温度影响化学反应速率
        temp = world.get_average_temperature()
        chem_rate = self.chemistry.calculate_rate(temp)
        world._reaction_rate = chem_rate

        # 生态压力影响经济
        resource_scarcity = self.ecology.calculate_scarcity(world)
        price_level = world.economy.adjust_prices(resource_scarcity)

        # 经济波动触发社会反应
        if price_level > 1.5:
            world.social.add_unrest(price_level * 0.1)

        # 社会动荡影响政治
        if world.social.unrest > 0.5:
            world.politics.update_stability(-0.05)

        # 政治稳定影响文化传播
        if world.politics.stability > 0.8:
            world.culture.accelerate_exchange()
```

### 4. 真实人类智能体 (HumanLikeAgent)

替代过于理性的Agent：

```python
class HumanLikeAgent:
    """
    真实人类智能体 - 具备非理性特质
    """

    def __init__(self, agent_id, personality):
        # 心理特质（随机生成）
        self.confirmation_bias = random.uniform(0.3, 0.9)
        self.loss_aversion = random.uniform(1.5, 3.0)
        self.herding_tendency = random.uniform(0.2, 0.8)
        self.empathy = random.uniform(0.1, 0.9)
        self.risk_seeking = random.uniform(0.1, 0.9)

        # 情绪状态
        self.emotions = {
            'anger': 0.0,
            'fear': 0.0,
            'joy': 0.0,
            'sadness': 0.0,
            'trust': 0.5,
            'disgust': 0.0,
        }

        # 认知状态
        self.irrational_factors = {
            'availability_bias': {},
            'anchoring_effect': {},
            'overconfidence': random.uniform(0.8, 1.5),
        }

    def make_decision(self, perception, world):
        """
        真实人类决策过程 - 融合理性与非理性
        """
        # 1. 理性分析（受限）
        rational_eval = self.rational_analysis(perception)

        # 2. 情绪影响
        emotional_factor = self.calculate_emotional_factor()

        # 3. 认知偏差注入
        biased_eval = self.apply_cognitive_biases(rational_eval)

        # 4. 从众效应
        herd_influence = self.calculate_herd_behavior(world)

        # 5. 随机性（真实人类不可预测）
        randomness = random.uniform(-0.1, 0.1)

        # 最终决策
        decision = (biased_eval * 0.4 +
                   emotional_factor * 0.2 +
                   herd_influence * 0.2 +
                   randomness * 0.2)

        # 更新情绪状态
        self.update_emotions(perception, decision)

        return decision

    def apply_cognitive_biases(self, rational_eval):
        """
        应用认知偏差 - 导致非理性决策
        """
        # 确认偏差：偏好支持已有信念的信息
        if self.irrational_factors['overconfidence'] > 1.0:
            rational_eval *= 1.2  # 高估自己

        # 损失厌恶：损失比收益影响更大
        # （已在参数中体现）

        # 可得性启发：近期事件权重过大
        recent_weight = self.get_recent_event_weight()
        rational_eval *= (1 + recent_weight * 0.1)

        return rational_eval
```

### 5. 历史蝴蝶效应系统 (HistoricalButterflySystem)

```python
class HistoricalButterflySystem:
    """
    历史蝴蝶效应系统 - 确保每次模拟独特
    """

    def __init__(self):
        self.event_chains = []
        self.bifurcation_points = []
        self.historical_memories = {}

    def record_event(self, event, world, tick):
        """记录事件并检测蝴蝶效应"""
        self.event_chains.append({
            'event': event,
            'tick': tick,
            'state': world.get_snapshot()
        })

        # 检测是否为分叉点
        if self.is_bifurcation_point(event):
            self.bifurcation_points.append(tick)

    def is_bifurcation_point(self, event):
        """
        检测事件是否导致历史分叉
        关键：使用真实混沌条件
        """
        # 事件影响力
        impact = event.get('impact', 0)

        # 临界系统条件
        system_state = event.get('system_state', {})

        # 真实蝴蝶效应：微小扰动可能产生巨大影响
        # 或巨大事件可能无关紧要
        chaos_factor = random.uniform(0.0, 2.0)

        return impact * chaos_factor > 0.7

    def get_branch_result(self, initial_condition):
        """根据初始条件返回独特的历史分支"""
        # 引入随机种子变化
        seed_variation = hash(str(initial_condition)) % 1000
        return seed_variation
```

---

## 具体实现计划

### Phase 1: 核心引擎重构 (2-3天)

1. **创建 UnifiedCausalEngine**
   - 实现领域间真实耦合
   - 因果传导链定义

2. **重构 FunctionalScienceEngine**
   - 实现完整可计算定律
   - 物理/化学/生物/生态真实联动

### Phase 2: 智能体系统升级 (2-3天)

1. **创建 HumanLikeAgent**
   - 认知偏差系统
   - 情绪模型
   - 非理性决策

2. **升级 TrueEmergenceLayer**
   - 移除预设信号
   - 开放行为空间

### Phase 3: 历史与涌现系统 (2-3天)

1. **创建 HistoricalButterflySystem**
   - 分叉点检测
   - 多历史轨迹

2. **强化涌现检测**
   - 真实制度涌现
   - 市场涌现
   - 文化涌现

### Phase 4: 可视化与性能 (1-2天)

1. **增强可视化**
   - 3D地形渲染
   - 实时热力图
   - 历史轨迹回放

2. **性能优化**
   - Numba加速关键计算
   - 内存池优化
   - 并行处理

---

## 验证标准

1. **真实耦合验证**：地震触发经济崩溃，经济崩溃触发政治动荡
2. **真实涌现验证**：无预设信号下出现交易行为
3. **科学真实性验证**：温度变化影响化学反应速率
4. **人类行为验证**：智能体出现非理性行为
5. **历史独特性验证**：相同参数产生不同结果

---

## 预期成果

最终系统将成为：
- **无预设**：所有结构从交互中涌现
- **高真实**：完整科学逻辑驱动
- **多结果**：蝴蝶效应确保独特性
- **强耦合**：全域因果传导
- **全学科**：自然科学+社会科学深度融合
