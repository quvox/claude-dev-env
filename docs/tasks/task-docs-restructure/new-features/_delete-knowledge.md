---
target: docs/knowledge/
change: delete
sections: []
deletes: []
reason: 旧体系の技術的知見置き場。新体系では技術的知見は 02-design の設計判断(DSN-*)の「理由」欄が持ち、そこに収まらないものは `docs/feedbacks/` が持つ。
---

削除理由(ディレクトリごと): 16件の移設先は下表のとおり。**削除は移設の完了後に行う**
(`docs/feedbacks/` への変換と設計判断の理由欄への吸収が済んでいることが前提)。

| ファイル | 移設先 |
|---|---|
| `append-missing-defaults-must-respect-file-structure.md` | `00-requests/decisions/scope.md` の `D0-scope-05` |
| `avoid-deep-shell-quote-nesting.md` | `docs/feedbacks/`(実装上の作法。設計判断ではない) |
| `changing-label-busts-layer-cache.md` | `02-design/architecture.md` の `DSN-dist-01` 理由欄 / `03-impl/environments/images.md` の落とし穴 |
| `container-is-the-only-isolation-boundary-for-agent-qa.md` | `00-requests/decisions/sec.md` の `D0-sec-06` / `02-design/environments.md` の Codex実行設定 |
| `cross-platform-isolate-os-deps-to-host-cli.md` | `02-design/system.md` の `DSN-mod-02` / `01-requirements/system.md` の `SR-02` |
| `docs-ahead-of-code-deadlocks-doc-check.md` | `docs/feedbacks/`(仕組みの運用上の気づき) |
| `host-credentials-are-not-imported-into-containers.md` | `00-requests/decisions/auth.md` の `D0-auth-02` 制約 |
| `nested-agent-sandbox-blocked-by-container-confinement.md` | `02-design/architecture.md` の `DSN-dist-02` 理由欄 |
| `orchestrator-tmux-residence-window-model.md` | `02-design/architecture.md` の `DSN-orch-02` |
| `per-task-intervention-and-resumable-suspend.md` | `00-requests/decisions/orch.md` の `D0-orch-12` / `D0-orch-13` |
| `portable-image-generic-user-runtime-uid.md` | `03-impl/environments/images.md`(ビルド引数)/ `FR-env-02` |
| `qemu-usermode-guest-dockerd-wiring.md` | `03-impl/relations/MODULE-vm-mode-up.md` / `00-requests/decisions/env.md` の `D0-env-03` |
| `real-binary-e2e-catches-what-mocks-miss.md` | `02-design/system.md` の `DSN-test-01` 理由欄 |
| `ssh-per-directory-dedicated-agent.md` | `00-requests/decisions/sec.md` の `D0-sec-08` |
| `tui-subprocess-shared-tty-ownership.md` | `02-design/system.md` の `DSN-ui-02` 理由欄 |
| `verify-automation-by-artifact-not-by-green-run.md` | `docs/feedbacks/`(検証の作法。`03-impl/tests/e2e.md` の E2E-06 手順にも反映済み) |

**適用時の停止条件**: 上に列挙したファイル**以外**が対象ディレクトリに存在する場合、削除せずに
停止して人間に報告する(移設漏れの可能性があるため)。削除は再帰削除でよいが、列挙と実在が
一致することを確認してから行う。
