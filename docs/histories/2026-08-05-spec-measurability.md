---
id: 2026-08-05-spec-measurability
date: 2026-08-05
task: task-spec-measurability
origin_layer: 00
issue: docs/issues/043-modify-nfr-targets-do-not-measure-whole-requirement.md
summary: 測れない記述を全部閉じ、追わないと決めた品質特性2件(運用補助・可観測性 / レビュー前コードの外向き通信)を要件から削除した
---

<!-- タスクごとに1ファイル。追記のみ(確定したエントリの文章は書き換えない)。
     タスク・進捗・TODO は書かない(それは memo.md の仕事だった)。 -->

# 2026-08-05 仕様を「測れる」形にする

## 変更理由

`/doc-check` が繰り返し検出してきた**同型の欠落**を一度に閉じた。「形は整っているが測れない」、
つまり要件・受入基準・設計が**合否を判定できる観測点を持たない**記述である。
起点層は **00**(用語の定義、`AC-02` の期待結果、`D0-scope-06` の委任範囲)。

決定シートで人間が **AI の推奨を3件覆した**ことが、このタスクの性格を変えた。当初は
「測れるように書き直す」だけの予定だったが、人間の裁定は **2つの品質特性については
「測れるようにする」のではなく「そもそも追わない」**というものだった:

- `NFR-ops-01`(運用補助と可観測性)を**削除**
- `NFR-sec-02`(レビュー前コードの外向き通信の制御)を**削除**
- `request.md` の枕詞「安全な」を落とし、代わりに**用語集に「安全」を定義**

理由は3件とも共通で「**その品質特性自体を本システムでは追わない**」。置き換えではないので、
相当する要件を別の形で書き直すことはしていない。この学びは
`docs/feedbacks/021-a-quality-attribute-can-be-declined-not-only-measured.md` にある。

## 変更内容の要約

- **要件を2件削除した**。裏付けを失う記述は下流まで実測して外した(02 の責務表・要件カバレッジ表、
  03 の `MODULE-*` frontmatter の `requirements`、テスト対応表)。
  外向き通信の制御は `FR-env-05`(機能要件)が、資源逼迫の検知は `FR-env-08` 受入基準4 が、
  介入の記録は `FR-orch-04` 受入基準4 が引き続き要求するので、**実装が要件の裏付けを失う機能は無い**。
  唯一の例外が追記型ログの `dispatch` / `result` で、これは `docs/issues/061` が追跡する。
- **用語集に6語を定義した**(安全 / 公開ポート / ブロック対象ドメイン / 破壊的操作 / 管理ラベル /
  資源逼迫)。表に**含む例・含まない例**の2列を新設し、この6語を埋めた。
- **`AC-02` を「利用者の Web アプリ用ポート」に限定**した。`USE_VNC=1` が既定の構成では
  noVNC の 6080 番台が必ず公開されるため、例外なしの「ポート非公開」は既定構成で成立しなかった
  (`D0-env-02` が既に例外を明記していたのに、`AC-02` だけが追随していなかった)。
- **`NFR-perf-02` / `NFR-sec-03` を測定可能にし、`NFR-ops-04` / `NFR-scale-02` に
  「測らない(理由)」を明記した**。「測らない」を書けるようにしたのが論点1 の裁定である。
- **`D0-scope-06` の委任範囲から程度語を外した**。「軽微な曖昧さ」を対象ファイルによる限定
  (`03-impl/relations/` と `contracts/` の散文)へ改めた。**委任範囲は広げていない**
  (旧ガードレールを 1〜3 として残し、4 として上流の層を明示的に加えたので、旧より狭いか同じ)。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/request.md | 1.2.0 → 1.3.0 | frontmatter `summary` の「安全な Docker コンテナ」から枕詞を落とした(本文は人間の言葉なので触っていない) |
| docs/00-requests/terminology.md | 1.1.0 → 1.2.0 | 6語を定義し「含む例 / 含まない例」列を新設。「資源逼迫」から環境変数名を落とし「既定値。上書き手段は 03-impl」とした(`docs/issues/044` の案A′) |
| docs/00-requests/acceptances.md | 1.0.0 → 1.1.0 | `AC-02` の期待結果と不合格条件を「利用者の Web アプリ用ポート」に限定し、noVNC を `D0-env-02` の例外として明記 |
| docs/00-requests/decisions/scope.md | 1.1.0 → 1.2.0 | `D0-scope-06` の見出しと委任範囲から「軽微な」を外し、対象ファイルによる限定へ改めた |
| docs/00-requests/decisions/env.md | 1.1.1 → 1.2.0 | `D0-env-06` の理由文「環境依存の分岐を安全に行える」を観測できる条件へ置換 |
| docs/00-requests/decisions/orch.md | 1.2.1 → 1.3.0 | `D0-orch-07` の「関連」から削除した要件 ID を外した(決定の内容は変えていない) |
| docs/01-requirements/functional.md | 1.5.1 → 1.6.0 | `FR-env-05` #4・#6 の「ブロック対象ドメイン」を用語集の定義付きへ(受入基準7 を新設し件数2つを起動ログへ出すことを要求)/ `FR-env-08` #4 を用語集参照へ / `FR-orch-02` #3 を「**タスク固有の文脈**を4種だけ」へ範囲明示 |
| docs/01-requirements/non-functional.md | 1.2.1 → 1.3.0 | **2要件を行ごと削除**(節の見出しは残す)。`NFR-perf-02` の目標値を6カテゴリへの割り当て方式に、`NFR-sec-03` を `SLACK_BOT_TOKEN` 1つに限定、`NFR-ops-04` / `NFR-scale-02` の第2文を「測らない(理由)」へ |
| docs/01-requirements/usecases.md | 1.1.0 → 1.2.0 | `UC-03` 事後条件の「安全な操作のみ」を `FR-env-07` の拒否規則参照へ / `UC-04`・シナリオ外要件から削除した2要件の参照を外した |
| docs/02-design/architecture.md | 1.2.0 → 1.3.0 | 責務表の「資源逼迫」を用語集参照へ。container-tools の対応要件を `FR-env-01` へ差し替えた(削除した要件が唯一の根拠だったため) |
| docs/02-design/system.md | 2.2.1 → 2.3.0 | `MOD-vm-mode` 責務の「資源逼迫」を用語集参照へ / 分割定義4行の要件列から2要件を外す / **要件カバレッジ表の2行を削除**(総括を NFR 15 → 13 件へ) |
| docs/02-design/logging.md | 1.2.1 → 1.3.0 | 「検知した指標と閾値」を用語集の数値で確定 / 「必要な範囲を超えて出さない」を判定基準つきへ / `dispatch` と `result` の対応要件を「**なし**」と明記(実装は出力を継続する) |
| docs/02-design/relations.md | 1.3.0 → 1.4.0 | `PLAN-vm-mode-healthd` の「資源逼迫」と `PLAN-makefile-update-claude` の「高速更新」を置換 / 一覧5行の要件列から削除した要件を外した |
| docs/02-design/contracts/entrypoint-firewall.md | 1.0.0 → 1.0.1 | 「対応要件」から `NFR-sec-02` を外した(`FR-env-05` が残るので契約の根拠は消えない)。5つの子節は1文字も変えていない |
| docs/03-impl/features.md | (version を持たない層) | `MODULE-makefile-update-claude` の概要から「高速更新」を落とした1行だけを差し替え |
| docs/03-impl/relations/MODULE-firewall-init.md | (relations 層) | ブロック対象ドメインの既定の内訳を**実測 16 件**(paste 系9 / webhook テスト系3 / トンネル系4)+ コメントアウトされた本番雛形2件として列挙 |
| docs/03-impl/relations/MODULE-vm-mode-healthd.md | (relations 層) | 「RAM 逼迫」を用語集の「資源逼迫」(CPU 使用率のみ)へ。`requirements` から削除した要件を外した |
| docs/03-impl/relations/MODULE-vm-mode-cli.md ほか3本 | (relations 層) | `requirements` から削除した要件を外した(`MODULE-hooks-save-prompt` / `MODULE-hooks-send-slack-message` / `MODULE-container-tools-wait-limit-reset`) |
| docs/03-impl/relations/MODULE-makefile-update-claude.md | (relations 層) | `summary` の「高速更新」を「コンテナイメージを作り直さずに Claude Code だけを更新する(ビルドキャッシュを使う)」へ |
| docs/03-impl/tests/firewall.md | 1.0.0 → 1.1.0 | 削除した要件の行を対応表と未検証一覧から削除(`FR-env-05` の行は残る) |
| docs/03-impl/tests/images.md | 1.0.0 → 1.1.0 | `NFR-perf-02` の未検証理由を6カテゴリ割り当て方式に追随させた |
| docs/03-impl/tests/orchestrator.md | 1.4.1 → 1.5.0 | 削除した要件の2行を削除し連番を繰り上げ / `NFR-sec-03` の未検証理由を実態(単体テストがあるのは対話 Claude 側だけ)へ / `NFR-ops-04` を「測らない」へ |
| docs/03-impl/tests/cli-login-codex.md | 1.0.0 → 1.1.0 | `NFR-scale-02` の第2文を「測らない」へ |
| docs/03-impl/index.md | (`/doc-check` が発行) | 「01 との差異」表から削除した要件をキーにした行を外し、`dispatch` / `result` が要件を持たない事実の行を追加 |

## 実装したもの

| 対象 | 内容 | コミット |
|---|---|---|
| (なし) | **コード変更は 0 件**。本タスクは記述の精密化のみで、`scripts/` `orchestrator/` `docker-proxy/` `claude-dev` `Makefile` `Dockerfile*` に差分は無い | — |

**測定可能化が実装を要求しなかった理由**: `FR-env-05` に新設した受入基準7(ブロック対象ドメインの
件数2つを起動ログへ出す)は、`scripts/init-firewall-claude.sh:133`〜`:134` の**既存の実装の写し**
である。フェーズ2 のドライランでこれを実測し、要件を実装より厳しくしていないことを確かめた。

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | MODULE-firewall-init | 「呼び出され方」に既定リストの内訳を実測値で列挙 |
| 変更 | MODULE-vm-mode-healthd | 「目的」「既知の制限」を用語集の定義語へ。`requirements` を更新 |
| 変更 | MODULE-vm-mode-cli / MODULE-hooks-save-prompt / MODULE-hooks-send-slack-message / MODULE-container-tools-wait-limit-reset | `requirements` から削除した要件を外した |
| 変更 | MODULE-makefile-update-claude | `summary` から測定不能語を外した |
| 追加・削除 | (なし) | 機能の境界は変えていない(`propose-features.py` の FT2 は 0 件) |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規 issue | docs/issues/060 | 01 に条項 ID と分割可否が無く、02 に充足列が無い |
| 新規 issue | docs/issues/061 | 追記型ログの `dispatch` / `result` が要件の裏付けを失う(本タスクの直接の帰結) |
| 新規 issue | docs/issues/062 | `MODULE-makefile-build-orchestrator` に残る「自己検証の高速ループ」 |
| 新規 issue | docs/issues/063 | ダッシュボードの資源逼迫バナーに受入基準が無い(実装済み・単体テスト4件つき) |
| 新規 issue | docs/issues/064 | `DSN-prompt-03` の「だけ」が共通の前置き・後置きを数えていない |
| 新規 issue | docs/issues/065 | レンズ代替の可否を書く欄が `environments.md` に無い |
| 気づき | docs/feedbacks/021 | **品質特性は「測れるようにする」だけでなく「追わない」と決められる** |
| 気づき | docs/feedbacks/022 | 承認の有効範囲は承認した人間が決める。AI が「1実行限り」へ勝手に狭めない |
| キット課題 | .claude/improvements/KIT-changeset-cs2-closure-and-deletes-as-sections.md | CS2 が部分的な relations 編集を原理的に通せない / CS9 が一度も走っていない |
| キット課題 | .claude/improvements/KIT-callgraph-output-during-task.md | staged コールグラフと CS1 が同時に成立しない |
| 解消した issue | docs/issues/017(削除) | 測定不能語。残存 10 箇所 + 資源逼迫の下降先6箇所をすべて置換した |
| 解消した issue | docs/issues/041(削除) | ブロック対象ドメインの集合を用語集で定義し、既定の内訳を 03 に列挙した(案D) |
| 解消した issue | docs/issues/042(削除) | `AC-02` を Web アプリ用ポートに限定した(案A) |
| 解消した issue | docs/issues/043(削除) | NFR の目標値・測定方法を要件本文の全体に合わせた(2件は削除、2件は測定可能化、2件は「測らない」明記) |
| 解消した issue | docs/issues/044(削除) | 「資源逼迫」の閾値定義を下降させ、`terminology.md` に合格証を発行できる状態にした |
| 解消した issue | docs/issues/049(削除) | `042` と同一事象。`049` の言い回し(「Web アプリ用のポート」)を採った |

## 独立レンズについて(記録)

**Codex は全フェーズで利用上限**(復旧 2026-08-11 12:56)。人間が代替を承認したため、
**フェーズ2・フェーズ3 ともサブエージェント(`Explore` / `sonnet`)で監査した。Codex ではない。**
フェーズ3 の指摘は2件で、「高」1件は**誤検知**(変更指示は実在した)だったが、
その指摘が closure 表の追随漏れという実在の欠陥を掘り当てたため訂正した。

**E2E は実行していない。** `docs/02-design/environments.md` が QA レーンを「無効(未運用)」と
定めており(`docs/pendings.md` P-003 で追跡)、自動テストランナーも無く、
**コード差分が空**なので影響を受けるシナリオが 0 本だったためである。人間が既定で承認した。

## 認証(`/doc-check ssot task-spec-measurability`)で加えた訂正

反映後の認証実行(`/task-close` フェーズ4 §4)は **PASS** で、**64 件の仕様ドキュメントのうち
58 件の合格証を発行・再発行した**(`request.md` 1.2.0 → 1.3.0 を起点に、`tests/` 30 本・
02 の契約5本・`environments.md`・`infra/local/` 2本まで連鎖して失効していた)。
そのうえで次の3点を訂正した。**上の版遷移表はこの3件を含まない**(表は反映時点の値である)。

| ドキュメント | version 遷移 | 何を直したか |
|---|---|---|
| docs/01-requirements/usecases.md | 1.2.0 → **1.2.1** | UC-01 の「関連要件」に **`FR-env-08` が無い**のに、同じ UC-01 の代替フロー A4 が「`--vm` が指定された \| ゲスト VM を起動し…(FR-env-08)」と参照していた。`FR-env-08` はどの UC の「関連要件」にも現れていなかった(**追跡の穴**)。本文が既に述べている ID を一覧へ足しただけなので PATCH |
| docs/00-requests/decisions/sec.md | 1.1.0 → **1.1.1** | 反映時に検証履歴コメントの1行(`docs/issues/041` の残課題)を削除したのに版が動いていなかった。コメントだけの変更なので PATCH |
| docs/03-impl/index.md | 1.13.2 → **1.14.0** | 反映時に「01(要件)との差異」表の行を入れ替えた(削除した要件をキーにした行 → `dispatch`/`result` が要件を持たない行)のに版が動いていなかった。表の内容が変わっているので MINOR |

**`docs/00-requests/terminology.md` に初めて合格証を発行した**(1.2.0)。これが本タスクの
Definition of Done 4 であり、`docs/issues/044` の下降が終わった証拠である。
あわせて frontmatter のプレースホルダ `# verified: /doc-check だけが書く` を実体に置き換えた。

### 認証で新しく起票した issue

| issue | severity | 内容 |
|---|---|---|
| `docs/issues/066` | 中 | **`docs/issues/043` と同型の測定欠落が、043 が列挙しなかった 6 件の NFR に残っている**(`NFR-perf-01` / `NFR-scale-01` / `NFR-avail-03` / `NFR-sec-01` / `NFR-perf-03` / `NFR-ops-02`)。043 の表は全行走査の結果ではなかった |
| `docs/issues/067` | 中 | `MODULE-hooks-send-slack-message` が Slack への POST 失敗を**無記録で**握りつぶすが、根拠に引用している `D0-orch-07` のガードレールは「握りつぶす場合でもログを残すこと」を要求している。`docs/issues/013` は別実装(`MODULE-orchestrator-slack`)が対象で、この経路を覆っていなかった |
| `docs/issues/068` | 低 | 用語集「介入トリガー」の「人間の判断を仰ぐ5条件」が、`D0-orch-18` の発火条件のうち「不可逆タスクの未承認」と `review_gate_defect` を含まない |

**3件とも本タスクでは直していない**(CLAUDE.md 原則8)。`066` は目標値を新しく決める要件レベルの
判断で決定シートの範囲外、`067` はコード修正を伴い本タスクは「コードを変更しない」と宣言済み、
`068` は 00 層の本文変更である。

### 独立レンズ(認証実行)

**Codex は実際に起動して利用上限を確認した**(復旧 2026-08-11 12:56)。人間の常設承認
(`docs/feedbacks/022`)にもとづき**サブエージェント(`Explore` / `sonnet`)を2本**立てた
(`docs` = A0〜A3・C7〜C12・E / `readiness` = D13〜D14 パス1)。**レンズは `subagent` であって
Codex ではない。** 上の3 issue はすべてレンズの指摘を起点に確定したもので、
**`066` の中心である `NFR-perf-01` はレンズが単独で最弱点として挙げた**。
一方でレンズの指摘 24 件のうち 10 件は**読み取り範囲の制約による誤検知**だった
(契約文書と `decisions/` を範囲外にしたため、そこに定義がある値を「未定義」と報告した)。

## 次の作業への申し送り(memo.md から移設)

memo.md はタスク削除とともに消えるため、**次の作業が必要とするものだけ**をここへ移した。
ナビゲーションの残骸(どのファイルを読んだ・変わっていないことを確認した)は意図的に捨てた。

- **2026-08-11 以降に新しいセッションで `/doc-check full` を1回**。Codex の利用上限が
  2026-08-11 12:56 に復旧するので、そこが**全層そろった状態での初のマイルストーン監査**になる
  (本タスクまでのフェーズ2〜4 はすべてサブエージェントのレンズで代替した)。
- **relations 層 83 本のうち、独立レンズがコードと全文照合できたのは 1 本だけ**である
  (22 本一括の監査が 900 秒でタイムアウトしたため)。`MOD-orchestrator` の残り 18 本を
  1本1監査で回す独立タスクの要否は、上の `/doc-check full` に委ねる(既定)。
- **`041` の「既定リスト16件が妥当か」のセキュリティレビューは未実施**。本タスクは集合を
  「測れる形」にしただけで、中身の妥当性は判断していない。必要なら別 issue として起票する。
- **キット側の未解決が2件**: `check-changeset.py` の CS2 が部分的な relations 編集を原理的に
  通せないこと、staged コールグラフと CS1 が同時に成立しないこと。どちらも
  `.claude/improvements/` が持っており、本タスクはドキュメントを歪めて通すことをしていない。
