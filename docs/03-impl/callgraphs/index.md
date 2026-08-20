---
id: index
languages: 6
---

<!-- BEGIN NOTE: build-callgraphs.py -->
<!-- 生成物。手書き禁止。`CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) && python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT"` で再生成する。
     辞書順に固定されており、実装が変わらなければこのファイルも変わらない。
     **これは機能間連携仕様書ではない**(.claude/directions/callgraphs.md)。 -->
<!-- END NOTE: build-callgraphs.py -->

# コールグラフ 目次

## 言語ごとの状態

| 言語 | Tier | 抽出器 | シンボル | 辺 | エンドポイント | 未解決 | 外部呼び出し | 降格理由 |
|---|---|---|---|---|---|---|---|---|
| [go](go.md) | 2 | tree-sitter-go | 16 | 20 | 1 | 0 | 145 | - |
| [infra](infra.md) | 2 | infra (CFN/SAM/OpenAPI/Terraform) | 0 | 0 | 0 | 0 | 0 | - |
| [make](make.md) | 3 | make-regex | 16 | 21 | 16 | 0 | 58 | 正規表現のみ(レシピ本文は shell と同じ限界を持つ) |
| [python](python.md) | 2 | python-ast (stdlib) | 0 | 0 | 0 | 0 | 0 | - |
| [shell](shell.md) | 3 | shell-regex | 179 | 274 | 46 | 3 | 2714 | 正規表現のみ(shell は変数展開・eval で静的解決が原理的に不完全) |
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
     **ここに本番コードが並んでいたら誤除外である。** callgraph-config.local.json の
     *_markers を絞ること。照合規則(目印の形で決まる)は directions/callgraphs.md
     §5.9.1 の表を見る。 -->

| 言語 | 種別 | 件数 | ファイル |
|---|---|---|---|
| go | テスト | 3 | `docker-proxy/binds_test.go`, `docker-proxy/labels_test.go`, `docker-proxy/main_test.go` |

## シンボルが集中しているディレクトリ

<!-- 第三者ライブラリのベンダリングが混ざっていないかを見るための表。
     混ざっていたら callgraph-config.local.json の excludes に入れること。 -->

| 言語 | ディレクトリ | シンボル | 割合 |
|---|---|---|---|
| (なし) | - | - | - |

## 設定

- internal_roots: `.`
- excludes: `.claude/`, `.codex/`, `.eggs/`, `.git/`, `.mypy_cache/`, `.next/`, `.nuxt/`, `.output/`, `.pnp/`, `.pytest_cache/`, `.ruff_cache/`, `.svelte-kit/`, `.terraform/`, `.tox/`, `.turbo/`, `.venv/`, `.yarn/`, `3rdparty/`, `Godeps/`, `__pycache__/`, `__pypackages__/`, `blob-report/`, `bower_components/`, `build/`, `coverage/`, `dist-packages/`, `dist/`, `docs/`, `htmlcov/`, `jspm_packages/`, `migrations/`, `node_modules/`, `playwright-report/`, `scripts/e2e6-codex.sh`, `site-packages/`, `target/`, `test-results/`, `third_party/`, `tmp/`, `vendor/`, `vendored/`, `venv/`, `workspace/`

## 注記

- なし
