> 本文描述的是较早的版本，最新内容请以[英文 README](README.md)和[项目介绍页](https://teddashh.github.io/clawd-lobster/)为准。

[English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

# Clawd-Lobster

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/github/license/teddashh/clawd-lobster)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Runtime](https://img.shields.io/badge/RAM-25MB-orange)

<p align="center">
<strong>你终究要用 Claude Code 的，为什么不一开始就选最好的体验？</strong><br>
<strong>反正你迟早要用 Claude Code，何不从最好的体验开始？</strong>
</p>

---

## 问题在哪

你看过那些 AI agent 框架。可能也试过几个。以下是实际会发生的事：

**问题一：Claude Code 很强，但你得一直盯着它。**
每次 session 都从零开始。它忘了昨天学到什么。你复制粘贴上下文，重新解释架构，重新描述规范。你就是内存。你就是管理者。你就是瓶颈。

**问题二：AI Agent 框架 demo 很炫，实际体验很痛。**
三十万行代码。自定义 adapter。配置文件比你的项目还长。底层模型一更新就挂。你花在维护框架的时间比开发产品还多。

**问题三：灰色地带。**
自建的 agent 循环绕过安全机制。API 按 token 计费毫无上限。东拼西凑的 Frankenstein 技术栈，你搞不清楚到底是你在用工具，还是工具在用你。

## 答案

Clawd-Lobster 不是要取代 Claude Code。它让 Claude Code 学会**记忆、规划、审查、构建、进化**，而且只用 Anthropic 官方工具。

- **100% Claude Code CLI + Agent SDK。** 没有包装层，没有自定义 agent 循环，没有灰色地带。跑在你现有的 Claude 订阅上。不用额外 API 费用。
- **约 9,000 行代码。** 不是 300,000 行，一个人也能看完。Claude Code 更新时，新功能直接到手。不用改写，不会挂掉。
- **5 分钟上手。** 开浏览器。点两下。搞定。不用 API key，不用 Docker，不用 YAML 博士学位。

```
  You describe what you want
       |
       v
  Claude asks smart questions (Discovery)
       |
       v
  +-------------------------------------+
  |         SPEC SQUAD                   |
  |                                      |
  |  [A] Architect    writes the spec    |
  |  [R] Reviewer     challenges it      |
  |  [C] Coder        builds it          |
  |  [T] Tester       verifies it        |
  |                                      |
  |  Each is a separate Claude session.  |
  |  The Reviewer has never seen the     |
  |  Architect's prompt.                 |
  |  That's why it catches real bugs.    |
  +-------------------------------------+
       |
       v
  Reviewed, tested, working code.
```

---

## 快速开始

### 所有人适用（Web UI）

```bash
git clone https://github.com/teddashh/clawd-lobster
cd clawd-lobster
pip install -e .
clawd-lobster serve
```

浏览器打开。安装向导带你走完一切。

### 给终端控

```bash
clawd-lobster setup        # 终端引导安装
clawd-lobster squad start  # 在终端里跑 Spec Squad
```

### 传统安装（高级用户）

```powershell
# Windows
.\install.ps1

# macOS / Linux
chmod +x install.sh && ./install.sh
```

---

## 你会得到什么

### 1. Spec Squad：你的 AI 开发团队

你描述你要什么。四个 Claude session 搞定剩下的。

**Architect** 写出一份包含可测试需求的完整规格书。**Reviewer**（一个完全独立、从未看过 Architect 指令的 Claude session）把它拆开来挑毛病。他们反复来回直到 Reviewer 批准，最多五轮。如果第五轮后 Reviewer 仍未批准，规格书还是会被批准，让流程继续，但会记录为强制批准：`.spec-squad.json` 写的是 `"approval": "round_limit"`，而不是 `"reviewer"`，回合记录里会多一条 `FORCED_APPROVAL`，终端和网页界面也都会注明这是轮数上限造成的批准。然后 **Coder** 严格按规格书来盖。**Tester** 验证每一条需求。

这不是花架子。测试中，Reviewer 在第一份规格书就找到 11 个真实 bug，都是自我验证清单永远抓不到的问题。返回类型冲突、API 不一致、不可能的 Gherkin 场景、包不兼容。

**为什么有效：** 每个 agent 跑在隔离的上下文里。Reviewer 不会受 Architect 的推理影响。Tester 不知道 Coder 走了什么捷径。独立的脑子找出独立的问题。

两种界面，同一个引擎：
- **Web：** 在浏览器跟 Claude 聊，然后在实时 dashboard 上看 agent 干活
- **终端：** Claude 在终端问你问题，agent 跑起来时实时显示进度

### 2. 不会忘记的脑子：Thin Ledger

两层协作。不用向量数据库。不需要云端。

| 层 | 内容 | 角色 |
|-----|------|------|
| **SQLite (The Ledger)** | 决策、TODO、审计日志、显著性分数、provenance | 运营真相：快速、结构化、可查询 |
| **Git Wiki (The Library)** | 交叉引用的 markdown 页面、索引、日志、来源 | 编译后的知识库：人类可读、Git 同步 |
| **Oracle Vector DB (The Vault)** | All knowledge vectorized + cross-machine semantic search | Deep recall: find anything you have ever discussed, across all machines |

每笔知识记录都带 **provenance**：谁写的、哪个 agent、信心分数、生命周期状态（raw → synthesized → accepted → superseded）。没有匿名事实。

**三个操作保持它的健康：**
- **INGEST**：新信息变成带引用的 wiki 页面
- **QUERY**：搜索两层、引用来源。有价值的答案会写回 wiki。
- **LINT**：定期健康检查，找出矛盾、过时声明、孤立页面、坏链接

**修正工作流：** Agent 不能直接编辑 wiki 页面。它们通过 `memory_propose_correction` 提出修正，建立审查队列。有争议的声明会被解决，不会被静默覆盖。

重要的想法浮上来。噪音沉下去。有用的技能被强化。过时的知识自然衰减。你完全不用管，全部自动。

*架构吸收自 [MemPalace](https://github.com/milla-jovovich/mempalace)（空间结构）和 [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)（INGEST/QUERY/LINT）。不安装任何依赖包，只用概念。*

### 3. 永远在线

合上笔记本。Clawd-Lobster 继续干活。

heartbeat 用的是你操作系统的调度器（Task Scheduler / cron / launchd），不是自定义 daemon，不是 polling 循环，不是烧 token 的后台进程。Session 挂了就带着完整上下文自动复活。不用盯。

### 4. 所有机器，一个脑子

GitHub 是控制面。Git 是协议。

机器 A 学到一个模式。它同步到你的私有 Hub。机器 B 立刻继承。新机器？`install.ps1`，「Join Hub」，粘贴网址，2 分钟，完全上线。

### 5. 自我进化

完成复杂工作后，系统会提取可重用的模式，存成学到的技能。下次遇到类似任务，它记得上次怎么解决的。

技能有效能分数。验证过的模式被强化。过时的技能自然衰减。系统越用越聪明。这不是魔法，是因为它把有效的方法写下来了。

---

## Dashboard

`clawd-lobster serve` 在 `localhost:3333` 打开常驻 web dashboard。

**新手引导（Skill Parade）**：Agent 引导式体验。网页显示互动式技能卡片；Claude Code 在终端用对话方式带你设置。一起走过语言、认证、workspace，然后逐一设置每个 skill。[完整指南 →](docs/onboarding-guide.html)

**Workspaces**：所有项目一目了然。状态、规格书进度、内存大小、最后活动时间。

**Skills（3 分页）**：MCP 服务器、Prompt 模式、Cron 任务。配置、启用/停用、健康检查。

**API 密钥**：管理 Claude、GitHub、Codex、Gemini、Oracle、Odoo 的认证。遮罩显示，逐项健康探测。

**Spec Squad**：跟 Claude 聊天厘清需求。在实时 dashboard 上看四个 agent 工作，有阶段时间轴和对话历程。

### Agent 引导式安装（Escape Room）

这不是传统安装程序。网页 dashboard 和 Claude Code 是**共同驾驶**：

```
网页（视觉层）         +     Claude Code（对话层）
显示技能卡片                 解释每个技能在做什么
显示设置进度                 回答你的问题
显示配置表单                 执行安装指令
实时更新                     读取状态，推进流程
```

---

## Skills

14 个技能，3 种类型。每个只做好一件事。点名称看完整文档。

### [memory-server](skills/memory-server/README.md)：根基
28 个 MCP 工具，跨 session 持久记忆。4 层架构，从即时本地缓存到云端同步。显著性引擎自动浮现重要知识、让噪音沉淀。支持 CJK token 估算。这就是让 Claude Code 不再失忆的 skill。

### [spec](skills/spec/README.md)：从想法到代码
引导式 workspace 创建、OpenSpec 文档生成（3W1H）、Spec Squad 多 agent 流水线。Discovery 访谈提取你的需求。Architect 撰写含 Gherkin 场景的可测试规格书。Reviewer 把它拆开来挑。Coder 按契约实现。Tester 逐条验证。终端或 Web 皆可。

### [evolve](skills/evolve/README.md)：自我精进
每 2 小时自动执行。扫描已完成的工作，提取可重用模式，存成学到的技能。技能有效能分数：验证过的模式被强化，过时的自然衰减。你的 agent 越用越锐利。不需任何配置。

### [absorb](skills/absorb/README.md)：知识吸收
指向一个 GitHub repo、本地文件夹或网址。它读完整份 codebase，提取架构决策、规范和模式，然后存成可搜索的知识。适合加入现有项目或研究参考实现时使用。

### [heartbeat](skills/heartbeat/README.md)：永远在线
操作系统原生保活（Task Scheduler / cron / launchd）。每 30 分钟检查一次。挂掉的 session 通过 `claude --resume` 带着完整上下文复活。没有自定义 daemon，没有 polling 循环，不烧 token。合上笔记本，你的 agent 继续干活。

### [migrate](skills/migrate/README.md)：一次性导入
检测现有的 AI 设置（`~/.claude/`、`~/.openclaw/`、`~/.hermes/`、`~/Documents/claude-setup/`）并导入记忆、配置和知识。上线时跑一次，之后不用再跑。

### [codex-bridge](skills/codex-bridge/README.md)：The Worker
把大量工作委派给 OpenAI Codex（跑在你的 ChatGPT Plus 上）。当**工人**用（并行任务、样板代码、测试生成）或当**评审**用（对抗式安全审查、架构辩论、code review）。Claude 自行判断何时委派。也能通过 AGENTS.md 把 Claude 的知识同步给 Codex。

### [gemini-bridge](skills/gemini-bridge/README.md)：The Consultant
调用 Google Gemini 获取不同观点。适合在你**不确定**时使用（事实核查、研究验证）、面对**复杂决策**时（架构取舍、技术栈选择）、或需要来自独立大脑的**安全审查**。支持三方辩论：Claude 形成观点 → Codex 审查 → Gemini 验证 → 达成共识。

### [connect-odoo](skills/connect-odoo/README.md)：ERP 集成
通过 XML-RPC + MCP 双向连接 Odoo ERP。6 个专用工具读写 Odoo 数据。实时 polling 检测变更。适合 AI 工作流需要与业务流程交互时使用。

### [notebooklm-bridge](skills/notebooklm-bridge/README.md)：文档生成
自动将 workspace 文档同步到 Google NotebookLM。从你的 codebase 文档生成幻灯片、信息图、podcast 和报告。内置水印移除：多页用页码盖章、单页用日期盖章。全页面风格一致。水印移除默认关闭（`auto_remove_watermark: false`）。注意：移除 NotebookLM 水印可能与 Google 的条款冲突，启用前请先查看 NotebookLM 的条款。

---

每个 skill 都有**触发描述**（Claude 知道何时启动）、**Gotchas 区块**（常见错误要避免）、和**动态 `!command` 注入**（加载时的即时上下文）。

---

## 架构

```
Skills (the what)      ->  14 skills with manifests (skill.json), instructions, gotchas
Tools (the how)        ->  27 MCP tools + Claude Code native tools + 22 onboarding APIs
Hooks (the when)       ->  OS scheduler, git hooks, PostToolUse, Stop hooks
Memory (the brain)     ->  SQLite Ledger + Git Wiki + Oracle Vault (4-layer)
Operations (the cycle) ->  INGEST / QUERY / LINT (continuous knowledge lifecycle)
Dashboard (the eyes)   ->  Web UI at localhost:3333 (Skill Parade + 3-tab Skills + Keys)
```

**站在巨人肩膀上。** Clawd-Lobster 不重建 Claude Code。它用 Claude Code 原生的扩展点（MCP servers、CLAUDE.md、hooks、settings.json），完全照 Anthropic 的设计走。Claude Code 出新功能，你直接受益。模型进步，你的 agent 跟着进步。零 adapter 代码。

```
Disk: ~2 MB    (code + configs)
RAM:  ~25 MB    (MCP server only)
CPU:  0% idle   (OS scheduler, not polling)
LOC:  ~25,000    (not 300,000)
```

完整文件树和运行时细节，请见 [ARCHITECTURE.md](ARCHITECTURE.md)。

---

## CLI 参考

| Command | What It Does |
|---------|-------------|
| `clawd-lobster serve` | Start web dashboard (localhost:3333) |
| `clawd-lobster setup` | Terminal onboarding wizard |
| `clawd-lobster workspace create <name>` | Create a new workspace |
| `clawd-lobster squad start` | Run Spec Squad in terminal |
| `clawd-lobster status` | Show system health |

---

## 多机器设置

```
  clawd-lobster (this repo -- the generator)
       |
       |  install once
       v
  clawd-yourname (your private Hub on GitHub)
       |
       +-- Machine A -- skills + memory + heartbeat
       +-- Machine B -- skills + memory + heartbeat
       +-- Machine C -- skills + memory + heartbeat
            |
            All connected. All sharing knowledge.
```

第一台机器创建 Hub。之后每台 2 分钟加入。

---

## 环境需求

- Python 3.10+
- Claude Code CLI ([install](https://claude.ai/code))
- Git 2.x+
- Node.js 18+ (optional, for Codex Bridge)
- GitHub account (for Hub sync)

---

## 比较

|  | Heavyweight Frameworks | Raw Claude Code | Clawd-Lobster |
|--|----------------------|----------------|---------------|
| Codebase | 300K+ lines | 0 (built-in) | ~25,000 lines |
| Setup | Hours/days | 0 | 5 minutes |
| Memory | Session-only | Session-only | 4-layer persistent |
| Multi-machine | Usually none | None | Git sync + Hub |
| Model updates | Breaks adapters | Automatic | Automatic |
| Token cost | API per-token | Subscription | Subscription |
| Multi-agent review | Some | None | Spec Squad (adversarial) |
| Self-evolution | None | None | Learned skills + salience |

---

## 设计哲学

**1. 放大，不是重建。**
Claude Code 是世上最强的 coding agent。我们给它装上神经系统。我们不重建大脑。

**2. 巨人长高，你也长高。**
每次 Claude Code 更新都让你的 Clawd-Lobster 更强。零迁移，零改写。

**3. 计划就是产品。**
Spec Squad 不是先写代码。它先写规格书，让对手来挑战，然后按规格书构建。计划就是契约。

---

## 贡献

欢迎 PR。贡献前请先读 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 许可

MIT，详见 [LICENSE](LICENSE)。
