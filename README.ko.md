> 이 README는 이전 버전 기준입니다. 최신 내용은 [영어 README](README.md)와 [프로젝트 페이지](https://teddashh.github.io/clawd-lobster/)를 참고하세요.

[English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

# Clawd-Lobster

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/github/license/teddashh/clawd-lobster)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Runtime](https://img.shields.io/badge/RAM-25MB-orange)

<p align="center">
<strong>你終究要用 Claude Code 的，為什麼不一開始就選最好的體驗？</strong><br>
<strong>You'll end up using Claude Code anyway, so why not start with the best experience?</strong><br>
<strong>어차피 결국 Claude Code를 쓰게 됩니다. 처음부터 최고의 경험을 선택하지 않을 이유가 있나요?</strong>
</p>

---

## 문제

AI 에이전트 프레임워크, 본 적 있으시죠. 몇 개 써봤을 수도 있습니다. 실제로 무슨 일이 벌어지는지:

**문제 1: Claude Code는 강력합니다. 하지만 당신이 보모 노릇을 하고 있습니다.**
매 세션이 제로에서 시작합니다. 어제 배운 걸 잊어버립니다. 컨텍스트를 복붙하고, 아키텍처를 다시 설명하고, 규칙을 또 알려줍니다. 당신이 메모리입니다. 당신이 매니저입니다. 당신이 병목입니다.

**문제 2: AI 에이전트 프레임워크. 데모는 화려하고, 경험은 최악입니다.**
30만 줄의 코드. 커스텀 어댑터. 실제 프로젝트보다 긴 설정 파일. 모델이 업데이트될 때마다 깨집니다. 프레임워크 유지보수에 쓰는 시간이 제품 개발보다 깁니다.

**문제 3: 그레이 존.**
안전 장치를 우회하는 셀프 호스팅 에이전트 루프. 상한선 없는 토큰 종량제 API. 도구를 쓰고 있는 건지, 도구에 쓰이고 있는 건지 구분 안 되는 프랑켄슈타인 스택.

## 답

Clawd-Lobster는 Claude Code를 대체하지 않습니다. Claude Code가 **기억하고, 계획하고, 리뷰하고, 구축하고, 진화하게** 만듭니다. 그것도 공식 Anthropic 도구만으로.

- **100% Claude Code CLI + Agent SDK.** 래퍼 없음, 커스텀 에이전트 루프 없음, 그레이 존 없음. 기존 Claude 구독으로 동작합니다. 추가 API 비용 없음.
- **약 9,000줄.** 30만 줄이 아닙니다. Claude Code가 업데이트되면 새 기능을 그대로 사용할 수 있습니다. 다시 작성할 필요 없음, 깨지지 않음.
- **5분이면 시작.** 브라우저를 열고, 두 번 클릭하면, 끝. API 키 불필요, Docker 불필요, YAML 박사학위 불필요.

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

## 빠른 시작

### 모든 사용자 (Web UI)

```bash
git clone https://github.com/teddashh/clawd-lobster
cd clawd-lobster
pip install -e .
clawd-lobster serve
```

브라우저가 열립니다. 설정 마법사가 모든 것을 안내합니다.

### 터미널을 좋아하는 분들

```bash
clawd-lobster setup        # terminal onboarding
clawd-lobster squad start  # run Spec Squad in terminal
```

### 클래식 설치 (파워 유저용)

```powershell
# Windows
.\install.ps1

# macOS / Linux
chmod +x install.sh && ./install.sh
```

---

## 무엇을 얻는가

### 1. Spec Squad: 당신의 AI 개발 팀

원하는 것을 설명하세요. 4개의 Claude 세션이 나머지를 합니다.

**Architect**가 테스트 가능한 요구사항이 포함된 완전한 사양을 작성합니다. **Reviewer**(Architect의 지시를 한 번도 본 적 없는 완전히 독립된 Claude 세션)가 그것을 철저히 뜯어봅니다. Reviewer가 승인할 때까지, 최대 5라운드까지 반복합니다. 5라운드가 끝나도 Reviewer가 승인하지 않으면 파이프라인을 계속 진행하기 위해 사양은 승인 처리되지만, 강제 승인으로 기록됩니다. `.spec-squad.json`에는 `"reviewer"`가 아니라 `"approval": "round_limit"`가 기록되고, 턴 로그에 `FORCED_APPROVAL` 항목이 추가되며, 터미널과 웹 화면 모두 라운드 제한에 의한 승인이라고 표시합니다. 그 후 **Coder**가 사양대로 구축하고, **Tester**가 모든 요구사항을 검증합니다.

기믹이 아닙니다. 테스트에서 Reviewer는 첫 사양에서 실제 버그 11개를 잡아냈습니다. 셀프 밸리데이션 체크리스트로는 절대 찾을 수 없는 문제들입니다. 반환 타입 충돌, API 불일치, 불가능한 Gherkin 시나리오, 라이브러리 호환성 문제.

**왜 효과가 있는가:** 각 에이전트가 격리된 컨텍스트에서 실행됩니다. Reviewer는 Architect의 추론에 영향받지 않습니다. Tester는 Coder가 어떤 지름길을 썼는지 모릅니다. 독립적인 두뇌가 독립적인 문제를 찾습니다.

두 가지 인터페이스, 같은 엔진:
- **Web:** 브라우저에서 Claude와 채팅하고, 라이브 대시보드에서 에이전트 작업을 감시
- **Terminal:** 터미널에서 Claude가 질문하고, 에이전트 실행 중 진행 상황 출력

### 2. 잊지 않는 두뇌: Thin Ledger

함께 작동하는 2개의 레이어. 벡터 데이터베이스 불필요. 클라우드 불필요.

| 레이어 | 내용 | 역할 |
|--------|------|------|
| **SQLite (The Ledger)** | 의사결정, TODO, 감사 로그, salience 점수, provenance | 운영상의 진실: 빠르고, 구조화되고, 쿼리 가능 |
| **Git Wiki (The Library)** | 상호 참조된 마크다운 페이지, 인덱스, 저널, 소스 | 체계화된 지식: 사람이 읽을 수 있고, Git 동기화 |
| **Oracle Vector DB (The Vault)** | All knowledge vectorized + cross-machine semantic search | Deep recall: find anything you have ever discussed, across all machines |

모든 지식 레코드는 **provenance**를 가집니다: 누가 작성했는지, 어떤 에이전트인지, 확신도 점수, 라이프사이클 상태(raw → synthesized → accepted → superseded). 익명의 사실은 없습니다.

**3가지 오퍼레이션이 건강을 유지합니다:**
- **INGEST**: 새로운 정보가 출처 인용이 포함된 Wiki 페이지가 됩니다
- **QUERY**: 두 레이어를 모두 검색하고, 출처를 인용합니다. 가치 있는 답변은 Wiki에 다시 기록됩니다
- **LINT**: 정기적인 헬스 체크가 모순, 오래된 주장, 고아 페이지, 깨진 링크를 찾아냅니다

**수정 워크플로우:** 에이전트는 Wiki 페이지를 직접 편집할 수 없습니다. `memory_propose_correction`을 통해 수정을 제안하고, 리뷰 큐가 생성됩니다. 분쟁이 있는 주장은 조용히 덮어쓰이지 않고, 해결됩니다.

중요한 아이디어는 떠오르고, 노이즈는 가라앉습니다. 효과 있는 스킬은 강화되고, 오래된 지식은 감쇠됩니다. 관리할 필요 없습니다. 전부 자동입니다.

*아키텍처는 [MemPalace](https://github.com/milla-jovovich/mempalace)(공간 구조)와 [Karpathy의 LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)(INGEST/QUERY/LINT)에서 흡수했습니다. 종속성은 설치하지 않았습니다. 개념만 차용했습니다.*

### 3. 항상 살아 있음

노트북을 닫아도 Clawd-Lobster는 계속 작동합니다.

heartbeat는 OS 스케줄러(Task Scheduler / cron / launchd)를 사용합니다. 커스텀 데몬도, 폴링 루프도, 토큰을 태우는 프로세스도 아닙니다. 세션이 죽으면 풀 컨텍스트로 부활합니다. 보모 노릇 불필요.

### 4. 모든 머신, 하나의 두뇌

GitHub이 컨트롤 플레인. Git이 프로토콜.

머신 A가 패턴을 학습합니다. 프라이빗 Hub에 동기화됩니다. 머신 B가 즉시 계승합니다. 새 머신? `install.ps1`, "Join Hub", URL 붙여넣기, 2분이면 완전 가동.

### 5. 자기 진화

복잡한 작업 완료 후, 시스템이 재사용 가능한 패턴을 추출하고 학습된 스킬로 저장합니다. 다음에 비슷한 태스크가 오면, 지난번에 어떻게 해결했는지 기억합니다.

스킬에는 유효성 점수가 있습니다. 입증된 패턴은 강화되고, 오래된 스킬은 감쇠됩니다. 쓸수록 시스템이 똑똑해집니다. 마법이 아니라, 잘된 것을 기록해두기 때문입니다.

---

## 대시보드

`clawd-lobster serve`가 `localhost:3333`에서 상주 Web 대시보드를 엽니다.

**온보딩 (Skill Parade)**: 에이전트 안내형 체험. 웹에 인터랙티브 스킬 카드를 표시하고, Claude Code가 터미널에서 대화형으로 안내합니다. 언어, 인증, 워크스페이스를 함께 설정한 뒤, 각 스킬을 하나씩 진행합니다. [전체 가이드 →](docs/onboarding-guide.html)

**워크스페이스**: 모든 프로젝트를 한 화면에. 상태, 사양 진행률, 메모리 크기, 마지막 활동.

**Skills (3 탭)**: MCP 서버, 프롬프트 패턴, Cron 작업. 설정, 활성화/비활성화, 헬스 체크.

**API 키**: Claude, GitHub, Codex, Gemini, Oracle, Odoo 인증 관리. 마스킹 표시, 서비스별 헬스 프로브.

**Spec Squad**: Claude와 대화하며 요구사항을 발견. 라이브 대시보드에서 4개 에이전트 실시간 감시.

### 에이전트 안내형 설정 (Escape Room)

기존 인스톨러가 아닙니다. 웹 대시보드와 Claude Code는 **공동 조종사**입니다:

```
웹 (시각 계층)         +     Claude Code (대화 계층)
스킬 카드 표시               각 스킬 설명
설정 진행 표시               질문에 답변
설정 폼 표시                 설치 명령 실행
실시간 업데이트               상태 읽기, 흐름 진행
```

---

## Skills

엄선된 10개 Skills. 각각 하나를 확실하게 합니다. 이름을 클릭하면 전체 문서를 볼 수 있습니다.

### [memory-server](skills/memory-server/README.md): 기반
세션을 넘나드는 영속 메모리를 위한 MCP 도구 26개. 즉시 로컬 캐시부터 클라우드 동기화까지 4계층 아키텍처. 중요한 지식을 떠올리고 노이즈를 감쇠시키는 salience 엔진. CJK 대응 토큰 추정. Claude Code가 더 이상 잊어버리지 않게 만드는 Skill입니다.

### [spec](skills/spec/README.md): 아이디어에서 코드로
가이드 기반 워크스페이스 생성, OpenSpec 문서 생성(3W1H), Spec Squad 멀티 에이전트 파이프라인. 디스커버리 인터뷰로 요구사항을 도출합니다. Architect가 Gherkin 시나리오를 포함한 테스트 가능 사양을 작성합니다. Reviewer가 철저히 뜯어봅니다. Coder가 계약대로 구축합니다. Tester가 모든 요구사항을 검증합니다. 터미널에서도 웹에서도.

### [evolve](skills/evolve/README.md): 자기 개선
2시간마다 실행됩니다. 완료된 작업을 스캔하고, 재사용 가능한 패턴을 추출하고, 학습된 스킬로 저장합니다. 스킬에는 유효성 점수가 있어서 입증된 패턴은 강화되고, 오래된 패턴은 감쇠됩니다. 쓸수록 에이전트가 날카로워집니다. 설정 불필요.

### [absorb](skills/absorb/README.md): 지식 흡수
GitHub 리포지토리, 로컬 폴더, 또는 웹 URL을 가리키기만 하면 됩니다. 코드베이스를 읽고, 아키텍처 결정/규약/패턴을 추출한 뒤 검색 가능한 지식으로 저장합니다. 기존 프로젝트에 온보딩하거나 레퍼런스 구현을 연구할 때 사용합니다.

### [heartbeat](skills/heartbeat/README.md): 항상 살아 있음
OS 네이티브 keep-alive(Task Scheduler / cron / launchd). 30분마다 체크합니다. 죽은 세션은 `claude --resume`으로 풀 컨텍스트와 함께 부활합니다. 커스텀 데몬 없음, 폴링 루프 없음, 토큰 소모 없음. 노트북을 닫아도 에이전트는 계속 일합니다.

### [migrate](skills/migrate/README.md): 원타임 임포트
기존 AI 셋업(`~/.claude/`, `~/.openclaw/`, `~/.hermes/`, `~/Documents/claude-setup/`)을 감지하고 메모리, 설정, 지식을 임포트합니다. 온보딩 시 한 번만 실행하면 됩니다. 그 이후로는 필요 없습니다.

### [codex-bridge](skills/codex-bridge/README.md): The Worker
OpenAI Codex에 대량 작업을 위임합니다(ChatGPT Plus로 동작). **워커**로 사용(병렬 태스크, 보일러플레이트, 테스트 생성)하거나, **크리틱**으로 사용(적대적 보안 리뷰, 아키텍처 토론, 코드 리뷰)합니다. Claude → Codex → Gemini 삼 에이전트 시스템으로, 각 모델이 독자적인 관점을 제공합니다. two-checkpoint 리뷰로 품질을 보증합니다. AGENTS.md를 통해 Claude의 지식을 Codex에 동기화하는 기능도 탑재.

### [gemini-bridge](skills/gemini-bridge/README.md): The Consultant
Google Gemini에 다른 관점을 구합니다. **불확실할 때**(팩트 체크, 리서치 검증), **복잡한 의사결정**(아키텍처 트레이드오프, 기술 스택 선정), 또는 독립적인 두뇌의 **보안 리뷰**가 필요할 때 사용합니다. 삼자 토론을 지원합니다: Claude가 의견을 형성 → Codex가 리뷰 → Gemini가 검증 → 합의 도출. GEMINI.md를 통해 컨텍스트를 공유합니다.

### [connect-odoo](skills/connect-odoo/README.md): ERP 연동
XML-RPC + MCP를 통한 양방향 Odoo ERP 연결. Odoo 데이터 읽기/쓰기를 위한 특화 도구 6개. 변경 사항 실시간 폴링. AI 워크플로우가 비즈니스 프로세스와 연동해야 할 때 사용합니다.

### [notebooklm-bridge](skills/notebooklm-bridge/README.md): 문서 생성
워크스페이스 문서를 Google NotebookLM에 자동 동기화합니다. 코드베이스 문서로부터 슬라이드, 인포그래픽, 팟캐스트, 리포트를 생성합니다. 페이지 번호 스탬프(다중 페이지) 또는 날짜 스탬프(단일 페이지)를 이용한 워터마크 제거 기능 내장. 모든 페이지에서 일관된 스타일링. 워터마크 제거는 기본값이 꺼짐입니다(`auto_remove_watermark: false`). 주의: NotebookLM 워터마크를 제거하면 Google 약관에 위배될 수 있습니다. 켜기 전에 NotebookLM 이용 약관을 확인하세요.

---

모든 Skill에는 트리거 설명(Claude가 활성화 시점을 판단), Gotchas 섹션(흔한 실수 방지책), 동적 `!command` 인젝션(로드 시 런타임 컨텍스트)이 있습니다.

---

## 아키텍처

```
Skills (the what)      ->  14 skills with manifests (skill.json), instructions, gotchas
Tools (the how)        ->  27 MCP tools + Claude Code native tools + 22 onboarding APIs
Hooks (the when)       ->  OS scheduler, git hooks, PostToolUse, Stop hooks
Memory (the brain)     ->  SQLite Ledger + Git Wiki + Oracle Vault (4-layer)
Operations (the cycle) ->  INGEST / QUERY / LINT (continuous knowledge lifecycle)
Dashboard (the eyes)   ->  Web UI at localhost:3333 (Skill Parade + 3-tab Skills + Keys)
```

**거인의 어깨 위에 서다.** Clawd-Lobster는 Claude Code를 재구축하지 않습니다. Claude Code의 네이티브 확장 포인트(MCP 서버, CLAUDE.md, hooks, settings.json)를 Anthropic이 설계한 그대로 사용합니다. Claude Code가 새 기능을 출시하면 그대로 사용 가능. 모델이 개선되면 에이전트도 개선됩니다. 어댑터 코드 제로.

```
Disk: ~2 MB    (code + configs)
RAM:  ~25 MB    (MCP server only)
CPU:  0% idle   (OS scheduler, not polling)
LOC:  ~25,000    (not 300,000)
```

파일 트리와 런타임 상세 정보는 [ARCHITECTURE.md](ARCHITECTURE.md)를 참조하세요.

---

## CLI 레퍼런스

| Command | What It Does |
|---------|-------------|
| `clawd-lobster serve` | Start web dashboard (localhost:3333) |
| `clawd-lobster setup` | Terminal onboarding wizard |
| `clawd-lobster workspace create <name>` | Create a new workspace |
| `clawd-lobster squad start` | Run Spec Squad in terminal |
| `clawd-lobster status` | Show system health |

---

## 멀티 머신 설정

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

첫 번째 머신이 Hub를 생성합니다. 이후 머신은 2분이면 합류 가능합니다.

---

## 요구사항

- Python 3.10+
- Claude Code CLI ([install](https://claude.ai/code))
- Git 2.x+
- Node.js 18+ (선택사항, Codex Bridge용)
- GitHub 계정 (Hub sync용)

---

## 비교

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

## 철학

**1. 증폭한다. 재구축하지 않는다.**
Claude Code는 세계에서 가장 유능한 코딩 에이전트입니다. 우리는 거기에 신경계를 추가합니다. 뇌를 다시 만들지 않습니다.

**2. 거인이 높아지면, 당신도 높아진다.**
Claude Code가 업데이트될 때마다 Clawd-Lobster도 좋아집니다. 마이그레이션 제로, 재작성 제로.

**3. 계획이 곧 제품이다.**
Spec Squad는 코드부터 쓰지 않습니다. 사양을 쓰고, 적대적으로 리뷰하고, 사양대로 구축합니다. 계획이 계약입니다.

---

## 기여

PR 환영합니다. 기여하기 전에 [ARCHITECTURE.md](ARCHITECTURE.md)를 읽어주세요.

## 라이선스

MIT. [LICENSE](LICENSE) 참조.
