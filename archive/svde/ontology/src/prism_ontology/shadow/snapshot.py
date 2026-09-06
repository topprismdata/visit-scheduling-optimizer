"""InputSnapshot — 输入原始字节的不可变只读快照

职责:
- 计算输入字节的 SHA-256
- 记录 snapshot_id, content_sha256, source_path, byte_length, media_type, schema_version
- captured_at 显式带 timezone (不参与内容哈希)
- 同一输入字节 -> 同一 hash; 内容变化 -> 不同 hash
- 全程只读, 不写回 WorldState, 不下发外部系统
- 不加载 BIZ 规则, 不修改 MVPResult

设计:
- InputSnapshot 是 frozen dataclass (不可变)
- snapshot_id 由 snapshot_factory 统一生成, 包含 content_sha256[:12] 避免重名
- captured_at 接受 timezone-aware datetime, 默认 UTC
- content_sha256 是 64 字符 hex (256-bit SHA-256)
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import hashlib


# SHA-256 二进制摘要 -> 64 字符 hex
SHA256_HEX_LEN = 64


@dataclass(frozen=True)
class InputSnapshot:
    """不可变输入快照

    Fields:
        snapshot_id: 唯一标识 (含 content_sha256[:12] 避免冲突)
        content_sha256: 输入字节的 SHA-256 hex 摘要 (64 字符)
        source_path: 输入来源路径 (本地路径 / URL / "-" 表示无路径)
        byte_length: 输入字节数
        media_type: 输入媒体类型 (如 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" / "text/csv" / "application/octet-stream")
        schema_version: 输入数据 schema 版本 (如 "fmcg_visit_history_v1.0" / "csv-1.0")
        captured_at: 捕获时间 (timezone-aware, 默认 UTC), 不参与内容哈希
    """
    snapshot_id: str
    content_sha256: str
    source_path: str
    byte_length: int
    media_type: str
    schema_version: str
    captured_at: datetime

    def __post_init__(self):
        # 字段完整性 (鲁棒性校验, 不依赖外部 schema)
        if not self.content_sha256 or len(self.content_sha256) != SHA256_HEX_LEN:
            raise ValueError(
                f"content_sha256 必须是 {SHA256_HEX_LEN} 字符 hex, 实际: {len(self.content_sha256)}"
            )
        if self.byte_length < 0:
            raise ValueError(f"byte_length 必须 >= 0, 实际: {self.byte_length}")
        if not self.media_type:
            raise ValueError("media_type 不能为空")
        if not self.schema_version:
            raise ValueError("schema_version 不能为空")
        # captured_at timezone 校验 (接受 aware; naive 拒绝)
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at 必须带 timezone (建议显式传入 timezone.utc)")


def compute_content_sha256(content: bytes) -> str:
    """计算输入字节的 SHA-256 hex 摘要 (64 字符)

    同一输入字节 -> 同一 hash; 字节变化 -> 不同 hash.
    """
    if not isinstance(content, bytes):
        raise TypeError(f"content 必须是 bytes, 实际: {type(content).__name__}")
    return hashlib.sha256(content).hexdigest()


def _build_snapshot_id(content_sha256: str, captured_at: datetime) -> str:
    """生成 snapshot_id: SNAP-<utc-timestamp>-<content_sha256[:12]>

    timestamp 用 captured_at UTC ISO8601 形式 (去除 ':' 和 '-' 以便文件系统安全).
    """
    if not isinstance(content_sha256, str) or len(content_sha256) != SHA256_HEX_LEN:
        raise ValueError(f"content_sha256 必须是 {SHA256_HEX_LEN} 字符 hex")
    if not isinstance(captured_at, datetime):
        raise TypeError("captured_at 必须是 datetime")
    if captured_at.tzinfo is None:
        raise ValueError("captured_at 必须带 timezone (建议显式传入 timezone.utc)")

    ts_utc = captured_at.astimezone(timezone.utc)
    ts_compact = ts_utc.strftime("%Y%m%dT%H%M%SZ")
    return f"SNAP-{ts_compact}-{content_sha256[:12]}"


def snapshot_factory(
    content: bytes,
    *,
    source_path: str = "-",
    media_type: str = "application/octet-stream",
    schema_version: str = "unknown",
    captured_at: Optional[datetime] = None,
) -> InputSnapshot:
    """构造 InputSnapshot 的统一入口

    Args:
        content: 原始输入字节
        source_path: 来源路径 (本地 / URL / "-" 表示无路径)
        media_type: 媒体类型 (MIME 风格)
        schema_version: 数据 schema 版本标识
        captured_at: 捕获时间 (默认 UTC now, 建议显式传入用于 replay)

    Returns:
        InputSnapshot (frozen dataclass)
    """
    if captured_at is None:
        captured_at = datetime.now(timezone.utc)
    content_sha256 = compute_content_sha256(content)
    snapshot_id = _build_snapshot_id(content_sha256, captured_at)
    return InputSnapshot(
        snapshot_id=snapshot_id,
        content_sha256=content_sha256,
        source_path=source_path,
        byte_length=len(content),
        media_type=media_type,
        schema_version=schema_version,
        captured_at=captured_at,
    )
