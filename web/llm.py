# -*- coding: utf-8 -*-
"""LLM 客户端：OpenAI 兼容协议 + 一个 mock 提供方。

三个槽位各自独立配置 base_url / api_key / model，所以你可以混用不同厂商。
base_url 以 `mock` 开头时不发网络请求，直接从 web/mock/ 回放固定内容——
用来在没有 API key 的情况下把整条流水线跑通（也是自检手段）。
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MOCK_DIR = os.path.join(HERE, "mock")


class LLMError(Exception):
    pass


class HTTPFail(Exception):
    def __init__(self, code, text):
        super().__init__(f"HTTP {code}")
        self.code = code
        self.text = text


# 已知不接受 temperature / max_tokens 的 (base_url, model)，命中后不再发送
_NO_TEMP = set()
_NO_MAXTOK = set()
MAX_TOKENS = 32768
# 没有任何服务商支持这么大的输出，填这么大只会被 400 拒绝，
# 然后被我们剥掉参数、退回服务商默认值（往往只有 4096），反而更容易截断
MAX_TOKENS_CAP = 65536


def _max_tokens(cfg):
    try:
        v = int(cfg.get("max_tokens") or 0)
    except Exception:
        v = 0
    if v <= 0:
        return MAX_TOKENS
    return min(v, MAX_TOKENS_CAP)


def _apply_extra(body, cfg):
    """把用户在槽位里填的额外参数并进请求体。

    只做 setdefault：不允许覆盖 model / messages / stream 这些必须由程序控制的键。
    返回实际加进去的键，便于 400 时精确剥掉。
    """
    extra = cfg.get("extra") or {}
    if not isinstance(extra, dict):
        return []
    added = []
    for k, v in extra.items():
        if k in ("model", "messages", "stream", "temperature", "max_tokens"):
            continue
        body[k] = v
        added.append(k)
    return added


def _drop_extra(body, keys):
    for k in keys:
        body.pop(k, None)


def _compat(body, base, model):
    if (base, model) in _NO_TEMP:
        body.pop("temperature", None)
    if (base, model) in _NO_MAXTOK:
        body.pop("max_tokens", None)
    return body


def _downgrade(body, base, model, text, extra_keys=()):
    """从 400 的错误信息里判断该砍哪个参数；返回 True 表示已改，可以重试。"""
    low = text.lower()
    if "temperature" in low and "temperature" in body:
        _NO_TEMP.add((base, model))
        body.pop("temperature", None)
        return True
    if "max_tokens" in low and "max_tokens" in body:
        _NO_MAXTOK.add((base, model))
        body.pop("max_tokens", None)
        return True
    # 用户自定义的额外参数被拒（比如某些服务商不认 thinking）→ 整个去掉
    for k in extra_keys:
        if k.lower() in low and k in body:
            _drop_extra(body, extra_keys)
            return True
    if extra_keys and any(k in body for k in extra_keys):
        _drop_extra(body, extra_keys)
        return True
    return False


def _post(url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise HTTPFail(e.code, e.read().decode("utf-8", "replace")[:600])
    except Exception as e:
        raise LLMError(str(e))


# ---------------------------------------------------------------- 解析输出
FILE_RE = re.compile(r"^===\s*FILE:\s*(.+?)\s*===\s*$", re.MULTILINE)
# 模型有时会自作主张加一行收尾标记（===END===、===EOF=== 之类），
# 留着会让 .py/.cpp 语法报错
TAIL_MARK = re.compile(r"^={3,}\s*[A-Za-z_ ]*\s*={3,}$")


def parse_files(text):
    """把 `===FILE: name===` 分块解析成 {name: content}。

    比让模型输出 markdown 代码块可靠得多：名字在分隔符里，不会被 ``` 干扰。
    """
    out = {}
    parts = FILE_RE.split(text)
    # parts = [前言, name1, body1, name2, body2, ...]
    for i in range(1, len(parts) - 1, 2):
        name = parts[i].strip().strip("`'\"")
        body = parts[i + 1]
        # 去掉正文首尾多余空行，但保留内部缩进
        body = body.strip("\n")
        # 如果模型还是套了 markdown 代码块，剥掉一层
        m = re.match(r"^```[a-zA-Z0-9_+-]*\n(.*)\n```\s*$", body, re.DOTALL)
        if m:
            body = m.group(1)
        # 去掉末尾的伪造收尾标记
        lines = body.split("\n")
        while lines and TAIL_MARK.match(lines[-1].strip()):
            lines.pop()
        out[name] = "\n".join(lines).rstrip() + "\n"
    return out


def _escape_repair(s):
    """把 JSON 字符串里非法的反斜杠转义补成合法的。

    模型写 LaTeX（\\le、\\times）时习惯用单反斜杠，塞进 JSON 就是非法转义，
    json.loads 会直接抛 "Invalid \\escape"。这里只动非法的那些，合法转义不碰。
    """
    return re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', s)


def extract_json(text):
    """从回复里抓第一段 JSON 对象。"""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    else:
        i = text.find("{")
        j = text.rfind("}")
        if i >= 0 and j > i:
            text = text[i:j + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 最常见的原因：LaTeX 里的裸反斜杠。修一次再试。
        return json.loads(_escape_repair(text))


# ---------------------------------------------------------------- 调用
def chat(cfg, messages, timeout=300):
    base = (cfg.get("base_url") or "").strip().rstrip("/")
    if not base:
        raise LLMError("没有配置 base_url")
    if base.startswith("mock"):
        return _mock(messages)

    url = base
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    model = cfg.get("model") or "gpt-4o-mini"
    body = {
        "model": model,
        "messages": messages,
        "temperature": float(cfg.get("temperature", 0.3)),
        "max_tokens": _max_tokens(cfg),
    }
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = "Bearer " + cfg["api_key"]
    _compat(body, base, model)
    extra_keys = _apply_extra(body, cfg)

    # 推理类模型（kimi k 系列、o1 系、seed-thinking 等）只接受 temperature=1；
    # 部分服务商不认 max_tokens。被拒一次就记下来，后面不再发。
    last = None
    for _ in range(3):
        try:
            raw = _post(url, body, headers, timeout)
            break
        except HTTPFail as e:
            last = e
            if e.code == 400 and _downgrade(body, base, model, e.text, extra_keys):
                continue
            raise LLMError(f"{cfg.get('name', '?')} HTTP {e.code}: {e.text}")
    else:
        raise LLMError(f"{cfg.get('name', '?')} HTTP {last.code}: {last.text}")
    try:
        data = json.loads(raw)
        # 有些服务商会在 content 里返回 null（全部内容跑到 reasoning_content 去了）
        return data["choices"][0]["message"].get("content") or ""
    except Exception:
        raise LLMError("返回格式不认识：" + raw[:500])


# ---------------------------------------------------------------- 流式
def chat_stream(cfg, messages, on_chunk, timeout=75, on_reasoning=None):
    """边收边回调。

    on_reasoning 收思考过程（reasoning_content），on_chunk 收正式输出（content）。
    推理模型会把大部分时间花在前者上，不显示出来的话界面就是干等。
    timeout 是**单次读超时**：超过这么久没有新数据就认定流式挂了，
    交给上层回退非流式。
    """
    base = (cfg.get("base_url") or "").strip().rstrip("/")
    if not base:
        raise LLMError("没有配置 base_url")
    if base.startswith("mock"):
        text = _mock(messages)
        for i in range(0, len(text), 160):
            on_chunk(text[i:i + 160])
        return text
    url = base if base.endswith("/chat/completions") else base + "/chat/completions"
    model = cfg.get("model") or "gpt-4o-mini"
    body = {"model": model, "messages": messages, "stream": True,
            "temperature": float(cfg.get("temperature", 0.3)),
            "max_tokens": _max_tokens(cfg)}
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = "Bearer " + cfg["api_key"]
    _compat(body, base, model)
    extra_keys = _apply_extra(body, cfg)

    for _ in range(3):
        try:
            return _stream_once(url, body, headers, timeout, on_chunk, on_reasoning)
        except HTTPFail as e:
            low = e.text.lower()
            if e.code == 400 and _downgrade(body, base, model, e.text, extra_keys):
                continue
            if e.code == 400 and "stream" in low:
                # 该服务商不支持流式，退化成一次性返回
                text = chat(cfg, messages, timeout)
                on_chunk(text)
                return text
            raise LLMError(f"{cfg.get('name', '?')} HTTP {e.code}: {e.text}")
    raise LLMError(f"{cfg.get('name', '?')} 参数降级后仍然失败")


def _stream_once(url, body, headers, timeout, on_chunk, on_reasoning=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        raise HTTPFail(e.code, e.read().decode("utf-8", "replace")[:600])
    except Exception as e:
        raise LLMError(str(e))
    parts = []
    last = time.time()
    chunks = 0
    try:
        with resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                last = time.time()
                chunks += 1
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                try:
                    delta = obj["choices"][0].get("delta", {}) or {}
                except Exception:
                    delta = {}
                # 推理模型把思考过程放在 reasoning_content（有的叫 reasoning）
                think = delta.get("reasoning_content") or delta.get("reasoning") or ""
                if think and on_reasoning:
                    on_reasoning(think)
                piece = delta.get("content") or ""
                if piece:
                    parts.append(piece)
                    on_chunk(piece)
    except Exception as e:
        # 上层用 Degenerate 主动中止（检测到重复输出），不能当成普通断流去回退
        if type(e).__name__ == "Degenerate":
            raise
        # 读取中途超时/断流必须转成 LLMError，否则上层的"回退非流式"接不住，
        # 会直接把这轮调用判死。
        idle = time.time() - last
        raise LLMError(f"流式读取中断：{e}（最后 {idle:.0f} 秒没有新数据，"
                       f"之前已收到 {chunks} 个分片）")
    return "".join(parts)


# ---------------------------------------------------------------- mock
def _slot_of(messages):
    blob = "\n".join(m.get("content", "") for m in messages)
    m = re.search(r"\[SLOT:([a-z_]+)\]", blob)
    return m.group(1) if m else None


def _mock(messages):
    slot = _slot_of(messages)
    if not slot:
        raise LLMError("mock 提供方需要一个 [SLOT:xxx] 标记")
    manifest = os.path.join(MOCK_DIR, "manifest.json")
    if not os.path.exists(manifest):
        raise LLMError("mock 缺少 manifest.json")
    with open(manifest, "r", encoding="utf-8") as f:
        table = json.load(f)
    entries = table.get(slot)
    if not entries:
        raise LLMError(f"mock 没有定义槽位 {slot}")
    root = os.path.dirname(HERE)
    blocks = []
    for src, dst in entries:
        path = src if os.path.isabs(src) else os.path.join(root, src)
        with open(path, "r", encoding="utf-8") as f:
            body = f.read()
        blocks.append(f"===FILE: {dst}===\n{body.rstrip()}\n")
    return "\n".join(blocks)
