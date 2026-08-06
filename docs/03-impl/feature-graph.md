---
id: feature-graph
features: 83
edges: 129
confirmed_edges: 122
candidate_edges: 7
shared: 27
unreached: 19
coupled_resources: 0
unlinked_pairs: 0
---

<!-- 生成物。手書き禁止。`python3 .claude/scripts/cluster-features.py --out "$(python3 .claude/scripts/resolve-callgraph-out.py)"` で再生成する。
     不変則: **実装と機能表が変わらなければ1バイトも変わらない**。
     鮮度は保存せず `--check` で検査する。
     **これは機能間連携仕様書ではない。** relations の代わりに使ってはならない
     (.claude/directions/features.md §6)。 -->

# 機能間の関係(機能表クラスタリング)

`docs/03-impl/features.md`(境界の定義)と `docs/03-impl/callgraphs/`(コード由来の事実)
から機械的に導出したもの。**どちらが正かは決めない。**

確度の意味(`.claude/directions/features.md` §5):

- `確定` — 名前解決が成功した辺だけで経路が繋がる
- `候補` — 同名衝突などの**候補辺**を算入して初めて繋がる。経路が実在するとは限らないが、**取りこぼすよりは出す**

## 機能間の辺

| 呼び出し元 | 呼び出し先 | 確度 | 呼び出し箇所 |
|---|---|---|---|
| MODULE-cli-attach | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#attach` → `claude-dev-mac::container_name`, `claude-dev::main#attach` → `claude-dev::container_name` |
| MODULE-cli-attach | MODULE-cli-common-is-running | 確定 | `claude-dev-mac::main#attach` → `claude-dev-mac::is_running`, `claude-dev::main#attach` → `claude-dev::is_running` |
| MODULE-cli-attach | MODULE-cli-common-require-setup | 確定 | `claude-dev-mac::main#attach` → `claude-dev-mac::require_setup`, `claude-dev::main#attach` → `claude-dev::require_setup` |
| MODULE-cli-attach | MODULE-cli-common-resolve-container-user | 確定 | `claude-dev-mac::main#attach` → `claude-dev-mac::resolve_container_user`, `claude-dev::main#attach` → `claude-dev::resolve_container_user` |
| MODULE-cli-code | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#code` → `claude-dev-mac::container_name`, `claude-dev::main#code` → `claude-dev::container_name` |
| MODULE-cli-code | MODULE-cli-common-is-running | 確定 | `claude-dev-mac::main#code` → `claude-dev-mac::is_running`, `claude-dev::main#code` → `claude-dev::is_running` |
| MODULE-cli-code | MODULE-cli-common-require-setup | 確定 | `claude-dev-mac::main#code` → `claude-dev-mac::require_setup`, `claude-dev::main#code` → `claude-dev::require_setup` |
| MODULE-cli-code | MODULE-cli-common-resolve-container-user | 確定 | `claude-dev-mac::main#code` → `claude-dev-mac::resolve_container_user`, `claude-dev::main#code` → `claude-dev::resolve_container_user` |
| MODULE-cli-common-require-setup | MODULE-cli-common-image-exists | 確定 | `claude-dev-mac::require_setup` → `claude-dev-mac::image_exists`, `claude-dev::require_setup` → `claude-dev::image_exists` |
| MODULE-cli-common-select-ssh-keys | MODULE-cli-common-write-project-ssh-keys | 確定 | `claude-dev-mac::select_ssh_keys_interactive` → `claude-dev-mac::write_project_ssh_keys`, `claude-dev::select_ssh_keys_interactive` → `claude-dev::write_project_ssh_keys` |
| MODULE-cli-firewall | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#firewall` → `claude-dev-mac::container_name`, `claude-dev::main#firewall` → `claude-dev::container_name` |
| MODULE-cli-firewall | MODULE-cli-common-is-running | 確定 | `claude-dev-mac::main#firewall` → `claude-dev-mac::is_running`, `claude-dev::main#firewall` → `claude-dev::is_running` |
| MODULE-cli-forward | MODULE-cli-common-container-exists | 確定 | `claude-dev-mac::main#forward` → `claude-dev-mac::container_exists`, `claude-dev::main#forward` → `claude-dev::container_exists` |
| MODULE-cli-forward | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#forward` → `claude-dev-mac::container_name`, `claude-dev::main#forward` → `claude-dev::container_name` |
| MODULE-cli-forward | MODULE-cli-common-is-running | 確定 | `claude-dev-mac::main#forward` → `claude-dev-mac::is_running`, `claude-dev::main#forward` → `claude-dev::is_running` |
| MODULE-cli-list | MODULE-cli-common-get-novnc-url | 確定 | `claude-dev-mac::main#list` → `claude-dev-mac::get_novnc_url`, `claude-dev::main#list` → `claude-dev::get_novnc_url` |
| MODULE-cli-list | MODULE-cli-common-is-running | 確定 | `claude-dev-mac::main#list` → `claude-dev-mac::is_running`, `claude-dev::main#list` → `claude-dev::is_running` |
| MODULE-cli-login | MODULE-cli-common-ensure-infrastructure | 確定 | `claude-dev-mac::main#login` → `claude-dev-mac::ensure_infrastructure`, `claude-dev::main#login` → `claude-dev::ensure_infrastructure` |
| MODULE-cli-login | MODULE-cli-common-lock | 確定 | `claude-dev-mac::main#login` → `claude-dev-mac::acquire_lock`, `claude-dev-mac::main#login` → `claude-dev-mac::release_lock`, `claude-dev::main#login` → `claude-dev::acquire_lock` ほか 1 件 |
| MODULE-cli-login | MODULE-cli-common-require-setup | 確定 | `claude-dev-mac::main#login` → `claude-dev-mac::require_setup`, `claude-dev::main#login` → `claude-dev::require_setup` |
| MODULE-cli-login-codex | MODULE-cli-common-ensure-infrastructure | 確定 | `claude-dev-mac::main#login-codex` → `claude-dev-mac::ensure_infrastructure`, `claude-dev::main#login-codex` → `claude-dev::ensure_infrastructure` |
| MODULE-cli-login-codex | MODULE-cli-common-lock | 確定 | `claude-dev-mac::main#login-codex` → `claude-dev-mac::acquire_lock`, `claude-dev-mac::main#login-codex` → `claude-dev-mac::release_lock`, `claude-dev::main#login-codex` → `claude-dev::acquire_lock` ほか 1 件 |
| MODULE-cli-login-codex | MODULE-cli-common-require-setup | 確定 | `claude-dev-mac::main#login-codex` → `claude-dev-mac::require_setup`, `claude-dev::main#login-codex` → `claude-dev::require_setup` |
| MODULE-cli-logout | MODULE-cli-common-container-exists | 確定 | `claude-dev-mac::main#logout` → `claude-dev-mac::container_exists`, `claude-dev::main#logout` → `claude-dev::container_exists` |
| MODULE-cli-logout | MODULE-cli-common-lock | 確定 | `claude-dev-mac::main#logout` → `claude-dev-mac::acquire_lock`, `claude-dev-mac::main#logout` → `claude-dev-mac::release_lock`, `claude-dev::main#logout` → `claude-dev::acquire_lock` ほか 1 件 |
| MODULE-cli-logout | MODULE-cli-common-require-setup | 確定 | `claude-dev-mac::main#logout` → `claude-dev-mac::require_setup`, `claude-dev::main#logout` → `claude-dev::require_setup` |
| MODULE-cli-orchestrate | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#orchestrate` → `claude-dev-mac::container_name`, `claude-dev::main#orchestrate` → `claude-dev::container_name` |
| MODULE-cli-orchestrate | MODULE-cli-common-is-running | 確定 | `claude-dev-mac::main#orchestrate` → `claude-dev-mac::is_running`, `claude-dev::main#orchestrate` → `claude-dev::is_running` |
| MODULE-cli-orchestrate | MODULE-cli-common-require-setup | 確定 | `claude-dev-mac::main#orchestrate` → `claude-dev-mac::require_setup`, `claude-dev::main#orchestrate` → `claude-dev::require_setup` |
| MODULE-cli-orchestrate | MODULE-cli-common-resolve-container-user | 確定 | `claude-dev-mac::main#orchestrate` → `claude-dev-mac::resolve_container_user`, `claude-dev::main#orchestrate` → `claude-dev::resolve_container_user` |
| MODULE-cli-ports | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#ports` → `claude-dev-mac::container_name`, `claude-dev::main#ports` → `claude-dev::container_name` |
| MODULE-cli-ports | MODULE-cli-common-get-novnc-url | 確定 | `claude-dev-mac::main#ports` → `claude-dev-mac::get_novnc_url`, `claude-dev::main#ports` → `claude-dev::get_novnc_url` |
| MODULE-cli-ports | MODULE-cli-common-is-running | 確定 | `claude-dev-mac::main#ports` → `claude-dev-mac::is_running`, `claude-dev::main#ports` → `claude-dev::is_running` |
| MODULE-cli-reset | MODULE-cli-common-container-exists | 確定 | `claude-dev-mac::main#reset` → `claude-dev-mac::container_exists`, `claude-dev::main#reset` → `claude-dev::container_exists` |
| MODULE-cli-reset | MODULE-cli-common-image-exists | 確定 | `claude-dev-mac::main#reset` → `claude-dev-mac::image_exists`, `claude-dev::main#reset` → `claude-dev::image_exists` |
| MODULE-cli-reset | MODULE-cli-common-lock | 確定 | `claude-dev-mac::main#reset` → `claude-dev-mac::acquire_lock`, `claude-dev-mac::main#reset` → `claude-dev-mac::release_lock`, `claude-dev::main#reset` → `claude-dev::acquire_lock` ほか 1 件 |
| MODULE-cli-ssh-keys | MODULE-cli-common-container-name | 確定 | `claude-dev::main#ssh-keys` → `claude-dev::container_name` |
| MODULE-cli-ssh-keys-reset | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#ssh-keys.reset` → `claude-dev-mac::container_name` |
| MODULE-cli-ssh-keys-reset | MODULE-cli-common-dev-agent-path | 確定 | `claude-dev-mac::main#ssh-keys.reset` → `claude-dev-mac::dev_agent_path` |
| MODULE-cli-ssh-keys-select | MODULE-cli-common-select-ssh-keys | 確定 | `claude-dev-mac::main#ssh-keys.select` → `claude-dev-mac::select_ssh_keys_interactive`, `claude-dev::main#ssh-keys.select` → `claude-dev::select_ssh_keys_interactive` |
| MODULE-cli-start | MODULE-cli-common-container-exists | 確定 | `claude-dev-mac::ensure_docker_proxy_container` → `claude-dev-mac::container_exists`, `claude-dev-mac::main#start` → `claude-dev-mac::container_exists`, `claude-dev::ensure_docker_proxy_container` → `claude-dev::container_exists` ほか 1 件 |
| MODULE-cli-start | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#start` → `claude-dev-mac::container_name`, `claude-dev::main#start` → `claude-dev::container_name` |
| MODULE-cli-start | MODULE-cli-common-dev-agent-path | 確定 | `claude-dev-mac::ensure_dedicated_agent` → `claude-dev-mac::dev_agent_path`, `claude-dev-mac::ensure_ssh_bridge` → `claude-dev-mac::dev_agent_path` |
| MODULE-cli-start | MODULE-cli-common-ensure-infrastructure | 確定 | `claude-dev-mac::main#start` → `claude-dev-mac::ensure_infrastructure`, `claude-dev::main#start` → `claude-dev::ensure_infrastructure` |
| MODULE-cli-start | MODULE-cli-common-get-novnc-url | 確定 | `claude-dev-mac::main#start` → `claude-dev-mac::get_novnc_url`, `claude-dev::main#start` → `claude-dev::get_novnc_url` |
| MODULE-cli-start | MODULE-cli-common-image-exists | 確定 | `claude-dev-mac::ensure_docker_proxy_container` → `claude-dev-mac::image_exists`, `claude-dev::ensure_docker_proxy_container` → `claude-dev::image_exists` |
| MODULE-cli-start | MODULE-cli-common-is-running | 確定 | `claude-dev-mac::ensure_docker_proxy_container` → `claude-dev-mac::is_running`, `claude-dev-mac::main#start` → `claude-dev-mac::is_running`, `claude-dev::ensure_docker_proxy_container` → `claude-dev::is_running` ほか 1 件 |
| MODULE-cli-start | MODULE-cli-common-lock | 確定 | `claude-dev-mac::main#start` → `claude-dev-mac::acquire_lock`, `claude-dev-mac::main#start` → `claude-dev-mac::release_lock`, `claude-dev::main#start` → `claude-dev::acquire_lock` ほか 1 件 |
| MODULE-cli-start | MODULE-cli-common-require-setup | 確定 | `claude-dev-mac::main#start` → `claude-dev-mac::require_setup`, `claude-dev::main#start` → `claude-dev::require_setup` |
| MODULE-cli-start | MODULE-cli-common-resolve-container-user | 確定 | `claude-dev-mac::main#start` → `claude-dev-mac::resolve_container_user`, `claude-dev::main#start` → `claude-dev::resolve_container_user` |
| MODULE-cli-start | MODULE-cli-common-select-ssh-keys | 確定 | `claude-dev-mac::ensure_project_config` → `claude-dev-mac::select_ssh_keys_interactive`, `claude-dev::ensure_project_config` → `claude-dev::select_ssh_keys_interactive` |
| MODULE-cli-start | MODULE-cli-common-write-project-ssh-keys | 確定 | `claude-dev-mac::ensure_project_config` → `claude-dev-mac::write_project_ssh_keys`, `claude-dev::ensure_project_config` → `claude-dev::write_project_ssh_keys` |
| MODULE-cli-stop | MODULE-cli-common-container-exists | 確定 | `claude-dev-mac::main#stop` → `claude-dev-mac::container_exists`, `claude-dev::main#stop` → `claude-dev::container_exists` |
| MODULE-cli-stop | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#stop` → `claude-dev-mac::container_name`, `claude-dev::main#stop` → `claude-dev::container_name` |
| MODULE-cli-stop | MODULE-cli-common-dev-agent-path | 確定 | `claude-dev-mac::stop_ssh_bridge` → `claude-dev-mac::dev_agent_path` |
| MODULE-cli-stop | MODULE-cli-common-is-running | 確定 | `claude-dev-mac::stop_proxy_if_idle` → `claude-dev-mac::is_running`, `claude-dev::stop_proxy_if_idle` → `claude-dev::is_running` |
| MODULE-cli-stop | MODULE-cli-common-lock | 確定 | `claude-dev-mac::main#stop` → `claude-dev-mac::acquire_lock`, `claude-dev-mac::main#stop` → `claude-dev-mac::release_lock`, `claude-dev::main#stop` → `claude-dev::acquire_lock` ほか 1 件 |
| MODULE-cli-unforward | MODULE-cli-common-container-exists | 確定 | `claude-dev-mac::main#unforward` → `claude-dev-mac::container_exists`, `claude-dev::main#unforward` → `claude-dev::container_exists` |
| MODULE-cli-unforward | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#unforward` → `claude-dev-mac::container_name`, `claude-dev::main#unforward` → `claude-dev::container_name` |
| MODULE-makefile-build | MODULE-makefile-build-claude | 確定 | `Makefile::build` → `Makefile::build-claude` |
| MODULE-makefile-build | MODULE-makefile-build-claude-vnc | 確定 | `Makefile::build` → `Makefile::build-claude-vnc` |
| MODULE-makefile-build | MODULE-makefile-build-docker-proxy | 確定 | `Makefile::build` → `Makefile::build-docker-proxy` |
| MODULE-makefile-build-claude-vnc | MODULE-makefile-build-claude | 確定 | `Makefile::build-claude-vnc` → `Makefile::build-claude` |
| MODULE-makefile-help | MODULE-makefile-build | 確定 | `Makefile::help` → `Makefile::build` |
| MODULE-makefile-help | MODULE-makefile-build-claude | 確定 | `Makefile::help` → `Makefile::build-claude` |
| MODULE-makefile-help | MODULE-makefile-build-claude-vnc | 確定 | `Makefile::help` → `Makefile::build-claude-vnc` |
| MODULE-makefile-help | MODULE-makefile-build-docker-proxy | 確定 | `Makefile::help` → `Makefile::build-docker-proxy` |
| MODULE-makefile-help | MODULE-makefile-build-orchestrator | 確定 | `Makefile::help` → `Makefile::build-orchestrator` |
| MODULE-makefile-help | MODULE-makefile-clean | 確定 | `Makefile::help` → `Makefile::clean` |
| MODULE-makefile-help | MODULE-makefile-login | 確定 | `Makefile::help` → `Makefile::login` |
| MODULE-makefile-help | MODULE-makefile-setup | 確定 | `Makefile::help` → `Makefile::setup` |
| MODULE-makefile-help | MODULE-makefile-status | 確定 | `Makefile::help` → `Makefile::status` |
| MODULE-makefile-help | MODULE-makefile-uninstall | 確定 | `Makefile::help` → `Makefile::uninstall` |
| MODULE-makefile-help | MODULE-makefile-update-claude | 確定 | `Makefile::help` → `Makefile::update-claude` |
| MODULE-makefile-help | MODULE-makefile-upgrade | 確定 | `Makefile::help` → `Makefile::upgrade` |
| MODULE-makefile-setup | MODULE-makefile-build | 確定 | `Makefile::setup` → `Makefile::build` |
| MODULE-makefile-setup | MODULE-makefile-env | 確定 | `Makefile::setup` → `Makefile::env` |
| MODULE-makefile-setup | MODULE-makefile-install | 確定 | `Makefile::setup` → `Makefile::install` |
| MODULE-makefile-setup | MODULE-makefile-login | 確定 | `Makefile::setup` → `Makefile::login` |
| MODULE-makefile-setup | MODULE-makefile-network | 確定 | `Makefile::setup` → `Makefile::network` |
| MODULE-makefile-setup | MODULE-makefile-volumes | 確定 | `Makefile::setup` → `Makefile::volumes` |
| MODULE-orchestrator-claude-exec | MODULE-orchestrator-controller | 候補 | `orchestrator/worker.go::ExecClaude.RunPrompt` → `orchestrator/controller.go::Controller.Run`(候補) |
| MODULE-orchestrator-claude-exec | MODULE-orchestrator-session | 候補 | `orchestrator/worker.go::ExecClaude.RunPrompt` → `orchestrator/session.go::SessionManager.Run`(候補) |
| MODULE-orchestrator-claude-exec | MODULE-orchestrator-streamlog | 確定 | `orchestrator/worker.go::ExecClaude.RunPrompt` → `orchestrator/streamlog.go::newStreamPrettyWriter` |
| MODULE-orchestrator-controller | MODULE-orchestrator-claude-exec | 確定 | `orchestrator/controller.go::Controller.checkCompletion` → `orchestrator/worker.go::ExecClaude.RunPrompt` |
| MODULE-orchestrator-controller | MODULE-orchestrator-dashboard | 確定 | `orchestrator/controller.go::Controller.refreshInterventionCount` → `orchestrator/dashboard.go::DashboardState.Set`, `orchestrator/controller.go::Controller.runBrainstormingSession` → `orchestrator/dashtui.go::newDashProgram`, `orchestrator/controller.go::Controller.runExecuting` → `orchestrator/dashtui.go::newDashProgram` ほか 1 件 |
| MODULE-orchestrator-controller | MODULE-orchestrator-handoff | 確定 | `orchestrator/controller.go::Controller.Run` → `orchestrator/handoff.go::Handoff.DiscardStale`, `orchestrator/controller.go::Controller.resolveInterventionInSession` → `orchestrator/handoff.go::Handoff.WaitConsume`, `orchestrator/controller.go::Controller.runBrainstorming` → `orchestrator/handoff.go::Handoff.Consume` ほか 2 件 |
| MODULE-orchestrator-controller | MODULE-orchestrator-mode | 確定 | `orchestrator/controller.go::Controller.resolveInterventionInSession` → `orchestrator/mode.go::Mode.IntervenePrompt`, `orchestrator/controller.go::Controller.resolveInterventionInSession` → `orchestrator/mode.go::Mode.WriteLaunchScript`, `orchestrator/controller.go::Controller.runBrainstorming` → `orchestrator/mode.go::Mode.BrainstormingArgs` ほか 4 件 |
| MODULE-orchestrator-controller | MODULE-orchestrator-plan | 確定 | `orchestrator/controller.go::Controller.runExecuting` → `orchestrator/controller.go::AllSettled`, `orchestrator/controller.go::Controller.runExecuting` → `orchestrator/controller.go::MarkBlockedByFailedDeps`, `orchestrator/controller.go::Controller.runExecuting` → `orchestrator/controller.go::NormalizeForResume` ほか 2 件 |
| MODULE-orchestrator-controller | MODULE-orchestrator-review | 確定 | `orchestrator/controller.go::Controller.runTaskPipeline` → `orchestrator/review.go::Reviewer.RunGate` |
| MODULE-orchestrator-controller | MODULE-orchestrator-session | 確定 | `orchestrator/controller.go::Controller.Run` → `orchestrator/session.go::SessionManager.DetectSession`, `orchestrator/controller.go::Controller.Run` → `orchestrator/session.go::SessionManager.SetupMainSession`, `orchestrator/controller.go::Controller.closeBrainstormingSession` → `orchestrator/session.go::SessionManager.BrainstormingWindow` ほか 19 件 |
| MODULE-orchestrator-controller | MODULE-orchestrator-state | 確定 | `orchestrator/controller.go::Controller.Run` → `orchestrator/state.go::Store.LoadState`, `orchestrator/controller.go::Controller.Run` → `orchestrator/state.go::Store.SaveState`, `orchestrator/controller.go::Controller.openInterventionLocked` → `orchestrator/state.go::Store.SavePlan` ほか 12 件 |
| MODULE-orchestrator-controller | MODULE-orchestrator-state-intervention | 確定 | `orchestrator/controller.go::Controller.Run` → `orchestrator/state.go::Store.AppendAudit`, `orchestrator/controller.go::Controller.openIDForTask` → `orchestrator/state.go::Store.LoadOpenInterventions`, `orchestrator/controller.go::Controller.openInterventionLocked` → `orchestrator/state.go::Store.AddOpenIntervention` ほか 24 件 |
| MODULE-orchestrator-controller | MODULE-orchestrator-term | 確定 | `orchestrator/controller.go::Controller.reportNotExecutable` → `orchestrator/mode.go::isTTY`, `orchestrator/controller.go::Controller.resolveInterventionInSession` → `orchestrator/term.go::printModeBanner`, `orchestrator/controller.go::Controller.runBrainstorming` → `orchestrator/term.go::printModeBanner` ほか 5 件 |
| MODULE-orchestrator-controller | MODULE-orchestrator-trigger | 確定 | `orchestrator/controller.go::Controller.evalStuck` → `orchestrator/trigger.go::Evaluate`, `orchestrator/controller.go::Controller.runExecuting` → `orchestrator/trigger.go::Evaluate`, `orchestrator/controller.go::Controller.runTaskPipeline` → `orchestrator/trigger.go::Evaluate` |
| MODULE-orchestrator-controller | MODULE-orchestrator-worker | 確定 | `orchestrator/controller.go::Controller.runTaskPipeline` → `orchestrator/worker.go::Worker.Dispatch`, `orchestrator/controller.go::parseCompletionVerdict` → `orchestrator/worker.go::extractFromClaudeEnvelope`, `orchestrator/controller.go::parseCompletionVerdict` → `orchestrator/worker.go::resultFromStream` |
| MODULE-orchestrator-controller | MODULE-orchestrator-worktree | 確定 | `orchestrator/controller.go::Controller.integrate` → `orchestrator/worker.go::ExecGit.Merge` |
| MODULE-orchestrator-dashboard | MODULE-orchestrator-session | 確定 | `orchestrator/dashtui.go::dashModel.Update` → `orchestrator/session.go::SessionManager.BrainstormingWindow`, `orchestrator/dashtui.go::dashModel.Update` → `orchestrator/session.go::SessionManager.SwitchTo`, `orchestrator/dashtui.go::dashModel.Update` → `orchestrator/session.go::SessionManager.WorkerWindow` |
| MODULE-orchestrator-dashboard | MODULE-orchestrator-state | 確定 | `orchestrator/dashtui.go::detailTails` → `orchestrator/state.go::Store.WorkerLogPath` |
| MODULE-orchestrator-handoff | MODULE-orchestrator-state-intervention | 確定 | `orchestrator/handoff.go::Handoff.Consume` → `orchestrator/state.go::Store.DeleteControl`, `orchestrator/handoff.go::Handoff.Consume` → `orchestrator/state.go::Store.LoadControl`, `orchestrator/handoff.go::Handoff.DiscardStale` → `orchestrator/state.go::Store.DeleteControl` |
| MODULE-orchestrator-main | MODULE-orchestrator-config | 確定 | `orchestrator/main.go::run` → `orchestrator/config.go::LoadConfig` |
| MODULE-orchestrator-main | MODULE-orchestrator-controller | 確定 | `orchestrator/main.go::run` → `orchestrator/controller.go::Controller.Run`, `orchestrator/main.go::run` → `orchestrator/controller.go::newRunID` |
| MODULE-orchestrator-main | MODULE-orchestrator-plan | 確定 | `orchestrator/main.go::run` → `orchestrator/controller.go::AllDone` |
| MODULE-orchestrator-main | MODULE-orchestrator-session | 確定 | `orchestrator/main.go::main` → `orchestrator/session.go::NewSessionManager`, `orchestrator/main.go::main` → `orchestrator/session.go::SessionManager.MainSession`, `orchestrator/main.go::run` → `orchestrator/session.go::NewSessionManager` |
| MODULE-orchestrator-main | MODULE-orchestrator-slack | 確定 | `orchestrator/main.go::run` → `orchestrator/slack.go::NewSlackNotifier` |
| MODULE-orchestrator-main | MODULE-orchestrator-state | 確定 | `orchestrator/main.go::run` → `orchestrator/state.go::NewStore`, `orchestrator/main.go::seedPlanReady` → `orchestrator/state.go::Store.LoadPlan` |
| MODULE-orchestrator-main | MODULE-orchestrator-term | 確定 | `orchestrator/main.go::run` → `orchestrator/term.go::ttyRestoreSane` |
| MODULE-orchestrator-main | MODULE-orchestrator-worktree | 確定 | `orchestrator/main.go::run` → `orchestrator/worker.go::CleanOrchWorktrees` |
| MODULE-orchestrator-mode | MODULE-orchestrator-claude-exec | 確定 | `orchestrator/mode.go::Mode.RunInteractive` → `orchestrator/claudebin.go::claudeChildEnv`, `orchestrator/mode.go::Mode.RunInteractive` → `orchestrator/claudebin.go::claudePath`, `orchestrator/mode.go::Mode.WriteLaunchScript` → `orchestrator/claudebin.go::claudePath` ほか 1 件 |
| MODULE-orchestrator-mode | MODULE-orchestrator-controller | 候補 | `orchestrator/mode.go::Mode.RunInteractive` → `orchestrator/controller.go::Controller.Run`(候補) |
| MODULE-orchestrator-mode | MODULE-orchestrator-session | 候補 | `orchestrator/mode.go::Mode.RunInteractive` → `orchestrator/session.go::SessionManager.Run`(候補) |
| MODULE-orchestrator-mode | MODULE-orchestrator-state | 確定 | `orchestrator/mode.go::Mode.ResolveArgs` → `orchestrator/state.go::LoadProjectPolicy`, `orchestrator/mode.go::Mode.ResolveArgs` → `orchestrator/state.go::VMModePreamble`, `orchestrator/mode.go::Mode.WriteLaunchScript` → `orchestrator/state.go::Store.path` ほか 5 件 |
| MODULE-orchestrator-mode | MODULE-orchestrator-state-intervention | 確定 | `orchestrator/mode.go::Mode.IntervenePrompt` → `orchestrator/mode.go::Store.ReadQuestion`, `orchestrator/mode.go::Mode.ResolveArgs` → `orchestrator/mode.go::Store.ReadQuestion`, `orchestrator/mode.go::Mode.ResolveArgsOne` → `orchestrator/mode.go::Store.ReadQuestion` ほか 1 件 |
| MODULE-orchestrator-mode | MODULE-orchestrator-state-io | 確定 | `orchestrator/mode.go::Mode.WriteLaunchScript` → `orchestrator/state.go::writeAtomic` |
| MODULE-orchestrator-mode | MODULE-orchestrator-term | 確定 | `orchestrator/mode.go::Mode.RunInteractive` → `orchestrator/term.go::ttyRestoreSane` |
| MODULE-orchestrator-review | MODULE-orchestrator-state | 確定 | `orchestrator/review.go::Reviewer.Review` → `orchestrator/state.go::Store.WorkerLogPath`, `orchestrator/review.go::Reviewer.Review` → `orchestrator/state.go::Store.WorktreeAbs`, `orchestrator/review.go::Reviewer.buildReviewPrompt` → `orchestrator/state.go::LoadProjectPolicy` ほか 1 件 |
| MODULE-orchestrator-review | MODULE-orchestrator-state-intervention | 確定 | `orchestrator/review.go::Reviewer.Review` → `orchestrator/state.go::Store.AppendAudit`, `orchestrator/review.go::Reviewer.RunGate` → `orchestrator/state.go::Store.AppendAudit`, `orchestrator/review.go::appendReviseError` → `orchestrator/state.go::Store.AppendAudit` |
| MODULE-orchestrator-review | MODULE-orchestrator-worker | 確定 | `orchestrator/review.go::ParseReviewResult` → `orchestrator/worker.go::extractFromClaudeEnvelope`, `orchestrator/review.go::ParseReviewResult` → `orchestrator/worker.go::resultFromStream`, `orchestrator/review.go::Reviewer.RunGate` → `orchestrator/worker.go::Worker.Dispatch` ほか 1 件 |
| MODULE-orchestrator-session | MODULE-orchestrator-controller | 候補 | `orchestrator/session.go::tmuxRun` → `orchestrator/controller.go::Controller.Run`(候補) |
| MODULE-orchestrator-session | MODULE-orchestrator-mode | 確定 | `orchestrator/session.go::SessionManager.LaunchInteractive` → `orchestrator/mode.go::shellSingleQuote` |
| MODULE-orchestrator-state | MODULE-orchestrator-state-io | 確定 | `orchestrator/state.go::Store.LoadPlan` → `orchestrator/state.go::readJSON`, `orchestrator/state.go::Store.LoadState` → `orchestrator/state.go::readJSON`, `orchestrator/state.go::Store.SavePlan` → `orchestrator/state.go::writeJSONAtomic` ほか 2 件 |
| MODULE-orchestrator-state-intervention | MODULE-orchestrator-state | 確定 | `orchestrator/mode.go::Store.ReadQuestion` → `orchestrator/state.go::Store.path`, `orchestrator/state.go::Store.AppendAssumption` → `orchestrator/state.go::Store.path`, `orchestrator/state.go::Store.AppendAudit` → `orchestrator/state.go::Store.path` ほか 9 件 |
| MODULE-orchestrator-state-intervention | MODULE-orchestrator-state-io | 確定 | `orchestrator/state.go::Store.AppendAssumption` → `orchestrator/state.go::appendJSONL`, `orchestrator/state.go::Store.AppendAudit` → `orchestrator/state.go::appendJSONL`, `orchestrator/state.go::Store.AppendIntervention` → `orchestrator/state.go::appendJSONL` ほか 5 件 |
| MODULE-orchestrator-term | MODULE-orchestrator-controller | 候補 | `orchestrator/term.go::sttyRun` → `orchestrator/controller.go::Controller.Run`(候補) |
| MODULE-orchestrator-term | MODULE-orchestrator-session | 候補 | `orchestrator/term.go::sttyRun` → `orchestrator/session.go::SessionManager.Run`(候補) |
| MODULE-orchestrator-worker | MODULE-orchestrator-state | 確定 | `orchestrator/worker.go::Worker.BuildPrompt` → `orchestrator/state.go::LoadProjectPolicy`, `orchestrator/worker.go::Worker.BuildPrompt` → `orchestrator/state.go::VMModePreamble`, `orchestrator/worker.go::Worker.Dispatch` → `orchestrator/state.go::Store.WorkerLogPath` ほか 1 件 |
| MODULE-orchestrator-worker | MODULE-orchestrator-state-intervention | 確定 | `orchestrator/worker.go::Worker.Dispatch` → `orchestrator/state.go::Store.AppendAudit` |
| MODULE-orchestrator-worker | MODULE-orchestrator-worktree | 確定 | `orchestrator/worker.go::Worker.Dispatch` → `orchestrator/worker.go::Worker.PrepareWorktree` |
| MODULE-orchestrator-worktree | MODULE-orchestrator-state | 確定 | `orchestrator/worker.go::Worker.PrepareWorktree` → `orchestrator/state.go::Store.WorktreeAbs`, `orchestrator/worker.go::Worker.PrepareWorktree` → `orchestrator/state.go::Store.WorktreeRel` |

## 複数機能から到達される共有関数(境界の実体)

ファンインが2以上の関数は機能の内部ヘルパではありえない(`.claude/directions/features.md` §4)。
機能表に足すとルートに昇格し、呼んでいた側に `callees` の辺が1本立つ。
**昇格させるかは人間の判断。**

| シンボル | ファンイン | 到達元の機能 |
|---|---|---|
| `claude-dev-mac::net_other_running_containers` | 3 | MODULE-cli-logout, MODULE-cli-reset, MODULE-cli-stop |
| `claude-dev::net_other_running_containers` | 3 | MODULE-cli-logout, MODULE-cli-reset, MODULE-cli-stop |
| `orchestrator/dashboard.go::oneline` | 3 | MODULE-orchestrator-controller, MODULE-orchestrator-dashboard, MODULE-orchestrator-streamlog |
| `claude-dev-mac::compose_project_name` | 2 | MODULE-cli-start, MODULE-cli-stop |
| `claude-dev-mac::compose_project_name_legacy` | 2 | MODULE-cli-start, MODULE-cli-stop |
| `claude-dev-mac::container_project_dir` | 2 | MODULE-cli-start, MODULE-cli-stop |
| `claude-dev-mac::destructive_abort_if_interrupted` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev-mac::destructive_arm_interrupt` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev-mac::destructive_deleted` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev-mac::destructive_failed` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev-mac::destructive_plan` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev-mac::destructive_report` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev-mac::destructive_rm` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev-mac::destructive_skipped` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev-mac::sha256_hex` | 2 | MODULE-cli-start, MODULE-cli-stop |
| `claude-dev::compose_project_name` | 2 | MODULE-cli-start, MODULE-cli-stop |
| `claude-dev::compose_project_name_legacy` | 2 | MODULE-cli-start, MODULE-cli-stop |
| `claude-dev::container_project_dir` | 2 | MODULE-cli-start, MODULE-cli-stop |
| `claude-dev::destructive_abort_if_interrupted` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev::destructive_arm_interrupt` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev::destructive_deleted` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev::destructive_failed` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev::destructive_plan` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev::destructive_report` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev::destructive_rm` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev::destructive_skipped` | 2 | MODULE-cli-logout, MODULE-cli-reset |
| `claude-dev::sha256_hex` | 2 | MODULE-cli-start, MODULE-cli-stop |

## どの入口からも到達しない関数

**候補辺も算入した上で**到達しない(`.claude/directions/features.md` §5:「無い」の主張は広く)。到達不能コードの候補だが、**削ってよいかは決めない** — 動的呼び出し・外部からの参照・ツール未対応の可能性がある。

| シンボル |
|---|
| `claude-dev-mac::_destructive_done` |
| `claude-dev-mac::_release_all_locks` |
| `claude-dev-mac::main` |
| `claude-dev::_destructive_done` |
| `claude-dev::_release_all_locks` |
| `claude-dev::main` |
| `docker-proxy/main.go::cachedResolveProjectDir` |
| `docker-proxy/main.go::lookupProjectDir` |
| `orchestrator/controller.go::Controller.openInterventionCount` |
| `orchestrator/controller.go::Controller.resolveInterventions` |
| `orchestrator/controller.go::Controller.resolveOne` |
| `orchestrator/dashboard.go::DashboardState.SelectableWorker` |
| `orchestrator/dashboard.go::DashboardState.SelectableWorkerStatus` |
| `orchestrator/dashboard.go::selectableWorker` |
| `orchestrator/dashboard.go::selectableWorkerID` |
| `orchestrator/main.go::terminalConfirm` |
| `orchestrator/state.go::Store.RemoveSidecar` |
| `orchestrator/state.go::Store.SaveControl` |
| `orchestrator/term.go::resolveMenu` |

## 同じ資源を触るのに呼び出し辺が無い機能

サーバレス/イベント駆動では、連携の相当部分が**呼び出し辺として原理的に存在しない**。
A がテーブルに書き B が読む — 呼び出しは1本も無いが、B は A の書式に依存している。
この結合は callgraph に出ないので、**CG4(取りこぼし検出)の網にかからない**。
資源そのものは `docs/03-impl/callgraphs/resources.md`。

- 2つ以上の機能が触る資源: 0
- そのうち**呼び出し辺で繋がっていない機能対**を含むもの: 0(対の総数 0)
- 広域共有資源(機能の 50% 以上が触る): 0 — **指摘からは外している**(全機能が触る資源に対の一覧を出しても読めないため。行としては下表に残る)
- どの機能にも属さないシンボルからの参照: 0(入口の登録漏れか、機能から到達しないコード)

**書き込みが絡む結合は「片方の書式に他方が依存する」**ので重大度は中、
読み取りだけなら共有された読み取りモデルなので参考に落としてある。

| 資源 | 触る機能 | 辺の無い対 | 重大度 | 書き込む機能(書式の持ち主) | 読むだけの機能(依存側) |
|---|---|---|---|---|---|
| (なし) | - | - | - | - | - |

**書き込む機能が書式を決め、読む機能がそれに依存する。**呼び出し辺が無いので、書式を変えても機械的には誰も気付かない — そこを relations の本文(戻り値・副作用 / 連携先と連携内容)で埋める。
個々の機能対は `--format json` の `resource_coupling.resources[].unlinked_pairs` に全部ある。

