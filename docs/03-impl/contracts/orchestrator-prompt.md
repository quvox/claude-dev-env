---
id: orchestrator-prompt
version: 1.1.0
updated: 2026-08-04
source:
  - docs/02-design/contracts/orchestrator-prompt.md
kind: other
impl: orchestrator/mode.go::Mode.ResolveArgs
summary: オーケストレーターが worker / 対話 Claude へ渡すプロンプトと受け取る結果の取り決め(実装側)
keywords: [契約, CTR, 実装]
verified:
  at: 2026-08-07
  version: 1.1.0
  against:
    - doc: docs/02-design/contracts/orchestrator-prompt.md
      version: 1.3.0
---

# CTR-orchestrator-prompt orchestrator → worker / 対話 Claude(実装)

- 実装: `orchestrator/mode.go::Mode.BrainstormingArgs` / `orchestrator/mode.go::Mode.ResolveArgs` /
  `orchestrator/mode.go::Mode.IntervenePrompt` / `orchestrator/mode.go::Mode.WriteLaunchScript`
  (対話モード)、`orchestrator/worker.go::Worker.BuildPrompt` /
  `orchestrator/worker.go::Worker.Dispatch`(worker)、
  `orchestrator/worker.go::ParseWorkerResult`(結果の解釈)
- 当事者: MOD-orchestrator → worker / 対話 Claude
- 対応する設計: `docs/02-design/contracts/orchestrator-prompt.md`

## 実装上の事実

| 項目 | 実際の値 | 定義箇所 |
|---|---|---|
| worker の起動 | 非対話実行。`-p <プロンプト> --output-format stream-json --verbose` を常に付け、`--model` / `--effort` はポリシー表の値、`--permission-mode` は `worker_permission_mode`(既定 `bypassPermissions`。**空文字ならフラグ自体を付けない**) | `orchestrator/worker.go::ExecClaude.RunPrompt`(`:350`〜`:364`) |
| 新規セッション / 再開 | `--session-id <UUIDv4>` で新規、`--resume <同じ ID>` で同一 Attempt の継続。**どちらも指定が無ければフラグを付けない**。ID は `crypto/rand` で生成する RFC 4122 v4 | `orchestrator/worker.go::ExecClaude.RunPrompt`(`:368`〜`:374`), `newSessionID`(`:19`) |
| 中断時の猶予 | `worker_grace_seconds > 0` のとき、`SIGKILL` ではなく **`SIGINT` を送り**、その秒数まで待ってから強制終了する(作業中コミットの機会を与える) | `orchestrator/worker.go::ExecClaude.RunPrompt`(`:379`〜`:382`) |
| worker プロンプトの構成 | VM モード前置 → プロジェクト方針前置 → `# Goal` → `# Completion criteria` → `# Task: <タイトル>` と説明 → (タスク完了条件が空白のみでなければ)`# This task's completion criteria …` → (完了済み依存タスクの要約があれば)`# Context from prerequisite tasks` → (フィードバックがあれば)`# Feedback from previous attempt …` → 結果スキーマの指示。**任意要素は見出しごと出さない** | `orchestrator/worker.go::Worker.BuildPrompt`(`:168`〜`:201`), `dependencySummaries`(`:204`) |
| 結果スキーマの指示 | 「4区分に当たらない判断は最も妥当な仮定を置いて進み `assumptions` に記録する(上げない。原文は MINOR decisions)」「上げるのは `critical_decision` / `ambiguity` / `policy_branch` / `prerequisite_broken` の4区分だけ」「区切りごとにコミットする」「push・deploy・削除・外部送信を行わない」を**プロンプト定数として毎回付す** | `orchestrator/worker.go::workerResultGuide`(`:94`〜`:110`) |
| 結果 JSON の走査 | 3形式を順に試す: ① stream-json の**末尾から** `"type":"result"` の行を探しその `result` 内を走査 → ② 単一オブジェクトの JSON エンベロープ → ③ 生の出力全体。いずれも**行単位に末尾から**「`{` で始まり `}` で終わり `"done"` を含む」行を探して復号する。**「最終行であること」は要求していない** | `orchestrator/worker.go::ParseWorkerResult`(`:257`), `findWorkerResultJSON`(`:281`), `resultFromStream`(`:301`), `extractFromClaudeEnvelope`(`:322`) |
| 候補行の復号に失敗したときの扱い | **その行を捨てて、さらに前の行の走査を続ける**(1件でも復号できればそれを採る)。3形式すべてで1件も復号できなかったときだけ `no parseable WorkerResult JSON in output`(レビュアは `no parseable ReviewResult JSON in output`)を返す。**部分的に復号できた値を採ることはない** — 復号エラーの行はオブジェクトごと破棄する | `orchestrator/worker.go::findWorkerResultJSON`(`:281`〜`:296`), `orchestrator/review.go::findReviewResultJSON`(`:274`) |
| 型が合わないフィールドがあるとき | その行は**オブジェクト全体が復号失敗**として扱われ、上の規則で捨てられる(`encoding/json` が型不一致でエラーを返すため)。フィールド単位の救済・型変換・警告は無い | `orchestrator/worker.go::findWorkerResultJSON`(`:292`) |
| 未知のフィールドがあるとき | **黙って無視する**。`DisallowUnknownFields` を使っていないため、余分な鍵は復号を妨げない | `orchestrator/worker.go`・`orchestrator/review.go`(`json.Unmarshal` の既定動作) |
| 必須フィールドが欠けているとき | **エラーにならず Go のゼロ値になる**(`done`→`false` / 文字列→`""` / 配列→`nil` / 整数→`0`)。唯一の例外は `done` **という鍵の文字列が行に含まれること**で、これは復号前の行選別の条件なので、`"done"` を含まない行はそもそも候補にならない | `orchestrator/worker.go::findWorkerResultJSON`(`:288`), `orchestrator/state.go::WorkerResult`(`:155`〜`:175`) |
| 結果の型 | `done`(必須。この鍵の存在が判定条件)/ `summary` / `changes` / `assumptions` / `needs_human{reason,question,options}` / `usage{input_tokens,output_tokens}`。**`needs_human.reason` が4区分以外のときは介入を開かない**(`trigger.go::Evaluate` の `switch` が4値だけを見る)。値の検証も警告も行わないため、申告は黙って捨てられる(`docs/issues/015`) | `orchestrator/state.go::WorkerResult`(`:155`〜`:175`) |
| 監査ログへの記録 | `usage` が非 `null` のときだけ `worker_result` 行を追記する(`detail.done` を含む) | `orchestrator/worker.go::Worker.Dispatch`(`:239`〜`:246`) |
| レビュープロンプト | VM モード前置 → プロジェクト方針前置 → `# Task under review` → `# This task's completion criteria (the ONLY scoring basis)` → `# Plan goal (context only — do NOT score against this)` → 出力形式の指示。**他タスクの責務・全体網羅を理由に `critical`/`major` を出さないことを明文で禁じている** | `orchestrator/review.go::Reviewer.buildReviewPrompt`(`:137`), `reviewGuide`(`:55`) |
| レビュー結果の型 | `findings[]{severity, file, message, aspect}` と任意の `usage`。**`severity` が `critical` または `major` のときだけ差し戻す**。`{"findings":[]}` は合格 | `orchestrator/review.go::ReviewResult`(`:19`), `HasSevere`(`:25`) |
| 散文の再整形 | 解釈に失敗したら**1回だけ** haiku・effort `low` で「散文 → JSON」の変換だけを依頼する。worktree もツールも使わず**判定内容を変えない**。成功したら `review_reformat_ok` を監査ログへ記録する | `orchestrator/review.go::Reviewer.reformatToJSON`(`:115`) |
| フォーマットエラーの打ち切り | 連続回数が `review_format_error_limit`(既定 2。**設定値が 0 以下なら 2 として扱う**)に達したら `FormatError` を返して介入へ回す。**worker は再実行しない**。解釈できた判定が1回でも返れば連続回数は 0 に戻る | `orchestrator/review.go::Reviewer.RunGate`(`:179`〜`:207`) |
| レビュー往復の上限 | `max_review_rounds`(既定 10)。**フォーマットエラーによるやり直しは往復数を消費しない** | `orchestrator/review.go::Reviewer.RunGate` |
| 対話モードの指示 | `--append-system-prompt` で渡す。テンプレートは**イメージ同梱**(`/usr/local/share/claude-orchestrator`)。**読めなければ空文字**として扱い、起動は止めない | `orchestrator/mode.go::instructionDir`(`:13`), `Mode.instructionPath`(`:27`), `brainstormingInstr`(`:65`), `interveneInstr`(`:90`) |
| 差し戻しの申し送り | `handoff_note.md` を**読んだ直後に削除する**(1回だけ消費)。内容があればブレインストーミング指示の先頭に前置する | `orchestrator/mode.go::Mode.brainstormingInstr`(`:65`〜`:78`) |
| プロジェクト方針の前置 | リポジトリルートの `ORCHESTRATOR.md` を読み、**空または読めなければ完全な no-op**。読めたら見出しを付けて前置する | `orchestrator/state.go::LoadProjectPolicy`(`:17`) |
| VM モードの前置 | 環境変数 `CLAUDE_DEV_VM` が **`1` に厳密一致**するときだけ前置する | `orchestrator/state.go::VMModePreamble`(`:34`) |
| 起動スクリプト | 対話モードは `sessions/<key>.sh` を書き出して tmux ウィンドウで実行する。**システムプロンプトと初回プロンプトは別ファイルへ原子的に書き、スクリプト内で `$(cat …)` で読む**(数 KB の引数を tmux 経由で渡さないため)。パスと値は単引用符でエスケープする | `orchestrator/mode.go::Mode.WriteLaunchScript`(`:116`), `shellSingleQuote`(`:105`) |
| 制御ファイル | `request` は `execute` / `resume` / `continue_brainstorming` / `abort` / `accept` のみ受理。**それ以外・壊れている・読めない場合は「無い」と同じ扱いにし、いずれもファイルを削除する**(壊れた指示で以後の実行が詰まらないようにする)。読めたら削除してから返す(1回だけ消費) | `orchestrator/handoff.go::Handoff.Consume`(`:19`〜`:39`), `orchestrator/state.go::Control`(`:177`), 定数(`:66`〜`:75`) |
| 古い制御ファイルの破棄 | 再開時(`executing`)と対話を起こす直前に削除する。**plan が正**として扱う | `orchestrator/handoff.go::Handoff.DiscardStale`(`:76`), `orchestrator/controller.go:207`〜`:208` |
| 秘密情報 | 子プロセスの環境から **`SLACK_BOT_TOKEN` を除去**し、`claude` の bin ディレクトリを PATH に足す。worker・レビュア・対話 Claude のすべてに同じ環境を使う。起動スクリプトにも `unset SLACK_BOT_TOKEN` を書く | `orchestrator/claudebin.go::claudeChildEnv`(`:77`), `orchestrator/worker.go::stripEnv`(`:408`), `orchestrator/mode.go::WriteLaunchScript` |

## 設計との差異

| 項目 | 設計(02) | 実装(03) | どちらが正か |
|---|---|---|---|
| 結果 JSON の位置 | worker は**最終行に1個の JSON オブジェクトだけ**を出す | 解釈側は最終行を要求せず、**末尾から順に「`"done"` を含む1行の JSON」を探す**。最終行の後ろに別の出力が続いていても解釈できる | **どちらも正**。契約(worker に課す義務)は 02 のとおりで、実装は受理側を緩めて版差に耐えるようにしている(意図的な寛容さ) |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| worker の出力形式はエージェント CLI の版に依存する | 版が変わると解釈に失敗しうる。`ParseWorkerResult` が3形式を受け付けることで緩和している | なし(閾値の外: 解釈失敗はその試行の失敗として表示される=**その場で気づける**) |
| 指示テンプレートがイメージ同梱のため、更新にはイメージの再取得が要る | プロジェクト側で差し替えられない(`ORCHESTRATOR.md` の前置のみが調整口) | なし(閾値の外: 観測可能な被害が無い。**設計上の割り切り**(`DSN-prompt-01`)) |
| `needs_human.reason` が4区分以外だと介入が開かれない | worker が「人間が必要」と申告しても黙って再試行に回り、申告が失われる | `docs/issues/015-modify-unknown-needs-human-reason-is-dropped.md` |
| プロンプトの全長に上限を設けていない | 依存タスクの要約とフィードバックが積み上がると、CLI 側の入力上限に達しうる(検出も切り詰めもしない) | なし(閾値の外: 上限を超えれば CLI がエラーを返し試行が失敗する=**その場で気づける**) |
| 再整形は**1回だけ・別モデル**で行う | 変換に失敗した場合の理由が残らない(監査ログには成功時の `review_reformat_ok` しか記録されない) | なし(閾値の外: 失敗すればフォーマットエラーとして数えられ、上限で介入へ回る=**気づける**) |
