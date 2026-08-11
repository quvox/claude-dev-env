---
id: task-fix-logout-records-and-marker
phase: 反映
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

> 保管: `memo-1.md` = 調査メモ(15件)+ フェーズ1・2 の進捗メモ

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

## 調査メモ(memo-1.md に移動)

## 質問キュー(未提示)

| # | 論点 | 何が止まるか | 推奨する回答(暫定) |
|---|---|---|---|
| - | なし(すべて sheet.md へ載せた) | - | - |

## タスクリスト

<!-- フェーズ2 の草案。/implement が確定させる -->

- [x] 1. **手順4 の問い合わせの成否を捕まえる**(`if _q=$(docker ps …); then … else _targets_query_ok=0 fi` の形へ)。引けなかったら0件判定に入らないようにし、確認プロンプトと手順11 に出す _要件:_ FR-env-03-19・18 _Boundary:_ `claude-dev:963`〜`:968` / `claude-dev-mac` の同一箇所 _Depends:_ -
- [x] 2. **手順6・手順10 の判定を位置ベースへ**(1行目が印 / 2行目以降が中身)。`grep -vxF` をやめる _要件:_ FR-env-03-19 _Boundary:_ `claude-dev:1044`〜`:1056` と `:1145`〜`:1164` _Depends:_ - (P)
- [x] 3. **手順10 で消去を確認できなかった資源を「削除した資源」に記録しない**(確認できたかの旗を別に持つ) _要件:_ FR-env-03-18 _Boundary:_ `claude-dev:1149`〜`:1164` _Depends:_ 2
- [x] 4. **失敗経路でもラベル無しコンテナの表示を出す**(stdout、失敗の列挙の後ろ・`exit 1` の直前) _要件:_ FR-env-03-17 _Boundary:_ `claude-dev:1169`〜`:1176` _Depends:_ - (P)
- [x] 5. **E2E-01 手順8 の確認**: 隔離ハーネス(実機 Docker。資源名を `cdx2-*` へ書き換えた `claude-dev` の複製)で T1〜T4 と対照2件を修正前後の差分として確認した。**実機の E2E-01 手順8 と macOS 版は流していない** — `sheet.md` 論点4(前タスク)と同じ理由で操作者の認証が消えるため。`docs/pendings.md` の残務(2026-08-11 の実機 E2E 未実施の行)に本タスク分もまとめて残す _要件:_ FR-env-03-17・18・19 _Boundary:_ `docs/03-impl/tests/e2e.md` の手順 _Depends:_ 1,2,3,4

## Definition of Done

(フェーズ3で埋める)

## 進捗メモ

> フェーズ1・2 の進捗メモは memo-1.md に移動した。
- 2026-08-11 フェーズ3 開始。**ゲート3条件を通過**: (1) closure 全 SSOT(7件)の `verified.version` が
  自身の MAJOR.MINOR と一致。(2) 未決点7件すべて帰着済み(回答 / 委任決定)。(3) `environments.md` の
  lint = `go vet ./...` / 単体 = `cd docker-proxy && go test ./...` が「未定」でないことを確認し、
  着手前の回帰確認として両方を実行して exit 0
  (`ok github.com/quvox/claude-dev-env/docker-proxy`)。フェーズ2 の草案タスクリストをそのまま使う。
  **タスク2 には /doc-check で足りた「手順10 の終了ステータス条件」も含める**(同じ 20 行の中で、
  位置ベースの判定と同時に入れる)。

- 2026-08-11 フェーズ3 実装完了(タスク1〜4)。コミット: `fa07a1f`(1) / `4f3b408`(2・3) /
  `5f81da4`(4)。変更は `claude-dev` と `claude-dev-mac` の2本のみ(各 +65/-24 行 = **正味 +44 行**)。
  `logout` 分岐は両 OS で**バイト単位で同一**(`diff` 0差分)。
  **タスク2 と3 を1コミットにした**のは、どちらも同じ `if/elif/else` の再構成で成り立ち、
  分けると中間状態が独立に検証できないため(DS-08 の範囲)。
- 2026-08-11 フェーズ3 で追加した委任決定:
  - **[DS-03]** 消去を確認できなかった共有ボリュームを**予定と同じ名前**で失敗に記録する
    (`（消去を確認できず）` を付けない)— 理由: 記録関数は名前が一致した予定行だけを消すので、
    違う名前だと予定側が `（未着手）` として残り、**同じ資源が結果表示に2行出る**(実測した)/
    見直す条件: `destructive_report` が予定と結果を名前以外で対応づけるようになったとき。
    開示先: `MODULE-cli-logout` 実装上の判断20
- 2026-08-11 **「実装上の判断」「テスト設計の判断」の棚卸し**(`delegation.md` §3.1):
  - `MODULE-cli-logout` 判断1〜22(22件): **判断4 は「更新」**(フェーズ2 で列挙の終了ステータスを
    判定に使う形へ改め、実装もそのとおりにした)。**判断20 は「更新」**(上記 [DS-03] を追記)。
    **残る20件は「継続」** — 見直す条件が起きたものは無い。判断13 の引用は行番号のずれで
    `claude-dev:1145`-`:1163` → **`:1176`-`:1203`** へ取り直した(PATCH)。
  - `tests/cli-logout.md` テスト設計の判断1〜7(7件): **全件「継続」**。判断6・7 はフェーズ2 で
    新設したもので、実機で流していないので前提は動いていない。
  - `tests/e2e.md` の `[DS-01]` 各行: **全件「継続」**。
- 2026-08-11 **C-1**: コールグラフをタスク配下へ再生成し、`callgraph-check.py --to-be` =
  **重大度「高」0 件(終了コード 0)**。`MODULE-cli-logout` の辺は6本で変更指示の `callees` と
  完全一致(**新しい記号は増えていない** — 関数を1つも増やしていない)。
  残る指摘 24 件はすべて中・低・参考で、いずれも `logout` と無関係な既存分。
  引用の行番号を **+44** で取り直した(`03-impl/contracts/cli-container.md` 64箇所 /
  `MODULE-cli-logout` 7箇所。変更範囲より後ろは内容の一致で全件検証し、範囲の内側は
  個別に実体を探して取り直した)。closure 外の9件は `docs/pendings.md` の残務を **+102** へ更新。

- 2026-08-11 **C-0 の検証: 実機 E2E-01 手順8 は未実施**(前タスクと同じ理由 — 手順8 は
  `claude-dev login` から始まり `logout --yes` / `reset --yes` を含むので、操作者の Claude / Codex
  認証と claude-dev のイメージ・ボリュームが実際に消える)。隔離ハーネス(資源名を `cdx2-*` へ
  書き換えた複製 + 検証用イメージ)で実機 Docker に対して確認した。実出力(逐語):

  | # | 状態 | 修正前 | 修正後 |
  |---|---|---|---|
  | T1 (`099`) | `docker ps` が失敗する状態 | 「削除対象がありません」/ **exit 0** | 「削除対象の Claude コンテナの一覧を引けませんでした」→ 消えなかった資源として列挙 / **exit 1** |
  | T2a (`098`) | 一時コンテナを起動できない | (前タスクで確認済み) | 「削除した資源: (なし)」+ 失敗に**1行だけ** / exit 1 |
  | T2b (02 契約) | 印は出るが列挙が非0 | **「✅ 認証情報を削除しました」/ exit 0**(消去を確認できていないのに成功) | 「消去を確認できませんでした」→ 失敗 / exit 1 |
  | T3 (`100`) | `/auth` に印と同名のファイルだけ | 「削除対象がありません」/ **exit 0** | 空と判定せず確認へ進み、非 TTY で exit 1 |
  | T4 (論点1) | 削除が失敗する状態 + ラベル無しコンテナ | 失敗の列挙で終わり、警告が出ない | 失敗の列挙の後にラベル無しコンテナの名前と書き戻しの警告が出る |
  | 対照 | 壊れていない通常経路 | — | 管理コンテナと共有ボリュームを削除して exit 0(回帰なし) |
  | 対照 | 真の0件 | — | 「削除対象がありません」/ exit 0(余分な行なし) |

  **T2b が最も重い**: 修正前は消去を確認できていないのに成功と報告して exit 0 だった
  (独立レビューの高1 が指摘した経路)。隔離資源は実行後に削除済みで、利用者の
  `claude-dev-auth`(21 項目)と `~/.claude-dev/locks/`(0 件)は無傷である。
  **未確認のまま残るのは (a) 実イメージでの手順8-18・8-19、(b) macOS 版、(c) 手順8 の他の部分手順の回帰**。

- 2026-08-11 **範囲外で見つけた欠陥を1件起票**: `docs/issues/101`(`reset` にも同型の
  「削除に失敗した実行でラベル無しコンテナの表示が出ない」欠陥がある。`claude-dev:2260` の
  失敗ブロックが `:2270` の表示より前に `exit 1` する。severity 中 / origin_layer 03)。
  本タスクの「やらないこと」が `reset` の振る舞いの変更を除いているので直していない。
  **`destructive_report` を使う破壊的操作は `logout` と `reset` の2つだけ**で、`logout` は
  修正済みなのでこの形が残るのは1箇所である。

- 2026-08-11 **DoD の実測**(`git rev-parse HEAD` = `5f81da4fd6630cb17b620dbde9f6420b25417931`):

  | DoD 項目 | 結果 | コマンドの最終行(逐語) |
  |---|---|---|
  | lint | ✅ | `go vet ./...` は出力なしで終了コード 0 |
  | 単体・結合テスト | ✅ | `ok  	github.com/quvox/claude-dev-env/docker-proxy	(cached)` |
  | 受入基準のテストが存在し通る | ✅(表の指し先) | `FR-env-03` は自動テストを持たない(`DSN-test-01`)。`tests/cli-logout.md` の該当行が手順8-18 の (a)(b)(c) / 手順8-19 / 手順8-10 を指すことを確認 |
  | 影響する E2E シナリオ(E2E-01) | ❌ **実機未実施** | 隔離ハーネスで T1〜T4 + 対照2件を確認(上表)。理由と残りは上の C-0 の行 |
  | コールグラフ再生成 + `callgraph-check --to-be` 高0 | ✅ | `最新。再生成しても差分は出ない。` / `callgraph-check --to-be` 終了コード 0 |
  | `check-relations.py` | ✅ | `合格: 対称性・参照実在・impl パス・必須項目・機能表との 1:1すべて問題なし。` |
  | `check-changeset.py` | ✅ | `合格: 不変条件の違反なし` |
  | `check-contracts.py` | ✅ | `合格: 契約に不整合なし。` |
  | `new-features/` を SSOT へ反映 | `/task-close` で実施 | — |
  | `/doc-check` が影響範囲を PASS | `/task-close` で実施 | — |
  | `docs/histories/` に記録 | `/task-close` で実施 | — |
  | 範囲外の問題を記録 | ✅ | `docs/issues/101` を新設 / `docs/pendings.md` の行番号ずれを +102 へ更新 |
  | 起点の issue 3件(098 / 099 / 100)を削除 | `/task-close` で実施 | — |

- 2026-08-11 **意図する版の上げ幅は変更指示の `version_bump` のまま**(`/task-close` が上げる)。
  **お伺いする事項なし**(C-2 の決定シートは空。質問キューに問う基準を満たす項目は無い)。

- 2026-08-11 **フェーズ4 §1 の事前検査で、DoD 表の測定時点 `5f81da4` の後にコードが動いていた**
  ことが分かった(C-0 の検証中に入れた「失敗の記録名を予定名に揃える」修正が、次の docs コミット
  `dd89caf` に含まれていた)。**短縮条件は使えないので隔離ハーネスの全件を現在のコードで流し直した**。
  結果は上の C-0 の表と同じで、T2a・T2b の失敗欄が**1行だけ**になっている(記録名を揃えた効果)。
  再実行時のコード = `2497834` の時点のもの。lint と単体テストも再実行して green
  (`ok  	github.com/quvox/claude-dev-env/docker-proxy	(cached)`)。
  **実機 E2E-01 手順8 と macOS 版は今回も未実施**。前タスクの `sheet.md` 論点4 で人間が
  「隔離ハーネスの結果を根拠に進め、実機分は残務へ回す」(案A)と裁定しており、
  **状況・証拠の種類・破壊の対象がまったく同じ**なので、`delegation.md` §1 の「過去の回答が
  settles する項目はシートに載せない」に従い新しい問いは立てない。`docs/pendings.md` の
  実機 E2E 未実施の残務へ本タスク分も併記する。

## 申し送り事項

- **`docs/issues/055`(受入基準17 が停止中のラベル無しコンテナの列挙まで求める / 01 ⇄ 02 の
  食い違い)は範囲外で残る。** 本タスクは受入基準17 の条件節を触らない(論点1 が「畳む」に
  なった場合でも、触るのは表示する**位置**であって条件節ではない)。
- 本タスクの実装でコード行が再びずれるため、`docs/pendings.md` の「行番号引用のずれ(+58)」の
  残務は**数値が変わる**。closure 外の9件を掃除するタスクは本タスクの後に行うこと。
- 並行タスクは無い(このタスクの作成時点で `docs/tasks/` は空だった)。
