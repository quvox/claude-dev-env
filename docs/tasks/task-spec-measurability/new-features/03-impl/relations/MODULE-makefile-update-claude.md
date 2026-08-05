---
target: docs/03-impl/relations/MODULE-makefile-update-claude.md
change: replace
sections:
  - "## 目的"
reason: >
  frontmatter summary と目的の「高速更新」「短時間で」が測定不能語である(docs/issues/017)。
  委任 b の範囲で、実装が実際に行うこと(イメージを作り直さずビルドキャッシュを使う)へ置き換える。
id: MODULE-makefile-update-claude
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::update-claude
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-dist-01
requirements: FR-env-09, FR-env-12
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-05
summary: コンテナイメージを作り直さずに Claude Code だけを更新する(ビルドキャッシュを使う)
---

## 目的

エージェント CLI(FR-env-12)だけを入れ替える(FR-env-09)。**イメージ全体を作り直さず**、
Go / Rust / Playwright 等の重い層は**ビルドキャッシュを再利用する**ため、
再ビルドの対象は `DSN-dist-01` が配布ステージの終端に置いた CLI 導入層だけになる。
