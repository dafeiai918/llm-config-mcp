# llm-config-mcp · 客户端配置生成 MCP

**让 AI 直接说：「Cherry Studio 这么填…… NextChat 那么填…… 你的 404 是因为 /v1 多了。」**

零依赖 · 单文件 · stdio MCP 服务器 · 18 种客户端 · 中文

---

## 它让 AI 能做什么

> 「帮我配置 Cherry Studio」
> → AI 调用 `generate_config`，给出完整填写步骤

> 「支持哪些客户端？」
> → AI 调用 `list_clients`，列出 18 种及各自的 `/v1` 要求

> 「我的客户端报 404」
> → AI 调用 `troubleshoot`，直接告诉你是 `/v1` 多了还是少了

> 「把全部客户端的配置都给我」
> → AI 调用 `generate_all`，一次生成 18 份

---

## 提供的工具

| 工具 | 作用 |
|---|---|
| `list_clients` | 列出 18 种支持的客户端 + 各自地址格式要求 |
| `generate_config` | 生成指定客户端的配置步骤 |
| `generate_all` | 一次生成全部 |
| `check_v1` | 查某客户端要不要带 `/v1` |
| `troubleshoot` | 按报错诊断：404 / 401 / 403 / 超时 / 模型不存在 |

---

## 支持的客户端

| 分类 | 客户端 |
|---|---|
| 桌面 | Cherry Studio、NextChat、Chatbox、Jan、AnythingLLM、SillyTavern |
| 自部署 | Open WebUI、LobeChat、LibreChat、Dify |
| 编程插件 | Continue (VSCode)、Cline (VSCode) |
| 命令行 | Aider、Codex CLI、OpenCode |
| 通用 | `.env`、cURL、Python SDK |

---

## 安装

```json
{
  "mcpServers": {
    "llm-config-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/dafeiai918/llm-config-mcp", "llm-config-mcp"]
    }
  }
}
```

或本地文件：

```json
{
  "mcpServers": {
    "llm-config-mcp": {
      "command": "python",
      "args": ["/绝对路径/llm-config-mcp/llm_config_mcp.py"]
    }
  }
}
```

零第三方依赖，Python 3.9+。

---

## 为什么这个 MCP 有用

配置 AI 客户端最常见的三个坑：

| 坑 | 后果 | 本工具怎么解决 |
|---|---|---|
| **`/v1` 带不带搞不清** | Cherry Studio 带了 `/v1` 直接连不上 | `check_v1` + 配置里明确标注 |
| **Chatbox 域名路径要分开填** | 填重复导致 404 | 模板里明确分开写 |
| **Codex CLI 整体覆盖 config.toml** | 丢掉已有的 projects / mcp_servers | 模板明确写「不要整体覆盖」 |

---

## 安全

- 只生成配置文本，**不会修改你本机的任何配置文件**
- 不做网络请求，密钥不会离开你的机器

---

## 相关项目

| 项目 | 用途 |
|---|---|
| [relay-converter](https://github.com/dafeiai918/relay-converter) | 同能力的命令行版（可导出配置文件） |
| [OneClickRelay](https://github.com/dafeiai918/oneclickrelay) | 一键自动写入 60+ 客户端（图形界面） |
| [relay-mcp](https://github.com/dafeiai918/relay-mcp) | 中转站账户管理 MCP |
| [awesome-relay](https://github.com/dafeiai918/awesome-relay) | 中转站与客户端精选导航 |

---

## License

MIT
