---
id: task-fix-logout-records-and-marker
phase: 決定
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
  - docs/issues/098-bug-logout-reports-unverified-auth-volume-as-deleted.md
  - docs/issues/099-bug-logout-equates-a-failed-managed-container-query-with-zero.md
  - docs/issues/100-bug-logout-cannot-tell-a-file-named-like-the-marker-from-the-marker.md
date: 2026-08-11
updated: 2026-08-11
source:
  - docs/01-requirements/functional.md
  - docs/02-design/contracts/cli-container.md
  - docs/02-design/logging.md
  - docs/03-impl/relations/MODULE-cli-logout.md
  - docs/03-impl/contracts/cli-container.md
  - docs/03-impl/tests/cli-logout.md
  - docs/03-impl/tests/e2e.md
  - docs/03-impl/index.md
summary: logout の削除結果の記録(消えていない資源を削除済みに数える / 列挙の失敗を0件と同一視する)と、共有ボリュームの「空」判定の印の見分け方を直す
---

# task-fix-logout-records-and-marker logout の削除判定の記録と印の判定を直す

> 解決済みの経緯: (まだ無し)

## 目的

`claude-dev logout` が「何が消えて何が残ったか」を誤って記録・表示する3つの欠陥を閉じる。
いずれも `D0-env-08` 項5「削除の失敗を握りつぶさない」と `D0-scope-07` の観測点の定義に反する。

- `docs/issues/098`: 手順10 で消去を確認できなかった共有ボリュームが、「削除できなかった資源」と
  **同時に「削除した資源」にも**列挙される(消えていないものを消したと表示する)。
- `docs/issues/099`: 手順4 の管理ラベル付きコンテナの `docker ps` が失敗しても空集合になるため、
  **確認できていないのに**削除対象0件の経路へ入って終了コード 0 で終わりうる。
- `docs/issues/100`: 「空」判定が `grep -vxF` で行の**内容**を見るため、`/auth` に印
  `__CLAUDE_DEV_AUTH_LISTED__` と同名のファイルがあると非空でも空と判定される(手順6・手順10 の両方)。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | `FR-env-03-19` の0件条件のうち**コンテナの集合**にも「無いことを確認できた」を課す(概念1・2)/ `CTR-cli-container` のエラーケースに「管理ラベル付きコンテナの列挙そのものが失敗した」を新設 / `logging.md` に「削除した資源」の外延(= 消えたことを確認できた資源だけ)を明記 / `MODULE-cli-logout` の手順4・6・10・11 と契約の印の判定を書き換え / 実装2箇所(`claude-dev` / `claude-dev-mac`)/ E2E-01 手順8 への確認の追加 |
| やらないこと(このタスクの範囲外) | **`MODULE-cli-common-destructive` に「1資源は3配列のうち1つだけ」の番人を置くこと**(調査メモ 3。`reset` 側に同型が無いので呼び出し側で直す)/ **`reset` の振る舞いの変更**(同型の二重記録を持たない — 調査メモ 3)/ **停止中のラベル無しコンテナの列挙**(`docs/issues/055`。受入基準17 の条件節は触らない)/ **closure 外の 03-impl 9件の行番号引用の付け替え**(調査メモ 5。本タスクでコード行が再びずれるので、一括の掃除タスクに委ねる)/ `docs/issues/097`(`help\|*)` 分岐が機能表に無い) |

## 影響範囲(closure)

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | - | - | 変更なし(理由: `D0-env-08` 項5「削除の失敗を握りつぶさない」と `D0-scope-07` の観測点の定義が既に3件すべての根拠を持つ。条件節を動かす必要が無い) |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | replace |
| 01 | - | - | usecases.md は変更なし(理由: 破壊的操作の条項はどの UC のフローにも現れない = `docs/issues/080` の既知の欠落。本変更はその欠落を拡げも縮めもしない) |
| 02 | docs/02-design/contracts/cli-container.md | new-features/02-design/contracts/cli-container.md | replace |
| 02 | docs/02-design/logging.md | new-features/02-design/logging.md | replace |
| 02 | - | - | system.md は変更なし(理由: 条項 ID は動かさないのでカバレッジ表の行は不変。`SCR-01` の「表示は 01 が正」の列挙には 2026-08-11 に受入基準19 を入れたので追加も不要) |
| 02 | - | - | relations.md は変更なし(理由: 呼び出す先が増えない。修正はすべて `logout` の中の記録と判定であり、`MODULE-cli-common-destructive` の呼び方も変えない — 調査メモ 3) |
| 03 | docs/03-impl/relations/MODULE-cli-logout.md | new-features/03-impl/relations/MODULE-cli-logout.md | replace |
| 03 | docs/03-impl/contracts/cli-container.md | new-features/03-impl/contracts/cli-container.md | replace |
| 03 | docs/03-impl/tests/cli-logout.md | new-features/03-impl/tests/cli-logout.md | replace |
| 03 | docs/03-impl/tests/e2e.md | new-features/03-impl/tests/e2e.md | replace |
| 03 | docs/03-impl/index.md | -(§3-4 で版のみ更新) | 版のみ更新 |

<!-- 起点は 01 である。`docs/issues/099` は `origin_layer: 03` で起票されていたが、
     §2 の判定で 01 へ改めた(理由は調査メモ 1)。issue 側の値も 2026-08-11 に修正した。
     コード(claude-dev / claude-dev-mac)は SSOT ではないのでこの表には現れない。 -->

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
  - docs/01-requirements/functional.md@1.14.0
  - docs/01-requirements/non-functional.md@1.7.0
  - docs/01-requirements/system.md@1.2.1
  - docs/01-requirements/usecases.md@1.5.0
  - docs/02-design/architecture.md@1.5.0
  - docs/02-design/contracts/cli-container.md@1.9.0
  - docs/02-design/contracts/docker-api.md@1.1.0
  - docs/02-design/contracts/entrypoint-firewall.md@1.0.1
  - docs/02-design/environments.md@1.4.0
  - docs/02-design/logging.md@1.6.0
  - docs/02-design/relations.md@1.10.0
  - docs/02-design/system.md@2.11.0
- 不要: なし(lane: critical のため 00〜02 を全文読了した)

<!-- 5件(functional.md / logging.md / contracts/cli-container.md / system.md / relations.md)は
     直前の task-fix-logout-zero-target-path で版が動いたので、その反映後の内容で読み直した。 -->

## 決定シート(回答済み)

> 回答待ち: `docs/tasks/task-fix-logout-records-and-marker/sheet.md`

| # | 論点 | 回答 | 反映先 |
|---|---|---|---|
| - | (未回答) | - | - |

## 未決点

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| 1 | 概念1〜4・論点1 | 決定シート(`sheet.md`)へ載せた。回答待ち | /task-new §3 |

## 調査メモ

| # | 調べたこと | 判明した事実 | 出どころ |
|---|---|---|---|
| 1 | `docs/issues/099` の起点層は 03 か 01 か | **01 である。** `FR-env-03-19` は EARS の条件節に「削除対象が0件(**管理ラベルを持つコンテナ(停止中を含む)が無く**…)」と**世界の状態**を書いており、その状態が**不明**なときに何をするかは何も課していない。共有ボリュームについては 2026-08-11 に「空であることを**確認できた**」+「確認できなかったならこの経路に入ってはならない」を加えて義務を明示したが、**コンテナの集合には同じ手当てが無い**。したがって不明時の禁止を課すのは要件の追加であり 03 では閉じない | `docs/01-requirements/functional.md:121`(`FR-env-03-19`)/ 直前タスクの決定シート 論点2 で人間が同型の判断を「01 を先に直す(案B)」と裁定した(`docs/histories/2026-08-11-fix-logout-zero-target-path.md`) |
| 2 | 手順4 の列挙が失敗を捨てている実体 | `done < <(docker ps -a --filter "label=claude-dev.managed=1" --format '{{.Names}}' 2>/dev/null \|\| true)` — `\|\| true` と `2>/dev/null` で成否を捨てるため、失敗と0件が同じ空集合になる | `claude-dev:963`〜`:968` / `claude-dev-mac` の同一箇所 |
| 3 | `reset` に同型の二重記録があるか | **無い。** `reset` は列挙の失敗を `destructive_plan` + `destructive_failed` の2回だけ記録し、`destructive_deleted` には入れない。共有ボリュームは `docker volume rm -f` で器ごと消すので、logout の「消去を確認できず失敗に数えたのに `_auth_left` が空だから削除済みにも入る」形が存在しない。**したがって `MODULE-cli-common-destructive` に番人を置く必要は無く、呼び出し側で直せる** | `claude-dev:2109`(`_rc_spawned_query_failed` の記録)/ `claude-dev:1149`〜`:1164`(logout の二重記録)/ `claude-dev:650`〜`:653`(3つの記録関数は素の追記) |
| 4 | 手順11 の失敗経路がラベル無しコンテナの表示を出すか | **出さない。** `if [ ${#_DESTRUCTIVE_FAILED[@]} -gt 0 ]; then … exit 1; fi` が `printf '%s' "$_unmanaged_notice"` より前にあるため、削除に失敗した実行では受入基準17 が無条件に課す表示が出ない(この形は本変更以前から在る) | `claude-dev:1169`〜`:1176` |
| 5 | 行番号引用のずれ | closure 外の 03-impl 9件が旧 1119 行目以降を指しており `+58` で古くなっている(`docs/pendings.md` の残務)。**本タスクでコード行が再びずれる**ので、このタスクで付け替えても次のずれが乗る。一括の掃除タスクに委ねるのが安い | `docs/pendings.md` 残務(2026-08-11 の行) |
| 6 | 印の衝突の再現 | `printf '%s\n' "__CLAUDE_DEV_AUTH_LISTED__" "__CLAUDE_DEV_AUTH_LISTED__" \| grep -vxF '__CLAUDE_DEV_AUTH_LISTED__'` が空を返す = 印と同名の行は中身として数えられない。手順6(`:1050`〜`:1051`)と手順10(`:1154`〜`:1155`)の両方が同じ形 | 2026-08-11 に実測 |
| 7 | 充足の前提(★ の確認) | closure が乗る条項 `FR-env-03-5` / `-14` / `-17` / `-18` / `-19` はいずれも充足 `完全`。**部分充足の条項に依存していない** | `docs/02-design/system.md:212`, `:221`, `:224`〜`:226` |
| 8 | closure の検証済み記録 | closure の全 SSOT ドキュメントの `verified.version` が自身の MAJOR.MINOR と一致(原則6 を満たす)。`against` も 2026-08-11 に発行し直した直後なので再検証候補は無い | 各ファイルの frontmatter |
| 9 | 走らせるべきテスト(DoD の種) | `relations-query.py --requirement FR-env-03` = 「検証しているテスト 0 件 / この要件は未検証(テスト未実装)」。`MODULE-cli-logout` の `tests:` も「なし」。DoD の検証は **E2E-01 手順8 の実機確認**が担う(前タスクと同じ) | `relations-query.py --requirement FR-env-03` の出力 |
| 10 | 仕様ドキュメントの一括検査(母集団) | `python3 .claude/scripts/check-changeset.py --ssot docs` = **NG 違反 75 件**(CS8 曖昧語 11 / CS11 参照実在 16 / CS19 理由の網羅 19 / CS20 issue の起点層 29 / CS12・CS18 は OK)。既起票の母集団: CS8 の「本変更」は `docs/issues/056`、CS11 は `docs/issues/054`、判断行の書式は `docs/pendings.md` の残務が追跡している | `check-changeset.py --ssot docs` の 2026-08-11 実行 |
| 11 | `MODULE-cli-logout` 判断15 の `[DS-05]` の見直す条件 | 「3箇所目でこの判定が必要になったとき」。`docs/issues/100` の修正は**手順6 と手順10 の2箇所のまま**なので、この条件は発生しない(起票時の文面が「直すときにその条件が発生する」と過大に書いていたため 2026-08-11 に訂正した) | `docs/03-impl/relations/MODULE-cli-logout.md` 判断15 |
| 12 | 上流の下流影響 | `relations-query.py --upstream MODULE-cli-logout` = **0 件**(誰も呼んでいない入口)。`--upstream MODULE-cli-common-destructive` = `MODULE-cli-logout` と `MODULE-cli-reset` の2件 — 共有基盤を触ると `reset` に波及するので、調査メモ 3 のとおり触らない | `relations-query.py` の出力 |

## 質問キュー(未提示)

| # | 論点 | 何が止まるか | 推奨する回答(暫定) |
|---|---|---|---|
| - | なし(すべて sheet.md へ載せた) | - | - |

## タスクリスト

(フェーズ2・3で埋める)

## Definition of Done

(フェーズ3で埋める)

## 進捗メモ

- 2026-08-11 フェーズ1: `docs/issues/098` / `099` / `100` の3件を1つのタスクへ昇格した
  (いずれも `claude-dev` の `logout` 分岐の同じ 20 行に在り、`100` の修正は手順6 と手順10 の
  両方に及ぶため、別々のタスクにすると同じ closure を3回開くことになる)。
  **`docs/issues/099` の `origin_layer` を 03 → 01 へ改めた**(調査メモ 1)。
  00〜02 を全文読了(lane: critical)。`check-lane.py` の判定は下の記録のとおり。
  決定シート(概念4件・論点1件)を `sheet.md` に置いた。

## 申し送り事項

- **`docs/issues/055`(受入基準17 が停止中のラベル無しコンテナの列挙まで求める / 01 ⇄ 02 の
  食い違い)は範囲外で残る。** 本タスクは受入基準17 の条件節を触らない(論点1 が「畳む」に
  なった場合でも、触るのは表示する**位置**であって条件節ではない)。
- 本タスクの実装でコード行が再びずれるため、`docs/pendings.md` の「行番号引用のずれ(+58)」の
  残務は**数値が変わる**。closure 外の9件を掃除するタスクは本タスクの後に行うこと。
- 並行タスクは無い(このタスクの作成時点で `docs/tasks/` は空だった)。
