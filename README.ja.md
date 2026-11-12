> この README は古い版の内容です。最新の情報は[英語版 README](README.md)と[プロジェクトページ](https://teddashh.github.io/clawd-lobster/)をご覧ください。

[English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

# Clawd-Lobster

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/github/license/teddashh/clawd-lobster)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Runtime](https://img.shields.io/badge/RAM-25MB-orange)

<p align="center">
<strong>你終究要用 Claude Code 的，為什麼不一開始就選最好的體驗？</strong><br>
<strong>You'll end up using Claude Code anyway, so why not start with the best experience?</strong><br>
<strong>どうせ最後は Claude Code を使うことになる。なら最初から最高の体験を選びませんか？</strong>
</p>

---

## 問題

AI エージェントフレームワーク、見たことありますよね。いくつか試したかもしれません。実際に何が起こるか：

**問題 1：Claude Code は強力。でもあなたがベビーシッターをしている。**
毎セッションがゼロから始まる。昨日学んだことを忘れる。コンテキストをコピペし、アーキテクチャを再説明し、規約を繰り返す。あなたがメモリ。あなたがマネージャー。あなたがボトルネック。

**問題 2：AI エージェントフレームワーク。デモは華やか、体験は最悪。**
30万行のコード。カスタムアダプター。プロジェクト本体より長い設定ファイル。モデルが更新されるたびに壊れる。フレームワークのメンテに費やす時間の方がプロダクト開発より長い。

**問題 3：グレーゾーン。**
安全機構を迂回するセルフホスト型エージェントループ。上限なしのトークン従量課金 API。ツールを使っているのか、ツールに使われているのか分からないフランケンシュタインスタック。

## 答え

Clawd-Lobster は Claude Code を置き換えません。Claude Code に**記憶し、計画し、レビューし、構築し、進化する力**を与えます。しかも公式 Anthropic ツールだけで。

- **100% Claude Code CLI + Agent SDK。** ラッパーなし、カスタムエージェントループなし、グレーゾーンなし。既存の Claude サブスクリプションで動作。追加 API コストなし。
- **約9,000行。** 30万行ではない。一人で全部読める規模。Claude Code がアップデートされれば、新機能はそのまま使える。書き直し不要。壊れない。
- **5分で開始。** ブラウザを開く。2回クリック。終わり。API キー不要、Docker 不要、YAML の博士号不要。

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

## クイックスタート

### 全員向け（Web UI）

```bash
git clone https://github.com/teddashh/clawd-lobster
cd clawd-lobster
pip install -e .
clawd-lobster serve
```

ブラウザが開きます。セットアップウィザードがすべてガイドします。

### ターミナル派の方へ

```bash
clawd-lobster setup        # terminal onboarding
clawd-lobster squad start  # run Spec Squad in terminal
```

### クラシックインストール（パワーユーザー向け）

```powershell
# Windows
.\install.ps1

# macOS / Linux
chmod +x install.sh && ./install.sh
```

---

## 手に入るもの

### 1. Spec Squad：あなたの AI 開発チーム

やりたいことを説明するだけ。4つの Claude セッションが残りをやります。

**Architect** がテスト可能な要件を含む完全な仕様を書きます。**Reviewer**（Architect の指示を一切見たことがない完全に独立した Claude セッション）がそれを徹底的に叩きます。Reviewer が承認するまで、最大5ラウンドまでループします。5ラウンド目が終わっても Reviewer が承認しない場合、パイプラインを先に進めるために仕様は承認扱いになりますが、強制承認として記録されます。`.spec-squad.json` には `"reviewer"` ではなく `"approval": "round_limit"` と書かれ、ターンログには `FORCED_APPROVAL` の記録が追加され、ターミナルと Web の画面でもラウンド上限による承認だと表示されます。その後 **Coder** が仕様通りに構築し、**Tester** がすべての要件を検証します。

ギミックではありません。テストでは、Reviewer が最初の仕様で実際のバグを11個発見しました。セルフバリデーションチェックリストでは絶対に見つからない問題です。戻り値の型の矛盾、API の不整合、実現不可能な Gherkin シナリオ、ライブラリの互換性問題。

**なぜ機能するのか：** 各エージェントは隔離されたコンテキストで実行されます。Reviewer は Architect の推論に影響されません。Tester は Coder がどんなショートカットを使ったか知りません。独立した頭脳が独立した問題を見つけます。

2つのインターフェース、同じエンジン：
- **Web：** ブラウザで Claude とチャットし、ライブダッシュボードでエージェントの作業を監視
- **Terminal：** ターミナルで Claude が質問し、エージェント実行中に進捗を表示

### 2. 忘れない頭脳：Thin Ledger

連携する2つのレイヤー。ベクターデータベース不要。クラウド不要。

| レイヤー | 内容 | 役割 |
|----------|------|------|
| **SQLite (The Ledger)** | 意思決定、TODO、監査ログ、salience スコア、provenance | 運用上の真実：高速・構造化・クエリ可能 |
| **Git Wiki (The Library)** | 相互参照されたマークダウンページ、インデックス、ジャーナル、ソース | 体系化された知識：人間が読める、Git 同期 |
| **Oracle Vector DB (The Vault)** | All knowledge vectorized + cross-machine semantic search | Deep recall: find anything you have ever discussed, across all machines |

すべてのナレッジレコードは **provenance** を持ちます：誰が書いたか、どのエージェントか、確信度スコア、ライフサイクル状態（raw → synthesized → accepted → superseded）。匿名の事実はありません。

**3つのオペレーションが健全性を維持します：**
- **INGEST**：新情報がソース引用付きの Wiki ページになります
- **QUERY**：両レイヤーを検索し、ソースを引用します。価値ある回答は Wiki に書き戻されます
- **LINT**：定期的なヘルスチェックが矛盾、古い主張、孤立ページ、リンク切れを発見します

**修正ワークフロー：** エージェントは Wiki ページを直接編集できません。`memory_propose_correction` を通じて修正を提案し、レビューキューが作られます。争いのある主張はサイレントに上書きされるのではなく、解決されます。

重要なアイデアは浮上し、ノイズは沈む。うまくいったスキルは強化され、古い知識は減衰する。あなたが管理する必要はありません。すべて自動です。

*アーキテクチャは [MemPalace](https://github.com/milla-jovovich/mempalace)（空間構造）と [Karpathy の LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)（INGEST/QUERY/LINT）から吸収しました。依存関係はインストールしていません。コンセプトのみです。*

### 3. 常に生きている

ノートパソコンを閉じても、Clawd-Lobster は動き続けます。

heartbeat は OS のスケジューラ（Task Scheduler / cron / launchd）を使います。カスタムデーモンでも、ポーリングループでも、トークンを燃やすプロセスでもありません。セッションが落ちたら、フルコンテキストで復活。ベビーシッター不要。

### 4. すべてのマシン、1つの頭脳

GitHub がコントロールプレーン。Git がプロトコル。

マシン A がパターンを学習。プライベート Hub に同期。マシン B が即座に継承。新しいマシン？`install.ps1`、「Join Hub」、URL を貼り付け、2分で完全稼働。

### 5. 自己進化

複雑な作業の完了後、システムは再利用可能なパターンを抽出し、学習済みスキルとして保存します。次に同様のタスクが来たとき、前回どう解決したかを覚えています。

スキルには有効性スコアがあります。実績のあるパターンは強化され、古いスキルは減衰します。使えば使うほど賢くなります。魔法ではなく、うまくいったことを書き留めているだけです。

---

## ダッシュボード

`clawd-lobster serve` で `localhost:3333` に常駐 Web ダッシュボードが開きます。

**オンボーディング（Skill Parade）**：エージェント案内型の体験。Webにインタラクティブなスキルカードを表示し、Claude Codeがターミナルで対話的にガイド。言語、認証、ワークスペースを一緒に設定し、各スキルを一つずつ進めます。[完全ガイド →](docs/onboarding-guide.html)

**ワークスペース**：すべてのプロジェクトを一覧表示。ステータス、仕様の進捗、メモリサイズ、最終アクティビティ。

**Skills（3タブ）**：MCPサーバー、プロンプトパターン、Cronジョブ。設定、有効/無効、ヘルスチェック。

**APIキー**：Claude、GitHub、Codex、Gemini、Oracle、Odooの認証管理。マスク表示、サービスごとのヘルスプローブ。

**Spec Squad**：Claude とチャットして要件を発見。ライブダッシュボードで4つのエージェントの作業をリアルタイムで監視。

### エージェント案内型セットアップ（Escape Room）

これは従来のインストーラーではありません。WebダッシュボードとClaude Codeは**共同操縦者**です：

```
Web（ビジュアル層）    +     Claude Code（対話層）
スキルカードを表示           各スキルの説明
設定進捗を表示               質問に回答
設定フォームを表示           インストールコマンドを実行
リアルタイム更新             状態を読み取り、フローを進行
```

---

## Skills

厳選された10の Skills。それぞれが1つのことを確実にこなします。名前をクリックすると詳細ドキュメントが開きます。

### [memory-server](skills/memory-server/README.md)：基盤
セッションをまたぐ永続メモリのための MCP ツール26個。ローカルキャッシュからクラウド同期までの4層アーキテクチャ。重要な知識を浮上させ、ノイズを減衰させるサリエンスエンジン。CJK 対応トークン推定。Claude Code に「忘れる」をやめさせる Skill です。

### [spec](skills/spec/README.md)：アイデアからコードへ
ガイド付きワークスペース作成、OpenSpec ドキュメント生成（3W1H）、Spec Squad マルチエージェントパイプライン。ディスカバリーインタビューで要件を引き出します。Architect がテスト可能な仕様を Gherkin シナリオ付きで作成。Reviewer が徹底的に叩きます。Coder が契約通りに構築。Tester がすべての要件を検証。ターミナルでも Web でも。

### [evolve](skills/evolve/README.md)：自己改善
2時間ごとに実行。完了した作業をスキャンし、再利用可能なパターンを抽出し、学習済みスキルとして保存します。スキルには有効性スコアがあり、実績のあるパターンは強化され、古いものは減衰します。使えば使うほどエージェントが鋭くなります。設定不要。

### [absorb](skills/absorb/README.md)：ナレッジ吸収
GitHub リポジトリ、ローカルフォルダ、または Web URL を指定するだけ。コードベースを読み取り、アーキテクチャの意思決定、規約、パターンを抽出し、検索可能なナレッジとして保存します。既存プロジェクトへのオンボーディングやリファレンス実装の研究に使えます。

### [heartbeat](skills/heartbeat/README.md)：常時稼働
OS ネイティブのキープアライブ（Task Scheduler / cron / launchd）。30分ごとにチェック。落ちたセッションは `claude --resume` でフルコンテキスト付きで復活。カスタムデーモンなし、ポーリングループなし、トークン消費なし。ノートパソコンを閉じても、エージェントは動き続けます。

### [migrate](skills/migrate/README.md)：ワンタイムインポート
既存の AI セットアップ（`~/.claude/`、`~/.openclaw/`、`~/.hermes/`、`~/Documents/claude-setup/`）を検出し、メモリ、設定、ナレッジをインポートします。オンボーディング時に一度だけ実行。以後は不要です。

### [codex-bridge](skills/codex-bridge/README.md)：The Worker
OpenAI Codex にバルクワークを委任します（ChatGPT Plus で動作）。**ワーカー**として使う（並列タスク、ボイラープレート、テスト生成）か、**クリティック**として使う（敵対的セキュリティレビュー、アーキテクチャ議論、コードレビュー）。Claude → Codex → Gemini の三エージェントシステムで、各モデルが独自の視点を提供します。two-checkpoint レビューで品質を保証。AGENTS.md 経由で Claude のナレッジを Codex に同期する機能も搭載。

### [gemini-bridge](skills/gemini-bridge/README.md)：The Consultant
Google Gemini に別の視点を求めます。**不確実なとき**（ファクトチェック、リサーチ検証）、**複雑な意思決定**（アーキテクチャのトレードオフ、技術スタック選定）、または独立した頭脳による**セキュリティレビュー**が必要なときに使います。三者議論に対応：Claude が意見を形成 → Codex がレビュー → Gemini が検証 → コンセンサス。GEMINI.md 経由でコンテキストを共有します。

### [connect-odoo](skills/connect-odoo/README.md)：ERP 連携
XML-RPC + MCP による双方向 Odoo ERP 接続。Odoo データの読み書き用に特化したツール6個。変更のリアルタイムポーリング。AI ワークフローがビジネスプロセスと連携する必要がある場合に使えます。

### [notebooklm-bridge](skills/notebooklm-bridge/README.md)：ドキュメント生成
ワークスペースのドキュメントを Google NotebookLM に自動同期。コードベースドキュメントからスライド、インフォグラフィック、ポッドキャスト、レポートを生成。ページ番号スタンプ（複数ページ）またはデートスタンプ（単一ページ）による透かし除去機能内蔵。全ページで一貫したスタイリング。透かし除去はデフォルトでオフです（`auto_remove_watermark: false`）。注意：NotebookLM の透かしを除去すると Google の利用規約に抵触する可能性があります。有効にする前に NotebookLM の利用規約を確認してください。

---

すべての Skill にはトリガー説明（Claude が起動タイミングを判断）、Gotchas セクション（よくある間違いの回避策）、動的 `!command` インジェクション（ロード時のランタイムコンテキスト）があります。

---

## アーキテクチャ

```
Skills (the what)      ->  14 skills with manifests (skill.json), instructions, gotchas
Tools (the how)        ->  27 MCP tools + Claude Code native tools + 22 onboarding APIs
Hooks (the when)       ->  OS scheduler, git hooks, PostToolUse, Stop hooks
Memory (the brain)     ->  SQLite Ledger + Git Wiki + Oracle Vault (4-layer)
Operations (the cycle) ->  INGEST / QUERY / LINT (continuous knowledge lifecycle)
Dashboard (the eyes)   ->  Web UI at localhost:3333 (Skill Parade + 3-tab Skills + Keys)
```

**巨人の肩の上に立つ。** Clawd-Lobster は Claude Code を再構築しません。Claude Code のネイティブ拡張ポイント（MCP サーバー、CLAUDE.md、hooks、settings.json）を Anthropic が設計した通りに使います。Claude Code が新機能をリリースすれば、そのまま使える。モデルが改善されれば、あなたのエージェントも改善される。アダプターコードはゼロ。

```
Disk: ~2 MB    (code + configs)
RAM:  ~25 MB    (MCP server only)
CPU:  0% idle   (OS scheduler, not polling)
LOC:  ~25,000    (not 300,000)
```

ファイルツリーとランタイムの詳細は [ARCHITECTURE.md](ARCHITECTURE.md) を参照。

---

## CLI リファレンス

| Command | What It Does |
|---------|-------------|
| `clawd-lobster serve` | Start web dashboard (localhost:3333) |
| `clawd-lobster setup` | Terminal onboarding wizard |
| `clawd-lobster workspace create <name>` | Create a new workspace |
| `clawd-lobster squad start` | Run Spec Squad in terminal |
| `clawd-lobster status` | Show system health |

---

## マルチマシンセットアップ

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

最初のマシンが Hub を作成。以降のマシンは2分で参加できます。

---

## 必要条件

- Python 3.10+
- Claude Code CLI ([install](https://claude.ai/code))
- Git 2.x+
- Node.js 18+（オプション、Codex Bridge 用）
- GitHub アカウント（Hub sync 用）

---

## 比較

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

## フィロソフィー

**1. 増幅する。再構築しない。**
Claude Code は世界で最も優秀なコーディングエージェントです。私たちはそこに神経系を加えます。脳を作り直すのではありません。

**2. 巨人が高くなれば、あなたも高くなる。**
Claude Code がアップデートされるたびに、あなたの Clawd-Lobster も良くなります。マイグレーションゼロ、書き直しゼロ。

**3. 計画こそがプロダクト。**
Spec Squad はまずコードを書きません。仕様を書き、それを敵対的にレビューし、仕様通りに構築します。計画が契約です。

---

## コントリビュート

PR 歓迎です。コントリビュートの前に [ARCHITECTURE.md](ARCHITECTURE.md) をお読みください。

## ライセンス

MIT。[LICENSE](LICENSE) を参照。
