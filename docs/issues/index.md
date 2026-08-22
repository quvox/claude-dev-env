# 未タスク化の課題 一覧

<!-- このファイルは build-index.py が生成する。手書きしない。 -->

<!-- BEGIN GENERATED: build-index.py -->

| ID | 種別 | 重大度 | 起点層 | 発見 | 関連 | 概要 |
|---|---|---|---|---|---|---|
| [005-modify-docker-proxy-relays-unparseable-bodies](005-modify-docker-proxy-relays-unparseable-bodies.md) | modify | 中 | - | 2026-08-03 | MODULE-docker-proxy-serve, CTR-docker-api, FR-env-07, AC-03, D0-sec-05 | docker-proxy は解釈できないボディを検査せず中継するため、AC-03 の「危険な操作は拒否される」という保証に穴がある |
| [010-modify-forward-host-port-selection-is-racy](010-modify-forward-host-port-selection-is-racy.md) | modify | 中 | - | 2026-08-03 | MODULE-cli-forward, FR-env-06, NFR-scale-01 | forward のホストポート選択が docker の公開ポートしか見ず、判定から docker run までのレースもあるため、同時実行や非 Docker プロセスとの競合で失敗する |
| [028-modify-name-uniqueness-does-not-satisfy-nfr-scale-01](028-modify-name-uniqueness-does-not-satisfy-nfr-scale-01.md) | modify | 中 | - | 2026-08-03 | NFR-scale-01, MODULE-cli-start, MODULE-cli-forward, MODULE-cli-stop, CTR-cli-container | コンテナ名・compose プロジェクト名・中継コンテナ名がいずれも「名前だけ」で同一性を決めるため、NFR-scale-01 の「プロジェクト間で衝突しない」を満たしていない |
| [055-modify-ac17-demands-listing-stopped-unlabeled-containers](055-modify-ac17-demands-listing-stopped-unlabeled-containers.md) | modify | 中 | - | 2026-08-05 | FR-env-03, D0-env-08, CTR-cli-container, MODULE-cli-logout, MODULE-cli-reset, docs/02-design/contracts/cli-container.md | FR-env-03 受入基準17 は管理ラベルを持たない Claude コンテナの名前を「表示して残す」ことを稼働中に限定せずに要求するが、02 の契約は停止中のものを列挙できないことを意図した限界として明記しており、01 と 02 が食い違う |
| [094-modify-user-visible-values-are-stated-verbatim-in-two-layers](094-modify-user-visible-values-are-stated-verbatim-in-two-layers.md) | modify | 中 | 02 | 2026-08-08 | FR-env-12-5, FR-orch-03-3, FR-env-01-18, FR-env-01-16, D0-dist-04, D0-env-06, DSN-dist-02, CTR-cli-orchestrator, CTR-cli-container, docs/02-design/logging.md | 既定値・受理する文字集合・設定の鍵と値の組が 2 つ以上の層に逐語で書かれており、どちらを直せば正になるかが決まらない |
| [097-modify-cli-help-dispatch-branch-is-absent-from-the-feature-table](097-modify-cli-help-dispatch-branch-is-absent-from-the-feature-table.md) | modify | 中 | 02 | 2026-08-11 | docs/03-impl/features.md, MODULE-makefile-help, docs/01-requirements/usecases.md | CLI の `help\|*)` ディスパッチ分岐(ヘルプ表示と未知サブコマンドの受け皿)が機能表に無く、対応する MODULE-*.md も存在しない |
| [098-modify-entrypoint-writes-user-controlled-paths-as-root](098-modify-entrypoint-writes-user-controlled-paths-as-root.md) | modify | 中 | 03 | 2026-08-22 | MODULE-entrypoint-claude, FR-env-11-2, FR-env-11-9, FR-env-12-14, scripts/entrypoint-claude.sh | root で動く entrypoint が、利用者が書き換えられる `/workspace` 配下の固定名パスへリダイレクトし、シンボリックリンクを追う chown を行っている |
| [099-bug-mcp-entry-presence-test-treats-null-as-absent](099-bug-mcp-entry-presence-test-treats-null-as-absent.md) | bug | 中 | 03 | 2026-08-22 | MODULE-entrypoint-claude, FR-env-11-9, FR-env-11-2, scripts/entrypoint-claude.sh | 登録の有無を `jq -e` の真偽で判定しているため、`null` や `false` が書かれたエントリを「未登録」とみなして上書きし、FR-env-11-9 の「それ以外の値は変更してはならない」に反する |

件数: 8

<!-- END GENERATED: build-index.py -->
