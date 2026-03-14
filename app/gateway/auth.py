"""
OpenCode 认证鉴权模块

支持多种认证方式：
- API Key 认证
- JWT Token 认证
- 基本认证（开发环境）
"""
import hashlib
import hmac
import json
import logging
import os
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import secrets
import base64

logger = logging.getLogger(__name__)

# 导出异常类
__all__ = [
    "AuthManager",
    "AuthContext",
    "AuthError",
    "InvalidCredentialsError",
    "ExpiredTokenError",
    "InsufficientPermissionsError",
    "APIKeyManager",
    "JWTManager",
]


# ============================================================================
# 认证上下文
# ============================================================================

@dataclass
class AuthContext:
    """认证上下文"""
    user_id: str
    auth_type: str  # api_key, jwt, basic
    credentials: Dict[str, Any]
    permissions: list = None
    expires_at: Optional[datetime] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []

    def is_valid(self) -> bool:
        """检查认证是否有效"""
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True

    def has_permission(self, permission: str) -> bool:
        """检查是否有指定权限"""
        return permission in self.permissions or "*" in self.permissions


# ============================================================================
# 认证异常
# ============================================================================

class AuthError(Exception):
    """认证错误基类"""
    pass


class InvalidCredentialsError(AuthError):
    """无效凭证错误"""
    pass


class ExpiredTokenError(AuthError):
    """令牌过期错误"""
    pass


class InsufficientPermissionsError(AuthError):
    """权限不足错误"""
    pass


# ============================================================================
# API Key 管理
# ============================================================================

class APIKeyManager:
    """API Key 管理器"""

    def __init__(self):
        """初始化 API Key 管理器"""
        # 存储有效的 API Keys
        # 格式: {api_key: {user_id, created_at, expires_at, permissions}}
        self._api_keys: Dict[str, Dict[str, Any]] = {}

        self.logger = logging.getLogger(__name__)

    def generate_api_key(
        self,
        user_id: str,
        expires_in_days: int = 365,
        permissions: list = None
    ) -> str:
        """
        生成 API Key

        Args:
            user_id: 用户ID
            expires_in_days: 过期天数（默认365天）
            permissions: 权限列表

        Returns:
            API Key
        """
        # 生成随机密钥
        api_key = f"opencode_{secrets.token_urlsafe(32)}"

        # 存储密钥信息
        expires_at = datetime.now() + timedelta(days=expires_in_days)

        self._api_keys[api_key] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "permissions": permissions or []
        }

        self.logger.info(f"Generated API key for user {user_id}")
        return api_key

    def verify_api_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """
        验证 API Key

        Args:
            api_key: API Key

        Returns:
            (is_valid, user_id): 是否有效及用户ID
        """
        if api_key not in self._api_keys:
            return False, None

        key_info = self._api_keys[api_key]

        # 检查过期
        if key_info["expires_at"] and datetime.now() > key_info["expires_at"]:
            return False, None

        return True, key_info["user_id"]

    def revoke_api_key(self, api_key: str) -> bool:
        """
        撤销 API Key

        Args:
            api_key: API Key

        Returns:
            是否成功
        """
        if api_key in self._api_keys:
            del self._api_keys[api_key]
            self.logger.info(f"Revoked API key: {api_key[:10]}...")
            return True
        return False

    def get_api_key_info(self, api_key: str) -> Optional[Dict[str, Any]]:
        """获取 API Key 信息"""
        return self._api_keys.get(api_key)


# ============================================================================
# JWT Token 管理
# ============================================================================

class JWTManager:
    """JWT Token 管理器"""

    def __init__(self, secret_key: str = None):
        """
        初始化 JWT 管理器

        Args:
            secret_key: 签名密钥（默认从环境变量读取）
        """
        # 修复：优先从环境变量读取，避免重启后令牌失效
        if secret_key is None:
            secret_key = os.getenv("OPENCODE_JWT_SECRET_KEY")

        if secret_key is None:
            secret_key = secrets.token_urlsafe(32)
            self.logger.warning(
                "JWT secret key auto-generated. "
                "Set OPENCODE_JWT_SECRET_KEY environment variable for persistence."
            )

        self.secret_key = secret_key
        self.algorithm = "HS256"

        self.logger = logging.getLogger(__name__)

    def generate_token(
        self,
        user_id: str,
        expires_in_hours: int = 24,
        permissions: list = None
    ) -> str:
        """
        生成 JWT Token

        Args:
            user_id: 用户ID
            expires_in_hours: 过期小时数
            permissions: 权限列表

        Returns:
            JWT Token
        """
        # Token 头部
        header = {
            "alg": self.algorithm,
            "typ": "JWT"
        }

        # Token 载荷
        now = datetime.now()
        payload = {
            "user_id": user_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=expires_in_hours)).timestamp()),
            "permissions": permissions or []
        }

        # 生成签名
        header_b64 = self._base64url_encode(json.dumps(header))
        payload_b64 = self._base64url_encode(json.dumps(payload))

        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()

        signature_b64 = self._base64url_encode(signature)

        token = f"{message}.{signature_b64}"

        self.logger.info(f"Generated JWT token for user {user_id}")
        return token

    def verify_token(self, token: str) -> Tuple[bool, Optional[str], Optional[list]]:
        """
        验证 JWT Token

        Args:
            token: JWT Token

        Returns:
            (is_valid, user_id, permissions): 是否有效、用户ID、权限列表
        """
        try:
            # 分割 token
            parts = token.split(".")
            if len(parts) != 3:
                return False, None, None

            header_b64, payload_b64, signature_b64 = parts

            # 验证签名
            message = f"{header_b64}.{payload_b64}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()

            expected_signature_b64 = self._base64url_encode(expected_signature)

            if not hmac.compare_digest(signature_b64, expected_signature_b64):
                return False, None, None

            # 解码载荷
            payload = json.loads(self._base64url_decode(payload_b64))

            # 检查过期
            if "exp" in payload:
                exp = payload["exp"]
                if datetime.now().timestamp() > exp:
                    return False, None, None

            return True, payload.get("user_id"), payload.get("permissions", [])

        except Exception as e:
            self.logger.error(f"Error verifying token: {e}")
            return False, None, None

    def _base64url_encode(self, data: bytes) -> str:
        """Base64 URL 编码"""
        if isinstance(data, str):
            data = data.encode()
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

    def _base64url_decode(self, data: str) -> bytes:
        """Base64 URL 解码"""
        # 添加填充
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)


# ============================================================================
# 认证管理器
# ============================================================================

class AuthManager:
    """
    认证管理器

    统一的认证入口，支持多种认证方式
    """

    def __init__(
        self,
        api_key_manager: APIKeyManager = None,
        jwt_manager: JWTManager = None,
        enable_basic_auth: bool = False
    ):
        """
        初始化认证管理器

        Args:
            api_key_manager: API Key 管理器
            jwt_manager: JWT 管理器
            enable_basic_auth: 是否启用基本认证（仅开发环境）
        """
        self.api_key_manager = api_key_manager or APIKeyManager()
        self.jwt_manager = jwt_manager or JWTManager()
        self.enable_basic_auth = enable_basic_auth

        # 修复：从环境变量读取基本认证凭证，避免硬编码
        self._basic_auth_credentials = {}
        if enable_basic_auth:
            username = os.getenv("OPENCODE_BASIC_AUTH_USERNAME")
            password = os.getenv("OPENCODE_BASIC_AUTH_PASSWORD")
            if username and password:
                self._basic_auth_credentials = {username: password}
                self.logger.warning(
                    "Basic auth enabled - NOT recommended for production"
                )
            else:
                self.logger.warning(
                    "Basic auth enabled but no credentials configured. "
                    "Set OPENCODE_BASIC_AUTH_USERNAME and PASSWORD."
                )

        self.logger = logging.getLogger(__name__)
        self.logger.info("AuthManager initialized")

    async def verify(self, auth_context: AuthContext) -> Tuple[bool, Optional[str]]:
        """
        验证认证上下文

        Args:
            auth_context: 认证上下文

        Returns:
            (is_valid, error): 是否有效及错误信息
        """
        try:
            # 检查是否过期
            if not auth_context.is_valid():
                return False, "Authentication expired"

            # 根据认证类型验证
            if auth_context.auth_type == "api_key":
                return await self._verify_api_key(auth_context)
            elif auth_context.auth_type == "jwt":
                return await self._verify_jwt(auth_context)
            elif auth_context.auth_type == "basic":
                return await self._verify_basic(auth_context)
            else:
                return False, f"Unsupported auth type: {auth_context.auth_type}"

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False, str(e)

    async def _verify_api_key(self, auth_context: AuthContext) -> Tuple[bool, Optional[str]]:
        """验证 API Key"""
        api_key = auth_context.credentials.get("api_key")

        if not api_key:
            return False, "API key is required"

        is_valid, user_id = self.api_key_manager.verify_api_key(api_key)

        if not is_valid:
            return False, "Invalid API key"

        return True, None

    async def _verify_jwt(self, auth_context: AuthContext) -> Tuple[bool, Optional[str]]:
        """验证 JWT Token"""
        token = auth_context.credentials.get("token")

        if not token:
            return False, "Token is required"

        is_valid, user_id, permissions = self.jwt_manager.verify_token(token)

        if not is_valid:
            return False, "Invalid or expired token"

        return True, None

    async def _verify_basic(self, auth_context: AuthContext) -> Tuple[bool, Optional[str]]:
        """验证基本认证"""
        if not self.enable_basic_auth:
            return False, "Basic auth is disabled"

        username = auth_context.credentials.get("username")
        password = auth_context.credentials.get("password")

        if not username or not password:
            return False, "Username and password are required"

        if username not in self._basic_auth_credentials:
            return False, "Invalid credentials"

        expected_password = self._basic_auth_credentials[username]

        if not hmac.compare_digest(password, expected_password):
            return False, "Invalid credentials"

        return True, None

    def create_api_key(
        self,
        user_id: str,
        expires_in_days: int = 365,
        permissions: list = None
    ) -> str:
        """创建 API Key"""
        return self.api_key_manager.generate_api_key(
            user_id,
            expires_in_days,
            permissions
        )

    def create_jwt_token(
        self,
        user_id: str,
        expires_in_hours: int = 24,
        permissions: list = None
    ) -> str:
        """创建 JWT Token"""
        return self.jwt_manager.generate_token(
            user_id,
            expires_in_hours,
            permissions
        )
