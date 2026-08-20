---
slug: fix-fr-env-07-13-owner-and-codex-sandbox-defaults
state: awaiting-verify
critical: true
origin: derived
issue: なし
started: 2026-08-20T14:39:55+09:00
updated: 2026-08-20T15:40:00+09:00
commit: 3421243b5edd0318961ad3711d9151f64c0e892a
summary: F2 の独立レビューが挙げた「高」2件(FR-env-07-13 の担当根拠と契約の正面衝突、codex サンドボックス既定と 02 の記述の不一致)を 02-design 側で直す修繕
---

# fix-fr-env-07-13-owner-and-codex-sandbox-defaults — 02-design の2つの正面衝突を直す

## 目的・やらないこと

- 目的: F2 の後追い独立レビュー(`.claude/missions/2026-08-20-converge-contract-green/reports/18*.md`)が挙げた「高」2件を、上流に合わせて 02-design 側で直す。中5・低1 は `docs/pendings.md` の残務へ。
- やらないこと: `verified` を書かない(原則6。この後 F2 `/verify-docs all` が検証する)/ 作業ツリーの既存4差分・`.claude/`・`externals/` に触らない(人間の裁定済み)/ `docs/issues/110` を作り直さない / 中1・中2・中5・低1 を直さない(残務へ1行)。

## 影響範囲(closure)

- docs/02-design/system.md
- docs/02-design/environments.md
- docs/pendings.md

## 主張

- 触ったモジュールのテスト: **このタスクは製品コードを1行も変えていない**ので、触ったモジュールは無い。既存テストが緑であることの確認: `cd docker-proxy && go test -count=1 ./...` → `ok  	github.com/quvox/claude-dev-env/docker-proxy	0.005s`
- lint: green(`cd docker-proxy && go vet ./...` → 出力なし・終了コード 0)
- build: 再実行していない。理由: 変更は Markdown だけで、Dockerfile・シェルスクリプト・Go のいずれも触っていないため、イメージのビルド結果は変わらない
- 仕様ドキュメントの一括検査: `python3 .claude/scripts/check-ssot.py docs` → `NG 違反 7 件`。**7件すべてが closure 外の既存違反**(CS11 参照実在3件 / CS20 起点層4件)で、着手時に凍結した値と同一である(1件も増やしていない)。CS8(曖昧語)は0件
- 外部挙動の変化: なし(コードを1行も変えない。02 の記述を上流へ合わせる修繕のみ)
- 認証・決済・不可逆への接触: あり(critical: true)— `docs/02-design/environments.md` の書き換え対象が「codex がサンドボックスと承認を通らずに走るかどうか」という権限境界の記述であるため。**機械判定(BRC2)の語には当たらないので、これは自分の判断で上げたものである**(先行して同じ記述を触った `document-codex-sandbox-preconditions` も同じ理由で critical: true)
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 収束契約)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | closure はドキュメント本文だけで、アカウント・権限・認証情報を作る/変える/消す機能を新設も変更もしない | — |
| BR-02 | 非該当 | 利用者や外部から値を受け取る口(画面・API・CLI 引数・ファイル取込)を新設も変更もしない | — |
| BR-03 | 非該当 | 利用者が値を決める識別子を新設しない | — |
| BR-04 | 非該当 | プロセス境界をまたぐ値のやり取りを変えない。`FR-env-07-13` の担当行は環境変数の到達義務の**担い手の書き方**を直すだけで、受け渡しの経路(`CTR-cli-container` の「実行時に決まる環境変数の受け渡し」)には触らない | — |
| BR-05 | 非該当 | 不可逆または影響の大きい操作を新設しない | — |
| BR-06 | 非該当 | 推測されると困る値を生成しない | — |

## 決定シート(回答済み)

- 問いなし(開示のみ)。問う基準(`delegation.md` §1)の関門1・2 を満たす論点が0件のため、シートは作成していない。理由: 2件とも**上流(00/01 と 02 の契約)が既に答えを持っており**、修繕は 02 の記述をその答えへ合わせる作業である。どちらも新しい選択をしていないので、人間に問える論点が生じない。

## 調査メモ

- 母集団の凍結: `python3 .claude/scripts/check-ssot.py docs` → `NG 違反 7 件`(CS11 参照実在 3 件 / CS20 issue の起点層 4 件)。CS11 の3件は `02-design/architecture.md:192`(issues/092)・`03-impl/relations/MODULE-cli-common-write-project-ssh-keys.md:86`(issues/002)・`03-impl/relations/MODULE-cli-ssh-keys-reset.md:30`(issues/002)。CS20 の4件は本 closure の外。
- ゲート: `check-backlog.py` → `合格: バックログは上限内`(issue 6/30・残務 44/50)。`check-debt.py --repair` → `通過(例外): 修繕タスク — 負債を減らす仕事は止めない`(未検証記録 7/5 で上限超過だが修繕は通る)。
- `relations-query.py --requirement FR-env-07-13` および `--requirement FR-env-12-5` はいずれも「0 件 / 要件に対応する実装が無い」。トレーサビリティが 03 側に無いので、担当の裁定は 02 の契約と 00/01 の上流だけで行う。

## 進捗メモ(再開点)

- 2026-08-20 14:39 指示 22 を受領。ゲート2本を通し、母集団を凍結。構築記録を作成。
- 2026-08-20 14:52 高2件目を修理: `docs/02-design/environments.md:177`-`:183` の「監査での禁止事項」段落を「監査と QA が走るサンドボックスの強度」へ書き換えた。上流(`docs/00-requests/decisions/dist.md:82`-`:88` の `D0-dist-04` 項6 / `docs/01-requirements/functional.md:324` の `FR-env-12-5` / `docs/02-design/architecture.md:258`-`:263` の `DSN-dist-02`)が既定3鍵を `sandbox_mode = "danger-full-access"` / `approval_policy = "never"` / `[features] use_legacy_landlock = true` と定めており、同ファイル `:143`「必須フラグ 無い」と合わせると監査も既定でサンドボックスと承認を通らない。よって「監査は read-only + landlock で足りる」は偽、「QA レーンのみ例外」も偽(既定の再掲)。02 の記述を上流へ合わせた(上流は正しいので 00/01 は触らない — 原則3)。

### (進捗つづき)

- 2026-08-20 15:02 高1件目を修理: `docs/02-design/system.md` の3箇所。`:297`(FR-env-07-13)と **`:358`(FR-env-14-11 — レビューは名指ししていないが同一の誤った根拠が二重に在り、`CTR-cli-container:72` は両条項を同時に引く)** の根拠欄から「主担当が `MOD-cli-start` ではなく `MOD-entrypoint` なのは…木を起こすのは entrypoint だからである」を削除し、`CTR-cli-container:76`-`:80` のとおり `MOD-cli-start` の再接続経路も同じ義務を負う旨へ改めた。主担当は規則どおり1条項1モジュールのまま(`docs/02-design/system.md:183`)で、共同の担い手は根拠欄に書く(`:222` の先例と同じ形)。`:86`-`:89`(分割の根拠の読み直し記録)も担い手を2モジュールへ更新(結論「新しいモジュールは増えない」は継続 — `delegation.md` §3.1 の更新)。

- 2026-08-20 15:18 中3(`2bc8d6d` の断定2行)を裁定: `system.md:233`(`FR-env-02-7`)と `:266`(`FR-env-04-9`)は主担当・充足・根拠のいずれも上流と一致していたので本文は変えず、判断の持ち主をこの記録へ移した(根拠は履歴の「`2bc8d6d` の断定2行の裁定」)。
- 2026-08-20 15:22 版を上げた: `system.md` 2.18.0 → 2.19.0 / `environments.md` 1.6.0 → 1.7.0。**`verified` は触っていない**ので両方の合格証は版の不一致で無効になった(原則6。再発行は次の `/verify-docs all`)。
- 2026-08-20 15:26 残務を処理: closure に掛かる4行へ裁定を付け(不要と裁定1・02側を直して narrow 1・持ち越す2)、中1・中2 を1行ずつ追加、`:186` の件数の自己矛盾を直した。44 行 → 46 行 / 上限 50。落としたものは無い。
- 2026-08-20 15:30 常時床: `go vet` 終了0 / `go test -count=1 ./...` → `ok`、`check-ssot.py docs` → `NG 違反 7 件`(着手時の凍結値と同一)。履歴を作成し `build-index.py` を実行。
- 2026-08-20 15:34 **他のエージェントが並行して `stamps.py promote` を走らせ、`awaiting-verify` の6記録が `verified` へ上がった**(スタンプは 05:43:33Z に green)。自分の closure の外なので触っていない。`check-debt.py` は 7/5 超過 → 1/5 へ下がった。

## override(人間の明示)

- なし(override 不使用)

## 申し送り

- **`.claude/directions/02-design.md:105` の検査行が、充足の語彙として `段階可` を挙げている**。同ファイル `:85` が定める4値は `完全` / `部分(P-nn)` / `適用外(理由)` / `-` で `段階可` は無く、`:105` はどこにも定義の無い語を検査対象として名指している。**キットは CLAUDE.md §3 により凍結中で `/kit-improve` の持ち物**なので触っていない。残務にも積んでいない(残務は `docs/` の整合を持つ場所であり、キットの内部矛盾はその外である)。**この矛盾が、削除した残務1行(SR 行の充足語彙)の出どころである。**
- **F2 の後追い独立レビューが挙げた「高」1件目は、レポートが名指しした `system.md:297`(`FR-env-07-13`)だけでなく `:358`(`FR-env-14-11`)にも同一の誤った根拠が在った。**両方直したが、**同じ型の見落としが他の条項にもあり得る**(2つの条項が同じ契約文を根拠に持つとき、片方だけが更新される型)。次の `/verify-docs all` はこの型を探すこと。
- 独立レビューは走らせていない(`/build` の内側にレビューは無い — CLAUDE.md §6)。この修繕の検証は指示22 が予告している `/verify-docs all` が持つ。
