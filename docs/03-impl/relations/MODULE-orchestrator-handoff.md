---
id: MODULE-orchestrator-handoff
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/handoff.go::Handoff.Consume, orchestrator/handoff.go::Handoff.WaitConsume, orchestrator/handoff.go::Handoff.DiscardStale
callers: MODULE-orchestrator-controller
callees: MODULE-orchestrator-state-intervention
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-01, FR-orch-04
tests: orchestrator/handoff_test.go::TestWaitConsume_ReturnsWhenControlAppears, orchestrator/handoff_test.go::TestWaitConsume_UntilEndsWithoutControl
updated: 2026-08-02
summary: TUI と制御ループの間で介入指示を受け渡す
---

# MODULE-orchestrator-handoff 対話 claude からの受け渡し

## 目的

対話している claude が「次に何をしてほしいか」をコントローラへ伝える唯一の経路
(FR-orch-01・FR-orch-04)。プロセスが別なので、契約 `CTR-orchestrator-prompt` が定める
`control.json` をファイルとして受け渡す。

## 処理の流れ

1. `Consume()` が `control.json` を読み、内容(`Control{Request, InterventionID, TS}`)を返して
   ファイルを削除する。読み書きは `MODULE-orchestrator-state-intervention` の
   `LoadControl` / `DeleteControl` を通す。
2. `WaitConsume(until)` がポーリングで `control.json` の出現を待つ。`until` が真になったら
   control が無くても戻る(対話ウィンドウが消えた・ペインが死んだ場合の停止条件)。
3. `DiscardStale()` が、対話を起こす直前に残っている `control.json` を破棄する
   (前回の指示を新しい対話の結果と取り違えないため)。
4. 書き込み側(対話 claude)は一時ファイル → rename の原子的操作で置く。

## 呼び出され方

- 契機: `MODULE-orchestrator-controller` がブレインストーミングまたは介入解決の対話を起こす前
  (`DiscardStale`)と、対話の終了を待つとき(`WaitConsume`)。
- 前提条件: `.orchestrator/` が読み書きできること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `until` | `func() bool` | `WaitConsume` で必須 | 真を返すとポーリングを打ち切る |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

### MODULE-orchestrator-state-intervention

- 何のために呼ぶか: `control.json` の読み取り(`LoadControl`)と削除(`DeleteControl`)のため。
- 何を渡すか: なし(パスは Store が持つ)。 / 何を受け取るか: `Control` 構造体とエラー。
- **失敗したときどうなるか**: 読めなければ「未消費」として扱い、次のポーリングで再試行する。
  削除に失敗すると同じ指示を二重に消費しうる。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `Control{Request, InterventionID, TS}` と、消費できたかどうか |
| 永続化 | `control.json` の**削除**。書き込みは対話 claude 側が行う(この機能は読んで消す側) |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 対話が control を残さずに終了した | `until`(ウィンドウ消失 / ペイン死亡)で `WaitConsume` が戻り、control 無しを返す | controller が `selectMenu` で人間に選ばせる |
| 前回の `control.json` が残っている | 対話を起こす直前の `DiscardStale` で破棄する | 取り違えが起きない |
| JSON が壊れている | 読み取りエラーになり未消費として扱う | ポーリングが続き、`until` で打ち切られる |
| 書き込みの途中で読んだ | 書き込み側が一時ファイル → rename の原子的操作を使うため、途中状態は見えない | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | プロセス間の受け渡しをファイル1本に限定する(ソケットやポートを増やさない) | D0-orch-02 |
| 2 | 対話を起こす直前に必ず `DiscardStale` を通す(古い指示の誤消費を構造的に防ぐ) | D0-orch-04 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| ポーリング方式(inotify を使わない) | 反応にポーリング間隔ぶんの遅延がある | なし |
