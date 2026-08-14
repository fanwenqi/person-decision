"""配置加载：启动时读取 backend/.env 与系统环境变量，决定 LLM 提供方（mock / deepseek）。

设计要点：
- 自动加载 backend/.env（极简解析，不依赖 python-dotenv）。
- LLM_PROVIDER 三态：留空（按 key 自动切换）| deepseek（强制）| mock（强制调试）。
- 留空且有 DEEPSEEK_API_KEY → 自动用 DeepSeek；无 key → 自动用 Mock（保证自测可过）。
- 配置为 deepseek 但缺少 key → 回退 Mock 并告警，保证“配置 key 后顺利交互、未配置不崩”。
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# 后端根目录（config.py 位于 backend/app/config.py）
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv() -> None:
    """极简 .env 加载（不依赖 python-dotenv）。

    仅当环境变量尚未设置时才填充，确保真实环境变量优先级高于 .env。
    依次尝试：backend/.env（与 .env.example 同目录）、当前工作目录 .env。
    """
    candidates = [
        os.path.join(_BACKEND_DIR, ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
        except OSError:
            pass


@dataclass
class Settings:
    llm_provider: str = "mock"          # mock | deepseek（留空由 key 自动决定）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    db_path: str = "council.db"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"


def load_settings() -> Settings:
    # 1) 先加载 .env（不覆盖已存在的真实环境变量）
    _load_dotenv()

    # 2) 读取配置
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    db_path = os.getenv("DB_PATH", "council.db").strip()

    # 3) 决定提供方：
    #    - LLM_PROVIDER=mock   → 强制 Mock（调试用）
    #    - LLM_PROVIDER=deepseek → 强制 DeepSeek（缺少 key 则回退 Mock）
    #    - 留空（默认）         → 有 key 自动用 DeepSeek，无 key 用 Mock
    if not provider:
        provider = "deepseek" if key else "mock"

    if provider == "deepseek":
        if not key:
            provider = "mock"
            print("[config] 已指定 deepseek 但缺少 DEEPSEEK_API_KEY，已回退到 Mock LLM。")
        else:
            print(f"[config] 使用 DeepSeek LLM（key={key[:6]}…{key[-4:]}）。")
    elif provider == "mock":
        print("[config] 使用 Mock LLM（已显式关闭 DeepSeek）。")
    else:
        # 未知 provider → 安全回退 mock
        provider = "mock"
        print(f"[config] 未知 LLM_PROVIDER，已回退到 Mock LLM。")

    return Settings(
        llm_provider=provider,
        deepseek_api_key=key,
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip(),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip(),
        db_path=db_path,
        host=os.getenv("HOST", "0.0.0.0").strip(),
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "info").strip(),
    )
