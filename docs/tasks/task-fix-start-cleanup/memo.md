---
id: task-fix-start-cleanup
phase: 反映
origin_layer: 01
issue: docs/issues/036-bug-start-retry-deletes-a-colliding-running-container.md
date: 2026-08-04
updated: 2026-08-04
source:
  - docs/01-requirements/functional.md
  - docs/02-design/contracts/cli-container.md
  - docs/02-design/logging.md
  - docs/03-impl/relations/MODULE-cli-start.md
  - docs/03-impl/contracts/cli-container.md
  - docs/03-impl/tests/cli-start.md
  - docs/03-impl/tests/e2e.md
  - docs/03-impl/tests/strategy.md
  - docs/03-impl/index.md
summary: start の再試行前の後片付けが同名の稼働中コンテナを削除する(データ破壊)のを止める
---

<!-- タスクの背骨。フェーズ1で作られフェーズ4で削除されるまで、このファイルだけで
     どのフェーズからでも再開できること(/clear を挟んでも)。
     ・仕様ドキュメントではない(version / verified を持たない)
     ・未決点はここに置く。仕様ドキュメントには絶対に書かない
     ・削除は /task-close の機械ゲート経由(close-task.py)。rm 禁止 -->

# task-fix-start-cleanup `start` の後片付けが他方の稼働中コンテナを消すのを止める

> 解決済みの経緯: (まだ無し。フェーズの引き渡しごとに memo-1.md、memo-2.md … へ追い出す)

## 目的

`docs/issues/036`(severity 高・**データの破壊**)を解消する。
`claude-dev` の `start` は `docker run` が失敗すると再試行の前に**無条件で**
`docker rm -f "$NAME"` を実行する(`claude-dev:928` / `claude-dev-mac:963`)。
この後片付けは「自分が作りかけたコンテナか」を確認しないため、**basename が同じ別ディレクトリ
(`~/a/web` と `~/b/web`)や同一ディレクトリでの同時実行で名前衝突が起きると、
先に成功した側の稼働中コンテナを tmux セッションごと強制削除する。**
`/workspace` はバインドマウントなのでソースは残るが、tmux のスクロールバック・
実行中の `claude` / orchestrator・コンテナ内の一時生成物は失われ、
しかも失敗表示は「コンテナ起動に失敗しました」だけで**他方を消したことは表示されない**。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | 後片付けを「**自分が作りかけたものだけ**」に限定する(方式は決定シート論点1)。`claude-dev` と `claude-dev-mac` の**両方**を直す。`FR-env-01` に異常系の受入基準を追加し、`CTR-cli-container` のエラーケース表に名前衝突の行を足す。`MODULE-cli-start` の「並行性」「異常系」「既知の制限」を修正後の事実へ更新する。**この1件の実機確認手順を書いて実行する** |
| やらないこと | **`docs/issues/020`(CLI に排他機構が無い = ロックの導入)**。**`docs/issues/028`(コンテナ名にパス情報が無い = 命名の一意化)**。どちらも別タスク(論点2)。破壊的操作一般の規則を 00 に起こすこと(論点5)。`stop` / `reset` / `logout` の同型問題(`docs/issues/024` / `025` / `029`)。実機確認手順の**一般化**(`docs/issues/004` 観点6 / `docs/issues/006` / `docs/pendings.md` P-003 に依存) |

## 影響範囲(closure)

<!-- close-task.py はこの表から SSOT パスを抽出して合格証を検査する。
     frontmatter の source: と一致させること。 -->

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | docs/00-requests/request.md | - | 変更なし(理由: 目的・対象ユーザー・スコープは不変。「やらないこと」5項目のいずれとも衝突しない — 本件は隔離の強度でもエージェント個別隔離でもない) |
| 00 | docs/00-requests/decisions/env.md | - | 変更なし(理由: `D0-env-05`(compose の分離とライフサイクル)も `D0-env-04`(macOS は CLI 差し替え)も変わらない。破壊的操作一般の規則を足すかは論点5 で、**推奨は足さない**) |
| 00 | docs/00-requests/acceptances.md | - | 変更なし(理由: `AC-01` の受け入れ観点は変わらない。同時起動時の破壊は AC に無い) |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | **replace(★起点)**。`FR-env-01` に異常系の受入基準を追加(名前衝突で起動に失敗したとき、既存の稼働中コンテナを削除してはならない / 何が起きたかを表示して非0で終わる) |
| 01 | docs/01-requirements/non-functional.md | - | 変更なし(理由: `NFR-scale-01` の要件・目標値・測定方法は変わらない。名前の一意化そのものは `docs/issues/028` の別タスク) |
| 01 | docs/01-requirements/usecases.md | - | 変更なし(理由: UC の主フロー・代替フローに同時起動の分岐は無い) |
| 01 | docs/01-requirements/system.md | - | 変更なし(理由: 実行環境・依存の前提は変わらない) |
| 02 | docs/02-design/contracts/cli-container.md | new-features/02-design/contracts/cli-container.md | replace。エラーケース表に「**コンテナ名が衝突して起動に失敗した**」を追加し、既存の「公開ポートが競合して起動に失敗した」行の「作りかけのコンテナを削除して」を**条件付きの表現へ**改める |
| 02 | docs/02-design/relations.md | - | 変更なし(理由: `PLAN-cli-start` の callees・契約・要件は変わらない。想定する連携そのものが不変) |
| 02 | docs/02-design/system.md | - | 変更なし(理由: モジュール分割定義は不変。`MOD-cli-start` の責務は変わらない) |
| 02 | docs/02-design/architecture.md | - | 変更なし(理由: 全体構成・データモデル・設計判断は変わらない) |
| 02 | docs/02-design/logging.md | new-features/02-design/logging.md | replace(**★下降中に判定 → 変更する**)。「主要イベントのログ仕様」表に「**コンテナ名の衝突による起動の中止 / ERROR**」の1行を追加する。理由: `FR-env-01` 受入基準12 が表示内容(稼働中である旨・別ディレクトリの可能性・次に取るべき操作)を要求しており、02 に持たせないと `docs/issues/013` / `014` と同型の「02 のログ仕様に無い出力を 03 が持つ」乖離になる |
| 03 | docs/03-impl/relations/MODULE-cli-start.md | new-features/03-impl/relations/MODULE-cli-start.md | replace。「並行性」の1行目(現状は**削除まで含めた事実**を書いている)・「異常系」・「既知の制限」を修正後の事実へ |
| 03 | docs/03-impl/tests/cli-start.md | new-features/03-impl/tests/cli-start.md | replace。追加した受入基準の行を足し、**この1件だけは実機確認手順を書いて実行する**(状態を「未検証」で終わらせない) |
| 03 | docs/03-impl/index.md | new-features/03-impl/index.md | replace。「実装の欠陥として起票済み」の集計と「要件との差異」表の `FR-env-01` / `NFR-scale-01` 行から **036 を外す**(層の代表) |
| 03 | docs/03-impl/contracts/cli-container.md | new-features/03-impl/contracts/cli-container.md | replace(**★下降中に判定 → 変更する**)。「実装上の事実」表の「起動の再試行」行が「失敗したら作りかけのコンテナを `docker rm -f` してから」と**無条件に**書いており、修正後の実装と食い違う |
| 03 | docs/03-impl/tests/e2e.md | new-features/03-impl/tests/e2e.md | replace(**★下降中に closure へ追加**)。`FR-env-01` 受入基準12・13 の実機確認手順の置き場所が無い。`E2E-01`(UC-01 = start)の手順に**手順7**として追加する。E2E シナリオ一覧(02 の `E2E-01`〜`06`)は増やさない(`E2E-nn` は `UC-nn` と 1:1 で、本件は UC-01 の境界値にあたる) |
| 03 | docs/03-impl/tests/strategy.md | new-features/03-impl/tests/strategy.md | replace(**★`/doc-check` が closure へ追加**)。「カバレッジの扱い」の**現状値**が「機能要件の全 180 基準に行がある(対応表 195 行)」なので、受入基準を2つ増やすと 182 / 197 になる。指標の定義は変えない |
| 03 | docs/03-impl/features.md / feature-graph.md / callgraphs/ | - | 変更なし(理由: 機能境界も入口も変わらない。関数を増やさない方式なら callgraph は同一。**方式によっては新関数が増えるので再生成して確認する**) |
| — | claude-dev / claude-dev-mac | (コード) | **修正の本体**。`claude-dev:928` と `claude-dev-mac:963`。あわせて `claude-dev:736` / `claude-dev-mac:797`(「停止中のコンテナがあれば削除」)の TOCTOU も同じ判定で守るかは委任 b |

**走らせるテスト**: `relations-query.py --impact` の「走らせるべきテスト」は **0 件**
(`MODULE-cli-start` の `tests:` は「なし(未実装。シェル実装のため自動テストランナーが無く
実機確認で代替する)」)。**テストが無い範囲を触る**ので、DoD は実機確認の実行を含む(論点4)。

## 決定シート(回答済み)

**回答日: 2026-08-04。回答: 「推奨通りで良い」(全5論点 + 委任2件とも推奨案を採用)。**

| # | 論点 | 確定した回答 | 反映先 |
|---|---|---|---|
| 1 | 後片付けの限定方式 | **A1′**(名前衝突でない **かつ** 稼働中でない ときだけ削除。名前衝突は明示エラー + 終了コード 1) | `FR-env-01` の新しい異常系基準 / `CTR-cli-container` エラーケース / `MODULE-cli-start` / コード両CLI |
| 2 | `020` / `028` を含めるか | **A**(036 だけ。020 / 028 は別タスク) | 本メモ「やること・やらないこと」/ 申し送り事項 |
| 3 | macOS 版も同時に直すか | **A**(`claude-dev` と `claude-dev-mac` の両方) | closure のコード行 / `tests/cli-start.md` の対象環境 |
| 4 | 検証の深さ | **A**(この1件の実機確認手順を書いて実行する。手順の一般化はしない) | `tests/cli-start.md` / DoD |
| 5 | 破壊的操作一般の規則を 00 に起こすか | **A**(起こさない。原則1 に反するため。まとめて直すタスクの起点として将来 B) | 00 は変更なし / 申し送り事項 |
| a | メッセージ文面・出力先・終了コード | **委任を承認**(ガードレールは下表のまま) | `/task-doc` の下降で決め、`MODULE-cli-start` の「実装上の判断」へ記録 |
| b | `claude-dev:736` にも稼働中判定を入れるか | **委任を承認**(ガードレールは下表のまま) | 同上 |

根拠の三方向は下表の「根拠」列。上流=既に選択を縛るもの / 同層=先例 / 下流=壊れるもの。

| # | 論点 | 選択肢 | 推奨案(理由・下流の代償・崩れる条件) | 未回答時の既定 | 根拠(上流/同層/下流) |
|---|---|---|---|---|---|
| 1 | **後片付けをどう限定するか** | **A1′**: 後片付けは (i) 失敗が名前衝突でない **かつ** (ii) 対象が稼働中でない ときだけ行う。名前衝突なら削除せず「同名のコンテナが稼働中(別ディレクトリの同名プロジェクトの可能性)」を表示して終了コード 1 / **A2**: `docker run` に `--label claude-dev.project-dir=<絶対パス>` を付け、ラベル一致時だけ削除する / **B**: `docker create` で名前を予約してから起動する / **C**: コンテナ名にパスのハッシュを含めて衝突自体を無くす(`docs/issues/028` と一体) | **A1′**。データ破壊の実体は「**稼働中**のコンテナを消すこと」なので (ii) だけで被害が消え、(i) が原因の局面を明示エラーにできる。**契約を増やさない**(ラベルもコンテナ名も変わらない)ので closure が各層1〜3ファイルに収まり1回で検証しきれる。**下流の代償**: 「作りかけの停止中コンテナ」が稀に残りうる(次の `start` の `:736` が消すので回復する)。**崩れる条件**: 別プロセスが同名コンテナを**停止状態で**作りかけている最中に自分が失敗すると相手の残骸を消しうる(実害は残骸のみ)。A2 はこれも塞ぐが `CTR-cli-container` の起動オプションが増える | **A1′** | 上流: `FR-env-01` #4(同一ディレクトリの再実行は既存へ再接続)/ `NFR-scale-01`(衝突0件)/ `D0-env-05`(共有資源は消さない) 同層: `MODULE-cli-stop` が `com.docker.compose.project` ラベルで対象を絞る先例(= A2 の前例) 下流: `--impact claude-dev` → `MODULE-cli-start` / `CTR-cli-container` / `tests/cli-start.md`。走らせるテストは0件 |
| 2 | **`docs/issues/020`(排他機構)/ `028`(命名の一意化)を同じタスクに含めるか** | **A**: 036 だけ直す / **B**: 020 も含める(`flock` を CLI に導入)/ **C**: 028 も含める(命名を一意化して根本解決) | **A**。036 は数行の局所修正で実機確認まで一度に終わる。**下流の代償**: 同時 `start` の他の被害(認証が空のまま起動 = `020`)は残る。**崩れる条件**: 020 を先に直せば 036 の局面自体が起きにくくなるので「先に 020」も筋は通るが、**ロックの設計は `logout`/`reset`/`stop` を巻き込み closure が CLI 全体へ広がる**ため、データ破壊を止めるまでの時間が延びる。C は `container_name` の**11 呼び出し元**と利用者に見えるコンテナ名が変わり、既存コンテナの移行手順が要る | **A** | 上流: `D0-scope-01`(タスク粒度)/ `docs/issues/036` の裁定「次タスクで優先的に修正」 同層: `task-impl-depth` が21本を1タスクにして検証が重くなった先例 下流: 020 を含めると `MODULE-cli-logout` / `-reset` / `-stop` が closure に入る |
| 3 | **macOS 版(`claude-dev-mac`)も同時に直すか** | **A**: 両方直す / **B**: Linux 版だけ直し macOS は別 issue に切る | **A**。`MODULE-cli-start` の `impl:` は `claude-dev::main#start, claude-dev-mac::main#start` の**両方**を持つので、片方だけ直すと原則2(コード ⇄ 03-impl の完全一致)を満たせない。`D0-env-04` は CLI を分けた理由を「**片方の変更が他方を壊す**」と述べており、同じ欠陥を片方に残す選択と整合しない。**下流の代償**: macOS の実機確認ができない場合は手順を書いて「未実施」を明示する必要がある。**崩れる条件**: macOS 側の構造が違って同じ判定が書けない場合(`claude-dev-mac:963` は同一形なので該当しない見込み) | **A** | 上流: `D0-env-04` / `FR-env-10` 同層: `issue 038` #8 が「`MODULE-cli-start` は Linux/macOS を区別せず1本で書いている」と記録済み 下流: `tests/cli-start.md` の実機確認の対象環境 |
| 4 | **検証をどこまでやるか**(シェルに自動テストランナーが無い) | **A**: この1件の**実機確認手順を書いて実行する** / **B**: 受入基準の行を足すだけで状態は「未検証(テスト未実装)」のまま(`issue 006` / P-003 の解決待ち)/ **C**: シェル用テストランナー(bats 等)を導入する | **A**。**データ破壊の修正を「未検証」で閉じるのは、直った証拠が無いまま「高」を消すことになる**。手順は短い(basename が同じ2ディレクトリで `start` を2回 → 先の稼働コンテナが残り、後は非0で終わる)。**下流の代償**: `tests/cli-start.md` の他 34 行は「未検証」のままで、1行だけ検証済みという不均衡が残る。**崩れる条件**: 手順の**一般化**を始めると範囲が P-003 へ広がる → 一般化はしないと明記して切る。C は `02-design/environments.md` のテストコマンドと `01-requirements/system.md` の依存が動くので別タスク | **A** | 上流: 不変則3 の例外(「未検証」行は PASS を止めないが DoD で閉じる)/ `docs/issues/006` 同層: `tests/cli-forward.md` は `task-impl-depth` で「行の追加だけ」を行った先例(= B の形) 下流: `close-task.py` の DoD ゲート |
| 5 | **破壊的操作一般の規則を 00 に起こすか**(`stop` / `reset` / `logout` も他プロジェクトの資源を消す = `docs/issues/024` / `025` / `029` と同根) | **A**: 起こさない(今回は `FR-env-01` の受入基準だけ)/ **B**: `D0-env-08`「破壊的操作は自分が作った資源に限る」を**決定**として新設 / **C**: 同内容を**委任**として新設しガードレールを与える | **A**。B / C を今やると**実装がまだ従っていない規則を 00 に書くことになり CLAUDE.md 原則1(SSOT は現在の姿だけを持つ)に反する**。`024` / `025` / `029` はコード未修正なので、規則を先に置けば即座に doc ⇄ code の乖離が3件生まれる。**下流の代償**: 同型の欠陥を止める規範が無いまま残る。**崩れる条件**: `020` / `024` / `025` / `029` をまとめて直すタスクを立てるなら、そのタスクの起点として B が正しい(そこで起こす) | **A** | 上流: CLAUDE.md 原則1 / `D0-scope-06`(要件に関わる食い違いは委任外) 同層: `D0-env-05` が「共有リソースは他プロジェクトが使用中のため残す」と compose 限定で同趣旨を持つ 下流: `docs/issues/024` / `025` / `029`(いずれもコード未修正) |

### 委任にしてよいか確認したい項目

| # | 論点 | 委任範囲 | 制約(ガードレール) | 根拠 |
|---|---|---|---|---|
| a | エラーメッセージの文面と終了コード | 名前衝突時に表示する文面、`stderr`/`stdout` の選択、終了コードの値 | **終了コードは非0**。文面に「同名のコンテナが稼働中」と「別ディレクトリの同名プロジェクトの可能性」を含める。**削除したかのような表現を使わない**。既存の表示スタイル(絵文字 + 日本語1行)に合わせる | 上流: 今回追加する `FR-env-01` の異常系基準 / 同層: `claude-dev:710` の `--vm` 中止メッセージ / 下流: `tests/cli-start.md` の実機確認の期待値 |
| b | `claude-dev:736` / `claude-dev-mac:797`(「停止中のコンテナがあれば削除」)にも同じ稼働中判定を入れるか | 入れる/入れないの判断と、入れる場合の書き方 | **観測可能な振る舞いを変えない**(停止中コンテナの削除は従来どおり)。TOCTOU で稼働中になっていた場合に削除しないことだけを追加する。既存の `is_running` を使い新しい判定関数を作らない | 上流: `FR-env-01` #4(既存コンテナへ再接続)/ 同層: 論点1 の (ii) と同じ判定 / 下流: `MODULE-cli-start` の「処理の流れ」手順3 |

### 方針合意(個別diff承認は行いません)

- 01: `FR-env-01` に異常系の受入基準を追加(EARS の IF…THEN 形式)
- 02: `CTR-cli-container` のエラーケース表に1行追加 + 既存1行の表現を条件付きへ
- 03: `MODULE-cli-start` の「並行性」「異常系」「既知の制限」を修正後の事実へ / `tests/cli-start.md` に受入基準の行と実機確認手順 / `index.md` の集計から 036 を外す
- コード: `claude-dev` と `claude-dev-mac` の後片付けを限定する(数行)
- 変更指示を書き終えた時点で差分サマリを提示します

## 未決点

<!-- 帰着は3つのいずれか: ドキュメント記載 / 委任決定(D-ID) / 決定シート(人間判断)。
     ★2026-08-04 パス1 完了。**人間判断に帰着した未決点は0件**なので `/implement` の
       入場条件(原則7 = 未決点ゼロ)を満たす。 -->

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| 1 | 名前衝突をどう見分けるか(`docker run` の出力は Docker のメッセージで、文言に依存する) | **委任決定(D0-scope-02)**: 既存のポート競合判定と同じ方式で、`Conflict.` / `already in use by container` を `grep -qiE` で見る。ラベルによる所有者判定は導入しない。`MODULE-cli-start`「実装上の判断」#5 に記録し、文言依存を「既知の制限」に明記した | ドライラン パス1 |
| 2 | 文言判定が外れたときに何が起きるか(Docker が文言を変えた場合) | **ドキュメント記載**: `MODULE-cli-start`「既知の制限」。**稼働中判定が二重の防護**になるためデータの破壊には至らず、被害は「停止中の同名コンテナを消す」「専用のエラー文が出ない」に留まる | ドライラン パス1 |
| 3 | 稼働中判定から `docker rm -f` までの TOCTOU が残る(排他が無い) | **ドキュメント記載**: `MODULE-cli-start`「既知の制限」に窓が残ることを明記し、`docs/issues/020`(排他の欠如)へ紐づけた。根本解決は別タスク | ドライラン パス1 |
| 4 | 手順7(停止中の残骸の削除)にも同じ判定を入れるか | **委任決定(D0-scope-02。委任 b として承認済み)**: 入れる。観測可能な振る舞い(停止中コンテナの削除)は変えず、TOCTOU で稼働中になっていた場合に削除しないことだけを足す。`MODULE-cli-start`「実装上の判断」#6 | ドライラン パス1 |
| 5 | エラーメッセージの表示内容(委任 a) | **ドキュメント記載 + 委任決定**: 表示すべき内容は `FR-env-01` 受入基準12 と `02-design/logging.md` の新しい行が定める(稼働中である旨・別ディレクトリの可能性・次に取るべき操作・既存に触れていないことが分かる表現)。**文面の言い回しだけが実装詳細**として残る | ドライラン パス1 |
| 6 | Linux 版と macOS 版で判定を分けるか | **委任決定(D0-scope-03)**: 分けない。両方に同じ形で入れる。`MODULE-cli-start`「実装上の判断」#7 | ドライラン パス1 |
| 7 | 呼び出し元(`MODULE-cli-orchestrate`)への影響 | **ドキュメント記載(影響なし)**: `claude-dev:1015` は未起動時に `CLAUDE_DEV_NO_ATTACH=1` で `start` を再帰呼出しする。名前衝突時の終了コードは**修正前も後も 1** なので、`orchestrate` の分岐は変わらない(`grep -c CLAUDE_DEV_NO_ATTACH` = Linux 5 / macOS 0) | ドライラン パス1 |
| 8 | 実機確認の手順をどこに置くか | **ドキュメント記載**: `03-impl/tests/e2e.md` の `E2E-01` 手順7(closure へ追加)。モジュール側の `tests/cli-start.md` に手順の節を新設すると `03-tests-module.md` の見出し構成を変えることになるため置かない | ドライラン パス1 |

## 調査メモ

- `claude-dev:899`〜`:938` が `docker run` の再試行ループ。失敗時に `_run_attempt` を増やし、
  **無条件で** `docker rm -f "$NAME"`(`:928`)→ ポート競合の文言に一致し `USE_VNC=1` かつ 20 回以内なら
  別ポートで再試行、それ以外は `exit 1`(`:936`〜`:938`)。
- 同じ形が `claude-dev-mac:963`。ほかの `docker rm -f "$NAME"` は
  `claude-dev:736`(停止中コンテナの掃除)・`:1126`(`stop` の本体。正当)/
  `claude-dev-mac:797`・`:1088`。
- `container_name()` は `basename $(pwd)` を小文字化し `[a-z0-9._-]` 以外を `-` に置換するだけ
  (`claude-dev:245`〜`:252`)。**パスを区別する情報が無い**(= `docs/issues/028` の根)。
- `MODULE-cli-start.md:212`(並行性の表)と `:252`(既知の制限)は、**削除まで含めた事実を既に
  正確に書いている**(`task-impl-depth` が書いた)。修正後はこの2箇所が変わる。
- `docs/03-impl/index.md:61`(起票済みの集計)と `:85`(要件との差異の表)が 036 を挙げている。
- `tests/cli-start.md` は受入基準 34 行がすべて「未検証(テスト未実装)」+ 対象外1行。

### パス2(技術調査)の事実 — 実装が使うもの

| 事実 | 場所 |
|---|---|
| `is_running()` は `docker ps -q -f "name=^<NAME>$"` の出力が非空かで判定する | `claude-dev:260`〜`:262` / `claude-dev-mac:324` |
| `container_exists()` は `docker ps -aq -f ...`(停止中を含む) | `claude-dev:265`〜`:267` / `claude-dev-mac:329` |
| `docker run` の**標準エラーは既に変数に取れている**: `_run_err=$(docker run -d … 2>&1 >/dev/null)` | `claude-dev:901`,`:923` / `claude-dev-mac` の同一形 |
| ポート競合の判定は `printf '%s' "$_run_err" \| grep -qiE "port is already allocated\|address already in use\|bind for .* failed"` | `claude-dev:929`〜`:930` / `claude-dev-mac:964`〜`:965` |
| **無条件の後片付け**(修正対象): `docker rm -f "$NAME" >/dev/null 2>&1 \|\| true` | `claude-dev:928` / `claude-dev-mac:963` |
| 停止中の残骸の削除(委任 b の対象): `if container_exists "$NAME"; then docker rm -f "$NAME" >/dev/null; fi` | `claude-dev:735`〜`:738` / `claude-dev-mac:794`〜`:797` |
| `stop` の `docker rm -f`(**触らない**。正当な削除) | `claude-dev:1126` / `claude-dev-mac:1088` |
| 名前衝突時の Docker のメッセージ(判定に使う語): `Conflict. The container name "/<NAME>" is already in use by container "<id>"` | Docker のエラー応答(実装は文言で判定する。文言依存は「既知の制限」に記録済み) |
| 新しい関数は作らない = `callees` は増えない(`is_running` は既に callee にある) | `MODULE-cli-start.md:8` |

## 質問キュー(未提示)

| # | 質問 | 前提 | いつ聞くか |
|---|---|---|---|
| (なし) | 仕様に関する質問は無い。パス1 の未決点8件はすべてドキュメント記載か委任決定に帰着した | — |

**プロセス上の1件(不変則6 により未決点ではない)**: 実装ドライランの独立レンズ
(`/codex-audit readiness`)が**走らない**(Codex の利用上限。復旧 2026-08-10 19:52)。
不変則7 により無断で代替を立てないので、**代替レンズ(新しい文脈のサブエージェント)を
立てるかを人間に問う**。既定は「立てない」。ドライランはゲートではないので、
これで `/implement` は止まらない。

## タスクリスト

- [x] 1. `/task-doc task-fix-start-cleanup` で 01→02→03 の1回の下降(実装ドライラン込み) _Depends:_ 決定シートの回答
      (2026-08-04 完了。変更指示8ファイル / 未決点は人間判断0件 / 独立レンズは Codex 利用上限で未実行)
- [x] 2. `/doc-check task-fix-start-cleanup` が PASS _Depends:_ 1
      (2026-08-04 **判定: PASS**。実行形態=著者セッション / 独立レンズ=なし(Codex 利用上限)。
      検出した指摘1件(`tests/strategy.md` のカバレッジ現状値が 180 のまま失効する)を
      closure へ追加して変更指示を作成。check F は9件すべて一致、機械検査は全合格)
- [x] 3. `/implement task-fix-start-cleanup`(コード修正 + 実機確認) _Depends:_ 2
      (2026-08-04 完了。`claude-dev` / `claude-dev-mac` を各2箇所修正 = 44行追加・6行削除。
      **修正前のコードでデータ破壊を再現し、修正後に再現しないことを実機で確認した**)
- [ ] 4. `/task-close task-fix-start-cleanup` _Depends:_ 3

## Definition of Done

<!-- フェーズ2 で具体化した。フェーズ3(/implement)が実行して埋める -->

- [x] `claude-dev:928` / `claude-dev-mac:963` の後片付けが「名前衝突でない かつ 稼働中でない」ときだけ実行される
- [x] `claude-dev:736` / `claude-dev-mac:797`(停止中の残骸の削除)にも稼働中判定が入っている(委任 b)
- [x] 名前衝突時に `FR-env-01` 受入基準12 の内容(稼働中である旨・別ディレクトリの可能性・次に取るべき操作)を表示して終了コード 1 で終わる(実機の出力で確認)
- [x] **実機確認(`03-impl/tests/e2e.md` の E2E-01 手順7)を実行した**: basename が同じ2ディレクトリで `start` を2回実行し、(a) 終了コード 1、(b) 期待するメッセージ、(c) 先のコンテナ ID が不変、(d) `marker-a` が残存 — の4点を確認した。macOS 分は実行または「未実施」を明記した
- [x] `docs/02-design/environments.md`「ドキュメント整合検査コマンド」1〜7 が合格(6 の既知の誤検出30件を除く)
- [ ] `new-features/` の全変更指示(**9件**)を SSOT へ反映済み(`reflected:` 印) — `/task-close` で実施
- [x] `/doc-check task-fix-start-cleanup`(合成ビュー)が PASS(2026-08-04。反復1/5。実行後に変更指示を実態へ合わせたので、`/task-close` の前に再確認する)
- [ ] `/doc-check` が SSOT の影響範囲を PASS(反映後) — `/task-close` で実施
- [ ] `docs/histories/` に記録した — `/task-close` で実施
- [ ] `docs/issues/036` を削除した(事象が再現しないことを実機確認で確かめたうえで) — **実機確認は完了**(修正前は再現・修正後は再現しない)。削除は `/task-close` で実施
- [x] `docs/issues/020`(排他)/ `028`(命名)は**残す**(本タスクの範囲外。`MODULE-cli-start` の「既知の制限」から参照している)
- [ ] `docs/03-impl/index.md` の「実装の欠陥として起票済み」から 036 が外れ、件数が 16 になっている — `/task-close` で実施(**★`docs/issues/045` を起票したので実際の件数は 17 になる**。反映時に確認する)

## 進捗メモ

- 2026-08-04 フェーズ1完了。`docs/issues/036` を昇格。closure を確定し、決定シート5論点 + 委任2件を提示。
  影響範囲の調査は `relations-query.py --impact claude-dev` / `--upstream MODULE-cli-start` と
  コードの直読で行った。**走らせるテストは 0 件**(シェルに自動テストランナーが無い)。
  **回答「推奨通りで良い」を取得**(全項目・委任2件とも推奨案)。フェーズ2 へ移行。
- 2026-08-04 フェーズ2(`/task-doc`)。**01 → 02 → 03 の1回の下降で変更指示8ファイルを書いた**。
  下降中に closure を3件更新した(`02-design/logging.md` = 変更する / `03-impl/contracts/cli-container.md`
  = 変更する / `03-impl/tests/e2e.md` = **追加**)。フェーズは抜けていない。
  - **実装ドライラン パス1**(ドキュメントだけ): 未決点8件を洗い出し、**すべてドキュメント記載か
    委任決定(D0-scope-02 / D0-scope-03)に帰着**した。**人間判断に帰着した未決点は0件**。
  - **パス2**(コードの事実): 9件を「調査メモ」へ記録した(`is_running` の実体・`_run_err` に
    stderr が入っていること・ポート競合判定の書式・修正対象の行番号・`stop` の正当な削除)。
  - **独立レンズは走っていない**(Codex 利用上限。復旧 2026-08-10 19:52)。不変則7 により代替は
    無断で立てず、質問キューのプロセス項目として提示する。
  - **`check-changeset.py`**: I1(変更指示の形)は **OK**。I2 の13件は**未配線ツールの構造的偽陽性**
    (callee を `new-features/` 内だけで解決するため、SSOT にある callee を「存在しない」と数える)。
    同スクリプトの docstring 自身が「未配線」と明記しており、配線は
    `.claude/improvements/KIT-changeset-invariants.md` の課題である。
- 2026-08-04 フェーズ3(`/implement`)。**ゲート3条件を通過**(合格証の連鎖は MAJOR.MINOR 一致で有効 /
  未決点は人間判断0件 / lint・テストコマンドは実値)。コードは `claude-dev` と `claude-dev-mac` の
  各2箇所(計 44行追加・6行削除)。
  - **委任で決めたこと**: `D0-scope-02` = 判定は既存の `is_running` と `docker run` のエラー文言
    (`Conflict.` / `already in use by container`)で行い、所有者ラベルは導入しない / 手順7 にも
    同じ稼働中判定を入れる / メッセージを稼働中・停止中で書き分ける。
    `D0-scope-03` = Linux 版と macOS 版に同じ形で入れる。いずれも `MODULE-cli-start` の
    「実装上の判断」#5〜#8 に記録した。
  - **★実機確認で手順そのものの誤りが判明した**: 「basename が同じ2ディレクトリで順に `start`」
    では**衝突が起きない**(同名が稼働中なら手順6 の再接続経路に入って `exit 0` する。
    `claude-dev:715`)。衝突は**手順6 の判定を通り抜けたあと手順13 までの数秒の窓**で
    同名コンテナが現れたときだけ起きる。→ `tests/e2e.md` の手順7 を
    **決定論的な手順**(バックグラウンドで `start` を走らせ、`SSH 鍵が未設定` の行が出た直後に
    `docker run -d --name web busybox sleep 600` で代役を立てる)へ書き換え、
    `MODULE-cli-start` の「並行性」「異常系」「処理の流れ」も実態へ合わせた。
  - **修正前のコードでデータ破壊を再現した**(`git show HEAD:claude-dev` を使用):
    稼働中の代役コンテナ `50ec825bcd21` が `docker rm -f` で削除され、終了コード 1。
  - **修正後は再現しない**: 終了コード 1 / 期待どおりの4行のメッセージ / 代役 `40d224b3c9ed` が
    稼働継続 / `docker exec web ls /tmp/marker-a` が成功。
  - **回帰**: 衝突なしの通常起動は成功(終了コード 0)、再実行で「実行中。接続します...」の
    再接続経路に入る(`FR-env-01` 受入基準4)。
  - **後片付けで別の欠陥を発見 → `docs/issues/045` を起票**: `claude-dev stop` の遊休判定が
    `--filter ancestor=<現在のイメージ>` なので、**古いイメージで稼働中の Claude コンテナを
    数え落として共有 docker-proxy を削除する**(`FR-env-01` 受入基準9 違反)。
    実際に `claude-dev-env` の Docker アクセスが切れたので、**その場で docker-proxy を
    再作成して復旧した**(復旧確認済み)。本タスクの範囲外なので修正はしていない。
  - **機械検査(再生成後)**: `build-callgraphs.py` を実行 → 差分は `callgraphs/index.md` の
    shell 行数(1667 → 1689)だけで、**シンボルも辺も増えていない**(新しい関数を作らない方式の
    確認)。`cluster-features.py` 再生成 → 機能 82 / 辺 121 で変化なし。
    `callgraph-check.py --to-be task-fix-start-cleanup` **高0件**。
  - lint: `go vet ./...`(両モジュール)= 0 / 単体テスト: `go test ./...`(docker-proxy /
    orchestrator)= ok / `bash -n` で両 CLI の構文検査 OK。

- 2026-08-04 **`/doc-check task-fix-start-cleanup` 判定: PASS**(反復 1/5)。
  実行形態は**著者セッション**(本セッションの運用ルールでサブエージェントを起こせないため
  `/doc-check` §0A の3行目)。**独立レンズは走っていない**(Codex 利用上限。復旧 2026-08-10 19:52。
  task モードはゲートではないので続行し、代替の可否を決定シートへ載せた)。
  - **check F(変更指示の妥当性)**: 9件すべて `target` 実在・`sections` の見出しが SSOT と
    文字列一致(計13見出し)・`deletes` 明示・`reflected`/`version`/`verified` の混入なし・
    同一 target の重複なし。**他タスクは存在しないので衝突なし**。
  - **検出した指摘(1件・中)**: `docs/03-impl/tests/strategy.md:115` の「機能要件の全 **180** 基準に
    行がある(対応表 195 行)」が、受入基準を2つ増やすと**失効する**。実測で 01 の機能要件の
    受入基準 = 180 / tests の `FR-` 行 = 180 / `NFR-` 行 = 15 を確認し、**182 / 197** へ直す
    変更指示を追加した(closure も更新)。→ **自動修正として処理**(指標の定義は変えていない)。
  - **A3**: 追加した受入基準12・13 は `tests/cli-start.md` に**1回だけ**行があり、
    `tests/strategy.md:94` の「受入基準の行は主担当モジュール1つにだけ置く」を満たす。
    状態は「実装済み」で、実機確認の手順は `tests/e2e.md` の E2E-01 手順7 が持つ。
  - **E(02 ⇄ 03 連携差分)**: `PLAN-cli-start` と `MODULE-cli-start` の `callees` / `contracts` は
    **変更なし**(新しい関数を作らない方式なので辺が増えない)。差分ゼロ。
  - **C7(曖昧語)**: 変更指示9件を走査して**0件**(`適切に` / `正しく` / `高速に` / `柔軟に` /
    `軽微` / `素早く` / `安全に` / `必要に応じて` / `十分に` / `なるべく`)。
  - **C8**: 追加した受入基準は EARS の IF…THEN 形式で、判定可能な条件(終了コード 1・表示内容・
    削除しないこと)を書いている。
  - **機械検査**: `build-callgraphs --check` 最新 / `cluster-features --check` 最新 /
    `callgraph-check --to-be task-fix-start-cleanup` **高0件** / `check-relations` 合格(82/82)/
    `check-contracts` 合格 / `build-index --check` 差分なし。
  - **未決点**: 人間判断に帰着したものは**0件**(パス1 の8件はすべてドキュメント記載か委任決定)。
    → **`/implement task-fix-start-cleanup` へ無人で進める。**
  - **最も弱い点(重大度 低)**: 合成ビューでは `03-impl/index.md` が「036 は解消済み」と述べる一方、
    `docs/issues/036` のファイルはまだ存在する。これは**実装後に `/task-close` が削除する**ことで
    整合する状態であり、task モードの合成ビュー(= 実装後の姿)としては正しい。
    ただし**実装せずにこのタスクを閉じると矛盾が残る**ので、DoD に036 の削除を明記してある。

## 申し送り事項

- **★`docs/issues/045`(新規・2026-08-04): `MODULE-cli-stop` の「既知の制限」へ書くこと。**
  本タスクの影響範囲は `MODULE-cli-start` なので、045 の記述は
  **`MODULE-cli-stop` を影響範囲に含む次のタスク**で行う(`03-impl/index.md` の
  「実装の欠陥として起票済み」の数え方は「`既知の制限` から参照されているもの」なので、
  それまで 045 は集計に入らない。`014` と同じ扱いであることを index.md に明記した)。
- **`docs/issues/020`(CLI に排他機構が無い)/ `028`(命名の一意化)/ `024` / `025` / `029`
  (`stop` / `reset` / `logout` が他プロジェクトの資源を消す)/ **`045`** は同根**である。
  本タスクの後に「破壊的操作を自分の資源に限る」タスクを1本立てると、
  そのタスクの起点として `D0-env-08`(決定シート論点5 の案B)を 00 に起こせる。
- **前タスク `task-impl-depth` から引き継いだ残件**: ①仕様の測定可能性
  (`docs/issues/043` + `017` + `041` 案D + `042` + `044` の下降)/ ②relations をコードへ全面追随
  (`docs/issues/038` + `032` + 契約)の2本。**②は本タスクが `MODULE-cli-start` を動かすので、
  本タスクを閉じた後に着手する**(先に②を回すと同じファイルを2回直す)。
- **2026-08-10 19:52 以降に `/doc-check full` を新しいセッションで1回**走らせること
  (2026-08-04 の合格証3実行分は独立レンズが1本も走っていない。Codex 利用上限)。
  `.claude/improvements/KIT-close-task-versionless-docs.md` のキット変更もその監査対象に含める。
