# docs/ の読み方(人間向けガイド)

<!-- キットが配る読解ガイド。仕様ドキュメントではない — version / verified を持たない
     (検証済み記録の対象外)。ただし参照実在スキャン(check-ssot.py)には含める。
     プロジェクト固有の補足は自由に追記してよい — キット更新で上書きされたら
     kit-manifest.py check が「改造」として差分を示す。 -->

このディレクトリは **4階層ドキュメントモデル**の置き場である。00〜03 が**仕様ドキュメント
(SSOT)** — 仕様の唯一の正 — であり、**今のシステムだけ**を書く(予定・願望は書かない)。
その脇に **`ux/`(UX 文書)** が在る — UI/UX の記述(画面・操作の流れ・デザインの基調)は
徐々にしか仕上がらないので、00〜03 の文書の検証(文書整合・実装整合)の外に置く — ここを直しても
それらは失効せず、代わりに**実ブラウザで画面を触る QA**(この試験を行うプロジェクトなら)が
失効して、出荷の前に画面と突き合わされる。だから頻繁に改訂される(それが正常な姿である)。

## どこから読むか

| 知りたいこと | 読む場所 |
|---|---|
| このシステムは何のためにあるか | `00-requests/request.md` |
| 何ができると約束しているか | `00-requests/acceptances.md`、`01-requirements/functional.md` |
| 誰が・どういう流れで使うか | `01-requirements/usecases.md` |
| 全体構成・データの流れ・外部との境界 | `02-design/architecture.md` |
| 画面はどう見えるか・どう遷移するか | `ux/policy.md`(基調)、`ux/flows.md`(画面一覧と流れ)、`ux/screens/`(画面ごと) |
| なぜこの画面はこうなのか(ユーザテストの経緯) | `ux/reviews/`(第N回ごとの指摘と処置) |
| どう分割され、どう繋がる設計か | `02-design/system.md`(分割)、`02-design/relations.md`(想定連携) |
| 実際にどう実装されているか | `03-impl/relations/MODULE-*.md`(機能単位の鏡)、`03-impl/index.md`(目次と進捗) |
| 何を「1機能」と数えるか(境界の定義) | `03-impl/features.md`(唯一の合意場所) |
| 機能同士が実際どう連携しているか(実装された連携の地図) | `03-impl/feature-graph.md`(生成物 — 初回の `/relations` 実行までは未生成) |
| なぜこの設計・実装なのか | 各文書の「設計判断」「実装上の判断」の節、`histories/`(経緯と棄却案) |
| この文書・仕様IDを過去に変えた理由 | `histories/index.md`(文書・IDから履歴への生成逆引き) |
| 上流変更をまだ確認していない文書 | `reverification.md`(再検証候補の生成一覧) |
| いま何が進行中か / 棚上げか | `build-records/`(進行中と検証待ち)、`pendings.md`、`issues/index.md` |
| 直すほどではない小さな気付き(残務) | `residual.md`(1件1行。押し出されたぶんは `residual-NNN.md`) |
| その棚上げ・課題票は今も成立しているのか(記録日つきの読むべき一覧) | `reverification.md` の「鮮度確認の候補」 |
| 過去に人間が覆した提案は何か(同じ提案を繰り返す前に読む) | `feedbacks/` |
| 本番の運用手順(障害対応・バックアップ) | `03-impl/infra/`(手順)、`02-design/logging.md`(対応の期待) |
| critical変更で実際に確認した切り戻し・復旧 | 該当する`histories/`の「ロールバック・復旧記録」 |

**02(意図)と 03(実装)を見比べる**のがこの体系の中心 — 食い違いは、実装が誤っているか、
設計の更新漏れかのどちらかである。

文書はコードの逐語的な説明ではないが、単なる索引でもない。外から見える正常・異常・境界値、
所有境界を跨ぐ契約と共有資源形式、状態遷移と不変条件、判断理由と見直す条件、検証・ロールバック
条件は文書側から辿れる(この方針の出どころは、このプロジェクトが使っている開発規範の
`.claude/directions/conventions.md` §2 である)。関数単位の流れや private 分岐など、コードから安定して
読める機構だけを「(コードを参照)」で省略する。完全な実行記述はコード、意味と制約の入口はSSOTである。

## ID の読み方(接頭辞 → 何の ID か、どこにあるか)

| 接頭辞 | 意味 | 定義場所 |
|---|---|---|
| `RQ-*` / `AC-nn` | 要求 / 受け入れシナリオ | `00-requests/` |
| `D0-*` | 00 層の決定事項 | `00-requests/decisions/` |
| `FR-<領域>-nn-#` | 機能要件(`-#` は受け入れ基準の条項番号。02/03 はこの条項単位で対応を取る) | `01-requirements/functional*.md` |
| `NFR-<分類>-nn` | 非機能要件 | `01-requirements/non-functional.md` |
| `UC-nn` | ユースケース | `01-requirements/usecases.md` |
| `SR-nn` | システム・環境の要件(技術前提) | `01-requirements/system.md` |
| `D1-*` | 01 層の決定事項 | `01-requirements/decisions/` |
| `MOD-<slug>` | モジュール(分割の単位) | `02-design/system.md` |
| `SCR-nn` | 画面(UI/UX 記述の単位。画面一覧・流れ・画面ごとのファイルが同じ ID で結ばれる) | `ux/flows.md` の画面一覧(台帳) |
| `DSN-*` | 設計判断 | `02-design/`(architecture ほか) |
| `PLAN-<slug>` | 設計が想定する機能間連携(03 の `MODULE-*` と同じ slug で対になる) | `02-design/relations.md` |
| `CTR-*` | 契約(API・スキーマ。02 と 03 に同じ ID で両側ある) | `02-design/contracts/`・`03-impl/contracts/` |
| `E2E-nn` | E2E シナリオ | `02-design/system.md`・`03-impl/tests/e2e.md` |
| `MODULE-<slug>` | 実装された機能単位(機能間連携仕様書。1実装 = 1文書) | `03-impl/relations/` |
| `EXTERNAL-<system>` | 外部システム(IdP・決済など) | `01-requirements/system.md` の外部依存表(ID 列)。02 の境界表・03 の relations は同一 ID で参照 |
| `P-nnn` | 棚上げ(意図的な延期) | `pendings.md` |
| `NNN-<type>-<slug>` | 課題票(不具合・要修正) | `issues/` |
| `DS-nn` | **人間に問わず AI が決めてよい**と、あらかじめ決めてある領域の番号。この ID が付いた行は「AI が決め、そう決めたことを開示した」という印である | 開発規範側の委任の定義(`.claude/directions/delegation.md`。この文書群の外) |

本文中の `[DS-nn] 決めたこと — 理由: … / 見直す条件: …` という1行は、**人間に問わず AI が
決めてよいと委任された判断の開示**である。見直す条件が崩れていない限りそのまま読んでよい。

読み間違えやすい語の注意:

- **`MOD-*` がモジュール(設計の分割単位)、`MODULE-*` が機能(実装された機能単位)** —
  接頭辞の直感と逆なので注意。1機能は1モジュールに属する(`MODULE-*` の `module:` が指す)。
- **`kind:` は2語彙ある**: relations(`03-impl/relations/` の連携種別、6値)と
  契約(`contracts/` の契約種別、5値)は別の語彙で、`rest-api`/`event`/`other` が重なるが
  意味の範囲が違う。文書の種類で読み分ける。
- **「種別」列は表ごとに意味が違う**: 機能表(`03-impl/features.md`)では連携種別、
  受け入れ基準表(`01-requirements/functional.md`)では 正常系/境界値/異常系、
  E2E 一覧(`02-design/system.md`)では 対象/適用外(理由)。あとの2つは退役の印として
  `delete` も取る(機能表の廃止は行を消すので、そこに `delete` は現れない)。
  表の置き場で読み分ける。

## 調べ方(逆引きしたいとき)

- この文書・要件に触ると何に波及するか →
  `python3 .claude/scripts/relations-query.py --impact <path>`
- この機能を呼ぶ側 / この機能が呼ぶ側 →
  `relations-query.py --upstream <MODULE-slug>` / `--downstream <MODULE-slug>`
- この要件はどの機能で実現されているか → `relations-query.py --requirement <FR-ID>`
- なぜこの方式か → 各 `MODULE-*.md` の「実装上の判断」。なぜ**別の方式でない**か →
  `histories/index.md` を文書パス・仕様ID・MODULE-IDで逆引きし、該当履歴の棄却案を読む

## 更新のされ方(なぜ古くならないか)

- 変更は、その仕事が触ると宣言した文書とコードの範囲の中で、仕様の文書に直接書かれ、
  仕事の出口で実装と突き合わされる。検証は別のしくみが、人間の指示したタイミングで全体を横断して
  行い、デプロイは**全部の検証が通っているときだけ**できる。
  **タスクは、宣言した範囲の外の仕様文書を書き換えない。** 範囲の外を書けるものは**閉じた一覧**
  として定められている(このプロジェクトが使っている開発規範の
  `.claude/directions/principles.md` §1。検証のしくみの機械的な自動修正や、導入時の一括生成が
  そこに在る)— **一覧に無いものは書かない。**
- `03-impl/callgraphs/`・`feature-graph.md`・各 `index.md` はツールの生成物 — 手で直さない。
- 各文書の `verified:` は機械+AI の検証済み記録。`version` の MAJOR.MINOR が一致していれば有効
  (規則そのものは、このプロジェクトが使っている開発規範の
  `.claude/directions/principles.md` §6 が定める)。
  例外が2つある:
  - `03-impl/relations/MODULE-*.md` と `features.md` は個別の `verified` を**持たない** —
    `03-impl/index.md` が層の代表としてまとめて検証済み記録を持つ。「検証済み記録が無い」ことは
    信用できないことを意味しない。
  - 上流文書が動いた下流文書は自動では失効せず**「再検証候補」**になる(`/verify-docs` が
    報告し、`doc-health.py` が `reverification.md` に一覧化する)。再検証候補は「無効」ではなく
    「上流の変化を確認していない」の意。`判定不能` は参照消滅や版形式不正で比較できなかった状態。
