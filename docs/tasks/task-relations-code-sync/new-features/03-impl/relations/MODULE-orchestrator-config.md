---
target: docs/03-impl/relations/MODULE-orchestrator-config.md
change: replace
sections:
  - "## 処理の流れ"
deletes: []
reason: 組込既定の列挙が 8 項目で worker_model と SlackChannel が落ちている(docs/issues/032 #14)。「0 以下など」の一般化が worker_grace_seconds に当てはまらない(同 #15)
id: MODULE-orchestrator-config
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/config.go::LoadConfig, orchestrator/config.go::DefaultConfig
callers: MODULE-orchestrator-main
callees: なし
contracts: CTR-cli-orchestrator
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-03, FR-orch-06, FR-orch-07
tests: なし(未実装。config.go に対応する単体テストが無い)
updated: 2026-08-05
summary: 実行設定を4段マージ(組込既定→ユーザー設定→workspace 設定→環境変数)で読み込み既定値で補完する
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。frontmatter は `updated` の日付以外変更なし。 -->

## 処理の流れ

1. `DefaultConfig` で組込既定を作る(`orchestrator/config.go:50`〜`:62`。**10 項目**):
   `max_workers=5` / `stuck_limit=3` / `max_review_rounds=10` / `review_format_error_limit=2` /
   `worker_grace_seconds=10` / **`worker_model=sonnet`** / `reviewer_vendor=claude` /
   `merge_strategy=merge` / `worker_permission_mode=bypassPermissions` /
   **`SlackChannel=DefaultSlackChannel`(`U5SJG0XEK`。`config.go:48`)**。
2. `~/.config/claude-dev.yaml` があれば、その `orchestrator:` セクションを重ねる。
3. `/workspace/.orchestrator/config.yaml` があれば、さらに重ねる(下ほど強い)。
4. **最後に環境変数を重ねる(最強)。ただし効くのは Slack の資格情報だけ**である:
   `SLACK_BOT_TOKEN` は常に `os.Getenv` の値で上書きし(未設定なら空になる)、`SLACK_CHANNEL` は
   空でないときだけ上書きする。他の設定キーに環境変数の段は無い。
5. パースは stdlib のみの簡易 `key: value` パーサで行う(YAML ライブラリに依存しない)。
   **落ち方は2段階**: ファイルが無い・開けない・走査に失敗したときは `err != nil` でその段を
   **丸ごと適用しない**。ファイルは読めたが個々の値が受理できないときは
   `applyConfigKV` がキー単位で検証するので、**そのキーだけを適用せず、同じファイル内の
   正常なキーは適用する**。起動は止めない。**受理する範囲はキーごとに違う**:
   `max_workers` / `stuck_limit` / `max_review_rounds` / `review_format_error_limit` は
   非数値と `n <= 0` を捨てるが、**`worker_grace_seconds` は `n >= 0` を受理するので 0 は有効値**
   である(`config.go:113`〜`:115`。0 は「猶予なしで即座に強制終了」を意味する)。
   文字列のキー(`worker_model` / `merge_strategy` など)は**空文字でないことだけ**を見る。
6. model / effort はここでは決めない(`models.go` のポリシー表が決める)。
