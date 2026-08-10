---
target: docs/02-design/environments.md
change: replace
version_bump: minor
sections:
  - "## セットアップ手順"
  - "## lint・テストコマンド"
  - "## CI"
  - "## コールグラフ抽出設定"
deletes: []
reason: 'オーケストレーターの全面削除にともなう開発環境・コマンドの整理(決定シート 概念1・論点4)。**この文書の lint / テストコマンドは実行される厳密な文字列なので、消えるモジュールを指したままにできない**(CLAUDE.md §9)。(1) セットアップ手順の表から「自己検証題材の配置 / 初期化 = `make orch-sample` / `make orch-sample-clean`」の行を削除する(7 行 → 6 行)。(2) lint・テストコマンドの表から 3 行を削除する: 単体テスト(orchestrator)= `cd orchestrator && go test -mod=vendor ./...` / 単体テスト(自己検証題材)= `cd examples/orch-sample && pytest` / build(個別)の `make build-orchestrator`。lint の備考を「各 Go モジュール(`docker-proxy/` と `orchestrator/`)のディレクトリで実行する」から「`docker-proxy/` のディレクトリで実行する」へ、結合テストを「上記2つの `go test` に含まれる」から「上記の `go test` に含まれる」へ、E2E テストを「`make orch-sample` で題材を配置し `claude-dev orchestrate` で実走する」から「実機で `claude-dev` を操作する」へ改める。**`docker-proxy` の単体テストとカバレッジ計測・`make build` 系・`make upgrade` は変えない**。(3) CI の「Go の2モジュールに閉じた検査」を「docker-proxy に閉じた検査」へ改める(日次ビルドと手動実行の行は変えない)。(4) コールグラフ抽出設定の `internal_roots` から `orchestrator/` と `examples/orch-sample/` を外し、`除外するパス` から `orchestrator/vendor/` と `.orchestrator/` を外す(どちらのディレクトリも消えるため、除外を残すと実在しないパスの設定になる)。**`workspace/` / `tmp/` / `scripts/e2e6-codex.sh` の除外は残す**(`docs/pendings.md` P-001 が `e2e6-codex.sh` の除外を追跡している)。**有効な言語・Tier・ツール環境・出力先・鮮度検査・CI で検査するかは変えない**。(4-2) `## CI` の「PR / 変更時」の行と直後の段落から未決点の書き方(「未定」)を外し、棚上げの追跡先が `docs/pendings.md` P-002 であることを明示する(**判断は変えていない** — 導入しないという棚上げのままである。`CS8` が「未決点が仕様に残っている」と読む書き方を、pendings を指す書き方へ改めただけ)。(5) `## ドキュメント整合検査コマンド` / `## コンテナ・実行環境` / `## Codex実行設定` / `## 将来設定` / `## 未解決事項` は変えない — いずれもオーケストレーターに依存しない'
reflected: 2026-08-10
---

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
| 状態の確認 | `make status` |

## lint・テストコマンド

| 用途 | コマンド | 備考 |
|---|---|---|
| lint | `go vet ./...` | `docker-proxy/` のディレクトリで実行する。**Bash には自動 lint を設けていない**(`SR-32`) |
| 単体テスト(docker-proxy) | `cd docker-proxy && go test ./...` | プロキシの検査ロジック |
| カバレッジ計測(docker-proxy) | `cd docker-proxy && go test -cover ./...` | テスト戦略が参照する計測手段(`03-impl/tests/strategy.md`)。合否の条件は課さない |
| 結合テスト | 上記の `go test` に含まれる | 契約ごとの責任モジュールは `system.md`「結合テスト対象」が正。シェル側の契約は実機確認 |
| E2Eテスト | 自動テストランナーは無い。実機で `claude-dev` を操作する | シェル系 E2E(E2E-01〜03・E2E-06)はすべて実機確認。手順は `03-impl/tests/e2e.md` |
| build | `make build` | `claude`(ブラウザ確認なし)+ `claude-vnc` + `docker-proxy` を一括ビルド |
| build(個別) | `make build-claude` / `make build-claude-vnc` / `make build-docker-proxy` | `claude-vnc` はベースに続けてビルドする |
| 再ビルド(キャッシュ無し) | `make upgrade` | 全イメージを作り直す |

## CI

| タイミング | 実行内容 | 失敗したらどうなるか |
|---|---|---|
| 日次 03:30 JST | エージェント CLI のバージョン解決 → マルチアーキ(amd64/arm64)でイメージをビルド → GHCR へ push(タイムスタンプタグ + `latest`) | その日の配布イメージが更新されない(前日のイメージは残る) |
| 手動実行 | 上と同じ。エージェント CLI のバージョンを入力で指定できる | 切り戻しができない |
| PR / 変更時 | **自動化していない。** `go vet` と `go test` は手元で実行する運用 | — |

**PR での自動テスト実行は導入していない。** docker-proxy に閉じた検査なので CI 化の障壁は低い。
導入するかどうかと、その時期は `docs/pendings.md` の **P-002** が持つ(意図的な棚上げであり、
この文書の未解決事項ではない)。

## コールグラフ抽出設定

| 項目 | 値 |
|---|---|
| internal_roots | リポジトリルート(`claude-dev` / `claude-dev-mac` / `scripts/` / `Makefile` / `docker-proxy/`) |
| 有効な言語 | shell / make / go / python / typescript / infra |
| 抽出器が無い言語 | **Dockerfile と GitHub Actions**。この2つはコールグラフに現れないため、モジュール分割定義から外し `03-impl/environments/` と `03-impl/infra/local/` が記述を持つ(`DSN-mod-05`) |
| Tier | shell=3 / make=3 / go=2 / python=2 / typescript=2 / infra=2 |
| ツール環境 | `.claude/.venv`(キット専用。**プロジェクトの環境には入れない**) |
| 用意するコマンド | `python3 .claude/scripts/setup-tools.py` |
| 除外するパス | `workspace/` / `tmp/` / `scripts/e2e6-codex.sh`(E2E の実機検証スクリプトであり、機能ではなく検証手段のため。決定シート2 論点9) |
| 出力先 | `docs/03-impl/callgraphs/` |
| 鮮度検査 | `python3 .claude/scripts/build-callgraphs.py --out "$(python3 .claude/scripts/resolve-callgraph-out.py)" --check` |
| CI で検査するか | いいえ(未定。PR での自動実行を導入する際に併せて決める) |
