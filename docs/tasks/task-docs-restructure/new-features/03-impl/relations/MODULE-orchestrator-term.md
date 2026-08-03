---
target: docs/03-impl/relations/MODULE-orchestrator-term.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-orchestrator-term
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/term.go::ttyRestoreSane, orchestrator/term.go::selectMenu, orchestrator/term.go::printModeBanner, orchestrator/term.go::rawKeyMode, orchestrator/term.go::sttyRun, orchestrator/mode.go::isTTY
callers: MODULE-orchestrator-controller, MODULE-orchestrator-main, MODULE-orchestrator-mode
callees: なし
contracts: なし
design: DSN-mod-01, DSN-ui-01
requirements: FR-orch-08
tests: orchestrator/term_test.go::TestResolveMenu_EnterPicksDefault, orchestrator/term_test.go::TestResolveMenu_ArrowThenEnter, orchestrator/term_test.go::TestResolveMenu_JKMovement, orchestrator/term_test.go::TestResolveMenu_NumberImmediate, orchestrator/term_test.go::TestResolveMenu_NoInputReturnsCurrent, orchestrator/term_test.go::TestSelectMenu_NonTTYReturnsDefault, orchestrator/term_test.go::TestTerminalConfirm_NonTTYContinue, orchestrator/term_test.go::TestBuildQuestion_NumbersOptions
updated: 2026-08-02
summary: 端末の raw モード制御・TTY 判定・メニュー選択を提供する
---

# MODULE-orchestrator-term 端末制御とメニュー

## 目的

対話 claude と TUI が同じ端末を奪い合うため、モードの切り替えと復元を1か所に集約する
(FR-orch-08)。**復元を怠ると Enter が `\r` のままになり行バッファ読み取りが永久にブロックする**
ので、これは可用性に直結する。

## 処理の流れ

1. `isTTY()`(mode.go に定義)が標準入出力が端末かを判定する。
2. `rawKeyMode()` が `stty` を使って端末を raw モードにし、1キーずつ読めるようにする。
3. `selectMenu(options, default)` が番号付きの選択メニューを出す。↑↓ / jk で移動、Enter で確定、
   数字キーで即決。**非 TTY のときは既定値をそのまま返す**(停止しない)。
4. `printModeBanner(mode)` が現在のモードを端末へ表示する。
5. `ttyRestoreSane()` が `stty sane` 相当でカノニカルモードへ戻す。
6. すべての `stty` 呼び出しは `sttyRun` に集約する。

## 呼び出され方

- 契機: `MODULE-orchestrator-main` の `defer`(終了時)、`MODULE-orchestrator-controller` が
  対話から戻ったときとメニューを出すとき、`MODULE-orchestrator-mode` の前景フォールバックから
  戻ったとき。
- 前提条件: `stty` が使えること(使えなければ端末制御は no-op に近い挙動になる)。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `options` | 文字列の並び | `selectMenu` で必須 | 表示順がそのまま番号になる |
| `default` | 整数 | `selectMenu` で必須 | 非 TTY のときに返る値 |

- 認可: 端末を見ている人間。

## 連携先と連携内容

連携先なし(`stty` の実行は外部コマンド呼び出しであり、機能間の辺には現れない)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `selectMenu` は選択されたインデックス、`isTTY` は真偽値 |
| 永続化 | なし(端末の状態というプロセス外の状態を変える) |
| 発火するイベント | なし |
| ログ | 標準出力へメニューとモードバナー |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 非 TTY(パイプ・CI) | `selectMenu` は既定値を返し、`terminalConfirm` は続行を返す | 無人でも止まらない |
| 入力が来ないまま `until` に達した | 現在のカーソル位置を返す | 既定の選択で進む |
| `stty` が無い / 失敗する | エラーを握りつぶす | raw モードにできず、キー操作が効かない |
| 対話から戻る経路で復元を忘れた | 端末が raw のまま残り、以降の行入力が読めなくなる。そのため `main.go` が経路によらず `defer ttyRestoreSane()` を張っている | - |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 端末復元を `main.go` の `defer` に置き、経路によらず必ず通す | D0-orch-06 |
| 2 | 非 TTY では既定値を返して停止しない(無人実行と CI を壊さない) | D0-orch-06 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `term.go::resolveMenu` はテスト専用の純粋関数(`selectMenu` のキー操作を単体テスト可能にしたもの)で製品コードから呼ばれない | 静的解析では未到達に見える(コードのコメントに明示あり) | なし |
| `sttyRun` の `cmd.Run()`(term.go:54)が、静的解析では `Controller.Run` / `SessionManager.Run` への候補辺として現れる | 実在しない候補辺。標準ライブラリの `*exec.Cmd.Run` であり**棄却した** | なし |
