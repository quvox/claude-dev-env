---
target: docs/03-impl/relations/MODULE-orchestrator-streamlog.md
change: replace
sections:
  - "## 処理の流れ"
  - "## 異常系"
  - "## 実装上の判断"
deletes: []
reason: 「未知の種別はそのまま出す」と書くが有効な JSON の未知イベントは破棄される(docs/issues/038 #23 = 032 #13)。あわせて 032 #3(callees に oneline が無い)が誤検知である理由を本文に明記する
id: MODULE-orchestrator-streamlog
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/streamlog.go::newStreamPrettyWriter, orchestrator/streamlog.go::streamPrettyWriter.Write
callers: MODULE-orchestrator-claude-exec
callees: なし
contracts: なし
design: DSN-mod-01, DSN-ui-01
requirements: FR-orch-08
tests: orchestrator/streamlog_test.go::TestFormatStreamLine, orchestrator/streamlog_test.go::TestStreamPrettyWriter_SplitsAndBuffersPartialLines
updated: 2026-08-05
summary: Claude の stream-json 出力を人が読める形へ整形する
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。frontmatter は `updated` の日付以外変更なし。

     ★docs/issues/032 #3(「callees: なし は誤りで oneline を呼んでいる」)は**誤検知として棄却する**:
     `orchestrator/dashboard.go::oneline` は docs/03-impl/features.md:145 で
     「畳み込む/薄いユーティリティ。単独で仕様として意味を持たない」と判定済みの共有関数であり、
     同一モジュール(MOD-orchestrator)内の畳み込み対象である。
     .claude/directions/relations.md §3 は callees を「**モジュール境界を跨ぐ**呼び出し」と定め、
     畳み込んだ同一モジュールのヘルパは載せないと明記している。したがって `callees: なし` が正しい。
     代わりに、その事実(共有ユーティリティを使っていること)を処理の流れ5 に書いた。 -->

## 処理の流れ

1. `newStreamPrettyWriter(out)` が `io.Writer` をラップした整形ライタを作る。
2. `streamPrettyWriter.Write(p)` が受け取ったバイト列を改行で区切って処理する。
   行が途中で切れている場合は内部バッファに溜め、次の `Write` で続きを結合する。
3. 完成した1行ごとに `formatStreamLine` が**外側イベントの `type` で分岐する**
   (`orchestrator/streamlog.go:88`〜`:113`):
   - `system` かつ `subtype == "init"` → `⏺ worker 起動（model: …）`(モデル名が取れないときは
     `⏺ worker 起動`)。`system` の他の `subtype` は**空文字**にする。
   - `assistant` / `user` → `formatContent` が content ブロックを整形する
     (text はそのまま、`tool_use` は `⏺ 名前(要約)`、`tool_result` は `⎿ …`)。
   - `result` → `is_error` が真なら `──── worker 終了（エラー） ────`、偽なら
     `──── worker 完了 ────`。
   - **上記以外の `type` は `default: return ""` で破棄する**(`:111`〜`:112`)。
     **未知の種別を素通しするのではない。** 素通しになるのは**そもそも JSON として解釈できない行**
     だけである(`:85`〜`:86`)。
4. 整形結果が空文字でなければ、ラップした `io.Writer` へ書く。
5. 要約の1行化には `orchestrator/dashboard.go::oneline` を使う(`:159` / `:233`)。
   **これは `callees` に現れない**: `oneline` は同一モジュール(`MOD-orchestrator`)内の
   薄い整形ユーティリティとして**機能へ畳み込む**と判定されている
   (`docs/03-impl/features.md` の「到達しない関数についての判断」表)。
   `MODULE-orchestrator-controller` / `-dashboard` も同じ関数を使う(共有関数)。

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 行が途中で切れて届く | 内部バッファに溜め、次の `Write` で結合して処理する | 整形が壊れない |
| JSON として解釈できない行 | **そのまま素通しする**(`:85`〜`:86`。コード側のコメントも「何も黙って失われないように verbatim で出す」と明示) | ログに生の行が混じる |
| **有効な JSON だが `type` が未知** | **空文字を返して破棄する**(`:111`〜`:112` の `default`)。`system` の未知の `subtype` も同じく破棄する(`:101`) | **その行は整形ログに現れない。** 解析は生 stream-json 側で行うので結果には影響しないが、tail 表示からは黙って消える |
| **出力先への書き込みが失敗した** | **エラーを捨てる**(`_, _ = io.WriteString(...)`)。`Write` は常に `(len(p), nil)` を返すため、`io.MultiWriter` は中断せず**解析用バッファへの書き込みは続く** | **失敗はどこにも現れない**(整形ログの一部または全部が欠けるだけで、結果の解析には影響しない)。閾値の外: **この機能は表示専用**であり(「目的」に明記)、解析は生 stream-json 側で行うため、被害はダッシュボードの tail 表示の欠落に限られる |
| 出力先を開けなかった(ファイル作成に失敗) | この機能は呼ばれない。呼び出し元(`MODULE-orchestrator-claude-exec`)が整形ライタを挟まず解析用バッファだけへ流す | 同上(`MODULE-orchestrator-claude-exec` の異常系「ログファイルを作れない」に従う) |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 整形と解析を分離する(整形の失敗が結果解釈に影響しないようにする) | D0-orch-06 |
| 2 | **素通しにするのは「JSON として解釈できない行」だけ**とし、**有効な JSON で `type` が未知のものは破棄する**(整形ライタは表示専用であり、解析は生 stream-json 側が行うため。情報の保全は解析側の責務) | D0-orch-06 |
