# 未タスク化の課題 一覧

<!-- このファイルは build-index.py が生成する。手書きしない。 -->

<!-- BEGIN GENERATED: build-index.py -->

| ID | 種別 | 重大度 | 発見 | 関連 | 概要 |
|---|---|---|---|---|---|
| [001-modify-orchestrator-test-only-symbols](001-modify-orchestrator-test-only-symbols.md) | modify | 中 | 2026-08-02 | MODULE-orchestrator-controller, MODULE-orchestrator-dashboard | orchestrator の7シンボルが製品コードから呼ばれず、テストからのみ参照されている |
| [002-modify-claude-dev-yaml-is-overwritten-wholesale](002-modify-claude-dev-yaml-is-overwritten-wholesale.md) | modify | 低 | 2026-08-02 | MODULE-cli-common-write-project-ssh-keys, MODULE-cli-ssh-keys-reset, FR-env-04 | .claude-dev.yaml が全面上書き・全リスト行削除される実装で、ssh_keys 以外のキーを持てない |
| [003-future-macos-orchestrator-scope](003-future-macos-orchestrator-scope.md) | future | 中 | 2026-07-31 | MODULE-cli-orchestrate, CTR-cli-orchestrator, FR-orch-02, FR-env-10 | macOS 版 orchestrate が生存判定・attach/resume を実装しておらず契約と食い違ったままになっている |
| [004-modify-03-impl-lacks-reimplementation-depth](004-modify-03-impl-lacks-reimplementation-depth.md) | modify | 中 | 2026-08-03 | MODULE-cli-start, MODULE-cli-forward, MODULE-orchestrator-controller, MODULE-orchestrator-state-io, CTR-cli-container, CTR-cli-orchestrator, CTR-orchestrator-prompt | 03-impl が「現状の説明」としては正しいが、ドキュメントだけから再実装・再試験できる深度に達していない領域が約20件ある |
| [005-modify-docker-proxy-relays-unparseable-bodies](005-modify-docker-proxy-relays-unparseable-bodies.md) | modify | 中 | 2026-08-03 | MODULE-docker-proxy-serve, CTR-docker-api, FR-env-07, AC-03, D0-sec-05 | docker-proxy は解釈できないボディを検査せず中継するため、AC-03 の「危険な操作は拒否される」という保証に穴がある |
| [006-modify-e2e-procedures-lack-reproducibility](006-modify-e2e-procedures-lack-reproducibility.md) | modify | 中 | 2026-07-31 | E2E-01, E2E-02, E2E-03, E2E-04, E2E-05, E2E-06, docs/03-impl/tests/e2e.md | E2E シナリオの実施手順に固定入力・観測点・合否判定の根拠・後始末が無く、実施者によって結果が変わる |
| [007-future-heterogeneous-vendor-reviewer](007-future-heterogeneous-vendor-reviewer.md) | future | 中 | 2026-07-31 | D0-orch-17, FR-orch-06, FR-env-12 | 品質ゲートのレビュアーを別ベンダー(Codex)常用へ昇格する。人間の回答は「決定へ昇格。ただしフォールバック付き」で取得済み |
| [008-modify-spec-depth-contracts-and-wording](008-modify-spec-depth-contracts-and-wording.md) | modify | 中 | 2026-07-31 | FR-orch-01, FR-orch-04, FR-orch-06, CTR-cli-orchestrator, CTR-orchestrator-prompt | モジュール間契約の深度が実装可能な粒度に達しておらず、オーケストレーション要件の判定語が測定不能 |
| [009-modify-relations-prose-signatures-drift-from-code](009-modify-relations-prose-signatures-drift-from-code.md) | modify | 中 | 2026-08-03 | MODULE-orchestrator-session, MODULE-orchestrator-worktree, MODULE-orchestrator-worker, MODULE-orchestrator-mode, MODULE-orchestrator-review, MODULE-orchestrator-slack, MODULE-orchestrator-term, MODULE-orchestrator-handoff, MODULE-orchestrator-claude-exec, MODULE-orchestrator-dashboard | relations の「処理の流れ」本文が書く関数シグネチャが実コードと一致しない箇所が約27件あり、省略記法として許容するのか誤りとして直すのかの規約が無い |

件数: 9

<!-- END GENERATED -->
