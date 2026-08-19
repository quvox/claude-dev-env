# task-stop-cleanup-and-project-env の解決済みの経緯(memo-1)

<!-- memo.md からフェーズ3 の入口で移した。移動であって要約ではない(task-memo.md §2)。 -->

## 未決点(すべて帰着済み。フェーズ2 のドライラン)


| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| 1 | `--volumes` を `stop` の引数解析のどこで取り除くか(コンテナ名の検証より前か後か) | 委任決定(DS-05)。`MODULE-cli-stop` の開示行 | 実装ドライラン パス1 |
| 2 | 存在しなかった資源と削除に失敗した資源をどう区別するか | 委任決定(DS-02)。`MODULE-cli-stop` の開示行(削除前の実在確認で行う) | 実装ドライラン パス1 |
| 3 | env ファイルの1行で値に `=` が含まれる場合と引用符の扱い | 委任決定(DS-04)。`MODULE-cli-start` の開示行(最初の `=` で割り、引用符は取り除かない) | 実装ドライラン パス1 |
| 4 | 予約した名前の判定は大文字小文字を区別するか | 委任決定(DS-04)。`MODULE-cli-start` の開示行(区別する) | 実装ドライラン パス1 |
| 5 | env ファイルのパスの封じ込めを実体解決で行うか字句的に行うか | 委任決定(DS-05)。`MODULE-cli-start` の開示行(字句的。`DSN-dp-02` と同じ考え方) | 実装ドライラン パス1 |
| 6 | `reset` にも `--volumes` の明示を求めるか | ドキュメント記載。`FR-env-01-32` の条項本文に `[DS-04]` つきで書いた | 実装ドライラン パス1 |
| 7 | 採用しなかった行の表示に値を含めるか | 委任決定(DS-03)。`MODULE-cli-start` の開示行(名前と行番号だけ。値は出さない) | 実装ドライラン パス1 |

**人間判断へ回した未決点は0件である。** 上の7件はいずれも標準委任の内側にあり、
決めて開示した(`.claude/directions/delegation.md` §1 の問う基準を満たさない)。


## 調査メモ(フェーズ1〜2 の技術調査)


| # | 調べたこと | 判明した事実 | 出どころ |
|---|---|---|---|
| 1 | docker-proxy が所有者ラベルを実際に注入するか | **注入する**。稼働中セッションの中から `docker network create` / `docker create` を実行し、ホスト側で `claude-dev.owner-project-dir` と `claude-dev.role=spawned` が付いていることを実測した(2026-08-18) | `docker-proxy/main.go:309`(`injectOwnerLabels`)/ `:350`(`labelNetworkCreate`)/ `:692` 付近(`validateContainerCreate` の付与) |
| 2 | `stop` がセッション由来のコンテナ・ネットワークを実際に消すか | **消す**。ラベル付きの疑似 Claude コンテナ(`cdxprobe`)を立て、その中から `docker compose up -d`(サービス1・名前付きボリューム1・追加ネットワーク1)を実行してから `./claude-dev stop cdxprobe` を実行したところ、コンテナ `cdxprobe-2d1e34-a-1` とネットワーク `cdxprobe-2d1e34_extra` はどちらも削除された(2026-08-18) | `claude-dev:1745`〜`:1772` |
| 3 | 同じ実測で `stop` が出した警告 | **「⚠️ 次のセッション由来の資源は削除できませんでした: ネットワーク: cdxprobe-2d1e34_default」が出た。この既定ネットワークはそもそも作られていない**(compose ファイルが `networks: [extra]` だけを使ったため)。実装は `docker network rm` の失敗を「存在しなかった」と「消せなかった」で区別せず、どちらも失敗として列挙する | `claude-dev:1728`〜`:1737`(コメントは「存在しなかった場合も同じ経路に入るが…害はない」と書いている) |
| 4 | 名前付きボリュームの扱い | **ラベルも付かず、削除もされない**。同じ実測でボリューム `cdxprobe-2d1e34_vdata` は `stop` の後も残り、`claude-dev.*` ラベルを1つも持たない。docker-proxy は `/volumes/create` を検査経路に持たない(ルーティングは `containerCreateRe` と `networkCreateRe` の2つだけ) | `docker-proxy/main.go:396`・`:401`・`:457`〜`:471` |
| 5 | 実機に残っている片付け漏れ | このホストには `ct_matchsupport-b5dc8f_*`(現行の一意化名)と `ct_matchsupport_*`(一意化前の旧名)の compose ボリュームが計 13 本残っている。いずれも `claude-dev.*` ラベルを持たない | `docker volume ls` / `docker volume inspect`(2026-08-18) |
| 6 | Linux 版と macOS 版の差分 | `stop` のセッション由来資源まわり(`spawned` / `_cproj` / `compose_project_name` を含む行)は**両 OS で完全一致**。`.claude-dev.yaml` まわりは案内文と字下げだけが違う | `diff <(grep spawned claude-dev) <(grep spawned claude-dev-mac)` |
| 7 | 本タスクが乗る条項に未充足のものがあるか | `FR-env-01-19` と `FR-env-07-5` が `部分(P-005)`(compose 一意化名のハッシュ先頭6桁の衝突を検出しない)。**P-005 の解消条件「同時に扱うプロジェクト数が数百規模になったとき、または衝突が実際に観測されたとき」は到達していない**(このホストの同時プロジェクト数は 1〜数件、衝突の観測は無い)。ただし**片付けの対象をボリュームへ広げる場合、衝突時に失われるものが「作り直せるコンテナ」から「利用者のデータ」に変わる** — これは論点1 の判断材料である | `docs/pendings.md` P-005 / `docs/02-design/system.md`「要件カバレッジ確認」 |
| 8 | 本タスクが解消できる記録 | `docs/issues/002`(`.claude-dev.yaml` が全面上書き・全リスト行削除される)は **R-02 の前提であり本タスクで解消する**。issue 本文の対処案 B が「`ssh_keys` 以外のキーを足す変更が発生した時点で直す」と書いており、その時点が来た | `docs/issues/002-modify-claude-dev-yaml-is-overwritten-wholesale.md` |
| 9 | 走らせるべきテスト(DoD の種) | `relations-query.py --impact claude-dev` は「走らせるべきテスト 0 件。**テストが無い範囲を変更しようとしている**」を返す。シェル実装に自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)の帰結であり、検証は **E2E-01(手順8 のセッション由来資源の部分)** と **E2E-03** の実機確認、および docker-proxy を触る場合の `cd docker-proxy && go test ./...` になる | `docs/02-design/system.md`「E2Eシナリオ一覧」/ `docs/02-design/environments.md`「lint・テストコマンド」 |
| 10 | 仕様ドキュメントの一括検査(母集団の凍結) | `python3 .claude/scripts/check-changeset.py --ssot docs` = **NG 違反 9 件**。内訳はすべて `CS20`(issue の `origin_layer` 欠落): `002` / `005` / `010` / `028` / `046` / `055` / `076` / `079` / `081`。`CS8`(曖昧語・未決点)/ `CS11`(参照実在)/ `CS12`(同型の走査記録)/ `CS18`(要件に降りてきた機構)/ `CS19`(理由の網羅)はすべて OK。**これが母集団である** | `check-changeset.py --ssot docs`(2026-08-18 実行) |
| 12 | 実装ドライラン パス2(技術調査): `stop` の引数解析 | `stop)` は `[ -n "$2" ]` で名前を取り、`case "$NAME" in *[!A-Za-z0-9._-]*)` で検証する。**フラグはこの手前で取り除く必要がある** | `claude-dev:1661`〜`:1675` |
| 13 | 同(存在確認の手段) | `spawned_resources` は `docker ps -a` / `docker network ls` を `--filter label=` で引く既存の形を持つ。**ボリュームは `docker volume ls --filter label=` が同じ形で使える**(実測で確認) | `claude-dev:586`〜`:592` |
| 14 | 同(所有者ラベルの注入点) | `injectOwnerLabels(body, owner)` はトップレベル `Labels` を書く汎用関数で、`labelNetworkCreate` が拒否判定なしの経路の型を既に持つ。**ボリューム作成経路はこの型をそのまま複製できる** | `docker-proxy/main.go:309`(注入) / `:350`(ネットワーク経路) / `:401`(経路の正規表現) |
| 15 | 同(設定ファイルの読み書き) | 読み取りは `_parse_ssh_keys_yaml`(行指向・`ssh_keys:` で節に入り、字下げの無い行で抜ける)、書き出しは `write_project_ssh_keys`(`> "$file"` で全面上書き)。**節の判定の骨は読み取り側に既に在る**ので、書き出し側と `ssh-keys reset` をその形へ揃える | `claude-dev:71`〜`:88`(読み取り)/ `:112`〜`:120`(書き出し)/ `:1301` 付近(`ssh-keys reset`) |
| 16 | 同(環境変数の付与点) | `docker run` は `$DOCKER_OPTS` `$COMPOSE_OPTS` などを展開したあと `-e NODE_OPTIONS=...` を置いている。**プロジェクト由来の `-e` はこの後ろに置く** | `claude-dev:1500`〜`:1527` |
| 17 | 同(`.gitignore` への追記) | `.claude` / `.codex` について「`<name>` も `<name>/` も未記載のものだけ追記する」既存の処理がある。**env ファイルのパスも同じ処理に載せられる** | `MODULE-cli-start` 手順12 |
| 11 | closure の合格証 | closure に載る既存 SSOT ドキュメント 20 本と層代表 `docs/03-impl/index.md` は、**すべて `verified.version` が自身の `version` と一致**している(原則6 を満たす)。フェーズ2 の前に直すべき合格証は無い | 各ファイルの frontmatter(2026-08-18 確認) |


## 進捗メモ(フェーズ1〜2 の詳細)

- 2026-08-19 フェーズ2: **03 完了 / 降下1回ぶんを書き終えた**。変更指示 25 件。
  relations 7 本(`-cli-stop` / `-cli-reset` / `-cli-start` / `-cli-common-spawned-resources` /
  `-cli-common-write-project-ssh-keys` / `-cli-ssh-keys-reset` / `-docker-proxy-serve`)、
  tests 4 本(`cli-stop` / `cli-reset` / `cli-start` / `e2e`)。
  **`check-changeset.py` 合格**(CS1〜CS22 で違反0。未検査は CS5/CS6/CS7/CS10/CS21 —
  いずれも設定が無いか対象外)。**警告**: 変更指示 25 件は目安 20 件を超えている
  (2つの依頼を1回の降下で扱うため。CLAUDE.md §4 の指針)。
  **03 の契約2本とテスト対応表3本は「変更なし」へ落とした** — 行番号を含む実装の鏡と
  まだ存在しないテストの識別子は、実装前に書くと必ず上書きされるため
  (`.claude/directions/03-impl.md`)。
- 2026-08-19 フェーズ2: **02 完了**。`contracts/cli-container.md`(渡す環境変数へ利用者由来の行と
  **予約する環境変数名**の節・適用順、`DSN-env-04` の対象へボリューム、`DSN-env-05` 新設、
  **プロジェクト設定ファイルとプロジェクト環境ファイル**の節を新設して `docs/issues/002` を閉じる
  取り決めを書いた、エラーケース 11 行追加)/ `contracts/docker-api.md`(注入経路にボリューム作成要求)/
  `architecture.md`(`DSN-arch-05` 新設 = `docs/issues/092` の裁定の項3、`DSN-arch-02` に環境ファイル)/
  `system.md`(分割定義・カバレッジ 17 行追加・条項数 147→164・結合テスト対象・E2E)/
  `relations.md`(`PLAN-cli-start` / `-stop` / `-reset` / `-docker-proxy-serve`)/ `logging.md`。
  **新しい機能(`PLAN-*` / `MODULE-*`)は1本も作らない** — 環境ファイルの読み取りは `start` からしか
  呼ばれず、共有基盤へ上げる条件(ファンイン2以上)を満たさないため(`DSN-env-05` / `PLAN-cli-start`)。
  この判断により **`03-impl/features.md` は変更不要**になったので closure から外した。次は 03。
- 2026-08-19 **範囲外の報告を1件受理**: 人間から「colabtmux から codex を呼ぶと
  『bwrap が非ゼロのため codex を起こせず』と出る」。**本タスクには混ぜず**
  `docs/issues/102` に起票した(CLAUDE.md §4 の「進行中のタスクを分割・併合しない」)。
  報告文はこのリポジトリにも同梱バイナリにも存在しないことをバイト列走査で確認済み。
- 2026-08-19 フェーズ2: **00 完了**。`request.md`(`RQ-env-07` と「やらないこと」7)/
  `acceptances.md`(`AC-08`)/ `terminology.md`(「セッション由来の資源」の外延にボリューム、
  新語「プロジェクト環境ファイル」)/ `decisions/env.md`(`D0-env-05` 項2 の改訂・`D0-env-08` 項2 と
  項8 の改訂・`D0-env-11` 新設)/ `decisions/sec.md`(`D0-sec-11` 新設)の5本を書いた。次は 01。
- 2026-08-19 フェーズ1 完了: 人間がチャットで回答。**論点2 だけ推奨を採らず**、
  「`.claude-dev.yaml` では env ファイルを指定し、秘密情報は env ファイルに書く(env は gitignore)」
  という形に決まった。他の4件(概念1・概念2・論点1・論点3)は推奨を承認。
  転記済み(決定シート(回答済み))。`phase:` を `ドキュメント` へ進めた。次は `/task-doc`。
- 2026-08-18 フェーズ1: 00〜02 を全文読了(21 ファイル)。実機で `stop` の片付けを再現し、
  コンテナ・ネットワークは消えること、**ボリュームだけが残ること**、**存在しない compose 既定
  ネットワークが「削除できませんでした」と表示されること**を確認した(調査メモ 2〜4)。
  closure と lane(`critical`)を確定し、sheet.md を作成。人間の回答待ち。
