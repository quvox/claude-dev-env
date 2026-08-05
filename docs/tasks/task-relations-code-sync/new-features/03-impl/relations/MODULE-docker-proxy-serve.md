---
target: docs/03-impl/relations/MODULE-docker-proxy-serve.md
change: replace
sections:
  - "## 既知の制限"
deletes: []
reason: D0-sec-05 のガードレールが「残存リスクは既知の制限に書く」ことを求めているのに該当行が無い(docs/issues/005 の対処案1。同 issue が「issue 038 と同じタスクで行う」と指定)
id: MODULE-docker-proxy-serve
module: MOD-docker-proxy
kind: tool
sync: sync
impl: docker-proxy/main.go::main
callers: なし
callees: なし
contracts: CTR-docker-api
design: DSN-mod-01, DSN-arch-01, DSN-mod-04
requirements: FR-env-07, NFR-sec-01
tests: docker-proxy/main_test.go::TestValidateContainerCreate_BlocksPrivileged, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksPidHost, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksNetworkHost, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksUsernsHost, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDangerousCaps, docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDevices, docker-proxy/main_test.go::TestValidateExecCreate_BlocksPrivileged, docker-proxy/main_test.go::TestContainerCreateRe, docker-proxy/main_test.go::TestHijackEndpointRe, docker-proxy/binds_test.go::TestContainWorkspacePath, docker-proxy/binds_test.go::TestContainWorkspacePath_LexicalOnly, docker-proxy/binds_test.go::TestRewriteBinds_RewritesUnderWorkspace, docker-proxy/binds_test.go::TestRewriteBinds_RejectsOutsideWorkspace, docker-proxy/binds_test.go::TestRewriteBinds_MountsBindOutsideRejected, docker-proxy/binds_test.go::TestValidateContainerCreate_RewritesWorkspaceBind
updated: 2026-08-05
summary: Docker API を検査・書き換えして透過中継する常駐プロキシ
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。frontmatter は `updated` の日付以外変更なし。
     実装は変えない(解釈できないボディの中継そのものは 2026-08-03 に人間が「現状維持 + 限定の明記」で
     裁定済み。docs/issues/005)。 -->

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **字句的封じ込めのみで symlink 脱出を防げない** | プロジェクト内の symlink がホスト外を指していると、その先が bind されうる(残存リスク) | なし(意図した割り切り) |
| `cachedResolveProjectDir` / `lookupProjectDir` は関数値経由で呼ばれる | 静的解析では未到達に見える(Tier 2 の限界) | なし |
| create 検査の後に hijack 判定へ落ちうる構造 | create パスと hijack パスは正規表現が排他なので実害は無い | なし |
| **解釈できないリクエストボディは検査せず中継する** | 拒否すべき操作がそのボディに含まれていても通る(最終的な検証は Docker daemon 側だけになる)。`AC-03`「危険な操作は拒否される」に対する残存リスクである | `docs/issues/005-modify-docker-proxy-relays-unparseable-bodies.md` |
