---
id: 004-modify-03-impl-lacks-reimplementation-depth
type: modify
severity: 中
found: 2026-08-03
found_in: task-docs-restructure の /doc-check(Claude 自身の実装ドライラン パス1。独立レンズの指摘ではない)
related: MODULE-cli-start, MODULE-cli-forward, MODULE-orchestrator-controller, MODULE-orchestrator-state-io, CTR-cli-container, CTR-cli-orchestrator, CTR-orchestrator-prompt
summary: 03-impl が「現状の説明」としては正しいが、ドキュメントだけから再実装・再試験できる深度に達していない領域が当初約20件あった。2026-08-03 の task-impl-depth で観点1〜5(入力検証・永続化・並行性・外部依存の失敗・ログ)と観点7(契約の型)を解消済み。**残件は「## 経緯」の4項目**(永続データモデル / モデル・effort ポリシー / 観点6 テストデータ / 02 契約の復号レベルのエラーケース)
---

# 004 03-impl に「ドキュメントだけから再実装・再試験できる」深度が無い領域がある

## 事象

`task-docs-restructure` の `/doc-check` で実装ドライラン パス1(ドキュメントだけを読み、
「決めないと実装を進められない点」を洗い出す)を行ったところ、**記述の深度が足りない**領域が
次の観点に集中していることが分かった。

<!-- 出所の訂正(2026-08-03): この issue は当初「独立レンズ(Codex readiness 3本)が高14件を含む
     29件を報告した」と書いていたが、それは事実ではない。実際に走った Codex readiness 2本の指摘は
     反映手順に関する11件で、下記の深度不足は含まれていない。下記は Claude 自身がドキュメントを
     読んで洗い出したものである。件数「約20件」も概算であり、レンズが数えた値ではない。 -->

| 観点 | 代表例 | 該当 |
|---|---|---|
| 入力検証と境界値 | `claude-dev forward <cport>` の `<cport>` が「整数」としか定義されず、0・負数・65536 以上・空・非数値・先頭ゼロの受理/拒否とメッセージが無い。`taskID` の許容文字・長さ・パストラバーサルも同様 | `MODULE-cli-forward` / `MODULE-cli-unforward` / `MODULE-orchestrator-worktree` |
| 永続化とトランザクション境界 | `start` の「認証コピー → 設定抽出 → hook コピー → `.gitignore` 追記 → Docker 資源作成」で、途中失敗時にどこまで残すか・再実行がどこから安全に回復するかの一貫性境界が無い。orchestrator も plan/state・git merge・複数の JSONL 追記を横断する境界と復旧順序が未定義 | `MODULE-cli-start` / `MODULE-orchestrator-state-io` / `MODULE-orchestrator-controller` |
| 並行性と順序 | 同時 `start` / `forward` / `reset` / `logout` の排他単位と許容結果が未定義。`forward` は競合時のリトライが無い。orchestrator は worker 完了・TUI 操作・tick・シグナルが同時に来たときの排他と重複イベントの冪等性が未記載 | `MODULE-cli-*` / `MODULE-orchestrator-controller` |
| 外部依存の失敗時の挙動 | Docker / GHCR / Slack / Claude CLI の失敗が「非0で停止」「握りつぶす」までで、認証失敗・タグ不存在・レート制限・通信断・部分取得の区別、タイムアウト・再試行回数・バックオフが無い | `infra/local/ghcr.md` / `MODULE-orchestrator-slack` / `MODULE-orchestrator-claude-exec` |
| ログ・可観測性 | 出力先が機能ごとに断片的で、レベル・時刻・run/task 識別子といった必須フィールドと、秘密値のマスキング方針が定義されていない | 03-impl 全般 |
| テストデータの準備と後始末 | 多くの機能が「自動テストランナーが無く実機確認で代替」とするだけで、実機確認の確認項目・初期状態・作成資源・失敗注入・cleanup の責任者・残存確認が無い | `03-impl/tests/` 全般 |
| 契約の型 | `CTR-orchestrator-prompt` の「必要な文脈」「構造化された結果」がフィールド単位で定義されておらず、必須性・型・列挙値・欠落時の判定を導出できない | `contracts/orchestrator-prompt.md` |

## なぜ本タスクで直さないか

`task-docs-restructure` は**ドキュメント体系の移設**であり、「やらないこと」に
**コードの変更**と**仕様そのものの変更(振る舞い・受け入れ基準の意味を変えない)**を掲げている。
上記を埋めるには、実装を読んで現在の振る舞いを新たに文書化する作業(観点によっては
「決まっていないことを決める」作業)が必要で、移設の範囲を超える。

また、この指摘は「**ドキュメントだけを読んで製品全体を再実装できるか**」という基準で出ている。
本タスクのフェーズ3は実装ではなく SSOT への反映であり、反映の実行可能性は別途担保されている
(memo のタスクリスト7 の手順)。したがって本タスクの完了はブロックしない。

## 影響

- 現状の把握には支障がない(03-impl はコードの合わせ鏡として `check-relations.py` /
  `callgraph-check.py` / `relations-coverage.py` に合格している)。
- 効いてくるのは**この領域を変更するタスクが立ったとき**である。境界値・異常系・並行性が
  書かれていないと、`/implement` が未決点ゼロの入場条件を満たせず、その時点で調査が発生する。

## どうしたいか

領域ごとに小さなタスクへ分割して埋める。優先度は次の順を推奨する。

1. **並行性と永続化の境界**(`MODULE-cli-start` / `MODULE-orchestrator-state-io`)— 事故が起きたときの
   影響が最も大きく、実測しないと分からない事実を含む。
2. **入力検証と境界値**(`MODULE-cli-forward` / `MODULE-orchestrator-worktree`)— コードを読めば
   一意に決まるので安価。パストラバーサルはセキュリティに直結する。
3. **外部依存の失敗時の挙動**と**ログ・可観測性** — 運用に効く。
4. **契約の型**(`CTR-orchestrator-prompt`)。

`03-impl/tests/` の「実機確認の手順化」は `docs/pendings.md` の QA レーン(P-003)と同時に扱うのが
効率的である。

## 関連

- `docs/pendings.md` P-003(QA レーンの各設定が未定)
- 検出経緯は `task-docs-restructure` の memo.md「独立レンズの実際の結果」および
  「/doc-check(task モード)2026-08-03 — 追加の未決点と裁定」

## 経緯

- 2026-08-03 `/task-new` でタスク `task-impl-depth` に昇格(issue 008 を同時対象、issue 009 は (b) のみ)。
- 2026-08-03 `task-impl-depth` のフェーズ2で**観点1〜5と観点7(契約の型)を解消**した
  (relations 19本・契約3件(02/03)・`infra/local/ghcr.md`・`tests/` 4件・01 の受入基準15行)。
  **本 issue は閉じない**(決定シート#6=B の人間の判断)。残件は次の3つである。
  1. **orchestrator の永続データモデルの記述**: `plan.json` / `state.json` /
     `intervention/open.json` のフィールド表(型・必須・`Status` の列挙・`Attempts` /
     `Irreversible` / `IrrevApproved` / `SessionID` / `ResumeSession` / `ReviewFormatErrors` の
     意味と既定)が 03 に無い。対象は `MODULE-orchestrator-state` / `-plan`
     (`task-impl-depth` の影響範囲外)。
  2. **工程別のモデル / effort ポリシーの記述**: `orchestrator/models.go` の
     「熟考 = `opus`/`high`、既定 = `sonnet`/`high`、`Task.Kind` による分岐」が 03 に無い。
     対象は `MODULE-orchestrator-claude-exec` / `-config` と `CTR-orchestrator-prompt`。
  3. **観点6(テストデータの準備と後始末)**: 変わらず `docs/issues/006` と
     `docs/pendings.md` P-003(QA レーン)に依存する。
  4. **02 の `CTR-orchestrator-prompt`「エラーケース」が復号レベルの異常を列挙していない**
     (★2026-08-03 `/doc-check` の独立レンズ Codex `readiness` が検出して追加)。
     型不一致・未知フィールド・必須欠落に対する受理/拒否は **03 側に実挙動を記載して閉じた**が、
     02 側は「解釈可能な結果 JSON が無い → 失敗」までしか述べていない。設計意図として
     デコーダの寛容さをどこまで要求するかは設計判断であり、質問キュー #8 の回答
     「02 契約の期待する振る舞いは今回触らない」に従って本タスクでは扱わなかった。重大度は「低」。
- 掘り下げの過程で起票した issue: `010`〜`016` / `020`〜`026` / `028` / `029`
  (`017`〜`019` および `023` は同タスクの `/doc-check` が起票。`027` は誤検知として取り消し)。
  ★2026-08-03 `/doc-check`: この一覧は以前 `010`〜`016` と `020`〜`022` しか挙げておらず、
  `023`〜`026` / `028` / `029` が漏れていた(`03-impl/index.md` の件数も同じ漏れを持っていた)。

## 追加(2026-08-05 `task-relations-code-sync` フェーズ2の実装ドライラン)— 独立レンズが残件を機能単位で列挙した

`/task-doc task-relations-code-sync` の実装ドライラン(パス1)で、独立レンズ(Codex `readiness`。
`gpt-5.6-terra` / reasoning `max`。スコープを3分割して実行)が **42 件**を返した。
うち **13 件は変更指示と未置換の節の自己矛盾**で、その場で全件修正した(同タスクの担当)。
**残る「深度が足りない」系の指摘は本 issue の残件そのもの**であり、機能単位に整理して記録する。
**コードを読まずにドキュメントだけで再実装できるかを試した結果**なので、
「経緯」の3項目より細かい粒度の作業リストとして使える。

| 対象 | ドキュメントだけからは決められない事柄(レンズの指摘) | 経緯のどの項目 |
|---|---|---|
| `MODULE-orchestrator-state` / `-plan` | `Store` 各 API の完全なシグネチャと戻り値型 / `State`・`Plan` の JSON 型・任意性・時刻形式 / `ReadyTasks` の返却順序・`nil`・空・重複 ID・自己依存・未知 `Status` の扱い / `blocked` 伝播が1回の呼び出しで閉じるか | **項目1** |
| `MODULE-orchestrator-config` | 許可キーの全列挙 / 空白・コメント・引用符・重複キー・オーバーフローの扱い / `orchestrator:` 節の文法 / 文字列キーの全列挙 | **項目2 に隣接**(設定の記述) |
| `MODULE-orchestrator-claude-exec` / `CTR-orchestrator-prompt` | `Task.Kind` から profile を選ぶ対応表と既定値 | **項目2** |
| `MODULE-orchestrator-worker` / `CTR-orchestrator-prompt`(02) | 結果 JSON の候補選択の優先順位(複数 JSON 行・末尾ログ・`done` 無し)/ 型違い・配列要素の型違い・`null`・壊れた入れ子・未知 `severity`・制御ファイルの型違いの扱い | **新規**(02 契約側。03 側には実値がある) |
| `MODULE-orchestrator-controller` | ready が `max_workers` を超えたときの選択順と同順位規則 / 状態遷移・介入投入・完了・統合ごとの**書き込み順**と途中停止時の復旧規約 | **新規**(一貫性境界の粒度) |
| `MODULE-orchestrator-session` | `ExpectedWindows(phase, plan)` の入力状態 → 期待ウィンドウ列の対応表 / `EnsureAll` の復旧順序 | **新規** |
| `MODULE-orchestrator-mode` | `ModelProfile` の構造 / 生成する launcher スクリプトの正確な内容 / `.sys`・`.prompt`・`.sh` の途中失敗時の順序と掃除 | **項目2 に隣接** |
| `MODULE-orchestrator-dashboard` | `dashAction` と行モデルの型 / 更新メッセージと描画順 / VM health の「鮮度内」の数値 | **新規** |
| `MODULE-orchestrator-streamlog` | イベント / content の JSON スキーマ / CRLF・未終端行・空行・短い書き込み・同時 `Write` の扱い | **新規** |
| `MODULE-orchestrator-trigger` | 不正・欠損の `TriggerContext`(未知 `Phase`・`nil Result`)を渡したときの戻り値 | **新規** |
| `MODULE-orchestrator-main` | `defaultWorkspace()` の規則 / 未知・欠損フラグの扱い / 各失敗経路の終了コードと後始末 / 標準出力へ出す7種の具体的文面 | **新規** |
| `MODULE-cli-start` / `-stop` / `-reset` と Slack / claude-exec | **再試験の手順が作れない**: シェル系と外部依存(Slack API・`claude` 実行ファイル)に対する fake・入力ベクトル・期待観測が無く、参照先が `E2E-01` の手順番号だけである | **項目3(観点6)** |

**本 issue は閉じない。** 上の表は「経緯」の3項目を機能単位へ展開したものであり、
次に 03 の深度を扱うタスクの closure の候補である。**`task-relations-code-sync` の範囲外**
(同タスクは「既にある記述をコードへ合わせる」ことだけを行い、深度の追加はしない)。
