---
id: feature-graph
features: 61
edges: 88
confirmed_edges: 88
candidate_edges: 0
shared: 2
unreached: 8
coupled_resources: 0
unlinked_pairs: 0
---

<!-- BEGIN NOTE: cluster-features.py -->
<!-- 生成物。手書き禁止。`CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) && python3 .claude/scripts/cluster-features.py --out "$CG_OUT"` で再生成する。
     不変則: **実装と機能表が変わらなければ1バイトも変わらない**。
     鮮度は保存せず `--check` で検査する。
     **これは機能間連携仕様書ではない。** relations の代わりに使ってはならない
     (.claude/directions/features.md §6)。 -->
<!-- END NOTE: cluster-features.py -->

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
| MODULE-cli-logout | MODULE-cli-common-destructive | 確定 | `claude-dev-mac::main#logout` → `claude-dev-mac::destructive_abort_if_interrupted`, `claude-dev-mac::main#logout` → `claude-dev-mac::destructive_arm_interrupt`, `claude-dev-mac::main#logout` → `claude-dev-mac::destructive_deleted` ほか 13 件 |
| MODULE-cli-logout | MODULE-cli-common-lock | 確定 | `claude-dev-mac::main#logout` → `claude-dev-mac::acquire_lock`, `claude-dev-mac::main#logout` → `claude-dev-mac::release_lock`, `claude-dev::main#logout` → `claude-dev::acquire_lock` ほか 1 件 |
| MODULE-cli-logout | MODULE-cli-common-net-other-running-containers | 確定 | `claude-dev-mac::main#logout` → `claude-dev-mac::net_other_running_containers`, `claude-dev::main#logout` → `claude-dev::net_other_running_containers` |
| MODULE-cli-logout | MODULE-cli-common-require-setup | 確定 | `claude-dev-mac::main#logout` → `claude-dev-mac::require_setup`, `claude-dev::main#logout` → `claude-dev::require_setup` |
| MODULE-cli-logout | MODULE-cli-common-spawned-resources | 確定 | `claude-dev-mac::main#logout` → `claude-dev-mac::spawned_resources`, `claude-dev::main#logout` → `claude-dev::spawned_resources` |
| MODULE-cli-ports | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#ports` → `claude-dev-mac::container_name`, `claude-dev::main#ports` → `claude-dev::container_name` |
| MODULE-cli-ports | MODULE-cli-common-get-novnc-url | 確定 | `claude-dev-mac::main#ports` → `claude-dev-mac::get_novnc_url`, `claude-dev::main#ports` → `claude-dev::get_novnc_url` |
| MODULE-cli-ports | MODULE-cli-common-is-running | 確定 | `claude-dev-mac::main#ports` → `claude-dev-mac::is_running`, `claude-dev::main#ports` → `claude-dev::is_running` |
| MODULE-cli-reset | MODULE-cli-common-container-exists | 確定 | `claude-dev-mac::main#reset` → `claude-dev-mac::container_exists`, `claude-dev::main#reset` → `claude-dev::container_exists` |
| MODULE-cli-reset | MODULE-cli-common-destructive | 確定 | `claude-dev-mac::main#reset` → `claude-dev-mac::destructive_abort_if_interrupted`, `claude-dev-mac::main#reset` → `claude-dev-mac::destructive_arm_interrupt`, `claude-dev-mac::main#reset` → `claude-dev-mac::destructive_failed` ほか 11 件 |
| MODULE-cli-reset | MODULE-cli-common-image-exists | 確定 | `claude-dev-mac::main#reset` → `claude-dev-mac::image_exists`, `claude-dev::main#reset` → `claude-dev::image_exists` |
| MODULE-cli-reset | MODULE-cli-common-lock | 確定 | `claude-dev-mac::main#reset` → `claude-dev-mac::acquire_lock`, `claude-dev-mac::main#reset` → `claude-dev-mac::release_lock`, `claude-dev::main#reset` → `claude-dev::acquire_lock` ほか 1 件 |
| MODULE-cli-reset | MODULE-cli-common-net-other-running-containers | 確定 | `claude-dev-mac::main#reset` → `claude-dev-mac::net_other_running_containers`, `claude-dev::main#reset` → `claude-dev::net_other_running_containers` |
| MODULE-cli-reset | MODULE-cli-common-spawned-resources | 確定 | `claude-dev-mac::main#reset` → `claude-dev-mac::spawned_resources`, `claude-dev::main#reset` → `claude-dev::spawned_resources` |
| MODULE-cli-ssh-keys | MODULE-cli-common-container-name | 確定 | `claude-dev::main#ssh-keys` → `claude-dev::container_name` |
| MODULE-cli-ssh-keys-reset | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#ssh-keys.reset` → `claude-dev-mac::container_name` |
| MODULE-cli-ssh-keys-reset | MODULE-cli-common-dev-agent-path | 確定 | `claude-dev-mac::main#ssh-keys.reset` → `claude-dev-mac::dev_agent_path` |
| MODULE-cli-ssh-keys-select | MODULE-cli-common-select-ssh-keys | 確定 | `claude-dev-mac::main#ssh-keys.select` → `claude-dev-mac::select_ssh_keys_interactive`, `claude-dev::main#ssh-keys.select` → `claude-dev::select_ssh_keys_interactive` |
| MODULE-cli-start | MODULE-cli-common-compose-project-name | 確定 | `claude-dev-mac::main#start` → `claude-dev-mac::compose_project_name`, `claude-dev::main#start` → `claude-dev::compose_project_name` |
| MODULE-cli-start | MODULE-cli-common-container-exists | 確定 | `claude-dev-mac::ensure_docker_proxy_container` → `claude-dev-mac::container_exists`, `claude-dev-mac::main#start` → `claude-dev-mac::container_exists`, `claude-dev::ensure_docker_proxy_container` → `claude-dev::container_exists` ほか 1 件 |
| MODULE-cli-start | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#start` → `claude-dev-mac::container_name`, `claude-dev::main#start` → `claude-dev::container_name` |
| MODULE-cli-start | MODULE-cli-common-container-project-dir | 確定 | `claude-dev-mac::main#start` → `claude-dev-mac::container_project_dir`, `claude-dev::main#start` → `claude-dev::container_project_dir` |
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
| MODULE-cli-stop | MODULE-cli-common-compose-project-name | 確定 | `claude-dev-mac::main#stop` → `claude-dev-mac::compose_project_name`, `claude-dev-mac::main#stop` → `claude-dev-mac::compose_project_name_legacy`, `claude-dev::main#stop` → `claude-dev::compose_project_name` ほか 1 件 |
| MODULE-cli-stop | MODULE-cli-common-container-exists | 確定 | `claude-dev-mac::main#stop` → `claude-dev-mac::container_exists`, `claude-dev::main#stop` → `claude-dev::container_exists` |
| MODULE-cli-stop | MODULE-cli-common-container-name | 確定 | `claude-dev-mac::main#stop` → `claude-dev-mac::container_name`, `claude-dev::main#stop` → `claude-dev::container_name` |
| MODULE-cli-stop | MODULE-cli-common-container-project-dir | 確定 | `claude-dev-mac::main#stop` → `claude-dev-mac::container_project_dir`, `claude-dev::main#stop` → `claude-dev::container_project_dir` |
| MODULE-cli-stop | MODULE-cli-common-dev-agent-path | 確定 | `claude-dev-mac::stop_ssh_bridge` → `claude-dev-mac::dev_agent_path` |
| MODULE-cli-stop | MODULE-cli-common-is-running | 確定 | `claude-dev-mac::stop_proxy_if_idle` → `claude-dev-mac::is_running`, `claude-dev::stop_proxy_if_idle` → `claude-dev::is_running` |
| MODULE-cli-stop | MODULE-cli-common-lock | 確定 | `claude-dev-mac::main#stop` → `claude-dev-mac::acquire_lock`, `claude-dev-mac::main#stop` → `claude-dev-mac::release_lock`, `claude-dev::main#stop` → `claude-dev::acquire_lock` ほか 1 件 |
| MODULE-cli-stop | MODULE-cli-common-net-other-running-containers | 確定 | `claude-dev-mac::stop_proxy_if_idle` → `claude-dev-mac::net_other_running_containers`, `claude-dev::stop_proxy_if_idle` → `claude-dev::net_other_running_containers` |
| MODULE-cli-stop | MODULE-cli-common-spawned-resources | 確定 | `claude-dev-mac::main#stop` → `claude-dev-mac::spawned_resources`, `claude-dev::main#stop` → `claude-dev::spawned_resources` |
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

## 複数機能から到達される共有関数(境界の実体)

ファンインが2以上の関数は機能の内部ヘルパではありえない(`.claude/directions/features.md` §4)。
機能表に足すとルートに昇格し、呼んでいた側に `callees` の辺が1本立つ。
**昇格させるかは人間の判断。**

| シンボル | ファンイン | 到達元の機能 |
|---|---|---|
| `claude-dev-mac::_strip_ssh_keys_section` | 2 | MODULE-cli-common-write-project-ssh-keys, MODULE-cli-ssh-keys-reset |
| `claude-dev::_strip_ssh_keys_section` | 2 | MODULE-cli-common-write-project-ssh-keys, MODULE-cli-ssh-keys-reset |

## どの入口からも到達しない関数

**候補辺も算入した上で**到達しない(`.claude/directions/features.md` §5:「無い」の主張は広く)。到達不能コードの候補だが、**削ってよいかは決めない** — 動的呼び出し・外部からの参照・ツール未対応の可能性がある。

**注意: うち 6 件は Tier 3(正規表現抽出)言語のシンボル** — 呼び出し関係が系統的に不完全で、**「到達しない」は取りこぼしでありうる**(features.md §5.1)。削除候補として扱う前に人間が確認すること。

| シンボル | 備考 |
|---|---|
| `claude-dev-mac::_destructive_done` | Tier 3(取りこぼしの可能性) |
| `claude-dev-mac::_release_all_locks` | Tier 3(取りこぼしの可能性) |
| `claude-dev-mac::main` | Tier 3(取りこぼしの可能性) |
| `claude-dev::_destructive_done` | Tier 3(取りこぼしの可能性) |
| `claude-dev::_release_all_locks` | Tier 3(取りこぼしの可能性) |
| `claude-dev::main` | Tier 3(取りこぼしの可能性) |
| `docker-proxy/main.go::cachedResolveProjectDir` | - |
| `docker-proxy/main.go::lookupProjectDir` | - |

## 同じ資源を触るのに呼び出し辺が無い機能

サーバレス/イベント駆動では、連携の相当部分が**呼び出し辺として原理的に存在しない**。
A がテーブルに書き B が読む — 呼び出しは1本も無いが、B は A の書式に依存している。
この結合は callgraph に出ないので、**CG4(取りこぼし検出)の網にかからない**。

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

