# task-remove-orchestrator memo-2(フェーズ3 の開始時に追い出した内容)

<!-- 追い出した元: memo.md の `## 未決点`(全4件が帰着済み)と `## 進捗メモ`(フェーズ2 の途中経過)。
     ゲートが読む行(`/doc-check(task) 判定: PASS`、`[DS-nn]` 行使行)は memo.md に残してある。 -->

## 未決点(全4件 帰着済み — 2026-08-08 に帰着、2026-08-10 に移動)

1〜3 は「決めないと進めない点」ではなく「実測しないと書けない値」で、書く時機がフェーズ3の末尾になる。
4 は記法の限界であり、反映時の手作業として DoD に落としてある。**いずれも帰着先が確定しているので
フェーズ3 の入場ゲート(未決点ゼロ)は満たしている。**

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| 1 | `docs/03-impl/index.md` の「この層の状態」「02 との差分」「01 との差異」が持つ数値(機能間連携仕様書の本数・網羅モジュール一覧・`check-relations.py` / `callgraph-check.py` / `relations-coverage.py` の結果・起票済み issue の件数) | ドキュメント記載(フェーズ3 の末尾で各ツールを再実行し、実測値で `new-features/03-impl/index.md` を書く。タスクリスト 14) | 実装ドライラン パス1 |
| 2 | `docs/03-impl/features.md`「昇格させた共通基盤機能」のファンイン値 | ドキュメント記載(同上。コールグラフの再生成から導出する。タスクリスト 14) | 実装ドライラン パス1 |
| 3 | `docs/03-impl/environments/images.md` が引用する `.devcontainer/Dockerfile.claude` の行番号 | ドキュメント記載(同上。`orch-builder` ステージの削除で前後がずれる。タスクリスト 14) | 実装ドライラン パス1 |
| 4 | `docs/01-requirements/functional.md` と `docs/01-requirements/non-functional.md` の frontmatter 直後にある HTML コメント(2026-08-04 / 2026-08-06 の検証記録)が `D0-orch-15` / `FR-orch-06` / `NFR-perf-03` / `docs/issues/035` に触れている。**見出しを持たないので `sections` にも `deletes` にも載せられない**(`.claude/directions/change-set.md` の記法の限界) | ドキュメント記載(`/task-close` の反映時に手で削除する。タスクリスト 15)。**これは「実測待ち」ではなく変更指示の記法の限界である** — `sections` / `deletes` は見出ししか指せず、最初の見出しより前の本文を表せない(`.claude/directions/change-set.md` §2)。機械検査で担保できないので、DoD に独立の1行を置いた | 実装ドライラン パス1(独立レビュー readiness 重大度「低」→ docs 重大度「中」で再指摘) |

## 進捗メモ(フェーズ2 の途中経過)

- 2026-08-08 フェーズ2: 実装ドライラン(パス1)を実施。**独立レビューは Codex が利用枠切れ
  (復旧 2026-08-11)のためサブエージェントへ自動フォールバックした(`lens: subagent` /
  model: sonnet / reasoning: セッション既定)**。レビューの指摘 8 件(高2・中4・低2)と
  自分のパス1で見つけた 3 件を裁定し、変更指示を 65 → 67 件へ増やして全件修正した。
  `check-changeset.py` は再実行して合格。
- 2026-08-08 フェーズ2: 02 完了(architecture / system / relations / environments / logging / contracts{cli-orchestrator,orchestrator-prompt,cli-container})。次は 03。
- 2026-08-08 フェーズ2: 01 完了(functional / non-functional / usecases / system / decisions/split)。
- 2026-08-08 フェーズ2: 00 完了(request / terminology / acceptances / decisions{orch,sec,dist,env})。次は 01。
- 2026-08-08 フェーズ1: 00〜02 を全文読了。影響範囲(closure)を確定し、決定シートを作成して
  人間の一括指示で転記した。次は `/task-doc task-remove-orchestrator`(フェーズ2)。
