# task-stop-session-spawned-containers 解決済みの経緯(フェーズ2)

> `memo.md` から追い出した記録。**要約ではなく逐語の移動**である(`.claude/directions/task-memo.md` §2)。
> 出どころ: フェーズ2(`/task-doc`)と `/doc-check`(2026-08-07)。全 26 件はいずれも帰着済みで、`memo.md` の「未決点」は空である。

## 未決点

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| 1 | 所有者ラベルの値を「呼び出し元の `/workspace` のマウント元」から取ると、`stop` が照合する `claude-dev.project-dir` と**別の出所**になり、両者が一致する保証が仕様として存在しない(どちらかが正規化・解決を挟むと片付けが黙って空振りする) | **ドキュメント記載**: 値を**呼び出し元コンテナの `claude-dev.project-dir` ラベルから写す**形に改めた(`DSN-env-04` の「定義」/ `MODULE-docker-proxy-serve` 手順6・7・判断7)。照合する2値が同じ1つのラベルに縛られ、一致が構成上の帰結になる | 実装ドライラン パス1(自分) |
| 2 | `docker rm -f` / `docker network rm` は削除した対象の名前または ID を標準出力へ出すので、捨てないと利用者向け出力に生の Docker ID が混じる(`docs/issues/051` と同型) | **委任決定(D0-scope-02)**: 標準出力を `>/dev/null` で捨て、種別つきの行は機能自身が `echo` する。`MODULE-cli-stop` 判断18 / `MODULE-cli-reset` 判断16 に記録 | 実装ドライラン パス1(自分) |
| 3 | 独立レビュー(`/codex-audit readiness`)が実行できなかった(Codex がアカウントの利用上限。復旧は 2026-08-11) | **人間判断 → 解決済み**: 決定シート 論点4 で人間が **B(サブエージェントで代替)** を選び、代替レビュー役を実行した(`lens: subagent`。指摘4件はすべて「確認済み・自動修正可能」と裁定して反映) | 実装ドライラン パス1 の起動 |
| 4 | `FR-env-01-24`(削除失敗時の続行)に主語が無く、`reset` にも掛かって `FR-env-03-18`(列挙して終了コード 1)と矛盾する | **ドキュメント記載**: 条項を `claude-dev stop` 限定に書き換え、`reset` は `FR-env-03` 受入基準18 に従うことを明記した | 独立レビュー(subagent)指摘1 |
| 5 | `FR-env-01-25` が `reset` の確認の列挙にセッション由来の資源を出すよう求めるが、`FR-env-03-14` は「コンテナ名」しか列挙を求めず、`FR-env-03-17` は「ネットワークは固定名で識別」と定めていて矛盾する | **ドキュメント記載**: **`FR-env-03` を影響範囲に加え**、条項14(列挙対象)と条項17(識別手段)を改めた。他の21条項は不変(`CS16` OK) | 独立レビュー(subagent)指摘2 |
| 6 | compose 経由で消える資源も用語上「セッション由来の資源」なのに、`FR-env-01-26` が求める表示の規定が手順6・7 に無い | **ドキュメント記載**: 手順6・7 で消えた名前を手順8-3 の1つの列挙へ渡す形にし、`MODULE-cli-stop` 判断19 に理由を書いた | 独立レビュー(subagent)指摘3 |
| 7 | E2E-01 手順8-14-6 が参照する `nolabel` は手順8-11 で既に削除済みで、手順が実行できない | **ドキュメント記載**: 手順8-14-6 を自己完結させ(`nolabel2` を自分で用意する)、後片付けにも追加した | 独立レビュー(subagent)指摘4 |
| 8 | `CTR-cli-container`「残したものをどう列挙するか」の除外条件に `claude-dev.role=spawned` が無いため、`claude-dev-net` に接続したセッション由来のコンテナが「ラベルを持たないコンテナ」として表示され、**`reset` が同じコンテナを「規則 D で削除する」と「残した」の両方に表示する** | **ドキュメント記載**: 同節を影響範囲に加え、除外を4つにした(`new-features/02-design/contracts/cli-container.md`) | `/doc-check` 独立レビュー(subagent)R-1 + Claude 自身(独立に検出) |
| 9 | `CTR-cli-container` の「## 破壊的操作の対象の識別」「### DSN-env-03」「### compose 資源の識別」と `02-design/system.md` の「## モジュール分割定義」が影響範囲から漏れ、いずれも「compose 資源にはラベルを付けられない / 管理ラベルを付けるのは Claude コンテナだけ」という**新設 `DSN-env-04` が覆した前提**を保持したまま合成ビューに残る | **ドキュメント記載**: 4節を影響範囲に加えて書き替えた | `/doc-check` 独立レビュー(subagent)C-1・C-2・A-1・A-2・A-3 |
| 10 | `FR-env-01-14` の「Claude コンテナ以外の資源にはラベルを付けない」が、同じ 01 の `FR-env-07-11`(docker-proxy がラベルを付与する)と正面から矛盾する | **ドキュメント記載**: 02 側の `DSN-env-01` と同じ「固定名または固定接頭辞を持つ資源には付けない」へ揃えた | `/doc-check` 独立レビュー(subagent)C-3・A-4(2本が独立に検出) |
| 11 | `FR-env-03-17` の括弧内が `logout` にも掛かる読みになり、`DSN-env-04` 規則 D の「`logout` はこの規則を使わない」と食い違う。実装者は「logout が所有者ラベルを引くのか」を発明することになる | **ドキュメント記載**: 括弧内を `reset` 限定に書き分け、`logout` は対象にしないと明記した。**`MODULE-cli-logout` は影響範囲に加えない**(01 の条項と 02 の規則 D の両方が logout を明示的に除外したので、03 側に追記しなくても実装者の答えは一意に決まる。logout のコードも変わらないので原則2 にも触れない) | `/doc-check` 独立レビュー(subagent)R-2 |
| 12 | `FR-env-03-14` の改訂「列挙するのは…である」が排他的な規定になり、`logging.md` が要求する認証ファイルのパスと `MODULE-cli-reset` 手順3 のボリューム・イメージを列挙対象から締め出す | **ドキュメント記載**: 下限規定(「少なくとも…を含めなければならない」)に改め、列挙対象の全体は `logging.md` が正だと明記した | `/doc-check` 独立レビュー(subagent)C-5 |
| 13 | `FR-env-01-22` が例外なしで「セッション由来の資源を削除する」と書く一方、所有者ラベルを付与できなかった資源は原理的に片付けられない(`FR-env-07-12` と 03 の「既知の制限」が明記)。02 のカバレッジ表の `完全` が事実と合わない | **ドキュメント記載**: 条項本文に「所有者ラベルを持つものすべて」という限定を書き、`完全` を成立させた(`部分(P-nn)` を新設しない) | `/doc-check` 独立レビュー(subagent)A-5・R-6(2本が独立に検出) |
| 14 | 所有者ラベルの注入が `CLAUDE_DEV_ALLOW_WORKSPACE_BINDS` に依存するかどこにも書かれておらず、bind の書き換えと同じ `if` へ畳み込むと bind 全面拒否の環境で `stop` の片付けが全件空振りする | **委任決定(`D0-env-10`)**: スイッチに依存しないと決め、`CTR-docker-api`「検査する要素と判定」と `MODULE-docker-proxy-serve` 手順6 に書いた | `/doc-check` 独立レビュー(subagent)R-3 |
| 15 | 「呼び出し元を特定できた」の定義が「ラベルを持っていること」だけで、**値が空文字**の場合を区別していない。空値を写すと `stop` では引けず `reset` では消える資源ができる | **委任決定(`D0-env-10`)**: 定義に「値が空文字でないこと」を加え、空値は「特定できない」へ倒すと決めた。`stop` 手順4 のガードも揃えた | `/doc-check` 独立レビュー(subagent)R-4 |
| 16 | セッション由来の資源を**引く問い合わせそのもの**(`docker ps` / `docker network ls`)が失敗したときの振る舞いが無い。`set -e` 下でそこで止まるのか安全側へ倒すのかを実装者が決めることになる | **ドキュメント記載**: 上流が答えを持っていた(`FR-env-01-24` = `stop` は続行 / `D0-env-08` 項5 = `reset` は握らない)ので、契約のエラーケースと両モジュールの異常系に「`stop` は行わずに続行し表示、`reset` は失敗として記録」を書いた。**0件と問い合わせ失敗を同一視しない**ことも明記 | `/doc-check` 独立レビュー(subagent)R-5 |
| 17 | `MODULE-cli-reset` 手順6 が手順3 と同じフィルタで**引き直す**書き方で、手順3〜4 の対話中に作られた資源が確認の列挙を経ずに消える。`FR-env-03-14` の「消える前に見られる唯一の機会」と食い違う | **ドキュメント記載**: 手順3 の集合をそのまま使う(引き直さない)と明記した。手順5 のコンテナ削除と同じ扱いである | `/doc-check` 独立レビュー(subagent)R-8 |
| 18 | `MODULE-docker-proxy-serve` の手順5 と手順6 がそれぞれ「`r.Body` / `ContentLength` / `Content-Length` を更新して中継する」と書いており、文面どおり実装すると判断8 の「ボディの再構成は1回」と矛盾する2回再構成になる | **ドキュメント記載**: 書き戻しを手順6 の末尾1箇所に集約した。既存15本の回帰も判断8 に書いた | `/doc-check` 独立レビュー(subagent)R-7 |
| 19 | 列挙コマンドの出力整形(`--format` か `-q` か既定の表か)が決まっておらず、実装者が発明することになる | **委任決定(`D0-scope-02`)**: `--format` で名前だけを取ると両モジュールの実装上の判断に書いた(既定はヘッダ付きの表、`-q` は ID なのでどちらもそのままでは使えない) | `/doc-check` 独立レビュー(subagent)R-9 前半 |
| 20 | `CTR-cli-container`「## エラーケース」を `replace` で差し替えた際に、**既存 26 行のうち2行(旧い名前の compose 資源 / `INT`・`TERM` を受けた)が落ちていた**。後者は `FR-env-03-23`(終了コード 130)を 02 側で受ける唯一の行で、`MODULE-cli-reset` 手順10 と `MODULE-cli-logout` が名指して参照している | **ドキュメント記載**: 2行を原文のまま復元した。**同型を全件走査した**(置き換える全 55 節の表を SSOT と行キーで突き合わせ、候補6件のうち真の欠落はこの2件、残り4件は意図した書き換えと確認) | `/doc-check` 再監査(subagent)X-1 |
| 21 | `CTR-docker-api` の判定表とエラーケースが、`DSN-env-04` の「値が空文字でないこと」を条件に含めていない。docker-proxy の実装者が読む契約はこちらなので、契約どおり実装すると空値が注入される | **ドキュメント記載**: 判定表とエラーケースの条件に空文字の場合を加え、`DSN-env-04` の定義と揃えた | `/doc-check` 再監査(subagent)X-3 |
| 22 | `MODULE-cli-stop` 手順8 の「列挙の問い合わせが失敗したらこの手順を行わずに続行」が**手順8 全体のスキップ**と読め、手順8-3(手順6・7 で消えた compose 資源の列挙)まで飛ばすと `FR-env-01-26` を満たさない。片方の問い合わせだけが失敗したときの扱いも無い | **ドキュメント記載**: 適用範囲を 8-1 / 8-2 に限定し、**8-3 の列挙は必ず実行する**と明記。片方だけ失敗した場合(成功した側は削除する。ただしコンテナ側が失敗したらネットワーク側はやらない)も書いた | `/doc-check` 再監査(subagent)X-6 |
| 23 | E2E-01 手順8-14-7(新設)が「`aaa` のコンテナを繋ぐ」と書くが、`aaa` は部分手順3 の `claude-dev stop aaa` で既に消えている。手順が実行できず、`FR-env-01-24` が実機確認の当てを失う | **ドキュメント記載**: 繋ぐ相手を手順内で作る形(`netholder`)に直し、後片付けにも足した | `/doc-check` 再監査(subagent)X-7 |
| 24 | `FR-env-03-14` が列挙対象の全体の正として名指した `logging.md`「破壊的操作の削除対象の確認」が、`MODULE-cli-reset` 手順3 より狭い(`fwd-*`・共有ボリューム・イメージ・共有資源の候補行を含まない)。**正のほうが 03 より狭い** | **ドキュメント記載**: `logging.md` の同行に `logout` / `reset` の列挙対象を種別ごとに書き分けた | `/doc-check` 再監査(subagent)X-8 |
| 25 | `docs/02-design/architecture.md` が影響範囲から漏れており、docker-proxy の責務に所有者ラベルの注入が無く、Docker 操作のデータの流れが3値のまま(改訂後の `CTR-docker-api` は4値) | **ドキュメント記載**: architecture.md を影響範囲に加え、「コンポーネントの責務」と「データの流れ」の2節を書き替えた | `/doc-check` 再監査(subagent)X-12 |
| 26 | `MODULE-cli-reset` の列挙失敗の扱いが手順6 にしか書かれておらず、実際に問い合わせるのは手順3 である。さらに手順4 の確認でキャンセルされた場合の扱いが無い | **ドキュメント記載**: 手順3 側にも書き、**キャンセル時は引けなかった事実を表示しつつ終了コードは 0 のまま**(何も削除していない以上「消えなかった資源」は無い)と定めた | `/doc-check` 再監査(subagent)X-9 |

## 進捗メモ(フェーズ1。`memo.md` から追い出した分)

- 2026-08-07 フェーズ1: 00〜02 を全文読了。影響範囲(closure)を確定し、決定シート
  (概念6件 / 論点3件 / 委任1件)を `sheet.md` に作成した。
- 2026-08-07 フェーズ2: **独立レビュー(`lens: subagent`。論点4=B の承認による代替)を実行し、
  指摘4件をすべて「確認済み・自動修正可能」と裁定して反映した**。うち1件は
  **`FR-env-03` が影響範囲から漏れていた**ことの検出で、条項14・17 を改めて closure に加えた。
  `check-changeset.py` は反映後も**合格**(条項 62 件 / 触った要件 3 件)。
  **フェーズ2 で私がやることは残っていない。次は `/doc-check task-stop-session-spawned-containers`**
  (人間が `/clear` 後に実行する = 決定シートの (c))。
- 2026-08-07 フェーズ2: **03 完了 → 下降を書き切った(変更指示 18 ファイル)**。
  `check-changeset.py` は**合格**(CS9 を「未検査」にしないため 02 の PLAN 一覧表も変更指示に含めた。
  CS5/6/7 が「未検査 — 未設定」なのは本タスクと無関係の既存の穴で `docs/issues/079` に起票した)。
  実装ドライラン **パス1 は自分の分だけ完了**(未決点3件。うち2件は変更指示へ反映済み)。
  **独立レビューは走らなかった**(Codex が利用上限。復旧 2026-08-11)ので、代替の可否を
  `sheet.md` 論点4 に載せた。**次は `/doc-check task-stop-session-spawned-containers`**。
- 2026-08-07 フェーズ2: **02 完了**(`contracts/cli-container.md` = `DSN-env-04` 新設・識別の表と
  管理ラベル表の更新・規則 D の追加・エラーケース6行追加 / `contracts/docker-api.md` = 検査する要素に
  所有者ラベルの付与2行・エラーケース4行・`DSN-env-04 の適用` / `system.md` = カバレッジ表に8行・
  結合テスト対象と E2E-01/03 の更新 / `relations.md` = `PLAN-cli-stop` の詳細を新設し
  `PLAN-docker-proxy-serve` を更新 / `logging.md` = 主要イベントに5行追加)。
- 2026-08-07 フェーズ2: **01 完了**(`new-features/01-requirements/functional.md` = `FR-env-01` に
  条項22〜27・`FR-env-07` に条項11〜12 を追加、両要件の分割可否の理由文の件数を更新 /
  `new-features/01-requirements/decisions/split.md` = `D1-split-01` の条項件数を更新)。
- 2026-08-07 フェーズ2: **00 完了**(`new-features/00-requests/decisions/env.md` = `D0-env-05` の
  見出し改名と項2 の拡張・`D0-env-08` の項1/項3/項7 改めと項8 新設・`D0-env-10` の委任範囲拡張 /
  `new-features/00-requests/terminology.md` = 「管理ラベル」の定義更新・「セッション由来の資源」の新設)。
- 2026-08-07 フェーズ1: 人間が `sheet.md` を記入完了(2026-08-07)。全件を上の
  「決定シート(回答済み)」へ転記した。**概念3 だけが推奨と異なり、セッション内から作られた
  ネットワークも削除対象に入った**(推奨は compose 既定ネットワークまで)。この帰結として
  `POST /networks/create` への所有者ラベル注入が必要になり、委任1(注入する API 経路を含む)の
  中で決める。次は `/task-doc task-stop-session-spawned-containers`。

## 調査メモ

| # | 調べたこと | 判明した事実 | 出どころ |
|---|---|---|---|
| 1 | `stop` が現在片付ける対象 | 本体コンテナ・`fwd-<NAME>-*`・`com.docker.compose.project=<一意化名>` のコンテナ・`<一意化名>_default` ネットワークだけ。`docker run` で作られたコンテナを指す印は無い | `claude-dev:1649`〜`:1707` |
| 2 | docker-proxy が呼び出し元を特定できるか | できる。`lookupProjectDir` が `GET /containers/json` を引き、接続元 IP に一致するコンテナの `/workspace` マウント元(ホスト側絶対パス)を返す。TTL 60 秒でキャッシュする | `docker-proxy/main.go:70`〜`:126` |
| 3 | docker-proxy が作成要求のボディを書き換える前例 | ある。`/workspace` 配下の bind を実ホストパスへ書き換え、`r.Body` / `ContentLength` / `Content-Length` を更新して中継する | `docker-proxy/main.go:158`〜`:254`, `:531`〜`:538` |
| 4 | 解釈できないボディの扱い | 検査せず中継する(`json.Unmarshal` 失敗で `return nil`)。ラベルも注入できない | `docker-proxy/main.go:493`〜`:496` / `FR-env-07-8` / `docs/issues/005` |
| 5 | 管理ラベルを付けている資源 | Claude コンテナだけ(`claude-dev.managed` / `claude-dev.role` / `claude-dev.project-dir`) | `claude-dev:1388`〜`:1390` / `docs/02-design/contracts/cli-container.md`「管理ラベル」 |
| 6 | `stop` の compose 一意化名のハッシュ源 | `claude-dev.project-dir` ラベルの値(起動ディレクトリの絶対パス)。本体コンテナを消す前に読む | `claude-dev:1656`〜`:1663` / `CTR-cli-container`「compose 資源の識別」 |
| 7 | 影響範囲の機械抽出(`relations-query.py --impact claude-dev`) | 機能31件 / 要件13件 / 契約2件(`CTR-cli-container`, `CTR-cli-orchestrator`)。**走らせるべきテストは0件**(シェル実装に自動テストが無い) | `relations-query.py --impact claude-dev` |
| 8 | 影響範囲の機械抽出(`relations-query.py --impact docker-proxy/main.go`) | 機能1件(`MODULE-docker-proxy-serve`)/ 要件2件(`FR-env-07`, `NFR-sec-01`)/ 契約1件(`CTR-docker-api`)。**走らせるべきテスト15件**(`docker-proxy/main_test.go` と `binds_test.go`) | `relations-query.py --impact docker-proxy/main.go` |
| 9 | 仕様ドキュメントの一括検査(母集団の凍結) | `check-changeset.py --ssot docs` は **NG 違反 31 件**(本タスク着手前の既存値)。内訳の主なものは参照先が実在しない `docs/issues/NNN`(`docs/issues/054` が追跡)と、同型の欠陥7種が各1件。**本タスクはこの件数を増やさないことを目標にする** | `check-changeset.py --ssot docs` の出力 |
| 10 | 同型の先例 | 2026-07-19 に同じ利用者要望で compose コンテナの片付けを入れた。片付け範囲は人間確認により「`docker compose down` 相当」= コンテナ + 当該 compose 既定ネットワークを削除、名前付きボリュームは保持、共有資源は残す | `docs/histories/2026-07-19-stop-compose-teardown.md` |
| 11 | 受入基準の条項数 | 機能要件の全 201 条項。対応表は 216 行(条項 214 件 + `FR-env-01-9` の重複2行)。条項を足すとこの数が動く | `docs/03-impl/tests/strategy.md:115` |
| 12 | `PROJECT_DIR` の作り方 | Linux 版・macOS 版とも `PROJECT_DIR="$(pwd)"`。この値が `-v` のマウント元にも `--label claude-dev.project-dir=` にも渡る | `claude-dev:1145`, `claude-dev-mac:1213`, `claude-dev:1388`〜`:1390` |
| 13 | `stop` がラベルを読む関数 | `container_project_dir()` が `docker inspect --format '{{index .Config.Labels "claude-dev.project-dir"}}'` を実行し、`<no value>` を空に潰す。**新しい手順8 はこの既存関数の戻り値をそのまま照合値に使える** | `claude-dev:559`〜`:566` |
| 14 | 遊休判定の実体 | `net_other_running_containers()` が `docker network inspect claude-dev-net` の接続コンテナと `docker ps` の積を取り、`claude-dev-docker-proxy` と `fwd-*` を除く。**問い合わせ失敗で非0を返す** | `claude-dev:577`〜`:594`, `:596`〜 |
| 15 | 新しい手順8 を挿す位置 | `stop` の compose ネットワーク削除(`claude-dev:1688`)と旧い名前の案内(`:1699`〜`:1707`)の後、共有資源単位のロック取得(`:1711`)の前 | `claude-dev:1688`〜`:1711` |
| 16 | `reset` の削除対象の列挙位置 | `_rc_containers` / `_rc_fwd` / `_rc_volumes` / `_rc_images` を作る区間。**セッション由来の資源の配列はここに足す**(確認プロンプトの列挙 `:1994`〜 に出るため) | `claude-dev:1954`〜`:1975`, `:1994`〜`:2000` |
| 17 | docker-proxy が呼び出し元を引く経路 | `lookupProjectDir()` が `GET http://docker/containers/json` を叩き、`NetworkSettings.Networks[*].IPAddress` の一致で1件を選び `Mounts` から `/workspace` の `Source` を取る。**同じ応答に `Labels` も含まれるので、構造体に `Labels map[string]string` を足せば問い合わせを増やさずに `claude-dev.project-dir` を取れる** | `docker-proxy/main.go:88`〜`:126` |
| 18 | docker-proxy がボディを書き換える既存の型 | `rewriteBinds()` が `map[string]json.RawMessage` でトップレベルを扱い、`HostConfig` だけを開いて書き戻す。**`Labels` もトップレベルなので同じ関数の形で扱える**。書き戻し後の後始末は `r.Body` / `r.ContentLength` / `Content-Length` の3つ | `docker-proxy/main.go:158`〜`:254`, `:531`〜`:538` |
| 19 | 独立レビューの実行可否 | `codex exec --sandbox read-only -c features.use_legacy_landlock=true` は起動するが **`ERROR: You've hit your usage limit ... try again at Aug 11th, 2026`** で終わる(終了コードは 0 のまま。`docs/feedbacks/003` の「成否を応答文で判定しない」に該当) | 2026-08-07 の実行ログ(スクラッチパッド) |
| 20 | `docker network ls` / `docker ps` の `--filter label=<キー>=<値>` は完全一致で、`--filter label=<キー>` だけならキーの存在一致になる | `reset` が所有者を問わず引くには `claude-dev.role=spawned`(値一致)でも `claude-dev.owner-project-dir`(キー存在)でも書ける。本設計は前者を採る(`MODULE-cli-reset` 判断13) | Docker CLI の `--filter` の仕様 |
| 21 | `GET /containers/json` の応答に含まれる `Labels` の値が空文字のとき、Go の `map[string]string` では「キーが無い」と区別できるが、`docker inspect --format` 側は `<no value>` を返し `container_project_dir()` が空へ潰す | 両側とも「空文字なら所有者を得られなかった」に倒せば、区別する必要そのものが消える(未決点15 の決定はこれに基づく) | `claude-dev:559`〜`:566` / `docker-proxy/main.go:88`〜`:126` |
| 22 | E2E-03(既存)には後片付けの手順が無い | 従来の手順1〜4 は `docker run alpine true`(名前なし・即終了)だけだったので必要がなかった。本タスクが `-d ... sleep 60` の名前付きコンテナ2つとネットワーク1つを足したので、後片付けが要るようになった | `docs/03-impl/tests/e2e.md` の E2E-01(手順16 に後片付けがある)との対比 |
