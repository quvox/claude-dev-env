---
id: system
layer: design
title: claude-dev-env 全体設計書
version: 1.9.0
updated: 2026-07-31
verified:
  at: 2026-07-31
  version: 1.9.0
  against:
    - doc: docs/01-requirements/core.md
      version: 1.9
    - doc: docs/01-requirements/orchestration.md
      version: 1.1
summary: >
  隔離Docker開発環境＋AIオーケストレーターの全体設計。14モジュール分割定義、モジュール間契約5件、
  CLI/TUIのUI設計、テスト戦略（単体/結合/E2E）とE2Eシナリオ一覧を定める。同梱エージェント CLI
  （Claude Code / Codex CLI）の導入位置・認証共有・Codex サンドボックス方針の構造を含む。
keywords: [全体設計, モジュール分割, docker-proxy, orchestrator, VMモード, テスト戦略, E2E, CodexCLI, Codexサンドボックス]
source:
  - docs/01-requirements/core.md
  - docs/01-requirements/orchestration.md
---

# 全体設計書:claude-dev-env

## 概要

Claude Code を隔離 Docker コンテナで動かす開発環境基盤（[core](../01-requirements/core.md)）と、その上で
複数エージェントを連携させる AIオーケストレーター（[orchestration](../01-requirements/orchestration.md)）を
実現する構造を定める。OS 依存はホスト CLI に閉じ、コンテナ内資産（イメージ・entrypoint・firewall・
docker-proxy）は OS 非依存に保つ。

## アーキテクチャ

```mermaid
graph TD
  subgraph Host[ホスト Linux/macOS]
    CLI[cli / cli-mac]
    MK[makefile]
    VM[vm-mode]
    GH[ghcr-workflow]
  end
  subgraph Images[コンテナイメージ devcontainer]
    EP[entrypoint]
    FW[firewall]
    PS[portsync]
    HK[hooks]
    CT[container-tools]
    ORCH[orchestrator]
  end
  DP[docker-proxy 共有]
  SP[sample-project]

  MK --> Images
  MK --> DP
  MK --> SP
  GH --> Images
  CLI -->|start/stop/forward/login| Images
  CLI -->|orchestrate| ORCH
  CLI --> VM
  EP --> FW
  EP --> PS
  ORCH --> HK
  ORCH --> SP
  Images -->|DOCKER_HOST| DP
```

- 開発者はホスト CLI（`cli`／macOS は `cli-mac`）で Claude コンテナのライフサイクルを操作する。
- コンテナ起動時は `entrypoint` が UID/GID 追従・認証コピー・`firewall` 起動・MCP/VNC 設定・tmux 開始を行う。
- コンテナ内 Docker は `docker-proxy`（共有）を介して制限付きで使う。重い案件は `vm-mode`。
- `orchestrator`（Go, コンテナ内常駐）が 2 モードで worker を並列制御する。`sample-project` で自己検証する。
- イメージは `makefile` でビルド、`ghcr-workflow` で GHCR 配布する。

## モジュール分割定義 ※この体系の要

| モジュール(slug) | 責務 | 対応する要件(領域/要件番号) | 依存モジュール | 詳細設計 | 03-impl |
|---|---|---|---|---|---|
| cli | ホスト CLI（Linux `claude-dev`）。start/stop/list/attach/forward/unforward/ports/login/login-codex/logout/ssh-keys/orchestrate/code/upgrade 等 | core/1,3,4,6,7(7-5 compose 名一意化),11,12(login-codex, 12-7 `--security-opt` 不付与) orchestration/13(起動) | container-tools, hooks, portsync, devcontainer | なし | 03-impl/cli.md |
| cli-mac | macOS 版 `claude-dev-mac` の差分（SSH agent TCP ブリッジ・ポート直結・VM/KVM 非対応・arm64） | core/10（cli が担う要件の macOS 差分を含む） | cli | なし | 03-impl/cli-mac.md |
| makefile | ビルド・セットアップ・install/uninstall・login・upgrade・orch-sample 等の入口 | core/9(build),全般 | devcontainer, docker-proxy, orchestrator, sample-project | なし | 03-impl/makefile.md |
| entrypoint | `entrypoint-claude.sh`：UID/GID 追従・認証コピー（claude/codex）・既定設定生成（claude `settings.json` / codex `config.toml`）・firewall 起動・MCP/VNC/Chrome・tmux・認証同期（claude/codex）・portsync 起動 | core/2,3,5,11,12(12-4〜12-6,12-9) | firewall, portsync | なし | 03-impl/entrypoint.md |
| firewall | `init-firewall-claude.sh`：iptables ファイアウォール | core/5 | — | なし | 03-impl/firewall.md |
| devcontainer | `Dockerfile.claude`(base / vnc-base / claude-cli / claude-vnc の4ステージ)・`Dockerfile.docker-proxy`・`.devcontainer/tmux.conf` 等イメージ定義。各モジュールの資産をイメージへ同梱し、エージェント CLI（Claude Code / Codex CLI）を終端ステージで導入する | core/1,11,9,12 | — | なし | 03-impl/devcontainer.md |
| docker-proxy | Go 製 Docker API 検査プロキシ（危険操作拒否・/workspace bind 書換） | core/7 | — | なし | 03-impl/docker-proxy.md |
| orchestrator | Go 製コントローラ：2モード・外部制御ループ・worker並列・タスク単位介入・相互レビュー・TUI・Slack・状態保全 | orchestration/12〜19 | hooks(Slack通知) | なし | 03-impl/orchestrator.md |
| sample-project | `examples/orch-sample/`（Python+pytest 題材）・`workspace/orch-sample`・`scripts/orch-sample.sh`（scaffold）：自己検証 | orchestration/20 | orchestrator | なし | 03-impl/sample-project.md |
| vm-mode | `scripts/vm`・`vm-up.sh`・`vm-portsync.sh`・`vm-healthd.sh`・`VM_DEV.md.tmpl`：ゲスト VM とネイティブ Docker | core/8 | cli | なし | 03-impl/vm-mode.md |
| ghcr-workflow | `.github/workflows/ghcr-images.yml`：GHCR マルチアーキ日次配布 | core/9 | devcontainer | なし | 03-impl/ghcr-workflow.md |
| hooks | Claude Code フック（イメージ同梱・`cli` が settings に配線）：`save_prompt.sh`（プロンプト保存）・`sendslackmsg.sh`（Slack通知） | orchestration/18 core周辺 | — | なし | 03-impl/hooks.md |
| container-tools | コンテナ内でユーザが使う資産：`wait-limit-reset.sh`（レート制限リセット待ち）・`scripts/tmux.conf`（実行時に `~/.tmux.conf` へマウントする tmux 設定） | core/1(tmux),運用補助 | — | なし | 03-impl/container-tools.md |
| portsync | `dood-portsync.sh`：DooD 実行時ポート同期ヘルパ（Dockerfile 同梱・entrypoint が起動、`127.0.0.1:PORT`→ホスト転送） | core/6 | — | なし | 03-impl/portsync.md |

### 分割の根拠

- **物理配置と1対1**: 各モジュールはリポジトリの実体（1スクリプト／1 Go モジュール／1 Dockerfile 群／
  1 ワークフロー）に対応する（[structure steering](../_steering/structure.md)）。変更が起きる単位＝ファイル単位で切った。
- **OS 依存の局所化**: `cli` と `cli-mac` を分け、OS 差分を macOS 側に閉じる（D-10）。共通ロジックは `cli`。
- **補助スクリプトは「役割」で分ける**: 旧一括の scripts 群を、担う役割ごとに独立モジュール化した——
  `hooks`（Claude Code フック）／`container-tools`（コンテナ内でユーザが使う資産）／`portsync`（実行時
  ネットワークヘルパ）。`entrypoint`・`firewall`・VM 系スクリプトは元々独立し、`orch-sample.sh` は題材の
  scaffold として `sample-project` に属する。役割が違うものを1モジュールに混ぜない方針。
- **orchestrator は最大モジュール**: Go の単一プログラムだが責務が多い。詳細は 03-impl/orchestrator.md が担い、
  肥大化時は本表に `02-design/orchestrator.md`（詳細設計）を足す判断を /change で行う。
- **共有 vs プロジェクト単位**: `docker-proxy` は全 Claude コンテナで共有、他はプロジェクト/イメージ単位。

## モジュール間インターフェース(契約)

### cli → コンテナ/entrypoint（環境変数・マウント）

```
起動時に渡す主な契約:
  DOCKER_HOST = tcp://claude-dev-docker-proxy:2375     # docker-proxy 経由（既定 DooD）
  CLAUDE_DEV_DOOD_PORTSYNC = 0|1(既定1)                # dood-portsync 有効/無効
  CLAUDE_DEV_VM = 0|1                                  # VM モード連携フラグ
  CLAUDE_DEV_ALLOW_WORKSPACE_BINDS = 0|1(既定1)        # docker-proxy の /workspace bind 許可
  mount: <cwd> -> /workspace (RW), claude-dev-auth -> ~/.claude-shared (RW),
         claude-dev-config -> ~/.config-shared (RW), $SSH_AUTH_SOCK -> /tmp/ssh-agent.sock (RO)
認証の受け渡し（cli が起動前に用意し、entrypoint が引き取る）:
  claude: 共有ボリューム直下 -> <cwd>/.claude/{.credentials.json,.claude.json}
  codex : 共有ボリューム codex/ -> <cwd>/.codex/auth.json
  ※ codex 認証は claude-dev-auth ボリュームの codex/ サブディレクトリに相乗りする（D-27。
    別ボリュームを増やさず logout/reset の分岐も増やさない）
```

### entrypoint → firewall（起動時の適用呼び出し）

```
起動シーケンス中に 1 度だけ実行:
  /usr/local/bin/init-firewall.sh          # 引数なし。OUTPUT チェインへブラックリストを適用
前提: NET_ADMIN/NET_RAW（cli が docker run で付与）、iptables/ipset/dig/curl/jq（イメージ同梱）
結果: 適用の成否に関わらず entrypoint は継続する（失敗は無視して起動を止めない）
```

### コンテナ → docker-proxy（HTTP Docker API）

```
GET/POST http://claude-dev-docker-proxy:2375/<docker-api>
  検査: POST /containers/create のボディ Binds/Privileged/NetworkMode/PidMode を検査し拒否 or 書換
  結果: 許可(透過) | 拒否(4xx) | /workspace 配下 bind を実ホストパスへ rewrite
```

### cli(orchestrate) → orchestrator（起動・復旧・設定）

```
claude-dev orchestrate [--fresh] ["<goal>"]           # コントローラ起動/attach/resume
  生存判定: コンテナ内の claude-orchestrator プロセス生存（pgrep 相当）で分岐
  設定: max_workers / stuck_limit / max_review_rounds / review_format_error_limit /
        worker_grace_seconds / merge_strategy / worker_permission_mode / reviewer_vendor
```

### orchestrator → worker / 対話Claude（プロンプト注入）

```
worker:     claude -p [--resume <session-id>] --model <opus|sonnet> --effort <high> ...
brainstorm/intervene: claude --append-system-prompt <brainstorming.md|intervene.md>
状態受け渡し: .orchestrator/{plan.json, control.json, state.json} + *.jsonl（機械のみ編集）
ORCHESTRATOR.md（あれば）を各プロンプト先頭へ前置
```

## UI設計 ※必須

本システムの UI はターミナル主体（Web GUI なし。ブラウザ確認は noVNC で提供するがアプリ UI ではない）。
接点は「ホスト CLI のコマンド体系」と「orchestrator の TUI」の 2 つ。

### 画面一覧

| 画面(slug) | 目的 | 主要項目 | 状態(loading/empty/error等) | 対応する要件 |
|---|---|---|---|---|
| cli-commands | コンテナ/認証/ポート/鍵の操作 | start/stop/list/attach/forward/unforward/ports/login/login-codex/logout/ssh-keys/orchestrate | 起動中/未セットアップ/エラー案内 | core/1,3,4,6 |
| orch-dashboard | 実行モードの俯瞰・worker 選択 | goal, worker 一覧(状態), ⏸要判断一覧, 直近サマリ, 仮定/要判断件数 | 実行中/一時停止/空(worker なし) | orchestration/19 |
| orch-brainstorming | ゴール/仕様を対話で固める | 対話Claude TUI, 番号付き選択肢 | 対話中 | orchestration/12,19 |
| orch-worker | worker のライブ出力 | claude -p ログ tail | 実行中/レビュー待ち/⏸要判断 | orchestration/14,15 |
| orch-intervention | 要判断1件への回答 | 質問・番号付き選択肢（日本語） | 回答待ち | orchestration/15,19 |
| orch-endmenu | 引き渡し不明時の選択 | 続ける/実行(実行可時のみ)/終了 | メニュー | orchestration/12,19 |

### 画面遷移（orchestrator）

```mermaid
stateDiagram-v2
  [*] --> Dashboard: orchestrate（ホーム表示）
  Dashboard --> Brainstorming: カーソル選択→Enter
  Brainstorming --> Execute: plan確定(execute)・/exit
  Brainstorming --> Dashboard: 実行不可→理由表示で戻す
  Execute --> Worker: ⏸以外をEnter
  Execute --> Intervention: ⏸をEnter
  Intervention --> Worker: 回答→/exit（同ウィンドウで実行復帰）
  Worker --> Execute: 完了(kill-window)
  Execute --> [*]: 全タスクdone（Slack完了）
```

- **カーソル選択→Enter 確定でのみ移動**（数字キー即移動・全画面再描画は行わない、D-17/要件19）。
- **抜け方は全対話モードで統一＝対話 Claude を `/exit`**。モード遷移時に日本語バナーを印字する。

## データモデル(全体)

| エンティティ | 所有モジュール | 概要 |
|---|---|---|
| plan.json（タスク計画・各タスクの kind/completion/status/attempt/session-id） | orchestrator | 実行の中核状態。機械が読み書き |
| control.json（execute/continue_brainstorming/abort、answer 記録） | orchestrator | モード引き渡し・介入回答 |
| state.json / *.jsonl（audit/assumptions/interventions） | orchestrator | 運用状態・追記型ログ |
| 認証ファイル（.credentials.json / .claude.json） | entrypoint(共有はcli) | claude-dev-auth ボリューム経由で共有 |
| codex 認証ファイル（auth.json） | entrypoint(共有はcli) | 同ボリュームの `codex/` 経由で共有（D-27）。`config.toml`・セッション履歴は共有せずコンテナ固有 |
| codex 設定（config.toml） | entrypoint | 共有しない。既定 3 鍵（`sandbox_mode`/`approval_policy`/`features.use_legacy_landlock`）を不在時は生成、存在時は不足鍵のみ追記（既存の値は不変。D-27 ⑥・core/12-5,12-6,12-9） |
| .claude-dev.yaml（ssh_keys） | cli | プロジェクト単位の SSH 鍵指定 |
| Docker リソース（claude-dev-net / 各ボリューム / イメージ） | cli, makefile, devcontainer | 命名は claude-dev- 接頭辞 |

## 主要フロー(モジュール横断)

```mermaid
sequenceDiagram
  participant U as 開発者
  participant CLI as cli
  participant EP as entrypoint
  participant DP as docker-proxy
  participant O as orchestrator
  U->>CLI: claude-dev start
  CLI->>EP: コンテナ起動（マウント/環境変数）
  EP->>EP: UID/GID追従・認証コピー・firewall・MCP/VNC・tmux
  U->>CLI: claude-dev orchestrate
  CLI->>O: コントローラ常駐起動/attach/resume
  O->>O: ブレスト→plan確定→worker並列（worktree）
  O->>DP: worker が docker 利用（検査・許可/拒否）
  O-->>U: Slack サマリ / 要判断通知
```

## エラーハンドリング方針

- **docker-proxy**: 危険操作は 4xx で拒否し理由を返す。判定不能は安全側（拒否）。
- **orchestrator**: LLM 起因の失敗（レビュー format error 等）は要件17の打切り規則で介入へ回す。
  中断は要件16のクリーン終了（コード0・状態保存）。plan/履歴は自動削除しない。
- **cli**: 前提不足（未セットアップ・認証なし・`.claude-dev.yaml` なし）は停止せず日本語で案内する。
- **人間向け表示は日本語**（要件19）。ファイル直接編集を促さない。

## テスト戦略

### レベル別方針

| レベル | 対象 | ツール/実行環境 | 方針(テストデータ・範囲・実行タイミング) |
|---|---|---|---|
| 単体 | docker-proxy の検査ロジック / orchestrator の状態・レビュー・モデル選択等 | `go test`（docker-proxy）, `go test -mod=vendor`（orchestrator） | 各 Go モジュールで実装同梱。PR/変更時に実行（[tech steering](../_steering/tech.md)） |
| 結合 | 「モジュール間インターフェース(契約)」の全 5 契約（cli→コンテナ/entrypoint / entrypoint→firewall / コンテナ→docker-proxy / cli(orchestrate)→orchestrator / orchestrator→worker・対話Claude） | `go test`（docker-proxy の API ボディ検査、orchestrator のプロンプト生成・`control.json` 検知）＋実機（コンテナ起動・`make orch-sample` 実走） | 契約ごとに担当モジュールを下表で定め、担当モジュールの 03-impl テスト対応表に結合レベルの行を置く。ホスト CLI（bash）側は自動テストランナーを持たないため、当該契約の手段は実機確認になる |
| E2E | ユースケース（下のシナリオ一覧） | 実機（`claude-dev` 実操作）＋ orchestrator 自己検証（`make orch-sample` で題材を scaffold し `claude-dev orchestrate` で実走） | シェル系は自動テストなし＝実機確認。orchestrator は題材を用意して実走・観測 |

備考: core/7-5（compose プロジェクト名の一意化）はシェル系のため自動テスト対象外。実機確認は「異なる 2 プロジェクトで同時に `claude-dev start` → 各コンテナで `COMPOSE_PROJECT_NAME` が別値になり、`docker compose` の生成リソース（ネットワーク／コンテナ名）がプロジェクト間で衝突しない」ことを確認する（cli/cli-mac が `docker run` に `-e COMPOSE_PROJECT_NAME` を付与）。

備考: core/12（同梱エージェント CLI）もシェル/Dockerfile 系のため自動テスト対象外。実機確認は
「配布 2 イメージで `codex --version` が、当該ビルドの prepare ジョブが解決し build-arg
`CODEX_VERSION` として渡した具体バージョン文字列と完全一致する」「対話シェル・`bash -c`・`docker exec` の
いずれからも `codex` が解決できる」ことを確認する（認証共有と**シェル実行の成否**〈12-4〉の実機確認は
E2E-6 が担う）。サンドボックス既定設定（12-5,12-6）は entrypoint の担当で、確認観点は「`config.toml` が
無いコンテナでは既定 3 鍵が生成される」「利用者が書き換えた `config.toml` を持つコンテナでは既存の鍵と値が
変わらず、不足していた既定鍵だけが追記される（再起動しても結果が変わらない）」の 2 点
（03-impl/entrypoint.md のテスト対応表が持つ）。12-7 は `docker run` に
`--security-opt` を付けない実装上の禁止事項で、cli/cli-mac の起動引数として確認する。12-9（明示
`--sandbox read-only` での成功）は landlock バックエンドの疎通が本質なので E2E-6 が担う（版更新で
`use_legacy_landlock` が撤去された場合の回帰検知も同じ観点）。

備考: core/1-6（stop 時の compose 片付け, D-24 ライフサイクル）もシェル系のため自動テスト対象外。実機確認は「コンテナ内で `docker compose up` → ホストで `claude-dev stop` → ラベル `com.docker.compose.project=<正規化NAME>` のコンテナと当該プロジェクトの compose デフォルトネットワークが消え、名前付きボリュームと共有の `claude-dev-net`／docker-proxy は残る」ことを確認する。VM モードは compose がゲスト内で完結するため対象外。

### 結合テスト対象

「モジュール間インターフェース(契約)」の全 5 契約を列挙する。担当は原則「呼び出し元」だが、本システムでは
**検証が観測可能な側**（呼び出し先）へ寄せている契約が 3 件ある（理由は下表の担当欄に併記）。ホスト CLI 側は bash で自動
テストランナーを持たないため、呼び出し元担当にすると全件が実機確認になり検証の所在が曖昧になるからである。

| 契約(呼び出し元→呼び出し先) | 検証観点 | 担当モジュール |
|---|---|---|
| cli → コンテナ/entrypoint | 環境変数・マウントが渡り、UID/GID が `/workspace` 所有者に追従し、認証（claude/codex）がコンテナローカルへコピーされ 30 秒書き戻しが働く | entrypoint（呼び出し元 cli は bash で自動テスト不可のため観測側が担当。手段は実機確認） |
| entrypoint → firewall | 起動時に FW が適用される | entrypoint |
| コンテナ → docker-proxy | 危険 bind/privileged/host mode 拒否・/workspace bind 書換・通常操作透過 | docker-proxy（観測側。`go test` で機械検証） |
| cli(orchestrate) → orchestrator | 生存判定による attach/resume 分岐・設定受け渡し | orchestrator（観測側。実 tmux＋実 claude を要するため手段は実機確認＝E2E-4/E2E-5） |
| orchestrator → worker / 対話Claude | プロンプト注入（instruction テンプレ・`ORCHESTRATOR.md` 前置・VM 前置）と `control.json` による受け渡し・消費 | orchestrator（orchestrator 側の生成・検知は `go test` で機械検証。実 `claude` プロセスとの結合は実機確認＝E2E-4） |

### E2Eシナリオ一覧

| シナリオID | 対応ユースケース | 検証するフロー | 優先度 |
|---|---|---|---|
| E2E-1 | UC-1 | `claude-dev start`（VNC あり/`--no-vnc`）→ /workspace マウント・認証・FW・tmux → claude 起動・再接続 | Must |
| E2E-2 | UC-2 | `claude-dev forward` → 8100〜割当・SSH トンネル → クライアントブラウザで表示・`ports` 確認 | Must |
| E2E-3 | UC-3 | コンテナ内 `docker run -v /:/host` 等 → docker-proxy が拒否／`/workspace` bind 許可／通常許可 | Must |
| E2E-4 | UC-4 | `orchestrate` → ブレスト→plan→worker 並列→要判断1件のみ待機・他継続→回答復帰→完了（`make orch-sample` で題材を scaffold し `claude-dev orchestrate` で実走） | Must |
| E2E-5 | UC-5 | 実行中に端末全終了→`orchestrate` 再実行→attach/resume・完了済み非再実行・plan/履歴保持 | Should |
| E2E-6 | UC-6 | `claude-dev login-codex` → デバイス認証 → 別プロジェクトで `start` → コンテナ内 `codex` が再ログイン不要で起動し、**codex が起こすシェルコマンドが成功して `/workspace` を読み書きできる**。さらに **landlock 疎通確認**（`codex sandbox --enable use_legacy_landlock -- /bin/true` が exit 0、同じ経路での書き込みは失敗）が通り、`--sandbox read-only` を明示した依頼で読み取りが成功する（12-9）。トークン更新が共有ボリュームへ書き戻り次のコンテナへ引き継がれる | Must |

## 設計判断と代替案

### 判断1:自作の外部制御ループ（Docker Agent 不採用）

- **採用:** コントローラがループを所有する外部制御ループ。L1 は claude から借りる。
- **却下した代替案:** Docker Agent（L1+L2 委譲配管）／Stop-hook 力技での連続走行。
- **理由:** 暴走しない・コンテキストを汚さない・再開可能。変化の速い依存を中核に据えると配布安定性にリスク（D-12）。

### 判断2:tmux 常駐（完全デーモン化しない）

- **採用:** コントローラを `orch-<project>-main:dashboard` で常駐。tmux サーバを「常駐の器」にする。
- **却下した代替案:** setsid の完全デーモン化。
- **理由:** 完全デーモン化はダッシュボード描画を別プロセス化し複雑。tmux なら 1 プロセスのまま端末破壊耐性を得る（D-14）。

### 判断3:認証はコピー＋同期（symlink 不採用）

- **採用:** 認証ファイル実体コピー＋30秒同期。claude（`.credentials.json`/`.claude.json`）と
  codex（`auth.json`）で同一方式・同一の同期ループを使う。
- **却下した代替案:** symlink 共有。
- **理由:** Claude Code のアトミック書き込み（tmp→rename）で symlink が壊れる（D-3）。codex の
  `auth.json` はその場書き換えのため symlink でも壊れないが、**方式を 2 つ持たない**ことを優先し
  コピー＋同期に揃える（同期ループ・logout・reset の分岐を増やさない）。トークンリフレッシュで内容が
  変わる点は claude と同じで、書き戻しは双方に必要（D-27）。

### 判断4:エージェント CLI の導入は「内容由来キー」で配布ステージの終端レイヤーに置く

- **採用:** `Dockerfile.claude` を 4 ステージに分ける——重い共通層を持つ `base`、VNC 資産を積む
  `vnc-base`(`FROM base`)、そして配布する 2 つの終端ステージ `claude-cli`(`FROM base`) /
  `claude-vnc`(`FROM vnc-base`)。Claude Code と Codex CLI の導入 `RUN` は**終端ステージの最終
  レイヤーにのみ**置き、キャッシュキーには具体バージョン（claude は `latest` チャネル、codex は npm
  registry の最新版を CI で解決した値）を使う（D-26／D-27）。
- **却下した代替案:** ①`base` の途中で導入したまま、日次タイムスタンプで cache-bust する
  ②`base` の途中で導入したまま、バージョンで cache-bust する ③導入をやめて実行時に自動更新させる。
- **理由:** `vnc-base` は `FROM base` で連なるため、`base` 途中の層を失効させると VNC の高コスト層
  （apt VNC 群・Chrome・`cargo install`）まで巻き込んで再ビルド・再 push・再 pull になる（①②が該当。
  ①は加えて新版が無い日も毎日失効する）。終端レイヤーへ移すと、失効の波及先がエージェント CLI の
  バイナリ層だけになり、鮮度（core/9 受入基準3・6）と pull の増分性（非機能:性能）を同時に満たせる。
  ③はファイアウォール下・オフライン起動で不確定になり、イメージが「同一構成の保証」を失うため却下
  （codex を `@latest` 直書きで焼く案も、文字列が変わらずキャッシュが永久ヒットして**中身だけ凍結**
  するため同様に却下。D-26 で実際に起きた事象）。
- **一般原則:** レイヤーチェーンに入れてよいのは**内容由来**の値（実バージョン等）に限る。時刻など
  内容と無関係に動く値を入れてはならない（`docs/knowledge/changing-label-busts-layer-cache.md`）。
  内容由来であっても、失効の波及範囲を最小化できる位置——依存される側ではなく終端——に置く。

### 判断5:Codex サンドボックスは既定で無効化し、読み取り専用用途だけ landlock で生かす

- **採用:** entrypoint が既定 3 鍵——`sandbox_mode = "danger-full-access"` /
  `approval_policy = "never"` / `[features] use_legacy_landlock = true`——を置く（D-27 ⑥）。
  `config.toml` 不在なら 3 鍵を生成し、存在するなら**書かれていない鍵だけを追記**して既存の値は
  書き換えない（core/12-5,12-6）。既定では codex 自前のサンドボックスを使わないが、`--sandbox
  read-only` を明示要求する呼び出し（コードレビュー・文書監査を codex に依頼する経路）だけは
  landlock バックエンドで成立させる（core/12-9）。`workspace-write` は landlock でも書き込みが
  失敗するため実用外とし、書き込みを伴う自動化・QA は `danger-full-access` で走らせる。
- **却下した代替案:** ①`docker run` に `--security-opt seccomp=unconfined --security-opt
  apparmor=unconfined` を足して bwrap を動かす ②`sandbox_mode = "workspace-write"` のまま運用する
  ③イメージに `config.toml` を焼き込む ④landlock を使わず、読み取り専用の依頼は常に「対象ファイルの
  内容をプロンプトへ添付し codex にシェルを使わせない方式」で回避する ⑤entrypoint が起動時に
  サンドボックス疎通確認を実行して警告を出す。
- **理由:** codex の Linux サンドボックスは bubblewrap 実装で、ユーザー名前空間の作成とマウント伝播の
  変更を要する。Claude コンテナは Docker 既定 seccomp と `docker-default` AppArmor の下で動くため、
  seccomp が `CLONE_NEWUSER` を拒否し、それを外しても AppArmor が `mount --make-rslave /` を拒否する
  2 段構えで bwrap が起動できない。②はこの状態を放置することであり、codex のシェルコマンドが例外なく
  失敗する（`exited 1`）。①は bwrap を動かせるが、隔離境界はコンテナ／ホスト間のみという前提（D-1）を
  支えている confinement 自体を外すことになり、生ソケット非マウント（D-2）等で守っている境界を弱めるため
  却下。コンテナ内の二重サンドボックスは元から前提にしていないので、claude 側の
  `permissions.defaultMode=bypassPermissions` と同じ扱いに揃えるのが構造的に一貫する。③は
  `~/.codex → /workspace/.codex` の symlink 化（プロジェクト単位の実体）より前に固定値を焼くことになり、
  プロジェクトごとに利用者が設定を変える余地を失うため却下。④は退避手段としては有効だが、恒久策に
  すると codex にファイルを読ませる経路（`codex exec review` 等）が使えないままになる。landlock が
  ユーザー名前空間を必要とせずコンテナの confinement 下で動くことを実測で確認できたため、内側の隔離を
  捨てずに済む④より上位の解を採った（④は `use_legacy_landlock` が撤去された場合の退避先として残す）。
  ⑤は codex を使わない利用者にも毎起動のコストがかかるため却下し、疎通確認は E2E-6 に持たせる。
- **副作用として設計に織り込む点:** 失敗が静かに起きる形（コマンド失敗をモデルが認識せず出力を捏造する、
  `codex doctor` も検知しない。**失敗しても `codex exec` の終了コードは 0**）だったため、E2E-6 は
  「起動する」ではなく**シェル実行が成功する**ところまで観測し、判定は成果物で行う
  （テスト戦略の E2Eシナリオ一覧）。`use_legacy_landlock` は codex 0.146.0 時点で deprecated であり
  版更新で撤去されうるため、E2E-6 に landlock の疎通確認を含めて回帰を検知する。

## 要件カバレッジ確認

| 要件(領域/番号) | 対応モジュール |
|---|---|
| core/1 コンテナ管理 | cli, entrypoint, devcontainer |
| core/2 UID/GID・共有 | entrypoint, cli |
| core/3 認証 | cli, entrypoint |
| core/4 SSH 鍵 | cli (mac 差分は cli-mac) |
| core/5 FW・ネットワーク | firewall, entrypoint, cli |
| core/6 ポートフォワード | cli, portsync |
| core/7 docker-proxy | docker-proxy, cli/cli-mac（7-5 compose プロジェクト名一意化） |
| core/8 VM モード | vm-mode |
| core/9 配布・ビルド | makefile, ghcr-workflow, devcontainer |
| core/10 macOS | cli-mac, makefile(install 判定) |
| core/11 ブラウザ確認 | entrypoint(11-1 の VNC/Chrome/noVNC 起動・11-2 MCP 設定), devcontainer(11-3 IBus-Mozc 同梱), container-tools(tmux), cli/cli-mac(11-1 のうち noVNC ポートの動的割当と URL 表示。分割定義の cli 行が持つ core/11 はこの範囲) |
| core/12 同梱エージェント CLI | devcontainer(導入), cli/cli-mac(login-codex, 12-7 `--security-opt` 不付与), entrypoint(認証コピー・同期, 12-4〜12-6,12-9 サンドボックス既定設定), ghcr-workflow(版解決)。※12-9 の landlock 疎通確認は E2E-6 が担う（`03-impl/e2e.md`。分割定義外の標準例外であり、モジュールではない） |
| orchestration/12〜19 | orchestrator, hooks(Slack) |
| orchestration/20 自己検証 | sample-project, orchestrator, makefile |
| core 非機能(セキュリティ/性能/保守/環境) | docker-proxy, devcontainer, ghcr-workflow(pull 増分性), cli/cli-mac |
| orchestration 非機能(耐障害/保守/性能/可観測) | orchestrator |

## 未解決事項(Open Questions)

- なし（要確認事項は decisions.md D-21〜D-23 に集約）
