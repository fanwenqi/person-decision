"""端到端集成测试：用 FastAPI TestClient 跑通 HTTP 接口（Mock 模式，无需 key）。
验证真实服务在“配置前”能用 Mock 正常交互。
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

# 必须在导入 app.main 之前设置环境变量
fd, db = tempfile.mkstemp(suffix=".db")
os.close(fd)
os.remove(db)
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DB_PATH"] = db

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def main():
    with TestClient(app) as client:
        h = client.get("/api/health").json()
        assert h["status"] == "ok", h
        assert h["llm_provider"] == "mock", h
        print("health:", h)

        sid = client.post("/api/sessions").json()["session_id"]
        print("session:", sid)

        r1 = client.post(f"/api/sessions/{sid}/messages",
                         json={"text": "我最近焦虑，做程序员没前途，要不要转 AI？"}).json()
        assert r1["state"] == "WAITING_ANSWERS", r1
        kinds = [m["metadata"].get("kind") for m in r1["messages"]]
        assert "role_questions" in kinds, kinds
        print("after problem -> roles asked questions:", len(
            next(m for m in r1["messages"] if m["metadata"].get("kind") == "role_questions")["content"]))

        r2 = client.post(f"/api/sessions/{sid}/messages",
                         json={"text": "Java 8 年，月入 25K，存款 20 万，月支出 6K，没做过 AI 项目。"}).json()
        final = r2["state"]
        assert final in ("WAITING_CLARIFICATION", "COMPLETED"), final

        detail = client.get(f"/api/sessions/{sid}").json()
        msgs = detail["messages"]
        kinds = [m["metadata"].get("kind") for m in msgs]
        assert kinds.count("agent") == 5, kinds
        assert "moderator" in kinds, kinds
        assert "action_plan" in kinds, kinds
        print("OK: 5 agent opinions + moderator + action_plan present")
        print("final state:", final)
    try:
        os.remove(db)
    except OSError:
        pass
    print("\n[integration] PASS — FastAPI 服务在 Mock 模式下端到端可交互")


if __name__ == "__main__":
    main()
