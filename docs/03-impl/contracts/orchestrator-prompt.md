---
id: orchestrator-prompt
version: 1.0.0
updated: 2026-08-03
source:
  - docs/02-design/contracts/orchestrator-prompt.md
kind: other
impl: orchestrator/mode.go::Mode.ResolveArgs
summary: オーケストレーターが worker / 対話 Claude へ渡すプロンプトと受け取る結果の取り決め(実装側)
keywords: [契約, CTR, 実装]
verified:
  at: 2026-08-03
  version: 1.0.0
  against:
    - doc: docs/02-design/contracts/orchestrator-prompt.md
      version: 1.0.0
---

# CTR-orchestrator-prompt orchestrator → worker / 対話 Claude(実装)

- 実装: `orchestrator/mode.go::Mode.BrainstormingArgs` / `orchestrator/mode.go::Mode.ResolveArgs` /
  `orchestrator/mode.go::Mode.IntervenePrompt` / `orchestrator/mode.go::Mode.WriteLaunchScript`
  (対話モード)、`orchestrator/worker.go::Worker.BuildPrompt` /
  `orchestrator/worker.go::Worker.Dispatch`(worker)、
  `orchestrator/worker.go::ParseWorkerResult`(結果の解釈)
- 当事者: MOD-orchestrator → worker / 対話 Claude
- 対応する設計: `docs/02-design/contracts/orchestrator-prompt.md`

## 実装上の事実

| 項目 | 実際の値 | 定義箇所 |
|---|---|---|
| worker の起動 | 非対話実行。`--permission-mode bypassPermissions` を既定にする(ヘッドレスでは権限プロンプトに答える人間がいないため) | `orchestrator/worker.go::Worker.Dispatch` |
| 再開 | 保存したセッション ID を指定して同一 Attempt の続きから再開する | `orchestrator/worker.go::Worker.Dispatch` |
| 対話モードの指示 | `--append-system-prompt` で渡す。テンプレートは**イメージ同梱**でプロジェクト側に置かない | `orchestrator/mode.go::Mode.instructionPath`, `Mode.brainstormingInstr`, `Mode.interveneInstr` |
| プロジェクト方針の前置 | リポジトリルートに `ORCHESTRATOR.md` があれば各プロンプトの先頭へ前置する | `orchestrator/policy.go`(`MODULE-orchestrator-mode`) |
| 起動スクリプト | 対話モードは起動スクリプトを書き出して tmux ウィンドウで実行する。引数のクォートは専用のエスケープを通す | `orchestrator/mode.go::Mode.WriteLaunchScript`, `orchestrator/mode.go::shellSingleQuote` |
| worker 結果の解釈 | ストリーム JSON と素の出力の両方を受け付け、解釈できないものは失敗として扱う | `orchestrator/worker.go::ParseWorkerResult`, `extractFromClaudeEnvelope`, `resultFromStream` |
| レビュー結果 | 構造化出力(スキーマ強制)。散文は1回だけ再整形し、判定内容は変えない | `MODULE-orchestrator-review` |
| 打ち切り | 同一フォーマットエラーが `review_format_error_limit` 回続いたら介入へ回す | `MODULE-orchestrator-review` |
| 秘密情報 | 子プロセスの環境から通知トークンを除去する(worker と対話 Claude へ渡さない) | `MODULE-orchestrator-claude-exec` |
| 制御ファイル | 対話を起こす直前に古い指示を破棄してから待ち受ける | `MODULE-orchestrator-handoff`, `MODULE-orchestrator-state-intervention` |

## 設計との差異

差異なし。

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| worker の出力形式はエージェント CLI の版に依存する | 版が変わると解釈に失敗しうる。`ParseWorkerResult` は複数形式を受け付けることで緩和している | なし |
| 指示テンプレートがイメージ同梱のため、更新にはイメージの再取得が要る | プロジェクト側で差し替えられない(`ORCHESTRATOR.md` の前置のみが調整口) | なし |
