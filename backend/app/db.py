"""SQLite 仓储层（文档 §11/§24 数据库表结构）。

表：
- sessions(id, status, current_state, created_at, updated_at)
- messages(id, session_id, phase, sender, content, metadata, created_at)
- contexts(session_id, version, data, created_at)
- questions(id, session_id, question_id, asked_by, question, reason, importance, answered, answer)

仅依赖标准库 sqlite3，保证零依赖可运行。本实现为单进程复用一条长连接（加锁），
足以支撑本地 SQLite 与个人决策议会这类低频写入场景。
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from typing import Dict, List, Optional

_LOCK = threading.Lock()


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'active',
        current_state TEXT NOT NULL DEFAULT 'INIT',
        created_at TEXT,
        updated_at TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        phase TEXT,
        sender TEXT,
        content TEXT,
        metadata TEXT,
        created_at TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS contexts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        data TEXT,
        created_at TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        question_id TEXT,
        asked_by TEXT,
        question TEXT,
        reason TEXT,
        importance TEXT,
        answered INTEGER DEFAULT 0,
        answer TEXT DEFAULT ''
    )""")
    conn.commit()


class Repository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        init_db(self.conn)

    def close(self) -> None:
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    # ---------------- sessions ----------------
    def create_session(self, current_state: str = "INIT") -> str:
        sid = uuid.uuid4().hex
        now = _now()
        with _LOCK:
            self.conn.execute(
                "INSERT INTO sessions(id, status, current_state, created_at, updated_at) VALUES (?,?,?,?,?)",
                (sid, "active", current_state, now, now))
            self.conn.commit()
        return sid

    def get_session(self, sid: str) -> Optional[Dict]:
        with _LOCK:
            row = self.conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        return dict(row) if row else None

    def update_state(self, sid: str, state: str) -> None:
        with _LOCK:
            self.conn.execute(
                "UPDATE sessions SET current_state=?, updated_at=? WHERE id=?",
                (state, _now(), sid))
            self.conn.commit()

    # ---------------- messages ----------------
    def add_message(self, sid: str, sender: str, content: str,
                    phase: Optional[str] = None, metadata: Optional[Dict] = None) -> int:
        meta = json.dumps(metadata or {}, ensure_ascii=False)
        with _LOCK:
            cur = self.conn.execute(
                "INSERT INTO messages(session_id, phase, sender, content, metadata, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (sid, phase, sender, content, meta, _now()))
            self.conn.commit()
            return cur.lastrowid

    def get_messages(self, sid: str) -> List[Dict]:
        with _LOCK:
            rows = self.conn.execute(
                "SELECT * FROM messages WHERE session_id=? ORDER BY id ASC", (sid,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["metadata"] = json.loads(d["metadata"] or "{}")
            out.append(d)
        return out

    # ---------------- contexts ----------------
    def save_context(self, sid: str, version: int, data: Dict) -> None:
        with _LOCK:
            self.conn.execute(
                "INSERT INTO contexts(session_id, version, data, created_at) VALUES (?,?,?,?)",
                (sid, version, json.dumps(data, ensure_ascii=False), _now()))
            self.conn.commit()

    def get_latest_context(self, sid: str) -> Optional[Dict]:
        with _LOCK:
            row = self.conn.execute(
                "SELECT * FROM contexts WHERE session_id=? ORDER BY version DESC LIMIT 1",
                (sid,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["data"] = json.loads(d["data"] or "{}")
        return d

    def get_all_contexts(self, sid: str) -> List[Dict]:
        with _LOCK:
            rows = self.conn.execute(
                "SELECT * FROM contexts WHERE session_id=? ORDER BY version ASC", (sid,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["data"] = json.loads(d["data"] or "{}")
            out.append(d)
        return out

    # ---------------- questions ----------------
    def save_questions(self, sid: str, questions: List[Dict]) -> None:
        with _LOCK:
            for q in questions:
                self.conn.execute(
                    "INSERT INTO questions(session_id, question_id, asked_by, question, reason, "
                    "importance, answered, answer) VALUES (?,?,?,?,?,?,?,?)",
                    (sid, q.get("question_id"), q.get("asked_by"), q.get("question"),
                     q.get("reason", ""), q.get("importance", "medium"),
                     1 if q.get("answered") else 0, q.get("answer", "")))
            self.conn.commit()

    def get_questions(self, sid: str) -> List[Dict]:
        with _LOCK:
            rows = self.conn.execute(
                "SELECT * FROM questions WHERE session_id=? ORDER BY id ASC", (sid,)).fetchall()
        return [dict(r) for r in rows]

    def answer_questions(self, sid: str, answers: List[Dict[str, str]]) -> None:
        """批量标记问题已回答并记录答案。answers: [{question_id, answer} | {asked_by, answer}]"""
        qs = self.get_questions(sid)
        by_id = {q["question_id"]: q for q in qs if q.get("question_id")}
        by_role = {}
        for q in qs:
            by_role.setdefault(q["asked_by"], []).append(q)
        with _LOCK:
            for a in answers:
                target = None
                if a.get("question_id") and a["question_id"] in by_id:
                    target = by_id[a["question_id"]]
                elif a.get("asked_by") and a["asked_by"] in by_role:
                    for q in by_role[a["asked_by"]]:
                        if not q["answered"]:
                            target = q
                            break
                if target:
                    self.conn.execute(
                        "UPDATE questions SET answered=1, answer=? WHERE id=?",
                        (a.get("answer", ""), target["id"]))
            self.conn.commit()
