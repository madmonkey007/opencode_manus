"""
OpenCode 新架构数据模型

基于官方 OpenCode Web API 的 Session + Message + Part 结构
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import time


# ====================================================================
# Enums
# ====================================================================

class SessionStatus(str, Enum):
    """会话状态"""
    ACTIVE = "active"
    IDLE = "idle"
    ARCHIVED = "archived"


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"


class PartType(str, Enum):
    """消息部分类型"""
    TEXT = "text"
    TOOL = "tool"
    FILE = "file"
    STEP_START = "step-start"
    STEP_FINISH = "step-finish"


class ToolStatus(str, Enum):
    """工具执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


# ====================================================================
# Session Models
# ====================================================================

class SessionTime(BaseModel):
    """会话时间戳"""
    created: int = Field(default_factory=lambda: int(time.time()))
    updated: int = Field(default_factory=lambda: int(time.time()))


class Session(BaseModel):
    """OpenCode 会话"""
    id: str = Field(..., description="会话ID，以 'ses_' 开头")
    title: str = Field(default="New Session", description="会话标题")
    version: str = Field(default="1.0.0", description="API版本")
    time: SessionTime = Field(default_factory=SessionTime, description="时间戳")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="会话状态")

    class Config:
        json_encoders = {
            int: int,
        }


# ====================================================================
# Message Models
# ====================================================================

class WorkspacePath(BaseModel):
    """工作区路径"""
    cwd: str = Field(..., description="当前工作目录")
    root: str = Field(..., description="项目根目录")


class TokenCount(BaseModel):
    """Token 计数"""
    input: int = 0
    output: int = 0
    reasoning: int = 0
    cache_write: int = 0
    cache_read: int = 0


class MessageMetadata(BaseModel):
    """消息元数据（Assistant 消息专用）"""
    system: Optional[List[str]] = Field(default=None, description="系统提示")
    model_id: Optional[str] = Field(default=None, description="模型ID")
    provider_id: Optional[str] = Field(default=None, description="提供商ID")
    path: Optional[WorkspacePath] = Field(default=None, description="工作区路径")
    summary: Optional[bool] = Field(default=None, description="是否为总结消息")
    cost: Optional[float] = Field(default=None, description="成本")
    tokens: Optional[TokenCount] = Field(default=None, description="Token使用")


class MessageTime(BaseModel):
    """消息时间戳"""
    created: int = Field(default_factory=lambda: int(time.time()))
    completed: Optional[int] = Field(default=None, description="完成时间")


class Message(BaseModel):
    """消息（User 或 Assistant）"""
    id: str = Field(..., description="消息ID，以 'msg_' 开头")
    session_id: str = Field(..., description="所属会话ID")
    role: MessageRole = Field(..., description="消息角色")
    time: MessageTime = Field(default_factory=MessageTime, description="时间戳")
    metadata: Optional[MessageMetadata] = Field(default=None, description="元数据（仅 Assistant）")


# ====================================================================
# Part Models
# ====================================================================

class PartTime(BaseModel):
    """部分时间戳"""
    start: int = Field(default_factory=lambda: int(time.time()))
    end: Optional[int] = Field(default=None, description="结束时间")


class ToolState(BaseModel):
    """工具执行状态"""
    status: ToolStatus = Field(..., description="执行状态")
    input: Optional[Dict[str, Any]] = Field(default=None, description="输入参数")
    output: Optional[str] = Field(default=None, description="输出内容")
    error: Optional[str] = Field(default=None, description="错误信息")


class ToolMetadata(BaseModel):
    """工具元数据（用于历史回溯）"""
    preview: Optional[str] = Field(default=None, description="文件内容预览")
    diff: Optional[str] = Field(default=None, description="编辑差异（unified diff格式）")
    title: Optional[str] = Field(default=None, description="操作标题")
    time: Optional[PartTime] = Field(default=None, description="执行时间")


class PartContent(BaseModel):
    """消息部分内容（Union 类型）"""
    text: Optional[str] = Field(default=None, description="文本内容")
    tool: Optional[str] = Field(default=None, description="工具名称")
    call_id: Optional[str] = Field(default=None, description="调用ID")
    state: Optional[ToolState] = Field(default=None, description="工具状态")
    mime: Optional[str] = Field(default=None, description="MIME类型（文件）")
    filename: Optional[str] = Field(default=None, description="文件名（文件）")
    url: Optional[str] = Field(default=None, description="文件URL")


class Part(BaseModel):
    """消息部分（Message 的组成部分）"""
    id: str = Field(..., description="部分ID，以 'part_' 开头")
    session_id: str = Field(..., description="所属会话ID")
    message_id: str = Field(..., description="所属消息ID")
    type: PartType = Field(..., description="部分类型")
    content: Optional[PartContent] = Field(default=None, description="部分内容")
    time: PartTime = Field(default_factory=PartTime, description="时间戳")
    metadata: Optional[ToolMetadata] = Field(default=None, description="工具元数据")


# ====================================================================
# Composite Models
# ====================================================================

class MessageWithParts(BaseModel):
    """包含部分的消息（用于API返回）"""
    info: Message = Field(..., description="消息元信息")
    parts: List[Part] = Field(default_factory=list, description="消息部分列表")


# ====================================================================
# File Snapshot（用于历史回溯）
# ====================================================================

class FileSnapshot(BaseModel):
    """文件快照（记录文件在某个时间点的状态）"""
    id: str = Field(..., description="快照ID")
    session_id: str = Field(..., description="所属会话ID")
    file_path: str = Field(..., description="文件路径")
    content: str = Field(..., description="文件内容")
    operation: str = Field(..., description="操作类型：created/modified/deleted")
    step_id: str = Field(..., description="关联的步骤ID（part_id）")
    timestamp: int = Field(..., description="时间戳")
    checksum: str = Field(..., description="文件校验和（MD5/SHA256）")


class TimelineStep(BaseModel):
    """时间轴步骤（用于前端显示操作历史）"""
    step_id: str = Field(..., description="步骤ID")
    action: str = Field(..., description="操作类型：write/edit/bash/grep等")
    path: str = Field(..., description="文件路径")
    timestamp: int = Field(..., description="时间戳")
    status: Optional[str] = Field(default=None, description="状态")
    preview: Optional[str] = Field(default=None, description="预览内容")


# ====================================================================
# API Request/Response Models
# ====================================================================

class UserMessagePart(BaseModel):
    """用户消息部分"""
    type: str = Field(default="text", description="部分类型")
    text: Optional[str] = Field(default=None, description="文本内容")


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    message_id: str = Field(..., description="消息ID")
    provider_id: str = Field(default="anthropic", description="提供商ID")
    model_id: str = Field(default="claude-3-5-sonnet-20241022", description="模型ID")
    mode: str = Field(default="auto", description="执行模式")
    parts: List[UserMessagePart] = Field(..., description="消息部分")


class SendMessageResponse(BaseModel):
    """发送消息响应"""
    id: str = Field(..., description="消息ID")
    session_id: str = Field(..., description="会话ID")
    role: MessageRole = Field(..., description="消息角色")
    time: MessageTime = Field(default_factory=MessageTime)


# ====================================================================
# SSE Event Models
# ====================================================================

class SessionEvent(BaseModel):
    """SSE 会话事件"""
    type: str = Field(..., description="事件类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="事件属性")


# ====================================================================
# Helper Functions
# ====================================================================

def generate_session_id() -> str:
    """生成会话ID"""
    import uuid
    return f"ses_{uuid.uuid4().hex[:8]}"


def generate_message_id() -> str:
    """生成消息ID"""
    import uuid
    return f"msg_{uuid.uuid4().hex[:8]}"


def generate_part_id(prefix: str = "") -> str:
    """生成部分ID"""
    import uuid
    prefix_suffix = f"{prefix}_" if prefix else ""
    return f"part_{prefix_suffix}{uuid.uuid4().hex[:8]}"


def generate_step_id() -> str:
    """生成步骤ID（用于文件快照）"""
    import uuid
    return f"step_{uuid.uuid4().hex[:8]}"
