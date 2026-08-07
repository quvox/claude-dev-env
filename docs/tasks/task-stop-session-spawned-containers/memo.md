---
id: task-stop-session-spawned-containers
phase: 実装
origin_layer: 00
issue: なし
date: 2026-08-07
updated: 2026-08-07
source:
  - docs/00-requests/decisions/env.md
  - docs/00-requests/terminology.md
  - docs/01-requirements/functional.md
  - docs/01-requirements/decisions/split.md
  - docs/02-design/architecture.md
  - docs/02-design/contracts/cli-container.md
  - docs/02-design/contracts/docker-api.md
  - docs/02-design/system.md
  - docs/02-design/relations.md
  - docs/02-design/logging.md
  - docs/03-impl/relations/MODULE-cli-stop.md
  - docs/03-impl/relations/MODULE-docker-proxy-serve.md
  - docs/03-impl/relations/MODULE-cli-reset.md
  - docs/03-impl/tests/cli-stop.md
  - docs/03-impl/tests/cli-reset.md
  - docs/03-impl/tests/docker-proxy.md
  - docs/03-impl/tests/e2e.md
  - docs/03-impl/tests/strategy.md
  - docs/03-impl/infra/local/docker-resources.md
summary: claude-dev stop が、そのセッションのコンテナ内から起動された Docker コンテナ群(compose 以外を含む)も片付けるようにする
---

<!-- フロントマターに インラインコメント(値のあとの # …)を書かないこと。 -->

# task-stop-session-spawned-containers セッション内から起動されたコンテナの片付け

> 解決済みの経緯: memo-1.md(フェーズ1の決定シートの回答の写し)/ memo-2.md(フェーズ2と `/doc-check` の未決点 26 件)

## 目的

`claude-dev stop` が片付けるのは、本体コンテナ・`fwd-<name>-*`・**compose ラベル
`com.docker.compose.project=<一意化名>` を持つコンテナ**だけで、セッション内から
`docker run`(compose を経由しない経路)で作られたコンテナはホストに残り続ける。
これを片付けの対象に入れる(利用者要望)。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | セッションのコンテナ内から docker-proxy 経由で作られた**コンテナとネットワーク**を識別できるようにし、`claude-dev stop` と `claude-dev reset` の片付け対象に入れる(削除は `docker rm -f` / `docker network rm`)。識別のための印(所有者を表すラベル)の付与を docker-proxy が行う。00 の決定(`D0-env-05` 項2 のライフサイクル / `D0-env-08` の識別)から 03 まで1回で下降する |
| やらないこと(このタスクの範囲外) | **名前付きボリュームの削除**(`D0-env-05` 項2 の「保持する」を維持)/ `logout` への適用(概念4 の回答)/ VM モード(ゲスト内 Docker はホストに現れないので現状どおり対象外)/ ラベル注入より前に作られた既存コンテナ・ネットワークの遡及的な片付け(識別する印が無い)/ `docs/issues/005`(解釈できないボディの中継)の根本解消 / コンテナ名の一意化(`docs/issues/028`)/ 遊休判定の方式変更 |

## 影響範囲(closure)

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | docs/00-requests/decisions/env.md | new-features/00-requests/decisions/env.md | replace |
| 00 | docs/00-requests/terminology.md | new-features/00-requests/terminology.md | replace |
| 00 | docs/00-requests/request.md | - | 変更なし(理由: 目的・対象ユーザー・スコープは変わらない。「やらないこと」5件のいずれにも当たらない) |
| 00 | docs/00-requests/acceptances.md | - | 変更なし(理由: AC は利用者視点の代表シナリオ6件で、`stop` の後片付けはどの旅程にも現れない。同型の先例 `docs/histories/2026-07-19-stop-compose-teardown.md` も AC を増やしていない) |
| 00 | docs/00-requests/decisions/sec.md | - | 変更なし(理由: `D0-sec-05` の委任範囲は「検査の厳密さと安全側の倒し方」であり、拒否判定を変えない所有者ラベルの付与はガードレール「拒否すべき操作を通してはならない」に触れない) |
| 00 | docs/00-requests/decisions/auth.md | - | 変更なし(理由: 認証の受け渡しに触れない) |
| 00 | docs/00-requests/decisions/dist.md | - | 変更なし(理由: 配布・同梱に触れない) |
| 00 | docs/00-requests/decisions/orch.md | - | 変更なし(理由: オーケストレーターに触れない) |
| 00 | docs/00-requests/decisions/scope.md | - | 変更なし(理由: 記述粒度と委任の範囲は変わらない。本変更は観測可能な振る舞いを変えるので `D0-scope-02` の委任では扱えず、00 起点として扱う) |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | replace |
| 01 | docs/01-requirements/decisions/split.md | new-features/01-requirements/decisions/split.md | replace |
| 01 | docs/01-requirements/usecases.md | - | 変更なし(理由: `stop` は UC-01〜06 のどのフローにも現れない。**これは本タスクが作った欠落ではなく既存の状態**であり、`docs/issues/080` が起票済み。要件単位では `FR-env-01` が UC-01 に現れるので A1 は通り、E2E-01 の上流 UC も UC-01 で成立する) |
| 01 | docs/01-requirements/non-functional.md | - | 変更なし(理由: 目標値・測定方法のどれにも影響しない) |
| 01 | docs/01-requirements/system.md | - | 変更なし(理由: 技術前提・実行環境・依存は変わらない) |
| 02 | docs/02-design/contracts/cli-container.md | new-features/02-design/contracts/cli-container.md | replace |
| 02 | docs/02-design/contracts/docker-api.md | new-features/02-design/contracts/docker-api.md | replace |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | replace |
| 02 | docs/02-design/relations.md | new-features/02-design/relations.md | replace |
| 02 | docs/02-design/logging.md | new-features/02-design/logging.md | replace |
| 02 | docs/02-design/architecture.md | new-features/02-design/architecture.md | replace(**`/doc-check` 2026-08-07 で影響範囲に加えた**。当初「責務もデータの流れも変わらない」としたが、docker-proxy の責務に所有者ラベルの注入が加わり、Docker 操作の結果が3値から4値になるため事実と合わなくなる) |
| 02 | docs/02-design/environments.md | - | 変更なし(理由: lint・テスト・ビルドのコマンド文字列は変わらない) |
| 02 | docs/02-design/contracts/cli-orchestrator.md | - | 変更なし(理由: オーケストレーターの起動に触れない) |
| 02 | docs/02-design/contracts/entrypoint-firewall.md | - | 変更なし(理由: ファイアウォールに触れない) |
| 02 | docs/02-design/contracts/orchestrator-prompt.md | - | 変更なし(理由: プロンプト契約に触れない) |
| 03 | docs/03-impl/relations/MODULE-cli-stop.md | new-features/03-impl/relations/MODULE-cli-stop.md | replace |
| 03 | docs/03-impl/relations/MODULE-docker-proxy-serve.md | new-features/03-impl/relations/MODULE-docker-proxy-serve.md | replace |
| 03 | docs/03-impl/relations/MODULE-cli-reset.md | new-features/03-impl/relations/MODULE-cli-reset.md | replace |
| 03 | docs/03-impl/contracts/cli-container.md | - | 変更なし(理由: **コードの鏡**で、全行が `path:line` の「定義箇所」を持つ事実表である。実装前に書くと存在しない行番号を書くことになるため、`D0-env-10` のガードレールどおり `/task-close` がコードから確定させる。確定させる内容は「申し送り事項」に書いた) |
| 03 | docs/03-impl/contracts/docker-api.md | - | 変更なし(理由: 同上。所有者ラベルの付与の実装事実は `/task-close` が `docker-proxy/main.go` の行番号つきで書く) |
| 03 | docs/03-impl/tests/cli-stop.md | new-features/03-impl/tests/cli-stop.md | replace |
| 03 | docs/03-impl/tests/cli-reset.md | new-features/03-impl/tests/cli-reset.md | replace |
| 03 | docs/03-impl/tests/docker-proxy.md | new-features/03-impl/tests/docker-proxy.md | replace |
| 03 | docs/03-impl/tests/e2e.md | new-features/03-impl/tests/e2e.md | replace |
| 03 | docs/03-impl/tests/strategy.md | new-features/03-impl/tests/strategy.md | replace |
| 03 | docs/03-impl/infra/local/docker-resources.md | new-features/03-impl/infra/local/docker-resources.md | replace |
| 03 | docs/03-impl/index.md | - | 変更なし(理由: 「この層の状態」「02 との差分」は実装後にしか数えられない集計であり、層代表の `version` と検証済み記録は `/task-close` と `/doc-check` が扱う。実装前に書くとコードの鏡ではなくなる) |
| 03 | docs/03-impl/features.md | - | 変更なし(理由: 機能(83本)の増減が無く、境界も動かない) |

**変更の起点**: 00-requests(`decisions/env.md`)。`D0-env-05` 項2 が「`stop` 時に片付けるもの」を
compose 資源に限っており、その集合を広げる判断だから。あわせて `D0-env-08` 項1(集合として列挙して
消す対象の限定)と `D0-env-10`(管理ラベルを付ける資源の種類)に届く。**下流だけ直すと
`D0-env-05` 項2 と実装が食い違う**(CLAUDE.md 原則3)。

**既存タスクとの関係**: なし(`docs/tasks/` に進行中のタスクは無い。`ls docs/tasks/` は `index.md` のみ)。

**解消できる pending / issue**: なし。関係するが解消しないもの — `docs/issues/005`
(解釈できないボディを中継する)は本変更で「ラベルを注入できない要求」という新しい観測点を得るが、
根本(fail-closed へ倒すか)は本タスクの範囲外。

## 読む範囲(読了記録)

- 全文読了: 2026-08-07
  - docs/00-requests/acceptances.md@1.2.0
  - docs/00-requests/decisions/auth.md@1.2.0
  - docs/00-requests/decisions/dist.md@1.0.1
  - docs/00-requests/decisions/env.md@1.2.0
  - docs/00-requests/decisions/orch.md@1.3.0
  - docs/00-requests/decisions/scope.md@1.2.0
  - docs/00-requests/decisions/sec.md@1.1.2
  - docs/00-requests/request.md@1.3.0
  - docs/00-requests/terminology.md@1.2.0
  - docs/01-requirements/decisions/split.md@1.1.1
  - docs/01-requirements/functional.md@1.9.0
  - docs/01-requirements/non-functional.md@1.5.0
  - docs/01-requirements/system.md@1.1.0
  - docs/01-requirements/usecases.md@1.3.0
  - docs/02-design/architecture.md@1.3.0
  - docs/02-design/contracts/cli-container.md@1.4.2
  - docs/02-design/contracts/cli-orchestrator.md@1.1.0
  - docs/02-design/contracts/docker-api.md@1.0.0
  - docs/02-design/contracts/entrypoint-firewall.md@1.0.1
  - docs/02-design/contracts/orchestrator-prompt.md@1.3.0
  - docs/02-design/environments.md@1.1.0
  - docs/02-design/logging.md@1.3.0
  - docs/02-design/relations.md@1.4.0
  - docs/02-design/system.md@2.5.0

## 決定シート(回答済み)

> 回答済み: `docs/tasks/task-stop-session-spawned-containers/sheet.md`(転記済み)。
> **論点5 は「未回答時の既定 A」で確定した** — `/doc-check` が論点5 を提示した直後に
> 人間が「実装に移って」と指示したため、シート自身が定める既定(A = `D0-env-10` の
> ガードレールを2ラベルへ広げる)を承認したものとして扱う。**A はコードを変えない**ので、
> 実装は既定のまま進められる(B ならコードが変わるため、その場合は本行を差し戻す)。
> <!-- 人間が記入する実体はこのファイル。**この行が sheet.md を名指す**ことで、memo.md を入口に
>      再開できる(directions/task-memo.md §1)。後続フェーズが sheet.md へ論点を追記したら
>      「回答待ち: sheet.md(論点 N 件)」に戻す。 -->

**フェーズ1の回答(概念6件 / 論点1〜3 / 委任1)は memo-1.md へ移動した**(変更指示へ反映済みのため)。
フェーズ2 で追記した論点の回答は次のとおり。

| # | 論点 | 回答 | 反映先 |
|---|---|---|---|
| 論点5 | 所有者ラベルを2つ注入することが `D0-env-10` のガードレールに収まるか | **既定を承認(A)**。2026-08-07、論点5 を提示した直後の「実装に移って」の指示による。`claude-dev.role=spawned` と `claude-dev.owner-project-dir` の**2つを注入する現行の 02・03 のまま実装する**。**00 の2箇所(`D0-env-10` のガードレール1行 / `D0-env-08` 項8 の「所有者を表す管理ラベル」)を「所有者と種別を表す2つ」へ書き直す**のは `/task-close` の反映で行う | `new-features/00-requests/decisions/env.md`(**フェーズ3 の C-1 で書き足す**)/ 実装は不変 |
| 論点4 | 独立レビューが実行できなかったときの代替 | **B**(サブエージェントを独立レビュー役に立てる)。2026-08-07 に実行し、指摘4件をすべて「確認済み・自動修正可能」と裁定して反映した。**実際に走ったレビュー役は `lens: subagent`**(Codex ではない。不変則7 が求める明示) | 未決点4〜7 / `new-features/01-requirements/functional.md`(`FR-env-01-24` と `FR-env-03` 条項14・17)/ `new-features/03-impl/relations/MODULE-cli-stop.md`(手順6・7・8-3 と判断19)/ `new-features/03-impl/tests/e2e.md`(手順8-14-6)/ `new-features/03-impl/tests/cli-stop.md` |

## 未決点

(memo-2.md に移動。**26 件すべて帰着済みで、未決点は0件である**)

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

## 質問キュー(未提示)

| # | 論点 | 何が止まるか | 推奨する回答(暫定) |
|---|---|---|---|
| - | なし(フェーズ1の論点はすべて sheet.md に載せた) | - | - |

## タスクリスト

<!-- フェーズ2 が置いた下書き。確定は `/implement` が行う。
     1タスク = 1コミット、依存順(印を付ける側 → 読む側 → テスト)。 -->

- [ ] 1. docker-proxy: 呼び出し元の解決を2値化する(`/workspace` のマウント元 + `claude-dev.project-dir` ラベル)。`GET /containers/json` の構造体に `Labels` を足し、キャッシュも2値で持つ _要件:_ FR-env-07-11 _Boundary:_ `docker-proxy/main.go` _Depends:_ -
- [ ] 2. docker-proxy: `POST /containers/create` と `POST /networks/create` へ所有者ラベルを注入する(拒否判定の後・ボディ再構成は1回・利用者の同名ラベルは上書き・失敗しても拒否しない) _要件:_ FR-env-07-11, FR-env-07-12 _Boundary:_ `docker-proxy/main.go` _Depends:_ 1
- [ ] 3. docker-proxy: 単体テストを足す(付与される / 他フィールドが変わらない / 上書きされる / 解決できないとき付与せず拒否もしない / ボディ不正で元のまま通す) _要件:_ FR-env-07-11, FR-env-07-12 _Boundary:_ `docker-proxy/main_test.go` _Depends:_ 2
- [ ] 4. claude-dev / claude-dev-mac: `stop` に手順8(所有者ラベルでコンテナ → ネットワークを削除・種別つき表示・0件なら無表示・失敗は握る・標準出力は捨てる)を入れ、遊休判定より前に置く _要件:_ FR-env-01-22, -23, -24, -26, -27 _Boundary:_ `claude-dev` の `stop)` 分岐 / `claude-dev-mac` の同一箇所 _Depends:_ 2
- [ ] 5. claude-dev / claude-dev-mac: `reset` に `claude-dev.role=spawned` の列挙(確認プロンプトに出す)と削除(失敗は握らない)を入れ、遊休判定より前に置く _要件:_ FR-env-01-25, -26, -27 _Boundary:_ `claude-dev` の `reset)` 分岐 / `claude-dev-mac` の同一箇所 _Depends:_ 2
- [ ] 6. E2E-01 手順8-14・8-15 と E2E-03 手順5・6 を実機で実行し、結果を記録する _要件:_ FR-env-01-22〜27, FR-env-07-11 _Boundary:_ 実機(ドキュメントは変更しない) _Depends:_ 3, 4, 5

## Definition of Done

- [ ] (フェーズ3の `/implement` が埋める。コマンドは `docs/02-design/environments.md` の厳密な文字列を使う)

## 進捗メモ

- 2026-08-07 `/doc-check`(task) 判定: **PASS**(残存: 重大度「高」0件 /「中」2件 /「低」4件。
  **中の1件は人間の裁定待ち** — `sheet.md` 論点5。もう1件は既存の `段階可 × 部分(P-005)` で、
  規範により PASS をブロックしない。低の4件は `docs/issues/079` `080` `081` `082` へ起票済み)。レビュー: **サブエージェント4本**(初回3本 + 修正後の再監査1本。Codex は利用上限で実行不可。
  代替は `sheet.md` 論点4 で人間が承認済み。**実際に走ったのは `lens: subagent`**)。
  **独立レビューは4本で計 46 件を指摘し、そのうち 33 件を「確認済み・自動修正可能」または
  「委任決定」として変更指示へ反映した**(未決点8〜26)。**再監査(4本目)は重大度「高」を1件
  出した**: `CTR-cli-container`「## エラーケース」の節ごと差し替えで**既存2行が落ちていた**
  (`INT` / `TERM` 中断の行は `FR-env-03-23` を 02 側で受ける唯一の行)。同型を全件走査するため、
  **置き換える全節の表を SSOT と行キーで突き合わせる検査を書いて回した**(候補6件のうち
  真の欠落は2件、残り4件は意図した書き換えと確認)。とくに重かったのは
  **`CTR-cli-container` の4節と `02-design/system.md` のモジュール分割定義が影響範囲から
  漏れており、`DSN-env-04` が覆した前提(「compose 資源にはラベルを付けられない」
  「管理ラベルを付けるのは Claude コンテナだけ」)を保持したまま合成ビューに残っていた**こと。
  この2ファイルは `sections:` を増やして解消した(**closure のファイル一覧は変わらない** —
  同じファイルの別の節を足しただけである)。
  **検査済みの状態**(次回の増分実行の起点。`sha1sum` を再実行して一致すれば A〜E を省略できる):

  ```
  1faad889aac9c4ede7e87c7789cad00eeb91c9b1  00-requests/decisions/env.md
  1f833fbb880b4a46f7e3e394f2be79bc950ea23f  00-requests/terminology.md
  838967d3fae87c71a0e7f1e1c386b8a7065552db  01-requirements/decisions/split.md
  300ab424f179a0eb22ef98ca4ab31e145c15112e  01-requirements/functional.md
  97976c13ccc1d8d8953daccd7780d7f0680cc2ba  02-design/architecture.md
  28f27ee75f43f85a684d271103e0f77e02c85484  02-design/contracts/cli-container.md
  1ec8905ece6035d1b53516f8d22ffc079ba58e50  02-design/contracts/docker-api.md
  9e56ff86d9cff339b463611770273b562120bfed  02-design/logging.md
  36185df90e28ebbcb78a0d532c5228ca315e081f  02-design/relations.md
  08df9bb23a72941ef82aad0a8a3535d12d777805  02-design/system.md
  f7a9dd8d2e5f12c32557c4136b41a5777f0c4a08  03-impl/infra/local/docker-resources.md
  fd84ff1cfa410deae999f406476e4a7693ac50df  03-impl/relations/MODULE-cli-reset.md
  0eb0fd3ba42c3a73c54a05b9eaa7da14d01c6331  03-impl/relations/MODULE-cli-stop.md
  84b009fc9c8c583dd4975628c293171e93ba23c7  03-impl/relations/MODULE-docker-proxy-serve.md
  e732ed4c22cf06c1042e8de767e5d0b8cc131f47  03-impl/tests/cli-reset.md
  80301af6f1fa105812651cff84840d5256f9751d  03-impl/tests/cli-stop.md
  b236d2426ea2d673d908a237af7da7890d2748d8  03-impl/tests/docker-proxy.md
  0ec46929260c11fdd975d6eb1ddf7fd4feb01641  03-impl/tests/e2e.md
  5e6f958ebe124a5a0c097c78c151ee1496690a5c  03-impl/tests/strategy.md
  ```

  - closure 側 SSOT の版: 「読む範囲(読了記録)」の 24 ファイルの版から**1つも動いていない**
    (他タスクは存在せず、SSOT 00〜03 は本実行で1文字も書いていない)
  - 機械検査: `check-changeset.py` 合格 / `check-relations.py` 合格 / `check-contracts.py` 合格 /
    `callgraph-check.py` 高 0 件 / `build-index.py --check` 差分なし / `check-sheet.py` 合格
  - **`--ssot docs` の一括検査は NG 31 件で、着手前(調査メモ9)から増減していない**

## 申し送り事項

- **`/task-close` がコードから確定させるもの**(フェーズ2 で変更指示を書かなかった3ファイル。
  理由は「影響範囲(closure)」の各行に書いた。**書き忘れると 02 の `DSN-env-04` に対応する
  実装の事実が 03 に無い状態が残る**):
  1. `docs/03-impl/contracts/cli-container.md`「実装上の事実」 — **管理ラベル**の行に
     `claude-dev.role=spawned` / `claude-dev.owner-project-dir` を追記し、**`stop` / `reset` が
     所有者ラベルで削除対象を引く**行を足す(`定義箇所` は実装後の `claude-dev` の行番号)。
  2. `docs/03-impl/contracts/docker-api.md`「実装上の事実」 — **所有者ラベルの注入**の行
     (対象パス2つ・上書きの扱い・付与できないときの挙動)を足す(`定義箇所` は
     `docker-proxy/main.go` の行番号)。「既知の制限」に、印を付けられない要求の残存を足す。
  3. `docs/03-impl/index.md` — 「この層の状態」の集計と層代表の `version` の更新。
     **02 との差分の表から「設計済み・未実装」の行が消えること**を確認する。
     **`:73` の「02(設計)との差分は上記4件で、これ以外に差分は無い」の件数も数え直す**
     (`DSN-env-04` の分が実装で解消するので4件のままのはずだが、確認せずに残すと
     `/doc-check ssot` が偽の完全性の主張として拾う)。
  4. **`docs/03-impl/tests/docker-proxy.md`** — `FR-env-07-11` / `FR-env-07-12` の
     **テスト識別子(いま `-`)を実シンボル名で埋め、状態を `実装済み` にする**。あわせて
     同ファイル「未検証(テスト未実装)の全件」の **3・4 の行を削除する**(解消の条件
     「所有者ラベルの注入の実装と同時に単体テストを追加した時点」が満たされるため)。
     **これに連動して `docs/03-impl/tests/strategy.md` の集計(209 条項 / 224 行 / 222 件)は
     変わらない**(行の増減が無く、状態列だけが動くため)。
  5. **`docs/03-impl/relations/MODULE-docker-proxy-serve.md` の frontmatter `tests:`** —
     追加した単体テストのシンボル名を足す(いまは既存15本のみ)。`/relations` の再生成で
     自動的に入るが、入っていることを確認する。
- **`docs/issues/077`(未検証の全件の「対象」列が旧表記のまま)との関係**: 本タスクで足した行は
  条項 ID の表記(`FR-env-01-22`)で書いた。既存行は旧表記(`FR-env-01 — 受入基準 6`)のまま
  残るので、`077` の移行対象は減っただけで解消していない。
