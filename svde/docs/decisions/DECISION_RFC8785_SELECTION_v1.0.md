# DECISION: RFC 8785 (JCS) Python 库选型研究 v1.0

**Document ID:** TOPPRISM-DECISION-RFC8785-SELECTION-v1_0  
**Date:** 2026-08-25  
**Status:** **INTERNAL TECHNICAL DECISION DRAFT v1.0.2 (A.2, PRACTICAL TEST PENDING)** — 待主管授权实测验证后进入冻结评审  
**上游约束:** `TOPPRISM_L3_DYNAMICS_TRANSITION_ENGINE_DETAILED_SPEC_v1_0.md` §3.2（审计哈希 = SHA256(RFC8785_Canonical_JSON(...)))  
**作用域:** 不引入未审依赖；不触 BIZ/TECH 签署；纯技术选型与评估

---

## 一、关键事实纠正（避免历史错误混淆）

### 错误候选澄清
- ❌ **pyca/cryptography**：定位为密码学原语（OpenSSL 绑定），**不提供** RFC 8785 JCS；
- ❌ "50 行自实现"：低估了 IEEE 754 数值序列化、浮点边界与跨语言一致性的真实复杂度，**不推荐**作为完整方案。

### 候选重新定义
| 候选 | 形态 | 已知性质 | 待核 |
| :--- | :--- | :--- | :--- |
| **C1** | 独立 `rfc8785` PyPI 包 | 纯 Python 实现，无传递依赖，输出 UTF-8 `bytes` | 维护活跃度、Python 3.9+ 支持、RFC 8785 测试向量覆盖率 |
| **C2** | 其他经审计 JCS 实现 | （按项目标准筛选：源代码可读、Apache-2.0 / MIT / BSD、有测试向量） | 候选列表在 §三 给出 |
| **C3** | 自实现适配层（**非 RFC 8785 合规**） | 仅做我们必要的子集（与 A.1 归一化层配合） | **仅供开发期实验**；严禁用于生产/审计指纹路径 |

---

## 二、关键架构：业务值归一化层与 JCS 库分离

```
┌─────────────────────────────────────┐
│  业务值归一化层（我们的代码，A.1）   │
│  datetime / Decimal / bytes / UUID / Enum   │
│              ↓                      │
│  JSON-safe FrozenValue              │
└──────────────┬──────────────────────┘
               ↓
┌──────────────┴──────────────────────┐
│  RFC 8785 JCS 库（外部 C1 / C2）     │  ← 仅 RFC 8785 合规实现
│  JSON Canonicalization  ONLY         │
│              ↓                      │
│  UTF-8 bytes                        │
└──────────────┬──────────────────────┘
               ↓
            SHA-256

┌─────────────────────────────────────┐
│  C3：开发期非合规实验适配器          │  ← 已从生产路径剔除
│  （不实现完整 RFC 8785，仅开发用）   │
└─────────────────────────────────────┘
```

**核心约束**：JCS 库**不能替代**我们的业务值归一化。原因：
- `Decimal` / `datetime` / `UUID` / `Enum` / `bytes` 在 RFC 8785 中**没有规定**如何序列化（属于实现自由区）；
- 跨语言一致性必须由我们保证，否则不同实现会产出不同指纹。

---

## 三、候选详细评估

### C1: `rfc8785` PyPI 包

**已知性质**（基于 PyPI 元数据与公开描述）：
- 纯 Python，无传递依赖；
- 输出 UTF-8 `bytes`；
- **真实公开 API**：`rfc8785.dumps(value) -> bytes` / `rfc8785.dump(value, io)`（来自 PyPI 官方 README 示例）；
- ⚠️ 历史草稿曾误写为 `canonicalize(value) -> bytes` —— **此为错误名称**，实测时必须以 `dumps/dump` 为准。

**待核问题**（实测阶段必须覆盖）：
| 测试维度 | 必须验证 |
| :--- | :--- |
| RFC 8785 测试向量 | 至少 `rfc8785-test-vectors` 公开向量集 100% 通过 |
| Python 版本 | 3.9 / 3.10 / 3.11 / 3.12 全绿 |
| 维护活跃度 | 最近 12 个月有 release；issue 响应 < 90 天 |
| 隐式类型转换 | `Decimal` / `datetime` / `UUID` 是否被库自动转换？我们要求**不被自动转换**（必须我们自己归一；RFC 8785 对这些类型**未规定**，依赖库实现，必须实测确认） |
| 字节编码 | `bytes` 输出为 base64url 还是其他？我们要求 base16 |
| 浮点边缘 | `-0.0` / `NaN` / `Infinity` 行为 |
| 锁定性 | 是否支持内容哈希锁定（pip hash 验证） |
| 许可证 | 需确认（Apache-2.0 / MIT / BSD 优先） |

### C2: 其他经审计的 JCS 实现

按以下顺序筛选（仅记录评估方向，不预选具体包）：
- 源代码可读、< 500 行核心逻辑；
- 维护活跃或为标准库（如 Go `jcs`）；
- 许可证可接受；
- 跨语言测试向量覆盖度。

### C3: 非 RFC 8785 合规降级实现（仅开发期 / 实验工具）

**性质声明**：C3 **不实现完整 RFC 8785**，**不能**作为生产路径的指纹实现。

**严禁使用场景**：
- ❌ 跨语言审计指纹（如 `StateTransitionRecord.audit_hash`）；
- ❌ 生产级 PipelineExecutionAudit；
- ❌ 与外部系统（如 ERP、对账系统）互操作的规范化结果；
- ❌ 任何需要密码学审计可信度的场景。

**允许使用场景**：
- ✅ 开发期实验工具；
- ✅ RFC 8785 测试向量自测的对照样本；
- ✅ 离线调试（非合规降级实现即可）。

**实现范围（若启用）**：
- 不实现完整 RFC 8785；
- 仅实现 JSON 数值规范化（IEEE 754 toJSON）+ 字典序键排序 + UTF-8 编码；
- 业务值归一化（A.1）必须前置完成。

**生产路径必须使用 C1 或 C2 的完整 RFC 8785 实现**，并通过公开测试向量。

---

## 四、必测向量表

| 类别 | 输入 | 期望 |
| :--- | :--- | :--- |
| 数值 -0.0 | `-0.0` | **拒绝**（与 A.1 决策严格一致：`NegativeZeroError` / `TimeContractViolation`）；禁止 JCS 库自动归一 |
| 数值 NaN | `float('nan')` | RFC 8785 明确禁止，库必须拒绝 |
| 数值 Infinity | `float('inf')` | 同上 |
| 超大整数 | `2**64 + 1` | 严格十进制；不能丢精度 |
| Decimal | `Decimal('1.10')` | 尾零规范化（业务层先做） |
| Unicode key（基本平面 BMP）| `{"中文": 1, "a": 2}` | 按 RFC 8785 §3.2.2 UTF-16 code unit 字典序（不要求 NFC 归一化） |
| Unicode key（非 BMP 平面）| `{"𝕏": 1}` | 代理对（surrogate pair）按 UTF-16 code unit 数值排序 |
| Unicode key（含组合字符）| `{"e\u0301": 1}` | 按代码单元字节序；**不进行 NFC 归一化**（RFC 8785 未规定） |
| Unicode key（含转义字符）| `{"\n": 1}` | 反斜杠 `\` (0x5C) 在双引号 `"` (0x22) 之前 |
| datetime TZ | `2026-08-25T12:00:00+08:00` | 强制 UTC 后 `YYYY-MM-DDTHH:MM:SSZ` |
| bytes | `b'hello'` | base16（小写） |
| UUID | `UUID('...')` | 标准 8-4-4-4-12 hex |
| Enum | `LifecycleStatus.PLANNED` | `enum.value`（字符串） |
| 嵌套 Mapping | `{"a": {"b": [1, 2]}}` | 递归规范化 |
| 字典键 None | `{None: 1}` | RFC 8785 要求键为 string，否则拒绝 |
| tuple | `(1, 2)` | JSON array |

---

## 五、最终选型标准（必须全过）

```
RFC 8785 向量通过          (test vectors PASS)
+ 跨 Python 3.9/3.10/3.11/3.12 稳定
+ 无隐式类型转换          (库不替我们归一化 Decimal/UUID/Enum/bytes/datetime)
+ 依赖可接受              (< 1MB, 0 传递依赖优先)
+ 许可证可接受            (Apache-2.0 / MIT / BSD)
+ 可离线运行              (缓存 wheel 可用, 离线 pip install)
+ 版本可锁定              (pip hash 锁定)
```

---

## 六、阶段状态（v1.0.1 修订后）

| 阶段 | 状态 |
| :--- | :--- |
| 候选清单修正 | ✅ 完成（剔除 pyca/cryptography 错误项） |
| C1 真实 API 名称锁定 | ✅ v1.0.1 修正（`rfc8785.dumps` / `rfc8785.dump`） |
| C3 性质重新定性 | ✅ v1.0.1 标记为"非 RFC 8785 合规降级实现"，从生产路径剔除 |
| 业务归一化层与 JCS 库边界 | ✅ 明确（业务值归一化由 A.1 层负责） |
| 实测评估（依赖安装、向量验证） | ⏳ 待主管明确启动信号 |
| 选型决策 | ⏳ 待实测后定 C1/C2 |
| 代码实现 | ❌ 未启动（不在本决策范围） |

**修订历程**：
- v1.0 → v1.0.1：修复 P1 两项（API 名称错误 canonicalize → dumps/dump、C3 性质标错为非合规降级实现）
- v1.0.1 → v1.0.2：修复 P1 三项（-0.0 期望唯一为拒绝、删除 NFC 错误表述、Unicode 排序规则统一为 RFC 8785 UTF-16 code unit；新增 4 项 Unicode 黄金测试向量覆盖非 BMP/组合字符/转义字符）

**下一步（待主管授权）**：进入实测阶段，安装候选包（`rfc8785`），运行公开 RFC 8785 测试向量并记录结果，再做最终选型。
