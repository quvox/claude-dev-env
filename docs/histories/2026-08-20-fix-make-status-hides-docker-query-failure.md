---
id: 2026-08-20-fix-make-status-hides-docker-query-failure
date: 2026-08-20
record: docs/build-records/fix-make-status-hides-docker-query-failure.md
critical: false
origin_layer: 03
issue: docs/issues/109-bug-make-status-treats-a-failed-docker-query-as-zero-sessions.md
summary: make status が docker への問い合わせの失敗を0件と同一視する欠陥を直し、あわせて同梱物 externals/arm64/colabtmux が darwin ビルドである事実を起票した
---

# 2026-08-20 `make status` の問い合わせ失敗を0件と同一視しない

## 変更理由

### R-01 `make status` が Docker への問い合わせの失敗を隠していた

- 起点層・根拠: `docs/02-design/contracts/cli-container.md`「稼働中セッションの一覧の列挙
  (`list` / `make status`)」が「**問い合わせが失敗したときは 0 件と同一視しない**。表示側は
  一覧が不完全である可能性を表示する」と定めており、`claude-dev list` は実装済み
  (`claude-dev:2206`-`:2211`)、`make status` は未実装だった(`docs/issues/109`)。
- 変更が必要になった条件: `Makefile:256`-`:258` の `ids=` の代入がパイプ末尾の `awk` の終了
  状態を取るため `docker ps` の非ゼロが消え、Docker が答えないときの出力が正常時の0件と
  1バイトも変わらなかった。同じホストで `claude-dev list` と `make status` が違う答えを返す。

### R-02 同梱物 `externals/arm64/colabtmux` が macOS 向けのビルドである

- 起点層・根拠: `AC-07`(用意した外部実行ファイルがコンテナ内でそのまま使える)の不合格条件
  「別のアーキテクチャ向けの実行ファイルが入っていて起動できない」/ `FR-env-13-2`。
- 変更が必要になった条件: 別のオーダーの作業中に実測された事実がどこにも記録されていなかった。
  本タスクで `file externals/arm64/colabtmux`(および HEAD の内容)を実行して再確認した。
  **修繕は行っていない**(同梱物の差し替えは不要と人間が述べているため、記録だけを行った)。

## 変更内容の要約

- `make status` のセッション列挙を、2回の `docker ps` を**別々の変数へ受けて代入の終了コードを
  1つの旗へ畳む**形へ改め、非ゼロなら一覧より前に `claude-dev list` と同一の警告行を出して
  引けた分の表示は続けるようにした(終了コードは 0 のまま)。
- 03 の文書(機能間連携仕様書の処理の流れ・異常系・実装上の判断、E2E の実機確認手順、
  テスト対応表)を実装の事実へ揃えた。
- `docs/issues/110` を起票した(arm64 の同梱物が darwin ビルドである事実。severity 「高」)。
- `make clean` に残る同型を `docs/pendings.md` の残務へ1行出した(契約が削除側の振る舞いを
  定めていないため、この closure では裁定できない)。

## 更新したドキュメント

| 理由ID | ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/03-impl/relations/MODULE-makefile-status.md | (層代表が持つ) | 処理の流れ手順2に「2つの問い合わせを別の変数へ受け旗へ畳む・旗が立てば一覧より前に警告1行」を追加。手順5を「セッションの列挙だけは終了コードを読む」へ訂正。異常系の1行目を新しい振る舞い(警告行の逐語・引けた分を表示・終了コード 0)へ書き換え。実装上の判断へ [DS-02] を1行追加し、既存3行を 継続 と読み直した。frontmatter の `tests:` に手順10-5 を追記 |
| R-01 | docs/03-impl/tests/e2e.md | 1.15.0 → 1.16.0 | 実機確認 手順10 の末尾に部分手順10-5(Docker が答えないときに0件と同じ表示にならないこと。`claude-dev list` と対にして観測)を追加。テスト設計の判断へ [DS-01] を2行追加 |
| R-01 | docs/03-impl/tests/makefile.md | 1.3.0 → 1.4.0 | `MODULE-makefile-status` 行のテスト識別子に手順10-5 を追記 |
| R-01 R-02 | docs/03-impl/index.md | 1.34.1 → 1.35.0 | 層の版を上げた(relations を変更したため)。「実装の欠陥として起票済み」の集計に、issue 110 がどの `## 既知の制限` からも参照されず数え方の定義によりこの数に入らないことを1文追記 |
| R-01 | docs/pendings.md | (版を持たない) | 残務へ1行追加(`make clean` の同型。42行 / 上限50) |

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| R-01 | MODULE-makefile-status(`Makefile::status`) | 2回の `docker ps` を別変数へ受け、代入の終了コードを `q_failed` へ畳み、非ゼロなら警告行を1本出してから畳んだ集合を表示する | 4af83d7 |
| R-02 | (実装なし。記録のみ) | `docs/issues/110-bug-bundled-arm64-binary-is-a-darwin-build.md` を起票 | 5391cf1 |

## 実施した移行

なし

### ロールバック・復旧記録

適用外(`critical: false`。closure は Makefile の読み取り専用ターゲットと 03 の文書だけで、
不可逆な操作・公開契約・認証・決済・個人情報・監査のいずれにも触れていない)。

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | MODULE-makefile-status | 異常系と処理の流れを新しい振る舞いへ。`callers` / `callees` / `contracts` / `impl` は不変(61機能・辺の増減なし) |

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| 問い合わせが失敗したときに処理を止めるか | 警告を1行出して引けた分の表示を続け、終了コードは 0 のままにする | 非ゼロで終了して呼び出し側に失敗を伝える | 引けた分を隠すと、片方の問い合わせだけが通る状況で情報が減る。`make status` は状態を見るための読み取り専用の入口であり、`claude-dev list` も同じ形を採っている / 崩れる条件: `make status` の終了コードを別の処理が合否として読むようになったとき |
| 警告の文言を新しく書くか | `claude-dev list` の文言を1字も変えずに使う | `make status` 用の文言を書く | 同じホストで同じ状態を2つのコマンドが別の言葉で伝えると、利用者はどちらが正しいのか判断できない / 崩れる条件: 契約が2つの表示を別物として定義したとき |
| 実機確認手順の置き場所 | 手順10 の末尾に部分手順10-5 として足し、既存の番号を1つも動かさない | 独立した手順を新設する / 手順10-3 の中に混ぜる | 外部の表が `手順10-3` / `手順10-4` を参照しており番号を詰めると別の手順を指す。またこの確認だけが Docker に届かない状態を要するので、手順10 の後片付けより後に置く必要がある / 崩れる条件: 手順番号を参照する外部の表が無くなったとき |
| `make clean` の同型をどう扱うか | `docs/pendings.md` の残務へ1行 | issue として起票する / この closure で直す | 契約は表示側にだけ警告行を求めており、削除側の振る舞いを定めていない。仕様に対して誤っていると言い切れないので原則8のゲート行4に当たる。直すには契約の裁定が要り、それは本 closure の外である |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規 issue | docs/issues/110-bug-bundled-arm64-binary-is-a-darwin-build.md | 同梱物 `externals/arm64/colabtmux` が macOS 向けの Mach-O で、arm64 配布イメージの中で起動しない(severity 「高」。修繕は未実施) |
| 解消した issue | docs/issues/109-bug-make-status-treats-a-failed-docker-query-as-zero-sessions.md(削除) | `closes_when` を満たした: `DOCKER_HOST=tcp://127.0.0.1:1 make status` が「一覧が不完全である可能性」の1行を出し、`(実行中のセッションはありません)` だけにならないことを実測した |
| 残務の裁定 | docs/pendings.md「残務」 | closure のパスを含む8行を読み直した。**直した: 0 件。不要と裁定: 0 件。持ち越す: 8 件** — (1) P-006 の「手順10・12」の指す先(起票者の意図の確認が要り、本タスクは材料を持たない)/ (2) e2e.md 手順8-3 の「すぐに」/ (3) e2e.md 手順7-3 の「すぐに」/ (4) issue 006 残件(E2E 手順の固定入力・観測点)/ (5) 旧表記「受入基準 N」の e2e.md 43箇所 — この4件はいずれも本タスクが触れていない手順・節であり、同じ降下で直すと closure を超える / (6) 削除済み issue を指す参照6件(残りはすべて closure 外のファイル。本タスクは追加した参照をすべて履歴のパスにして新たな1件も作っていない)/ (7) index.md:41・:48・:50 が廃止スクリプトを指す(後継が何かを決めるのは本 closure の外)/ (8) `claude-dev list` / `make status` に固定名 `claude-dev-docker-proxy` を除く条件が無い(02 の契約側の裁定が要り、片方だけ直すと食い違いが増える。本タスクの「やらないこと」に明記した) |
