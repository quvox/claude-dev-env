---
id: go
language: go
tier: 2
symbols: 14
edges: 17
endpoints: 1
unresolved: 0
---

<!-- BEGIN NOTE: build-callgraphs.py -->
<!-- 生成物。手書き禁止。`CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) && python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT"` で再生成する。
     辞書順に固定されており、実装が変わらなければこのファイルも変わらない。
     **これは機能間連携仕様書ではない**(.claude/directions/callgraphs.md)。 -->
<!-- END NOTE: build-callgraphs.py -->

# go コールグラフ (Tier 2)

## エントリポイント

| 種別 | 識別子 | 正規化キー | ハンドラ | 検出根拠 |
|---|---|---|---|---|
| cli | `dispatch main @ docker-proxy/main.go::main` | `/docker-proxy/main.go` | `docker-proxy/main.go::main` | docker-proxy/main.go |

## 関数表

| シンボル | 種別 | 可視性 | 呼び出す先 | 呼び出し元 |
|---|---|---|---|---|
| `docker-proxy/main.go::cachedResolveProjectDir` | function | private | `docker-proxy/main.go::lookupProjectDir` | - |
| `docker-proxy/main.go::clientIP` | function | private | - | `docker-proxy/main.go::labelNetworkCreate`, `docker-proxy/main.go::validateContainerCreate` |
| `docker-proxy/main.go::closeWrite` | function | private | - | `docker-proxy/main.go::handleHijack` |
| `docker-proxy/main.go::containWorkspacePath` | function | private | - | `docker-proxy/main.go::rewriteBinds` |
| `docker-proxy/main.go::handleHijack` | function | private | `docker-proxy/main.go::closeWrite` | `docker-proxy/main.go::main` |
| `docker-proxy/main.go::injectOwnerLabels` | function | private | - | `docker-proxy/main.go::labelNetworkCreate`, `docker-proxy/main.go::validateContainerCreate` |
| `docker-proxy/main.go::labelNetworkCreate` | function | private | `docker-proxy/main.go::clientIP`, `docker-proxy/main.go::injectOwnerLabels`, `docker-proxy/main.go::readAndRestoreBody`, `docker-proxy/main.go::writeBackBody` | `docker-proxy/main.go::main` |
| `docker-proxy/main.go::lookupProjectDir` | function | private | - | `docker-proxy/main.go::cachedResolveProjectDir` |
| `docker-proxy/main.go::main` | function | private | `docker-proxy/main.go::handleHijack`, `docker-proxy/main.go::labelNetworkCreate`, `docker-proxy/main.go::validateContainerCreate`, `docker-proxy/main.go::validateExecCreate` | (エントリポイント) |
| `docker-proxy/main.go::readAndRestoreBody` | function | private | - | `docker-proxy/main.go::labelNetworkCreate`, `docker-proxy/main.go::validateContainerCreate`, `docker-proxy/main.go::validateExecCreate` |
| `docker-proxy/main.go::rewriteBinds` | function | private | `docker-proxy/main.go::containWorkspacePath` | `docker-proxy/main.go::validateContainerCreate` |
| `docker-proxy/main.go::validateContainerCreate` | function | private | `docker-proxy/main.go::clientIP`, `docker-proxy/main.go::injectOwnerLabels`, `docker-proxy/main.go::readAndRestoreBody`, `docker-proxy/main.go::rewriteBinds`, `docker-proxy/main.go::writeBackBody` | `docker-proxy/main.go::main` |
| `docker-proxy/main.go::validateExecCreate` | function | private | `docker-proxy/main.go::readAndRestoreBody` | `docker-proxy/main.go::main` |
| `docker-proxy/main.go::writeBackBody` | function | private | - | `docker-proxy/main.go::labelNetworkCreate`, `docker-proxy/main.go::validateContainerCreate` |

## 解決できなかった呼び出し

<!-- 空欄は「呼び出しが無い」を意味する。解決できなかったものは必ずここに出る。 -->

| 呼び出し元 | 呼び出し式 | 分類 | 候補 |
|---|---|---|---|
| (なし) | - | - | - |
