---
id: 058-bug-unknown-severity-passes-the-review-gate
type: bug
severity: 中
found: 2026-08-04
found_in: /doc-check ssot task-impl-depth(独立監査 Codex relations)。2026-08-05 に task-relations-code-sync が docs/issues/038 から切り出した
related: FR-orch-06, D0-orch-15, CTR-orchestrator-prompt, MODULE-orchestrator-review, docs/issues/034, docs/issues/015
summary: レビュー結果の severity の値域を検証しないため、綴り違いや別語彙の重大な指摘が「重大でない」扱いでゲートを通過する
---

## 事象

品質ゲートの検証は **`findings` キーが在るかどうかだけ**である
(`orchestrator/review.go:296`〜`:312` の `tryReviewResult`)。各 finding の必須項目も
**`severity` の値域も検証しない**。

一方で差し戻しの判定は完全一致である(`orchestrator/review.go:24`〜`:31`):

```go
func (r ReviewResult) HasSevere() bool {
	for _, f := range r.Findings {
		if f.Severity == "critical" || f.Severity == "major" { return true }
	}
	return false
}
```

したがって `Critical` / `CRITICAL` / `blocker` / `high` のような値を持つ指摘は
**`HasSevere` が偽**になり、`GateOutcome.Passed` が真で返って**タスクが `done` になる**。

## 影響

`FR-orch-06`(品質ゲート)は「重大な指摘があれば差し戻す」ことを要件としているが、
**レビュアが重大と申告しても、語彙が1文字違えば通過する**。

- 通過は**静かに**起こる。フォーマットエラーとしても数えられないので `review_format_error` も出ず、
  監査ログには「合格」として残る。**利用者が失敗に気づける観測点が無い。**
- `docs/issues/034` の裁定(2026-08-04。**ツールによるスキーマ強制は行わない** =
  `D0-orch-15` と `FR-orch-06` 受入基準3 をそう改めた)と組み合わせると、
  **形式の検証がどこにも無い**ことになる。034 が決めたのは「**強制**をしない」ことであって、
  「**検証もしない**」ことではない(値域の検証はプロンプト側の強制とは別の手段である)。
- 同種の欠陥が `docs/issues/015`(`needs_human.reason` が4区分以外だと介入が開かれず申告が失われる)
  にもある。**列挙値を受け取って完全一致で分岐し、外れ値を黙って捨てる**という同じ形である。

## 原因の見当

**推測**: 寛容パース(版差に耐えるため受理側を緩める)の方針を、
**判定に使う列挙値**にも適用してしまった。契約(`CTR-orchestrator-prompt`)は
`severity` を `critical` / `major` / `minor` の列挙と定めており、受理側が緩いことと
**列挙外の値を黙って無視してよいこと**は別である。

## 正はどちらか

**要検討**(人間の判断が要る)。次の2つの読み方があり、どちらを採るかで直す場所が変わる。

1. **実装が誤り**: 契約が列挙と定めている以上、列挙外は「解釈できない」として扱うべきである
   → 未知の `severity` をフォーマットエラーとして数える(既存の再整形・打ち切りの経路に乗る)。
2. **契約が不足**: 未知の値をどう扱うかを契約が書いていないのが問題である
   → `CTR-orchestrator-prompt` に「列挙外の `severity` は `critical` として扱う」(安全側)
   あるいは「`minor` として扱う」(現行)を明記する。

**安全側は「未知は重大として扱う」**である(品質ゲートは通す方向に外すより止める方向に外す方が
被害が小さい)が、これは `FR-orch-06` の受入基準に触れるので **01 起点の判断**になる。

## 対処案

| 案 | 内容 |
|---|---|
| A | 未知の `severity` を**フォーマットエラーとして数える**(`review_format_error` → 再整形1回 → 上限で介入)。既存の経路に乗るので新しい状態が増えない |
| B | 未知の `severity` を **`critical` とみなす**(安全側に倒す)。`FR-orch-06` の受入基準に1行足す |
| C | 契約どおり `minor` 扱いのままにし、**その事実を受入基準に明記する**(現行実装が正) |

いずれも `docs/issues/015` と**同じ形の欠陥**なので、同じタスクで方針を1つに決めるのが安い
(「列挙値を受け取ったとき、列挙外をどう扱うか」の一般方針)。

## 経緯

- 2026-08-04 `docs/issues/038` #5 として起票。人間が案B(記述を直し、コード修正は別タスク)で裁定し、
  `MODULE-orchestrator-review` の処理の流れ3 に事実を明記した。
- 2026-08-05 `task-relations-code-sync` の `/doc-check` が、**`038` を削除すると本欠陥の追跡先が
  消える**ことを検出した(`038` は「記述の乖離」の issue として起票され、
  `03-impl/index.md` の「実装の欠陥として起票済み」の集計にも入っていなかった)。
  そこで本 issue として切り出した(同タスクの決定シート #8)。
  **記述側(`MODULE-orchestrator-review` の処理の流れ3)の参照先は本 issue へ付け替える。**
