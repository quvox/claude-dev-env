---
slug: fix-make-status-hides-docker-query-failure
state: verified
critical: false
origin: derived
issue: docs/issues/109-bug-make-status-treats-a-failed-docker-query-as-zero-sessions.md
started: 2026-08-20T12:58:59+09:00
updated: 2026-08-20T05:43:36+00:00
commit: 16d3b40
summary: make status が docker への問い合わせの失敗を0件と同一視する欠陥を直し、claude-dev list と同じ警告行を出す
---

# fix-make-status-hides-docker-query-failure — `make status` が問い合わせの失敗を隠すのを直す

## 目的・やらないこと

- 目的: `make status` が `docker ps` の非ゼロを `awk` の終了状態で消し、失敗を「0件」と
  同一視して `(実行中のセッションはありません)` だけを出す(`docs/issues/109`)。
  `CTR-cli-container`「稼働中セッションの一覧の列挙」が禁じる読み違えであり、
  `claude-dev list` が既に持つ警告行(`claude-dev:2209`-`:2211`)と同じ形へ揃える。
- やらないこと:
  - **02 の契約の変更**。契約は現状で正しく、実装だけが従っていない(閲覧のみ)。
  - **`make clean` の同型の箇所**(`Makefile:286`-`:289`)。契約が表示側にだけ警告行を求めて
    おり、削除側の振る舞いは 02 が定めていないため、この closure では裁定できない
    (残務へ1行出す)。
  - **固定名 `claude-dev-docker-proxy` を列挙から除く条件**(`docs/pendings.md` の
    2026-08-20 の残務が持つ。`claude-dev list` と `make status` の両方に無く、
    片方だけ直すと食い違いが増える)。
  - **`externals/arm64/colabtmux` の差し替え**(別件として起票のみ。人間が版上げ作業は
    不要と述べている)。

## 影響範囲(closure)

- Makefile
- docs/03-impl/relations/MODULE-makefile-status.md
- docs/03-impl/tests/e2e.md
- docs/03-impl/tests/makefile.md
- docs/03-impl/index.md

## 主張

- 触ったモジュールのテスト: **MOD-makefile に自動テストは無い**(`docs/03-impl/tests/makefile.md`
  の16行がすべて `未検証(テスト未実装)`。方針は `DSN-test-01` / `SR-32`)。実機で追加した
  実機確認手順10-5 を実行して観測した:
  `DOCKER_HOST=tcp://127.0.0.1:1 make status` → `⚠️  Docker への問い合わせが失敗したため、この一覧は不完全である可能性があります。`
  同じ環境変数を付けた `./claude-dev list` → `⚠️  Docker への問い合わせが失敗したため、この一覧は不完全である可能性があります。`(1行1バイト同じ)。
  `DOCKER_HOST=tcp://127.0.0.1:1 make status >/dev/null 2>&1; echo $?` → `0`。
  退行の確認として `make status`(通常)→ `  (実行中のセッションはありません)`(警告行は出ない)
- lint / build: green。`make -n status` → 終了コード `0`(構文解析)。
  `cd docker-proxy && go vet ./...` → 出力なし・終了コード `0`
  (**Bash / Makefile には自動 lint を設けていない** — `docs/02-design/environments.md:54` /
  `SR-32`)。`python3 .claude/scripts/check-ssot.py docs` → `NG 違反 7 件`
  (**着手時に凍結した母集団と同数・同内容**。CS11 の3件と CS20 の4件はいずれも closure の外)
- 外部挙動の変化: **あり** — `make status` で、Docker への2回の問い合わせのどちらかが非ゼロで
  終わったときに警告行が1本増える(それ以外の出力は1バイトも変わらない)。終了コードは 0 のまま
- 認証・決済・不可逆への接触: なし(closure は Makefile の表示ターゲットと 03 の文書だけで、
  読み取りのみである — `MODULE-makefile-status.md` の「永続化: なし(読み取りのみ)」)
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 収束契約)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | closure はアカウント・権限・認証情報を作る/変える/消す機能を1つも含まない(`make status` は表示のみ) | - |
| BR-02 | 非該当 | `make status` は引数を取らず、利用者・外部から値を受け取らない(`MODULE-makefile-status.md` の引数表が「(なし)」) | - |
| BR-03 | 非該当 | 利用者が値を決める識別子を扱わない(表示するコンテナ名は Docker が持つ既存の値である) | - |
| BR-04 | **該当** | `docker ps` はプロセスの外にある外部サービスであり、closure はその応答と終了状態を読む。**本タスクの修繕そのものがこの項目である**(応答の失敗を握りつぶさず、分類された失敗として扱う) | `docs/02-design/contracts/cli-container.md`「稼働中セッションの一覧の列挙」の「問い合わせが失敗したときは 0 件と同一視しない」(既存。02 は変更しない)+ `docs/03-impl/relations/MODULE-makefile-status.md` の異常系 + `Makefile` の `status:` |
| BR-05 | 非該当 | 破壊的操作も不可逆な操作も起こさない(読み取りのみ。`make clean` はこの closure の外である) | - |
| BR-06 | 非該当 | 推測されると困る値を1つも作らない | - |

## 決定シート(回答済み)

- 問いなし(開示のみ)

## 調査メモ

- `Makefile:256`-`:258`: `ids=$(...| awk ...)` の代入がパイプ末尾の `awk` の終了状態を取るため
  `docker ps` の非ゼロが消える。`Makefile:263` の `(実行中のセッションはありません)` に落ちる。
- `claude-dev:2206`-`:2211`: 同じ問題を `_q_failed` の2代入(`|| _q_failed=1`)と警告行1本で
  解決済み。文言は `⚠️  Docker への問い合わせが失敗したため、この一覧は不完全である可能性があります。`
- `docs/02-design/contracts/cli-container.md:561` の節末: 「**問い合わせが失敗したときは 0 件と
  同一視しない**(「エラーケース」)。表示側は一覧が不完全である可能性を表示する」。
  → 契約は正しく、実装だけが従っていない(原則2 の事実の乖離ではなく、契約違反である)。
- `Makefile:286`-`:289`(`clean`)は同じ畳み方をしており、失敗時は削除対象0件として静かに
  `✅ 全リセット完了` を出す。契約は削除側の表示を定めていないため、この closure では裁定しない。
- `docs/03-impl/tests/makefile.md:50` / `:43` と `MODULE-makefile-status.md:12` /
  `MODULE-makefile-clean.md:12` が `手順10-3` / `手順10-4` を外から参照している
  → 既存の手順番号は動かせない(`e2e.md` のテスト設計の判断が同じ理由を既に書いている)。
- `check-ssot.py docs`(母集団の凍結。2026-08-20 12:56): `NG 違反 7 件`(origin_layer 欠落2件 /
  同型欠陥1件 / 変更相対語の候補7件は違反に数えない)。**いずれも本 closure の外**である。

## 進捗メモ(再開点)

- 2026-08-20 12:58 構築記録を作成。closure を確定(オーダー指定の5パス。`docs/issues/109` 自身は
  00〜03 でもコードでもないため closure に列挙せず `issue:` が持つ)。critical: false。
- 2026-08-20 13:05 決定シートを作成し `check-sheet.py` を通した(SH4 免除 = 「曖昧さなし」1件・
  論点0件・委任0件)。**問いなし(開示のみ)**と判定してシートを削除した。
- 2026-08-20 13:12 [DS-02] 問い合わせが非ゼロなら一覧より前に警告を1行出し、処理は続けて
  引けた分を表示する(終了コードは 0 のまま) — 理由: 契約が0件と同一視することを禁じ、
  `claude-dev list` が同じ形を既に採っている。引けた分を隠すと片方だけ通る状況で情報が減る /
  見直す条件: `make status` の終了コードを別の処理が合否として読むようになったとき
  (記録先: `docs/03-impl/relations/MODULE-makefile-status.md` の実装上の判断)
- 2026-08-20 13:15 [DS-01] 実機確認を手順10 の末尾に部分手順10-5 として足し、既存の番号を
  1つも動かさない。`claude-dev list` と対にして観測する — 理由: 外部の表が `手順10-3` /
  `手順10-4` を参照しており番号を詰めると別の手順を指す。片方だけ見ると「同じホストで違う答え」
  を検出できない / 見直す条件: 手順番号を参照する外部の表が無くなったとき
  (記録先: `docs/03-impl/tests/e2e.md` のテスト設計の判断)
- 2026-08-20 13:20 03 の文書を書いた(`MODULE-makefile-status.md` の処理の流れ・異常系・
  実装上の判断 / `tests/e2e.md` 手順10-5 と判断2行 / `tests/makefile.md` の識別子 /
  `index.md` の版と集計)。既存の判断3行は 継続 と読み直した。
- 2026-08-20 13:30 `Makefile` の `status:` を実装。実機で通常時と応答しない `DOCKER_HOST` の
  両方を観測した(主張の節に逐語)。
- 2026-08-20 13:35 [DS-08] コミットを2本に分けた(起票 → 修繕の順) — 理由: 別のオーダーが
  まとめた2件は構築単位が別で、`index.md` の集計文が issue 110 に言及するため起票を先に置く
  必要があった / 見直す条件: 1オーダーが1構築単位だけを持つようになったとき
- 2026-08-20 13:40 追加した参照が削除予定の `docs/issues/109` を指していたので、3箇所
  (`Makefile` の註釈 / `tests/e2e.md` の2箇所)をすべて履歴のパスへ書き換えた
  (削除済み issue を指す参照を新たに作らないため)。
- 2026-08-20 13:45 issue 110 を起票(severity 高。同型走査は `find externals -type f` の3件)。
  `make clean` の同型を残務へ1行(42行 / 上限50)。履歴を作成し issue 109 を削除した。

## override(人間の明示)

- なし(override 不使用。`check-debt.py --repair` の修繕例外で通過)

## 申し送り

- **`docs/histories/index.md` は再生成していない**(履歴数の表示が 62 のまま、実ファイルは 64。
  本タスクの前から2件ずれている)。この索引を書くのは `doc-health.py` であり、
  それを走らせるのは F2 文書整合フロー(`--sweep` つき)だけなので、ここでは触っていない。
  次の `/verify-docs` が拾う。
- `docs/issues/110` は**起票だけで修繕していない**。案A(差し替え)/ 案B(削除)/ 案C(設置時の
  検査)のどれを採るかは人間の裁定を待つ(同梱物の差し替えは不要と述べられている)。
