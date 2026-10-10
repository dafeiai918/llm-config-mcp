# -*- coding: utf-8 -*-
"""llm-config-mcp 测试：协议 + 全部模板，不发外网"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import llm_config_mcp as lc  # noqa: E402

CTX = {"base_url": "https://api.example.com/v1", "api_key": "sk-test123456",
       "model": "gpt-4o-mini"}


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.sent = []
        self.server = lc.MCPServer("t", "1.0", lc.TOOLS)
        self.server._send = lambda m: self.sent.append(m)

    def _call(self, method, **kw):
        msg = {"jsonrpc": "2.0", "id": 1, "method": method}
        if kw:
            msg["params"] = kw
        self.server.handle(msg)
        return self.sent[-1]

    def test_initialize(self):
        self.assertEqual(self._call("initialize")["result"]["serverInfo"]["name"], "t")

    def test_tools_list(self):
        names = [t["name"] for t in self._call("tools/list")["result"]["tools"]]
        self.assertEqual(sorted(names),
                         ["check_v1", "generate_all", "generate_config",
                          "list_clients", "troubleshoot"])

    def test_missing_args_iserror(self):
        out = self._call("tools/call", name="generate_config", arguments={"client": "cherry"})
        self.assertTrue(out["result"]["isError"])


class TemplateTest(unittest.TestCase):
    def test_split_base(self):
        self.assertEqual(lc.split_base("https://a.com/v1"), ("https://a.com", "https://a.com/v1"))
        self.assertEqual(lc.split_base("https://a.com"), ("https://a.com", "https://a.com/v1"))
        self.assertEqual(lc.split_base("https://a.com/v1/"), ("https://a.com", "https://a.com/v1"))

    def test_all_templates_render_with_key(self):
        for tid, (name, render) in lc.TARGETS.items():
            with self.subTest(client=tid):
                ctx = {"root": "https://api.example.com", "full": "https://api.example.com/v1",
                       "key": "sk-test123456", "model": "gpt-4o-mini"}
                text = render(ctx)
                self.assertGreater(len(text), 10)
                self.assertIn("sk-test123456", text)

    def test_cherry_no_v1(self):
        text = lc.tool_generate_config({**CTX, "client": "cherry"})
        self.assertIn("https://api.example.com ", text)
        self.assertIn("不要带 /v1", text)

    def test_nextchat_has_v1(self):
        text = lc.tool_generate_config({**CTX, "client": "nextchat"})
        self.assertIn("https://api.example.com/v1", text)

    def test_codex_warns_about_overwrite(self):
        text = lc.tool_generate_config({**CTX, "client": "codex"})
        self.assertIn("不要整体覆盖", text)

    def test_list_clients_count(self):
        self.assertIn("18 种", lc.tool_list_clients({}))

    def test_unknown_client_suggests(self):
        text = lc.tool_generate_config({**CTX, "client": "cherrystudio"})
        self.assertIn("cherry", text)

    def test_unknown_client_no_suggestion(self):
        text = lc.tool_generate_config({**CTX, "client": "zzzz"})
        self.assertIn("未知客户端", text)

    def test_generate_all(self):
        text = lc.tool_generate_all(CTX)
        self.assertIn("地址(接口)", text)
        self.assertEqual(text.count("─" * 46), len(lc.TARGETS))
        for tid, (_, render) in lc.TARGETS.items():
            ctx = {"root": "https://api.example.com", "full": "https://api.example.com/v1",
                   "key": "sk-test123456", "model": "gpt-4o-mini"}
            self.assertIn(render(ctx).splitlines()[0], text)

    def test_check_v1_rules(self):
        self.assertIn("不要带 /v1", lc.tool_check_v1({"client": "cherry"}))
        self.assertIn("要带 /v1", lc.tool_check_v1({"client": "nextchat"}))
        self.assertIn("分开填", lc.tool_check_v1({"client": "chatbox"}))
        self.assertIn("未知客户端", lc.tool_check_v1({"client": "zzz"}))

    def test_troubleshoot_mapping(self):
        self.assertIn("404", lc.tool_troubleshoot({"error": "HTTP 404"}))
        self.assertIn("401", lc.tool_troubleshoot({"error": "Unauthorized 401"}))
        self.assertIn("超时", lc.tool_troubleshoot({"error": "connect timeout"}))
        self.assertIn("模型", lc.tool_troubleshoot({"error": "model not found"}))
        self.assertIn("常见对照", lc.tool_troubleshoot({"error": "无法描述"}))

    def test_v1_rule_covers_all_targets(self):
        for tid in lc.TARGETS:
            self.assertIn(tid, lc.V1_RULE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
