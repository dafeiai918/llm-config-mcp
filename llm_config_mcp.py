#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llm-config-mcp · 客户端配置生成 MCP
让 AI 直接生成 19 种 AI 客户端接入任意 OpenAI 兼容站点的配置
零依赖 stdio MCP 服务器
"""
from __future__ import annotations

import json
import os
import sys

__version__ = "1.0.0"
PROTOCOL_VERSION = "2025-06-18"


# ================= MCP 内核 =================

class MCPServer:
    def __init__(self, name: str, version: str, tools: list):
        self.name, self.version, self.tools = name, version, tools

    def _send(self, msg: dict) -> None:
        sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def _result(self, id_, result) -> None:
        self._send({"jsonrpc": "2.0", "id": id_, "result": result})

    def _error(self, id_, code: int, message: str) -> None:
        self._send({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}})

    def handle(self, msg: dict) -> None:
        if not isinstance(msg, dict):
            return
        method, id_ = msg.get("method"), msg.get("id")
        if method == "initialize":
            self._result(id_, {"protocolVersion": PROTOCOL_VERSION,
                               "capabilities": {"tools": {"listChanged": False}},
                               "serverInfo": {"name": self.name, "version": self.version}})
        elif method in ("notifications/initialized", "initialized", "notifications/cancelled"):
            return
        elif method == "ping":
            self._result(id_, {})
        elif method == "tools/list":
            self._result(id_, {"tools": [
                {"name": t["name"], "description": t["description"],
                 "inputSchema": t.get("inputSchema") or {"type": "object", "properties": {}}}
                for t in self.tools]})
        elif method == "tools/call":
            params = msg.get("params") or {}
            tool = next((t for t in self.tools if t["name"] == params.get("name")), None)
            if tool is None:
                self._error(id_, -32602, f"未知工具: {params.get('name')}")
                return
            try:
                out = tool["handler"](params.get("arguments") or {})
                self._result(id_, {"content": [{"type": "text", "text": str(out)}], "isError": False})
            except Exception as exc:
                self._result(id_, {"content": [{"type": "text",
                                                "text": f"错误: {type(exc).__name__}: {exc}"}],
                                   "isError": True})
        elif id_ is not None:
            self._error(id_, -32601, f"不支持的方法: {method}")

    def serve(self) -> None:
        for raw in sys.stdin:
            raw = raw.strip()
            if not raw:
                continue
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            for item in (msg if isinstance(msg, list) else [msg]):
                self.handle(item)


# ================= 配置模板 =================

def split_base(url: str) -> tuple[str, str]:
    root = (url or "").strip().rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3].rstrip("/")
    return root, root + "/v1"


def t_cherry(c) -> str:
    return f"""[Cherry Studio] 设置 → 模型服务 → 添加提供商（类型 OpenAI）
  API 地址   {c['root']}          ← 不要带 /v1
  API 密钥   {c['key']}
  模型 ID    {c['model']}
点「检查」通过后保存。"""


def t_nextchat(c) -> str:
    return f"""[NextChat] 设置 → 自定义接口
  接口地址   {c['full']}
  API Key    {c['key']}
  模型名     {c['model']}"""


def t_chatbox(c) -> str:
    return f"""[Chatbox] 设置 → 模型 → 添加自定义提供方
  API 域名   {c['root']}
  API 路径   /v1/chat/completions
  API 密钥   {c['key']}
  模型名     {c['model']}"""


def t_jan(c) -> str:
    return f"""[Jan] 设置 → 模型 → 添加提供商（OpenAI 兼容）
  Base URL   {c['full']}
  API Key    {c['key']}
  模型 ID    {c['model']}"""


def t_openwebui(c) -> str:
    return f"""[Open WebUI] 管理员设置 → 连接 → OpenAI API
  URL        {c['full']}
  Key        {c['key']}
或环境变量：
  OPENAI_API_BASE_URL={c['full']}
  OPENAI_API_KEY={c['key']}"""


def t_lobechat(c) -> str:
    return f"""[LobeChat] 环境变量
  OPENAI_API_KEY={c['key']}
  OPENAI_PROXY_URL={c['full']}"""


def t_librechat(c) -> str:
    payload = {"version": 1, "endpoints": {"custom": [{
        "name": "Relay", "apiKey": c["key"], "baseURL": c["full"],
        "models": {"default": [c["model"]], "fetch": True}}]}}
    return "[LibreChat] 合并进 librechat.yaml：\n" + json.dumps(payload, ensure_ascii=False, indent=2)


def t_continue(c) -> str:
    payload = {"models": [{"title": "Relay", "provider": "openai", "model": c["model"],
                           "apiBase": c["full"], "apiKey": c["key"]}]}
    return "[Continue] 合并进 ~/.continue/config.json：\n" + json.dumps(
        payload, ensure_ascii=False, indent=2)


def t_cline(c) -> str:
    payload = {"cline.apiProvider": "openai", "cline.openAiBaseUrl": c["full"],
               "cline.openAiApiKey": c["key"], "cline.openAiModelId": c["model"]}
    return "[Cline] 合并进 VS Code settings.json：\n" + json.dumps(
        payload, ensure_ascii=False, indent=2)


def t_aider(c) -> str:
    return f"""[Aider] .env
  OPENAI_API_BASE={c['full']}
  OPENAI_API_KEY={c['key']}
用法：aider --model openai/{c['model']}"""


def t_codex(c) -> str:
    return f"""[Codex CLI] 合并进 ~/.codex/config.toml（不要整体覆盖！）
model = "{c['model']}"
model_provider = "relay"

[model_providers.relay]
name = "Relay"
base_url = "{c['full']}"
wire_api = "chat"
env_key = "RELAY_API_KEY"

同时设置环境变量 RELAY_API_KEY={c['key']}"""


def t_opencode(c) -> str:
    payload = {"provider": {"relay": {"npm": "@ai-sdk/openai-compatible",
                                      "options": {"baseURL": c["full"], "apiKey": c["key"]},
                                      "models": {c["model"]: {}}}}}
    return "[OpenCode] opencode.json：\n" + json.dumps(payload, ensure_ascii=False, indent=2)


def t_anythingllm(c) -> str:
    return f"""[AnythingLLM] 设置 → LLM 首选项 → Generic OpenAI
  Base URL   {c['full']}
  API Key    {c['key']}
  Chat Model {c['model']}"""


def t_sillytavern(c) -> str:
    return f"""[SillyTavern] 连接设置 → Chat Completion → Custom (OpenAI-compatible)
  Custom URL   {c['full']}
  API Key      {c['key']}
  模型名        {c['model']}"""


def t_env(c) -> str:
    return f"""[通用 .env]
  OPENAI_BASE_URL={c['full']}
  OPENAI_API_KEY={c['key']}
  OPENAI_MODEL={c['model']}"""


def t_curl(c) -> str:
    return f"""[cURL 测试]
curl {c['full']}/chat/completions \\
  -H "Authorization: Bearer {c['key']}" \\
  -H "Content-Type: application/json" \\
  -d '{{"model":"{c['model']}","messages":[{{"role":"user","content":"你好"}}]}}'"""


def t_python(c) -> str:
    return f"""[Python SDK]
from openai import OpenAI
client = OpenAI(base_url="{c['full']}", api_key="{c['key']}")
resp = client.chat.completions.create(model="{c['model']}",
    messages=[{{"role":"user","content":"你好"}}])
print(resp.choices[0].message.content)"""


def t_dify(c) -> str:
    return f"""[Dify] 设置 → 模型供应商 → OpenAI-API-compatible
  API Base URL   {c['full']}
  API Key        {c['key']}
  模型名称        {c['model']}
注：Dify 许可证禁止移除其前端 LOGO。"""


TARGETS = {
    "cherry": ("Cherry Studio", t_cherry),
    "nextchat": ("NextChat", t_nextchat),
    "chatbox": ("Chatbox", t_chatbox),
    "jan": ("Jan", t_jan),
    "openwebui": ("Open WebUI", t_openwebui),
    "lobechat": ("LobeChat", t_lobechat),
    "librechat": ("LibreChat", t_librechat),
    "dify": ("Dify", t_dify),
    "anythingllm": ("AnythingLLM", t_anythingllm),
    "sillytavern": ("SillyTavern", t_sillytavern),
    "continue": ("Continue (VSCode)", t_continue),
    "cline": ("Cline (VSCode)", t_cline),
    "aider": ("Aider", t_aider),
    "codex": ("Codex CLI", t_codex),
    "opencode": ("OpenCode", t_opencode),
    "env": ("通用 .env", t_env),
    "curl": ("cURL", t_curl),
    "python": ("Python SDK", t_python),
}

# 该客户端地址要不要带 /v1
V1_RULE = {
    "cherry": False, "nextchat": True, "chatbox": None, "jan": True,
    "openwebui": True, "lobechat": True, "librechat": True, "dify": True,
    "anythingllm": True, "sillytavern": True, "continue": True, "cline": True,
    "aider": True, "codex": True, "opencode": True, "env": True,
    "curl": True, "python": True,
}


# ================= 工具 =================

def _ctx(args: dict) -> dict:
    base = (args.get("base_url") or "").strip()
    key = (args.get("api_key") or "").strip()
    if not base or not key:
        raise ValueError("需要 base_url 和 api_key")
    root, full = split_base(base)
    return {"root": root, "full": full, "key": key,
            "model": (args.get("model") or "gpt-4o-mini").strip()}


def tool_list_clients(args: dict) -> str:
    lines = [f"支持 {len(TARGETS)} 种客户端：", ""]
    for tid, (name, _) in TARGETS.items():
        rule = V1_RULE.get(tid)
        tag = "不带 /v1" if rule is False else "带 /v1" if rule is True else "域名/路径分开填"
        lines.append(f"- {tid:<12} {name:<18} {tag}")
    lines += ["", "生成配置：generate_config，指定 client 和地址密钥。"]
    return "\n".join(lines)


def tool_generate_config(args: dict) -> str:
    ctx = _ctx(args)
    client = (args.get("client") or "").strip().lower()
    if client not in TARGETS:
        close = [k for k in TARGETS if client and (client in k or k in client)]
        hint = f"你是不是想用：{', '.join(close)}？" if close else "用 list_clients 看全部。"
        return f"未知客户端「{client}」。{hint}"
    name, render = TARGETS[client]
    return f"{name} 配置：\n\n{render(ctx)}"


def tool_generate_all(args: dict) -> str:
    ctx = _ctx(args)
    parts = [f"地址(接口) {ctx['full']}", f"地址(根)   {ctx['root']}",
             f"模型       {ctx['model']}", ""]
    for tid, (name, render) in TARGETS.items():
        parts.append("─" * 46)
        parts.append(render(ctx))
        parts.append("")
    return "\n".join(parts)


def tool_check_v1(args: dict) -> str:
    client = (args.get("client") or "").strip().lower()
    if client not in TARGETS:
        return f"未知客户端「{client}」。用 list_clients 看全部。"
    rule = V1_RULE.get(client)
    name = TARGETS[client][0]
    if rule is False:
        return (f"{name}：地址**不要带 /v1**。\n"
                f"填成 https://api.example.com 而不是 https://api.example.com/v1。\n"
                f"带了会连接失败——这是最常见的配置错误。")
    if rule is None:
        return (f"{name}：域名和路径**分开填**。\n"
                f"域名填 https://api.example.com，路径填 /v1/chat/completions，不要重复。")
    return f"{name}：地址**要带 /v1**，即 https://api.example.com/v1"


def tool_troubleshoot(args: dict) -> str:
    err = (args.get("error") or "").strip()
    text = err.lower()
    if "404" in text:
        return ("404 Not Found → 地址的 /v1 多了或少了。\n"
                "先确认客户端要不要带 /v1（用 check_v1 工具），"
                "再用 test_site 验证根地址和接口地址哪个能通。")
    if "401" in text or "unauthorized" in text:
        return ("401 Unauthorized → 密钥问题。\n"
                "检查：① 密钥是否复制完整（常见首尾空格）② 客户端里是否加了 Bearer 前缀"
                "（多数客户端只需填裸密钥）③ 密钥是否已过期/余额为 0。")
    if "403" in text or "forbidden" in text:
        return ("403 Forbidden → 有密钥但被拒绝。\n"
                "常见原因：该密钥没有此模型的权限、站点风控、或需要指定可用模型。")
    if "timeout" in text or "超时" in text or "connect" in text:
        return ("连接超时 → 网络或站点问题。\n"
                "① 先用 test_site 测站点本身能否访问 ② 检查是否开了代理/防火墙"
                " ③ 换网络试试 ④ 站点可能确实挂了。")
    if "model" in text or "模型" in text:
        return ("模型相关错误 → 模型名不对或该站没有这个模型。\n"
                "用 list_models 拉取站点真实可用的模型名，复制粘贴过去。")
    return ("请把完整报错发来。常见对照：\n"
            "  404 → /v1 多了或少了\n"
            "  401 → 密钥错误\n"
            "  403 → 无权限/风控\n"
            "  超时 → 网络或站点故障\n"
            "  模型不存在 → 用 list_models 查真实模型名")


TOOLS = [
    {"name": "list_clients",
     "description": "列出支持生成配置的所有 AI 客户端（19 种）。用户问「支持哪些客户端」时使用。",
     "inputSchema": {"type": "object", "properties": {}},
     "handler": tool_list_clients},
    {"name": "generate_config",
     "description": "生成某个 AI 客户端接入 OpenAI 兼容站点的配置。"
                    "用户说「帮我配置 Cherry Studio / NextChat / Cursor」时使用。",
     "inputSchema": {"type": "object", "properties": {
         "client": {"type": "string", "description": "客户端标识，如 cherry / nextchat / codex"},
         "base_url": {"type": "string", "description": "站点地址"},
         "api_key": {"type": "string", "description": "API 密钥"},
         "model": {"type": "string", "description": "模型名，默认 gpt-4o-mini"}},
         "required": ["client", "base_url", "api_key"]},
     "handler": tool_generate_config},
    {"name": "generate_all",
     "description": "一次生成全部 19 种客户端的配置。用户想一次性拿到所有格式时使用。",
     "inputSchema": {"type": "object", "properties": {
         "base_url": {"type": "string"}, "api_key": {"type": "string"},
         "model": {"type": "string"}}, "required": ["base_url", "api_key"]},
     "handler": tool_generate_all},
    {"name": "check_v1",
     "description": "查某个客户端的地址要不要带 /v1。用户配置后连不上时先查这个。",
     "inputSchema": {"type": "object", "properties": {
         "client": {"type": "string"}}, "required": ["client"]},
     "handler": tool_check_v1},
    {"name": "troubleshoot",
     "description": "根据报错信息诊断配置问题。用户说「客户端连不上」「报 404/401」时使用。",
     "inputSchema": {"type": "object", "properties": {
         "error": {"type": "string", "description": "报错原文或现象描述"}},
         "required": ["error"]},
     "handler": tool_troubleshoot},
]


def main() -> int:
    if os.name == "nt":
        try:
            sys.stdin.reconfigure(encoding="utf-8")
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    MCPServer("llm-config-mcp", __version__, TOOLS).serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
