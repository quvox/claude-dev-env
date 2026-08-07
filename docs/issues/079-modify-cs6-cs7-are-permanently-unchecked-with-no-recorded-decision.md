---
id: 079-modify-cs6-cs7-are-permanently-unchecked-with-no-recorded-decision
type: modify
severity: 低
found: 2026-08-07
found_in: task-stop-session-spawned-containers のフェーズ2(`/task-doc` §4 の `check-changeset.py` 実行)
related: .claude/scripts/changeset-invariants.json, .claude/directions/change-set.md, docs/pendings.md
pattern: なし
pattern_survey: なし
summary: CS6(状態値の語彙)と CS7(失敗分類 ⇄ 試行回数)が未設定のまま毎回「未検査」を出し続けるが、要否を決めた記録がどこにも無い
---

# 079 CS6 / CS7 が「未検査」のままで、要否を決めた記録が無い

## 事象

`python3 .claude/scripts/check-changeset.py <new-features>` を実行すると、毎回次の2行が出る。

```
  CS6 状態値の語彙: 未検査 — 未設定(`state_vocab` と `dead_tokens` が空)
  CS7 失敗分類 ⇄ 試行回数: 未検査 — 未設定(`failure_classification` が無い)
```

`.claude/scripts/changeset-invariants.json` の `state_vocab` は `{}`、`dead_tokens` は `[]`、
`failure_classification` は `null` である(プロジェクト固有の
`changeset-invariants.local.json` は存在しない)。

規範は `.claude/directions/change-set.md` §6「CS5 / CS6 / CS7 — where their values come from」で
次のように定めている。

> **CS6 / CS7 do need configuration** … A project may legitimately have neither, so an
> unconfigured CS6/CS7 asserts nothing and prints 「未検査 — 未設定」 every run:
> **never OK, and never a nonzero exit.** … **if you decide this project needs neither,
> record that decision in `docs/pendings.md`** so 「見ていない」 and 「見た上で要らないと決めた」
> stop looking the same (原則8).

**その記録が `docs/pendings.md`(P-001〜P-005)にも `docs/issues/` にも無い。**
`grep -rln "CS6\|CS7\|state_vocab\|failure_classification" docs/issues/ docs/pendings.md` は
0件を返す。

再現手順:

1. `python3 .claude/scripts/check-changeset.py docs/tasks/<進行中のタスク>/new-features` を実行する。
2. 出力に CS6 / CS7 の「未検査 — 未設定」が出ることを確認する。
3. `docs/pendings.md` を開き、この2つの検査を要らないと決めた記録が無いことを確認する。

## 影響

**この2つの検査は、設定されるまで永久に何も主張しない。** 規範自身が
「**未検査は合格ではない**」と書いているのに、記録が無いため
**「まだ誰も見ていない」のか「見た上で要らないと決めた」のか**を、出力からも文書からも
区別できない。フェーズ2のゲート(`/task-doc` §4)は毎回この2行を見ることになり、
**読み飛ばす習慣がつくと、後で本当に必要になったときにも気づけない**。

severity を「低」とする根拠: 現時点で観測可能な被害は無い(検査が落ちることも、
誤った文書が通ることも無い)。壊れるのは「見ていない/要らないと決めた」の区別だけである。

## 原因の見当

- CS6 は「状態値の語彙」を検査する。本システムに状態機械らしきものは
  オーケストレーターのタスク状態(実行中 / レビュー中 / 待機 / 完了 / 失敗 / ブロック。
  `docs/02-design/system.md` の SCR-02)があり、**候補はある**(推測)。
- CS7 は「失敗分類 ⇄ 試行回数」を検査する。`FR-orch-04` 受入基準5 の `stuck_limit` と
  `CTR-orchestrator-prompt` の再試行規則が候補である(推測)。
- どちらも**設定すれば効かせられる可能性がある**が、値を決めるのは人間の判断であり、
  本 issue はその判断を求めるものである。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| CS6 / CS7 を効かせるか | 設定ファイルが空なので何も主張していない | `change-set.md` §6 は「要らないと決めたなら `docs/pendings.md` に記録する」とだけ定め、要否そのものは定めていない | **要確認**(人間が決める) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | **要らないと決めて `docs/pendings.md` に記録する**(P-006 として、何が不完全か・なぜ今は OK か・どうなったら解消が必要かを書く) | `docs/pendings.md` 1ファイル。検査の出力は変わらない(未検査のまま) |
| B | **CS6 に状態値の語彙を設定する**(オーケストレーターのタスク状態と、廃止済みの表記) | `.claude/scripts/changeset-invariants.local.json` の新設。既存文書に廃止表記が残っていれば違反として出る |
| C | **CS7 に失敗分類を設定する**(`CTR-orchestrator-prompt` の再試行規則の表を指す) | 同上。表の見出しと捕獲群の定義が要る |

**この issue はキット側の設定の問題であり、`docs/` の仕様そのものの欠陥ではない。**
B / C を採る場合は `/kit-improve` の案件になりうる。

## 経緯

- 2026-08-07 `task-stop-session-spawned-containers` のフェーズ2 で `check-changeset.py` を
  実行した際に発見。**当該タスクの範囲外**(セッション由来の資源の片付けとは無関係)なので
  起票して先へ進んだ。
