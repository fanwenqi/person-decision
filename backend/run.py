"""启动入口：python run.py（依赖 fastapi/uvicorn，见 requirements.txt）。"""
import os
import sys

from app import config as cfg

settings = cfg.load_settings()

if __name__ == "__main__":
    import uvicorn

    # 允许通过环境变量或命令行参数覆盖端口
    port = int(os.getenv("PORT", str(settings.port)))
    print(f"[server] LLM={settings.llm_provider}  DB={settings.db_path}  http://{settings.host}:{port}")
    uvicorn.run("app.main:app", host=settings.host, port=port,
                log_level=settings.log_level, reload=False)
