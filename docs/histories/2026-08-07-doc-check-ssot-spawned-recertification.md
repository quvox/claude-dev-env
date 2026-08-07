---
id: 2026-08-07-doc-check-ssot-spawned-recertification
date: 2026-08-07
task: task-stop-session-spawned-containers(`/task-close` フェーズ4 §6 からの `/doc-check ssot task-<slug>`)
origin_layer: 03
issue: docs/issues/087〜092(本実行で起票)/ docs/issues/082(本タスクの反映で解消・削除済み)
summary: セッション由来の資源の片付けを SSOT へ反映したあと、実装コミットでずれた「定義箇所」の行番号 96 件とコードとの事実の差異 8 件を直し、02 に PLAN-cli-reset 節を新設して 65 ファイルを再認証した
---

# 2026-08-07 セッション由来の資源の片付け 反映後の SSOT 再認証(`/doc-check ssot`)

## 変更理由

`task-stop-session-spawned-containers` の変更指示が SSOT へ反映され(コミット `89ce036`)、
00 の `decisions/env.md` / `terminology.md`、01 の `functional.md` / `decisions/split.md`、
02 の5ファイル、03 の contracts・relations・tests・infra の版が上がった。その下流の
**検証済み記録 40 件が失効した**ため、`/task-close` のフェーズ4 §6 がこの実行を起動した。

再認証の前に検査 A〜E を走らせたところ、**反映そのものは変更指示と一致**していた一方で、
次の3種類の欠陥が見つかったので、検証済みにする前に直した。

## 直したもの

| # | 種別 | 内容 |
|---|---|---|
| 1 | **コード ⇄ 03-impl の事実の差異(原則2)** | `03-impl/contracts/cli-container.md` と `docker-api.md` の「定義箇所」の行番号が、実装コミット `a271d83` / `1d912b4` で挿入された行の分だけずれたまま反映されていた。**96 件**をコードを正として引き直し、範囲の両端まで1件ずつ現物と突き合わせた。`entrypoint-firewall.md` の `NET_ADMIN` の定義箇所は本タスク以前から別の行(codex ディレクトリの削除)を指していたので、これも実物 `claude-dev:1403` に直した |
| 2 | **本文とコードの事実の差異 8 件** | `docker-api.md`「付与できないとき」の「ログにも残さない」(実際は `NO-OWNER-LABEL` を出す)/ `MODULE-docker-proxy-serve` の「`rewriteBinds` を条件付きで呼ぶ」(実際は常に呼ぶ)/ `MODULE-cli-stop` の二重削除が起きない理由(実装の根拠は列挙のタイミング)/ 旧名 compose 案内の実行位置 / `MODULE-cli-reset` 判断12 の `-f` の扱い / `tests/docker-proxy.md` のテストファイル名1件 / 同ファイルの「本数が一致していない」(実際は 39 対 39 で一致)/ `MODULE-cli-logout` が契約の除外を4つでなく3つと要約していた件 |
| 3 | **層をまたぐ不整合 9 件** | 01 の `FR-env-03-5` が `logout` を「停止」と書いていた(00 の `D0-env-05` 項2 が「削除の意味は削除であって停止ではない」と決めている)/ `FR-env-01-6` が compose 限定の書き方のままだった / 02 のエラーケース表が `reset` の失敗の扱いを `stop` と区別していなかった / 規則 C に `reset` の順序、規則 D に削除集合の固定が無かった / **`02-design/relations.md` に `PLAN-cli-reset` の節が無く、`stop` にだけ設計された順序制約が `reset` では実装にしか無かった**(節を新設)/ `system.md` の SCR-01 が `stop` / `reset` の片付けの状態を持たなかった / `FR-env-03-22` の主担当が `MOD-cli-logout` になっていた / 程度語4件 |

## 更新したドキュメント

| ドキュメント | version | 一言 |
|---|---|---|
| `docs/01-requirements/functional.md` | 1.10.0 → 1.11.0 | `FR-env-03-5` を「削除」へ、`FR-env-01-6` にセッション由来の資源への参照を追加 |
| `docs/02-design/contracts/cli-container.md` | 1.5.0 → 1.6.0 | エラーケースの `stop` / `reset` の区別、規則 C の順序、規則 D の集合固定、程度語2件 |
| `docs/02-design/relations.md` | 1.5.0 → 1.6.0 | **`### PLAN-cli-reset` を新設**(順序性・冪等性・失敗の扱い) |
| `docs/02-design/system.md` | 2.6.0 → 2.7.0 | SCR-01 に片付けの状態、`FR-env-01-6` の根拠に `DSN-env-04`、`FR-env-03-22` の主担当を `MOD-cli-reset` へ |
| `docs/03-impl/contracts/cli-container.md` | 1.6.0 → 1.7.0 | 定義箇所の行番号を実測へ、`NODE_OPTIONS` に行番号、程度語1件 |
| `docs/03-impl/contracts/docker-api.md` | 1.1.0 → 1.2.0 | 定義箇所の行番号を実測へ、ログの記述を事実へ |
| `docs/03-impl/contracts/entrypoint-firewall.md` | 1.0.0 → 1.1.0 | `NET_ADMIN` の定義箇所を実測へ |
| `docs/03-impl/tests/cli-stop.md` | 1.5.0 → 1.6.0 | テスト識別子を部分手順の粒度へ(3箇所)、`DS-01` の見直す条件を実態へ |
| `docs/03-impl/tests/docker-proxy.md` | 1.2.0 → 1.3.0 | テストファイル名1件、`MODULE ⇄ テスト`表を 39 本へ、解消済み issue への参照を削除 |
| `docs/03-impl/index.md` | 1.16.0 → 1.17.0 | 層代表として `relations/` と `features.md` を認証。起票済みの実装欠陥を 18 → 21 件へ |

## 独立レビュー

**Codex はアカウントの利用上限(復旧 2026-08-11)で実行できず、サブエージェントで代替した**
(不変則7。人間の常設承認あり)。**レビュー役は 4 本すべて `lens: subagent`** である。
初回3本(00〜02 の縦整合 / 02 ⇄ 03 と 03 単体品質 / 03 ⇄ コード)で 36 件、
修正後の再監査1本で 20 件を指摘し、計 56 件を1件ずつコードと現物で裁定した。
**再監査は、私のアンカー修正が表の最終セルしか対象にしておらず中間セルの 12 箇所が
残っていたことを検出した** — 独立レビューが無ければ「直したつもり」で認証していた。

## 起票したもの

`docs/issues/087`(コンテナ経路の注入失敗にログが無い)/ `088`(`stop` が compose 既定
ネットワークの削除失敗を表示しない)/ `089`(`logout` がセッション由来のコンテナを
「管理ラベルを持たない」と誤表示する)/ `090`(`logout` が作る孤児資源の帰結が未記録)/
`091`(`D0-env-08` 項8 に `reset` が所有者を問わない理由が無い)/ `092`(docker-proxy を
00・01 は「停止」、実装は「削除」)。**`090`・`091`・`092` は 00 への意味のある編集を伴うため
AI は決めず、決定シートに載せた。**
