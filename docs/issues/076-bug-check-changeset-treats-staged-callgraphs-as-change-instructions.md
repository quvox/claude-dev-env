---
id: 076-bug-check-changeset-treats-staged-callgraphs-as-change-instructions
type: bug
severity: 中
found: 2026-08-07
found_in: /doc-check(task-clause-ids-and-split-policy の check F)
related: .claude/scripts/check-changeset.py, .claude/scripts/close-task.py, .claude/directions/change-set.md, .claude/directions/callgraphs.md
pattern: staged-derived-artefact-treated-as-change-instruction
pattern_survey: `new-features/` 配下を走査するキットのスクリプト3本(check-changeset.py / close-task.py / callgraph-check.py)を確認。導出物の除外を持たないのは check-changeset.py の変更指示モードのみ(1件)
summary: 進行中タスクの staged コールグラフを check-changeset.py が変更指示とみなし、CS1 違反 29 件でフェーズ2のゲートが通らなくなる
---

# 076 `check-changeset.py` が staged コールグラフを変更指示として検査する

## 事象

`.claude/directions/callgraphs.md` §3.1 は「進行中タスクがある間、コールグラフの生成先は
`docs/tasks/task-<slug>/new-features/03-impl/callgraphs/`(staged)」と定め、
`.claude/directions/change-set.md` は
「**`new-features/03-impl/callgraphs/` にファイルが存在するのは正常**である — これは変更指示ではなく
導出物であり、`close-task.py` はこの理由でゲートから除外する」と明記している。

しかし `check-changeset.py` の**変更指示モード**は、この除外を持たない。
規範どおりに staged を生成すると、導出物7ファイル(`callgraphs/` 6 + `feature-graph.md`)を
変更指示として読み、`target` / `change` / `reason` / `deletes` が無いとして
**CS1 違反 29 件**を出す。`/task-doc` §4 は「exit 0 が下降を終える条件」と定めるため、
**フェーズ2のゲートが構造的に通らなくなる**。

`--ssot` モード側には除外がある(`check-changeset.py:913` 「`03-impl/callgraphs/` は除く
(ツールの純粋な導出物。曖昧語の概念が無い)」)。**片側にだけ除外がある**のが直接の原因である。

再現手順:

1. 進行中タスクがある状態で
   `CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) && python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT"` を実行する
   (`/doc-check` B6 と `.claude/directions/callgraphs.md` §3.1 が指示する形)。
2. `python3 .claude/scripts/cluster-features.py --out "$CG_OUT"` も実行する。
3. `python3 .claude/scripts/check-changeset.py docs/tasks/task-<slug>/new-features` を実行する。
4. `CS1 変更指示の形: 違反 29 件`(対象 42 ファイル)となり終了コードが非0になる。

## 影響

**コードを変更するタスクは、規範どおりに staged を生成した時点でフェーズ2のゲートを通せなくなる。**
回避するには規範に反して staged を生成しないか、検査結果を無視するしかない。
どちらも「機械検査を人間が読み飛ばす」習慣を作るため、severity は「中」とする。
`close-task.py` は正しく除外するので、フェーズ4は影響を受けない。

本プロジェクトの `task-clause-ids-and-split-policy` はコードを変更しないため、
staged を生成しないことで回避した(生成しない選択自体は正常 — `/doc-check` の check B は
「コードがあるとき」の検査であり、コード無変更のタスクに staged の生成義務は無い)。

## 原因の見当

`check-changeset.py` の変更指示モードのファイル収集が、`new-features/` 配下の `*.md` を
すべて変更指示として扱っている。`--ssot` モード側(913〜919行)には
`if "callgraphs" not in p.parts` の除外があるが、変更指示モード側には無い。
`feature-graph.md` はどちらのモードでも除外されていない。

## 正はどちらか

| 観点 | 実装(スクリプト)はどう言っているか | 規範(directions)はどう言っているか | 判定 |
|---|---|---|---|
| staged 導出物の扱い | `check-changeset.py` の変更指示モードは変更指示として検査する | `change-set.md`「存在するのは正常。変更指示ではない」/ `close-task.py` は除外する | **規範が正**。スクリプトを直す |

## 対処案

**キット側の修正であり `/kit-improve` 案件である**(本プロジェクトの `docs/` では閉じられない)。

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | 変更指示モードの収集から `03-impl/callgraphs/` と `03-impl/feature-graph.md` を除外する(`close-task.py:57-62` の `VERSIONLESS_DOCS` / `CALLGRAPH_SEGMENT` と同じ定義を使う) | `check-changeset.py` のみ。3本のスクリプトで除外の定義が1つに揃う |
| B | 除外の定義をキットの共有モジュールへ出し、3本のスクリプトが同じ判定を使う | 3本 + 新設モジュール。将来の導出物の追加に強い |

## 経緯

- 2026-08-07 起票。`task-clause-ids-and-split-policy` のフェーズ2で、
  `/doc-check` B6 の指示どおり staged を生成した直後に CS1 が 29 件出て発覚した。
  同タスクはコード無変更のため staged を削除して回避し、ゲートは緑に戻した。

## 経緯

- 2026-08-07 `/implement`(task-stop-session-spawned-containers のフェーズ3 C-1):
  **予告どおり再現した**。`/implement` C-1 が指示する
  `build-callgraphs.py --out <staged>` と `cluster-features.py --out <staged>` を実行した直後、
  `python3 .claude/scripts/check-changeset.py docs/tasks/task-stop-session-spawned-containers/new-features`
  が **CS1 違反 29 件**(`03-impl/callgraphs/*.md` 6件 + `feature-graph.md`、各4項目)で
  非0終了した。**変更指示 19 ファイルそのものには違反が無い**ことを、
  導出物2つを一時的に退避して同じコマンドを流し直して確認した(`合格: 不変条件の違反なし`)。
- **この issue の回避策**: 検査したいときは `03-impl/callgraphs/` と `03-impl/feature-graph.md` を
  一時退避してから `check-changeset.py` を流す。`close-task.py` は除外を持つので影響を受けない
  (同タスクの `--check` は6条件すべてこの2つを数えなかった)。
- **フェーズ2 とフェーズ3 で被害の出方が違う**: フェーズ2 は staged を作らないので通るが、
  フェーズ3 は `/implement` C-1 が作れと指示するので**必ず踏む**。
  対処案 A(`--ssot` 側と同じ除外を変更指示モードにも入れる)の優先度は、
  当初の見積もりより高い。

