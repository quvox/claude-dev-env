---
id: 062-modify-residual-fast-loop-wording-in-makefile-build-orchestrator
type: modify
severity: 中
found: 2026-08-05
found_in: /doc-check task-spec-measurability(合成ビューの C7 走査。`docs/issues/017` を閉じる直前に取りこぼしを実測)
related: MODULE-makefile-build-orchestrator, docs/03-impl/relations/MODULE-makefile-build-orchestrator.md, D0-scope-06, FR-orch-09, docs/issues/017
summary: docs/issues/017(relations に残る測定不能語)を閉じるタスクの走査から漏れた測定不能語が1件ある。MODULE-makefile-build-orchestrator.md:27 の「自己検証の高速ループが直接起動する」で、017 が同ファイルを「解消済み」と記録しているため 017 を削除すると追跡先が消える
---

# 062 `MODULE-makefile-build-orchestrator` に測定不能語「高速ループ」が残る

## 事象

`docs/03-impl/relations/MODULE-makefile-build-orchestrator.md` の「処理の流れ」2 に
次の記述がある(2026-08-05 に実測)。

```
2. `go build -o orchestrator .` でバイナリを明示的に出力する
   (`go build ./...` はバイナリを残さないため。自己検証の高速ループが直接起動する)。
```

「**高速**ループ」は程度語であり、何と比べて速いのか、どの所要時間を満たせば合格なのかが
定まらない。CLAUDE.md §8 は測定不能語を全層で禁じており、
「高速に」はその例示語そのものである。

## なぜ取りこぼされたか(重要)

`docs/issues/017`(仕様ドキュメントに残る測定不能語)は **`related` にこのファイルを挙げており**、
その表の該当行は次のように書いている。

| 箇所 | 判定 |
|---|---|
| `MODULE-makefile-build-orchestrator.md` 目的 | 「(イメージを作り直さずに)ビルド・検証するための入口」 | **解消済み**(「素早く」が無い) |

つまり 017 は **「目的」節の「素早く」だけ**を追跡対象にしており、
**同じファイルの「処理の流れ」節に別の測定不能語「高速」がある**ことを見ていない。
`task-spec-measurability` の再実測(memo の「2026-08-05 の再実測」)も
017 の表を出発点にしたため、同じ取りこぼしを引き継いでいる。

**`task-spec-measurability` が 017 を削除すると、この1件の追跡先が消える。**
本 issue はそれを引き取るために起票する。

## 影響

- `docs/03-impl/relations/` は原則2(コード ⇄ 03-impl の1:1)の当事者であり、
  実装の事実に還元できない程度語が残ると、次に読む実装者が判断を発明することになる。
- 実害は小さい(この文は `go build ./...` ではなく `go build -o` を使う**理由**の補足であり、
  受入基準にも契約にもぶら下がっていない)ので severity は「中」。

## 対処案

| # | 案 | 備考 |
|---|---|---|
| A | 実装の事実へ置換する。`make orch-sample` 系の自己検証がビルド成果物のパスを直接起動することを、パスと呼び出し元を挙げて書く | `D0-scope-06` の委任範囲(03 の散文をコードを正として直す)の内側。**推奨** |
| B | 括弧の補足ごと落とし、`go build -o` を使う理由を「`go build ./...` はバイナリを残さないため」だけにする | 情報は減るが測定不能語は消える |
| C | 何もしない | 017 を閉じた直後に同種の語が残るため、次の `/doc-check full` が同じ指摘を再生産する |

## 関連

- `docs/issues/017`(本 issue の親。`task-spec-measurability` が削除する)
- `D0-scope-06`(03 の散文をコードを正として直す委任。案A はこの範囲内)
