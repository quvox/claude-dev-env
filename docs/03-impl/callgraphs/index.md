---
id: index
languages: 6
---

<!-- 生成物。手書き禁止。`python3 .claude/scripts/build-callgraphs.py` で再生成する。
     辞書順に固定されており、実装が変わらなければこのファイルも変わらない。
     **これは機能間連携仕様書ではない**(.claude/directions/callgraphs.md)。 -->

# コールグラフ 目次

## 言語ごとの状態

| 言語 | Tier | 抽出器 | シンボル | 辺 | エンドポイント | 未解決 | 外部呼び出し | 降格理由 |
|---|---|---|---|---|---|---|---|---|
| [go](go.md) | 2 | tree-sitter-go | 219 | 399 | 2 | 6 | 951 | - |
| [infra](infra.md) | 2 | infra (CFN/SAM/OpenAPI/Terraform) | 0 | 0 | 0 | 0 | 0 | - |
| [make](make.md) | 3 | make-regex | 19 | 22 | 19 | 0 | 45 | 正規表現のみ(レシピ本文は shell と同じ限界を持つ) |
| [python](python.md) | 2 | python-ast (stdlib) | 5 | 0 | 0 | 0 | 0 | - |
| [shell](shell.md) | 3 | shell-regex | 170 | 258 | 51 | 4 | 2287 | 正規表現のみ(shell は変数展開・eval で静的解決が原理的に不完全) |
| [typescript](typescript.md) | 2 | tree-sitter-typescript | 0 | 0 | 0 | 0 | 0 | - |

## Tier の意味

| Tier | 手段 | 保証 |
|---|---|---|
| 1 | 索引器・言語ツールチェーン | 型解決済み・跨ファイル正確 |
| 2 | 構文解析 + 名前解決 | 同名衝突は `ambiguous` として候補列挙 |
| 3 | 正規表現 | 定義とエンドポイントのみ。**呼び出し関係は不完全** |

**Tier 3 の結果を「網羅した」と報告してはならない。**

## 解析対象から外したもの

<!-- ベンダリングされた第三者ライブラリ・テスト・開発ツールは解析対象にしない
     (.claude/directions/callgraphs.md §5.3 / features.md §0.1)。
     **黙って外すと「網羅した」という誤読を生む**のでここに出す。 -->

| 言語 | ディレクトリ(第三者ライブラリ) |
|---|---|
| (なし) | - |

<!-- 開発ツール = Makefile / CI 定義 / compose 等。判定は tooling_markers。
     本番実行系から到達しないものは機能ではない(features.md §0.1)。
     **照合は部分文字列なので誤除外が起きる。** 本番コードが並んでいたら
     callgraph-config.local.json の *_markers を絞ること。 -->

| 言語 | 種別 | 件数 | ファイル |
|---|---|---|---|
| go | テスト | 19 | `docker-proxy/binds_test.go`, `docker-proxy/main_test.go`, `orchestrator/accept_test.go`, `orchestrator/archive_test.go`, `orchestrator/controller_test.go`, `orchestrator/dashboard_test.go`, `orchestrator/dashtui_test.go`, `orchestrator/handoff_test.go`, `orchestrator/mode_test.go`, `orchestrator/models_test.go` ほか 9 件 |
| python | テスト | 3 | `examples/orch-sample/tests/test_geometry.py`, `examples/orch-sample/tests/test_stats.py`, `examples/orch-sample/tests/test_strings.py` |

## シンボルが集中しているディレクトリ

<!-- 第三者ライブラリのベンダリングが混ざっていないかを見るための表。
     混ざっていたら callgraph-config.local.json の excludes に入れること。 -->

| 言語 | ディレクトリ | シンボル | 割合 |
|---|---|---|---|
| python | `examples/orch-sample/src/` | 5 | 100% |

## 設定

- internal_roots: `.`
- excludes: `.claude/`, `.eggs/`, `.git/`, `.mypy_cache/`, `.next/`, `.nuxt/`, `.orchestrator/`, `.output/`, `.pnp/`, `.pytest_cache/`, `.svelte-kit/`, `.terraform/`, `.tox/`, `.turbo/`, `.venv/`, `.yarn/`, `3rdparty/`, `Godeps/`, `__pycache__/`, `__pypackages__/`, `bower_components/`, `build/`, `coverage/`, `dist-packages/`, `dist/`, `docs/`, `jspm_packages/`, `migrations/`, `node_modules/`, `orchestrator/vendor/`, `scripts/e2e6-codex.sh`, `site-packages/`, `target/`, `third_party/`, `tmp/`, `vendor/`, `vendored/`, `venv/`, `workspace/`

## 注記

- なし
