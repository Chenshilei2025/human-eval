#!/usr/bin/env python3
"""Small local web app for blinded human evaluation.

The app deliberately serves only blinded task files, never the answer keys.
Each reviewer gets an independent JSON file under ``responses/``.
"""
from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
WEB = Path(__file__).resolve().parent
RESPONSES = WEB / "responses"
RESPONSES.mkdir(exist_ok=True)
LOCK = threading.Lock()


def load_tasks(kind: str) -> list[dict]:
    if kind not in {"eil", "miu"}:
        raise ValueError("unknown task kind")
    return json.loads((ROOT / f"{kind}_blinded_tasks.json").read_text(encoding="utf-8"))


def safe_reviewer(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())[:50]
    if not value:
        raise ValueError("reviewer is required")
    return value


def response_path(reviewer: str, kind: str) -> Path:
    return RESPONSES / f"{safe_reviewer(reviewer)}_{kind}.json"


def read_scores(reviewer: str, kind: str) -> dict:
    path = response_path(reviewer, kind)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("scores", {}) if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


HTML = (WEB / "index.html").read_text(encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/tasks":
            query = parse_qs(parsed.query)
            kind = query.get("kind", ["eil"])[0]
            reviewer = query.get("reviewer", [""])[0]
            try:
                tasks = load_tasks(kind)
                self.send_json({"kind": kind, "tasks": tasks, "scores": read_scores(reviewer, kind)})
            except ValueError as exc:
                self.send_json({"error": str(exc)}, 400)
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/score":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            reviewer = safe_reviewer(str(payload["reviewer"]))
            kind = payload["kind"]
            task_id = str(payload["task_id"])
            score = payload["score"]
            if kind not in {"eil", "miu"} or not isinstance(score, dict):
                raise ValueError("invalid score payload")
            expected = (
                {"adversary_reasonable", "leakage_reasonable", "utility_reasonable"}
                if kind == "eil" else {"faithfulness_reasonable"}
            )
            if not set(score).issubset(expected) or any(value not in {0, 1} for value in score.values()):
                raise ValueError("scores must contain only the expected 0/1 rationality labels")
            task_ids = {task["task_id"] for task in load_tasks(kind)}
            if task_id not in task_ids:
                raise ValueError("unknown task_id")
            path = response_path(reviewer, kind)
            with LOCK:
                current = {"reviewer": reviewer, "kind": kind, "scores": read_scores(reviewer, kind)}
                current["scores"][task_id] = score
                path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.send_json({"ok": True, "saved": task_id})
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, 400)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Blinded human-evaluation web app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Open http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
