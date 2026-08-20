---
id: 097-modify-cli-help-dispatch-branch-is-absent-from-the-feature-table
type: modify
severity: 中
origin_layer: 02
found: 2026-08-11
found_in: /relations all --apply の独立レビュー(Codex)
related: docs/03-impl/features.md, MODULE-makefile-help, docs/01-requirements/usecases.md
closes_when: 人間が `MODULE-cli-help` を機能表に加えるか加えないかを回答し、その回答が docs/03-impl/features.md に反映されたとき(加える場合は docs/03-impl/relations/MODULE-cli-help.md と 02-design/relations.md の PLAN-* まで反映されたとき)
pattern: なし
pattern_survey: なし
summary: CLI の `help|*)` ディスパッチ分岐(ヘルプ表示と未知サブコマンドの受け皿)が機能表に無く、対応する MODULE-*.md も存在しない
---

# 097 CLI の `help` 入口が機能表に無い

## 事象

`claude-dev` / `claude-dev-mac` の `main` の case 文に `help|*)` 分岐が実在し、
ヘルプ本文を表示する。

- `claude-dev:2651` — `help|*)` (直前のコメントは `# ヘルプ`)
- `claude-dev-mac:2693` — 同じ分岐

しかし `docs/03-impl/features.md` の「機能一覧」表に対応する行が無く、
`docs/03-impl/relations/MODULE-cli-help.md` も存在しない。
機能表にある `help` は `MODULE-makefile-help`(`Makefile::help`)だけで、これは別物である。

**この分岐は `*)` を兼ねているため、未知のサブコマンドを打ったときの受け皿でもある。**
利用者から見て観測できる CLI の振る舞いでありながら、どの機能にも属していない。

再現手順:

1. `grep -n 'help|\*)' claude-dev claude-dev-mac`
2. `grep -n 'help' docs/03-impl/features.md` — `MODULE-makefile-help` の1行しか出ない

## 影響

`callgraph-check.py` の **FT2(機能表に無いエントリポイント)は 0 件を報告する**が、
それは shell 抽出器が `help|*)` をエントリポイントとして取り出せていないためで、
**機械の網が通っていないことによる 0 件**である(Tier 3 = 正規表現抽出。
`.claude/directions/features.md` §5.1 が言う「無いことの主張が弱い」場所に当たる)。
`docs/03-impl/index.md` の「`relations-coverage.py` 最終結果 … 未記載 0 件」も同じ理由で、
この1件を含んでいない。

未知サブコマンドの扱い(何を表示し、どの終了コードで終わるか)がどの層にも書かれていない。

severity は、**振る舞いそのものは正しく動いており文書側の欠落である**ため「中」とする。

## 原因の見当

推測: `docs/histories/2026-08-03-docs-restructure.md` の機能表起草時、
入口の一覧を `propose-features.py` の出力から写したため、
抽出器が拾わない `help|*)` が最初から候補に上がらなかった。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| `claude-dev help` と未知サブコマンドの振る舞い | `claude-dev:2183` / `claude-dev-mac:2207` の `help|*)` がヘルプ本文を表示する | 機能表・relations・`01-requirements/usecases.md` のいずれにも記述が無い | **実装が正**(実在する振る舞いであり、文書側の欠落) |
| 機能表に `MODULE-cli-help` の行を足すか | — | — | 要確認(境界の合意は人間の仕事。`.claude/directions/features.md` §7) |

## 対処案

**★ 2026-08-11 追記: 案 A は現状のままでは実施できない**(下の「実測」参照)。

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | 機能表に `MODULE-cli-help` を1行追加し(入口は `claude-dev::main#help` と `claude-dev-mac::main#help` を統合)、`docs/03-impl/relations/MODULE-cli-help.md` を1本書く。未知サブコマンドの終了コードを実測して記載する | **実施不能**。入口がコールグラフに無いため FT1 が重大度「高」で落ち、以降の検査が打ち切られる |
| A2 | コードで `help)` と `*)` を**別のラベルに分ける**。そうすると抽出器が `help` を入口として拾い、案 A が成立する | コード変更(`claude-dev` / `claude-dev-mac` 各1箇所)+ 案 A の影響範囲。**未知サブコマンドの振る舞い(現在は終了コード 0)を変えるかどうかの判断も伴う** |
| A3 | 抽出器の決定 D を「ラベル全体ではなく `*` の要素だけを落とす」に直す | **キット変更**。CLAUDE.md §3 により製品 DoD 未達の間は凍結されている |
| B(AI推奨) | 機能表の記録節に「機能にしない」と理由つきで記録し、未知サブコマンドの振る舞いは 01 の受入基準として書く | 機能表に1行 / 01 に条項1〜2件 / 02 のカバレッジ表と 03 のテスト対応表に対応する行 |

**2026-08-11 時点の AI 推奨は B。** 理由: A は実施不能、A3 は凍結中、A2 は
「未知のサブコマンドで終了コード 0 を返し続けてよいか」という**利用者から見える振る舞いの判断**を
含むので、`/task-new` で別タスクとして立てるのが筋である。崩れる条件: 製品 DoD を満たして
キットの凍結が解けたとき(そのときは A3 → A が最も素直になる)。

## 実測(2026-08-11。`task-promote-shared-helpers` フェーズ2 のドライラン)

1. **`help` の入口はコールグラフに存在しない。** シェル抽出器の**決定 D**
   「catch-all(`*` を含むラベル)は入口にしない」は、**ラベル全体を落とす**実装である
   (`.claude/scripts/cgx/shell_regex.py:169` の `if "*" in label:`)。
   `help|*)` はラベル全体が該当するので、**`help` の側も巻き添えで落ちる**。
   `docs/03-impl/callgraphs/shell.md` に `dispatch help @ claude-dev::main` の行は無い。
2. したがって機能表に `MODULE-cli-help` の行を足すと、**FT1(入口がコールグラフに存在するか)が
   重大度「高」で落ちる**。FT1 は落ちると以降の検査を打ち切るゲートなので、
   CG1〜CG7 まで含めた機械検査が丸ごと無効になる(`DSN-mod-05` が同じ理由で
   Dockerfile をモジュールから外している)。
3. **振る舞いの実測**: `claude-dev help` も未知のサブコマンド(`claude-dev nosuchsubcommand`)も、
   ヘルプ本文を**標準出力**へ出して**終了コード 0** で終わる。
   **未知のサブコマンドでも 0 なので、自動実行では打ち間違いを検出できない。**

## 経緯

- 2026-08-11 `task-promote-shared-helpers`(`docs/issues/096` のタスク)のフェーズ1 決定シート 論点3 で「本 issue を畳み込む」と回答を得たが、**フェーズ2 のドライランで案 A が実施不能と判明したため closure から外した**(上の「実測」を追記して差し戻した)。096 の範囲は同タスクで完遂している
- 2026-08-11 `/relations all --apply` の独立レビュー(Codex)が検出し起票。**この実行では機能表に行を足していない** — 機能の追加は境界の変更であり `.claude/directions/delegation.md` §2 の DS-05「対象外」に当たる。加えて `--apply` のケース2 は 02 層への書き込みを許さないため、案 A は `/task-new 097` でタスク化しないと実施できない
