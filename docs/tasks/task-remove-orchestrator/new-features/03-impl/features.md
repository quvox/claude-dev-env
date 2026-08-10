---
target: docs/03-impl/features.md
change: replace
version_bump: minor
sections:
  - "## 機能一覧"
  - "## 統合した機能"
  - "## 昇格させた共通基盤機能"
  - "## 到達しない関数についての判断"
deletes: []
keywords: [機能表, 境界, claude-dev, Makefile, docker-proxy]
reason: 'オーケストレーターの全面削除にともなう機能表の整理(決定シート 概念1・概念2)。(1) `## 機能一覧` は**差分の表**で書く(`.claude/directions/change-set.md` 例外1)。`種別` に `delete` を書いた 27 行が削除対象である: `MODULE-orchestrator-*` 19 本 / `MODULE-cli-orchestrate` / `MODULE-makefile-build-orchestrator` / `MODULE-makefile-orch-sample` / `MODULE-makefile-orch-sample-clean` / `MODULE-sample-project-scaffold` / `MODULE-sample-project-mathkit` / `MODULE-hooks-save-prompt` / `MODULE-hooks-send-slack-message`。**機能は 83 → 56 本になる。**27 本それぞれに `new-features/03-impl/relations/` の削除指示が対になっている(片側だけだと `CS10` / `FT3` が落ちる)。(2) `## 統合した機能` から `MODULE-orchestrator-*` と `MODULE-sample-project-mathkit` の 2 行を削除し、`MODULE-cli-*` の件数を 20 → 19 へ改める(`orchestrate` の削除による)。(3) `## 昇格させた共通基盤機能` から `orchestrator/state.go` の行を削除する。**同表のファンインの数値は、実装を削除したあとに再生成したコールグラフから実測して確定させる** — ファンイン(到達できる機能の数)はコードから導出される事実であり、`/task-close` §2 が再生成した relations と突き合わせて確定する(コードが正)。memo.md のタスクリストにその手順を持たせている。(4) `## 到達しない関数についての判断` から orchestrator の 4 行(`orchestrator/main.go::terminalConfirm` / `orchestrator/term.go::resolveMenu` / `orchestrator/state.go::Store.SaveControl` と `Store.RemoveSidecar` / `orchestrator/controller.go::Controller.resolveInterventions` ほか)を削除する — シンボルごと消える。**残る 2 行(`claude-dev::main` のディスパッチャ本体と `docker-proxy/main.go::cachedResolveProjectDir` / `lookupProjectDir`)は変えない**。あわせて節冒頭の HTML コメントから件数「16件」を外す — この数は生成物 `feature-graph.md` から導かれる値で、実装を削除して再生成するまで確定しない。**件数を書かなくても仕分けの対象(到達しない関数の全件)は一意に決まる**ので、実測待ちの数値を本文に持たせない。(5) frontmatter の `keywords` から `orchestrator` を外す'
---

## 機能一覧

| 機能ID | 種別 | 入口 | 所属 | 概要 |
|---|---|---|---|---|
| MODULE-cli-orchestrate | delete | - | MOD-cli-orchestrate | `claude-dev orchestrate` サブコマンドを廃止する |
| MODULE-hooks-save-prompt | delete | - | MOD-hooks | Claude Code フックのプロンプト保存を廃止する |
| MODULE-hooks-send-slack-message | delete | - | MOD-hooks | Claude Code フックの Slack 通知を廃止する |
| MODULE-makefile-build-orchestrator | delete | - | MOD-makefile | `make build-orchestrator` を廃止する |
| MODULE-makefile-orch-sample | delete | - | MOD-makefile | `make orch-sample` を廃止する |
| MODULE-makefile-orch-sample-clean | delete | - | MOD-makefile | `make orch-sample-clean` を廃止する |
| MODULE-orchestrator-claude-exec | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-config | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-controller | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-dashboard | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-handoff | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-main | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-mode | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-plan | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-review | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-session | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-slack | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-state | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-state-intervention | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-state-io | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-streamlog | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-term | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-trigger | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-worker | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-orchestrator-worktree | delete | - | MOD-orchestrator | Go 実装 `orchestrator/` を廃止する |
| MODULE-sample-project-mathkit | delete | - | MOD-sample-project | 自己検証題材の実装対象を廃止する |
| MODULE-sample-project-scaffold | delete | - | MOD-sample-project | 自己検証題材の配置を廃止する |

## 統合した機能

<!-- 複数の入口を1行にまとめた場合だけ、その理由をここに残す。 -->

| 機能ID | まとめた入口 | まとめた理由 |
|---|---|---|
| `MODULE-cli-*`(19件すべて) | `claude-dev::main#<subcmd>` と `claude-dev-mac::main#<subcmd>` | 同一のコマンド面を Linux/macOS で別実装しているだけで、外から見える振る舞いは同じ。OS 別に割ると同一仕様のモジュールが17本増えて依存表が読めなくなる(決定シート 委任(e))。**旧 `cli-mac` モジュールはこれにより解体される** |
| `MODULE-cli-common-*`(12件すべて) | `claude-dev::<fn>` と `claude-dev-mac::<fn>` | 同上。同名対の共通基盤関数を1機能として扱い、OS 差分は本文の「異常系・差分」に書く |
| `MODULE-portsync-dood` / `MODULE-vm-mode-portsync` / `MODULE-vm-mode-healthd` | `main#--loop` と `main` | 同じスクリプトの一発実行と常駐実行。抽出器は `--loop` だけをエントリポイントとするが、一発実行も公開インターフェースなので同一機能に含める |

## 昇格させた共通基盤機能

<!-- ファンイン(到達できる機能の数)が2以上の関数は境界の実体である。 -->

| 機能ID / シンボル | ファンイン | 昇格したか | 判断の理由 |
|---|---|---|---|
| `claude-dev::container_name` / `claude-dev-mac::container_name` | 9 | 昇格 | コンテナ命名規則の実体。全サブコマンドがこの規則に依存する |
| `claude-dev::project_name` / `claude-dev-mac::project_name` | 9 | 畳み込む | 呼び出し元は `container_name` だけ。命名規則の内側の一段で、単独では意味を持たない |
| `claude-dev::is_running` / `claude-dev-mac::is_running` | 8 | 昇格 | 「セッションが動いているか」の判定はこのシステムの状態モデルそのもの |
| `claude-dev::image_exists` / `claude-dev-mac::image_exists` | 7 | 昇格 | `require_setup` を昇格させても `ensure_docker_proxy_container` から到達するのでファンイン2が残る |
| `claude-dev::require_setup` / `claude-dev-mac::require_setup` | 6 | 昇格 | セットアップ未実施時の停止条件。6機能に共通の事前条件ゲート |
| `claude-dev::acquire_lock` / `release_lock`(および macOS 版の同名対) | 6 | 昇格 | 共有資源(共有ボリューム・docker-proxy)を触る6機能を直列化する排他の実体。`start` / `stop` / `logout` / `reset` / `login` / `login-codex` が同じキー体系(`CTR-cli-container` の「排他(ロックキー)」)に依存する |
| `claude-dev::container_exists` / `claude-dev-mac::container_exists` | 5 | 昇格 | 停止中コンテナを含む存在判定。`is_running` と別概念で、stop/logout の分岐条件 |
| `claude-dev::resolve_container_user` / `claude-dev-mac::resolve_container_user` | 3 | 昇格 | docker exec の実行ユーザ決定。権限に関わる判断を含む |
| `claude-dev::ensure_infrastructure` / `claude-dev-mac::ensure_infrastructure` | 3 | 昇格 | docker network とボリュームを作る副作用を持つ |
| `claude-dev::get_novnc_url` / `claude-dev-mac::get_novnc_url` | 3 | 昇格 | 利用者に提示する接続 URL の組み立て規則。3機能が同じ URL を出す |
| `claude-dev-mac::dev_agent_path` | 3 | 昇格 | macOS 専用の ssh-agent ソケット配置規則。start/stop/ssh-keys reset が同じ場所を前提にする |
| `claude-dev::select_ssh_keys_interactive` / `claude-dev-mac::select_ssh_keys_interactive` | 2 | 昇格 | 対話 UI を持ち、`start` と `ssh-keys select` の双方から呼ばれる |
| `claude-dev::write_project_ssh_keys` / `claude-dev-mac::write_project_ssh_keys` | 2 | 昇格 | `.claude-dev.yaml` への書き込み(副作用)。`ensure_project_config` と選択 UI の双方から呼ばれる |
| `claude-dev::discover_ssh_keys` / `claude-dev-mac::discover_ssh_keys` | 2 | 畳み込む | `select_ssh_keys_interactive` を昇格させれば呼び出し元は1つになる |

## 到達しない関数についての判断

<!-- feature-graph.md の「どの入口からも到達しない関数」に対する仕分け。生成物ではなく人間の判断。 -->

| シンボル | 判断 |
|---|---|
| `claude-dev::main` / `claude-dev-mac::main` | ディスパッチャ本体。サブコマンドのハンドラを入口にしているので本体には辺が立たない(抽出の構造上そうなる) |
| `docker-proxy/main.go::cachedResolveProjectDir` / `lookupProjectDir` | `var resolveProjectDir = cachedResolveProjectDir`(`docker-proxy/main.go:76`)の関数値経由。Tier 2 の静的解決の限界 |
