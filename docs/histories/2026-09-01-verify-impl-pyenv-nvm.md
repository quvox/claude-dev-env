---
id: 2026-09-01-verify-impl-pyenv-nvm
date: 2026-09-01
record: なし(taskless — flow: verify-impl)
critical: false
origin_layer: 03
issue: なし
summary: コールグラフを再生成し、エントリポイントの種別が cli から main へ直った(道具の出力の変化)
---

# 2026-09-01 コールグラフ再生成でエントリポイントの種別が直った

## 変更理由

### R-01 実装整合フロー(F3)の増分 run が生成物を再生成した

- 起点層・根拠: `/verify-impl` の再生成は原則1 が名指す書き手である(ツール生成領域)。
  契機は `.devcontainer/Dockerfile.claude` と `docs/03-impl/environments/images.md` の変更
  (構築記録 `docs/build-records/pyenv-nvm-in-claude-image.md`)。
- 変更が必要になった条件: 前回の再生成(2026-08-22)以降にキットの生成器が更新され、
  シェル・Go のエントリポイントのうち**ディスパッチ表を持たないもの**の種別が
  `cli` から `main` へ変わり、索引に「宣言」の欄と説明が加わった。

## 変更内容の要約

- `docs/03-impl/callgraphs/shell.md` — `entrypoint-claude.sh` / `init-firewall-claude.sh` /
  `vm` / `vm-up.sh` / `wait-limit-reset.sh` の5件の種別が `cli` → `main`。
- `docs/03-impl/callgraphs/go.md` — `docker-proxy/main.go::main` の種別が `cli` → `main`。
- `docs/03-impl/callgraphs/index.md` — 表の見出しが「ファイル」→「ファイル / 宣言」になり、
  宣言したガード節(`dispatch_guards`)の効き目を読むための説明が加わった。
- 機能・辺・契約は変わっていない(`feature-graph.md` と `relations/` は同じバイト列に再生成された)。

## 更新した仕様ドキュメント

| 理由ID | 仕様ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/03-impl/callgraphs/shell.md | (生成物。版を持たない) | エントリポイント5件の種別 |
| R-01 | docs/03-impl/callgraphs/go.md | (生成物。版を持たない) | エントリポイント1件の種別 |
| R-01 | docs/03-impl/callgraphs/index.md | (生成物。版を持たない) | 表の欄と説明 |
