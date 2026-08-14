"""FastAPI 入口：个人决策议会后端服务。

提供：会话创建、发送消息（驱动状态机）、获取会话详情。
允许跨域（H5 / 本地调试）。LLM 提供方由环境变量决定（mock / deepseek）。
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config as cfg
from . import db as dbmod
from .council import CouncilOrchestrator
from .llm import build_llm

_SETTINGS = cfg.load_settings()
_REPO = dbmod.Repository(_SETTINGS.db_path)
_LLM = build_llm(_SETTINGS)
_ORCH = CouncilOrchestrator(_LLM, _REPO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时确保表已建（Repository 构造时已建）
    yield


app = FastAPI(title="Personal Decision Council API", version="0.2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageIn(BaseModel):
    text: str


@app.get("/api/health")
def health() -> Dict:
    return {"status": "ok", "llm_provider": _SETTINGS.llm_provider,
            "deepseek_configured": bool(_SETTINGS.deepseek_api_key)}


@app.post("/api/sessions")
def create_session() -> Dict:
    sid = _ORCH.create_session()
    return {"session_id": sid, "state": "INIT"}


@app.get("/api/sessions/{sid}")
def get_session(sid: str) -> Dict:
    detail = _ORCH.get_detail(sid)
    if not detail:
        raise HTTPException(status_code=404, detail="会话不存在")
    return detail


@app.post("/api/sessions/{sid}/messages")
def post_message(sid: str, body: MessageIn) -> Dict:
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=400, detail="text 不能为空")
    try:
        result = _ORCH.send(sid, body.text.strip())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=_SETTINGS.host, port=_SETTINGS.port,
                log_level=_SETTINGS.log_level)
