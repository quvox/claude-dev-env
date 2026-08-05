---
id: 064-modify-dsn-prompt-03-omits-the-common-prompt-prefixes
type: modify
severity: 中
found: 2026-08-05
found_in: /doc-check task-spec-measurability(独立レンズ docs の再監査が FR-orch-02 受入基準3 で検出したものを、02 側へ遡って確定)
related: DSN-prompt-03, CTR-orchestrator-prompt, docs/02-design/contracts/orchestrator-prompt.md, MODULE-orchestrator-worker, FR-orch-08, FR-orch-02
summary: DSN-prompt-03 が「プロンプトに載せるのは(4種)だけとする」と書いているが、実装の Worker.BuildPrompt はそれに加えて VMModePreamble・ORCHESTRATOR.md の内容・結果の出力形式指示を必ず書き込む。FR-orch-08 受入基準5 は ORCHESTRATOR.md の前置を要求しているので、02 の「だけ」は 01 とも実装とも食い違う
---

# 064 `DSN-prompt-03` の「だけ」が共通の前置き・後置きを数えていない

## 事象

`docs/02-design/contracts/orchestrator-prompt.md` の `DSN-prompt-03` は次のように書く。

```
- 判断: プロンプトに載せるのは **plan のゴール・完了条件・当該タスクの説明と完了条件・
  完了した依存タスクの結果要約・前回試行のフィードバック**だけとする。
```

実装(`orchestrator/worker.go` の `Worker.BuildPrompt`)は、この4種に加えて次を**必ず**書き込む
(2026-08-05 にコードで確認)。

| 実装が足しているもの | 実体 | それを要求している上流 |
|---|---|---|
| VM モードの周知 | `VMModePreamble()` を先頭へ | `FR-env-08`(VM モードの発見導線) |
| プロジェクト固有の判断基準 | `LoadProjectPolicy(w.Workspace)`(`ORCHESTRATOR.md` の内容)を先頭へ | **`FR-orch-08` 受入基準5**(「`ORCHESTRATOR.md` が存在する場合、その内容を各プロンプトの先頭へ前置しなければならない」) |
| 結果の出力形式の指示 | 固定文字列 `workerResultGuide` を末尾へ | 契約 `CTR-orchestrator-prompt`(結果の形式) |

同じ3つは `orchestrator/mode.go:74`・`:91`・`:167`(ブレインストーミング / 介入)でも前置される。

## なぜ問題か

`FR-orch-08` 受入基準5 は `ORCHESTRATOR.md` の前置を**要求している**。したがって
`DSN-prompt-03` の「だけ」を字義どおりに読むと、**02 の設計判断が 01 の受け入れ基準を否定する**。
実装は 01 に従っており、齟齬は 02 の文言の側にある。

## 経緯(なぜ今見つかったか)

`task-spec-measurability` が `FR-orch-02` 受入基準3 の測定不能語「必要な文脈だけ」を
`DSN-prompt-03` の列挙へ結び付けて測定可能にしようとしたとき、
**02 の不正確さが 01 の受け入れ基準(SHALL)へそのまま持ち上がりかけた**。
同タスクの `/doc-check` はこれを検出し、01 側は
「**タスク固有の文脈**を次の4種だけで構成する。全プロンプトに共通して前置・後置される要素は
この4種に数えない」と範囲を明示する形へ直した(実装と `FR-orch-08` の双方に一致する)。
**02 側の `DSN-prompt-03` は同タスクの影響範囲に無いので直していない。**

## 対処案

- **案A(推奨)**: `DSN-prompt-03` の「だけ」の対象を**タスク固有の文脈**に限定し、
  共通の前置き・後置き3種を明示的に列挙して「本判断の対象外」と書く。
  01 側(`FR-orch-02` 受入基準3)と同じ言い方に揃える。実装は変えない。
- **案B**: 実装から3種の前置き・後置きを外す。**`FR-orch-08` 受入基準5 に反するので採れない。**

案A は 02 の1節を書き替えるだけだが、`CTR-orchestrator-prompt` は認証済みなので
版と合格証の更新を伴う。独立したタスクで行う。
