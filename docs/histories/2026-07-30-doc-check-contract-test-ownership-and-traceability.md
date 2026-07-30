---
slug: doc-check-contract-test-ownership-and-traceability
layer: history
title: 検証指摘の修正（契約と結合テスト担当の1対1化・トレーサビリティ欠落の補完）
date: 2026-07-30
trigger: 検証指摘の修正（/doc-check full の残存指摘4件への対応。利用者指示）
origin_layer: design
affected:
  - doc: docs/02-design/system.md
    version: 1.5 -> 1.6
  - doc: docs/03-impl/entrypoint.md
    version: 1.3 -> 1.4
  - doc: docs/03-impl/orchestrator.md
    version: 1.0 -> 1.1
  - doc: docs/01-requirements/orchestration.md
    version: 1.0 -> 1.1
  - doc: docs/00-requests/decisions.md
    version: 1.5.0 -> 1.5.1
    change: D-19 の制約欄から陳腐化したモジュール数（12）を除去（PATCH）
---

# 変更記録:検証指摘の修正（契約と結合テスト担当の1対1化・トレーサビリティ欠落の補完）

## 変更理由・背景

`/doc-check full`（22件全件再検証）で残った指摘4件に、利用者の指示（「指摘事項に全て対応して。
ただし現状の実装に大きな影響を及ぼす場合は停止して」）を受けて対応した。**4件はいずれも
ドキュメント内の整合・トレーサビリティの欠落であり、実装コード（`claude-dev`／`claude-dev-mac`／
`scripts/*`／Dockerfile／Makefile／ワークフロー／Go 2 モジュール）の変更は 1 行も不要**だったため
停止せず実施した。要件の追加・変更、モジュール分割の変更、振る舞いの変更はいずれも無い。

### 指摘1（中・A2）契約と結合テスト担当が1対1でない

02-design の「モジュール間インターフェース(契約)」は契約4件を宣言する一方、「結合テスト対象」の表は
3行しか持たず、**`cli → コンテナ/entrypoint` と `orchestrator → worker/対話Claude` に担当行が無かった**。
逆に表にある `entrypoint → firewall` は契約節にコードブロックを持たなかった。02-design テンプレートは
「『モジュール間インターフェース(契約)』の全契約を列挙」することを要求しており、表が不完全だった。

実質の検証は下流に存在していた（`entrypoint.md` の結合レベル行、`orchestrator.md` の
`mode_test.go`／`policy_test.go`／`handoff_test.go`）ため、**新たな検証を作るのではなく、既にある
検証実態を 02 の表へ書き起こして 1 対 1 にする**方針を採った（もう一つの選択肢＝「対象外(理由)」と
宣言する案は、実際には検証が存在するため実態と合わないので却下）。

担当の割り当てはテンプレートの原則「呼び出し元が担当」から意図的に外し、**検証が観測可能な側**へ
寄せた。ホスト CLI（bash）は自動テストランナーを持たないため呼び出し元担当にすると全件が実機確認に
なり検証の所在が曖昧になる。既存2件（コンテナ→docker-proxy を docker-proxy、cli(orchestrate)→
orchestrator を orchestrator）も同じ理由で観測側担当になっており、今回の割り当てはその前例に従う。
この逸脱理由を表の直前に明文化した。

### 指摘2（低・A0）decisions.md D-19 のモジュール数が陳腐化

D-19（委任）の制約欄が「02-design の分割定義（**12モジュール**）を逸脱しない」と書いており、現在の
`system.md` の分割定義は 14 モジュール（03-impl も 14 件＋e2e.md で整合）。ガードレールの主旨は有効
だが括弧内の数値だけが古かった。**数値を 14 に直すのではなく、数を書き写す行為そのものをやめた**
（「モジュール数は同表が正本。本欄に数を書き写さない」と明記）。数値を 00 に複製する限り同じ陳腐化が
再発するためで、下流が守るべき制約の意味は変わらないので PATCH とした（合格証は失効しない）。

### 指摘3（低・A1）UC-4 の関連要件に要件19 が漏れ

UC-4 の基本フロー2・7 がダッシュボード表示とセレクタ選択（要件19）を使っているのに、関連要件が
「要件12〜18」で要件19 を挙げていなかった。要件19 自体は UC-5 の関連要件に載るためカバレッジ判定は
成立していたが、トレーサビリティとして取りこぼしだった。

### 指摘4（低・A3）orchestrator.md に担当契約の結合レベル行が無い

02-design 上 orchestrator が担当する契約について、`orchestrator.md` のテスト対応表にレベル=結合 の行が
無かった（`cli(orchestrate)→orchestrator` は散文で理由のみ記述、`orchestrator→worker/対話Claude` は
単体行のみ）。表として空白のままだった。

## 変更内容の要約

- **02-design/system.md（1.5.0 → 1.6.0）**: 「モジュール間インターフェース(契約)」に
  `entrypoint → firewall`（起動時の適用呼び出し・前提・失敗時の継続）を追加し契約を 5 件に。
  「結合テスト対象」を全 5 契約 5 行へ拡張し、`cli → コンテナ/entrypoint`（担当 entrypoint）と
  `orchestrator → worker/対話Claude`（担当 orchestrator）を追加。表の直前に、担当を「呼び出し元」
  ではなく「観測可能な側」へ寄せている理由を明文化。frontmatter summary に「モジュール間契約5件」を反映。
- **03-impl/entrypoint.md（1.3.0 → 1.4.0）**: テスト節冒頭に「本モジュールは 2 契約の担当」である旨と
  その理由を追記。テスト表に `cli → コンテナ/entrypoint` 契約の受け取り検証行（環境変数・マウント・
  両 rc 永続化・portsync 起動条件）を新設し、UID/GID・認証・codex 認証の各行に同契約の併記を追加。
- **03-impl/orchestrator.md（1.0.1 → 1.1.0）**: テスト表に担当2契約の結合レベル行を新設
  （`cli(orchestrate)→orchestrator`＝生存判定と設定受け渡し／`orchestrator→worker/対話Claude`＝実
  `claude` プロセスへのプロンプト注入と `control.json` 往復。いずれも **未検証(自動テストなし)**＝実機
  確認 E2E-4/E2E-5）。`mode_test.go`／`policy_test.go`／`handoff_test.go` の各行に
  `orchestrator→worker/対話Claude` 契約を併記。表後の散文を「担当2契約」の構成へ書き替え、orchestrator
  側ロジックは `go test` で機械検証・実プロセスとの結合は実機確認、という切り分けを明示。
- **01-requirements/orchestration.md（1.0.0 → 1.1.0）**: UC-4 の関連要件を「要件12〜19」へ拡張し、
  要件19 が基本フロー2・7（ダッシュボード表示・セレクタ選択・要判断の日本語提示）に対応する旨を併記。
- **00-requests/decisions.md（1.5.0 → 1.5.1・PATCH）**: D-19 の制約欄から陳腐化したモジュール数を除去し、
  分割定義の正本が `02-design/system.md` であること・本欄に数を書き写さないことを明記。
- **合格証の上流版参照のみ更新（内容変更なし・版据え置き）**: 03-impl の残り13件
  （cli／cli-mac／makefile／firewall／devcontainer／docker-proxy／sample-project／vm-mode／hooks／
  container-tools／portsync／e2e／ghcr-workflow）の `verified.against` を system.md 1.5 → 1.6 へ。

## 残した判断（申し送り）

`03-impl/cli.md` のテスト節は「結合テスト契約 `cli(orchestrate)→orchestrator` の担当は orchestrator
（本モジュールではない）」と 1 契約だけに言及している。今回 cli が呼び出し元となる契約が 2 件に
なったため記述としては不完全だが、**誤りではなく**（cli はどちらの担当でもない）どの検証項目も要求
しないため、版を上げず据え置いた。次に cli.md を意味変更する際に併せて 2 契約へ言及を広げるとよい。
