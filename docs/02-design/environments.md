---
id: environments
version: 1.3.0
updated: 2026-08-08
source:
  - docs/01-requirements/system.md
  - docs/02-design/architecture.md
summary: 開発環境の構成・セットアップ手順・lint/テスト/ドキュメント整合検査の厳密なコマンド文字列・Codex実行設定
keywords: [開発環境, コマンド, lint, テスト, Codex]
verified:
  at: 2026-08-08
  version: 1.3.0
  against:
    - doc: docs/01-requirements/system.md
      version: 1.1.0
    - doc: docs/02-design/architecture.md
      version: 1.4.0
---

<!-- 2026-08-04 /doc-check ssot task-impl-depth(新しい実行): **合格証を再発行した(1.0.0)。**
     直前に削除した理由(source の docs/02-design/architecture.md が未検証 = docs/issues/040 の高)は、
     人間が案A(実装が正)で裁定し architecture.md 1.2.0 が再認証されたことで解消した。
     本文には問題を見つけていない。
     残る「中」: 「Codex実行設定」のモデル・reasoning 行がプレースホルダ「未定」のままで、
     docs/pendings.md P-003 の記述と食い違う(docs/issues/031)。**本実行でもこの行を「不在」と
     扱い規範の既定(gpt-5.6-terra / max)を明示指定した。**
     ★本実行の独立監査は起動できなかった(Codex がアカウントの利用上限に達し 2026-08-10 まで復旧しない)。
     これはツールの問題で本文の欠陥ではないが、合格証は Claude 単独の検証に基づく。 -->

# 開発環境・開発ツールの基本設計

## セットアップ手順

1. リポジトリを取得する。
2. `make setup` を実行する(`.env` の作成 → ネットワーク作成 → 共有ボリューム作成 →
   イメージのビルド → CLI の導入 の順に進む)。
3. `make login` で Claude の認証を済ませる。Codex を使う場合は `claude-dev login-codex` も実行する。
4. 任意のプロジェクトディレクトリで `claude-dev start` を実行する。

| 用途 | コマンド |
|---|---|
| セットアップ | `make setup` |
| CLI の導入 / 除去 | `make install` / `make uninstall` |
| 認証(Claude) | `make login` |
| 認証(Codex) | `claude-dev login-codex` |
| 配布イメージの取得 | `claude-dev pull` |
| 自己検証題材の配置 / 初期化 | `make orch-sample` / `make orch-sample-clean` |
| 状態の確認 | `make status` |

## lint・テストコマンド

| 用途 | コマンド | 備考 |
|---|---|---|
| lint | `go vet ./...` | 各 Go モジュール(`docker-proxy/` と `orchestrator/`)のディレクトリで実行する。**Bash には自動 lint を設けていない**(`SR-32`) |
| 単体テスト(docker-proxy) | `cd docker-proxy && go test ./...` | プロキシの検査ロジック |
| 単体テスト(orchestrator) | `cd orchestrator && go test -mod=vendor ./...` | 制御ループ・状態・レビュー・プロンプト生成など |
| 単体テスト(自己検証題材) | `cd examples/orch-sample && pytest` | 題材プロジェクト |
| カバレッジ計測(docker-proxy) | `cd docker-proxy && go test -cover ./...` | テスト戦略が参照する計測手段(`03-impl/tests/strategy.md`)。合否の条件は課さない |
| 結合テスト | 上記2つの `go test` に含まれる | 契約ごとの責任モジュールは `system.md`「結合テスト対象」が正。シェル側の契約は実機確認 |
| E2Eテスト | 自動テストランナーは無い。`make orch-sample` で題材を配置し `claude-dev orchestrate` で実走する | シェル系 E2E(E2E-01〜03)は実機確認。手順は `03-impl/tests/e2e.md` |
| build | `make build` | `claude`(ブラウザ確認なし)+ `claude-vnc` + `docker-proxy` を一括ビルド |
| build(個別) | `make build-claude` / `make build-claude-vnc` / `make build-docker-proxy` / `make build-orchestrator` | `claude-vnc` はベースに続けてビルドする |
| 再ビルド(キャッシュ無し) | `make upgrade` | 全イメージを作り直す |

## コンテナ・実行環境

| サービス | イメージ・起動方法 | ポート | 依存 |
|---|---|---|---|
| Claude コンテナ(ブラウザ確認あり) | `claude-dev-claude-vnc`。`claude-dev start` で起動 | noVNC のみ 6080 番台から動的割当 | 共有ネットワーク、共有ボリューム3本 |
| Claude コンテナ(なし) | `claude-dev-claude`。`claude-dev start --no-vnc` | 公開しない | 同上 |
| docker-proxy | `claude-dev-docker-proxy`。最初のコンテナ起動時に自動で立つ | 共有ネットワーク内のみ(ホストへ公開しない) | ホストの Docker ソケット |
| forward プロキシ | `claude-dev forward <port>` で都度起動 | ホスト側 8100 番台から動的割当 | 対象の Claude コンテナ |
| ゲスト VM(任意) | `claude-dev start --vm` | ゲスト内で完結。必要なポートはホストの 127.0.0.1 へ同期 | `/dev/kvm` |

- 実行環境の前提は `01-requirements/system.md`(`SR-10`〜`SR-15`)が正。
- ネットワーク名・ボリューム名・命名規則といった具体的な構成値は `03-impl/infra/local/` が正。
- **クライアント PC からの到達手順**: `claude-dev forward` が割り当てるのは**サーバ(ホスト)側の
  ポート**であり、クライアント PC からはそこへ **SSH トンネル**を張って到達する
  (`claude-dev forward` はそのコマンドを表示する)。**SSH の ControlMaster による接続の多重化を
  前提とする** — 転送のたびに認証をやり直さずに済ませるためである。**macOS ではポートが直結の
  ため、この手順は不要である**(`FR-env-10` 受入基準2)。

## CI

| タイミング | 実行内容 | 失敗したらどうなるか |
|---|---|---|
| 日次 03:30 JST | エージェント CLI のバージョン解決 → マルチアーキ(amd64/arm64)でイメージをビルド → GHCR へ push(タイムスタンプタグ + `latest`) | その日の配布イメージが更新されない(前日のイメージは残る) |
| 手動実行 | 上と同じ。エージェント CLI のバージョンを入力で指定できる | 切り戻しができない |
| PR / 変更時 | **自動化されていない(未定)**。`go vet` と `go test` は手元で実行する運用 | — |

**未定(いつ決めるか)**: PR での自動テスト実行は導入していない。Go の2モジュールに閉じた検査
なので CI 化の障壁は低いが、導入時期は未定(`docs/pendings.md` で管理する)。

## ドキュメント整合検査コマンド

仕様ドキュメントが互いに整合しているかを機械検査する。**この順で実行し、すべて合格して初めて
ドキュメントが整合しているとみなす。**

| # | 用途 | コマンド | 合格条件 |
|---|---|---|---|
| 0 | 生成先の解決(1・2 の前に1回) | `CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py)` | 出力先のパスを返す(終了コード 0)。**出力先を自分で決めてはならない**(進行中タスクがあるときはタスク配下、無ければ `docs/03-impl/callgraphs/` を返す) |
| 1 | コールグラフの鮮度 | `python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT" --check` | 「最新」を返す(終了コード 0)。古い場合は `--out "$CG_OUT"` を付けたまま `--check` を外して再生成してから 2 以降をやり直す |
| 2 | 機能間関係グラフの鮮度 | `python3 .claude/scripts/cluster-features.py --out "$CG_OUT" --check` | 「最新」を返す(終了コード 0)。古い場合は `--out "$CG_OUT"` を付けたまま `--check` を外して再生成してから 3 以降をやり直す |
| 3 | コールグラフ ⇄ 機能表 ⇄ 機能間連携仕様書 | `python3 .claude/scripts/callgraph-check.py` | 重大度「高」が 0 件(終了コード 0)。**中・低・参考は残ってよい**(残っている件数と内訳の正は `03-impl/index.md`「この層の状態」である) |
| 4 | 機能間連携仕様書の内部整合 | `python3 .claude/scripts/check-relations.py` | 「合格」と表示され終了コード 0 |
| 5 | 契約(02 ⇄ 03 ⇄ コード) | `python3 .claude/scripts/check-contracts.py` | 重大度「高」が 0 件(終了コード 0)。REST API を持たないため CT1〜CT3 は該当なし |
| 6 | コードとドキュメントの片側漏れ | `python3 .claude/scripts/relations-coverage.py` | 片側にしか無いものが、**既知の誤検出を除いて** 0 件。**既知の誤検出の内訳と件数は `03-impl/index.md`「`relations-coverage.py` 最終結果」が正である**(このスクリプトは終了コード 1 を返し続ける) |
| 7 | 目次・進捗の再生成 | `python3 .claude/scripts/build-index.py --check` | 差分なし。差分がある場合は引数なしで再生成する |
| 8 | 構造の健全性(**モジュール間・機能間の循環の有無**) | `python3 .claude/scripts/relations-query.py --health` | 循環が 0 件(終了コード 0)。**`02-design/relations.md` の `PLAN-cli-common-*` が「循環しない」と課している期待を、この検査が担保する** |

- **前提**: `python3 .claude/scripts/setup-tools.py` を1回実行してキット専用の実行環境
  (`.claude/.venv`)を用意しておくこと。**プロジェクトの環境には入れない。**
- 実行位置はリポジトリルート。いずれのスクリプトも書き込むのは生成物(`--check` を外したとき)だけで、
  仕様ドキュメント本文は書き換えない。
- 作業中のタスクの変更指示を合成して検査したいときは `3` に `--to-be <task-slug>` を付ける
  (未実装のシンボルをエラーにしない)。`4`〜`6` と `8` は合成ビューに対応しないため、SSOT へ反映した後に
  実行する。

## コールグラフ抽出設定

| 項目 | 値 |
|---|---|
| internal_roots | リポジトリルート(`claude-dev` / `claude-dev-mac` / `scripts/` / `Makefile` / `orchestrator/` / `docker-proxy/` / `examples/orch-sample/`) |
| 有効な言語 | shell / make / go / python / typescript / infra |
| 抽出器が無い言語 | **Dockerfile と GitHub Actions**。この2つはコールグラフに現れないため、モジュール分割定義から外し `03-impl/environments/` と `03-impl/infra/local/` が記述を持つ(`DSN-mod-05`) |
| Tier | shell=3 / make=3 / go=2 / python=2 / typescript=2 / infra=2 |
| ツール環境 | `.claude/.venv`(キット専用。**プロジェクトの環境には入れない**) |
| 用意するコマンド | `python3 .claude/scripts/setup-tools.py` |
| 除外するパス | `orchestrator/vendor/` / `workspace/` / `tmp/` / `.orchestrator/` / `scripts/e2e6-codex.sh`(E2E の実機検証スクリプトであり、機能ではなく検証手段のため。決定シート2 論点9) |
| 出力先 | `docs/03-impl/callgraphs/` |
| 鮮度検査 | `python3 .claude/scripts/build-callgraphs.py --out "$(python3 .claude/scripts/resolve-callgraph-out.py)" --check` |
| CI で検査するか | いいえ(未定。PR での自動実行を導入する際に併せて決める) |

## Codex実行設定

| 項目 | 値 |
|---|---|
| Codex連携 | 有効(Claude コンテナに同梱。`codex` は PATH 上。認証は共有ボリューム経由) |
| ドキュメント監査 | 有効 |
| QA(E2E + CDP探索) | 無効(未運用。開始時期は未定) |
| フロントエンド | CLI(`codex exec`)。MCP サーバは登録していない |
| 監査の経路 | (a) scoped(スコープ渡し)。添付方式は予備 |
| コマンド | `codex` |
| **必須フラグ** | **監査・QA で codex を呼ぶときは常に `-c features.use_legacy_landlock=true` を付ける** |
| プロファイル | 未定(`docs-audit` / `qa` は未作成。codex 既定設定で走らせる) |
| モデル・reasoning(増分監査) | 未定(いつ決めるか: `docs/issues/031`。**未記入の行は不在として扱われ、キットの既定が効く**) |
| モデル・reasoning(full監査) | 未定(同上) |
| モデル・reasoning(QA) | 未定(QA レーン開始時に決める) |
| 代替レビュー(サブエージェント)のモデル・reasoning | 未定(**未記入なのでキットの既定が効く**。この行を埋めればレンズを常設指名できる) |
| タイムアウト / 最大出力 | 監査 900 秒 / QA 未定。最大出力は未定 |
| 最大調査ステップ | 未定 |
| 書き込み許可ディレクトリ | 未定(QA レーンが未運用のため) |
| CDP エンドポイント | `http://localhost:9222`(コンテナ内 Chrome) |
| QA シードコマンド | 未定(QA レーン開始時に決める) |
| QA リセットコマンド | 未定(同上) |
| ブラウザ排他ロック | 未定(同上。`docs/pendings.md` P-003 で追跡。**QA レーン開始の前提条件**) |
| Claude のシェルからの到達方法 | コンテナ内 CLI(同一コンテナ内で `codex` を直接呼ぶ) |
| 証跡の保管場所と保持期間 | スクラッチパッドのみ(永続化しない) |
| full 最終監査で「中」が PASS をブロックするか | いいえ |
| CDP 探索を必須にする変更範囲 | 未定(QA レーンが未運用) |
| 段階導入フェーズ | 1 観測モード |

**必須フラグの理由**: このコンテナでは codex 既定の bubblewrap サンドボックスが起動できない
(seccomp が `CLONE_NEWUSER` を拒否し、AppArmor が `mount --make-rslave /` を拒否する。
`DSN-dist-02`)。legacy landlock バックエンドはユーザー名前空間を使わないため、コンテナの
confinement を緩めずに動く。**付け忘れると読み取りコマンドがすべて失敗するが `codex exec` の
終了コードは 0 のまま**なので、成否は終了コードではなく最終メッセージと成果物で判定する。

**サンドボックス疎通確認**: `codex sandbox --enable use_legacy_landlock -- /bin/true` が exit 0、
かつ `codex sandbox --enable use_legacy_landlock -- /bin/sh -c 'touch /tmp/x'` が失敗すること。
フラグ無しの `codex sandbox -- /bin/true` は exit 1(bubblewrap)で、これは既知・正常。
`codex doctor` はこの故障を検知しない。

**監査での禁止事項**: 監査(`docs` / `readiness` / `diff`)では承認・サンドボックスを迂回する
フラグを使わない(read-only + landlock で足りる)。**QA レーンのみ例外**として
`-c sandbox_mode="danger-full-access"` で走らせる(landlock 経路では書き込みが成立しないため。
「コンテナ自体が隔離空間であり、これ以上の隔離は不要」という `D0-sec-06` の一貫適用。
2026-07-31 の人間判断)。QA の他の制約(専用シード・ブラウザ排他・テスト成果物ディレクトリ以外を
書かない・終了時にリセット)はそのまま守る。git 未初期化のリポジトリでは `--skip-git-repo-check`
を付ける(これは迂回ではない)。

**イメージ更新時の注意**: `use_legacy_landlock` は codex 0.146.0 時点で deprecated(起動時に
撤去予告が出る)。同梱バージョンはビルド時に最新へ解決されるため、イメージを更新したら上記の
疎通確認を再実行する。撤去された場合の退避先は添付方式。

## 将来設定(運用開始時に決めるもの・未解決事項ではない)

**上表の「未定」の帰着**: 「未定」と書いてある項目(PR での CI 自動実行、Codex のプロファイル名・
モデル・QA レーンの各設定)は、いずれも**まだ運用していない機能の設定値**であり、
「まだ誰も決めていない要確認事項」ではない。したがって未解決事項には数えず、下流の検証を
ブロックしない。運用を始める時点で決めるものとして `docs/pendings.md`(**P-002** = PR での CI 自動実行 /
**P-003** = QA レーンの各設定)で追跡する。決めた時点でこの文書の該当行を「未定」から実値へ
置き換える(MINOR 変更)。

## 未解決事項

- なし。
