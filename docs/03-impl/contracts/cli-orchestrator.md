---
id: cli-orchestrator
version: 1.0.0
updated: 2026-08-03
source:
  - docs/02-design/contracts/cli-orchestrator.md
kind: other
impl: claude-dev::main#orchestrate
summary: ホスト CLI(orchestrate)がオーケストレーターを起動・合流させるときの取り決め(実装側)
keywords: [契約, CTR, 実装]
verified:
  at: 2026-08-03
  version: 1.0.0
  against:
    - doc: docs/02-design/contracts/cli-orchestrator.md
      version: 1.0.0
---

# CTR-cli-orchestrator ホスト CLI(orchestrate) → orchestrator(実装)

- 実装: `claude-dev::main#orchestrate` / `claude-dev-mac::main#orchestrate`(発行側)、
  `orchestrator/main.go::main`(受け側)、`orchestrator/config.go::LoadConfig`(設定の解釈)
- 当事者: MOD-cli-orchestrate → MOD-orchestrator
- 対応する設計: `docs/02-design/contracts/cli-orchestrator.md`

## 実装上の事実

| 項目 | 実際の値 | 定義箇所 |
|---|---|---|
| 起動 | コンテナ内で `claude-orchestrator` を起動する。引数はゴール文字列(省略可)と `--fresh` | `claude-dev::main#orchestrate`, `orchestrator/main.go::main` |
| 生存判定 | `pgrep` 相当のプロセス存在で判定する(`tmux has-session` では判定しない) | `claude-dev::main#orchestrate` |
| セッション名の提示 | orchestrator が `--print-main-session` を持ち、CLI 側が名前を推測しなくて済む | `orchestrator/main.go::main` |
| コンテナ未起動(Linux) | `CLAUDE_DEV_NO_ATTACH=1` を付けて `start` を再帰的に呼んでから続行する | `claude-dev::main#orchestrate` |
| コンテナ未起動(macOS) | 先に `claude-dev start` を実行するよう表示して `exit 1` | `claude-dev-mac::main#orchestrate` |
| 空き殻セッション(Linux) | `kill-session` してから新規起動する | `claude-dev::main#orchestrate` |
| 設定の読み込み | **4段マージ(弱い順)**: ① 組込既定(`DefaultConfig`)→ ② `~/.config/claude-dev.yaml` の `orchestrator:` セクション → ③ `<workspace>/.orchestrator/config.yaml`(セクション無しのフラット)→ ④ 環境変数。**④ は Slack の資格情報だけに効く**(`SLACK_BOT_TOKEN` は常に環境の値で上書きし、`SLACK_CHANNEL` は空でないときだけ上書きする)。**段の落ち方は2段階**: ②③ のファイルが無い・開けない・走査に失敗したときは**その段を丸ごと適用しない**。ファイルは読めたが個々の値が型として不正なとき(`max_workers` に非数値や 0 以下 など)は**そのキーだけを適用せず、同じファイル内の正常なキーは適用する**(`applyConfigKV` がキー単位で検証する)。いずれの場合も起動は止めない | `orchestrator/config.go::LoadConfig`(`:67`〜`:90`), `orchestrator/config.go::DefaultConfig`, `orchestrator/config.go::applyConfigKV` |
| 設定キー | `max_workers` / `stuck_limit` / `max_review_rounds` / `review_format_error_limit` / `worker_grace_seconds` / `merge_strategy` ほか | `orchestrator/config.go:97`〜`125` |
| モデル・effort | **設定では変えられない**。ポリシー表から決める | `orchestrator/models.go`(`MODULE-orchestrator-claude-exec`) |
| 再開/新規の判定 | plan の完了状況で判定する(専用のフラグやマーカーを持たない) | `orchestrator/state.go`, `orchestrator/plan.go` |

## 設計との差異

| 項目 | 設計(02) | 実装(03) | どちらが正か |
|---|---|---|---|
| 実行中の run への再接続(macOS) | 生存判定で合流する | **macOS 版は生存判定を持たず**、新しいウィンドウでコントローラがもう1つ起動しうる。`claude-dev attach` で入り直す運用で回避している | **実装が現状**。設計の期待(OS によらず同じ観測可能な結果。`FR-env-10` 受け入れ基準4)を満たしていないため、`docs/issues/003-future-macos-orchestrator-scope.md` で追跡する |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| macOS でコントローラの生存判定が無い | 二重起動が起きうる | `docs/issues/003-future-macos-orchestrator-scope.md` |
