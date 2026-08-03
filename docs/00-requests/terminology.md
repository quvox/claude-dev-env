---
id: terminology
version: 1.0.0
updated: 2026-08-03
source:
  - docs/00-requests/request.md
summary: 本システムで使う語の定義・英語表記(識別子)・使ってはいけない言い方
keywords: [用語集, 識別子, 表記ゆれ]
verified:
  at: 2026-08-03
  version: 1.0.0
  against:
    - doc: docs/00-requests/request.md
      version: 1.2.0
---

# 用語集

| 用語 | 定義 | 英語表記(識別子) | 使ってはいけない言い方 |
|---|---|---|---|
| claude-dev | ホスト側 CLI。コンテナのライフサイクル・認証・ポート・SSH 鍵を操作する。Linux は `claude-dev`、macOS は `claude-dev-mac`(`make install` が OS を判定して symlink を統一する) | `claude-dev` / `claude-dev-mac` | 「CLIツール」単独表記 |
| Claude コンテナ | プロジェクトごとに起動する開発用コンテナ。ブラウザ確認あり(`claude-dev-claude-vnc`)/なし(`claude-dev-claude`) | `claude-dev-<project>` | — (「プロジェクトコンテナ」は同義。文脈で使い分ける) |
| Codex CLI | OpenAI 製のコーディングエージェント CLI(npm パッケージ `@openai/codex`、コマンド名 `codex`)。Claude コンテナに同梱し、`codex login --device-auth` で認証する。認証ファイルは `~/.codex/auth.json` | `codex` | 本文で `codex` と書く(コマンド名を指すときのみ可) |
| Codex サンドボックス | Codex CLI がシェルコマンドを実行する際に張る自前の隔離機構。強度は `config.toml` の `sandbox_mode`(`read-only` / `workspace-write` / `danger-full-access`)で決まる。Linux には bubblewrap(既定。Claude コンテナ内では起動できない)と landlock(`features.use_legacy_landlock` で選ぶ。読み取り専用のみ実用)の 2 バックエンドがある | `sandbox_mode` | bubblewrap / bwrap / landlock は実装名。方針を語るときは「Codex サンドボックス」と書く |
| docker-proxy | Docker Socket Proxy。生ソケットを直接使わせず、危険な Docker API を拒否する Go 製リバースプロキシ。全 Claude コンテナで共有する | `claude-dev-docker-proxy` | 「プロキシ」単独 |
| forward プロキシ | `claude-dev forward` が立てる `fwd-<name>-<port>` の socat コンテナ。Web アプリのポート中継用 | `fwd-<name>-<port>` | docker-proxy と混同する書き方 |
| DooD | Docker-outside-of-Docker。コンテナがホストの Docker デーモンを(docker-proxy 経由で)使う既定方式 | `dood` | DinD(本構成では非採用)と混同する書き方 |
| VM モード | オプトイン(`--vm`)。ゲスト VM(QEMU+virtiofs)内でネイティブ Docker を動かす層構成 | `vm-mode` | — |
| オーケストレーター | プロジェクトに1体立てる AIオーケストレーター。ブレインストーミング/実行の2モードを持つ「1実体」 | `orchestrator` | リードエージェント(旧称) |
| コントローラ | オーケストレーターの外部制御ループ本体(Go 実装。`orchestrate` で起動し tmux に常駐する) | `controller` | — |
| worker | 実装/レビューを行うコーディングエージェント(`claude -p`)。git worktree で分離する | `worker` | ワーカー、コーディングエージェント(同義だが表記は worker に統一) |
| ブレインストーミングモード | 人間×対話 Claude でゴール/仕様を固める検討モード(自動化しない) | `brainstorming` | ブレスト(本文では正式名を使う) |
| 実行モード | plan の各タスクを worker へ並行ディスパッチして自律実装するモード | `execute` | — |
| 介入 | 実行中に要判断が出たタスク1件を保留し、その worker ウィンドウで対話 Claude に諮ること | `intervention` | ストップ・ザ・ワールド(旧廃止方式) |
| 介入トリガー | 人間の判断を仰ぐ5条件(重大判断/曖昧さ/行き詰まり/方針分岐/前提崩れ) | `trigger` | — |
| 運用状態 | `.orchestrator/` に置く `plan.json` / `control.json` / `state.json` と追記型ログ。機械が読み書きし、人間は直接編集しない | `.orchestrator/` | — |
| ORCHESTRATOR.md | リポジトリルートに置く任意のプロジェクト固有方針(コミット対象。運用状態とは別) | `ORCHESTRATOR.md` | — |

## 判断に迷いやすい区別

| A | B | 何が違うか |
|---|---|---|
| docker-proxy | forward プロキシ(socat) | 前者は Docker API を検査・制限する共有プロキシ。後者は Web アプリのポートを中継する使い捨てコンテナ |
| DooD(既定) | VM モード | DooD はホストの Docker デーモンを proxy 経由で使う軽量既定。VM モードは VM 内ネイティブ Docker(bind/compose/privileged 可)でオプトイン |
| ブレインストーミングモード | 実行モード | 前者は人間主導・同期・自動化しない検討。後者は自律・並列の実装。境界は仕様ドキュメント |
| 仕様(`docs/`) | 運用状態(`.orchestrator/`) | 固まった仕様は `docs/` に、進捗・仮定・plan 等の運用状態は `.orchestrator/` に置く |
| Codex サンドボックス | Claude コンテナの隔離 | 前者は codex がコンテナ内で自前に張る隔離(既定は無効化。読み取り専用を要求する呼び出しのためだけに landlock を残す)。後者はコンテナ/ホスト間の隔離境界(唯一の境界であり緩めない) |
| Codex CLI の同梱 | 異種ベンダー worker の常用 | 前者は開発者がコンテナ内で codex を使える状態にすること(決定済み)。後者はオーケストレーターが worker/レビューアーとして codex を常用すること(未決) |
