---
id: make
language: make
tier: 3
symbols: 19
edges: 22
endpoints: 19
unresolved: 0
---

<!-- 生成物。手書き禁止。`python3 .claude/scripts/build-callgraphs.py` で再生成する。
     辞書順に固定されており、実装が変わらなければこのファイルも変わらない。
     **これは機能間連携仕様書ではない**(.claude/directions/callgraphs.md)。 -->

# make コールグラフ (Tier 3)

## エントリポイント

| 種別 | 識別子 | 正規化キー | ハンドラ | 検出根拠 |
|---|---|---|---|---|
| cli | `dispatch build @ Makefile::build` | `/Makefile/build` | `Makefile::build` | Makefile |
| cli | `dispatch build-claude @ Makefile::build-claude` | `/Makefile/build-claude` | `Makefile::build-claude` | Makefile |
| cli | `dispatch build-claude-vnc @ Makefile::build-claude-vnc` | `/Makefile/build-claude-vnc` | `Makefile::build-claude-vnc` | Makefile |
| cli | `dispatch build-docker-proxy @ Makefile::build-docker-proxy` | `/Makefile/build-docker-proxy` | `Makefile::build-docker-proxy` | Makefile |
| cli | `dispatch build-orchestrator @ Makefile::build-orchestrator` | `/Makefile/build-orchestrator` | `Makefile::build-orchestrator` | Makefile |
| cli | `dispatch clean @ Makefile::clean` | `/Makefile/clean` | `Makefile::clean` | Makefile |
| cli | `dispatch env @ Makefile::env` | `/Makefile/env` | `Makefile::env` | Makefile |
| cli | `dispatch help @ Makefile::help` | `/Makefile/help` | `Makefile::help` | Makefile |
| cli | `dispatch install @ Makefile::install` | `/Makefile/install` | `Makefile::install` | Makefile |
| cli | `dispatch login @ Makefile::login` | `/Makefile/login` | `Makefile::login` | Makefile |
| cli | `dispatch network @ Makefile::network` | `/Makefile/network` | `Makefile::network` | Makefile |
| cli | `dispatch orch-sample @ Makefile::orch-sample` | `/Makefile/orch-sample` | `Makefile::orch-sample` | Makefile |
| cli | `dispatch orch-sample-clean @ Makefile::orch-sample-clean` | `/Makefile/orch-sample-clean` | `Makefile::orch-sample-clean` | Makefile |
| cli | `dispatch setup @ Makefile::setup` | `/Makefile/setup` | `Makefile::setup` | Makefile |
| cli | `dispatch status @ Makefile::status` | `/Makefile/status` | `Makefile::status` | Makefile |
| cli | `dispatch uninstall @ Makefile::uninstall` | `/Makefile/uninstall` | `Makefile::uninstall` | Makefile |
| cli | `dispatch update-claude @ Makefile::update-claude` | `/Makefile/update-claude` | `Makefile::update-claude` | Makefile |
| cli | `dispatch upgrade @ Makefile::upgrade` | `/Makefile/upgrade` | `Makefile::upgrade` | Makefile |
| cli | `dispatch volumes @ Makefile::volumes` | `/Makefile/volumes` | `Makefile::volumes` | Makefile |

## 関数表

| シンボル | 種別 | 可視性 | 呼び出す先 | 呼び出し元 |
|---|---|---|---|---|
| `Makefile::build` | handler | public | `Makefile::build-claude`, `Makefile::build-claude-vnc`, `Makefile::build-docker-proxy` | `Makefile::help`, `Makefile::setup` |
| `Makefile::build-claude` | handler | public | - | `Makefile::build`, `Makefile::build-claude-vnc`, `Makefile::help` |
| `Makefile::build-claude-vnc` | handler | public | `Makefile::build-claude` | `Makefile::build`, `Makefile::help` |
| `Makefile::build-docker-proxy` | handler | public | - | `Makefile::build`, `Makefile::help` |
| `Makefile::build-orchestrator` | handler | public | - | `Makefile::help` |
| `Makefile::clean` | handler | public | - | `Makefile::help` |
| `Makefile::env` | handler | public | - | `Makefile::setup` |
| `Makefile::help` | handler | public | `Makefile::build`, `Makefile::build-claude`, `Makefile::build-claude-vnc`, `Makefile::build-docker-proxy`, `Makefile::build-orchestrator`, `Makefile::clean`, `Makefile::login`, `Makefile::setup`, `Makefile::status`, `Makefile::uninstall`, `Makefile::update-claude`, `Makefile::upgrade` | (エントリポイント) |
| `Makefile::install` | handler | public | - | `Makefile::setup` |
| `Makefile::login` | handler | public | - | `Makefile::help`, `Makefile::setup` |
| `Makefile::network` | handler | public | - | `Makefile::setup` |
| `Makefile::orch-sample` | handler | public | - | (エントリポイント) |
| `Makefile::orch-sample-clean` | handler | public | - | (エントリポイント) |
| `Makefile::setup` | handler | public | `Makefile::build`, `Makefile::env`, `Makefile::install`, `Makefile::login`, `Makefile::network`, `Makefile::volumes` | `Makefile::help` |
| `Makefile::status` | handler | public | - | `Makefile::help` |
| `Makefile::uninstall` | handler | public | - | `Makefile::help` |
| `Makefile::update-claude` | handler | public | - | `Makefile::help` |
| `Makefile::upgrade` | handler | public | - | `Makefile::help` |
| `Makefile::volumes` | handler | public | - | `Makefile::setup` |

## 解決できなかった呼び出し

<!-- 空欄は「呼び出しが無い」を意味する。解決できなかったものは必ずここに出る。 -->

| 呼び出し元 | 呼び出し式 | 分類 | 候補 |
|---|---|---|---|
| (なし) | - | - | - |
