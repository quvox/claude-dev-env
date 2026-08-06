---
id: task-clause-ids-and-split-policy
phase: ドキュメント
origin_layer: 01
issue: docs/issues/060-modify-01-and-02-lack-clause-ids-split-policy-and-coverage-status.md
date: 2026-08-06
updated: 2026-08-07
source:
  - docs/01-requirements/functional.md
  - docs/01-requirements/non-functional.md
  - docs/01-requirements/usecases.md
  - docs/01-requirements/decisions/index.md
  - docs/01-requirements/decisions/split.md
  - docs/02-design/system.md
  - docs/pendings.md
  - docs/03-impl/tests/cli-attach.md
  - docs/03-impl/tests/cli-code.md
  - docs/03-impl/tests/cli-common.md
  - docs/03-impl/tests/cli-firewall.md
  - docs/03-impl/tests/cli-forward.md
  - docs/03-impl/tests/cli-list.md
  - docs/03-impl/tests/cli-login-codex.md
  - docs/03-impl/tests/cli-login.md
  - docs/03-impl/tests/cli-logout.md
  - docs/03-impl/tests/cli-orchestrate.md
  - docs/03-impl/tests/cli-ports.md
  - docs/03-impl/tests/cli-pull.md
  - docs/03-impl/tests/cli-reset.md
  - docs/03-impl/tests/cli-setup.md
  - docs/03-impl/tests/cli-ssh-keys.md
  - docs/03-impl/tests/cli-start.md
  - docs/03-impl/tests/cli-stop.md
  - docs/03-impl/tests/cli-unforward.md
  - docs/03-impl/tests/cli-upgrade.md
  - docs/03-impl/tests/container-tools.md
  - docs/03-impl/tests/docker-proxy.md
  - docs/03-impl/tests/entrypoint.md
  - docs/03-impl/tests/firewall.md
  - docs/03-impl/tests/hooks.md
  - docs/03-impl/tests/images.md
  - docs/03-impl/tests/makefile.md
  - docs/03-impl/tests/orchestrator.md
  - docs/03-impl/tests/portsync.md
  - docs/03-impl/tests/sample-project.md
  - docs/03-impl/tests/vm-mode.md
summary: 01 の受入基準に条項ID を振り、全要件に分割可否を入れ、02 の要件カバレッジ表を条項単位 + 充足列へ作り替える
---

> 解決済みの経緯: memo-1.md(フェーズ1の決定シート — 概念1〜4・論点1〜3・委任1の回答)

**回答待ち: sheet.md(論点 2 件)**
(フェーズ1分の概念1〜4・論点1〜3・委任1は回答済み・転記済み — 下の表。2026-08-07 の
フェーズ2で **論点4**(FR-env-01-9 の重複)と **論点5**(不可分の要件が部分の条項を持つ)を
追記した。どちらも未回答時の既定 = A。**論点5 は回答が無いと `/task-close` で 01・02 を
検証済みにできない**。
フェーズ1分の転記の経緯: 本 sheet は旧テンプレート製で「記入完了」欄が無いため、人間の
「SSOTを修正してほしい」という 2026-08-07 の直接指示を返却とみなし、空欄はシート冒頭の
約束どおり「既定を承認」として転記した)

## 目的

`.claude/directions/` が規範として定める3つの書式が SSOT に実装されていない状態を解消し、
**要件の部分充足を構造的に見えるようにする**(`docs/issues/060`)。規範自身の理由:

> Keyed by requirement, a design that realises one clause out of three is **textually identical**
> to one that realises all three, so partial satisfaction cannot be seen or checked.

## やること・やらないこと

**やること**

- `docs/01-requirements/functional.md` の受入基準 **201 行**に条項ID(`FR-<domain>-nn-#`)を振る。
- `functional.md`(21要件)と `non-functional.md`(13要件)に **`分割可否`**(`不可分` / `段階可(理由)`)を入れる。
- `docs/01-requirements/decisions/` を新設し、分割可否の判断を **`D1-*`** として記録する。
- `docs/02-design/system.md` の要件カバレッジ表(現 59 行)を**条項単位のキー + `充足` 列**へ作り替える。
- `docs/pendings.md` の `関連` を、`部分` を裏付ける条項ID で名指す形へ書き替える。

**やらないこと(理由つき)**

- **受入基準の意味は変えない。** 本タスクは記述形式の移行であり、要件の内容には触れない
  (触る必要が出たら別タスクにする)。
- **コードは変えない。** 実装への影響はゼロである。
- **`.claude/directions/` は変えない**(キット側の変更は `/kit-improve` 案件)。
- 03-impl/tests/*.md 30 ファイルの移行と CS9 の件を含めるかは**論点1・論点2**(回答待ち)。

## 影響範囲(closure)

| 層 | SSOT | 変更指示 | 変更の種類 |
|---|---|---|---|
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | modify |
| 01 | docs/01-requirements/non-functional.md | new-features/01-requirements/non-functional.md | modify |
| 01 | docs/01-requirements/system.md | (変更なし) | 変更なし(概念3 の回答 = SR は対象に含めない) |
| 01 | docs/01-requirements/usecases.md | new-features/01-requirements/usecases.md | modify(AC⇄UC 表の参照を条項ID へ) |
| 01 | docs/01-requirements/decisions/index.md | (変更指示なし) | 生成物(`build-index.py` が作る。手書きしない — `.claude/directions/01-requirements.md`。フェーズ1の add 宣言は誤りで、独立レビューの指摘で訂正) |
| 01 | docs/01-requirements/decisions/split.md | new-features/01-requirements/decisions/split.md | add(`D1-split-*`) |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | modify |
| 02 | docs/02-design/relations.md | (変更なし) | 変更なし(論点2 の回答 = C。CS9 の件は今回触らない) |
| — | docs/pendings.md | (SSOT ではないので変更指示を持たない。`/task-close` が直接直す) | modify |
| 03 | docs/03-impl/tests/cli-attach.md | new-features/03-impl/tests/cli-attach.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-code.md | new-features/03-impl/tests/cli-code.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-common.md | new-features/03-impl/tests/cli-common.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-firewall.md | new-features/03-impl/tests/cli-firewall.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-forward.md | new-features/03-impl/tests/cli-forward.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-list.md | new-features/03-impl/tests/cli-list.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-login-codex.md | new-features/03-impl/tests/cli-login-codex.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-login.md | new-features/03-impl/tests/cli-login.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-logout.md | new-features/03-impl/tests/cli-logout.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-orchestrate.md | new-features/03-impl/tests/cli-orchestrate.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-ports.md | new-features/03-impl/tests/cli-ports.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-pull.md | new-features/03-impl/tests/cli-pull.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-reset.md | new-features/03-impl/tests/cli-reset.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-setup.md | new-features/03-impl/tests/cli-setup.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-ssh-keys.md | new-features/03-impl/tests/cli-ssh-keys.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-start.md | new-features/03-impl/tests/cli-start.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-stop.md | new-features/03-impl/tests/cli-stop.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-unforward.md | new-features/03-impl/tests/cli-unforward.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/cli-upgrade.md | new-features/03-impl/tests/cli-upgrade.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/container-tools.md | new-features/03-impl/tests/container-tools.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/docker-proxy.md | new-features/03-impl/tests/docker-proxy.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/entrypoint.md | new-features/03-impl/tests/entrypoint.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/firewall.md | new-features/03-impl/tests/firewall.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/hooks.md | new-features/03-impl/tests/hooks.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/images.md | new-features/03-impl/tests/images.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/makefile.md | new-features/03-impl/tests/makefile.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/orchestrator.md | new-features/03-impl/tests/orchestrator.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/portsync.md | new-features/03-impl/tests/portsync.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/sample-project.md | new-features/03-impl/tests/sample-project.md | modify(対応表を条項ID キーへ) |
| 03 | docs/03-impl/tests/vm-mode.md | new-features/03-impl/tests/vm-mode.md | modify(対応表を条項ID キーへ) |

**変更の起点: 01**。理由 = 条項ID と分割可否は**要件そのものの記述形式と性質**であり、
02 のカバレッジ表はそれに従属する(条項ID が無ければ条項単位のキーを作れない)。
`.claude/directions/task-memo.md` §3.3 も「分割可否は 00/01 の概念で、答えは `D1-*` に記録する」と定める。

**触らない層の明示的な判断**

- **00: 変更なし。** 分割可否は 01 の要件の性質であり、`D1-*` に記録すると規範が定めている。
  `request.md` の「やらないこと」5項目のいずれとも衝突しない(いずれも機能の話で、記述形式の話ではない)。
- **03-impl/relations/(83本): 変更なし。** `MODULE-*` の frontmatter は要件を `requirements: FR-env-01`
  の**要件単位**で持つ。条項単位へ落とすかは規範が要求しておらず、今回は触らない。

**既存タスクとの関係**: なし(`docs/tasks/` は本タスク以外に空)。

**解消できる pending / issue**: `docs/issues/060`(本タスクの起点。全体)。
`docs/issues/066`(6件の NFR の目標値が要件文の一部しか測っていない)は**解消しない**が、
条項ID が入ると測定対象を条項で名指せるようになるため、次のタスクの前提が整う。

## 読む範囲(読了記録)

- 全文読了: 2026-08-06(本タスク直前の `/doc-check full` で 00〜02 を全ファイル読了。
  その実行で 01・02 を書き換えたので、下の版はいずれも書き換え後の現在値である)
  - docs/00-requests/acceptances.md@1.2.0
  - docs/00-requests/decisions/auth.md@1.2.0
  - docs/00-requests/decisions/dist.md@1.0.1
  - docs/00-requests/decisions/env.md@1.2.0
  - docs/00-requests/decisions/index.md@-
  - docs/00-requests/decisions/orch.md@1.3.0
  - docs/00-requests/decisions/scope.md@1.2.0
  - docs/00-requests/decisions/sec.md@1.1.2
  - docs/00-requests/request.md@1.3.0
  - docs/00-requests/terminology.md@1.2.0
  - docs/01-requirements/functional.md@1.8.1
  - docs/01-requirements/non-functional.md@1.3.1
  - docs/01-requirements/system.md@1.0.1
  - docs/01-requirements/usecases.md@1.2.1
  - docs/02-design/architecture.md@1.3.0
  - docs/02-design/contracts/cli-container.md@1.4.2
  - docs/02-design/contracts/cli-orchestrator.md@1.1.0
  - docs/02-design/contracts/docker-api.md@1.0.0
  - docs/02-design/contracts/entrypoint-firewall.md@1.0.1
  - docs/02-design/contracts/index.md@-
  - docs/02-design/contracts/orchestrator-prompt.md@1.3.0
  - docs/02-design/environments.md@1.1.0
  - docs/02-design/logging.md@1.3.0
  - docs/02-design/relations.md@1.4.0
  - docs/02-design/system.md@2.4.0
- 不要: docs/00-requests/decisions/._sec.md@- — 理由: macOS の AppleDouble メタデータファイル
  (バイナリ・git 未追跡)。仕様ドキュメントではない。**2026-08-07 解消: 人間が自ら削除済み**
  (`.gitignore` に `._*` を追加し `._sheet.md` も削除している。`find docs -name '._*'` は 0 件)

## 決定シート(回答済み)

フェーズ1分(概念1〜4・論点1〜3・委任1)の転記表は **memo-1.md に移動**した
(変更指示へ反映済みのため。`.claude/directions/task-memo.md` §2.1)。
フェーズ2で追記した **論点4・論点5 は未回答**で、回答が入ったらこの節へ転記する。

## 未決点

| # | 未決点 | 帰着 |
|---|---|---|
| 1 | `FR-env-01-9` のテスト対応行が2ファイル計3行に重複(cli-stop 1行 / cli-logout 2行。内容は異なる: logout側=E2E-01 手順8-5、reset側=手順8-12)。02 の主担当は1つしか書けない | **人間判断**(sheet.md 論点4。既定=A: 02 は MOD-cli-stop、重複は `docs/issues/074` で追跡) |
| 2 | **`FR-env-01` と `FR-env-07` は `分割可否: 不可分` なのに、条項 `FR-env-01-19` / `FR-env-07-5` の充足が `部分(P-005)`**。規範は「不可分の要件に部分の条項があれば例外なく PASS をブロックする」と定めるため、このままでは `/task-close` で 01・02 を検証済みにできない | **人間判断**(sheet.md 論点5。既定=A: 当該2要件を `段階可(理由)` にする)。委任 `D1-split-01` のガードレールが「3件以外を段階可にしたくなったら人間へ問う」と定めるため、AI では決められない |

上記2件を除き、ドライラン(自走 + 独立レビュー2本)で「決めないと反映できない」点は出なかった。
**未決点が残っているので `/implement` は開始できない**(原則7)。

## 調査メモ

**実測値**(2026-08-06。移行対象の規模)

| 対象 | 件数 | 出どころ |
|---|---|---|
| 機能要件 | 21 | `functional.md` の `## FR-` 見出し |
| 受入基準の行(= 条項ID を振る対象) | **201** | `functional.md` の `\| N \| 種別 \|` 行 |
| 非機能要件 | 13 | `non-functional.md` の `\| NFR-` 行 |
| システム要件 | 21 | `system.md` の `\| SR-` 行 |
| 02 の要件カバレッジ表の行 | 59 | `02-design/system.md` の `\| FR/NFR/SR-` 行 |
| 03-impl/tests の旧2列形式ファイル | **30** | `\| 要件 ID \| 受入基準 # \|` を含むファイル |
| pendings のエントリ | 5(P-001〜P-005) | `pendings.md` の `## P-` 見出し |

**基準線の訂正(2026-08-07)**: 下の凍結時に「CS11 の 23 件は全件 `docs/issues/054` が追跡する
削除済み issue のパス」と書いたが、**正しくは 22 件**である。残る1件は
`03-impl/feature-graph.md:230` → `docs/03-impl/callgraphs/resources.md` で、
生成物どうしの参照切れという別の欠陥(`docs/issues/075` に起票。キット側の修正が要る)。

**キット更新による生成物の陳腐化(2026-08-07 実測)**: `docs/03-impl/callgraphs/` の6ファイルと
`docs/03-impl/feature-graph.md` が現行ツールの出力と食い違う。staged へ生成して差分を取ったところ、
**違いは注記コメント(再生成コマンドの案内文と `BEGIN/END NOTE` マーカー)だけで、コード由来の
内容は1バイトも変わらない**。したがって原則2(コード ⇄ 03-impl の一致)は保たれており、
原因はキット更新である。`/task-close` §2 の SSOT 再生成で解消する。
検査に使った staged は `check-changeset.py` が変更指示と誤認する(`docs/issues/076`)ため削除した
(本タスクはコード無変更なので staged の生成義務は無い)。

**仕様ドキュメントの一括検査(母集団の凍結)** — 2026-08-06 `check-changeset.py --ssot docs`:

```
## 仕様ドキュメントの一括検査(SSOT 全体): 154 ファイル
  CS8 曖昧語・未決点: 違反 8 件
  CS11 参照実在: 違反 23 件
  CS12 同型の走査記録: OK
✗ 違反 31 件
```

CS8 の 8 件は全件 `pendings.md` P-002 / P-003 が追跡する「将来設定」、
CS11 の 23 件は全件 `docs/issues/054` が追跡する削除済み issue のパスである。**本タスクの対象外。**

**フェーズ2の実測・確認(2026-08-07)**

- 変更指示は35ファイル(01: 4 / 02: 1 / 03: 30)。`check-changeset.py` 合格
  (CS13 が 201条項 + NFR 13件の 01⇄02⇄03 照合を機械確認)。target 実在・sections 見出しの
  文字一致も全件機械確認済み。
- 条項 ID の初期値 = 現行の通し番号(ずれ・欠落・重複ゼロを機械照合。独立レビューも
  「201条項の照合・02表 235行・03 30ファイルの完全一致」を独立に確認)。
- 02 の条項主担当は `03-impl/tests/` の対応表の行配置から導出(全201条項で一致。
  唯一の例外 FR-env-01-9 は論点4)。
- 旧式参照「FR-x 受入基準N」は閉包外の 00/02/03 に **154 箇所**残るが、条項番号は現行番号を
  そのまま初期値とするため**全て有効なまま**(壊れる参照ゼロ。表記の統一は本タスクの対象外)。
- `build-index.py` の状態集計は列構成に依存しない(`.claude/templates/03-tests-module.md` の注記)。
  反映後に `--check` で再集計を確認する。
- `docs/03-impl/tests/strategy.md:115` の手書き集計(「全 182 基準 / 197 行」)は現状(201基準 /
  FR 202行 + NFR 14行)と食い違う既存欠陥 → `docs/issues/073` に起票(同型走査: 手書き集計は
  SSOT 内でこの1箇所のみ)。
- functional.md 冒頭の HTML コメント(過去の /doc-check 記録)内の旧式表記は**書き換えない**
  (日付つきの履歴記録であり、番号が同一なので参照は壊れない — 独立レビュー指摘#6 は誤検知と裁定)。

**関連する既知の事実**

- `docs/03-impl/tests/` の対応表は **264 行が「未検証(テスト未実装)」**で、E2E-01〜06 は全件未検証。
  `充足` 列を「実装が満たしているか」で書くと、ほぼ全件が根拠を持たない値になる(概念4 の論点)。
- CS9(02 `PLAN-*` ⇄ 03 `MODULE-*`)は `check-changeset.py:343` が PLAN-ID をバッククォートで
  囲むことを要求するのに `02-design/relations.md` の一覧表(64行)が囲んでいないため、
  **本プロジェクトで一度も実行されていない**(`docs/issues/060` の追加節。論点2)。

## 質問キュー(未提示)

(なし。フェーズ2で出た1件は sheet.md 論点4 として提示済み — 未決点表を参照)

## タスクリスト

(フェーズ3 `/implement` が確定する。下書き)

- [ ] 論点4 の回答を変更指示へ反映する(A なら変更なし + issue 起票 / B なら cli-logout.md の指示を修正)
- [ ] コード変更: **なし**(本タスクはドキュメントのみ。`/implement` はコード差分ゼロの確認と検査群の実行だけを行う)
- [ ] `/task-close` 時: 変更指示35ファイルの反映 → `docs/pendings.md` P-005 の `関連` を条項 ID の名指しへ書き替え(具体文言は申し送り) → `build-index.py`(tests 集計・issues・decisions index)→ 検査群の再実行

## Definition of Done

(フェーズ3で埋める)

## 進捗メモ

- 2026-08-06 `/task-new 060` でタスクを作成。`docs/issues/060` からの昇格。
  直前の `/doc-check full` が 00〜02 を全文読了しており、その読了記録を転記した。
  **`/doc-check full` の SSOT 修正はすべてタスク作成前に完了している**(タスクが存在すると
  原則1 により `/doc-check` は SSOT を直せなくなるため、順序を意図的にこうした)。
- 2026-08-07 `/doc-check(task) 判定: 不合格(残存2件 — いずれも人間判断待ち。指摘の重大度「高」は0件)`。
  レビュー: **サブエージェント**(Codex は利用上限で 2026-08-11 まで起動不可。人間の常設承認により代替。
  `readiness` と `docs` の2本、いずれも model=sonnet / Explore 型・読み取り専用)。
  実行形態: **著者セッション**(フレッシュコンテキストのサブエージェントが API のセッション上限で
  中断したため。`/doc-check` §0A 第3行)。
  検証済みの状態(次回の増分実行の基準):
  - 変更指示35ファイルのハッシュ集約 `sha1sum` = `5a370185c77b7cd9`
  - closure の現在版: `01-requirements/functional.md@1.8.1` / `non-functional.md@1.3.1` /
    `usecases.md@1.2.1` / `system.md@1.0.1` / `02-design/system.md@2.4.0` /
    `02-design/relations.md@1.4.0` / `03-impl/tests/*.md@1.0.1〜1.5.1`
  - 機械検査: `check-changeset.py` 合格(CS1/4/8/13/14/15 OK。CS16 は移行前のため未検査)/
    `check-relations.py` 合格 / `callgraph-check.py` 高0 / `check-contracts.py` 合格 /
    `build-index.py --check` 差分なし
- 2026-08-07 フェーズ2の下降を完了: 00 変更なし(理由は「触らない層の明示的な判断」)→ 01 完了
  (functional / non-functional / usecases / decisions/split.md)→ 02 完了(system.md
  要件カバレッジ確認)→ 03 完了(tests 30ファイル)。`check-changeset.py` 合格。
  実装ドライラン: 独立レビューは Codex が利用上限(〜2026-08-11)のため起動できず、
  **常設承認(docs/feedbacks 相当の人間指示 2026-08-05)に基づきサブエージェントで代替**
  (`lens: subagent`、モデル sonnet(Sonnet 5)/ reasoning はセッション既定。Explore 型・読み取り専用)。
  指摘6件を裁定: #1 closure の decisions/index.md 行の誤り(修正済み=生成物注記)/
  #2 質問キュー参照切れと重複件数の訂正(修正済み + 論点4へ)/ #3 P-005 の関連欄が FR-env-07-5 を
  名指ししていない(申し送りへ反映済み)/ #4 D1-split-01 の関連の範囲表記(修正済み=列挙)/
  #5 02 reason の「旧表から変えていない」の曖昧さ(修正済み=書き分け)/ #6 functional.md 冒頭
  コメントの旧式表記(誤検知と裁定: 日付つき履歴記録は書き換えない)。
- 2026-08-07 決定シート回答を転記しフェーズ1完了(`check-sheet.py` PASS)。`phase: ドキュメント` へ。
  同日キットが更新されており(全ファイル 00:42 再配置)、`.claude/directions/01-requirements.md` は
  条項ID の安定規則を規範自身が持つ形になった(検査 CS16 新設)。概念2 の回答(安定ID)と同方向で
  矛盾なし。SSOT 一括検査は基準線と同一(違反31件 = 全件 issues/054・pendings P-002/P-003 が追跡)、
  `check-relations.py` 合格、`callgraph-check.py` 重大度「高」0件。

## 申し送り事項

- 本タスクは**記述形式の移行**であり、受入基準の意味とコードは変えない。
  意味を変える必要が出た時点で、それは別タスクの起点である。
- **`docs/pendings.md` P-005 の `関連` は 2026-08-07 に修正済み**(条項 `FR-env-01-19`・`FR-env-07-5` を
  名指す形へ。`/doc-check` task モードは pendings を書いてよい — `/doc-check` §0 の書き込み表)。
  `/task-close` で改めて直す必要は無い。他の pending の `関連` は触らない(決定シート論点3=B)。
- `/task-close` で `build-index.py` を必ず実行する(01-requirements/decisions/index.md の新規生成、
  issues index、tests の状態集計の再生成)。
- **`/task-close` §2 の SSOT 再生成で、キット更新による生成物の陳腐化も解消する**
  (`docs/03-impl/callgraphs/` 6ファイルと `feature-graph.md`。差分は注記コメントだけ。調査メモ参照)。
- **反映で検証済み記録が失効する下流は 50 ファイル**(02 の全ファイル + 03-impl の contracts /
  environments / infra / index / tests 全件)。`/task-close` の再認証はこの規模になる
  (`source` の推移閉包で機械的に算出済み)。
- 本タスクで起票し、**本タスクでは直さない** issue: `073`(strategy.md の手書き集計が古い)/
  `074`(FR-env-01-9 のテスト対応行が3行。論点4 が B・C で回答された場合は削除する)/
  `075`(feature-graph.md → callgraphs/resources.md の参照切れ。キット側の修正が要る)/
  `076`(check-changeset.py が staged コールグラフを変更指示と誤認する。キット側の修正が要る)。
  **`075` と `076` は `/kit-improve` 案件**で、`docs/` の修正では閉じられない。
