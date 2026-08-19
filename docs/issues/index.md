# 未タスク化の課題 一覧

<!-- このファイルは build-index.py が生成する。手書きしない。 -->

<!-- BEGIN GENERATED: build-index.py -->

| ID | 種別 | 重大度 | 起点層 | 発見 | 関連 | 概要 |
|---|---|---|---|---|---|---|
| [002-modify-claude-dev-yaml-is-overwritten-wholesale](002-modify-claude-dev-yaml-is-overwritten-wholesale.md) | modify | 低 | - | 2026-08-02 | MODULE-cli-common-write-project-ssh-keys, MODULE-cli-ssh-keys-reset, FR-env-04 | .claude-dev.yaml が全面上書き・全リスト行削除される実装で、ssh_keys 以外のキーを持てない |
| [005-modify-docker-proxy-relays-unparseable-bodies](005-modify-docker-proxy-relays-unparseable-bodies.md) | modify | 中 | - | 2026-08-03 | MODULE-docker-proxy-serve, CTR-docker-api, FR-env-07, AC-03, D0-sec-05 | docker-proxy は解釈できないボディを検査せず中継するため、AC-03 の「危険な操作は拒否される」という保証に穴がある |
| [010-modify-forward-host-port-selection-is-racy](010-modify-forward-host-port-selection-is-racy.md) | modify | 中 | - | 2026-08-03 | MODULE-cli-forward, FR-env-06, NFR-scale-01 | forward のホストポート選択が docker の公開ポートしか見ず、判定から docker run までのレースもあるため、同時実行や非 Docker プロセスとの競合で失敗する |
| [028-modify-name-uniqueness-does-not-satisfy-nfr-scale-01](028-modify-name-uniqueness-does-not-satisfy-nfr-scale-01.md) | modify | 中 | - | 2026-08-03 | NFR-scale-01, MODULE-cli-start, MODULE-cli-forward, MODULE-cli-stop, CTR-cli-container | コンテナ名・compose プロジェクト名・中継コンテナ名がいずれも「名前だけ」で同一性を決めるため、NFR-scale-01 の「プロジェクト間で衝突しない」を満たしていない |
| [046-bug-list-and-make-targets-undercount-containers-from-older-images](046-bug-list-and-make-targets-undercount-containers-from-older-images.md) | bug | 中 | - | 2026-08-04 | MODULE-cli-list, MODULE-makefile-status, MODULE-makefile-clean, FR-env-01, docs/issues/045 | list / make status / make clean が `--filter ancestor` でコンテナを列挙するため、イメージを再取得・再ビルドした後は「稼働中なのに一覧に出ない」セッションが生じる(利用者は欠落に気づけない) |
| [055-modify-ac17-demands-listing-stopped-unlabeled-containers](055-modify-ac17-demands-listing-stopped-unlabeled-containers.md) | modify | 中 | - | 2026-08-05 | FR-env-03, D0-env-08, CTR-cli-container, MODULE-cli-logout, MODULE-cli-reset, docs/02-design/contracts/cli-container.md | FR-env-03 受入基準17 は管理ラベルを持たない Claude コンテナの名前を「表示して残す」ことを稼働中に限定せずに要求するが、02 の契約は停止中のものを列挙できないことを意図した限界として明記しており、01 と 02 が食い違う |
| [076-bug-check-changeset-treats-staged-callgraphs-as-change-instructions](076-bug-check-changeset-treats-staged-callgraphs-as-change-instructions.md) | bug | 中 | - | 2026-08-07 | .claude/scripts/check-changeset.py, .claude/scripts/close-task.py, .claude/directions/change-set.md, .claude/directions/callgraphs.md | 進行中タスクの staged コールグラフを check-changeset.py が変更指示とみなし、CS1 違反 29 件でフェーズ2のゲートが通らなくなる |
| [079-modify-cs6-cs7-are-permanently-unchecked-with-no-recorded-decision](079-modify-cs6-cs7-are-permanently-unchecked-with-no-recorded-decision.md) | modify | 低 | - | 2026-08-07 | .claude/scripts/changeset-invariants.json, .claude/directions/change-set.md, docs/pendings.md | CS6(状態値の語彙)と CS7(失敗分類 ⇄ 試行回数)が未設定のまま毎回「未検査」を出し続けるが、要否を決めた記録がどこにも無い |
| [081-bug-check-changeset-aborts-on-a-non-utf8-file-in-the-task-directory](081-bug-check-changeset-aborts-on-a-non-utf8-file-in-the-task-directory.md) | bug | 低 | - | 2026-08-07 | .claude/scripts/check-changeset.py, .claude/directions/change-set.md, docs/issues/076 | タスクディレクトリに UTF-8 でない .md ファイルが1つあると check-changeset.py が UnicodeDecodeError で異常終了し、変更指示の検査が1件も走らない |
| [092-modify-01-says-stop-halts-docker-proxy-while-the-code-deletes-it](092-modify-01-says-stop-halts-docker-proxy-while-the-code-deletes-it.md) | modify | 中 | 00 | 2026-08-07 | FR-env-01, D0-env-08, docs/02-design/contracts/cli-container.md, MODULE-cli-stop, MODULE-cli-logout, MODULE-cli-reset, claude-dev, claude-dev-mac | docker-proxy について 00・01 は「停止」、02・03・実装は「削除」(`docker rm -f`)と書いており、利用者向け出力も「停止しました」なのでコンテナが残らないことが伝わらない |
| [094-modify-user-visible-values-are-stated-verbatim-in-two-layers](094-modify-user-visible-values-are-stated-verbatim-in-two-layers.md) | modify | 中 | 02 | 2026-08-08 | FR-env-12-5, FR-orch-03-3, FR-env-01-18, FR-env-01-16, D0-dist-04, D0-env-06, DSN-dist-02, CTR-cli-orchestrator, CTR-cli-container, docs/02-design/logging.md | 既定値・受理する文字集合・設定の鍵と値の組が 2 つ以上の層に逐語で書かれており、どちらを直せば正になるかが決まらない |
| [097-modify-cli-help-dispatch-branch-is-absent-from-the-feature-table](097-modify-cli-help-dispatch-branch-is-absent-from-the-feature-table.md) | modify | 中 | 02 | 2026-08-11 | docs/03-impl/features.md, MODULE-makefile-help, docs/01-requirements/usecases.md | CLI の `help\|*)` ディスパッチ分岐(ヘルプ表示と未知サブコマンドの受け皿)が機能表に無く、対応する MODULE-*.md も存在しない |
| [102-bug-colabtmux-refuses-to-launch-codex-on-a-nonzero-bwrap-probe](102-bug-colabtmux-refuses-to-launch-codex-on-a-nonzero-bwrap-probe.md) | bug | 中 | 02 | 2026-08-19 | FR-env-12, AC-06, D0-dist-04, DSN-dist-02, MODULE-entrypoint-claude, docs/02-design/environments.md | 同梱外部バイナリ colabtmux が codex を起こす前に bwrap の可否を見ており、コンテナ内では既知かつ正常な非ゼロを故障と読んで起動を拒む |

件数: 13

<!-- END GENERATED: build-index.py -->
