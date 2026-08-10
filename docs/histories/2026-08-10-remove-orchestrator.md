---
id: 2026-08-10-remove-orchestrator
date: 2026-08-10
task: task-remove-orchestrator
origin_layer: 00
issue: なし
summary: AI オーケストレーターに関する要求・要件・設計・実装仕様とコードをすべて削除し、隔離コンテナ開発環境だけで 00〜03 とコードの辻褄が合う状態へ戻した
---

# 2026-08-10 オーケストレーターの全面削除

## 変更理由

起点は **00(要求)**。人間の要求「orchestrator に関する全ての記述、機能、実装を削除して、
辻褄を合わせたい。とにかく全く無かったことにしたい」(2026-08-08 の起票発話)。
`RQ-orch-01`(並列開発力の向上)という要求そのものを取り下げる決定であり、
それを支える 01〜03 とコードが連鎖して消える。

製品側の背景は `docs/kit-report.md` が測っている: `orchestrator/` の最終コミットは
2026-07-06 で、以後コードは 1 行も動いていないのに、その文書整合だけが 1 か月続いていた。

## 変更内容の要約

- 00: `RQ-orch-01` と `AC-04` / `AC-05`、決定台帳 `decisions/orch.md`(`D0-orch-*` 全件)、
  用語集のオーケストレーター系の語を削除した
- 01: `FR-orch-01`〜`09`(69 条項)と `NFR-perf-03` / `NFR-avail-01` / `NFR-sec-03` /
  `NFR-ops-04`、`UC-04` / `UC-05`、`SR-22` / `SR-23` を削除し、`SR-21` / `SR-31` を縮めた。
  機能要件は 210 条項 → 140 条項になった。**`NFR-ops-05`(利用者へ向けた文は日本語)を新設**した
  (フェーズ2 の `/doc-check` で `DSN-log-03` から 01 へ引き上げたもの)
- 02: `MOD-orchestrator` / `MOD-hooks` / `MOD-sample-project` / `MOD-cli-orchestrate` の
  4 モジュール(29 → 25)、契約 `CTR-cli-orchestrator` / `CTR-orchestrator-prompt`、
  設計判断 `DSN-orch-01` / `DSN-orch-02` / `DSN-ui-02` / `DSN-log-02`、
  画面 `SCR-02`〜`SCR-06` と画面遷移、`PLAN-orchestrator-main` を削除した
- 03: 機能表を 83 → 56 本にし、対応する `relations/MODULE-*` 27 本・契約 2 本・
  テスト対応 4 本を削除した
- コード: `orchestrator/`(Go 一式・vendor・instructions)、`examples/orch-sample/`、
  `workspace/orch-sample/`、`scripts/orch-sample.sh`、通知フック 2 本、`.orchestrator/`、
  `claude-dev` / `claude-dev-mac` の `orchestrate` サブコマンド、Makefile の 3 ターゲット、
  Dockerfile の `orch-builder` ステージを削除した
- `docs/issues/` から、対象の実装ごと消える 21 件を削除した(61 → 39 件)

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/request.md | 1.3.0 → 1.4.0 | 目的・対象ユーザー・完成イメージから並列開発を落とし、「やらないこと」4・5 を削除 |
| docs/00-requests/acceptances.md | 1.3.0 → 1.4.0 | `AC-04` / `AC-05` を削除(番号は再利用しない)。対象外シナリオを 3 行 → 1 行へ |
| docs/00-requests/terminology.md | 1.4.0 → 1.5.0 | オーケストレーター・worker・介入・品質ゲートなどの語を削除 |
| docs/00-requests/decisions/orch.md | 削除 | `D0-orch-*` 全件が対象を失った |
| docs/00-requests/decisions/dist.md | 1.1.0 → 1.2.0 | 配布物から orchestrator バイナリを外した |
| docs/00-requests/decisions/env.md | 1.4.0 → 1.5.0 | 環境の決定から自己検証題材を外した |
| docs/00-requests/decisions/sec.md | 1.2.0 → 1.3.0 | `D0-sec-06` の worker の含意を外した |
| docs/01-requirements/functional.md | 1.12.0 → 1.13.0 | `FR-orch-01`〜`09` を削除(210 → 140 条項)。冒頭の検証記録コメントを削除 |
| docs/01-requirements/non-functional.md | 1.6.0 → 1.7.0 | 非機能 4 件を削除し `NFR-ops-05` を新設(13 → 10 件)。冒頭の検証記録コメントを削除 |
| docs/01-requirements/usecases.md | 1.4.0 → 1.5.0 | `UC-04` / `UC-05` を削除 |
| docs/01-requirements/system.md | 1.1.0 → 1.2.0 | `SR-22` / `SR-23` を削除、`SR-21` / `SR-31` を docker-proxy だけへ縮めた |
| docs/01-requirements/decisions/split.md | 1.2.0 → 1.3.0 | 分割可否の判断から orchestrator の条項を外した |
| docs/02-design/architecture.md | 1.4.0 → 1.5.0 | 全体構成から ORCH / HK / SP を削除。`DSN-arch-02` を「2箇所」、`DSN-arch-03` を「起動から開発開始まで」へ改名し、`DSN-orch-01` / `DSN-orch-02` を削除 |
| docs/02-design/system.md | 2.8.0 → 2.9.0 | モジュール 29 → 25。`DSN-mod-06` / `DSN-test-01` / `DSN-ui-01` を改名し、`DSN-ui-02` / 画面遷移 / `SCR-02`〜`SCR-06` を削除 |
| docs/02-design/relations.md | 1.7.0 → 1.8.0 | `PLAN-orchestrator-main` を削除し、連携図と一覧を 25 モジュールへ揃えた |
| docs/02-design/environments.md | 1.3.0 → 1.4.0 | lint / テスト / build のコマンドから orchestrator と題材を外し、コールグラフ抽出設定を更新 |
| docs/02-design/logging.md | 1.4.1 → 1.5.0 | `## 必須フィールド`(追記型ログ)と `DSN-log-02` を削除。ログは 3 系統 → 2 系統 |
| docs/02-design/contracts/cli-container.md | 1.7.0 → 1.8.0 | `orchestrate` サブコマンドの行を削除 |
| docs/02-design/contracts/cli-orchestrator.md | 削除 | 対象の CLI ごと消えた |
| docs/02-design/contracts/orchestrator-prompt.md | 削除 | 同上 |
| docs/03-impl/index.md | 1.18.0 → 1.19.0 | 層代表の版。「この層の状態」「コールグラフ」を実測値で書き直し(機能 56 / 起票済み欠陥 21 → 11 件)、02 との差分を 4 件 → 0 件へ。冒頭の検証記録コメント 2 件を削除 |
| docs/03-impl/features.md | (版を持たない) | 機能一覧 83 → 56 行。統合した機能・昇格させた共通基盤機能・到達しない関数の各表から orchestrator 由来の行を削除 |
| docs/03-impl/environments/images.md | 1.0.0 → 1.1.0 | `orch-builder` ステージを削除し、Dockerfile の引用行番号を実測で 12 行ぶん繰り上げた |
| docs/03-impl/relations/MODULE-*(27 本) | 削除 | orchestrator 19 / cli-orchestrate / makefile 3 / sample-project 2 / hooks 2 |
| docs/03-impl/relations/MODULE-cli-start.md ほか 6 本 | (版を持たない) | `callers` から `MODULE-cli-orchestrate` を外し、契機の列挙と引用の委任 ID を直した |
| docs/03-impl/contracts/cli-orchestrator.md / orchestrator-prompt.md | 削除 | 02 と対で消えた |
| docs/03-impl/tests/(orchestrator / cli-orchestrate / hooks / sample-project).md | 削除 | 対象の機能ごと消えた |
| docs/03-impl/tests/e2e.md | 1.4.0 → 1.5.0 | `E2E-04` / `E2E-05` を削除 |
| docs/03-impl/tests/strategy.md | 1.4.0 → 1.5.0 | 単体テストの対象を docker-proxy だけへ |
| docs/03-impl/tests/(cli-common / images / makefile).md | 各 MINOR | 削除した対象の行を落とし、`## テスト設計の判断` を新設(`[DS-01]`) |

## 実装したもの

| 対象 | 内容 | コミット |
|---|---|---|
| `orchestrator/` ほか | Go モジュール一式・自己検証題材・通知フック・実行時状態を削除 | `c7f9c21` |
| `Makefile` / `claude-dev` / `claude-dev-mac` / `Dockerfile.claude` / `.gitignore` / `README.md` / `INDEX.md` / `scripts/vm-healthd.sh` | orchestrator への参照を削除 | `c7f9c21` |
| `docs/issues/` | 対象の消えた 21 件を削除し、`docs/pendings.md` P-002 を修正 | `d68a725` |
| 変更指示 68 件 | 実測値と新しいキット記法へ更新 | `e4fc59b` |

## 実施した移行

| 対象 | 手順(実行したコマンド / スクリプト) | 実行日 | 結果・確認方法 |
|---|---|---|---|
| 配布イメージ | `make build`(`orch-builder` ステージと通知フック 2 本の `COPY` を外した `Dockerfile.claude` で再ビルド) | 2026-08-10 | 3 イメージとも成功。`claude-dev-claude` は 8.35GB → 8.16GB |
| 実行時運用状態 `.orchestrator/` | `rm -rf .orchestrator`(gitignore 済みの生成物。削除前にスクラッチへ tar で退避) | 2026-08-10 | ディレクトリが存在しないこと |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 削除 | MODULE-orchestrator-*(19 本) | controller / state / state-io / state-intervention / session / worktree / worker / review / plan / mode / handoff / claude-exec / dashboard / slack / streamlog / term / trigger / config / main |
| 削除 | MODULE-cli-orchestrate | `claude-dev orchestrate` サブコマンド |
| 削除 | MODULE-makefile-build-orchestrator / -orch-sample / -orch-sample-clean | Makefile の 3 ターゲット |
| 削除 | MODULE-sample-project-scaffold / -mathkit | 自己検証題材 |
| 削除 | MODULE-hooks-save-prompt / -send-slack-message | Claude Code の通知フック |
| 変更 | MODULE-cli-common-container-name / -is-running / -require-setup / -resolve-container-user | `callers` から `MODULE-cli-orchestrate` を削除(11→10 / 9→8 / 7→6 / 4→3) |
| 変更 | MODULE-cli-start | `callers` が「なし」になった。`## 呼び出され方` から orchestrate の再帰呼び出しを削除 |
| 変更 | MODULE-docker-proxy-serve | 実装上の判断3 の根拠を `D0-orch-02` → `D0-scope-02` へ付け替え |
| 変更 | MODULE-vm-mode-healthd | health ファイルの読み手から `MODULE-orchestrator-dashboard` を外した |

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| 通知フック(`save_prompt.sh` / `sendslackmsg.sh`)を範囲に含めるか | 含める(削除する) | 残す | `MOD-hooks` の対応要件は `FR-orch-07` と `NFR-sec-03` / `NFR-avail-03` だけで、`FR-orch-07` を消すと要件の裏付けが 0 になる。崩れる条件: 通知そのものを別の要求として立てたとき |
| `docs/orch/` と `docs/histories/` / `docs/feedbacks/` を範囲に含めるか | 含めない(残す) | まとめて削除する | `docs/orch/` は別プロジェクトへ分離するための抽出物(`fce4552`)で SSOT ではない。histories / feedbacks は過去の記録であり現在の姿を述べる SSOT ではない |
| 対象の消えた `docs/issues/` をどうするか | 21 件を削除する | 「解消」として残す | 参照先の実装・ID がすべて消えるため、残すと実在しない ID を指す記録になる。崩れる条件: 同じ欠陥が別モジュールで再発したとき(そのときは新規起票) |
| 重複タスク(2026-08-08 のタスクが残っていた)の扱い | 既存を継続してフェーズ3へ | 破棄して `/task-new` からやり直す | 変更指示 68 件と `/doc-check` PASS を捨てる利得が無く、新規範でもレーン判定は `critical` で通る。崩れる条件: 規範の変更が 00〜02 の判断そのものを変えるとき(今回は記法と検査の変更だった) |
| `/task-close`(SSOT 一括書き換え)を今走らせるか | 走らせる | キット側の食い違いを先に確認する / 合成 diff を人間が見る | 合成ビューでの検査がすべて合格し、反映は git で戻せる。崩れる条件: `.claude/` が git 追跡外のままキットの修正が失われたとき |
| `version_bump` の水準(32 件) | 意味が変わる 25 件を `minor`、引用の付け替え等 7 件を `patch` | 全件 `minor` / 全件 `patch` | 原則6「意味を変える修正は MINOR」と §3「PATCH 級=字句・引用の付け替え・陳腐化した記述の削除」の両方に当てる。崩れる条件: `patch` にした relations の本文が意味レベルで変わっていたとき |
| キットの合成器が異常終了した件 | CLAUDE.md §3 の例外として最小修正を入れた | 修正せず人間へ差し戻す | 4 件とも `.claude/directions/` の記述とスクリプトの食い違い(スクリプト側の誤り)で、直さないと反映そのものができない。崩れる条件: 規範側が「relations と features.md も版を持つ」へ変わったとき |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 気づき | docs/feedbacks/026-a-kit-rewrite-invalidates-change-sets-already-verified.md | キットの書き換えは検証済みの変更指示を無効化する。6 箇所のうち 3 箇所は黙って壊れた |
| 棚上げ | docs/pendings.md「残務(文書整合ほか)」9 行 | INDEX.md / README.md の古いパス、`.claude/scripts/*.local.json` の喪失、`tests/index.md` の語彙、issues 009 / 030 の後始末、features.md の未到達 4 件、change-set 記法の限界 |
| 解消した issue | docs/issues/ の 21 件(削除) | 001 / 003 / 007 / 011 / 012 / 013 / 014 / 015 / 021 / 022 / 026 / 033 / 057 / 058 / 059 / 061 / 062 / 063 / 064 / 067 / 068 |
| キットの修正 | `.claude/scripts/compose-changeset.py`(git 追跡外) | `verified:` ブロックの除去 / relations・features.md の版要求 / 変更指示 frontmatter の反映 / features.md の他 sections の適用 / features.md の `updated` |
| キットの復旧 | `.claude/scripts/callgraph-config.local.json`(git 追跡外) | 2026-08-10 のキット書き換えで失われた抽出設定を 02 に合わせて作り直した |

## タスクの計測

```
python3 .claude/scripts/task-metrics.py task-remove-orchestrator report
{ "started_at": 1786330301, "events": [], "elapsed_seconds": 0 }
```

`metrics.json` はフェーズ3 の途中(2026-08-10)に初めて作られたため、フェーズ1〜2
(2026-08-08)の経過は記録されていない。**このタスクの実時間は 2 日間**(2026-08-08 に
フェーズ1〜2、2026-08-10 にフェーズ3〜4)である。lane は `critical`。
