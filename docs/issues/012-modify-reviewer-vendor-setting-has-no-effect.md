---
id: 012-modify-reviewer-vendor-setting-has-no-effect
type: modify
severity: 中
found: 2026-08-03
found_in: task-impl-depth のドライラン パス2(コード精読。issue 004 の観点「契約の型」)
related: CTR-cli-orchestrator, MODULE-orchestrator-config, MODULE-orchestrator-review, FR-orch-06
summary: 設定 reviewer_vendor は読み込まれるが製品コードから一度も参照されず、レビュアのベンダーを切り替えられない
---

# 012 `reviewer_vendor` 設定が実装から参照されていない

## 事象

`orchestrator/config.go` は `reviewer_vendor` を解析して `Config.ReviewerVendor` に格納する
(`:32` 宣言 / `:59` 既定値 `"claude"` / `:121-123` 解析)。しかし**製品コードにこのフィールドを
読む箇所が1つも無い**。

```
$ grep -rn "ReviewerVendor" orchestrator/ --include='*.go'
orchestrator/config.go:32    ReviewerVendor     string // claude | codex
orchestrator/config.go:59        ReviewerVendor:         "claude",
orchestrator/config.go:121        case "reviewer_vendor":
orchestrator/config.go:123                cfg.ReviewerVendor = v
```

したがって `reviewer_vendor: codex` と設定してもレビュアは Claude のままである。

同じ状態のフィールドがもう1つある: `WorkerModel`(`:31`)。こちらは
**コード上に `DEPRECATED: model/effort は models.go のポリシー表で工程別に決まる` と明記**されており、
意図された死蔵である。`ReviewerVendor` にはその注記が無い。

## 影響

- `02-design/contracts/cli-orchestrator.md`「受け渡す設定」が
  「worker の権限モード / レビュアのベンダー | **実行時の振る舞い**」として列挙しており、
  **契約が実態より強いことを主張している**。
- 設定した利用者は切り替わったと誤解する。切り替わらなかったことに気づく手段が無い
  (警告もログも出ない)。
- severity を「中」とした根拠: 既定値(`claude`)での動作は正しく、実害は「効かない設定がある」こと。
  ただし契約の虚偽記載であり、`docs/issues/007`(異種ベンダーのレビュアーを常用へ昇格)を
  実装するときの前提が崩れている。

## 原因の見当

`docs/issues/007-future-heterogeneous-vendor-reviewer.md` が示すとおり、異種ベンダーのレビュアーは
「将来」の位置づけである。設定の受け口だけが先に入り、消費側が未実装のまま残ったと推測する。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| `reviewer_vendor` の効果 | 無い(参照されない) | `CTR-cli-orchestrator` は「実行時の振る舞い」を変えると書く | **契約が誤り**。実装が正 |
| 異種ベンダーのレビュアーを持つべきか | 未実装 | `docs/issues/007` が「決定へ昇格。ただしフォールバック付き」で人間の回答を取得済み | **要件が正**(将来実装する) |

本タスクでは**契約の記述を実態に合わせる**(効かないことを明記する)。実装を要件に追いつかせるのは
`docs/issues/007` の仕事である。

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `docs/issues/007` の実装時に消費側を作る。それまで契約に「現在は効かない」と明記する | 本タスクで契約を修正済み。実装は 007 |
| B | 参照されない設定キーを解析対象から外し、未知キーとして警告する | `orchestrator/config.go` 1箇所。`WorkerModel` の扱いと揃える必要がある |

推奨は **A**(007 が既に人間の回答を得ており、削るより実装する方向が決まっている)。
**コードの変更を伴うため本タスクでは扱わない。**

## 関連

- `docs/issues/007-future-heterogeneous-vendor-reviewer.md`
- `issue 008`(**2026-08-04 に解消して削除。経緯は `docs/histories/2026-08-04-impl-depth.md`**)(契約の深度)
