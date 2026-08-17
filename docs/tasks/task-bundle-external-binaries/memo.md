---
id: task-bundle-external-binaries
phase: 反映
lane: critical
origin_layer: 00
external_behavior: true
irreversible_data: true
security_payment_privacy: true
public_contract_breaking: false
shared_resource_format: true
unresolved_impact: false
rollback_defined: false
issue: なし
origin: human-report
date: 2026-08-18
updated: 2026-08-18
source:
  - docs/00-requests/request.md
  - docs/00-requests/decisions/dist.md
  - docs/00-requests/acceptances.md
  - docs/00-requests/terminology.md
  - docs/01-requirements/functional.md
  - docs/01-requirements/non-functional.md
  - docs/01-requirements/system.md
  - docs/01-requirements/usecases.md
  - docs/01-requirements/decisions/split.md
  - docs/02-design/system.md
  - docs/02-design/architecture.md
  - docs/03-impl/environments/images.md
  - docs/03-impl/infra/local/ghcr.md
  - docs/03-impl/tests/images.md
  - docs/03-impl/tests/strategy.md
  - docs/03-impl/index.md
summary: 保守者が用意した外部実行ファイルを externals/ 経由で配布イメージの PATH へ同梱する仕組みを作る
---

<!-- フロントマターに インラインコメント(値のあとの # …)を書かないこと。 -->

# task-bundle-external-binaries 外部実行ファイルの同梱(externals/)

> 解決済みの経緯: (まだ無し)

## 目的

保守者がリポジトリ直下の `externals/` に置いた実行ファイルを、配布イメージ2種
(`claude-cli` / `claude-vnc`)の PATH の通った場所へ同梱する仕組みを作る。最初の同梱対象は
別リポジトリ `zettant/colabtmux` の Linux 向け実行ファイル `colabtmux` であり、バイナリそのものは
人間が手で `externals/` へコピーする。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | (1) `externals/` の規約(直下 = 全アーキ共通 / `externals/amd64/` `externals/arm64/` = そのアーキのみ / `README.md` はコピー対象外)を決めて 00〜03 へ降ろす (2) `.devcontainer/Dockerfile.claude` の配布ステージ2つの**最終**レイヤーで `/usr/local/bin` へ設置する (3) `externals/` の骨格(`README.md`)を作りコミットする (4) 検証手順を `03-impl/tests/images.md` に足す |
| やらないこと(このタスクの範囲外) | `colabtmux` のバイナリ本体をコミットすること(**人間が置く**。このタスクは器と仕組みだけを納める) / colabtmux 側リポジトリの CI・リリース整備 / バイナリを自動で取得する経路(Release からの curl / private repo の clone ビルド)の実装 — 人間が 2026-08-18 に却下した / `externals/` の中身をイメージビルド時に検証すること(署名・チェックサム) |

## 影響範囲(closure)

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | docs/00-requests/request.md | new-features/00-requests/request.md | replace |
| 00 | docs/00-requests/decisions/dist.md | new-features/00-requests/decisions/dist.md | replace |
| 00 | docs/00-requests/acceptances.md | new-features/00-requests/acceptances.md | replace |
| 00 | docs/00-requests/terminology.md | new-features/00-requests/terminology.md | replace |
| 00 | - | - | 変更なし(理由: decisions の auth・env・sec・scope は認証・実行環境・隔離・記述粒度の決定であり、外部実行ファイルの同梱はどれにも触れない) |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | replace |
| 01 | docs/01-requirements/non-functional.md | new-features/01-requirements/non-functional.md | replace |
| 01 | docs/01-requirements/system.md | new-features/01-requirements/system.md | replace |
| 01 | docs/01-requirements/usecases.md | new-features/01-requirements/usecases.md | replace |
| 01 | docs/01-requirements/decisions/split.md | new-features/01-requirements/decisions/split.md | replace |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | replace |
| 02 | docs/02-design/architecture.md | new-features/02-design/architecture.md | replace |
| 02 | - | - | 変更なし(理由: relations.md と contracts の3本は機能間連携とモジュール間契約を扱い、Dockerfile はモジュールでない〈DSN-mod-05〉ため PLAN も CTR も動かない。environments.md はビルドコマンド文字列が変わらない〈`make build` のまま〉。logging.md は実行時の端末出力と常駐ログの規定でビルド時を扱わない) |
| 03 | docs/03-impl/environments/images.md | new-features/03-impl/environments/images.md | replace |
| 03 | docs/03-impl/infra/local/ghcr.md | new-features/03-impl/infra/local/ghcr.md | replace |
| 03 | docs/03-impl/tests/images.md | new-features/03-impl/tests/images.md | replace |
| 03 | docs/03-impl/tests/strategy.md | new-features/03-impl/tests/strategy.md | replace |
| 03 | docs/03-impl/index.md | -(§3-4 で版のみ更新) | 版のみ更新 |
| 03 | - | - | 変更なし(理由: relations/ と features.md と callgraphs/ は入口を持つ機能の鏡であり、Dockerfile はコールグラフに現れない〈DSN-mod-05〉。infra/local/docker-resources.md は起動時に作られる Docker 資源の一覧でイメージの中身を扱わない) |

## 読む範囲(読了記録)

- 全文読了: 2026-08-18
  - docs/00-requests/acceptances.md@1.4.1
  - docs/00-requests/decisions/auth.md@1.3.1
  - docs/00-requests/decisions/dist.md@1.2.0
  - docs/00-requests/decisions/env.md@1.5.1
  - docs/00-requests/decisions/scope.md@1.2.1
  - docs/00-requests/decisions/sec.md@1.3.1
  - docs/00-requests/request.md@1.4.0
  - docs/00-requests/terminology.md@1.5.0
  - docs/01-requirements/decisions/split.md@1.3.0
  - docs/01-requirements/functional.md@1.16.0
  - docs/01-requirements/non-functional.md@1.7.0
  - docs/01-requirements/system.md@1.2.1
  - docs/01-requirements/usecases.md@1.5.0
  - docs/02-design/architecture.md@1.5.0
  - docs/02-design/contracts/cli-container.md@1.11.0
  - docs/02-design/contracts/docker-api.md@1.1.0
  - docs/02-design/contracts/entrypoint-firewall.md@1.0.1
  - docs/02-design/environments.md@1.5.0
  - docs/02-design/logging.md@1.8.0
  - docs/02-design/relations.md@1.10.1
  - docs/02-design/system.md@2.12.0

## 決定シート(回答済み)

> 回答済み: sheet.md(転記済み)

- チャット回答(2026-08-18)「すべて推奨どおり」 — 対象: 一括(概念1〜3・論点1〜3 の全6ブロック。シートの「★あなたの記入」は空のまま)

| # | 論点 | 回答 | 反映先 |
|---|---|---|---|
| 概念1 | 語の外延 —「同梱外部バイナリ(externals)」 | 推奨を承認(含む = 保守者がビルド前に置いた、コンテナ内で利用者が直接実行する単一実行ファイル / 含まない = エージェント CLI・`scripts/` 配下の同梱スクリプト・設定/データファイル) | `docs/00-requests/terminology.md`(用語集の行)/ `FR-env-13`(`docs/01-requirements/functional.md`) |
| 概念2 | 範囲の境界 — 仕組みだけか colabtmux まで含むか | 推奨を承認(仕組み + `externals/` の骨格 + ドキュメントまで。`colabtmux` のバイナリ本体はコミットしない) | 未反映(理由: **このタスクの作業範囲の決定であって SSOT が持つ事実ではない**。SSOT は「保守者が置く」という恒久の事実だけを持ち〈`RQ-dist-02` / `D0-dist-05` 項1〉、「今回は置かない」はタスクとともに消える。除外範囲 = `colabtmux` のバイナリ本体の配置。本 memo.md「やること・やらないこと」が持つ) |
| 概念3 | 主体と権限 — 誰がいつ置くか | 推奨を承認(主体は**保守者**、操作はイメージビルドより前の手作業。開発者は触らない) | `docs/00-requests/request.md`「対象ユーザー」/ `docs/01-requirements/usecases.md`「シナリオ外要件」 |
| 論点1 | 新しい要求を立てるか `RQ-env-03` を広げるか | 推奨を承認(案 A = 新しい要求 `RQ-dist-02` を新設する) | `docs/00-requests/request.md`「やること」/ `docs/01-requirements/functional.md`「要求カバレッジ確認」 |
| 論点2 | リリース DoD に受入基準を1件足すか | 推奨を承認(案 A = `AC-07` を新設する) | `docs/00-requests/acceptances.md`(`AC-07`)/ `docs/01-requirements/usecases.md`(`AC ⇄ UC` カバレッジ) |
| 論点3 | `externals/` に置いてよいものの制約 | 推奨を承認(案 A = ①認証情報・秘密鍵・API キーを置かない ②公開配布してよいものに限る、の2条をガードレールにする) | `D0-dist-05`(`docs/00-requests/decisions/dist.md`)/ `docs/03-impl/infra/local/ghcr.md` |

**シート提示より前に人間が示した決定**(逐語引用+日付。**シートの論点への回答ではない**ので、
SH4 の転記行としては数えない — 意図して「チャット回答」の語を使っていない)

- 人間の発言(2026-08-18)「externals/というディレクトリをこのリポジトリに作り、私がバイナリファイルをそこにコピーする。externals/にあるファイルは全てコンテナイメージに書き込む」 — 対象: 取得経路 — 反映先: `D0-dist-05`(`docs/00-requests/decisions/dist.md`)
- 人間の発言(2026-08-18)「CI の公開イメージにも焼く」 — 対象: 公開範囲 — 反映先: `D0-dist-05`(`docs/00-requests/decisions/dist.md`)
- 人間の発言(2026-08-18)「arch サブディレクトリ併用」= `externals/` 直下のファイルは全アーキのイメージへ入る / `externals/amd64/` と `externals/arm64/` があればそのアーキのイメージにだけ追加で入る / `README.md` はコピー対象から除外する / 設置先は `/usr/local/bin` — 対象: アーキテクチャ差の扱い — 反映先: `FR-env-13`(`docs/01-requirements/functional.md`)と `docs/03-impl/environments/images.md`

## 未決点

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| - | 未決点なし(フェーズ2のドライランで洗い直す) | - | - |

## 調査メモ

| # | 調べたこと | 判明した事実 | 出どころ |
|---|---|---|---|
| 1 | `origin: human-report` の根拠 | 人間の依頼文そのもの: 「../colabtmux のツールをclaudeコンテナのイメージに追加したい。別リポジトリなので、Linux用のバイナリだけを取得して、パスの通っているところにおいてイメージを作るようにして欲しい」(2026-08-18) | 人間の依頼文(2026-08-18) |
| 2 | ビルド文脈に `externals/` が入るか | `docker build ... -f $(BASE_DIR)/.devcontainer/Dockerfile.claude $(BASE_DIR)` でビルド文脈はリポジトリルート。`.dockerignore` は存在しない。CI も `context: .` なので、**Makefile と CI ワークフローは変更不要** | `Makefile:140`〜`:158` / `.github/workflows/ghcr-images.yml:126` |
| 3 | CI のアーキ構成 | 3イメージ×2アーキ(amd64: `ubuntu-latest` / arm64: `ubuntu-24.04-arm`)をネイティブ runner で並行ビルドし push-by-digest する | `.github/workflows/ghcr-images.yml:99`〜`:150` |
| 4 | 配布ステージの位置 | `base`(`:11`)→ `vnc-base`(`:298`)→ 配布ステージ `claude-cli`(`:486`)/ `claude-vnc`(`:514`)。エージェント CLI は配布ステージの終端レイヤーに置く方針 | `.devcontainer/Dockerfile.claude:11,298,486,514` / `DSN-dist-01` |
| 5 | `unresolved_impact` を false とした根拠 | `relations-query.py --impact .devcontainer/Dockerfile.claude` は 0 件を返すが、これは欠落ではなく `DSN-mod-05`(Dockerfile と GitHub Actions はコールグラフに入口を持たないためモジュール分割定義から外し、`03-impl/environments/` と `03-impl/infra/local/` が記述を持つ)の帰結である。影響集合は閉じている | `docs/02-design/system.md:114`〜`:125` |
| 6 | `NFR-perf-02` の測定方法が課す制約 | ブラウザ確認ありイメージだけが持つ追加層に「ビルド済み成果物」が現れると**不合格**。ただし「同梱エージェント CLI の導入層は両イメージが等しく持つので (2) の対象外」と明記されている。externals も**両配布ステージへ等しく置く**ことでこの例外と同型になるが、条文はエージェント CLI しか名指していないため 01 側の文言を広げる必要がある | `docs/01-requirements/non-functional.md:23` |
| 7 | `SR-03` との関係 | `SR-03` が禁じるのは「認証情報(API キー・トークン・OAuth 資格情報)をイメージへ焼き込むこと」であり、実行ファイルの同梱は対象外。`NFR-sec-01` の4項目にも触れない | `docs/01-requirements/system.md:26` / `docs/01-requirements/non-functional.md:40` |
| 8 | `SR-24` との関係 | 「エージェント CLI の導入を配布ステージの終端レイヤーに置くこと」とあり、externals も同じ理由(更新時の再取得範囲の最小化)で終端に置く。条文はエージェント CLI しか名指していない | `docs/01-requirements/system.md:47` |
| 9 | colabtmux 側の配布状況 | `zettant/colabtmux` は private・タグ0件・リリース0件・`.github/workflows/` 無し。クロスビルドは `scripts/build-all.sh` が `linux/amd64` `linux/arm64` `darwin/arm64` を `dist/` へ出す | `gh api repos/zettant/colabtmux` / `../colabtmux/scripts/build-all.sh` |
| 10 | 本リポジトリの公開状況 | `quvox/claude-dev-env` は public。イメージは `ghcr.io/quvox/claude-dev-claude(-vnc)` へ push される。CI は `actions/checkout` したツリーをビルド文脈にするため、公開イメージへ焼くなら `externals/` の中身は git にコミットされる必要がある | `gh api repos/quvox/claude-dev-env` / `.github/workflows/ghcr-images.yml:150` |
| 11 | closure 内 SSOT の検証済み記録 | closure に挙げた 15 ファイルすべてで `verified.version` が現在の MAJOR.MINOR と一致しており、有効である(原則6) | 各ファイルの frontmatter |
| 12 | 部分充足の条項への依存 | 02 のカバレッジ表で `部分(P-005)` なのは `FR-env-01-19` と `FR-env-07-5`(compose 資源の一意化)の2条項だけ。本タスクは compose 資源にも命名にも触れないため、この2条項に依存しない | `docs/02-design/system.md:193,264` / `docs/pendings.md` P-005 |
| 13 | 解消できる pending / issue | 無し。issues 12 件はいずれもホスト CLI・docker-proxy・キット由来で、イメージへの外部実行ファイル同梱に関係しない。P-001〜P-007 の解消条件も、いずれも本タスクでは発火しない(P-002 = 開発者増または Go 以外の自動テスト増、P-003 = QA レーン開始、P-004 = 認証の共有運用、P-005 = 数百プロジェクト規模、P-006 = 専有ホストか macOS 機、P-007 = 利用範囲が SR-05 を超える) | `docs/issues/index.md` / `docs/pendings.md` |
| 14 | 再検証候補との重なり | `docs/reverification.md` の8件のうち `docs/03-impl/environments/images.md`(上流 `02-design/environments.md` 1.4.0 → 1.5.0)が closure に入る。本タスクの降下で読み直す | `docs/reverification.md` |
| 15 | 走らせるべきテスト(DoD の種) | `relations-query.py --impact` は Dockerfile について 0 件を返す(調査メモ 5)。イメージの検証は `docs/03-impl/tests/images.md` の受入基準 ⇄ テスト対応表が担い、既存行はすべて `未検証(テスト未実装)`。実機確認の手段は `docker run --rm <image> which colabtmux` 相当になる見込み | `docs/03-impl/tests/images.md:22`〜`:37` |
| 17 | コンテナ内の利用者の権限 | 非 root ユーザーに `NOPASSWD:ALL` の sudo が与えられている。したがって 0755・`root:root` が保証するのは**非特権の操作では書き換わらない**ことまでで、「書き換えられない」とは書けない | `.devcontainer/Dockerfile.claude:106` |
| 18 | アーキテクチャ判定の既存の流儀 | この Dockerfile は `dpkg --print-architecture` を5箇所(apt のリポジトリ定義2件・Go・Terraform・GUI ブラウザの分岐)で使っている。返す語彙は `amd64` / `arm64` で、`externals/` のサブディレクトリ名として使える | `.devcontainer/Dockerfile.claude:71,78,129,173,328` |
| 19 | 配布ステージの末尾の状態 | `claude-cli` / `claude-vnc` はどちらも `USER root` のまま codex 共通ランチャーを作る `RUN` で終わる。設置処理を末尾へ足せば root で走り、最終レイヤーになる | `.devcontainer/Dockerfile.claude:486`〜`:541` |
| 20 | GHCR パッケージの可視性 | `quvox` の3パッケージ(`claude-dev-claude` / `-claude-vnc` / `-docker-proxy`)すべてで、匿名トークンによる `tags/list` が **200** を返す。`ghcr.md` の「組織内」という記述は事実と違っていた | 2026-08-18 の実測(`ghcr.io/token` → `tags/list`) |
| 21 | `.gitignore` と `externals/` | 現行の9パターンのいずれも `externals` にも `externals/README.md` にもマッチしない。`.gitignore` の変更は不要 | `.gitignore` |
| 22 | `tests/strategy.md` の集計値 | 「機能要件の全 141 条項に行がある(…対応表は 151 行)」と書かれており、`FR-env-13` の6条項を足すと **147 条項 / 157 行**になる。この文書を closure へ入れて直す必要がある | `docs/03-impl/tests/strategy.md:102` |
| 16 | 仕様ドキュメントの一括検査(母集団の凍結) | `python3 .claude/scripts/check-changeset.py --ssot docs` = 125 ファイル。CS8 / CS11 / CS12 / CS18 / CS19 は OK、**CS20 が 9 件違反**(issues の `origin_layer` 欠落。いずれも本タスクより前から在り、`docs/pendings.md` の残務が追跡している)。変更相対語の候補5件はいずれも既存の正当な用法 | `check-changeset.py --ssot docs`(2026-08-18 実行) |

## 質問キュー(未提示)

| # | 論点 | 何が止まるか | 推奨する回答(暫定) |
|---|---|---|---|
| - | なし(フェーズ1のシートへ3件を載せた) | - | - |

## タスクリスト

- [x] 1. `externals/` の骨格を作る(`externals/README.md`。規約の案内 + ディレクトリを git に残す役目) _要件:_ FR-env-13-1 _Boundary:_ `externals/` _Depends:_ -
- [x] 2. 配布ステージ2つ(`claude-cli` / `claude-vnc`)の**最終レイヤー**へ設置処理を足す _要件:_ FR-env-13-1〜6 _Boundary:_ `.devcontainer/Dockerfile.claude` _Depends:_ 1
- [x] 3. 実機確認(`03-impl/tests/images.md` 手順16〜21)を実行する _要件:_ FR-env-13-1〜6 / AC-07 _Boundary:_ 検証のみ(確認用の実行物はコミットしない) _Depends:_ 2

## Definition of Done

- [x] lint が通る: `cd docker-proxy && go vet ./...`
- [x] 単体・結合テストが通る: `cd docker-proxy && go test ./...`
- [x] 受入基準のテストが全て存在し通る(`FR-env-13-1`〜`-6` は自動テストを持たない領域なので `未検証(テスト未実装)` を意図して残す。実機確認が代替する)
- [x] 影響する E2E シナリオが通る: **適用外**(`FR-env-13` は `UC` を持たない)
- [x] `03-impl/tests/images.md` 手順16〜21 がすべて合格する(`AC-07` の実機確認)
- [x] コールグラフを再生成し、`callgraph-check.py --to-be task-bundle-external-binaries` の重大度「高」が0
- [x] `check-relations.py` が合格
- [ ] `new-features/` の全変更指示を SSOT へ反映済み(**`/task-close` で実施**)
- [x] `/doc-check` が影響範囲を PASS(フェーズ2で取得)
- [ ] `docs/histories/` に記録(**`/task-close` で実施**)
- [x] 見つけた範囲外の問題を `docs/issues/` / `docs/pendings.md` に記録済み

**2026-08-18 に全項目を実行して確認した(コミット前の作業ツリー。`git rev-parse HEAD` = `9549d6396bf2549f06f4b14adc570184ea42631c`)。**

| # | 項目 | コマンド | 最終出力(逐語) | 判定 |
|---|---|---|---|---|
| 1 | lint | `cd docker-proxy && go vet ./...` | (出力なし。終了コード 0) | 合格 |
| 2 | 単体・結合テスト | `cd docker-proxy && go test ./...` | `ok  	github.com/quvox/claude-dev-env/docker-proxy	0.061s` | 合格 |
| 3 | 受入基準のテストが全て存在し通る | (対応表の確認) | `FR-env-13-1`〜`-6` の6行はすべて `未検証(テスト未実装)` = **自動テストを持たない**(`DSN-test-01` / `SR-32` の既定。未検証行は重大度「高」だが PASS を妨げない)。実機確認は #5 が担う | 合格(未検証行を意図して残す) |
| 4 | 影響する E2E シナリオ | — | **適用外**(`FR-env-13` は `UC` を持たず、02 の E2E シナリオ一覧に対応項目が無い) | 適用外 |
| 5 | `03-impl/tests/images.md` 手順16〜21 | 各手順のコマンド(下の実測を参照) | 手順16 `cdx-externals-probe-ok` rc=0(両イメージ)/ 手順17 `-rwxr-xr-x 1 root root` + 非特権書き込み rc=2(両イメージ)/ 手順18 共通 rc=0・amd64 rc=0・arm64 rc=127 / 手順19 ビルド rc=0・`README.md` 設置 rc=2 / 手順20 ビルド rc=0・警告0行 / 手順21 ビルド rc=2(`exit code: 123`) | **6件すべて合格** |
| 6 | コールグラフ再生成 + `callgraph-check.py --to-be` 高0 | `build-callgraphs.py --out <staged>` → `callgraph-check.py --to-be task-bundle-external-binaries` | 重大度「高」0 件(中3 / 低9 / 参考12 はいずれも本タスク以前からのもの) | 合格 |
| 7 | `check-relations.py` | `python3 .claude/scripts/check-relations.py` | `合格: 対称性・参照実在・impl パス・必須項目・機能表との 1:1すべて問題なし。` | 合格 |
| 8 | `new-features/` の全変更指示を SSOT へ反映 | — | — | **`/task-close` で実施** |
| 9 | `/doc-check` が影響範囲を PASS | — | フェーズ2 で PASS 済み(反復 2/2、独立レビュー Codex ×2) | 合格 |
| 10 | `docs/histories/` に記録 | — | — | **`/task-close` で実施** |
| 11 | 範囲外の問題を issues / pendings へ記録 | — | `docs/pendings.md` へ残務2件(テスト状態列の語彙 / `DSN-dist-01` の見出し)。issue の起票は無し(いずれもバグでも DoD 阻害でもない) | 合格 |

**実測の補足(AC-07 の実物での確認)**: 人間が置いた `externals/amd64/colabtmux` と
`externals/arm64/colabtmux` を使い、amd64 の配布イメージ2種で
`/usr/local/bin/colabtmux`(`-rwxr-xr-x 1 root root 8577289`)が `colabtmux` の名前だけで起動し、
使い方が表示されることを確認した。**arm64 用は amd64 のイメージに入っていない。**

**確認用の実行物は残していない**: `cdx-externals-probe*` は確認後にすべて削除し、
`externals/` は `README.md` + `amd64/colabtmux` + `arm64/colabtmux` の状態でイメージを作り直した
(両イメージで `cdx-externals-probe` の残存 0 件を確認済み)。
一時的に差し替えた `.devcontainer/Dockerfile.claude` も原状へ復元した(`diff` で一致を確認)。

## 進捗メモ

- 2026-08-18 フェーズ1: 00〜02 を全文読了(critical レーン)。影響範囲を確定し、決定シートを提示した。
- 2026-08-18 フェーズ3 完了: タスク1〜3 をすべて実施。`externals/README.md` を新設し、`.devcontainer/Dockerfile.claude` の配布ステージ2つ(`claude-cli` / `claude-vnc`)の最終レイヤーへ `COPY externals/ /tmp/externals/` + 設置の `RUN` を足した。**DoD 11 項目を実際に実行して記録した(上の表)**。実機確認の手順16〜21 は6件すべて合格し、**人間が置いた `colabtmux` の実物でも両イメージで起動を確認**した。フェーズ3で下した委任判断は無い(フェーズ2で決めた形をそのまま実装した) — [DS-nn] の新規行なし。**コミットはしていない**(規範上の要件ではなく、公開リポジトリへ非公開由来のバイナリを載せる操作なので人間の判断に委ねる)。
- 2026-08-18 **/doc-check(task) 判定: PASS(ブロッキング 0 件)**。反復 2/2。実行形態: 著者のセッション内(サブエージェントの起動は本セッションの制約で不可のため。`/doc-check` §0A の「どちらも不可なら著者のセッションで走らせ、その旨を報告に書く」経路)。**独立レビュー: Codex(`gpt-5.6-sol` / high)を2回** — 1回目は全体、2回目は改訂で新しく下した判断だけに絞った再監査。どちらも作業ツリーへの書き込みなし(`git status --porcelain` の前後一致で確認)。
  - 変更指示のハッシュ(全14ファイルの md5 の md5): `a28ca1a30bd43a853d24a1c22e5e68b9`
  - closure の版: 読了記録のとおり(00〜02 の21ファイル)。SSOT は本タスク中に動いていない
  - 修正の区分 — **MINOR**(意味変更): `NFR-perf-01` の目標値の条件 / `FR-env-13-2` の「非特権の操作では」への限定と具体値の 03 への移動 / `AC-07` の操作を保守者完結へ / `D1-split-01` の不可分の射程 / `DSN-dist-01` の射程拡大 / アーキ判定を `TARGETARCH` から `dpkg --print-architecture` へ / 実機確認手順の全面書き換え(`--entrypoint` 迂回・両イメージ・前提の是正) / `tests/strategy.md` を closure へ追加。**PATCH**(意味保存): 充足の4値を `適用外(理由)` へ訂正 / GHCR の3パッケージ確認の記述 / `dpkg` の使用箇所の内訳 / `usecases.md` の未対応理由の言い換え / `images.md` の設置節を `###` から独立した `##` へ
  - 変更指示の総バイト: 入場時 119,523 → 131,985(**+12,462**)。増えた理由は、偽の記述を直すために事実の追記が要ったこと(ENTRYPOINT が引数を実行しないという但し書き、両イメージ分の観測、アーキ片側確認の限界の明記)と、closure へ `tests/strategy.md` の指示を1本足したこと。**言い換えの追加ではない**
  - 最弱点: `FR-env-13-3` の実機確認が amd64 側のビルド1つで完結するため、**実装がアーキテクチャ名を固定していた場合はこの手順では検出できない**。手順18 にその限界を明記してあり、arm64 をビルドできる環境が使えるようになったときに塞ぐ
- 2026-08-18 フェーズ2: 03 完了(environments/images.md / infra/local/ghcr.md / tests/images.md の3本)。降下は 00→03 の1回で終了。
- 2026-08-18 フェーズ2: 02 完了(system.md / architecture.md の2本)。
- 2026-08-18 フェーズ2: 01 完了(functional.md / non-functional.md / system.md / usecases.md / decisions/split.md の5本)。
- 2026-08-18 フェーズ2: 00 完了(request.md / decisions/dist.md / acceptances.md / terminology.md の4本)。
- 2026-08-18 標準委任の行使(8件。開示先は各変更指示):
  - [DS-04] 同梱外部バイナリの権限を 0755・所有者 `root:root` にする — 理由: `FR-env-13-2` が求める「実行でき、非特権の操作では書き換えられない」を満たす最小の権限で、`/usr/local/bin` の既存の同梱物と同じ扱い / 見直す条件: 利用者が書き換える前提の資産を同梱したくなったとき(記録先: `new-features/03-impl/environments/images.md`。**独立レビューの指摘を受けて 01 から 03 へ移した** — 具体値は実現方法であり、01 が持つのは観測できる形だけ)
  - [DS-02] `externals/` が空でもビルドを失敗させない — 理由: 同梱は任意の仕組みで、何も置かれていない状態が初期状態である / 見直す条件: 特定の同梱物を要件が必須と定めたとき(記録先: 同上 `FR-env-13-4`)
  - [DS-02] 片方のアーキテクチャ向けだけが在るとき、もう一方のビルドを失敗も警告もさせない — 理由: 使うアーキテクチャが1つに限られる運用を仕様として認めるため / 見直す条件: 全アーキに同じ同梱物が入っていることを要件が求めるようになったとき(記録先: 同上 `FR-env-13-5`)
  - [DS-02] 設置に失敗したらビルドを失敗させる — 理由: 欠けたイメージが公開されると利用者は原因に到達できず、公開したものは回収できない / 見直す条件: 同梱物が任意であることを利用者が実行時に判別できる手段ができたとき(記録先: 同上 `FR-env-13-6`)
  - [DS-05] 設置層をエージェント CLI の導入層より後ろの最終レイヤーに置く — 理由: `DSN-dist-01` の一般原則の適用。前に置くと差し替えのたびに CLI 層が失効する / 見直す条件: 同梱物が CLI の動作に必要になったとき(記録先: `new-features/03-impl/environments/images.md`)
  - [DS-05] 設置を両方の終端ステージへ等しく行い、中間ステージへ共通化しない — 理由: 片側だけだと `NFR-perf-02` の不合格条件に当たり、中間ステージは終端配置の意味を失う / 見直す条件: ブラウザ確認ありのイメージにだけ同梱したいものが出てきたとき(記録先: 同上)
  - [DS-06] アーキテクチャの判定に `dpkg --print-architecture` を使い、BuildKit の自動 ARG `TARGETARCH` を使わない — 理由: この Dockerfile が既に5箇所で使っている値で語彙も一致し、レガシービルダーでも空にならない / 見直す条件: `dpkg` を持たないベースイメージへ移ったとき(記録先: `new-features/03-impl/environments/images.md`)
  - [DS-01] 観測点を「確認用の実行物を実際に実行し、固定の出力と終了コードを見る」ことにする — 理由: 存在と権限だけでは壊れた実行形式や別アーキのバイナリでも通過し、「起動できる」を検証しない / 見直す条件: 同梱物を実行せずに起動可否を判定できる手段ができたとき(記録先: `new-features/03-impl/tests/images.md`)
  - [DS-01] 確認に使う実行物はその場で作り、コミットせず、確認後に消す — 理由: 確認用のファイルをコミットすると意図しないものが公開イメージへ焼かれる / 見直す条件: 常設の同梱物ができ回帰確認したくなったとき(記録先: 同上)
  - [DS-01] `FR-env-13-3` の確認を1つのアーキテクチャのビルドだけで両方向とも行う — 理由: 「用意したものが入る」と「用意していないものが入らない」は1アーキのイメージで同時に観測でき、機材待ちで手順が実施されないまま残るのを避けられる / 見直す条件: ビルドした側のイメージから判定結果を観測できなくなったとき(記録先: 同上)
- 2026-08-18 フェーズ1 完了: 人間が「すべて推奨どおり」(2026-08-18)で全6ブロックを一括承認。転記済み。`phase: ドキュメント` へ進めた。人間から「問題がなければ止まることなく close まで実施」の指示を受けたため、フェーズ2〜4 を連続実行する。

## 申し送り事項

- **切り戻しの難所**: 公開 GHCR へ push したイメージは回収できない(`irreversible_data: true` の根拠)。切り戻しは「次の日次ビルドで `externals/` を空にする」しかなく、既に pull された分は戻らない。フェーズ2 の変更指示でこの点を明記し、フェーズ4 で実測結果を履歴へ書く。
- **`origin: human-report` の帰着**: `close-task.py` 条件 (g) が知見の行き先(`D0-*` / `docs/feedbacks/` / 「今回限り(理由)」)を履歴に要求する。
