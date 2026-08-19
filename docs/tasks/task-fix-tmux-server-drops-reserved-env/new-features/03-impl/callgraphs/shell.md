---
id: shell
language: shell
tier: 3
symbols: 178
edges: 273
endpoints: 46
unresolved: 3
---

<!-- BEGIN NOTE: build-callgraphs.py -->
<!-- 生成物。手書き禁止。`CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) && python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT"` で再生成する。
     辞書順に固定されており、実装が変わらなければこのファイルも変わらない。
     **これは機能間連携仕様書ではない**(.claude/directions/callgraphs.md)。 -->
<!-- END NOTE: build-callgraphs.py -->

# shell コールグラフ (Tier 3)

## エントリポイント

| 種別 | 識別子 | 正規化キー | ハンドラ | 検出根拠 |
|---|---|---|---|---|
| cli | `dispatch --loop @ scripts/dood-portsync.sh::main` | `/dood-portsync.sh/--loop` | `scripts/dood-portsync.sh::main#--loop` | scripts/dood-portsync.sh |
| cli | `dispatch --loop @ scripts/vm-healthd.sh::main` | `/vm-healthd.sh/--loop` | `scripts/vm-healthd.sh::main#--loop` | scripts/vm-healthd.sh |
| cli | `dispatch --loop @ scripts/vm-portsync.sh::main` | `/vm-portsync.sh/--loop` | `scripts/vm-portsync.sh::main#--loop` | scripts/vm-portsync.sh |
| cli | `dispatch attach @ claude-dev-mac::main` | `/claude-dev-mac/attach` | `claude-dev-mac::main#attach` | claude-dev-mac |
| cli | `dispatch attach @ claude-dev::main` | `/claude-dev/attach` | `claude-dev::main#attach` | claude-dev |
| cli | `dispatch code @ claude-dev-mac::main` | `/claude-dev-mac/code` | `claude-dev-mac::main#code` | claude-dev-mac |
| cli | `dispatch code @ claude-dev::main` | `/claude-dev/code` | `claude-dev::main#code` | claude-dev |
| cli | `dispatch entrypoint-claude.sh @ scripts/entrypoint-claude.sh::main` | `/entrypoint-claude.sh` | `scripts/entrypoint-claude.sh::main` | scripts/entrypoint-claude.sh |
| cli | `dispatch firewall @ claude-dev-mac::main` | `/claude-dev-mac/firewall` | `claude-dev-mac::main#firewall` | claude-dev-mac |
| cli | `dispatch firewall @ claude-dev::main` | `/claude-dev/firewall` | `claude-dev::main#firewall` | claude-dev |
| cli | `dispatch forward @ claude-dev-mac::main` | `/claude-dev-mac/forward` | `claude-dev-mac::main#forward` | claude-dev-mac |
| cli | `dispatch forward @ claude-dev::main` | `/claude-dev/forward` | `claude-dev::main#forward` | claude-dev |
| cli | `dispatch init-firewall-claude.sh @ scripts/init-firewall-claude.sh::main` | `/init-firewall-claude.sh` | `scripts/init-firewall-claude.sh::main` | scripts/init-firewall-claude.sh |
| cli | `dispatch list @ claude-dev-mac::main` | `/claude-dev-mac/list` | `claude-dev-mac::main#list` | claude-dev-mac |
| cli | `dispatch list @ claude-dev::main` | `/claude-dev/list` | `claude-dev::main#list` | claude-dev |
| cli | `dispatch login @ claude-dev-mac::main` | `/claude-dev-mac/login` | `claude-dev-mac::main#login` | claude-dev-mac |
| cli | `dispatch login @ claude-dev::main` | `/claude-dev/login` | `claude-dev::main#login` | claude-dev |
| cli | `dispatch login-codex @ claude-dev-mac::main` | `/claude-dev-mac/login-codex` | `claude-dev-mac::main#login-codex` | claude-dev-mac |
| cli | `dispatch login-codex @ claude-dev::main` | `/claude-dev/login-codex` | `claude-dev::main#login-codex` | claude-dev |
| cli | `dispatch logout @ claude-dev-mac::main` | `/claude-dev-mac/logout` | `claude-dev-mac::main#logout` | claude-dev-mac |
| cli | `dispatch logout @ claude-dev::main` | `/claude-dev/logout` | `claude-dev::main#logout` | claude-dev |
| cli | `dispatch ports @ claude-dev-mac::main` | `/claude-dev-mac/ports` | `claude-dev-mac::main#ports` | claude-dev-mac |
| cli | `dispatch ports @ claude-dev::main` | `/claude-dev/ports` | `claude-dev::main#ports` | claude-dev |
| cli | `dispatch pull @ claude-dev-mac::main` | `/claude-dev-mac/pull` | `claude-dev-mac::main#pull` | claude-dev-mac |
| cli | `dispatch pull @ claude-dev::main` | `/claude-dev/pull` | `claude-dev::main#pull` | claude-dev |
| cli | `dispatch reset @ claude-dev-mac::main` | `/claude-dev-mac/reset` | `claude-dev-mac::main#reset` | claude-dev-mac |
| cli | `dispatch reset @ claude-dev::main` | `/claude-dev/reset` | `claude-dev::main#reset` | claude-dev |
| cli | `dispatch setup @ claude-dev-mac::main` | `/claude-dev-mac/setup` | `claude-dev-mac::main#setup` | claude-dev-mac |
| cli | `dispatch setup @ claude-dev::main` | `/claude-dev/setup` | `claude-dev::main#setup` | claude-dev |
| cli | `dispatch ssh-keys @ claude-dev-mac::main` | `/claude-dev-mac/ssh-keys` | `claude-dev-mac::main#ssh-keys` | claude-dev-mac |
| cli | `dispatch ssh-keys @ claude-dev::main` | `/claude-dev/ssh-keys` | `claude-dev::main#ssh-keys` | claude-dev |
| cli | `dispatch ssh-keys.reset @ claude-dev-mac::main` | `/claude-dev-mac/ssh-keys/reset` | `claude-dev-mac::main#ssh-keys.reset` | claude-dev-mac |
| cli | `dispatch ssh-keys.reset @ claude-dev::main` | `/claude-dev/ssh-keys/reset` | `claude-dev::main#ssh-keys.reset` | claude-dev |
| cli | `dispatch ssh-keys.select @ claude-dev-mac::main` | `/claude-dev-mac/ssh-keys/select` | `claude-dev-mac::main#ssh-keys.select` | claude-dev-mac |
| cli | `dispatch ssh-keys.select @ claude-dev::main` | `/claude-dev/ssh-keys/select` | `claude-dev::main#ssh-keys.select` | claude-dev |
| cli | `dispatch start @ claude-dev-mac::main` | `/claude-dev-mac/start` | `claude-dev-mac::main#start` | claude-dev-mac |
| cli | `dispatch start @ claude-dev::main` | `/claude-dev/start` | `claude-dev::main#start` | claude-dev |
| cli | `dispatch stop @ claude-dev-mac::main` | `/claude-dev-mac/stop` | `claude-dev-mac::main#stop` | claude-dev-mac |
| cli | `dispatch stop @ claude-dev::main` | `/claude-dev/stop` | `claude-dev::main#stop` | claude-dev |
| cli | `dispatch unforward @ claude-dev-mac::main` | `/claude-dev-mac/unforward` | `claude-dev-mac::main#unforward` | claude-dev-mac |
| cli | `dispatch unforward @ claude-dev::main` | `/claude-dev/unforward` | `claude-dev::main#unforward` | claude-dev |
| cli | `dispatch upgrade @ claude-dev-mac::main` | `/claude-dev-mac/upgrade` | `claude-dev-mac::main#upgrade` | claude-dev-mac |
| cli | `dispatch upgrade @ claude-dev::main` | `/claude-dev/upgrade` | `claude-dev::main#upgrade` | claude-dev |
| cli | `dispatch vm @ scripts/vm::main` | `/vm` | `scripts/vm::main` | scripts/vm |
| cli | `dispatch vm-up.sh @ scripts/vm-up.sh::main` | `/vm-up.sh` | `scripts/vm-up.sh::main` | scripts/vm-up.sh |
| cli | `dispatch wait-limit-reset.sh @ scripts/wait-limit-reset.sh::main` | `/wait-limit-reset.sh` | `scripts/wait-limit-reset.sh::main` | scripts/wait-limit-reset.sh |

## 関数表

| シンボル | 種別 | 可視性 | 呼び出す先 | 呼び出し元 |
|---|---|---|---|---|
| `claude-dev-mac::_destructive_done` | function | private | - | - |
| `claude-dev-mac::_env_name_is_reserved` | function | private | - | `claude-dev-mac::load_project_env_file` |
| `claude-dev-mac::_lock_busy_message` | function | private | - | `claude-dev-mac::acquire_lock` |
| `claude-dev-mac::_lock_link` | function | private | - | `claude-dev-mac::acquire_lock` |
| `claude-dev-mac::_lock_path` | function | private | - | `claude-dev-mac::acquire_lock`, `claude-dev-mac::release_lock` |
| `claude-dev-mac::_parse_env_file_key` | function | private | - | `claude-dev-mac::load_project_env_file` |
| `claude-dev-mac::_parse_ssh_keys_yaml` | function | private | - | `claude-dev-mac::resolve_ssh_keys_for_start` |
| `claude-dev-mac::_release_all_locks` | function | private | `claude-dev-mac::_release_lock_path` | - |
| `claude-dev-mac::_release_lock_path` | function | private | - | `claude-dev-mac::_release_all_locks`, `claude-dev-mac::release_lock` |
| `claude-dev-mac::_strip_ssh_keys_section` | function | private | - | `claude-dev-mac::main#ssh-keys.reset`, `claude-dev-mac::write_project_ssh_keys` |
| `claude-dev-mac::acquire_lock` | function | private | `claude-dev-mac::_lock_busy_message`, `claude-dev-mac::_lock_link`, `claude-dev-mac::_lock_path` | `claude-dev-mac::main#login`, `claude-dev-mac::main#login-codex`, `claude-dev-mac::main#logout`, `claude-dev-mac::main#reset`, `claude-dev-mac::main#start`, `claude-dev-mac::main#stop` |
| `claude-dev-mac::check_host_deps` | function | private | - | `claude-dev-mac::main#start` |
| `claude-dev-mac::compose_project_name` | function | private | `claude-dev-mac::compose_project_name_legacy`, `claude-dev-mac::sha256_hex` | `claude-dev-mac::main#start`, `claude-dev-mac::main#stop` |
| `claude-dev-mac::compose_project_name_legacy` | function | private | - | `claude-dev-mac::compose_project_name`, `claude-dev-mac::main#stop` |
| `claude-dev-mac::container_exists` | function | private | - | `claude-dev-mac::ensure_docker_proxy_container`, `claude-dev-mac::main#forward`, `claude-dev-mac::main#logout`, `claude-dev-mac::main#reset`, `claude-dev-mac::main#start`, `claude-dev-mac::main#stop`, `claude-dev-mac::main#unforward` |
| `claude-dev-mac::container_is_managed` | function | private | - | `claude-dev-mac::main#stop` |
| `claude-dev-mac::container_name` | function | private | `claude-dev-mac::project_name` | `claude-dev-mac::main#attach`, `claude-dev-mac::main#code`, `claude-dev-mac::main#firewall`, `claude-dev-mac::main#forward`, `claude-dev-mac::main#ports`, `claude-dev-mac::main#ssh-keys.reset`, `claude-dev-mac::main#start`, `claude-dev-mac::main#stop`, `claude-dev-mac::main#unforward` |
| `claude-dev-mac::container_project_dir` | function | private | - | `claude-dev-mac::main#start`, `claude-dev-mac::main#stop` |
| `claude-dev-mac::destructive_abort_if_interrupted` | function | private | `claude-dev-mac::destructive_report` | `claude-dev-mac::main#logout`, `claude-dev-mac::main#reset` |
| `claude-dev-mac::destructive_arm_interrupt` | function | private | - | `claude-dev-mac::main#logout`, `claude-dev-mac::main#reset` |
| `claude-dev-mac::destructive_deleted` | function | private | - | `claude-dev-mac::destructive_rm`, `claude-dev-mac::main#logout` |
| `claude-dev-mac::destructive_failed` | function | private | - | `claude-dev-mac::destructive_rm`, `claude-dev-mac::main#logout`, `claude-dev-mac::main#reset` |
| `claude-dev-mac::destructive_plan` | function | private | - | `claude-dev-mac::main#logout`, `claude-dev-mac::main#reset` |
| `claude-dev-mac::destructive_report` | function | private | - | `claude-dev-mac::destructive_abort_if_interrupted`, `claude-dev-mac::main#logout`, `claude-dev-mac::main#reset` |
| `claude-dev-mac::destructive_rm` | function | private | `claude-dev-mac::destructive_deleted`, `claude-dev-mac::destructive_failed` | `claude-dev-mac::main#logout`, `claude-dev-mac::main#reset` |
| `claude-dev-mac::destructive_skipped` | function | private | - | `claude-dev-mac::main#logout`, `claude-dev-mac::main#reset` |
| `claude-dev-mac::detect_docker_sock` | function | private | - | `claude-dev-mac::ensure_docker_proxy_container`, `claude-dev-mac::main#start` |
| `claude-dev-mac::dev_agent_path` | function | private | - | `claude-dev-mac::ensure_dedicated_agent`, `claude-dev-mac::ensure_ssh_bridge`, `claude-dev-mac::main#ssh-keys.reset`, `claude-dev-mac::stop_ssh_bridge` |
| `claude-dev-mac::discover_ssh_keys` | function | private | - | `claude-dev-mac::select_ssh_keys_interactive` |
| `claude-dev-mac::ensure_dedicated_agent` | function | private | `claude-dev-mac::dev_agent_path` | `claude-dev-mac::main#start` |
| `claude-dev-mac::ensure_docker_proxy_container` | function | private | `claude-dev-mac::container_exists`, `claude-dev-mac::detect_docker_sock`, `claude-dev-mac::image_exists`, `claude-dev-mac::is_running` | `claude-dev-mac::main#start` |
| `claude-dev-mac::ensure_infrastructure` | function | private | - | `claude-dev-mac::main#login`, `claude-dev-mac::main#login-codex`, `claude-dev-mac::main#start` |
| `claude-dev-mac::ensure_project_config` | function | private | `claude-dev-mac::select_ssh_keys_interactive`, `claude-dev-mac::write_project_ssh_keys` | `claude-dev-mac::main#start` |
| `claude-dev-mac::ensure_ssh_bridge` | function | private | `claude-dev-mac::dev_agent_path`, `claude-dev-mac::find_free_local_port` | `claude-dev-mac::main#start` |
| `claude-dev-mac::find_available_host_port` | function | private | - | `claude-dev-mac::main#forward` |
| `claude-dev-mac::find_available_novnc_port` | function | private | - | `claude-dev-mac::main#start` |
| `claude-dev-mac::find_free_local_port` | function | private | - | `claude-dev-mac::ensure_ssh_bridge` |
| `claude-dev-mac::get_novnc_url` | function | private | - | `claude-dev-mac::main#list`, `claude-dev-mac::main#ports`, `claude-dev-mac::main#start` |
| `claude-dev-mac::image_exists` | function | private | - | `claude-dev-mac::ensure_docker_proxy_container`, `claude-dev-mac::main#reset`, `claude-dev-mac::require_setup` |
| `claude-dev-mac::image_version` | function | private | - | `claude-dev-mac::main#start` |
| `claude-dev-mac::is_running` | function | private | - | `claude-dev-mac::ensure_docker_proxy_container`, `claude-dev-mac::main#attach`, `claude-dev-mac::main#code`, `claude-dev-mac::main#firewall`, `claude-dev-mac::main#forward`, `claude-dev-mac::main#list`, `claude-dev-mac::main#ports`, `claude-dev-mac::main#start`, `claude-dev-mac::stop_proxy_if_idle` |
| `claude-dev-mac::load_project_env_file` | function | private | `claude-dev-mac::_env_name_is_reserved`, `claude-dev-mac::_parse_env_file_key` | `claude-dev-mac::main#start` |
| `claude-dev-mac::main` | handler | private | - | - |
| `claude-dev-mac::main#attach` | handler | private | `claude-dev-mac::container_name`, `claude-dev-mac::is_running`, `claude-dev-mac::require_setup`, `claude-dev-mac::resolve_container_user` | (エントリポイント) |
| `claude-dev-mac::main#code` | handler | private | `claude-dev-mac::container_name`, `claude-dev-mac::is_running`, `claude-dev-mac::require_setup`, `claude-dev-mac::resolve_container_user` | (エントリポイント) |
| `claude-dev-mac::main#firewall` | handler | private | `claude-dev-mac::container_name`, `claude-dev-mac::is_running` | (エントリポイント) |
| `claude-dev-mac::main#forward` | handler | private | `claude-dev-mac::container_exists`, `claude-dev-mac::container_name`, `claude-dev-mac::find_available_host_port`, `claude-dev-mac::is_running` | (エントリポイント) |
| `claude-dev-mac::main#list` | handler | private | `claude-dev-mac::get_novnc_url`, `claude-dev-mac::is_running` | (エントリポイント) |
| `claude-dev-mac::main#login` | handler | private | `claude-dev-mac::acquire_lock`, `claude-dev-mac::ensure_infrastructure`, `claude-dev-mac::release_lock`, `claude-dev-mac::require_setup` | (エントリポイント) |
| `claude-dev-mac::main#login-codex` | handler | private | `claude-dev-mac::acquire_lock`, `claude-dev-mac::ensure_infrastructure`, `claude-dev-mac::release_lock`, `claude-dev-mac::require_setup` | (エントリポイント) |
| `claude-dev-mac::main#logout` | handler | private | `claude-dev-mac::acquire_lock`, `claude-dev-mac::container_exists`, `claude-dev-mac::destructive_abort_if_interrupted`, `claude-dev-mac::destructive_arm_interrupt`, `claude-dev-mac::destructive_deleted`, `claude-dev-mac::destructive_failed`, `claude-dev-mac::destructive_plan`, `claude-dev-mac::destructive_report`, `claude-dev-mac::destructive_rm`, `claude-dev-mac::destructive_skipped`, `claude-dev-mac::net_other_running_containers`, `claude-dev-mac::release_lock`, `claude-dev-mac::require_setup`, `claude-dev-mac::spawned_resources` | (エントリポイント) |
| `claude-dev-mac::main#ports` | handler | private | `claude-dev-mac::container_name`, `claude-dev-mac::get_novnc_url`, `claude-dev-mac::is_running` | (エントリポイント) |
| `claude-dev-mac::main#pull` | handler | private | - | (エントリポイント) |
| `claude-dev-mac::main#reset` | handler | private | `claude-dev-mac::acquire_lock`, `claude-dev-mac::container_exists`, `claude-dev-mac::destructive_abort_if_interrupted`, `claude-dev-mac::destructive_arm_interrupt`, `claude-dev-mac::destructive_failed`, `claude-dev-mac::destructive_plan`, `claude-dev-mac::destructive_report`, `claude-dev-mac::destructive_rm`, `claude-dev-mac::destructive_skipped`, `claude-dev-mac::image_exists`, `claude-dev-mac::net_other_running_containers`, `claude-dev-mac::release_lock`, `claude-dev-mac::spawned_resources` | (エントリポイント) |
| `claude-dev-mac::main#setup` | handler | private | - | (エントリポイント) |
| `claude-dev-mac::main#ssh-keys` | handler | private | - | (エントリポイント) |
| `claude-dev-mac::main#ssh-keys.reset` | handler | private | `claude-dev-mac::_strip_ssh_keys_section`, `claude-dev-mac::container_name`, `claude-dev-mac::dev_agent_path` | (エントリポイント) |
| `claude-dev-mac::main#ssh-keys.select` | handler | private | `claude-dev-mac::select_ssh_keys_interactive` | (エントリポイント) |
| `claude-dev-mac::main#start` | handler | private | `claude-dev-mac::acquire_lock`, `claude-dev-mac::check_host_deps`, `claude-dev-mac::compose_project_name`, `claude-dev-mac::container_exists`, `claude-dev-mac::container_name`, `claude-dev-mac::container_project_dir`, `claude-dev-mac::detect_docker_sock`, `claude-dev-mac::ensure_dedicated_agent`, `claude-dev-mac::ensure_docker_proxy_container`, `claude-dev-mac::ensure_infrastructure`, `claude-dev-mac::ensure_project_config`, `claude-dev-mac::ensure_ssh_bridge`, `claude-dev-mac::find_available_novnc_port`, `claude-dev-mac::get_novnc_url`, `claude-dev-mac::image_version`, `claude-dev-mac::is_running`, `claude-dev-mac::load_project_env_file`, `claude-dev-mac::release_lock`, `claude-dev-mac::require_setup`, `claude-dev-mac::resolve_container_user`, `claude-dev-mac::resolve_ssh_keys_for_start` | (エントリポイント) |
| `claude-dev-mac::main#stop` | handler | private | `claude-dev-mac::acquire_lock`, `claude-dev-mac::compose_project_name`, `claude-dev-mac::compose_project_name_legacy`, `claude-dev-mac::container_exists`, `claude-dev-mac::container_is_managed`, `claude-dev-mac::container_name`, `claude-dev-mac::container_project_dir`, `claude-dev-mac::release_lock`, `claude-dev-mac::spawned_resources`, `claude-dev-mac::stop_proxy_if_idle`, `claude-dev-mac::stop_ssh_bridge` | (エントリポイント) |
| `claude-dev-mac::main#unforward` | handler | private | `claude-dev-mac::container_exists`, `claude-dev-mac::container_name` | (エントリポイント) |
| `claude-dev-mac::main#upgrade` | handler | private | - | (エントリポイント) |
| `claude-dev-mac::net_other_running_containers` | function | private | - | `claude-dev-mac::main#logout`, `claude-dev-mac::main#reset`, `claude-dev-mac::stop_proxy_if_idle` |
| `claude-dev-mac::project_name` | function | private | - | `claude-dev-mac::container_name` |
| `claude-dev-mac::release_lock` | function | private | `claude-dev-mac::_lock_path`, `claude-dev-mac::_release_lock_path` | `claude-dev-mac::main#login`, `claude-dev-mac::main#login-codex`, `claude-dev-mac::main#logout`, `claude-dev-mac::main#reset`, `claude-dev-mac::main#start`, `claude-dev-mac::main#stop` |
| `claude-dev-mac::require_setup` | function | private | `claude-dev-mac::image_exists` | `claude-dev-mac::main#attach`, `claude-dev-mac::main#code`, `claude-dev-mac::main#login`, `claude-dev-mac::main#login-codex`, `claude-dev-mac::main#logout`, `claude-dev-mac::main#start` |
| `claude-dev-mac::resolve_container_user` | function | private | - | `claude-dev-mac::main#attach`, `claude-dev-mac::main#code`, `claude-dev-mac::main#start` |
| `claude-dev-mac::resolve_ssh_keys_for_start` | function | private | `claude-dev-mac::_parse_ssh_keys_yaml` | `claude-dev-mac::main#start` |
| `claude-dev-mac::select_ssh_keys_interactive` | function | private | `claude-dev-mac::discover_ssh_keys`, `claude-dev-mac::write_project_ssh_keys` | `claude-dev-mac::ensure_project_config`, `claude-dev-mac::main#ssh-keys.select` |
| `claude-dev-mac::sha256_hex` | function | private | - | `claude-dev-mac::compose_project_name` |
| `claude-dev-mac::spawned_resources` | function | private | - | `claude-dev-mac::main#logout`, `claude-dev-mac::main#reset`, `claude-dev-mac::main#stop` |
| `claude-dev-mac::stop_proxy_if_idle` | function | private | `claude-dev-mac::is_running`, `claude-dev-mac::net_other_running_containers` | `claude-dev-mac::main#stop` |
| `claude-dev-mac::stop_ssh_bridge` | function | private | `claude-dev-mac::dev_agent_path` | `claude-dev-mac::main#stop` |
| `claude-dev-mac::write_project_ssh_keys` | function | private | `claude-dev-mac::_strip_ssh_keys_section` | `claude-dev-mac::ensure_project_config`, `claude-dev-mac::select_ssh_keys_interactive` |
| `claude-dev::_destructive_done` | function | private | - | - |
| `claude-dev::_env_name_is_reserved` | function | private | - | `claude-dev::load_project_env_file` |
| `claude-dev::_lock_busy_message` | function | private | - | `claude-dev::acquire_lock` |
| `claude-dev::_lock_link` | function | private | - | `claude-dev::acquire_lock` |
| `claude-dev::_lock_path` | function | private | - | `claude-dev::acquire_lock`, `claude-dev::release_lock` |
| `claude-dev::_parse_env_file_key` | function | private | - | `claude-dev::load_project_env_file` |
| `claude-dev::_parse_ssh_keys_yaml` | function | private | - | `claude-dev::load_ssh_keys_from_config` |
| `claude-dev::_release_all_locks` | function | private | `claude-dev::_release_lock_path` | - |
| `claude-dev::_release_lock_path` | function | private | - | `claude-dev::_release_all_locks`, `claude-dev::release_lock` |
| `claude-dev::_strip_ssh_keys_section` | function | private | - | `claude-dev::main#ssh-keys.reset`, `claude-dev::write_project_ssh_keys` |
| `claude-dev::acquire_lock` | function | private | `claude-dev::_lock_busy_message`, `claude-dev::_lock_link`, `claude-dev::_lock_path` | `claude-dev::main#login`, `claude-dev::main#login-codex`, `claude-dev::main#logout`, `claude-dev::main#reset`, `claude-dev::main#start`, `claude-dev::main#stop` |
| `claude-dev::check_host_deps` | function | private | - | `claude-dev::main#start` |
| `claude-dev::compose_project_name` | function | private | `claude-dev::compose_project_name_legacy`, `claude-dev::sha256_hex` | `claude-dev::main#start`, `claude-dev::main#stop` |
| `claude-dev::compose_project_name_legacy` | function | private | - | `claude-dev::compose_project_name`, `claude-dev::main#stop` |
| `claude-dev::container_exists` | function | private | - | `claude-dev::ensure_docker_proxy_container`, `claude-dev::main#forward`, `claude-dev::main#logout`, `claude-dev::main#reset`, `claude-dev::main#start`, `claude-dev::main#stop`, `claude-dev::main#unforward` |
| `claude-dev::container_is_managed` | function | private | - | `claude-dev::main#stop` |
| `claude-dev::container_name` | function | private | `claude-dev::project_name` | `claude-dev::main#attach`, `claude-dev::main#code`, `claude-dev::main#firewall`, `claude-dev::main#forward`, `claude-dev::main#ports`, `claude-dev::main#ssh-keys`, `claude-dev::main#start`, `claude-dev::main#stop`, `claude-dev::main#unforward` |
| `claude-dev::container_project_dir` | function | private | - | `claude-dev::main#start`, `claude-dev::main#stop` |
| `claude-dev::destructive_abort_if_interrupted` | function | private | `claude-dev::destructive_report` | `claude-dev::main#logout`, `claude-dev::main#reset` |
| `claude-dev::destructive_arm_interrupt` | function | private | - | `claude-dev::main#logout`, `claude-dev::main#reset` |
| `claude-dev::destructive_deleted` | function | private | - | `claude-dev::destructive_rm`, `claude-dev::main#logout` |
| `claude-dev::destructive_failed` | function | private | - | `claude-dev::destructive_rm`, `claude-dev::main#logout`, `claude-dev::main#reset` |
| `claude-dev::destructive_plan` | function | private | - | `claude-dev::main#logout`, `claude-dev::main#reset` |
| `claude-dev::destructive_report` | function | private | - | `claude-dev::destructive_abort_if_interrupted`, `claude-dev::main#logout`, `claude-dev::main#reset` |
| `claude-dev::destructive_rm` | function | private | `claude-dev::destructive_deleted`, `claude-dev::destructive_failed` | `claude-dev::main#logout`, `claude-dev::main#reset` |
| `claude-dev::destructive_skipped` | function | private | - | `claude-dev::main#logout`, `claude-dev::main#reset` |
| `claude-dev::discover_ssh_keys` | function | private | - | `claude-dev::select_ssh_keys_interactive` |
| `claude-dev::ensure_docker_proxy_container` | function | private | `claude-dev::container_exists`, `claude-dev::image_exists`, `claude-dev::is_running` | `claude-dev::main#start` |
| `claude-dev::ensure_infrastructure` | function | private | - | `claude-dev::main#login`, `claude-dev::main#login-codex`, `claude-dev::main#start` |
| `claude-dev::ensure_project_config` | function | private | `claude-dev::select_ssh_keys_interactive`, `claude-dev::write_project_ssh_keys` | `claude-dev::main#start` |
| `claude-dev::ensure_ssh_agent` | function | private | `claude-dev::load_ssh_keys_from_config` | `claude-dev::main#start` |
| `claude-dev::find_available_host_port` | function | private | - | `claude-dev::main#forward` |
| `claude-dev::find_available_novnc_port` | function | private | - | `claude-dev::main#start` |
| `claude-dev::get_novnc_url` | function | private | - | `claude-dev::main#list`, `claude-dev::main#ports`, `claude-dev::main#start` |
| `claude-dev::image_exists` | function | private | - | `claude-dev::ensure_docker_proxy_container`, `claude-dev::main#reset`, `claude-dev::require_setup` |
| `claude-dev::image_version` | function | private | - | `claude-dev::main#start` |
| `claude-dev::is_running` | function | private | - | `claude-dev::ensure_docker_proxy_container`, `claude-dev::main#attach`, `claude-dev::main#code`, `claude-dev::main#firewall`, `claude-dev::main#forward`, `claude-dev::main#list`, `claude-dev::main#ports`, `claude-dev::main#start`, `claude-dev::stop_proxy_if_idle` |
| `claude-dev::load_project_env_file` | function | private | `claude-dev::_env_name_is_reserved`, `claude-dev::_parse_env_file_key` | `claude-dev::main#start` |
| `claude-dev::load_ssh_keys_from_config` | function | private | `claude-dev::_parse_ssh_keys_yaml` | `claude-dev::ensure_ssh_agent` |
| `claude-dev::main` | handler | private | - | - |
| `claude-dev::main#attach` | handler | private | `claude-dev::container_name`, `claude-dev::is_running`, `claude-dev::require_setup`, `claude-dev::resolve_container_user` | (エントリポイント) |
| `claude-dev::main#code` | handler | private | `claude-dev::container_name`, `claude-dev::is_running`, `claude-dev::require_setup`, `claude-dev::resolve_container_user` | (エントリポイント) |
| `claude-dev::main#firewall` | handler | private | `claude-dev::container_name`, `claude-dev::is_running` | (エントリポイント) |
| `claude-dev::main#forward` | handler | private | `claude-dev::container_exists`, `claude-dev::container_name`, `claude-dev::find_available_host_port`, `claude-dev::is_running` | (エントリポイント) |
| `claude-dev::main#list` | handler | private | `claude-dev::get_novnc_url`, `claude-dev::is_running` | (エントリポイント) |
| `claude-dev::main#login` | handler | private | `claude-dev::acquire_lock`, `claude-dev::ensure_infrastructure`, `claude-dev::release_lock`, `claude-dev::require_setup` | (エントリポイント) |
| `claude-dev::main#login-codex` | handler | private | `claude-dev::acquire_lock`, `claude-dev::ensure_infrastructure`, `claude-dev::release_lock`, `claude-dev::require_setup` | (エントリポイント) |
| `claude-dev::main#logout` | handler | private | `claude-dev::acquire_lock`, `claude-dev::container_exists`, `claude-dev::destructive_abort_if_interrupted`, `claude-dev::destructive_arm_interrupt`, `claude-dev::destructive_deleted`, `claude-dev::destructive_failed`, `claude-dev::destructive_plan`, `claude-dev::destructive_report`, `claude-dev::destructive_rm`, `claude-dev::destructive_skipped`, `claude-dev::net_other_running_containers`, `claude-dev::release_lock`, `claude-dev::require_setup`, `claude-dev::spawned_resources` | (エントリポイント) |
| `claude-dev::main#ports` | handler | private | `claude-dev::container_name`, `claude-dev::get_novnc_url`, `claude-dev::is_running` | (エントリポイント) |
| `claude-dev::main#pull` | handler | private | - | (エントリポイント) |
| `claude-dev::main#reset` | handler | private | `claude-dev::acquire_lock`, `claude-dev::container_exists`, `claude-dev::destructive_abort_if_interrupted`, `claude-dev::destructive_arm_interrupt`, `claude-dev::destructive_failed`, `claude-dev::destructive_plan`, `claude-dev::destructive_report`, `claude-dev::destructive_rm`, `claude-dev::destructive_skipped`, `claude-dev::image_exists`, `claude-dev::net_other_running_containers`, `claude-dev::release_lock`, `claude-dev::spawned_resources` | (エントリポイント) |
| `claude-dev::main#setup` | handler | private | - | (エントリポイント) |
| `claude-dev::main#ssh-keys` | handler | private | `claude-dev::container_name` | (エントリポイント) |
| `claude-dev::main#ssh-keys.reset` | handler | private | `claude-dev::_strip_ssh_keys_section` | (エントリポイント) |
| `claude-dev::main#ssh-keys.select` | handler | private | `claude-dev::select_ssh_keys_interactive` | (エントリポイント) |
| `claude-dev::main#start` | handler | private | `claude-dev::acquire_lock`, `claude-dev::check_host_deps`, `claude-dev::compose_project_name`, `claude-dev::container_exists`, `claude-dev::container_name`, `claude-dev::container_project_dir`, `claude-dev::ensure_docker_proxy_container`, `claude-dev::ensure_infrastructure`, `claude-dev::ensure_project_config`, `claude-dev::ensure_ssh_agent`, `claude-dev::find_available_novnc_port`, `claude-dev::get_novnc_url`, `claude-dev::image_version`, `claude-dev::is_running`, `claude-dev::load_project_env_file`, `claude-dev::release_lock`, `claude-dev::require_setup`, `claude-dev::resolve_container_user` | (エントリポイント) |
| `claude-dev::main#stop` | handler | private | `claude-dev::acquire_lock`, `claude-dev::compose_project_name`, `claude-dev::compose_project_name_legacy`, `claude-dev::container_exists`, `claude-dev::container_is_managed`, `claude-dev::container_name`, `claude-dev::container_project_dir`, `claude-dev::release_lock`, `claude-dev::spawned_resources`, `claude-dev::stop_proxy_if_idle` | (エントリポイント) |
| `claude-dev::main#unforward` | handler | private | `claude-dev::container_exists`, `claude-dev::container_name` | (エントリポイント) |
| `claude-dev::main#upgrade` | handler | private | - | (エントリポイント) |
| `claude-dev::net_other_running_containers` | function | private | - | `claude-dev::main#logout`, `claude-dev::main#reset`, `claude-dev::stop_proxy_if_idle` |
| `claude-dev::project_name` | function | private | - | `claude-dev::container_name` |
| `claude-dev::release_lock` | function | private | `claude-dev::_lock_path`, `claude-dev::_release_lock_path` | `claude-dev::main#login`, `claude-dev::main#login-codex`, `claude-dev::main#logout`, `claude-dev::main#reset`, `claude-dev::main#start`, `claude-dev::main#stop` |
| `claude-dev::require_setup` | function | private | `claude-dev::image_exists` | `claude-dev::main#attach`, `claude-dev::main#code`, `claude-dev::main#login`, `claude-dev::main#login-codex`, `claude-dev::main#logout`, `claude-dev::main#start` |
| `claude-dev::resolve_container_user` | function | private | - | `claude-dev::main#attach`, `claude-dev::main#code`, `claude-dev::main#start` |
| `claude-dev::select_ssh_keys_interactive` | function | private | `claude-dev::discover_ssh_keys`, `claude-dev::write_project_ssh_keys` | `claude-dev::ensure_project_config`, `claude-dev::main#ssh-keys.select` |
| `claude-dev::sha256_hex` | function | private | - | `claude-dev::compose_project_name` |
| `claude-dev::spawned_resources` | function | private | - | `claude-dev::main#logout`, `claude-dev::main#reset`, `claude-dev::main#stop` |
| `claude-dev::stop_proxy_if_idle` | function | private | `claude-dev::is_running`, `claude-dev::net_other_running_containers` | `claude-dev::main#stop` |
| `claude-dev::write_project_ssh_keys` | function | private | `claude-dev::_strip_ssh_keys_section` | `claude-dev::ensure_project_config`, `claude-dev::select_ssh_keys_interactive` |
| `scripts/dood-portsync.sh::is_excluded` | function | private | - | `scripts/dood-portsync.sh::sync_once` |
| `scripts/dood-portsync.sh::local_listening` | function | private | - | `scripts/dood-portsync.sh::sync_once` |
| `scripts/dood-portsync.sh::log` | function | private | - | `scripts/dood-portsync.sh::main`, `scripts/dood-portsync.sh::main#--loop`, `scripts/dood-portsync.sh::sync_once` |
| `scripts/dood-portsync.sh::main` | handler | private | `scripts/dood-portsync.sh::log`, `scripts/dood-portsync.sh::published_ports`, `scripts/dood-portsync.sh::sync_once` | - |
| `scripts/dood-portsync.sh::main#--loop` | handler | private | `scripts/dood-portsync.sh::log`, `scripts/dood-portsync.sh::sync_once` | (エントリポイント) |
| `scripts/dood-portsync.sh::published_ports` | function | private | - | `scripts/dood-portsync.sh::main`, `scripts/dood-portsync.sh::sync_once` |
| `scripts/dood-portsync.sh::sync_once` | function | private | `scripts/dood-portsync.sh::is_excluded`, `scripts/dood-portsync.sh::local_listening`, `scripts/dood-portsync.sh::log`, `scripts/dood-portsync.sh::published_ports` | `scripts/dood-portsync.sh::main`, `scripts/dood-portsync.sh::main#--loop` |
| `scripts/entrypoint-claude.sh::ensure_codex_config` | function | private | - | `scripts/entrypoint-claude.sh::main` |
| `scripts/entrypoint-claude.sh::main` | handler | private | `scripts/entrypoint-claude.sh::ensure_codex_config` | (エントリポイント) |
| `scripts/init-firewall-claude.sh::main` | handler | private | - | (エントリポイント) |
| `scripts/vm-healthd.sh::cpu_ticks` | function | private | - | `scripts/vm-healthd.sh::evaluate_once` |
| `scripts/vm-healthd.sh::evaluate_once` | function | private | `scripts/vm-healthd.sh::cpu_ticks`, `scripts/vm-healthd.sh::log`, `scripts/vm-healthd.sh::smp_of`, `scripts/vm-healthd.sh::tmux_clear`, `scripts/vm-healthd.sh::tmux_flash`, `scripts/vm-healthd.sh::tmux_set`, `scripts/vm-healthd.sh::write_health` | `scripts/vm-healthd.sh::main`, `scripts/vm-healthd.sh::main#--loop` |
| `scripts/vm-healthd.sh::log` | function | private | - | `scripts/vm-healthd.sh::evaluate_once`, `scripts/vm-healthd.sh::main#--loop` |
| `scripts/vm-healthd.sh::main` | handler | private | `scripts/vm-healthd.sh::evaluate_once` | - |
| `scripts/vm-healthd.sh::main#--loop` | handler | private | `scripts/vm-healthd.sh::evaluate_once`, `scripts/vm-healthd.sh::log` | (エントリポイント) |
| `scripts/vm-healthd.sh::smp_of` | function | private | - | `scripts/vm-healthd.sh::evaluate_once` |
| `scripts/vm-healthd.sh::tmux_clear` | function | private | - | `scripts/vm-healthd.sh::evaluate_once` |
| `scripts/vm-healthd.sh::tmux_flash` | function | private | - | `scripts/vm-healthd.sh::evaluate_once` |
| `scripts/vm-healthd.sh::tmux_set` | function | private | - | `scripts/vm-healthd.sh::evaluate_once` |
| `scripts/vm-healthd.sh::write_health` | function | private | - | `scripts/vm-healthd.sh::evaluate_once` |
| `scripts/vm-portsync.sh::log` | function | private | - | `scripts/vm-portsync.sh::main#--loop`, `scripts/vm-portsync.sh::sync_once` |
| `scripts/vm-portsync.sh::main` | handler | private | `scripts/vm-portsync.sh::published_ports`, `scripts/vm-portsync.sh::qmp`, `scripts/vm-portsync.sh::sync_once` | - |
| `scripts/vm-portsync.sh::main#--loop` | handler | private | `scripts/vm-portsync.sh::log`, `scripts/vm-portsync.sh::sync_once` | (エントリポイント) |
| `scripts/vm-portsync.sh::published_ports` | function | private | - | `scripts/vm-portsync.sh::main`, `scripts/vm-portsync.sh::sync_once` |
| `scripts/vm-portsync.sh::qmp` | function | private | - | `scripts/vm-portsync.sh::main`, `scripts/vm-portsync.sh::sync_once` |
| `scripts/vm-portsync.sh::sync_once` | function | private | `scripts/vm-portsync.sh::log`, `scripts/vm-portsync.sh::published_ports`, `scripts/vm-portsync.sh::qmp` | `scripts/vm-portsync.sh::main`, `scripts/vm-portsync.sh::main#--loop` |
| `scripts/vm-up.sh::dockerd_ready` | function | private | - | `scripts/vm-up.sh::main` |
| `scripts/vm-up.sh::log` | function | private | - | `scripts/vm-up.sh::main`, `scripts/vm-up.sh::start_healthd`, `scripts/vm-up.sh::start_portsync` |
| `scripts/vm-up.sh::main` | handler | private | `scripts/vm-up.sh::dockerd_ready`, `scripts/vm-up.sh::log`, `scripts/vm-up.sh::start_healthd`, `scripts/vm-up.sh::start_portsync` | (エントリポイント) |
| `scripts/vm-up.sh::start_healthd` | function | private | `scripts/vm-up.sh::log` | `scripts/vm-up.sh::main` |
| `scripts/vm-up.sh::start_portsync` | function | private | `scripts/vm-up.sh::log` | `scripts/vm-up.sh::main` |
| `scripts/vm::main` | handler | private | `scripts/vm::qemu_pid`, `scripts/vm::qemu_running` | (エントリポイント) |
| `scripts/vm::qemu_pid` | function | private | - | `scripts/vm::main` |
| `scripts/vm::qemu_running` | function | private | - | `scripts/vm::main` |
| `scripts/wait-limit-reset.sh::main` | handler | private | - | (エントリポイント) |

## 解決できなかった呼び出し

<!-- 空欄は「呼び出しが無い」を意味する。解決できなかったものは必ずここに出る。 -->

| 呼び出し元 | 呼び出し式 | 分類 | 候補 |
|---|---|---|---|
| `claude-dev-mac::main` | `source $CONFIG_FILE` | dynamic | - |
| `claude-dev::main` | `source $CONFIG_FILE` | dynamic | - |
| `claude-dev::main#start` | `eval "_val=\${$_v:-}"` | dynamic | - |
