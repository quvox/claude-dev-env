---
target: docs/03-impl/relations/MODULE-orchestrator-config.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
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
updated: 2026-08-02
summary: 実行設定を4段マージ(組込既定→ユーザー設定→workspace 設定→環境変数)で読み込み既定値で補完する
---

# MODULE-orchestrator-config 実行設定の読み込み

## 目的

並列数・再試行上限・統合方式といった運用パラメータを、コードを変えずに調整できるようにする
(FR-orch-03・FR-orch-06)。契約 `CTR-cli-orchestrator` が列挙する設定項目の実体である。

## 処理の流れ

1. `DefaultConfig` で組込既定を作る(`max_workers=5` / `stuck_limit=3` / `max_review_rounds=10` /
   `review_format_error_limit=2` / `worker_grace_seconds=10` / `merge_strategy=merge` /
   `worker_permission_mode=bypassPermissions` / `reviewer_vendor=claude`)。
2. `~/.config/claude-dev.yaml` があれば、その `orchestrator:` セクションを重ねる。
3. `/workspace/.orchestrator/config.yaml` があれば、さらに重ねる(下ほど強い)。
4. **最後に環境変数を重ねる(最強)。ただし効くのは Slack の資格情報だけ**である:
   `SLACK_BOT_TOKEN` は常に `os.Getenv` の値で上書きし(未設定なら空になる)、`SLACK_CHANNEL` は
   空でないときだけ上書きする。他の設定キーに環境変数の段は無い。
5. パースは stdlib のみの簡易 `key: value` パーサで行う(YAML ライブラリに依存しない)。
   **落ち方は2段階**: ファイルが無い・開けない・走査に失敗したときは `err != nil` でその段を
   **丸ごと適用しない**。ファイルは読めたが個々の値が型として不正なとき
   (`max_workers` に非数値や 0 以下 など)は `applyConfigKV` がキー単位で検証するので、
   **そのキーだけを適用せず、同じファイル内の正常なキーは適用する**。起動は止めない。
6. model / effort はここでは決めない(`models.go` のポリシー表が決める)。

## 呼び出され方

- 契機: `MODULE-orchestrator-main` が起動直後に1度だけ呼ぶ。
- 前提条件: なし(設定ファイルはすべて任意)。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| workspace | パス | 必須 | `<workspace>/.orchestrator/config.yaml` を探す基準 |

- 認可: コンテナ内のユーザ。

## 連携先と連携内容

連携先なし(ファイル読み込みのみ)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | マージ済みの設定構造体 |
| 永続化 | なし(読み取りのみ)。読む資源は `~/.config/claude-dev.yaml` と `/workspace/.orchestrator/config.yaml` |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 設定ファイルが存在しない | その段を飛ばす(既定のまま) | なし |
| 未知のキーがある | 無視する | 設定ミスに気づけない |
| 値が数値として解釈できない | その項目は既定値のままになる | 想定と違う並列数で動きうる |
| `worker_model` が書かれている | **DEPRECATED**。解析はするが使わない(model は `models.go` が決める) | 設定しても効果が無い |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | YAML ライブラリを足さず簡易パーサで済ませる(vendoring するモジュールを増やさない) | D0-orch-02 |
| 2 | model / effort を設定で変えられないようにする(工程別ポリシーを1か所=`models.go` に閉じるため) | D0-orch-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 簡易パーサのためネスト・リスト・引用符の扱いが限定的 | 複雑な設定は書けない | なし |
| `reviewer_vendor` は読むだけで未使用(常に Claude) | 別ベンダーレビューはフェーズ2 | なし |
| 単体テストが無い | マージ順の回帰を機械検出できない | なし |
