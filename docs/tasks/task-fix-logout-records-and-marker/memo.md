---
id: task-fix-logout-records-and-marker
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

> 回答済み: sheet.md(転記済み)

- チャット回答(2026-08-11)「すべて推奨通り。進めて」 — 対象: 一括 — 反映先: 概念1〜4 と論点1 の
  全ブロック(各ブロックの「AI推奨」がそのまま確定。下表の反映先を参照)

<!-- 人間はシートのファイルには記入せず、チャットで一括回答した。task-memo.md §1.2 の
     第3の返答形(逐語引用+日付の転記)で確定とする。sheet.md の「★あなたの記入」は空のまま
     (AI は書き込まない)。「一括回答」が全ブロックを覆うので、空欄のブロックは
     「推奨を承認」として扱う。 -->

| # | 論点 | 回答 | 反映先 |
|---|---|---|---|
| 概念1 | 0件条件のコンテナの集合にも「無いことを確認できた」を課すか | 推奨を承認(一括回答)= **課す**。`docker ps` が成功して0行だった場合だけ0件に数え、引けなかった場合は数えない | `FR-env-03-19` / `new-features/01-requirements/functional.md` |
| 概念2 | 引けなかったときに観測される振る舞い | 推奨を承認(一括回答)= **(i)** 0件の経路に入らず、引けなかったことを表示して受入基準14 の確認へ進み、**引けなかったこと自体を「消えなかった資源」として記録して終了コード 1**(`reset` の `claude-dev:2109` と同じ倒し方)。**終了コードが 0 → 1 に変わることを含めて承認された** | `FR-env-03-19` / `new-features/01-requirements/functional.md` + `new-features/02-design/contracts/cli-container.md`(エラーケース新設)+ `new-features/02-design/logging.md` |
| 概念3 | 「削除した資源」の外延 | 推奨を承認(一括回答)= **消えたことを確認できた資源だけ**を挙げる。**同じ資源を「削除した」と「削除できなかった」の両方に出してはならない**と明文化する | `new-features/02-design/logging.md`(共通制約)+ `new-features/03-impl/contracts/cli-container.md`(記録の行) |
| 概念4 | 「印以外の行」の外延 | 推奨を承認(一括回答)= **印を出した1行より後ろの行**(位置で判定)。`grep -vxF` による文字列一致での除去をやめる。**手順6 と手順10 の両方**を直す | `new-features/03-impl/relations/MODULE-cli-logout.md` 手順6・手順10 + `new-features/03-impl/contracts/cli-container.md` |
| 論点1 | 削除に失敗した実行でラベル無しコンテナの警告を出すか(4件目の欠陥) | 推奨を承認(一括回答)= **A(このタスクに畳む)**。closure は増えない(`MODULE-cli-logout` 手順11 と実装2箇所) | `new-features/03-impl/relations/MODULE-cli-logout.md` 手順11 |
| 方針合意 | 各ドキュメントへの変更方針7行 | 一括回答に含まれる(異議なし)= 全方針に合意 | シートの「方針合意」節がそのままフェーズ2の作業方針 |

## 未決点

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| 1 | 概念1〜4・論点1 | 2026-08-11 に人間がチャットで一括回答(「すべて推奨通り。進めて」)。全件 AI 推奨のとおりで確定 | /task-new §3 |
| 2 | `while ... done < <(cmd)` はプロセス置換の終了ステータスを取れないので、手順4 の成否をどう捕まえるか | **委任決定(DS-05)**: 既存の `spawned_resources` / `net_other_running_containers` の呼び出しと同じ `if _q=$(cmd); then … else … fi` の形にする(同じ分岐の中に既に3例ある) | フェーズ2 実装ドライラン パス1 |
| 3 | 引けなかったことを何という名前で「消えなかった資源」に記録するか | **委任決定(DS-03)**: `reset` の「セッション由来のコンテナの列挙(Docker への問い合わせに失敗)」に揃えて「削除対象の Claude コンテナの列挙(Docker への問い合わせに失敗)」にする。`MODULE-cli-logout` 判断21 へ記載 | フェーズ2 実装ドライラン パス1 |
| 4 | 集合を引けなかったとき、手順7 の確認プロンプトに何を出すか(受入基準14 は「何が消えるかを消える前に見る唯一の機会」と定める) | **委任決定(DS-03)**: 一覧を引けなかった旨と、引けていないコンテナは削除されないことを1行出す。判断21 へ記載 | フェーズ2 実装ドライラン パス1 |
| 5 | 「印の行より後ろ」をどう実装するか(印と同名の行があっても壊れない形) | **委任決定(DS-05)**: 印は標準出力の**1行目**に現れるので、(i) は「1行目が印と一致」・(iii) は「2行目以降が空」で判定する。`head -1` / `tail -n +2` 相当で足り、内容の照合を使わない。判断19 へ記載(調査メモ 13 で実測) | フェーズ2 実装ドライラン パス1 |
| 6 | 手順10 で印が無いときに「削除した資源」へ落ちないようにする形 | **委任決定(DS-05)**: `_auth_left=""` を成功の合図に流用するのをやめ、確認できたかどうかの旗を別に持つ。判断20 へ記載 | フェーズ2 実装ドライラン パス1 |
| 7 | 失敗経路のラベル無しコンテナの表示をどの宛先・どの位置に出すか | **委任決定(DS-03)**: 標準出力へ、失敗の列挙(stderr)の後ろ・`exit 1` の直前。文言は成功経路と同じ組み立て済みの文字列を使う。判断22 へ記載 | フェーズ2 実装ドライラン パス1 |

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

| 13 | 位置で判定する形の実測(パス2) | `out=$(...) && st=0 \|\| st=$?` で status を取り、`head -1` が印と一致するか・`tail -n +2` が空かで判定すると、**空 / 中身あり / 印と同名のファイルが中身 / 起動できない / 印は出るが列挙が非0** の5状態すべてを正しく分けられた。実イメージ `claude-dev-claude` で `docker run --entrypoint bash … -c 'echo 印; ls -A /auth'` の標準出力は**1行目が印**である(`docker` の警告は標準エラーへ出るため混ざらない) | 2026-08-11 に実測 |
| 14 | 手順4 の成否を捕まえる既存の形 | 同じ `logout` 分岐の中に `if _q=$(spawned_resources container …); then … else … fi` と `if _others=$(net_other_running_containers); then … else … fi` の2例があり、`reset` にも同型が在る。**新しい流儀を持ち込む必要が無い** | `claude-dev:972`〜`:978`, `:987`〜`:997` / `claude-dev:1977`〜`:1981` |
| 15 | `reset` の失敗の表示名 | `destructive_plan "$_t"; destructive_failed "$_t"` に渡す `$_t` は「セッション由来のコンテナの列挙(Docker への問い合わせに失敗)」。**`logout` の表示名はこれに揃える** | `claude-dev:1980`, `:2109` |

## 質問キュー(未提示)

| # | 論点 | 何が止まるか | 推奨する回答(暫定) |
|---|---|---|---|
| - | なし(すべて sheet.md へ載せた) | - | - |

## タスクリスト

<!-- フェーズ2 の草案。/implement が確定させる -->

- [ ] 1. **手順4 の問い合わせの成否を捕まえる**(`if _q=$(docker ps …); then … else _targets_query_ok=0 fi` の形へ)。引けなかったら0件判定に入らないようにし、確認プロンプトと手順11 に出す _要件:_ FR-env-03-19・18 _Boundary:_ `claude-dev:963`〜`:968` / `claude-dev-mac` の同一箇所 _Depends:_ -
- [ ] 2. **手順6・手順10 の判定を位置ベースへ**(1行目が印 / 2行目以降が中身)。`grep -vxF` をやめる _要件:_ FR-env-03-19 _Boundary:_ `claude-dev:1044`〜`:1056` と `:1145`〜`:1164` _Depends:_ - (P)
- [ ] 3. **手順10 で消去を確認できなかった資源を「削除した資源」に記録しない**(確認できたかの旗を別に持つ) _要件:_ FR-env-03-18 _Boundary:_ `claude-dev:1149`〜`:1164` _Depends:_ 2
- [ ] 4. **失敗経路でもラベル無しコンテナの表示を出す**(stdout、失敗の列挙の後ろ・`exit 1` の直前) _要件:_ FR-env-03-17 _Boundary:_ `claude-dev:1169`〜`:1176` _Depends:_ - (P)
- [ ] 5. **E2E-01 手順8-10 の追加分 / 手順8-18 の (c) / 手順8-19 を実機で流す**(macOS 側も。実行できない場合は未実施を記録する) _要件:_ FR-env-03-17・18・19 _Boundary:_ `docs/03-impl/tests/e2e.md` の手順 _Depends:_ 1,2,3,4

## Definition of Done

(フェーズ3で埋める)

## 進捗メモ

- 2026-08-11 フェーズ1: `docs/issues/098` / `099` / `100` の3件を1つのタスクへ昇格した
  (いずれも `claude-dev` の `logout` 分岐の同じ 20 行に在り、`100` の修正は手順6 と手順10 の
  両方に及ぶため、別々のタスクにすると同じ closure を3回開くことになる)。
  **`docs/issues/099` の `origin_layer` を 03 → 01 へ改めた**(調査メモ 1)。
  00〜02 を全文読了(lane: critical)。`check-lane.py` の判定は下の記録のとおり。
  決定シート(概念4件・論点1件)を `sheet.md` に置いた。
- 2026-08-11 フェーズ1 完了: 人間がチャットで一括回答(逐語「すべて推奨通り。進めて」)。
  **確定した方針 = 概念1 課す / 概念2 (i) 進めて失敗に数えて 1 / 概念3 消えたことを確認できた
  資源だけ + 両方の一覧に出さない / 概念4 印の行より後ろ(位置で判定) / 論点1 A(4件目を畳む)**。
  **論点1 が A で確定したので、失敗経路のラベル無しコンテナの表示もこのタスクで直す**
  (closure の行は増えない — `MODULE-cli-logout` 手順11 と実装2箇所)。
  `check-sheet.py` 合格(SH4 はチャット回答の転記行で通る / 読了記録とも OK)。
  `phase: ドキュメント` へ進め `/task-doc` を実行する。

- 2026-08-11 フェーズ2 下降: **00 完了**(変更なし — `D0-env-08` 項5「削除の失敗を握りつぶさない」と
  `D0-scope-07` の観測点の定義が3件すべての根拠を既に持ち、条件節を動かす必要が無いことを確認した)。
  **01 完了**(`functional.md` の `FR-env-03` 節。受入基準19 の1行だけを書き換え、条項 ID は不動)。
  次は 02。
- 2026-08-11 フェーズ2 下降: **02 完了**(`contracts/cli-container.md` のエラーケース1行新設 /
  `logging.md` の新設1行 + 共通制約への3点の書き足し)。**03 完了**(`MODULE-cli-logout` /
  `contracts/cli-container.md` / `tests/cli-logout.md` / `tests/e2e.md` の4本)。
  変更指示は 7 ファイル。
- 2026-08-11 フェーズ2 実装ドライラン: パス1 で未決点6件(上表 2〜7)。**どれも問う基準を満たさない**
  (観測される振る舞いは受入基準17・18・19 と決定シートの回答が既に固定しており、残るのは実現方法)
  ので決めて開示した。行使した委任: **[DS-03]**(失敗の表示名 / 確認プロンプトの1行 / 失敗経路の
  表示の宛先と位置)/ **[DS-05]**(成否の捕まえ方 / 位置ベースの判定 / 記録の旗)。
  開示先は `MODULE-cli-logout` の「実装上の判断」19〜22 と `tests/*.md` の「テスト設計の判断」。
  パス2 の事実は調査メモ 13〜15 に記録した。`check-changeset.py` **合格(違反なし)**。

- 2026-08-11 **/doc-check(task) 判定: PASS**。実行形態: 作成者セッション(サブエージェント不可のため
  §0A のフォールバック)。**独立レビュー: Codex**(`gpt-5.6-sol` / reasoning high、指摘 5 件)。
  レンズは作業ツリーへ書き込んでいない(前後の `git status` の差分は私が生成した staged callgraph のみ)。
  反復 1/2 で収束。
  **レンズ指摘の裁定**:
  - **高1(A3)**: 手順10 が列挙の終了ステータスを見ないので、印の直後に `ls` が失敗すると
    「消去に成功して空になった」と読み替える → **確認済み。実測で裏付けた**: 一時コンテナに渡す
    コマンドは `rm -rf …; echo 印; ls -A /auth` の順で、**最後が列挙なのでコンテナの終了ステータスは
    `ls` の状態**である(`rm` の非0は混ざらない)。02 契約は既に「列挙そのものができなかった場合も
    『消去を確認できなかった』として同じ扱いにする」と課しており、**03 がそれを受けていなかった**。
    手順10 を手順6 と同じ3条件へ揃え、判断4 を更新した(**MINOR**)。
  - **高2(A3)**: `tests/cli-logout.md` が受入基準17・18 の確認先を手順8-18 の (b) に割り当てて
    いたが、(b) は `--yes` 側を持たず削除まで到達しない → **確認済み**。指し先を
    受入基準18 = 手順8-18 の (a)(b) の `--yes` 側 / 受入基準17 = 手順8-10 の後半 へ付け替え(**PATCH**)、
    (a) に「削除した資源に現れないこと」を、(b) に `--yes` 側を新設(**MINOR**)。
  - **中1(C8)**: `FR-env-03-19` が1条項で4義務 → **裁定: 修正しない**。条項を分けると 02 カバレッジ表と
    03 テスト表の行追加を伴い、人間が承認した方針(「条項 ID は動かさない」)を超える。
    `docs/pendings.md` の残務へ1行として起票済み(2026-08-11)。
  - **低2件**: E2E-01 手順8-3 の「すぐに」= 前タスクで既に残務へ起票済み(範囲外の既存記述)。
    `reason` の「判断3行」が実体4行 → 実体へ修正(**PATCH**)。
  **変更指示の合計バイト: 167,322 → 170,802(+3,480)**。増加は (a) 手順10 の3条件と判断4 の更新、
  (b) E2E の `--yes` 側2つの新設による。**削除では直せない**(受けていない義務を受ける記述である)。
  行使した委任: [DS-03] / [DS-05]。
  変更指示のハッシュ(sha256 先頭12桁):
    - 01-requirements/functional.md 665b5acdaeb5
    - 02-design/contracts/cli-container.md 9ec279e966cf
    - 02-design/logging.md 78150c05f440
    - 03-impl/contracts/cli-container.md b052bff3f914
    - 03-impl/relations/MODULE-cli-logout.md d57361cca2c3
    - 03-impl/tests/cli-logout.md fd36edf23155
    - 03-impl/tests/e2e.md ea6be7e7f971
  closure の版: functional.md@1.14.0 / contracts/cli-container.md@1.9.0 / logging.md@1.6.0 /
  03-impl/index.md@1.23.0 / 03-impl/contracts/cli-container.md@1.8.0 / tests/cli-logout.md@1.6.1 /
  tests/e2e.md@1.8.0
  機械検査: `check-changeset.py` 合格 / `build-callgraphs --check` 最新 /
  `cluster-features --check` 最新 / `callgraph-check --to-be` 高0 / `check-relations` 合格 /
  `check-contracts` 合格。
  **最弱点**: 手順6 と手順10 が同じ3条件の判定を**それぞれ持つ**こと(判断15 の [DS-05] が
  「3箇所目まで関数に切り出さない」と定めているため)。今回2箇所を同時に直したので食い違いは無いが、
  **次にどちらか片方だけを触るタスクが出たときに、もう片方が取り残される形は残っている**。
- 2026-08-11 staged callgraph(`new-features/03-impl/callgraphs/` と `feature-graph.md`)を生成した。
  進行中タスクがある間は SSOT の代わりにこれが合成ビューの根拠になる(`change-set.md` §1)。
  **中身は変更前のコードの鏡**であり、`/implement` C-1 が実装後に再生成する。

- 2026-08-11 フェーズ3 開始。**ゲート3条件を通過**: (1) closure 全 SSOT(7件)の `verified.version` が
  自身の MAJOR.MINOR と一致。(2) 未決点7件すべて帰着済み(回答 / 委任決定)。(3) `environments.md` の
  lint = `go vet ./...` / 単体 = `cd docker-proxy && go test ./...` が「未定」でないことを確認し、
  着手前の回帰確認として両方を実行して exit 0
  (`ok github.com/quvox/claude-dev-env/docker-proxy`)。フェーズ2 の草案タスクリストをそのまま使う。
  **タスク2 には /doc-check で足りた「手順10 の終了ステータス条件」も含める**(同じ 20 行の中で、
  位置ベースの判定と同時に入れる)。

## 申し送り事項

- **`docs/issues/055`(受入基準17 が停止中のラベル無しコンテナの列挙まで求める / 01 ⇄ 02 の
  食い違い)は範囲外で残る。** 本タスクは受入基準17 の条件節を触らない(論点1 が「畳む」に
  なった場合でも、触るのは表示する**位置**であって条件節ではない)。
- 本タスクの実装でコード行が再びずれるため、`docs/pendings.md` の「行番号引用のずれ(+58)」の
  残務は**数値が変わる**。closure 外の9件を掃除するタスクは本タスクの後に行うこと。
- 並行タスクは無い(このタスクの作成時点で `docs/tasks/` は空だった)。
