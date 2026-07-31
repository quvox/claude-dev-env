---
slug: heterogeneous-vendor-reviewer
layer: task
title: 異種ベンダー worker（Codex）によるレビューを常用にする（D-22 を決定へ昇格・フォールバック付き）
date: 2026-07-31
updated: 2026-07-31
phase: 決定
source:
  - docs/00-requests/decisions.md
history: []
---

# タスク:異種ベンダーレビューを常用にする（D-22 昇格）

## 目的

オーケストレーターの品質ゲート（相互レビュー）で、**実装 worker と別ベンダー**のレビュアー（Codex）を
常用する。ただし Codex が使えないときに作業が止まらないよう**フォールバック**できるようにする。

## 起票の経緯

`/doc-check full`（2026-07-31）の独立監査（02 レンズ）が、steering と仕様チェーンの不整合を検出した——
`docs/_steering/product.md:36` は「実装と独立レビューを**別ベンダーのワーカーに担わせ**、盲点を相互補完する」
と断定するが、`00-requests/decisions.md` の D-22 は「異種ベンダー worker（Codex 等）の常用可否」を**要確認
（未決）**のままとし、`01-requirements/core.md` スコープ外・`orchestration.md` スコープ外も同じ線引きをしている。

この不整合の解消方法として (A) steering を「将来像」と明記して弱める / (B) D-22 を決定へ昇格する を提示し、
**人間の回答は B（ただしフォールバックできるように）**（2026-07-31）。00 層の要求変更であり、今回の
codex-landlock-sandbox 作業の影響範囲外なので独立作業として起票した。進め方も人間が「別作業として
`/change` で回す」を選択している。

## 前提となる既存の状態（調査済み）

| # | 事実 | 根拠 |
|---|---|---|
| 1 | `reviewer_vendor` 設定は既に存在するが **v1 は値を読むだけで未使用**（常に Claude・codex はフェーズ2） | `03-impl/orchestrator.md` 設定表・既知の制限 |
| 2 | レビュアーは `claude -p`（`reviewerProfile`＝opus/high）で起動され、契約「orchestrator → worker / 対話Claude」も `claude -p` に限定して書かれている | `02-design/system.md` 契約節・`03-impl/orchestrator.md` review 節 |
| 3 | 要件 17-1 は「実装 worker と別 worker（**できれば別ベンダー**）による独立レビュー」。この「できれば」は独立監査からも C6/C7（合否境界が定まらない）として指摘されている | `01-requirements/orchestration.md` 要件17 |
| 4 | Codex CLI は既にコンテナへ同梱され、認証共有も実装済み（D-27）。ただし D-27 ⑤ が「開発者が対話的に使えるところまで」とスコープを切っており、worker/レビュアー常用は明示的に対象外 | `00-requests/decisions.md` D-27 |
| 5 | コンテナ内の codex は `--sandbox read-only` を明示指定した呼び出しが landlock で成立する（レビュー用途に必要な読み取りは可能） | `01-requirements/core.md` 12-9 |

## 影響範囲(closure)（暫定・フェーズ1 で確定する）

| 層 | ファイル | 変更の見込み |
|---|---|---|
| 00 | docs/00-requests/decisions.md | D-22 を要確認 → 決定へ。フォールバック方針を含めて記述。D-27 ⑤ のスコープ記述も併せて更新 |
| 00 | docs/00-requests/request.md | §7 の Could/将来「異種ベンダー worker の常用」を Should/やること側へ移すか要判断 |
| 01 | docs/01-requirements/orchestration.md | 要件17-1 の「できれば別ベンダー」を、常用＋フォールバックの検証可能な基準へ。スコープ外の記述も更新 |
| 02 | docs/02-design/system.md | 契約「orchestrator → worker / 対話Claude」がレビュアー起動を `claude -p` に限定している箇所、テスト戦略 |
| 03 | docs/03-impl/orchestrator.md | review 節・設定表（`reviewer_vendor`）・既知の制限「codex はフェーズ2」 |
| steering | docs/_steering/product.md | 本作業の完了により、現行の断定的な記述が正しくなる（本作業が終わるまでは不整合が残る点に注意） |
| コード | orchestrator/review.go, models.go, config.go 等 | `reviewer_vendor` を実際に効かせる。codex 起動経路・構造化出力の取得・フォールバック |

## 未決点

| # | 対象 | 未決点 | 帰着 | 状態 |
|---|---|---|---|---|
| 1 | 全体 | **フォールバックの発動条件**（codex が未インストール／未認証／起動失敗／タイムアウト／構造化出力を返さない のどれで Claude へ落とすか） | フェーズ1 の決定シート | 未closure |
| 2 | 全体 | フォールバックしたことを**どこに記録し、人間にどう見せるか**（audit.jsonl のみ／Slack 通知／ダッシュボード表示） | フェーズ1 の決定シート | 未closure |
| 3 | 全体 | `reviewer_vendor` の**既定値**（`codex` を既定にするのか、`claude` 既定のままオプトインか） | フェーズ1 の決定シート | 未closure |
| 4 | 03/コード | codex から**構造化レビュー結果**をどう得るか（`codex exec --output-schema` が使えるか。現行 Claude 経路は「最終行 JSON＋寛容パース＋散文の再整形」で、スキーマ強制ではない） | フェーズ1 の決定シート＋フェーズ2 の技術調査 |
| 5 | 全体 | codex をレビュアーに使うときの**サンドボックス**（レビューは読み取りのみなので `read-only`＋landlock で足りるか。要件 core/12-9 と整合するか） | フェーズ1 の決定シート |
| 6 | 00 | D-27 ⑤ の「開発者が対話的に使うところまで」というスコープ宣言を、本決定に合わせてどう書き換えるか | フェーズ1 の決定シート |

## 質問キュー

なし（未決点はフェーズ1 の決定シートで一括提示する）

## タスク

（フェーズ1 未着手。決定シートの回答後に分解する）

## Definition of Done

- [ ] D-22 が decisions.md の決定として書かれ、フォールバック方針を含んでいる
- [ ] 要件17-1 が「別ベンダー常用」と「フォールバック」を検証可能な形で述べている（「できれば」を排除）
- [ ] `reviewer_vendor` が実際に効き、codex レビュアーが動作する
- [ ] codex が使えない環境でフォールバックが働き、その事実が記録される
- [ ] steering product.md の記述が仕様チェーンと一致する
- [ ] lint・単体テスト（`cd orchestrator && go test -mod=vendor ./...`）が通る
- [ ] 影響する E2E シナリオ（E2E-4）を実施する
- [ ] `/doc-check` が PASS する
- [ ] 本作業の 質問/修正/委任判断 が `docs/feedback/log.md` に記録されている

## 進捗メモ

- 2026-07-31: `/doc-check full` の決定シート #4 の回答（案B: D-22 を決定へ昇格・フォールバック付き／
  進め方は別作業として `/change`）により起票。未着手。**次は `/change` でフェーズ1（決定シート）を回す。**
  なお本作業が終わるまで、steering product.md と D-22 の不整合は**既知の残存事項として残る**
  （今回の /doc-check では重大度 中 と裁定し、PASS はブロックしていない）。
