---
id: 2026-08-05-doc-check-ssot-destructive-scope-recertification
date: 2026-08-05
task: task-fix-destructive-scope
origin_layer: 03
issue: docs/issues/053-bug-logout-treats-unlistable-auth-volume-as-empty.md
summary: /doc-check ssot をやり直し、中断した前回実行が残した記述の食い違いを直して 02/03 を再認証した
---

# 2026-08-05 `/doc-check ssot task-fix-destructive-scope` のやり直しと再認証

## 変更理由

前回の `/doc-check ssot task-fix-destructive-scope`(コミット `b7d1ebc`)は**セッション上限で
途中終了**しており、合格証は発行されていたが検証が最後まで通っていない可能性があった。
合格証の存在を根拠にせず、`/doc-check` の手順どおりに検証をやり直した。

起点層は **03**: 見つかった食い違いはいずれも「実装仕様が実装と、あるいは自分自身と
食い違っている」ものであり、要件・設計の内容そのものは変わっていない。
ただし 02 のモジュール分割定義に、`reset` の削除対象集合を一意に読めない記述があったため、
そこだけ 02 起点で直した。

**独立レンズ**: Codex(`gpt-5.6-terra` / reasoning max)。5本起動して**3本が完走**
(`relations` / `docs` 00〜02層 / 変更差分の最終監査)、**2本が 900 秒でタイムアウト**
(対象集合を絞る前の `docs` 全体と、03層+E差分)。**03層の A3 / E / C12 に対しては
独立レンズが立っていない**。これはツールの問題であり issue には起票しない(CLAUDE.md 不変則6)。

## 変更内容の要約

- **前回実行が半分だけ直した記述を最後まで直した**: `MODULE-cli-stop` の
  「docker-proxy の削除は失敗を握らない」を戻り値欄だけに書いて、実装上の判断3・順序の段落・
  異常系の表の3箇所に旧い記述(「握って続行する」「この1件だけ失敗を握らない」)が残っていた。
- **独立レンズが検出した記述とコードの食い違いを直した**(3件): `logout` の共有ボリューム
  「空」判定 / `DOCKER_HOST` の macOS 側ソケット探索 / 契約 frontmatter の `impl` に macOS 版が無い。
- **自分の修正が生んだ矛盾を最終監査が検出したので直した**(2件): `logout` の戻り値欄と手順6 /
  `MODULE-cli-stop` の目的節が `stop <name>` の例外に触れていない。
- **`reset` の削除対象集合の書き方を 02 と 03 でそろえた**: 「管理ラベルを持つコンテナ・
  ボリューム・イメージ」は、ラベルが Claude コンテナにしか付かない実態と食い違う読み方を許していた。
- **`docs/issues/` へ3件起票**(053 / 054 / 055)。いずれも本タスクの範囲外なので直していない。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/02-design/system.md | 2.1.1 → 2.2.0 | `MOD-cli-reset` の責務を「管理ラベルを持つ Claude コンテナ + 固定名の資源」と資源の種類ごとに書き分け、列挙の仕方(共有 docker-proxy とネットワークだけは候補として常に挙げる)を明記した |
| docs/02-design/relations.md | 1.2.0 → 1.3.0 | `PLAN-cli-reset` の概要を `MOD-cli-reset` の責務と同じ対象集合の表現へそろえた |
| docs/03-impl/index.md | 1.10.0 → 1.11.0 | 「実装の欠陥として起票済み」を 14 → 15 件にし `053` を追加、`054` を「既知の制限から参照されていない」側へ記載した。relations 層の代表として `MODULE-cli-stop` / `-logout` / `-reset` の本文修正もこの版に含む |
| docs/03-impl/contracts/cli-container.md | 1.4.1 → 1.5.0 | `DOCKER_HOST` に macOS の `detect_docker_sock`(`${HOME}/.docker/run/docker.sock` へのフォールバック)を追記し、frontmatter の `impl` へ `claude-dev-mac::main#start` を足した |
| docs/02-design/contracts/*.md(5件)/ docs/03-impl/tests/*.md(32件) | 据え置き | 本文は変えていない。`verified.against` の `docs/02-design/system.md` を 2.1.1 → 2.2.0 へ更新して再認証した(変更箇所は `MOD-cli-reset` の責務欄だけで、これらの文書が参照する E2E シナリオ一覧・テスト戦略・他モジュールの責務には触れていないことを確認した) |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | MODULE-cli-stop | 目的節に `stop <name>` がラベルの有無を問わない例外であることを明記 / docker-proxy 削除の失敗を握らないことを判断3・順序・異常系の3箇所へ反映 / 判断2 の測定不能語「速くする」を具体化 |
| 変更 | MODULE-cli-logout | 手順6 の「空」判定が印を使わないこと・docker-proxy を0件判定に数えないことを明記 / 戻り値欄の「0 はすべて消えたときだけ」に手順6 の例外を追記 / 並行性節のロック保持区間を「取得〜解放」と明示 |
| 変更 | MODULE-cli-reset | summary と手順3 を、資源の種類ごとの識別方法と列挙の仕方に合わせて書き直した |
| 変更 | docs/03-impl/features.md | `MODULE-cli-reset` の概要を同じ表現へそろえた |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規 issue | docs/issues/053-bug-logout-treats-unlistable-auth-volume-as-empty.md | `logout` の「共有ボリュームが空か」の判定が列挙の成否を見ないため、一時コンテナを起動できない状態では認証が残っていても 0 で終わる(独立レンズは「高」、`/doc-check` が理由を付して「中」へ是正) |
| 新規 issue | docs/issues/054-modify-ssot-references-deleted-issue-paths.md | 解消して削除された issue のパスが SSOT に残り、10 ID・20 以上のファイルで参照先が実在しない(本タスク以前から続く運用の問題) |
| 新規 issue | docs/issues/055-modify-ac17-demands-listing-stopped-unlabeled-containers.md | `FR-env-03` 受入基準17 が停止中のラベル無しコンテナの表示まで求めているが、02 は「列挙できない」を意図した限界としている(01 と 02 の食い違い) |
