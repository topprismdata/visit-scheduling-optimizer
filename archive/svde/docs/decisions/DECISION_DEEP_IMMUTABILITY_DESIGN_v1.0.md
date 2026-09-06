# DECISION: 深度不可变 (Deep Immutability) 设计方案 v1.0

**Document ID:** TOPPRISM-DECISION-DEEP-IMMUTABILITY-DESIGN-v1_0  
**Date:** 2026-08-25  
**Status:** **INTERNAL TECHNICAL DECISION DRAFT v1.0.2 (A.1, REVISION COMPLETED)** — 待主管授权实测与冻结评审  
**上游约束:** `TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md` §17/§18 FrozenScalar/FrozenValue、§36 加载契约  
**作用域:** 不动 Canonical API；不引入 runtime 依赖；不触发 BIZ/TECH 签署

---

## 一、选型结论

**采纳方案 A（归一化）**：`deep_freeze` 接受 Mapping（含原生 `dict`）与 Tuple 输入，在构造边界统一归一化为不可变视图后写入 frozen dataclass。拒绝原始可变对象穿透边界（拒绝项见 §四）。

> 拒绝方案 B（严格拒绝 `dict`）的理由：调用方负担过重且与 `FrozenValue = Union[FrozenScalar, Tuple[FrozenValue,...], Mapping[str, FrozenValue]]` 类型注解不契合。

---

## 二、10 项设计交付

### §1 FrozenValue 递归语法

消费侧（类型注解用）：
```python
FrozenValue = Union[
    FrozenScalar,
    Tuple["FrozenValue", ...],
    Mapping[str, "FrozenValue"],
]
```

生产侧（运行时实际形态）：
```python
FrozenRuntimeValue = Union[
    str, int, float, bool, bytes, None,
    datetime, date, time, Decimal, UUID, Enum,
    Tuple["FrozenRuntimeValue", ...],          # 实际为 tuple, 非 list
    types.MappingProxyType,                    # 实际为 MappingProxyType, 非 dict
]
```

边界：`FrozenValue`（类型注解） ↔ `deep_freeze(v: Any) -> FrozenRuntimeValue`（运行时期望）。

### §2 Mapping / Tuple 输入归一化规则（双路径规范化签名）

> **与 §3 保持一致**：`_to_immutable` 全文档仅存一种双路径签名实现，下方伪代码为可执行级示例（仅展示 Mapping/Tuple 分支；其它分支见 §4/§5）。

```python
def _to_immutable(
    v: Any,
    _id_path: Tuple[int, ...] = (),
    _display_path: Tuple[str, ...] = (),
) -> FrozenRuntimeValue:
    obj_id = id(v)
    if obj_id in _id_path:
        raise CyclicValueError(f"cycle detected at path: {'.'.join(_display_path)}")
    new_id_path = _id_path + (obj_id,)

    # Mapping（含 dict / MappingProxyType / OrderedDict 等）
    if isinstance(v, Mapping):
        try:
            return MappingProxyType({
                k: _to_immutable(val, new_id_path, _display_path + (str(k),))
                for k, val in v.items()
            })
        except NonStringKeyError:
            raise  # propagate; NonStringKeyError 已在键检查处抛出

    # Tuple / list（仅 tuple 形式接收，list 也归一化以方便调用方）
    if isinstance(v, (tuple, list)):
        return tuple(
            _to_immutable(item, new_id_path, _display_path + (f"[{i}]",))
            for i, item in enumerate(v)
        )
    ...
```

要点：
- **禁止**使用单 `path` 同时承担对象身份检测与展示职责（已在 §3 明确禁止）；
- 输入侧接受 `dict`/`Mapping`/`list`/`tuple`（调用方友好）；
- 输出侧全部统一为 `MappingProxyType` / `tuple`（运行期不可变）；
- 字符串键强制规范（仅 `str`；非 `str` key 一律报 `NonStringKeyError`）。

### §3 循环检测：双路径独立（对象 ID 路径 vs 展示路径）

**关键约束**：单一路径无法同时承担"对象身份检测"与"人类可读错误消息"两个职责——字符串路径片段与对象不能用 `is` 比较。

**双路径设计（规范性）**：

```python
def _to_immutable(
    v: Any,
    _id_path: Tuple[int, ...] = (),           # 用 id(obj) 检测循环
    _display_path: Tuple[str, ...] = (),       # 仅用于错误消息与日志
) -> FrozenRuntimeValue:
    obj_id = id(v)
    if obj_id in _id_path:
        raise CyclicValueError(
            f"cycle detected at path: {'.'.join(_display_path)}"
        )
    new_id_path = _id_path + (obj_id,)
    ...
```

**职责分离保证**：
- `_id_path` 仅存 `id(obj)`（整数），与 `in` 比较兼容；不混入字符串键，避免类型错配；
- `_display_path` 仅用于错误消息，不参与循环判定；
- 不同位置的同名对象（合法重复引用）不会被误判，因为 `id()` 唯一；
- 实际成环（如 `a["self"] = a`）能可靠检测。

错误码：`CyclicValueError: DeepFreezeErrorCode.CYCLE`

### §4 数值边缘与禁止类型

| 输入 | **确定性处置** | 错误码 |
| :--- | :--- | :--- |
| `-0.0` | **拒绝**（不允许静默归一） | `NegativeZeroError` |
| `NaN` | **拒绝** | `NotFiniteNumberError` |
| `Infinity` | **拒绝** | `NotFiniteNumberError` |
| `complex` | **拒绝**（实部/虚部非 0 一并拒） | `ComplexNumberError` |
| `bytearray` | **拒绝**（不静默转 bytes，避免语义偏移） | `MutableBytesError` |
| `set` / `frozenset` | **拒绝**（迭代顺序非确定 → 指纹漂移） | `UnsupportedContainerError` |

**核心原则**：避免"或"分支——每个边界处置必须唯一确定，否则不同进程产生不同指纹。

**绝对禁止行为**：
- ❌ `set` 转 `tuple`（哈希顺序不稳定，不同进程产生不同指纹）；
- ❌ `bytearray` 静默转 `bytes`（语义偏移风险，调用方应显式 `bytes(ba)`）；
- ❌ `-0.0` 静默归一为 `0.0`（隐式转换，违反"无隐式"原则）。

错误码全集：`DeepFreezeErrorCode` 枚举（见 §7）。

### §5 datetime / date / time 时区规则

```python
if isinstance(v, datetime):
    if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
        raise NaiveDatetimeError(f"naive datetime at path {'.'.join(_display_path)}")
    return v.astimezone(timezone.utc)  # 强制归一为 UTC（确定性指纹）
if isinstance(v, time):
    # Strict aware check: tzinfo present AND can compute UTC offset
    # Note: time.utcoffset(None) uses None as "imaginary datetime" placeholder;
    # per PEP 495 a fixed-offset tzinfo must return a non-None utcoffset for any input.
    if v.tzinfo is None or v.tzinfo.utcoffset(None) is None:
        raise NaiveTimeError(
            f"naive time not allowed at API boundary: path {'.'.join(_display_path)}; "
            f"tzinfo must be present AND utcoffset() must be computable"
        )
    # 注意：time-of-day 仅有 UTC 偏移；跨日后的 UTC 换算需结合日期上下文
    # 此处仅保留 tzinfo，不做跨日换算（由业务层显式提供日期或转为完整 datetime）
    return v.replace(tzinfo=v.tzinfo)  # 规范化 tzinfo 但不换算
if isinstance(v, date):
    return v  # date 无时区概念，原样保留
```

要点：
- `datetime` 必须 TZ-aware，**强制归一为 UTC**；
- `time` 必须 TZ-aware（**naive time 拒绝**，与主 API 类型矩阵一致）；
- `date` 无时区，原样保留；
- 严禁使用 `datetime.now()` 默认值（与 TypesSpec §35.7 规范一致）；
- 严禁 naive datetime/time（破坏确定性指纹）。

### §6 MappingProxyType 默认值策略

frozen dataclass 字段默认值若是容器，须前置 freeze：

```python
# 不可：
@dataclass(frozen=True)
class WorldState:
    customers: Mapping[str, Customer] = {}              # ❌ 可变默认
    policies: Mapping[str, Policy] = MappingProxyType({})  # ⚠️ 不可变但内部值可变

# 应为：
@dataclass(frozen=True)
class WorldState:
    customers: Mapping[str, Customer] = field(default_factory=lambda: MappingProxyType({}))
    policies: Mapping[str, Policy] = field(default_factory=lambda: _to_immutable({"R1": default_policy}))
```

**规则**：所有 `Mapping` / `Tuple` 默认值必须经 `field(default_factory=lambda: deep_freeze(...))` 显式冻结。

### §7 deep_freeze 失败错误码（枚举）

```python
class DeepFreezeErrorCode(str, Enum):
    CYCLE = "CYCLE"
    NAIVE_DATETIME = "NAIVE_DATETIME"
    NAIVE_TIME = "NAIVE_TIME"
    NEGATIVE_ZERO = "NEGATIVE_ZERO"
    NOT_FINITE_NUMBER = "NOT_FINITE_NUMBER"   # NaN / Infinity
    COMPLEX_NUMBER = "COMPLEX_NUMBER"
    MUTABLE_BYTES = "MUTABLE_BYTES"           # bytearray forbidden
    UNSUPPORTED_CONTAINER = "UNSUPPORTED_CONTAINER"  # set / frozenset
    NON_STRING_KEY = "NON_STRING_KEY"
    UNRECOGNIZED_TYPE = "UNRECOGNIZED_TYPE"
```

### §8 反向解冻禁止规则

- **`deep_freeze` 是单向构造边界**：仅在输入边界归一化为不可变形态；
- **严禁提供任何反向 API**：包括 `thaw` / `unfreeze` / `make_mutable` / `_unsafe_mutate_view` / `UnfreezeWindow` / `UnfreezeContext` 等所有命名变体；违反"反向解冻禁止"将破坏单向不变性；
- **修改需求**：调用方应创建新对象，不可修改原对象；
- **本期无任何例外**：若未来性能优化需要可变窗口，应作为新的内部实验协议并标注 "INTERNAL EXPERIMENT - NOT PART OF CANONICAL API"，单独走决策流程，不在本 v1.0 合约中预留接口；
- **Linter 约束**：建议添加静态检查禁止 `setattr` / `__setitem__` 于已 deep_freeze 的对象。

### §9 逐类型测试向量表（type × edge）

| 输入类型 | 测试向量 | 期望 |
| :--- | :--- | :--- |
| `dict` | `{"a": 1}` | `MappingProxyType({"a": 1})` |
| `dict` | `{"a": {"b": 2}}` | 嵌套 `MappingProxyType` |
| `list` | `[1, 2, 3]` | `(1, 2, 3)` |
| `tuple` | `(1, [2, 3])` | `(1, (2, 3))`（内部 list 被归一） |
| 循环 | `a = {}; a["self"] = a` | `CyclicValueError`（**双路径独立**：`id(a)` 在 `_id_path` 中命中） |
| `-0.0` | `-0.0` | **`NegativeZeroError`（拒绝）** |
| `float('nan')` | `NaN` | `NotFiniteNumberError` |
| `float('inf')` | `Infinity` | `NotFiniteNumberError` |
| `complex(1, 2)` | `1+2j` | `ComplexNumberError` |
| `bytearray(b'x')` | bytearray | **`MutableBytesError`（拒绝）** |
| `set([1,2])` | set | **`UnsupportedContainerError`（拒绝）** |
| `frozenset([1,2])` | frozenset | **`UnsupportedContainerError`（拒绝）** |
| `datetime.now()` | naive | `NaiveDatetimeError` |
| `datetime.now(tz=UTC)` | aware | 归一为 UTC（`astimezone(UTC)`） |
| `time(12,0)` | naive time | **`NaiveTimeError`（拒绝，与主 API 一致）** |
| `time(12,0,tzinfo=UTC)` | aware time | 原样（保留 tzinfo） |
| `date(2026,8,25)` | date | 原样 |
| `Decimal('1.10')` | Decimal | 保留 Decimal，序列化层负责 |
| `UUID('...')` | UUID | 保留 UUID，序列化层负责 |

### §10 与 §36 加载拓扑的依赖关系

- `deep_freeze` 函数位于 `prism_ontology/contracts/immutability.py`；
- 加载顺序：模块 A（枚举）→ 模块 B（types）→ **模块 C（immutability，可选）**；
- C 仅在构造边界使用，不影响 dataclass 类创建；
- 与 §36 兼容：模块 C 可独立 import，不引入新依赖。

---

## 三、阶段状态（v1.0.1 修订后）

| 阶段 | 状态 |
| :--- | :--- |
| 选型 | ✅ 方案 A（归一化） |
| 双路径循环检测 | ✅ v1.0.1 修复（§2 与 §3 签名统一） |
| 确定性策略唯一化 | ✅ v1.0.1 修复（-0.0 / bytearray / set 全部拒绝） |
| 时间规则与主 API 一致 | ✅ v1.0.2 修复（utcoffset 严格判断 + 不换算 UTC 语义对齐） |
| UnfreezeWindow 公共契约 | ✅ v1.0.1 删除（严禁任何反向 API） |
| bytearray 跨文档拒绝统一 | ✅ v1.0.2 修复（主 API/Matrix/Checklist 同步） |
| 代码实现 | ❌ 未启动（不在本决策范围） |
| 测试向量 | ⏳ v1.0.2 已与 §4 策略对齐，20 项实现期验证 |
| 接入 §36 | ⏳ 待 Runtime 阶段 |

**修订历程**：
- v1.0 → v1.0.1：修复 P1 三项（双路径、确定性策略、时间一致性）+ P2 一项（删除 UnfreezeWindow 公共契约）
- v1.0.1 → v1.0.2：修复 P1 五项（§2 双路径签名重写、bytearray 跨文档拒绝统一、time UTC 语义对齐 A.1、awake utcoffset 严格判断统一、A.1 time utcoffset 与主 API 对齐、扫描器对 '转换 bytearray' 同义表述漏检修复）

**下一步**：本决策进入冻结评审流程，配合 A.2 RFC 8785 选型共同构成冻结前置条件。
