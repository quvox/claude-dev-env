---
id: 2026-08-20-fix-session-list-undercount
date: 2026-08-20
record: docs/build-records/fix-session-list-undercount.md
critical: true
origin_layer: 01
issue: docs/issues/046-bug-list-and-make-targets-undercount-containers-from-older-images.md
summary: list / make status / make clean の Claude コンテナ列挙を、イメージ由来から管理ラベルとの論理和へ改め、中継コンテナを一覧から外した
---

# 2026-08-20 セッション一覧の数え落としを直す

## 変更理由

### R-01 イメージを作り直すと、稼働中のセッションが一覧から消える

- 起点層・根拠: `FR-env-01` 受入基準5(`claude-dev list` は実行中セッションの一覧を表示する)。
  `docs/issues/046`(2026-08-04 起票)。
- 変更が必要になった条件: `docker ps --filter ancestor=<名前>` はその名前が**今**指している
  イメージ ID から作られたコンテナにしか一致しない。`make upgrade` / `claude-dev pull` /
  再ビルドで `latest` が別のイメージ ID を指すと、それ以前に起動したコンテナが一致しなくなり、
  **出力は正常時と同じ形で件数だけが少ない**ため利用者は欠落に気づけない。
  同じ書き方が `claude-dev list` / `make status` / `make clean` の3箇所に残っていた
  (`stop` 系の遊休判定は 2026-08-04 に `claude-dev-net` への接続へ移行済み)。

### R-02 中継コンテナがセッションとして一覧に出ていた

- 起点層・根拠: 同じ列挙の行に在った欠陥。`fwd-*` 中継コンテナは `$IMG_CLAUDE` から起動する
  (`claude-dev:2099`)ため `--filter ancestor=claude-dev-claude` に一致する。
- 変更が必要になった条件: R-01 の修正で同じ行を書き換えるため、`.claude/directions/issues-pendings.md`
  §1 の行1(現タスクの範囲で直すべきもの)に当たる。

## 変更内容の要約

- 列挙条件を「管理ラベル `claude-dev.managed=1`」と「イメージ(`ancestor`)」の**和集合**にし、
  名前が `fwd-` で始まる中継コンテナを除いた(`claude-dev` / `claude-dev-mac` の `list`、
  `Makefile` の `status`)。`make clean` は固定接頭辞 `fwd-` を加えた和集合(停止中を含む)。
- 和集合が新たに加えるのは**管理ラベルを持つコンテナ**、すなわち本システムが作ったものだけである。
  したがって `make clean` の削除範囲は「本システムが作ったもの」から広がっていない。
- Docker への問い合わせの失敗を 0 件と同一視せず、一覧が不完全である可能性を表示する。
- `FR-env-01-35`・`FR-env-01-36` を新設し、02 の契約に「稼働中セッションの一覧の列挙」節を足した。

## 更新したドキュメント

| 理由ID | ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01, R-02 | docs/01-requirements/functional.md | 1.20.0 → 1.21.0 | `FR-env-01-35`(数え落としの禁止)・`FR-env-01-36`(中継コンテナと docker-proxy をセッションとして出さない)を新設。`FR-env-01` の「他の 33 条項は不可分」を 35 条項へ |
| R-01, R-02 | docs/02-design/contracts/cli-container.md | 1.14.0 → 1.15.0 | 「稼働中セッションの一覧の列挙(`list` / `make status`)と一括削除(`make clean`)」節を新設。管理ラベルの読み手に MOD-cli-list / MOD-makefile を追加 |
| R-01 | docs/02-design/system.md | 2.16.0 → 2.17.0 | 要件カバレッジ表に`FR-env-01-35`・`FR-env-01-36` の行(主担当 MOD-cli-list) |
| R-01 | docs/02-design/relations.md | 1.11.2 → 1.12.0 | PLAN-cli-list / PLAN-makefile-status / PLAN-makefile-clean の契約列を CTR-cli-container へ |
| R-01, R-02 | docs/03-impl/relations/MODULE-cli-list.md | (層の版) | 処理の流れ1・異常系3行・実装上の判断(1行を更新+2行を追加。表から開示の1行形式へ)・既知の制限を実装に合わせた。frontmatter の contracts を CTR-cli-container へ |
| R-01, R-02 | docs/03-impl/relations/MODULE-makefile-status.md | (層の版) | 同上(処理の流れ2・異常系2行・判断2行追加・既知の制限) |
| R-01, R-02 | docs/03-impl/relations/MODULE-makefile-clean.md | (層の版) | 同上(処理の流れ1・2・異常系1行の訂正・判断2行追加・既知の制限) |
| R-01 | docs/03-impl/tests/cli-list.md | 1.1.1 → 1.2.0 | `FR-env-01-35`・`FR-env-01-36` の対応行(E2E-01 手順10 / 実装済み) |
| R-01 | docs/03-impl/tests/makefile.md | 1.2.1 → 1.3.0 | MODULE-makefile-status / -clean を 実装済み へ。未検証全件を 18 → 16 行へ詰めた |
| R-01, R-02 | docs/03-impl/tests/e2e.md | 1.12.0 → 1.13.0 | E2E-01 手順10 を新設(別イメージ ID のコンテナで数え落としを再現する)。シナリオ表・トレーサビリティ・テスト設計の判断2行 |
| R-01 | docs/03-impl/index.md | 1.30.0 → 1.31.0 | 層の版。`check-relations.py` 最終結果を 2026-08-20 の再実行へ。issue 046 の扱いの行を「解消して削除」へ |

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| R-01, R-02 | MODULE-cli-list | `list` の列挙を和集合にし `fwd-*` を除いた。問い合わせ失敗時に不完全である可能性を表示(claude-dev / claude-dev-mac 各 +15 行) | 25c40e6 |
| R-01, R-02 | MODULE-makefile-status | 同じ集合を `Makefile` の `status` にも。0件のときは1行で表示 | 25c40e6 |
| R-01 | MODULE-makefile-clean | 削除対象を「ラベル ∪ イメージ ∪ 固定接頭辞 `fwd-`」の和集合(停止中を含む)へ | 25c40e6 |

## 実施した移行

なし(データ移行・スキーマ変更を伴わない。既存コンテナのラベルの有無はどちらでも列挙される)。

### ロールバック・復旧記録

| 理由ID | 不可逆点 | 切り戻し可能な条件・期限 | 切り戻し手順 / forward-fix のみの理由と復旧手順 | 復元元 | 確認日 | 復旧確認コマンド・結果 |
|---|---|---|---|---|---|---|
| R-01 | `make clean` によるコンテナ・共有ボリューム(認証を含む)・イメージの削除。**本タスクが変えたのは対象の集合(管理ラベルを持つコンテナが新たに入る)で、削除そのものは以前から不可逆である** | 列挙条件の行を戻せばいつでも切り戻せる(`make clean` を実行していない間はいつでも) | `git revert 25c40e6`。**すでに `make clean` で消えたコンテナは復元できない**ので、その場合は `claude-dev start` で作り直し、`claude-dev login` で認証を取り直す(利用者の作業は `/workspace` = ホスト側のディレクトリに在るので失われない) | 不要(削除対象はコンテナ・共有ボリューム・イメージで、いずれも作り直せる。利用者のデータはホスト側に在る) | 2026-08-20 | `docker ps -a` → 0 件(E2E-01 手順10 の後片付け後。テスト用コンテナが残っていないことを確認) |
| R-02 | なし(中継コンテナを一覧から外すのは表示だけの変更である) | — | — | — | 2026-08-20 | `./claude-dev list` → `fwd-cdx-t-9999` が現れない |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | MODULE-cli-list | contracts に CTR-cli-container を追加(管理ラベルを読むため)。callers / callees は変化なし |
| 変更 | MODULE-makefile-status | 同上 |
| 変更 | MODULE-makefile-clean | 同上 |

追加・削除はなし(新しい関数を作っていないため、機能は 61 本のまま)。

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| Claude コンテナの引き方 | 管理ラベル ∪ イメージ の和集合 | 管理ラベルだけ | ラベルが付く前(2026-08-04 より前)に起動された既存コンテナを数え落とす。崩れる条件: 該当コンテナがホストから無くなったとき(そのときイメージ側は落とせる) |
| 同上 | 同上 | `claude-dev-net` への接続(遊休判定と同じ手段) | 一覧では**利用者が手で繋いだ無関係なコンテナと `login` の一時コンテナをセッションとして表示することになる**。削除(`make clean`)では利用者のコンテナを消すことになる。崩れる条件: 一覧の目的が「本システムのセッション」から「ネットワーク上の稼働物」へ変わったとき |
| 同上 | 同上 | `ancestor` に `docker images -q <名前>` の全イメージ ID を並べる(issue 046 の案C) | 削除済みイメージから作られたコンテナは依然取りこぼす。ラベルが在る今、イメージを列挙する手数に見合わない |
| 中継コンテナの除き方 | 名前の接頭辞 `fwd-` | ラベルを付けて引く | 本システムが決めた固定接頭辞なので名前で所有権が読み取れる(02 の契約「識別の手段は資源ごとに違う」)。ラベルを足すと既存分がラベルを持たない移行問題を作り込む |
| `make clean` の対象 | 数え落としだけを直し、削除の方針は変えない | `D0-env-08` 規則 A を適用し、ラベルを持たないコンテナは名前を表示して残す | 同決定の用語が破壊的操作を `stop` / `logout` / `reset` の3つと明示的に列挙しており、`make clean` は入らない。**方針そのものは 00 の決定なので裁定を残務へ移した** |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 解消した issue | docs/issues/046-bug-list-and-make-targets-undercount-containers-from-older-images.md(削除) | list / make status / make clean の数え落とし。3箇所すべてを直し、`FR-env-01-35` として 01 に固定した |
| 残務 | docs/pendings.md 残務(2026-08-20) | `make clean` を `D0-env-08` の破壊的操作の定義に加えるかが未裁定(issue 046 の「対処案」の指摘の移し先) |
| 残務 | docs/pendings.md 残務(2026-08-20) | P-006 の「手順10・12」がどの手順を指すか確定できない(E2E-01 に手順10 を新設したため別の読みが生じた) |
| 残務 | docs/pendings.md 残務(2026-08-11 の行へ追記) | コード引用の行番号のずれ: `list` 分岐が各 +15 行になったため、両ファイルの 2169 行目より後ろを指す引用が closure 外の4文書でさらにずれる |
| 残務の裁定(直した) | docs/pendings.md 残務(2026-08-19 の行を更新) | 削除済み issue を指す参照: closure 内の2件(`02-design/contracts/cli-container.md` / `03-impl/index.md`)を経緯の履歴を指す形へ直し、11件 → 9件にした(`check-ssot.py` CS11 の違反は 5 → 3 件) |
| 残務の裁定(持ち越す) | docs/pendings.md 残務(2026-08-12) | 旧表記「受入基準 N」の残り 61 箇所: 範囲表記を条項ID で書く規約が未定。**本タスクの新規記述はすべて条項ID(`FR-env-01-35` 形)で書き、この残務を増やしていない** |
| 残務の裁定(持ち越す) | docs/pendings.md 残務(2026-08-19 / 2026-08-11) | `docs/02-design/system.md` の「主担当が複数モジュールの行(`:171`)」と「SR 行19件の充足欄」、`docs/02-design/relations.md` の「`PLAN-cli-logout` の連携の詳細が無い」: いずれも本タスクが触った行(受入基準35・36 の2行 / 3つの PLAN 行の契約列)と別の箇所である |
| 残務の裁定(持ち越す) | docs/pendings.md 残務(2026-08-11 / 2026-08-19 / 2026-08-12) | `docs/03-impl/tests/e2e.md` の「E2E-01 手順8-3・手順7-3 の許容時間」と「issue 006 の残件(固定入力・観測点・合否判定・後始末が揃っていない)」: 新設した手順10 はこの4点を揃えたが、既存の手順は未整備のまま。手順7・8 は closure 外である |
| 残務の裁定(持ち越す) | docs/pendings.md 残務(2026-08-20。別タスクが同日に起票) | `docs/02-design/system.md:465` と `docs/03-impl/index.md:41`・`:48`・`:50` の廃止ツール参照: 本タスクが触った行と別の箇所で、道具名の扱いは起票者の裁定を待つ |
| 残務の裁定(持ち越す) | docs/pendings.md 残務(2026-08-11 / 2026-08-12) | 実機 E2E-01 手順8 が未実施(専有ホストが要る): 本タスクは手順10 を足しただけで、手順8 の前提は変わらない |
| 気づき | 今回限り(この列挙の行に固有) | `fwd-*` 中継コンテナが `$IMG_CLAUDE` から起動するため、イメージ由来の列挙は中継コンテナを**過剰に**数えていた。同じ1行が数え落としと数え過ぎを同時に起こしていた |
