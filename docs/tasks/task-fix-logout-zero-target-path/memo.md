---
id: task-fix-logout-zero-target-path
phase: 実装
lane: critical
origin_layer: 01
external_behavior: true
irreversible_data: false
security_payment_privacy: true
public_contract_breaking: false
shared_resource_format: false
unresolved_impact: false
rollback_defined: true
issue:
  - docs/issues/052-bug-logout-skips-unmanaged-warning-when-nothing-to-delete.md
  - docs/issues/053-bug-logout-treats-unlistable-auth-volume-as-empty.md
  - docs/issues/089-bug-logout-lists-session-spawned-containers-as-unmanaged.md
date: 2026-08-11
updated: 2026-08-11
source:
  - docs/01-requirements/functional.md
  - docs/02-design/logging.md
  - docs/02-design/contracts/cli-container.md
  - docs/02-design/system.md
  - docs/02-design/relations.md
  - docs/03-impl/relations/MODULE-cli-logout.md
  - docs/03-impl/relations/MODULE-cli-common-spawned-resources.md
  - docs/03-impl/contracts/cli-container.md
  - docs/03-impl/tests/cli-logout.md
  - docs/03-impl/tests/e2e.md
  - docs/03-impl/index.md
summary: logout の削除対象0件の経路で、ラベル無しコンテナの警告に到達せず、共有ボリュームの状態を確かめずに 0 で終わる2つの欠陥を閉じる
---

# task-fix-logout-zero-target-path logout の削除対象0件の経路を直す

> 保管: `memo-1.md` = 調査メモ(19件)+ フェーズ1・2 の進捗メモ

> 解決済みの経緯: (まだ無し)

## 目的

`claude-dev logout` の「削除対象0件」の早期終了経路(`MODULE-cli-logout` 手順6)が持つ2つの欠陥を
閉じる。利用者が `logout` の効果を誤解する状態を残さない(`D0-env-08` の目的)。

- `docs/issues/052`: この経路はラベル無し稼働コンテナの列挙と「認証が書き戻される」警告に到達しない。
- `docs/issues/053`: 「共有ボリュームが空」の判定が列挙の失敗と空を区別せず、認証が残っていても
  「削除対象がありません」と表示して終了コード 0 で終わる。
- `docs/issues/089`(2026-08-11 の決定シート 論点3 で畳むと確定): `logout` がセッション由来の
  コンテナを「管理ラベルを持たない」と事実に反して表示する。052 の修正がこの表示ブロックを
  新しい経路からも呼ぶため、同時に直さないと誤表示が2箇所へ増える。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | `FR-env-03` 受入基準19 の書き換え(2点。論点1=案A / 論点2=案B)/ `logging.md` の既存2行の発火条件の明示と1行の新設 / `CTR-cli-container` のエラーケース1行の新設 / `MODULE-cli-logout` 手順6 の書き換え / **`MODULE-cli-logout` 手順4 への `claude-dev.role=spawned` の除外の追加(`docs/issues/089`。論点3=畳む)** / `E2E-01` 手順8 への確認項目の追加と新設手順1つ / 実装2箇所(`claude-dev` / `claude-dev-mac`) |
| やらないこと(このタスクの範囲外) | **`FR-env-03` 受入基準17 の条件節を広げること**(論点1 で案A が確定したので触らない。したがって `docs/issues/055` の 01 ⇄ 02 の食い違いは範囲外のまま残る)/ **遊休 docker-proxy を「削除対象が0件」に数えること**(概念2 で「やらないこと」へ回すと確定)/ `reset` 側の振る舞いの変更(0件の早期終了と空判定を持たないため対象が無い。調査メモ 4)/ 停止中のラベル無しコンテナの列挙(`docs/issues/055`)/ `docs/issues/080`(破壊的操作が UC のフローに無い)/ `PLAN-cli-logout` の「連携の詳細」節の新設(申し送り事項へ) |

## 影響範囲(closure)

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | - | - | 変更なし(理由: `D0-env-08` は目的「消したつもりで残る状態を作らない」と項5「削除の失敗を握りつぶさない」を既に持ち、項1・項5 の条件節を動かす必要が無い。`D0-env-05` 項2 の `logout` の除外範囲も動かない) |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | replace |
| 01 | - | - | usecases.md は変更なし(理由: 破壊的操作の条項はどの UC のフローにも現れず、シナリオ外要件にも無い = `docs/issues/080` の既知の欠落。本変更はその欠落を拡げも縮めもしない) |
| 02 | docs/02-design/logging.md | new-features/02-design/logging.md | replace |
| 02 | docs/02-design/contracts/cli-container.md | new-features/02-design/contracts/cli-container.md | replace |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | replace |
| 02 | docs/02-design/relations.md | new-features/02-design/relations.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-logout.md | new-features/03-impl/relations/MODULE-cli-logout.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-common-spawned-resources.md | new-features/03-impl/relations/MODULE-cli-common-spawned-resources.md | replace |
| 03 | docs/03-impl/contracts/cli-container.md | new-features/03-impl/contracts/cli-container.md | replace |
| 03 | docs/03-impl/tests/cli-logout.md | new-features/03-impl/tests/cli-logout.md | replace |
| 03 | docs/03-impl/tests/e2e.md | new-features/03-impl/tests/e2e.md | replace |
| 03 | docs/03-impl/index.md | -(§3-4 で版のみ更新) | 版のみ更新 |

<!-- 2026-08-11: 論点3 = 「畳む」で確定したので docs/issues/089 の分も入るが、
     行き先は既に表に在る MODULE-cli-logout と実装2箇所なので**この表の行は増えない**
     (089 は 02 契約の既定に実装が追いついていない = origin_layer: 03。01/02 は動かない)。
     コード(claude-dev / claude-dev-mac)は SSOT ではないので、この表には現れない。 -->

## 読む範囲(読了記録)

- 全文読了: 2026-08-11
  - docs/00-requests/acceptances.md@1.4.1
  - docs/00-requests/decisions/auth.md@1.3.0
  - docs/00-requests/decisions/dist.md@1.2.0
  - docs/00-requests/decisions/env.md@1.5.0
  - docs/00-requests/decisions/scope.md@1.2.0
  - docs/00-requests/decisions/sec.md@1.3.0
  - docs/00-requests/request.md@1.4.0
  - docs/00-requests/terminology.md@1.5.0
  - docs/01-requirements/decisions/split.md@1.3.0
  - docs/01-requirements/functional.md@1.13.1
  - docs/01-requirements/non-functional.md@1.7.0
  - docs/01-requirements/system.md@1.2.1
  - docs/01-requirements/usecases.md@1.5.0
  - docs/02-design/architecture.md@1.5.0
  - docs/02-design/contracts/cli-container.md@1.8.0
  - docs/02-design/contracts/docker-api.md@1.1.0
  - docs/02-design/contracts/entrypoint-firewall.md@1.0.1
  - docs/02-design/environments.md@1.4.0
  - docs/02-design/logging.md@1.5.0
  - docs/02-design/relations.md@1.9.0
  - docs/02-design/system.md@2.10.1
- 不要: なし(lane: critical のため 00〜02 を全文読了した)

## 決定シート(回答済み)

> 回答済み: sheet.md(転記済み)

<!-- 2026-08-11 に人間が sheet.md へ記入した(概念3件に記入あり、論点3件は空欄)。
     「一括回答」と「記入完了」は空欄。人間の発言「記入したので進めて」(2026-08-11)により
     返答済みと確定し、空欄のブロックは task-memo.md §1.2 の規則どおり「既定を承認」
     (= 各ブロックの「未回答時の既定」= AI推奨のとおりにする)として扱う。 -->

| # | 論点 | 回答 | 反映先 |
|---|---|---|---|
| 概念1 | 「共有ボリュームが空」の外延 | 回答(sheet.md 逐語: 「AI推奨のとおり」)= 空 は**空であることを確かめられた状態**。一時コンテナを起動できず出力が空だった場合は「空」に含まない | `FR-env-03-19` / `new-features/01-requirements/functional.md` |
| 概念2 | 「削除対象が0件」に何を数えるか | 回答(sheet.md 逐語: 「AI推奨のとおりにする((b) は「やらないこと」へ回す)」)= ラベル無し稼働コンテナも遊休 docker-proxy も0件には数えない。ただしラベル無しが在れば名前と書き戻しの警告を表示する。(b) 遊休 docker-proxy は「やらないこと」 | `FR-env-03-19` / `new-features/01-requirements/functional.md` |
| 概念3 | 状態を確認できなかったときの振る舞い | 回答(sheet.md 逐語: 「AI推奨のとおり」)= (i) 通常経路へ進める(列挙 → 確認 → 削除 → 手順10 の印で失敗を検出し終了コード 1) | `FR-env-03-19` / `new-features/01-requirements/functional.md` + `new-features/02-design/logging.md`(新設行) |
| 論点1 | `docs/issues/052` の対処 | 既定を承認(空欄 = 未回答時の既定 = AI推奨)= **案A**。`FR-env-03-19` に「ラベル無しの稼働中コンテナがあるなら名前と書き戻しの警告は表示する」を足す。**受入基準17 は触らない**ので `docs/issues/055` は範囲外のまま | `FR-env-03-19` / `new-features/01-requirements/functional.md` + `new-features/02-design/logging.md`(既存2行の発火条件の明示) |
| 論点2 | `docs/issues/053` の対処 | 既定を承認(同上)= **案B**。`FR-env-03-19` に「共有ボリュームの状態を確認できなかった場合はこの経路に入らない」を明記してから実装を直す | `FR-env-03-19` / `new-features/01-requirements/functional.md` + `new-features/02-design/contracts/cli-container.md`(エラーケース新設行) |
| 論点3 | `docs/issues/089` を畳むか | 既定を承認(同上)= **畳む(案A)**。closure に 089 分(`MODULE-cli-logout` 手順4 と「既知の制限」/ 実装2箇所)を加える。01/02 は動かない | `MODULE-cli-logout` / `new-features/03-impl/relations/MODULE-cli-logout.md` |
| 方針合意 | 各ドキュメントへの変更方針8行 | 空欄 = 全方針に合意(sheet.md「方針合意」節) | シートの「方針合意」節がそのままフェーズ2の作業方針 |

## 未決点

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| 1 | 概念1〜3・論点1〜3 | 2026-08-11 に人間が回答(シート / 既定を承認) | /task-new §3 |
| 2 | 印が出た**直後に列挙が失敗**した場合、出力が印だけになり「空だった」と区別できない(手順10 も同じ形だが、手順6 は新しく受入基準19 の「確認できた」を担うので放置できない) | **委任決定(DS-02)**: 印 + **一時コンテナの終了ステータス 0** + 印以外の行なし の3条件の論理積にする。`MODULE-cli-logout` 手順6 と判断15、02/03 契約へ記載 | フェーズ2 実装ドライラン パス1 |
| 3 | 0件の経路で、ラベル無しコンテナの**集合の問い合わせ自体が失敗**していたとき何を出すか(黙ると「0件だった」と区別できない) | **委任決定(DS-03)**: `claude-dev:1116` と同じ文言で「問い合わせに失敗したため列挙できなかった」を出す。`MODULE-cli-logout` 手順6 へ記載 | フェーズ2 実装ドライラン パス1 |

## 調査メモ(memo-1.md に移動)

## 質問キュー(未提示)

| # | 論点 | 何が止まるか | 推奨する回答(暫定) |
|---|---|---|---|
| - | なし(すべて sheet.md へ載せた) | - | - |

## タスクリスト

- [x] 1. **手順6 の「空」判定を3条件へ差し替える**(印 + 終了ステータス 0 + 印以外の行なし)。`claude-dev` と `claude-dev-mac` の同一箇所 _要件:_ FR-env-03-19 _Boundary:_ `claude-dev:993`〜`:1002` / `claude-dev-mac:1061`〜`:1070` _Depends:_ -
- [x] 2. **確かめられなかったときは0件の経路に入らない**ようにし、その旨を表示して手順7 の確認へ落とす _要件:_ FR-env-03-19 _Boundary:_ 同上 _Depends:_ 1
- [x] 3. **0件の経路の直前で、ラベル無しコンテナの名前・書き戻しの警告・問い合わせ失敗の旨を表示する**(手順11 と同じ出力ブロックを使う) _要件:_ FR-env-03-19 _Boundary:_ `claude-dev:999`〜`:1002` と `:1108`〜`:1117` _Depends:_ 1
- [x] 4. **手順4 の `_unmanaged` から `claude-dev.role=spawned` を除外する**(`spawned_resources` を `reset` と同じ引数で呼び、`:2091` と同型の突き合わせを置く) _要件:_ FR-env-03-17 _Boundary:_ `claude-dev:972`〜`:983` / `claude-dev-mac:1040`〜`:1051` _Depends:_ - (P)
- [~] 5. **E2E-01 手順8-5 (セッション由来の除外) / 8-8 の (e) / 8-18 を実機で流す**(macOS 側も。実行できない場合は未実施を記録する) **→ 2026-08-11: 実機 E2E は未実施(論点4 で人間の判断待ち)。隔離ハーネスで代替確認済み — 下の DoD 表と進捗メモを参照** _要件:_ FR-env-03-17・19 _Boundary:_ `docs/03-impl/tests/e2e.md` の手順 _Depends:_ 1,2,3,4

## Definition of Done

- [x] lint が通る: `go vet ./...`(`docker-proxy/` で実行。**本タスクは Go を触らないので回帰確認のみ**)
- [x] 単体・結合テストが通る: `cd docker-proxy && go test ./...`(同上)
- [x] 受入基準のテストが全て存在し通る(未検証行を残さない) — **`FR-env-03` は自動テストを持たない**(memo-1.md 調査メモ 13)。`03-impl/tests/cli-logout.md` の該当行が E2E-01 手順8-8 (d)(e) と 8-18 を指すことを確認した
- [ ] 影響する E2E シナリオが通る: E2E-01(手順8-8 の (e) と、053 用の新設手順8-18)**→ 実機は未実施。隔離ハーネスで代替確認済み(進捗メモの表)。誰が流すかは sheet.md 論点4**
- [x] `CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py task-fix-logout-zero-target-path) && python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT"` でコールグラフを再生成し、`callgraph-check.py --to-be task-fix-logout-zero-target-path` の重大度「高」が0
- [x] `check-relations.py` が合格
- [ ] `new-features/` の全変更指示を SSOT へ反映済み
- [ ] `/doc-check` が影響範囲を PASS
- [ ] `docs/histories/` に記録
- [x] 見つけた範囲外の問題を `docs/issues/` / `docs/pendings.md` に記録済み(`docs/issues/098` / 残務1行)
- [ ] **起点となった issue 3件を削除済み**(`docs/issues/052` / `053` / `089`。frontmatter の `issue:` は3件のリストである — `/task-close` §7-2 は単数形で書かれているので取りこぼさないこと)

## 進捗メモ

> フェーズ1・2 の進捗メモは memo-1.md に移動した。
- 2026-08-11 フェーズ3 開始。**ゲート3条件を通過**: (1) closure 全 SSOT の `verified.version` が
  自身の MAJOR.MINOR と一致(`02-design/system.md` 2.10.1 対 検証 2.10.0 / `03-impl/index.md`
  1.22.1 対 1.22.0 は PATCH 差なので原則6 を満たす)。(2) 未決点は上表の3件すべて帰着済み
  (回答 / 委任決定)。(3) `environments.md` の lint = `go vet ./...` / 単体 = `cd docker-proxy &&
  go test ./...` が「未定」でないことを確認。着手前の回帰確認として両方を実行し **exit 0**
  (`ok github.com/quvox/claude-dev-env/docker-proxy`)。タスクリストは既存の5件をそのまま使う。

- 2026-08-11 フェーズ3 実装完了(タスク1〜4)。**実施順は 1 → 2 → 4 → 3**。理由: タスク3 の
  表示文字列はタスク4 が決める「セッション由来の一覧を引けなかった」行を含むため、4 を先に
  入れると同じ行を二度書かずに済む。**タスクリストがタスク4 に `(P)` を付けて並列可と宣言済み
  なので、これは新しい判断ではなく宣言済みの並列化の実施である**(委任の行使ではないため
  `[DS-nn]` の開示行は立てない)。
  コミット: `96bbdbd`(1) / `55f1d12`(2) / `a4dc297`(4) / `56a65ba`(3)。
  変更ファイルは `claude-dev` と `claude-dev-mac` の2本のみ(各 +74/-16 行 = **正味 +58 行**)。
  `logout` 分岐は両 OS で**バイト単位で同一**であることを `diff` で確認(0差分。`D0-scope-03`)。

- 2026-08-11 フェーズ3 で行使した委任(フェーズ2 の4件に加えて):
  - **[DS-05]** ラベル無しコンテナの表示文言を、共有シェル関数ではなく**組み立て済みの文字列変数**
    `_unmanaged_notice` で手順6 と手順11 に共用させた — 理由: 判断16 が要求する「文言を複製しない」
    を満たす手段は関数と変数の2つだが、トップレベルにシェル関数を1つ増やすとコールグラフの記号が
    1つ増え、この変更指示が持たない機能を `relations/` に新設することになる(抽出器は入れ子の関数
    定義も記号として拾う — `.claude/scripts/cgx/shell_regex.py` の `_FUNC` 走査) /
    見直す条件: 出力点が3箇所目になったとき。**開示先: `MODULE-cli-logout` 実装上の判断18**

- 2026-08-11 **「実装上の判断」「テスト設計の判断」の棚卸し**(`delegation.md` §3.1。触った4本):
  - `MODULE-cli-logout` 判断1〜17: **全件「継続」**。見直す条件が起きたものは無い。ただし判断13 の
    引用は行番号のずれで `claude-dev:1077`-`:1095` → **`:1145`-`:1163` へ取り直した(PATCH)**。
    判断18 を新設(上記 [DS-05])。
  - `MODULE-cli-common-spawned-resources` の判断: **全件「継続」**(この機能の振る舞い・引数・戻り値・
    異常系は1文字も変わらず、呼び出し元が1つ増えただけである)。引用 `:1639`/`:1977`/`:1982` は
    `+58` で取り直した(PATCH)。
  - `tests/cli-logout.md` テスト設計の判断1〜5: **全件「継続」**。判断4(0件経路の確認を手順8-8 に
    相乗りさせる)と判断5(壊した状態の確認は独立した手順8-18)は、実機で流していないので
    前提は動いていない。
  - `tests/e2e.md` の `[DS-01]` 各行: **全件「継続」**。

- 2026-08-11 **C-0 の検証: 実機 E2E-01 手順8 は未実施**。理由: 手順8 は `claude-dev login`(対話 OAuth)
  から始まり `logout --yes` / `reset --yes` を含むため、**このホストで流すと利用者の現在の
  Claude / Codex 認証(`claude-dev-auth` の中身 21 項目)と claude-dev のイメージ・ボリュームが実際に
  消える**。無人のフェーズ3 が独断で行ってよい操作ではない(macOS 版は当環境では実行不能)。
  代わりに**隔離ハーネス**で実機の Docker に対して確認した — `claude-dev` の複製の資源名を
  `cdx-e2e-*`、ラベルを `cdx-e2e.*` へ書き換え、専用のボリューム・ネットワーク・コンテナを作り、
  `HOME` も一時ディレクトリへ向けた。**修正前(`effdcac`)と修正後で同じ状態を流し、3つの欠陥が
  いずれも修正前だけ再現することを確認した**。実出力(逐語):

  | # | 状態 | 修正前(`effdcac`) | 修正後(`56a65ba`) |
  |---|---|---|---|
  | S1 (`052`) | 0件 + ラベル無し稼働コンテナ `cdx-legacy-claude` | 「削除対象がありません」だけ / exit 0 | 同文 + 「管理ラベルを持たないため削除しなかったコンテナ: cdx-legacy-claude」+ 書き戻しの警告 / exit 0 |
  | S2 (`089`) | S1 + `cdx-e2e.role=spawned` の `cdx-spawn-a` | (通常経路で)ラベル無し欄に `cdx-spawn-a` が出る | `cdx-spawn-a` は出ない(`cdx-legacy-claude` のみ) |
  | S3 (`053`) | 認証が残った状態で一時コンテナを起動できない(`IMG_CLAUDE`=busybox) | 「削除対象がありません」/ **exit 0** | 「共有ボリューム … が空かどうかを確認できませんでした」→ 非TTY で **exit 1**(受入基準15) |
  | S4 (対照) | 0件 + 空を確認できる | 「削除対象がありません」/ exit 0 | 同一(余分な行は出ない) |
  | S5 (受入基準18) | S3 の状態で `--yes` | — | 「消去を確認できませんでした」→ 消えなかった資源を列挙 / **exit 1**。ボリュームの `.credentials.json` は残存 |
  | 回帰 | 管理ラベル付きコンテナを消す通常経路(手順11) | — | 修正前と**089 分の1行を除いて同一出力**(表示の共通化で文言が変わっていないこと) |

  隔離資源は実行後に削除済み。利用者の `claude-dev-*` ボリューム・`~/.claude-dev/locks/` は無傷
  (確認済み)。**未確認のまま残るのは (a) 実イメージ `claude-dev-claude` での手順8-18、
  (b) macOS 版の実行、(c) 手順8 の他の部分手順の回帰**であり、これを誰が流すかは**論点4** で問う。

- 2026-08-11 **C-1**: `resolve-callgraph-out.py` → `build-callgraphs.py` → `cluster-features.py` を
  タスク配下へ生成し、`callgraph-check.py --to-be` = **重大度「高」0 件(終了コード 0)**。
  新しい辺 `MODULE-cli-logout` → `MODULE-cli-common-spawned-resources` は機械側で**確定**として出て、
  02/03 の変更指示の宣言と一致した(片側漏れなし)。残る指摘 24 件はすべて中・低・参考で、
  いずれも `logout` と無関係な既存分(`MODULE-entrypoint-claude` の CG3 3件・CG2 8件・
  Makefile の CG4 12件・CG3 1件)。
  変更指示の追記: `MODULE-cli-logout` の「異常系」へ2行(手順6 で確かめられなかった / セッション由来の
  一覧を引けなかった)と、0件の行の書き換え、実装上の判断18。`tests/e2e.md` の `reason` が指す部分手順
  番号を実体(手順8-5 / 手順8-8)へ修正(**PATCH**)、`tests/cli-logout.md` の `FR-env-03-19` 行を
  (d) と (e) の2つで名指すよう修正(**PATCH**)。
  **意図する版の上げ幅は変更指示の `version_bump` のまま**(`/task-close` が上げる)。

- 2026-08-11 **行番号引用のずれ**: 正味 +58 行のため、旧 1119 行目以降を指す `path:line` が古くなった。
  closure 内の3件(`03-impl/contracts/cli-container.md` 64箇所 / `MODULE-cli-logout` 6箇所 /
  `MODULE-cli-common-spawned-resources` 8箇所)は**内容を1件ずつ突き合わせて取り直した**
  (`git show effdcac:claude-dev` の当該行と現在行の文字列一致で全件検証。変更範囲の内側にある
  6箇所は個別に取り直した)。closure 外の 03-impl ドキュメント9件は原則8 に従い
  `docs/pendings.md` の残務へ1行(バグではない — `.claude/directions/03-impl.md` が
  「行番号は編集ごとに腐る」ことを前提に安定なアンカーを勧めており、機械検査も無い)。

- 2026-08-11 **範囲外で見つけた欠陥を1件起票**: `docs/issues/098`(手順10 で消去を確認できなかった
  共有ボリュームが「削除した資源」にも列挙される。`claude-dev:1150`-`:1164`。severity 中 /
  origin_layer 03)。S5 の実出力で観測した。手順10 は本タスクの closure に無いので直していない。

- 2026-08-11 **DoD の実測**(`git rev-parse HEAD` = `56a65ba5f58bcc1fc70d65590bc62a37608081fc`):

  | DoD 項目 | 結果 | コマンドの最終行(逐語) |
  |---|---|---|
  | lint | ✅ | `go vet ./...` は出力なしで終了コード 0 |
  | 単体・結合テスト | ✅ | `ok  	github.com/quvox/claude-dev-env/docker-proxy	(cached)` |
  | 受入基準のテストが存在し通る | ✅(表の指し先) | `FR-env-03` は自動テストを持たない(調査メモ 13)。`tests/cli-logout.md` の該当行が E2E-01 手順8-8 (d)(e) と 8-18 を指すことを確認 |
  | 影響する E2E シナリオ(E2E-01) | ❌ **未実施** | 実機実行は利用者の認証を破壊するため実施せず。隔離ハーネスで S1〜S5 + 回帰を確認(上表)。**論点4 で判断待ち** |
  | コールグラフ再生成 + `callgraph-check.py --to-be` 高0 | ✅ | `最新。再生成しても差分は出ない。` / `callgraph-check.py --to-be` 終了コード 0(高 0 件) |
  | `check-relations.py` | ✅ | `合格: 対称性・参照実在・impl パス・必須項目・機能表との 1:1すべて問題なし。` |
  | `check-changeset.py` | ✅ | `合格: 不変条件の違反なし` |
  | `new-features/` を SSOT へ反映 | `/task-close` で実施 | — |
  | `/doc-check` が影響範囲を PASS | `/task-close` で実施 | — |
  | `docs/histories/` に記録 | `/task-close` で実施 | — |
  | 範囲外の問題を記録 | ✅ | `docs/issues/098` を新設 / `docs/pendings.md` の残務へ1行 |
  | 起点の issue 3件(052 / 053 / 089)を削除 | `/task-close` で実施 | — |

- 2026-08-11 **回答待ち**: `sheet.md` の**論点4**(E2E-01 手順8 の実機実行を誰がやるか)。
  未回答のまま `/task-close` へは進まない(`/implement` C-4-4)。

## 申し送り事項

- **`02-design/relations.md` に `PLAN-cli-logout` の「連携の詳細」節が無い**(`PLAN-cli-stop` /
  `PLAN-cli-reset` / `PLAN-entrypoint-claude` / `PLAN-docker-proxy-serve` / `PLAN-cli-common-*` には
  在る)。`reset` の「失敗の扱い」だけが「列挙の問い合わせの失敗を0件と区別する」を持ち、`logout`
  側には同じ意図を書く場所が無い。**バグではなくドキュメント整合の穴なので、原則8 に従い
  `docs/pendings.md` の残務へ1行**(`/task-close` で起票する)。
- 再検証候補が2件ある(調査メモ 11): `03-impl/contracts/cli-container.md` と
  `03-impl/tests/cli-logout.md` の `against`。どちらも本タスクの closure に入っているので、
  `/task-close` の検証済み記録の再発行で解消する。
- `docs/issues/055`(受入基準17 が停止中のラベル無しコンテナの表示まで求めている / 01 ⇄ 02 の
  食い違い)は**範囲外で残る**(2026-08-11 に論点1 = 案A が確定し、受入基準17 を触らないため)。
  受入基準17 を次に動かすタスクは 055 を同じ降下に入れること。
- 並行タスクは無い(このタスクの作成時点で `docs/tasks/` は空だった)。
