# -*- coding: utf-8 -*-
"""Web 服务：只依赖标准库。

    python web/server.py            # http://127.0.0.1:8770
    python web/server.py --port 9000

接口：
    GET  /                       页面
    GET  /api/config             读配置（api_key 打码）
    POST /api/config             保存三个槽位
    GET  /api/runs               运行列表
    POST /api/runs               新建并启动一次运行
    GET  /api/runs/<id>          运行状态（含日志）
    GET  /api/runs/<id>/tree     题目目录文件树
    GET  /api/runs/<id>/file     读单个文件
"""
import argparse
import json
import os
import sys
import threading
import traceback
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
OJ_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, OJ_ROOT)

import orchestrator
import prompts  # noqa: E402

CONFIG = os.path.join(HERE, "config.json")
RUNS = os.path.join(HERE, "runs")
PROBLEMS = os.path.join(OJ_ROOT, "problems")
ACTIVE = {}
BATCH = {}
BATCH_LOCK = threading.Lock()

DEFAULT_CONFIG = {
    "slots": [
        {"name": "1 号 作者", "base_url": "mock", "api_key": "", "model": "mock",
         "temperature": 0.3, "max_tokens": 0},
        {"name": "2 号 审题者", "base_url": "mock", "api_key": "", "model": "mock",
         "temperature": 0.3, "max_tokens": 0},
        {"name": "3 号 审查者", "base_url": "mock", "api_key": "", "model": "mock",
         "temperature": 0.3, "max_tokens": 0},
        {"name": "4 号 实现者", "base_url": "mock", "api_key": "", "model": "mock",
         "temperature": 0.3, "max_tokens": 0},
    ]
}
SLOT_COUNT = 4


def load_config():
    if not os.path.exists(CONFIG):
        return json.loads(json.dumps(DEFAULT_CONFIG))
    with open(CONFIG, "r", encoding="utf-8-sig") as f:
        cfg = json.load(f)
    # 老配置可能只有 3 个槽，补齐到 4 个
    slots = cfg.setdefault("slots", [])
    while len(slots) < SLOT_COUNT:
        slots.append(json.loads(json.dumps(DEFAULT_CONFIG["slots"][len(slots)])))
    for s in slots:
        s.setdefault("extra", {})
        s.setdefault("max_tokens", 0)
    return cfg


def save_config(cfg):
    with open(CONFIG, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def mask(cfg):
    out = json.loads(json.dumps(cfg))
    for s in out.get("slots", []):
        if s.get("api_key"):
            s["api_key"] = "已设置（" + "*" * 6 + s["api_key"][-4:] + "）"
            s["key_set"] = True
        else:
            s["key_set"] = False
    return out


def _batch_hints(topic, count):
    """给批量任务排好每道题的子方向：先把菜单里的用完，再交给模型自选。"""
    hints = prompts.subtype_list(topic)
    if not hints:
        return [""] * count
    out = []
    for i in range(count):
        out.append(hints[i] if i < len(hints) else "")
    return out


def batch_thread(bid):
    b = BATCH[bid]
    slots = load_config()["slots"]
    hints = _batch_hints(b["topic"], b["count"])
    for i in range(b["count"]):
        if b.get("stopped"):
            break
        seed = {"topic": b["topic"], "difficulty": b["difficulty"],
                "ladder": b.get("ladder") or "", "subtype": hints[i],
                "problem_id": None}
        try:
            run = orchestrator.start(seed, slots)
        except Exception:
            b["results"].append({"index": i + 1, "status": "failed",
                                  "error": traceback.format_exc()[-300:]})
            b["done"] = i + 1
            continue
        ACTIVE[run.run_id] = run
        b["current_run_id"] = run.run_id
        b["current_problem"] = run.problem_id
        b["current_index"] = i + 1
        b["subtype"] = hints[i]
        try:
            run.run()
        except Exception:
            run.status = "failed"
            run.error = "内部异常"
        b["results"].append({"index": i + 1, "run_id": run.run_id,
                              "problem_id": run.problem_id, "subtype": hints[i],
                              "status": run.status, "error": run.error})
        b["done"] = i + 1
        b["ok_count"] = sum(1 for r in b["results"] if r.get("status") == "done")
    b["status"] = "stopped" if b.get("stopped") else "done"
    b["current_run_id"] = None


def run_thread(run):
    try:
        run.run()
    except Exception:
        run.status = "failed"
        run.error = "内部异常"
        run.log("内部异常：" + traceback.format_exc()[-600:], "bad")
        run.save()
    finally:
        # 不从这里移除：保留对象，前端跑完后仍能读到最后一次的模型输出
        pass


class Handler(BaseHTTPRequestHandler):
    server_version = "OJPipeline/1.0"

    def log_message(self, fmt, *args):
        pass

    # ---------------------------------------------------------------- 工具
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, text, code=200, ctype="text/plain; charset=utf-8"):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    # ---------------------------------------------------------------- 路由
    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        try:
            if p in ("/", "/index.html"):
                path = os.path.join(HERE, "index.html")
                with open(path, "r", encoding="utf-8") as f:
                    return self._text(f.read(), ctype="text/html; charset=utf-8")
            if p == "/api/config":
                return self._json(mask(load_config()))
            if p == "/api/runs":
                return self._json({"runs": list_runs()})
            if p == "/health":
                return self._json({"ok": True})
            if p.startswith("/api/batch/") and p != "/api/batch/":
                return self._batch_status(p.rsplit("/", 1)[-1])
            if p.startswith("/api/runs/"):
                rest = p[len("/api/runs/"):].split("/")
                rid = rest[0]
                if len(rest) == 1:
                    return self._json(load_run(rid))
                if rest[1] == "tree":
                    return self._json({"files": list_tree(rid)})
                if rest[1] == "live":
                    run = ACTIVE.get(rid)
                    if run is None:
                        return self._json({"state": "idle", "text": "", "seq": 0})
                    return self._json(dict(run.live, seq=run.live_seq))
                if rest[1] == "file":
                    q = parse_qs(u.query)
                    return self._file(rid, (q.get("path") or [""])[0])
            return self._json({"error": "not found"}, 404)
        except FileNotFoundError as e:
            return self._json({"error": str(e)}, 404)
        except Exception as e:
            return self._json({"error": traceback.format_exc()[-600:]}, 500)

    def do_POST(self):
        p = urlparse(self.path).path
        try:
            if p == "/api/config":
                return self._save_config(self._body())
            if p == "/api/runs":
                return self._start(self._body())
            if p == "/api/batch":
                return self._start_batch(self._body())
            if p.startswith("/api/batch/"):
                return self._batch_status(p.rsplit("/", 1)[-1])
            if p == "/api/models":
                return self._models(self._body())
            return self._json({"error": "not found"}, 404)
        except Exception as e:
            return self._json({"error": traceback.format_exc()[-600:]}, 500)

    def _models(self, body):
        """拉取服务商的模型列表：GET {base_url}/models。

        key / base_url 留空时，回退到该槽位已保存的配置——
        因为页面上 key 输入框为了安全是空的，不这样就永远拿不到 key。
        """
        cfg = load_config()
        idx = body.get("slot")
        saved = cfg["slots"][idx] if isinstance(idx, int) and 0 <= idx < len(cfg["slots"]) else {}

        base = (body.get("base_url") or "").strip().rstrip("/")
        if not base:
            base = (saved.get("base_url") or "").strip().rstrip("/")
        key = (body.get("api_key") or "").strip() or (saved.get("api_key") or "")

        if not base:
            return self._json({"error": "先填 base_url"}, 400)
        if base.startswith("mock"):
            return self._json({"models": ["mock"], "url": "mock"})
        if not base.startswith(("http://", "https://")):
            return self._json({"error": "base_url 必须以 http:// 或 https:// 开头"}, 400)
        if base.endswith("/chat/completions"):
            base = base[: -len("/chat/completions")]

        # 常见笔误：漏了 /v1。两个都试。
        cands = [base + "/models"]
        if "/v1" not in base:
            cands.append(base.rstrip("/") + "/v1/models")

        tried = []
        for url in cands:
            req = urllib.request.Request(url)
            if key:
                req.add_header("Authorization", "Bearer " + key)
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    raw = r.read().decode("utf-8", "replace")
                    status = r.status
            except urllib.error.HTTPError as e:
                tried.append({"url": url, "status": e.code,
                              "body": e.read().decode("utf-8", "replace")[:300]})
                continue
            except Exception as e:
                tried.append({"url": url, "status": None, "body": str(e)[:300]})
                continue
            ids = self._parse_models(raw)
            if ids:
                return self._json({"models": ids, "url": url})
            tried.append({"url": url, "status": status, "body": raw[:300]})

        return self._json({"error": self._models_hint(tried, bool(key)), "tried": tried})

    @staticmethod
    def _parse_models(raw):
        try:
            data = json.loads(raw)
        except Exception:
            return []
        items = data.get("data") or data.get("models") or []
        if isinstance(items, dict):
            items = list(items.values())
        ids = []
        for it in items:
            if isinstance(it, str):
                ids.append(it)
            elif isinstance(it, dict):
                ids.append(it.get("id") or it.get("name") or "")
        return sorted({i for i in ids if isinstance(i, str) and i})

    @staticmethod
    def _models_hint(tried, has_key):
        for t in tried:
            s = t.get("status")
            body = (t.get("body") or "")
            if s in (401, 403):
                return ("鉴权失败（401/403）：API key 没了或不对。"
                        if not has_key else
                        "鉴权失败（401/403）：这个 key 对当前 base_url 无效，检查是不是另一个厂商的 key。")
            if s == 404:
                return "404：base_url 路径不对，多半是少了 /v1，或者该服务商不开放 /models。"
            if s is None:
                return f"连不上：{body[:120]}"
            if body.lstrip()[:1] == "<":
                return "返回的是网页而不是 JSON：base_url 可能填成了官网首页（应该填 API 地址）。"
        return "对方返回里没有模型列表"

    # ---------------------------------------------------------------- 处理
    def _save_config(self, body):
        cfg = load_config()
        incoming = body.get("slots") or []
        for i, s in enumerate(incoming[:len(cfg["slots"])]):
            old = cfg["slots"][i]
            for k in ("name", "base_url", "model", "temperature", "max_tokens"):
                if k in s:
                    old[k] = s[k]
            if isinstance(s.get("extra"), dict):
                old["extra"] = s["extra"]
            key = (s.get("api_key") or "").strip()
            if key and not key.startswith("已设置"):
                old["api_key"] = key
            if s.get("clear_key"):
                old["api_key"] = ""
        save_config(cfg)
        return self._json({"ok": True})

    def _start(self, body):
        seed = {
            "topic": (body.get("topic") or "").strip(),
            "difficulty": (body.get("difficulty") or "").strip(),
            "ladder": (body.get("ladder") or "").strip(),
            "problem_id": (body.get("problem_id") or "").strip() or None,
        }
        if not seed["topic"] or not seed["difficulty"]:
            return self._json({"error": "考点和难度都要填"}, 400)
        cfg = load_config()
        slots = cfg["slots"]
        run = orchestrator.start(seed, slots)
        ACTIVE[run.run_id] = run
        t = threading.Thread(target=run_thread, args=(run,), daemon=True)
        t.start()
        return self._json({"run_id": run.run_id, "problem_id": run.problem_id})

    def _start_batch(self, body):
        topic = (body.get("topic") or "").strip()
        diff = (body.get("difficulty") or "").strip()
        try:
            count = int(body.get("count") or 1)
        except Exception:
            count = 1
        count = max(1, min(count, 20))
        if not topic or not diff:
            return self._json({"error": "考点和难度都要填"}, 400)
        with BATCH_LOCK:
            for b in BATCH.values():
                if b.get("status") == "running":
                    return self._json({"error": "已有批量任务在跑，等它结束或先停止"}, 400)
            bid = "batch-" + time.strftime("%H%M%S") + "-" + uuid.uuid4().hex[:4]
            BATCH[bid] = {"batch_id": bid, "topic": topic, "difficulty": diff,
                          "ladder": (body.get("ladder") or "").strip(),
                          "count": count, "done": 0, "ok_count": 0,
                          "current_index": 0, "current_run_id": None,
                          "current_problem": None, "subtype": "",
                          "status": "running", "results": []}
        threading.Thread(target=batch_thread, args=(bid,), daemon=True).start()
        return self._json({"batch_id": bid, "count": count})

    def _batch_status(self, bid):
        b = BATCH.get(bid)
        if not b:
            return self._json({"error": "没有这个批量任务"}, 404)
        if bid.rstrip("/").endswith("/stop"):
            pass
        return self._json(b)

    def _file(self, rid, rel):
        run = load_run(rid)
        base = os.path.join(PROBLEMS, run["problem_id"])
        target = os.path.abspath(os.path.join(base, rel))
        if not target.startswith(os.path.abspath(base)):
            return self._json({"error": "非法路径"}, 400)
        if not os.path.isfile(target):
            return self._json({"error": "文件不存在"}, 404)
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            return self._json({"path": rel, "content": f.read()})


def list_runs():
    out = []
    if not os.path.isdir(RUNS):
        return out
    for name in sorted(os.listdir(RUNS), reverse=True):
        p = os.path.join(RUNS, name, "run.json")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            out.append({"run_id": d.get("run_id"), "problem_id": d.get("problem_id"),
                        "status": d.get("status"), "phase": d.get("phase"),
                        "elapsed": d.get("elapsed")})
    return out[:50]


def load_run(rid):
    p = os.path.join(RUNS, rid, "run.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        # 运行中的题，elapsed 用实时值，否则长调用期间界面上的计时会冻住
        run = ACTIVE.get(rid)
        if run is not None and d.get("status") == "running":
            import time as _t
            d["elapsed"] = round(_t.time() - run.started, 1)
        return d
    if rid in ACTIVE:
        return {"run_id": rid, "status": "pending", "phase": "", "logs": []}
    raise FileNotFoundError("没有这个运行")


def list_tree(rid):
    run = load_run(rid)
    base = os.path.join(PROBLEMS, run["problem_id"])
    out = []
    if not os.path.isdir(base):
        return out
    for b, dirs, names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in ("build", "__pycache__"))
        for n in sorted(names):
            if n.endswith((".pyc", ".exe")):
                continue
            full = os.path.join(b, n)
            rel = os.path.relpath(full, base).replace("\\", "/")
            out.append({"path": rel, "size": os.path.getsize(full)})
    return out


def mark_orphans():
    """服务重启后，把上次没跑完、还标着 running 的运行标成中断。

    否则历史列表里会永远挂着一条"运行中"。
    """
    if not os.path.isdir(RUNS):
        return
    for name in os.listdir(RUNS):
        p = os.path.join(RUNS, name, "run.json")
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        if d.get("status") in ("running", "pending"):
            d["status"] = "failed"
            d["error"] = "服务重启，这次运行被中断"
            d.setdefault("logs", []).append(
                {"t": d.get("elapsed", 0), "level": "bad", "msg": "服务重启，运行被中断"})
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    os.makedirs(RUNS, exist_ok=True)
    mark_orphans()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"命题流水线已启动： http://{a.host}:{a.port}")
    print(f"题目目录：{PROBLEMS}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
