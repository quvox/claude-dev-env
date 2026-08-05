---
target: docs/03-impl/relations/MODULE-orchestrator-term.md
change: replace
sections:
  - "## 呼び出され方"
  - "## 戻り値・副作用"
  - "## 異常系"
deletes: []
reason: 引数表と戻り値が実シグネチャと違う(docs/issues/038 #16)。存在しない `until` の異常系がある(同 #17)。モードバナーの出力先が違う(同 #28)。tests に他機能を検証するテストが混じる(同 #29)
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
tests: orchestrator/term_test.go::TestResolveMenu_EnterPicksDefault, orchestrator/term_test.go::TestResolveMenu_ArrowThenEnter, orchestrator/term_test.go::TestResolveMenu_JKMovement, orchestrator/term_test.go::TestResolveMenu_NumberImmediate, orchestrator/term_test.go::TestResolveMenu_NoInputReturnsCurrent, orchestrator/term_test.go::TestSelectMenu_NonTTYReturnsDefault
updated: 2026-08-05
summary: 端末の raw モード制御・TTY 判定・メニュー選択を提供する
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。
     tests から orchestrator/term_test.go::TestBuildQuestion_NumbersOptions を外した
     (このテストは term.go のシンボルを呼ばず、orchestrator/controller.go:1147 の buildQuestion を
     検証している。038 #29)。同テストは MODULE-orchestrator-controller の tests へ移した。
     同じ性質のものが1件あったので併せて外した: orchestrator/term_test.go::TestTerminalConfirm_NonTTYContinue は
     orchestrator/main.go:194 の terminalConfirm を検証しており term.go のシンボルを呼ばない
     (D0-scope-06 の委任内。MODULE-orchestrator-main の tests へ移した)。 -->

## 呼び出され方

- 契機: `MODULE-orchestrator-main` の `defer`(終了時)、`MODULE-orchestrator-controller` が
  対話から戻ったときとメニューを出すとき、`MODULE-orchestrator-mode` の前景フォールバックから
  戻ったとき。
- 前提条件: `stty` が使えること(使えなければ端末制御は no-op に近い挙動になる)。
- 引数(実シグネチャは `selectMenu(title string, items []menuItem, def int) string`。
  `orchestrator/term.go:96`):

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| `title` | 文字列 | `selectMenu` で必須 | メニューの見出しとして1行そのまま出す | **検証しない**(空文字でも空行を出すだけ) |
| `items` | `[]menuItem` | `selectMenu` で必須 | **文字列の並びではない。** `menuItem` は `Value`(選ばれたときに返る文字列)/ `Label`(短い表示。空なら `Value` を表示に使う)/ `Desc`(1行説明)の3フィールド(`term.go:84`〜`:88`)。表示順がそのまま番号キー 1..9 に対応する | **検証しない**。**空スライスなら空文字を返して即座に戻る**(`:97`〜`:99`) |
| `def` | 整数 | `selectMenu` で必須 | 既定として選択しておく項目のインデックス。非 TTY と raw モード取得失敗のときはこの項目の `Value` が返る | **範囲外なら 0 に丸める**(`:100`〜`:102`) |
| `mode` | 文字列 | `printModeBanner` で必須 | `brainstorming` / `intervene` / `executing` のいずれか | **検証しない**。未知の値は該当する文面が無いので**何も出さない** |
| `args...` | 文字列の可変長 | `sttyRun` で必須 | `stty` へそのまま渡す引数列 | 検証しない。**非 TTY なら `stty` を起動せず `false` を返す**(`:49`〜`:51`) |

- 認可: 端末を見ている人間。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `selectMenu` は**選択された項目の `Value`(文字列)**(インデックスではない。項目が空なら空文字、非 TTY と raw モード取得失敗なら既定項目の `Value`)、`resolveMenu` も同じ文字列。`isTTY` は真偽値。**`rawKeyMode` は `(restore func(), ok bool)`** を返し(失敗時は no-op の `restore` と `ok=false`。`term.go:34`〜`:40`)、**`ttyRestoreSane` は戻り値を持たない**(`:44`)、**`sttyRun` は成否の真偽値**(`:48`〜`:56`)である。**この3つは `error` を返さない** |
| 永続化 | なし(端末の状態というプロセス外の状態を変える) |
| 発火するイベント | なし |
| ログ | **メニューは標準出力**(`selectMenu` の `draw` が `fmt.Fprint(os.Stdout, …)`。`term.go:131`)、**モードバナーは標準エラー**(`printModeBanner` が `fmt.Fprintf(os.Stderr, …)`。`term.go:75`)。**出力先が違う**ので、標準出力だけを取り込むとバナーが落ちる |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 非 TTY(パイプ・CI) | `selectMenu` は既定項目の `Value` を返し、`terminalConfirm` は続行を返す。`sttyRun` は `stty` を起動せず `false` を返す | 無人でも止まらない |
| **raw モードにできなかった**(`stty` が無い / 失敗する) | `rawKeyMode` が `ok=false` を返し、`selectMenu` は**プロンプトを出さずに**既定項目の `Value` を返す | 既定の選択で進む。キー操作は受け付けない |
| **入力が来ないまま待ち続ける** | **タイムアウトは無い。** `selectMenu` に `until` 引数もタイマーも無く、`os.Stdin.Read` が `n==0` を返す間は `continue` で読み直す(`term.go:137`〜`:142`。raw モードは VMIN=0 / VTIME=1 なので約 0.1 秒ごとに空読みが返る)。**人間がキーを押すまで戻らない** | メニューの前で無期限に待つ(非 TTY はそもそもこの経路に入らない) |
| 読み取りが `io.EOF` 以外のエラーになった | **現在選択中の項目の `Value` を返す**(`:139`〜`:141`) | 選択途中の値で進む |
| 対話から戻る経路で復元を忘れた | 端末が raw のまま残り、以降の行入力が読めなくなる。そのため `main.go` が経路によらず `defer ttyRestoreSane()` を張っている | - |
