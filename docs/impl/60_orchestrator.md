---
summary: AI オーケストレーター（Go 製コントローラ）の実装仕様。外部制御ループ・状態ストア・モード切替・worker 並行ディスパッチ・品質ゲート・介入・判断基準・Slack 通知・ビルド配置を定める。設計の意図は docs/06_orchestration.md を参照。
keywords: [ オーケストレーター, Go, 制御ループ, 状態ストア, worker, 介入, 並行実行 ]
---

# 実装仕様: orchestrator/（AI オーケストレーター）

> **この文書の役割**: プロジェクトごとに 1 体立てる AI オーケストレーター（Go 製コントローラ）の実装仕様。設計の意図・全体像は [docs/06_orchestration.md](../06_orchestration.md)、セキュリティ上の位置づけは [docs/03_security.md](../03_security.md) を参照。CLI 連携の正本は [10_cli.md](10_cli.md)、ビルド配置の正本は [40_devcontainer.md](40_devcontainer.md) / [20_makefile.md](20_makefile.md)（いずれも本機能の実装時に更新する）。

## 要件（なぜ必要か）

人間がオーケストレーター（進行管理）を兼ねるとプロジェクト並列度が上げられない。そこで、プロジェクトごとに「壁打ち（検討）」と「実行（自律）」の 2 モードを持つ単一のコントローラを置き、人間は壁打ちと例外対応（介入）だけに関与する。コントローラは**外部制御ループ**としてループを所有し（Stop-hook の力技は採らない）、worker（`claude -p`）へ委譲し、結果を統合・レビューし、介入トリガー該当時のみ人間を呼ぶ。詳細根拠は 06 を参照。

## カバーするコード

```
orchestrator/                      ← 本書が正本（Go コンポーネント）
├── go.mod                         module github.com/quvox/claude-dev-env/orchestrator。docker-proxy 同様の独立モジュールで**外部依存なし（stdlib のみ）**。go.work は用いない。`go.mod` の `go 1.22` は最小言語版で、ビルドは golang:1.24-alpine（docker-proxy と同一慣習）
├── main.go                        エントリ。引数解析（--fresh 等）・再開/新規判定・状態ストア初期化・モードブートストラップ
├── controller.go                  状態機械と run loop（中核）
├── state.go                       状態ストアの読み書きとスキーマ（JSON/JSONL）
├── mode.go                        前景所有とモード切替（対話 claude の exec / ダッシュボード描画）
├── term.go                        端末モード制御（stty による raw/カノニカル切替・復元）
├── claudebin.go                   claude 実行ファイルの解決と子プロセス環境（PATH 補完）
├── handoff.go                     壁打ち↔実行↔介入の受け渡しプロトコル（control.json）
├── worker.go                      worker ディスパッチ（claude -p）・worktree 管理・構造化出力
├── review.go                      品質ゲート（レビュー改訂ループ）
├── trigger.go                     介入トリガー判定
├── slack.go                       Slack 通知（chat.postMessage 直接 POST）
├── dashboard.go                   実行モードのステータス表示（TTY 描画）
├── config.go                      設定・環境変数の読み込みと既定値
├── instructions/                  対話 claude 用テンプレート（イメージに同梱）
│   ├── wallbounce.md              壁打ち脳の instruction
│   └── intervene.md               介入対応の instruction（question.md を前置して起動）
└── *_test.go                      trigger / state / plan 遷移の単体テスト

（本機能の実装時に更新する既存コード。各々の正本は別文書）
claude-dev                         orchestrate サブコマンド追加（→ 10_cli.md）
.devcontainer/Dockerfile.claude    Go ビルドステージ追加＋バイナリ COPY（→ 40_devcontainer.md）
Makefile                           build-orchestrator / テストターゲット（→ 20_makefile.md）
```

イメージへは `claude-orchestrator` という名前のバイナリとして `/usr/local/bin/` に焼き込む（docker-proxy と同方式のマルチステージビルド）。docker-proxy のような独立コンテナではなく、**プロジェクトコンテナ内で実行**する（tmux・`claude` CLI・git worktree を同コンテナ内で扱うため）。

## 全体構成と責務

`claude-orchestrator` は単一プロセス。`main.go` が状態ストアを開き、現在の `Phase` に応じて `controller.go` の run loop に入る。run loop は端末の前景を所有し、モードに応じて前景の中身を差し替える（06 §4）。

| モジュール | 責務 |
|---|---|
| controller | 状態機械（wallbounce/executing/done）と run loop の駆動。介入は executing 内のタスク単位イベントとして処理 |
| state | `/workspace/.orchestrator/` 以下のファイル群の読み書き。監査ログ追記 |
| mode | 壁打ち/介入＝対話 `claude` を子プロセスで exec（stdio を TTY に接続）／実行＝dashboard 描画 |
| handoff | 対話 claude（壁打ち脳）からの遷移要求を `control.json` 経由で受け取る |
| worker | タスクを `claude -p` で worktree 上に実行し、構造化結果を回収 |
| review | 実装 worker と別 worker による独立レビューと改訂ループ |
| trigger | 各ステップ（worker 起動前/実行後）で介入要否を明示的コードで判定 |
| slack | サマリ・介入アラートを Slack へ送る（発信源はコントローラに一本化） |
| dashboard | 実行モードの進捗・worker 状態・直近サマリを TTY に描画 |
| config | trigger 回数・モデル・並行度・最大レビュー周回などの設定 |

### 頭脳の所在（Claude か Go か）

オーケストレーターの「頭脳」（推論・判断）は**すべて Claude** が担う。Go コードは推論しない——ループの所有・順序付け・状態管理・ディスパッチ・機械的なトリガー判定（カウンタ／ハードルール）・Slack・描画という**決定論的な配管**に徹する（06 §3.1 の「L1 推論ループは自作せず Claude から借りる」の具体化）。

- **壁打ち脳** ＝ 対話 `claude`：ゴール分解と計画（`plan.json`）の作成
- **worker 脳** ＝ `claude -p`：各タスクの実装・レビュー
- **適応判断** ＝ 分岐点（レビュー失敗時の再試行/エスカレーション等）でのみ `claude -p` を呼ぶ

したがって「タスクをどう分解するか」「何を実装するか」「指摘が妥当か」はすべて Claude の判断であり、Go は「次にどのタスクを誰へ渡し、いつ止めて人間を呼ぶか」という**段取り**だけを決める。

## 状態ストアのファイル構成

プロジェクト内 `/workspace/.orchestrator/` に置き、永続化・再開・監査を担う。`.gitignore` に `/.orchestrator/` を追加する（成果物ではなく運用状態のため）。壁打ちで固めた**仕様そのもの**は CLAUDE.md の規約に従い通常どおり `docs/`（実装仕様ドキュメント）へ書く。`.orchestrator/` は実行の運用状態を持つ。

```
/workspace/.orchestrator/
├── state.json            現在の Phase・RunID・現在タスク・タイムスタンプ
├── plan.json             タスク計画（壁打ちの成果。タスク配列）
├── control.json          対話 claude → コントローラへの遷移要求（handoff）
├── summary.md            最新の状況サマリ（Slack 送信内容と同一）
├── assumptions.jsonl     置いた仮定（軽微判断）の追記ログ
├── interventions.jsonl   介入イベントと解決の追記ログ
├── audit.jsonl           委譲・結果・トークン使用量の監査ログ
├── intervention/open.json 未解決の要判断キュー（タスク単位・複数同時可。controller が所有）
├── intervention/<id>/    介入 1 件ごとの質問と回答（question.md / answer.md）
├── workers/<taskID>.log  worker ごとの生ログ
└── worktrees/<taskID>/   worker 用 git worktree（git worktree add で作成）
```

### 主要スキーマ

```go
// state.json
type State struct {
    Phase       string `json:"phase"`        // "wallbounce"|"executing"|"done"（intervening は廃止）
    RunID       string `json:"run_id"`
    CurrentTask string `json:"current_task"` // 最後に着手したタスクID（情報用。並行実行のため一意ではない）
    StartedAt   string `json:"started_at"`   // RFC3339（コントローラが刻む）
    UpdatedAt   string `json:"updated_at"`
}

// plan.json
type Plan struct {
    Goal           string `json:"goal"`            // ゴールの要約（完了基準は completion へ）
    Completion     string `json:"completion"`      // プラン全体の完了基準（タスク採点には使わない。§品質ゲート）
    Ready          bool   `json:"ready"`           // 壁打ちで実行可と確定したか
    Tasks          []Task `json:"tasks"`
}
type Task struct {
    ID          string   `json:"id"`
    Title       string   `json:"title"`
    Description string   `json:"description"`     // worker へ渡す自己完結の指示
    Completion  string   `json:"completion"`      // **必須**。このタスク単体で判定可能な完了基準（担当対象・唯一の成果物パス・満たすべき構造・責務外の明示）。レビューはこれだけで採点する（§品質ゲート）。空ならプラン検証で弾く
    Deps        []string `json:"deps"`            // 先行タスクID
    Status      string   `json:"status"`          // pending|running|review|revise|waiting_human|blocked|done|failed
    Irreversible bool    `json:"irreversible,omitempty"` // トリガー1: 計画段階で後戻り不可操作を含むと印付け
    IrrevApproved bool   `json:"irrev_approved,omitempty"` // 介入で承認済み。pre-dispatch trigger1 を再発火させない
    Attempts    int      `json:"attempts"`        // 実装ディスパッチ回数。revise では増やさない（§試行回数とエスカレーション）
    Worktree    string   `json:"worktree"`        // 相対パス
    SessionID   string   `json:"session_id,omitempty"`   // 現 Attempt の claude -p セッション ID。中断後の同一 Attempt 再開は --resume に使う（§worker ディスパッチ）。新しい Attempt（別アプローチ）では空に戻す
    ResumeSession bool   `json:"resume_session,omitempty"` // 中断で pending へ戻した同一 Attempt を --resume で継続する印。NormalizeForResume/resetToPending が立て、次ディスパッチで消費（Attempts は増やさない）
    OpenInterventionID string `json:"open_intervention_id,omitempty"` // waiting_human の間だけ非空。対応する介入キューエントリの ID
    ReviewFormatErrors int   `json:"review_format_errors,omitempty"` // 連続したレビュー結果のパース不能回数（§品質ゲート 8.2）。内容不合格ではリセット
    Result      *WorkerResult `json:"result,omitempty"`
}

// worker（claude -p）の構造化出力（worker.go が要求するスキーマ）
type WorkerResult struct {
    Done       bool       `json:"done"`           // タスク完遂を主張するか
    Summary    string     `json:"summary"`
    Changes    []string   `json:"changes"`        // 変更ファイル
    NeedsHuman *NeedsHuman `json:"needs_human,omitempty"` // エスカレーション要求
    Assumptions []string  `json:"assumptions,omitempty"` // 置いた軽微な仮定（controller が assumptions.jsonl へ追記）
    Usage      *Usage     `json:"usage,omitempty"`
}
type NeedsHuman struct {
    Reason  string   `json:"reason"`              // "critical_decision"|"ambiguity"|"policy_branch"|"prerequisite_broken"（トリガー1/2/4/5）。trigger3 は controller 検出で NeedsHuman を使わない
    Question string  `json:"question"`
    Options []string `json:"options,omitempty"`
}

// control.json（対話 claude → コントローラ）
type Control struct {
    Request        string `json:"request"`        // "execute"|"resume"|"continue_wallbounce"|"abort"
    InterventionID string `json:"intervention_id,omitempty"` // 任意。介入対応で 1 件のみ解決した場合のヒント。複数解決時は controller が answer.md の有無で再照合する
    TS             string `json:"ts"`
}

// intervention/open.json（介入キュー＝未解決の要判断の一覧。controller が所有）
type OpenInterventions struct {
    Items []OpenIntervention `json:"items"`
}
type OpenIntervention struct {
    ID            string `json:"id"`             // iv-...
    TaskID        string `json:"task_id"`
    TriggerReason string `json:"trigger_reason"` // irreversible|ambiguity|stuck|policy_branch|prerequisite|review_gate_defect（trigger.go の reason 文字列に一致。worker の NeedsHuman.Reason とは別レイヤで、critical_decision→irreversible・prerequisite_broken→prerequisite に対応する）
    OpenedAt      string `json:"opened_at"`      // RFC3339
}

// assumptions.jsonl / interventions.jsonl / audit.jsonl の各行（1 行 1 レコード）
type Assumption   struct { TaskID, Description, Rationale, TS string }
type Intervention struct { ID, TaskID, TriggerReason, Question, Answer, TS string }
type AuditEntry   struct { TS, Event, TaskID string; Detail map[string]any; Usage *Usage }
```

**介入キュー（タスク単位・複数同時可）**: 旧設計の「単一の open_intervention サイドカー＋最上位 `intervening` 状態」を廃止し、未解決の要判断を `intervention/open.json` の配列で持つ。あるタスクが要判断に該当したら controller は (1) そのタスクを `waiting_human` にして `OpenInterventionID` を埋め、(2) `intervention/<id>/question.md` を書き、(3) `open.json` にエントリを追加、(4) Slack 通知（件数）を出す。`waiting_human` のタスクは worker スロットを占有せず、**他タスクの実行は継続**する。人間が `[i]` で対応すると、対話 Claude に `open.json` の全件を seed し、回答ごとに `intervention/<id>/answer.md` と該当タスクが更新される。controller は回答済み（answer.md あり）のエントリを `open.json` から外し、`interventions.jsonl` へ確定記録し、当該タスクを再ディスパッチ可能（`pending`）へ戻す。`review_gate_defect` はレビューのフォーマット不具合起因の要判断（§品質ゲート 8.2）。

**Task.Status の遷移**：`pending`（依存解決待ちを含む）→ `running`（controller が worker ディスパッチ時に設定）→ `review` →（重大指摘）`revise` → 解消で `done`。介入トリガーに該当したタスクは `waiting_human` へ移り、その worker だけが停止して**介入キューに積まれる**（他タスクは継続。§介入トリガー判定／§並行性・再開・エラー処理）。人間の回答後、controller が `waiting_human`→`pending` に戻して再ディスパッチする（trigger1 の承認なら `IrrevApproved` を立てて再発火を防ぐ）。先行タスクが `failed`/`blocked` で起動不能なものは `MarkBlockedByFailedDeps` が `blocked` にする。`blocked` は**その run では終端**（依存が満たせない以上そのまま）。`done`/`failed`/`blocked` のいずれかになった全タスクは `AllSettled`＝これ以上進めないと判定されるが、**未解決の `waiting_human` が 1 件でも残る間は run を終了しない**（人間の回答を待ち続ける）。判断待ちが無く全タスクが settled なら、run は `verifyCompletion` で「未完了タスクあり」または完了として `done` へ遷移して終了する。中断後の再開や依存タスクの修正で状況が変われば、次回 run で再評価される。

## 制御フロー（状態機械と run loop）

`controller.go` の状態遷移は 06 §2.2 に対応する。

```
[wallbounce] ──control.execute──▶ [executing] ──全タスク settled & 要判断 0──▶ [done]
                                    │  ▲
              タスクが要判断に該当     │  │ 人間が [i] で回答 → 該当タスクを再ディスパッチ
                                    ▼  │
              そのタスクのみ waiting_human（介入キューへ）。他タスクは executing 内で継続
（abort は wallbounce／介入対応中いずれからも done へ）

**最上位状態としての `intervening` は廃止**した（06 §2.2）。介入は `executing` の内部イベントとして、タスク単位で処理する。実行モードを離脱しないため、判断待ち以外の worker は止まらない。
```

run loop の擬似フロー：

0. 起動時、`main.go` は `--workspace` を **`filepath.Abs` で絶対パスに正規化**する。Store のパス（worktree パス含む）はこれに基づき、`git` は `cmd.Dir=workspace` で実行されるため、相対 workspace だと worktree パスが二重ネスト（`…/ws/ws/.orchestrator/worktrees/…`）して `git worktree add` が exit 128 → 「既に checked out」で stuck 化する。本番の `/workspace`（絶対）では顕在化しないが、任意パス起動の堅牢性として必須（[docs/reviews/2026-07-01_orchestrator-e2e.md](../reviews/2026-07-01_orchestrator-e2e.md)）。
1. 続いて `main.go` が `state.json` を読んで**再開か新規開始かを判定**する（§ 並行性・再開・エラー処理の「再開と新規開始の判定」）：中断された run（Phase=`executing`）のみ再開し、それ以外（不在／`done`／未知 Phase）または `--fresh` 指定時は実行状態を破棄して新規開始する。その後 `controller.go` の run loop は、新規開始なら Phase=wallbounce（RunID 採番）、再開なら永続化済みの Phase（executing）から動く。再開（executing）時は `plan.json`・`intervention/open.json` を正本とし、残存する `control.json` は無視して消す。
2. **wallbounce**：`mode.RunInteractive()` で対話 `claude` を前景に exec し、終了を待つ。終了後 `control.json` を読む：
   - `execute` かつ `plan.Ready==true` → executing へ。ただし遷移前に**プラン検証（lint）**を行い、各タスクに `completion` が無ければ executing へ進めず壁打ちへ差し戻す（§品質ゲート 8.1）
   - `continue_wallbounce` / Ready 未確定 → コントローラが端末で「続ける/実行/終了」を確認（『続ける』→ Phase=wallbounce のまま `mode.RunInteractive()` 再実行／『実行』→ executing／『終了』→ done）
   - `abort` → done
3. **executing（スケジューラ・ループ）**：`dashboard` を前景に出し、ループを所有し続ける。1 tick ごとに：
   - 依存解決済みの `pending` タスクを並行度 `max_workers` まで起動。各タスクは pipeline：`worker 実装 → review → (重大指摘あり) revise → … → done`。各ステップで `trigger.Evaluate()`（条件1は worker 起動前、条件2/4/5 は実行後）。
   - **トリガー発火はそのタスクだけに作用する**：当該 worker を停止（停止前に中間コミット猶予）、タスクを `waiting_human` にし `intervention/open.json` へ積む。**他 worker・ループは止めない**（旧 `runCancel()` による全停止は廃止）。
   - `[i]` キー（または `--resolve`）で人間が要判断に対応する時だけ、ループを止めずに（背景 worker は走らせたまま）対話 `claude` を前景に exec し、`open.json` 全件を seed。戻ったら回答済みエントリを解決し該当タスクを `pending` へ戻す。
   - `[p]`/`[q]` キー、SIGINT/SIGTERM の扱いは §モード切替・§並行性で定義。
   - **終了判定**：未解決の `waiting_human`／`open.json` エントリが 1 件でも残る間は run を終了しない。判断待ちが 0 かつ全タスク settled になったら完了検証（5）へ。
4. **介入対応（executing の内部イベント。最上位状態ではない）**：該当タスクを `waiting_human` にした時点で `intervention/<id>/question.md` を書き、`open.json` に積み、Slack で件数アラート。人間が `[i]` を押すまで対話 `claude` は起動しない（オンデマンド。06 §6.2／6.3）。`[i]` 時は対話 `claude`（文脈 seed 済、複数件はまとめて提示）を前景に exec。回答後 `control.json` を読む：`resume` なら answer.md のあるエントリを `interventions.jsonl` へ確定・`open.json` から除去・該当タスクを `pending` へ戻して executing 継続、`abort` なら done へ遷移。
5. 判断待ち 0 かつ全タスク settled → 完了検証 → **done**。完了時、`plan.completion`（自然言語の完了基準）が非空なら `claude -p` で**助言的な完了検証**を行う（`checkCompletion`）：完了基準と各タスクの結果サマリを渡し `{"satisfied":bool,"missing":string}` を読み取る。これは**ブロックしない助言**で、エラー・空・解析不能時は満たしたものとして扱い（`parseCompletionVerdict` が `(true,"")` を返す）run を止めない。未充足なら Slack 通知に不足点を添えて人間の最終確認を促す。未充足時の**不足分の自動タスク化**は意図的に範囲外（人間が判断）。`failed`/`blocked` を含み全 `done` でない場合は「未完了タスクあり」で done。最終サマリを Slack 送信。

## モード切替の実装（前景所有・子プロセス）

`mode.go` がコントローラの「前景の差し替え」を担う（06 §4.2）。

> **claude の実行ファイル解決（`claudebin.go`）**：オーケストレーターは `claude-dev orchestrate` から tmux ウィンドウの**非対話シェル（`zsh -c`）**で起動される。Claude Code のネイティブ導入先 `~/.local/bin` は**対話シェルの rc（`.zshrc`）でしか PATH に入らない**ため、非対話起動では `claude` が PATH に無く、素朴な `exec.Command("claude", …)` は「executable file not found」で失敗して壁打ち・介入・worker・レビュアの**すべてが動かない**。これを避けるため、対話モードと worker/レビュアの双方で `claudePath()`（`exec.LookPath`→無ければ `$HOME/.local/bin/claude` にフォールバック）で絶対パス解決し、子プロセスの環境は `claudeChildEnv()`（`SLACK_BOT_TOKEN` を除去しつつ claude の bin ディレクトリを PATH に補完）で渡す。

- **対話モード（壁打ち/介入）** `RunInteractive(ctx)`：`exec.Command(claudePath(), args...)` を生成し、`Stdin/Stdout/Stderr = os.Stdin/os.Stdout/os.Stderr`（同一 TTY を共有）。`cmd.Run()` で**子の終了までブロック**する。これによりコントローラのループは自然に停止し、壁打ち/介入中は実行が止まる。**子の対話 `claude`（全画面 TUI）は共有 TTY を非カノニカル（raw）モードに切り替え、終了時にカノニカルへ戻さない**。コントローラは同じ TTY を使うため、`cmd.Run()` 復帰直後に `ttyRestoreSane()`（`term.go`）で**カノニカルな健全状態へ復元**する。これを怠ると、以降の行バッファ読み取り（`terminalConfirm` の確認入力、ダッシュボードのキー入力）が、raw モードでは Enter が `\n` ではなく `\r` を送るため `\n` を待ち続けて**永久にブロック**する。
  - 壁打ち：引数なしの対話起動＋オーケストレーター脳の instruction を投入（§ instruction 注入）。
  - 介入対応（`[i]` 押下時のみ）：`--resume` は使わず**フレッシュ起動**し、`intervention/open.json` の全件と各 `intervention/<id>/question.md` を初期プロンプト/コンテキストとして渡す（06 §6.2 ノブ1=フレッシュ再構成、ノブ3=常駐セッションを使わず controller が毎回新規 exec）。**旧「ノブ2=先に起動して待たせる」は廃止**——トリガー発火で自動起動して全実行をブロックする旧挙動をやめ、人間が `[i]` を押した時にオンデマンド起動する（06 §6.3）。複数件あればまとめて提示し、1 件ずつ回答させる。コントローラは `cmd.Run()` でその終了までブロックするが、**背景の worker 子プロセスは前景占有中も走り続ける**。
- **実行モード** `RunDashboard(ctx)`：`dashboard.go` が ANSI で TTY を再描画しつつ、`worker.go` の goroutine 群を監督する。各タスク行は `待機中/実行中/レビュー中/修正中/要判断/完了/失敗/ブロック` のラベルと、実行中タスクの経過時間・試行回数を表示する（タスクが running になった時点で `syncDashboard` を呼ぶため「ずっと待機中に見える」ことはない）。`要判断`（`waiting_human`）は ⏸ で示し、要判断キューの件数も表示する。キー操作：
  - **VM 資源逼迫バナー（VM モード時）**：`render()` は描画のたびに `vm-healthd` の health ファイル（`$HOME/.claude-dev-vm/health`。正本 [80_vm-mode.md](80_vm-mode.md) §7.2）をベストエフォートで読み、`STATE=WARN` かつ `TS` が新しい（既定 120 秒以内）ときだけ画面上部へ赤の警告バナー（`⚠ VM資源逼迫（QEMU CPU …% / 上限 …%）…`）を出す。ファイルが無い／VM モードでない／鮮度切れ・パース失敗時は何も出さない（読取専用・エラーは無視）。**controller ループは非改変**で、追加は `dashboard.go`（`render` と補助 `readVMHealthBanner`）に限定する。
  - **`d`（worker 出力）**：詳細表示をトグルする。ON の間は実行中 worker の出力ログ（`workers/<taskID>.log`）の末尾をライブ表示する（`dashboard.go` の `renderDetail`/`tailFile`）。worker は出力をログへ**ストリーム書き込み**する（§ worker ディスパッチ）ので、完了を待たずに進捗が見える。
  - **`p`（一時停止）**：新規スケジューリングを止める／再開するトグル（実行中 worker は走り続ける）。
  - **`i`（介入対応）**：`intervention/open.json` に未解決の要判断がある時だけ意味を持つ。対話 `claude` を前景に exec し、溜まっている要判断をまとめて回答させる（上記「介入対応」）。**他 worker は前景占有中も走り続ける**。回答済みタスクは executing で再ディスパッチされる。
  - **`q`（中断）/ Ctrl-C**：実行中 worker に**中間コミットの猶予**（`worker_grace_seconds`、既定 10 秒）を与えて停止し、**状態を `executing` のまま保存して終了する（done にしない）**。次回 `claude-dev orchestrate` は中断点から再開する（`controller.go` は `errSuspended` を返し `Run` がクリーン終了＝終了コード 0。`log.Fatal` しない。worktree のコミットと `session_id` は保全）。SIGINT/SIGTERM も同一経路で処理し、`[q]` と等価のクリーン中断とする。中断は破壊的ではない。
  
  キー読み取り（`dashboard.go` の `readKeys`）は **`term.go` の `rawKeyMode()` で TTY を自前で非カノニカル・no-echo（`stty -icanon -echo min 0 time 1`）に設定**し、1 バイトずつ読む（Enter 不要・即時反応）。`VMIN=0/VTIME=1` により無入力時の `os.Stdin.Read` は約 0.1 秒ごとに `(0, io.EOF)` を返すので、`ctx` キャンセルを取りこぼさず、stdin にブロックしたまま残る goroutine も生じない。終了時は `ttyRestoreSane()` でカノニカルへ復元する。`isig` は無効化しないため Ctrl-C は引き続きコントローラのシグナルハンドラへ届く。`main.go` は経路によらず（正常終了・エラー・シグナル）`defer ttyRestoreSane()` で最終的に端末を健全状態へ戻す。これらの端末制御は `stty` 呼び出しのみで実現し、外部 Go モジュールを増やさない（stdlib のみ方針を維持）。

### instruction 注入

対話モードの `claude` は「オーケストレーター脳」として振る舞う必要がある。起動時に専用 instruction（役割・介入トリガー・サマリ方針・`control.json`/`plan.json` への書き出し規約）を与える。instruction はイメージ同梱のテンプレート（例 `/usr/local/share/claude-orchestrator/wallbounce.md`）を `mode.go` が `claude` の初期コンテキストへ渡す。テンプレートは付録ドキュメント（06 §13 の「リードエージェント指示書テンプレート」相当）として別途管理する。

### 判断基準（介入トリガー・仮定方針・サマリ方針）の所在

オーケストレーターに与える**判断基準は、プロジェクトの `CLAUDE.md` には置かない**。次に明文化する（環境リポジトリでバージョン管理し、イメージに同梱）：

- **共通の定性ポリシー**：`orchestrator/instructions/wallbounce.md`（壁打ち脳）・`intervene.md`（介入脳）に、介入トリガー 5 条件・「軽微判断は最も妥当な仮定を置いて進め記録する」方針・状況サマリ定型・**開発フロー**（要件/設計/ユースケース → 整合性確認 → 実装仕様 → 実装 → ユースケース動作確認 → レビュー〔結果は `docs/reviews/`〕。CLAUDE.md と整合）を記述する。`plan.json` はこの開発フローを反映してタスク化する。**各タスクには `completion`（そのタスク単体で判定可能な完了基準。担当対象・唯一の成果物パス・満たすべき構造・責務外の明示）を必ず付与する**よう壁打ち脳に指示する（§品質ゲート 8.1。未設定はプラン検証で弾く）。
- **worker 向けの判断ルール**：`worker.go` の `workerResultGuide`（worker プロンプトに付加）に、(a)「軽微は仮定して `assumptions` に記録／重大のみ `needs_human` でエスカレーション」、(b)**意味のある区切りで worktree に逐次コミットする**（中断時の作業保全。§worker ディスパッチ 5）、(c) 後戻り不可操作（push/deploy/削除/外部送信）は行わずエスカレーションする、を worker 視点で記述する。
- **定量しきい値**（`stuck_limit` 等）は config（§設定）で調整する。
- **プロジェクト固有の判断基準**（任意）：プロジェクトルートの `ORCHESTRATOR.md`（**コミット対象**。gitignore される `.orchestrator/` 運用状態とは別）。存在すれば、壁打ち/介入の対話 instruction と worker/reviewer プロンプトの先頭に `mode.go`／`worker.go`／`review.go` が prepend する。CLAUDE.md とは独立で、CLAUDE.md には判断基準を書かない。
- **VM モード対応（正本 [80_vm-mode.md](80_vm-mode.md) / [docs/08_vm-mode.md](../08_vm-mode.md)）**：
  - **VM_DEV.md 前置（発見導線2）**：VM モード（環境変数 `CLAUDE_DEV_VM=1`）のとき、`LoadProjectPolicy`（`ORCHESTRATOR.md` 前置）と同じ仕組みで、壁打ち/介入 instruction と worker/reviewer プロンプトの先頭に **VM モードの短いポインタ**（「docker はゲスト VM daemon（`DOCKER_HOST` 設定済）を指す・bind mount の source は `/workspace` 配下のみ・詳細は `/workspace/VM_DEV.md`」）を prepend する。実装は `state.go` の `VMModePreamble()`（`CLAUDE_DEV_VM=1` のとき定型文を返し、それ以外は空）を `mode.go`／`worker.go`／`review.go` の各プロンプト先頭で `LoadProjectPolicy` と並べて前置。CLAUDE.md には触れない。
  - **ゲスト `DOCKER_HOST` の継承**：orchestrator は `claude-dev orchestrate` が source した `/etc/claude-dev/vm.env` によりゲストの `DOCKER_HOST` を持ち、worker は `claudeChildEnv()`（`os.Environ()` 由来）でそれを継ぐ。よって Go 側の追加実装は不要（`DOCKER_HOST` を明示操作しない）。

CLAUDE.md に置かない理由：CLAUDE.md は worker を含む Claude Code 全般への指示であり、オーケストレーターのガバナンス（いつ人間を呼ぶか）を混在させると worker にも波及して責務が濁るため。オーケストレーター脳は自分の instruction（＋将来のプロジェクト固有 policy）だけを読む。

## 壁打ち/介入の受け渡しプロトコル（handoff）

対話 `claude` は前景の子プロセスであり、コントローラと**ファイル経由**で受け渡す（プロセス間でメモリ共有しない）。

- 壁打ち脳は決定を `plan.json` に書き、実行可と判断したら `plan.Ready=true` にし、`control.json` に `{"request":"execute"}` を書いてからセッションを終了する（人間が `/exit`、または instruction が終了を促す）。
- 介入時は、対話脳が回答を `intervention/<id>/answer.md` と該当タスクへ反映し、`control.json` に `{"request":"resume","intervention_id":"<id>"}` を書いて終了する。
- 書き込みは原子的に行う（一時ファイル → rename）。コントローラは前景を取り戻した直後に `control.json` を読み、**消費後に `controller.go` が削除する**。`control.json` が無い/不正な場合はコントローラが端末で明示的に確認する（プロンプト依存にしない安全側）。再開時（Phase=executing）は `plan.json` を正本とし、残存する `control.json` は無視して消す（壁打ち直後のクラッシュも `plan.Ready` と `plan.json` の整合だけで判断する）。

## worker ディスパッチ

`worker.go` がタスク 1 件を `claude -p` で実行する。

1. **worktree 準備**：`git worktree add .orchestrator/worktrees/<taskID> -b orch/<taskID>`（ベースは現在の作業ブランチ）。タスクはこの worktree を CWD として走る（ファイル競合防止、06 §4.4）。ディレクトリが既存なら再利用、ディレクトリは無いがブランチ `orch/<taskID>` が残っている場合は `git worktree add <path> orch/<taskID>`（`-b` なし）で**再接続**する（`-b` 重複エラーで再試行ループに陥らない）。
2. **プロンプト構築**：`Task.Description` ＋ 状態ストアから必要文脈（関連 docs/実装仕様の該当箇所、先行タスクの結果サマリ、制約・既決事項）を**過不足なく**注入（NFR-2）。巨大リポジトリ全体は渡さない。
3. **起動**：`claude -p "<prompt>" --output-format stream-json --verbose [--model <m>] --permission-mode <mode> [--session-id <new>|--resume <saved>]`、CWD=worktree。出力は `io.MultiWriter` でバッファと `workers/<taskID>.log` へ**ライブ tee**する。`stream-json`（`-p` では `--verbose` が必須）はイベントを 1 行ずつ逐次出力するため、ログが実行中に伸び、ダッシュボードの `[d]` 詳細表示が worker の進捗をリアルタイムに見せられる（`--output-format json` だと完了まで何も出ずログが空に見える）。**`--permission-mode` は明示的に渡す**（既定 `bypassPermissions`、`config.worker_permission_mode` で変更可・空文字で無指定）。ヘッドレス worker は権限プロンプトに答える人間がいないため、非対話モードを明示しないと全 Write/Bash が拒否され worker が無言で何もしなくなる。bypass の安全性はコンテナ隔離・FW・proxy・instruction 制約で担保（06 §10）。`claude` 実行ファイルは `claudePath()` で解決（PATH→`$HOME/.local/bin/claude`）し、PATH を補完した環境（`claudeChildEnv()`）で起動する。レビュア（`claude -p`）も同じ runner を共有し同モードで起動する（`git diff` 実行に Bash 権限が要るため）。
   - **セッション継続（中断からの再開で白紙やり直しを防ぐ）**：worker 起動時、`stream-json` の初期 `system`/`init` イベントに含まれる `session_id` を捕捉し `Task.SessionID` に保存する（新規 Attempt は `--session-id <uuid>` で採番してもよい）。中断後の再開で**同一 Attempt を続行**する場合（`Task.SessionID` が非空かつ Attempts を増やさない再開）は `--resume <session-id>` を付けて起動し、worker は前回の続きから作業する。**別アプローチでの再試行（新しい Attempt）に入るときは `Task.SessionID` を空に戻し**、新規セッションで始める（前回の失敗文脈は feedback として別途プロンプトへ渡す）。`--resume` が失敗した場合（セッション喪失等）は新規セッションへフォールバックし audit へ記録する。
4. **結果回収**：stdout の JSON を `WorkerResult` にデコード。worker・レビュア双方 `stream-json` で起動するため、`ParseWorkerResult`／`ParseReviewResult` はいずれも **stream-json の最終 result イベント → single envelope → bare の順**で内側 JSON を取り出す（レビュア側の stream-json 非対応は実機検証で発見・修正済み。[docs/reviews/2026-07-01_orchestrator-e2e.md](../reviews/2026-07-01_orchestrator-e2e.md)）。`Usage` を `audit.jsonl` に記録。`NeedsHuman` が非 nil なら trigger へ（人間に直接問わせない＝06 §7）。`NeedsHuman.Options` は worker が提示する**候補データ**であり、worker 自身がレンダリングするのではなく、controller が介入対応の対話モードで select→submit として人間に提示する（06 §7 と矛盾しない）。`WorkerResult.Assumptions`（軽微な仮定）は controller が `assumptions.jsonl` に追記する。
5. **取り込み**：worker は worktree 内で実装し、**意味のある区切りで逐次コミット**したうえで最終的にもコミットする（中間コミット方針は `workerResultGuide` に明記。中断されてもコミット済み分が保全される）。レビュー合格後、**controller** が worktree のコミットを作業ブランチへ統合する（`merge`/`rebase` は `config.merge_strategy`。git 操作は orchestrator ユーザが実行し、worker の bypass とは独立）。コンフリクト・クラッシュ・タイムアウトは当該 Attempt の失敗として次の Attempt へ（§試行回数とエスカレーション）。

`claude -p` は worker のみが用いる。worker は Slack を送らず、結果は stdout でコントローラへ返す（06 §9）。technical control として worker プロセスには `SLACK_BOT_TOKEN` を渡さない。また worker には後戻りできない操作（push/deploy/削除/外部送信）を実行させず、必要なら `WorkerResult.NeedsHuman` でエスカレーションさせる。リモートへの push やデプロイ等の取り返しのつかない操作は controller のみが、介入で承認された場合に行う（トリガー1）。

## 品質ゲート（レビュー改訂ループ）

`review.go`：

1. 実装 worker と**別の** worker をレビュアとして起動（フェーズ 1 は同じ Claude、フェーズ 2 で Codex＝別ベンダー。06 §8/§11）。
2. レビュー入力は worktree の diff。観点を分ける：①要件充足・動作 ②セキュリティ・エラー処理・保守性（FR-9）。両観点のチェックリストを **1 回のレビュー呼び出し**に与え、findings を観点タグ付きで返させる（観点ごとに別呼び出しはしない）。
3. **採点基準は当該タスクの `Task.Completion` のみ**（プラン全体のゴールや兄弟タスクの責務で減点しない）。`Task.Completion` 空時に `Plan.Completion`/`Plan.Goal` へフォールバックする旧挙動は**禁止**（プラン検証で空タスクを弾く前提。06 §8.1）。レビュアプロンプトには「全体網羅・他観点・統合・後始末は別タスクの担当であり、本タスクの採点に含めない」旨を明記する。
4. **レビュア出力は構造化出力（スキーマ強制）で受ける**（findings[]：`severity`(`critical`|`major`|`minor`), file, message, aspect）。散文中の JSON を正規表現で拾う方式は補助フォールバックに留める。06 §8.2。
5. **重大** severity（`critical`/`major`）が残る間は実装 worker へ差し戻し（revise）、`max_review_rounds`（既定 3）まで反復する（この間 `Attempts` は増やさない。§試行回数とエスカレーション）。
6. **フォーマット違反（パース不能）と内容不合格を区別する**（06 §8.2/§8.3）：
   - パース不能なら `Task.ReviewFormatErrors++`。**実装は完了しているので worker を再ディスパッチ（実作業のやり直し）せず、レビュー工程のみ再試行**する。
   - `ReviewFormatErrors` が閾値（`review_format_error_limit`、既定 2）に達したら、それ以上リトライしても解消しない蓋然性が高いため、`review_gate_defect` 理由で**介入キューへ**（trigger3 とは別系統。実作業のやり直しはしない）。介入 seed に「成果物が `Task.Completion` を満たすかの一次確認」を添える（06 §8.2）。
   - 内容として不合格（パースできた severe findings）なら `ReviewFormatErrors` をリセットし、5 の revise を続ける。
7. 解消すれば `done`。`max_review_rounds` 上限到達でも重大指摘が残れば trigger 3（行き詰まり）として介入キューへ（§試行回数とエスカレーション）。

## 試行回数とエスカレーション（Attempts / stuck_limit / max_review_rounds）

実装者が一意に解釈できるよう用語を確定する。

- **1 試行（Attempt）** = worker への 1 回の実装ディスパッチ（初回実装／別アプローチでの再実装／クラッシュ・タイムアウト後の再実装のいずれか）。`Task.Attempts` はこの単位でのみ増やす（インクリメント主体は controller）。
- **レビュー差し戻し（revise）** は同一 Attempt 内のループで、`max_review_rounds`（既定 3）が上限。**revise では `Attempts` を増やさない**。
- **trigger 3（行き詰まり）** は次のいずれかで発火する：(a) `Attempts >= stuck_limit`（既定 3）、(b) ある Attempt 内で revise が `max_review_rounds` に達しても重大指摘が残る。
- **別アプローチ**：ある Attempt が失敗（revise で重大指摘を解消できない／worker が `done` を出せない／クラッシュ）したら、controller は直前の失敗情報（worktree diff・レビュー指摘・worker ログの要約）を付して worker を**再ディスパッチ**し、異なる方針を促す。これが次の Attempt。最大 `stuck_limit` 回まで繰り返し、なお未解決なら trigger 3。

`max_review_rounds`（Attempt 内のレビュー反復）と `stuck_limit`（Attempt 総数）は独立した上限であり、いずれかに達した時点で trigger 3 とする。

## 介入トリガー判定

`trigger.go` の `Evaluate(ctx TriggerContext) (fire bool, reason string)` を各ステップで呼ぶ。`TriggerContext` は判定に要する `Task`・`Plan`・`State`・直前の `WorkerResult`・`Config` を保持する。条件 1（後戻り不可操作の事前審査）は worker 起動**前**に、条件 2/4/5 は worker 実行**後**に評価する。06 §6.1 に対応：

| # | 条件 | 実装上の検出 |
|---|---|---|
| 1 | 後戻りできない重大判断 | 計画段階で当該操作（push/deploy/削除/外部送信）を含むと印付け（`Irreversible`）されたタスクは worker 起動**前**に fire。介入で承認後は `IrrevApproved` を立てて再発火させない。worker 自身は当該操作を行わず `NeedsHuman`(`critical_decision`) でエスカレーションする（§worker ディスパッチ） |
| 2 | 要件の曖昧さ | worker が `NeedsHuman`(`ambiguity`) を返した場合 |
| 3 | 行き詰まり | `Attempts >= stuck_limit`、または Attempt 内で `max_review_rounds` 到達後も重大指摘が残る（§試行回数とエスカレーション） |
| 4 | 方針の重大な分岐 | worker が `NeedsHuman`(`policy_branch`) を返す（計画上のマークによる検出はフェーズ2以降の拡張。v1 は未実装） |
| 5 | 前提の崩れ | worker が `NeedsHuman`(`prerequisite_broken`) で報告（依存結果との矛盾の自動検出はフェーズ2以降の拡張。v1 は未実装） |

上記以外の軽微判断は fire せず、worker が置いた仮定を `assumptions.jsonl` に記録して続行する。

## Slack 通知

`slack.go`：`net/http` で `https://slack.com/api/chat.postMessage` に `Authorization: Bearer $SLACK_BOT_TOKEN` で JSON POST。`SLACK_BOT_TOKEN` 未設定なら no-op、送信失敗は握りつぶしてログのみ（既存 `sendslackmsg.sh` と同じ堅牢性方針）。`SLACK_CHANNEL`（既定は既存と同値）を宛先にする。これらの環境変数はホスト `~/.claude/settings.json` の `env` から entrypoint 経由でコンテナへ渡る（[30_scripts.md](30_scripts.md) §連携）。

送信契機：(a) 実行モードでサマリ更新時（`summary.md` 更新と同時）、(b) **タスクが要判断に該当し介入キューへ積まれた時**（要判断アラート「要判断 N 件。巡回時に attach し `[i]` で対応を」。run は止まらない旨を含意）、(c) 完了時。**発信源はコントローラに一本化**し、worker・壁打ち中の対話 claude は送らない（06 §9）。worker・壁打ち/介入の対話 claude いずれにも `SLACK_BOT_TOKEN` を渡さないことで技術的に封じる（加えて対話 claude は instruction でも抑止）。トークンは controller のみが保持して送信する。

## ステータス・ダッシュボード

`dashboard.go` は 06 §5.2 ② の画面を描画する：goal、各タスクの `[i/n] worker X (claude): 状態ラベル 経過時間 (試行N)`（`waiting_human` は ⏸ 要判断ラベル）、直近サマリ、仮定カウント・**未解決の要判断件数（`intervention/open.json`）**・実行中数、キーヒント（`[d]`/`[p]`/`[i]`/`[q]`）。worker の実行内容は `[d]` 詳細表示でログ末尾をライブ確認できる（別ウィンドウ＝旧 Config B は廃止し、`[d]` に一本化した）。`[i]` は未解決の要判断がある時のみ有効。単一ウィンドウ構成（Config A）のみ。

## 設定（config / env）

`config.go` は設定を次の優先順位でマージする（下ほど強い）：**組み込み既定 → ユーザ全体 `~/.config/claude-dev.yaml` の `orchestrator:` セクション**（CLI と同ファイル、[10_cli.md](10_cli.md)）**→ プロジェクト `/workspace/.orchestrator/config.yaml`**。すべて任意で、無ければ既定値を使う。プロジェクト単位で並行度やモデルを変えられる。設定ファイルは `key: value` 形式の素朴な YAML サブセットで、外部ライブラリを使わず `config.go` 内の小さなパーサで読む（stdlib のみ）。

```yaml
# /workspace/.orchestrator/config.yaml（例）
max_workers: 5
worker_permission_mode: bypassPermissions
stuck_limit: 3
max_review_rounds: 3
review_format_error_limit: 2
worker_grace_seconds: 10
worker_model: sonnet
reviewer_vendor: claude      # フェーズ 2 で codex
merge_strategy: merge
```

| キー | 既定 | 用途 |
|---|---|---|
| `max_workers` | 5 | 並行 worker 数（コスト・競合の上限） |
| `stuck_limit` | 3 | トリガー 3 の規定回数（06 未決事項の解決） |
| `max_review_rounds` | 3 | レビュー改訂の最大周回 |
| `review_format_error_limit` | 2 | レビュー結果のパース不能が連続したら `review_gate_defect` 介入へ（実作業はやり直さない。§品質ゲート 8.2） |
| `worker_grace_seconds` | 10 | 中断・タスク保留時に worker へ中間コミットさせる猶予秒数（§並行性・再開・エラー処理） |
| `worker_model` | settings.json の既定（`sonnet`） | worker の `claude -p` モデル |
| `reviewer_vendor` | `claude` | レビュア種別。**v1 では値は読み込むだけで未使用**（常に Claude）。`codex` 連携はフェーズ 2（§実装状況） |
| `merge_strategy` | `merge` | worktree 取り込み方式 |
| `worker_permission_mode` | `bypassPermissions` | worker/レビュア `claude -p` の `--permission-mode`（空文字でフラグ無指定＝ambient settings 依存） |

環境変数：`SLACK_BOT_TOKEN` / `SLACK_CHANNEL`（Slack）。`ANTHROPIC_API_KEY` 等は既存どおり（イメージに焼かない、SEC-7）。

## 並行性・再開・エラー処理

- **並行性**：`executing` で依存解決済みタスクを `max_workers` まで goroutine 起動。各 worker は独立 worktree。共有状態（plan/Store/state/open.json）は排他制御し、作業ブランチへの統合（merge）は直列化する。長時間の外部呼び出し中はロックを保持しない（plan のスナップショットに対して実行）。**`waiting_human` のタスクは worker スロットを占有しない**ので、空いたスロットは他の `pending` タスクへ回る。
- **トリガー発火＝タスク単位の保留（peer を止めない）**：トリガーは worker 起動**前**（条件1・pre-dispatch）または worker が結果を返した**後**（条件2/4/5・stuck・review_gate_defect）に評価される。いずれの時点でも当該タスクの worker は「まだ起動していない／既に完了している」ため、発火時に**走行中の worker を個別に kill する処理は不要**（per-task の中断 context は持たない）。発火したタスクは `waiting_human` にして `intervention/open.json` へ積むだけで、`openInterventionLocked` は他へ一切干渉しない。**全 worker を束ねる単一 context を発火で `runCancel()` する旧挙動は廃止**する（これが「1 件の判断要求で全 worker が止まり再開時にやり直しになる」根因だった）。複数タスクが同時に要判断になっても、それぞれが独立に `waiting_human` になるだけで、互いを止めない。`abort`（中止）だけは run 全体を畳む特例として全 worker を停止し done へ向かう。中間コミット猶予（`worker_grace_seconds`）は**中断（Ctrl-C/`[q]`）で走行中 worker を止める経路にのみ**適用される（介入の保留経路では worker は走っていない）。
- **再開と新規開始の判定**：起動時に `state.json` を読み、**genuinely 中断された run（Phase=`executing`）のみ再開**する。それ以外（state.json 不在／Phase=`done`／未知の Phase）は**壁打ちから新規開始**する（`main.go` の `isResumable`）。これにより、(a) 完了済みの run が Phase=`done` を残して次回起動が即終了する、(b) 古い `executing` 状態へ無言で再開して壁打ちを飛ばす、という 2 つの失敗を防ぐ。`--fresh` を付けると中断された run でも強制的に新規開始する（`Store.ResetRun()` で state/plan/control・intervention/open.json を削除し、`CleanOrchWorktrees` で前回の worktree と `orch/*` ブランチを撤去してから壁打ちへ）。新規開始時は標準出力に「🆕 新規セッションを開始します」、再開時は「↩️ 前回の executing フェーズから再開します」を表示し、挙動を可視化する。
- **再開（executing）— 完了タスクを再実行しない**：`plan.json`・`intervention/open.json` を読み、`done` 以外のタスクから継続（06 §4.3、状態はファイルに永続）。正規化（`NormalizeForResume`）は**途中状態だけ**を対象とする：
  - `done`/`failed`/`blocked` は**一切触らない**（完了タスクは絶対に再実行しない）。
  - `waiting_human` は**保留のまま維持**（`open.json` のエントリと対応）。pending へ戻さない。
  - `running`/`review`/`revise` のまま落ちたタスクは `pending` に戻して再ディスパッチする。このとき `Task.SessionID` が残っていれば、その Attempt は `--resume <session-id>` で**続きから再開**し、白紙からやり直さない（§worker ディスパッチ 3）。
  - worktree ディレクトリが消えていてもブランチ `orch/<id>` が残っている場合は、`add -b`（ブランチ重複でエラー）ではなく**既存ブランチへ worktree を再接続**して以前のコミットを保全する（`Worker.PrepareWorktree` が `BranchExists`→`WorktreeAddExisting` で処理）。
- **中断（Ctrl-C / `[q]`）= クリーン中断**：SIGINT/SIGTERM は `[q]` と同一経路で処理する。in-flight worker へ中間コミットの猶予（`worker_grace_seconds`、既定 10 秒）を与えてから停止し、plan/state/open.json/session_id を保存し、`controller.go` は `errSuspended` を返して `Run` がクリーン終了（終了コード 0）。`main.go` は signal 受信で `log.Fatal` せず、この経路へ落とす。次回起動は Phase=`executing` から再開する。
- **エラー**：worker クラッシュ/タイムアウトは `Attempts++` で再試行、上限超過で trigger 3。レビューのフォーマット違反は実作業をやり直さずレビュー工程のみ再試行し、連続 `review_format_error_limit` 回で `review_gate_defect` 介入（§品質ゲート）。Slack 失敗は無視。コントローラ自身の panic は state を flush してから終了し、次回再開できるようにする。

## ビルドと配置

docker-proxy と同方式のマルチステージで `claude-orchestrator` を base イメージへ焼き込む。

- `.devcontainer/Dockerfile.claude`：builder ステージを追加し base へ COPY（既存 scripts COPY 群の近傍）。
  ```dockerfile
  FROM golang:1.24-alpine AS orch-builder
  WORKDIR /app
  COPY orchestrator/go.mod ./
  RUN go mod download
  COPY orchestrator/*.go ./
  RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /claude-orchestrator .
  # base ステージ内:
  COPY --from=orch-builder /claude-orchestrator /usr/local/bin/claude-orchestrator
  ```
  instruction テンプレートも `COPY orchestrator/instructions/ /usr/local/share/claude-orchestrator/` で同梱。
- `Makefile`：`build-orchestrator`（ローカル `go build`/`go test` 用）を追加。イメージ用は base ビルドに含まれるため独立イメージは作らない。

## CLI 連携（claude-dev orchestrate）

正本は [10_cli.md](10_cli.md)。契約のみ：既存 `cmd_code`（`tmux new-window -t main "claude"`）と同系統で、`claude-dev orchestrate [<ゴール>] [--fresh]` は実行中コンテナに対し
`docker exec -it -u <user> <name> tmux new-window -t main "claude-orchestrator …"` → `tmux attach` する。コンテナ起動は従来どおり `claude-dev start`。ゴール引数は任意（既定は壁打ちから開始、06 §5.1）。`--fresh` はそのままバイナリへ渡す（前回の実行状態を破棄して壁打ちから新規開始）。単一ウィンドウ構成のみ（worker 出力はダッシュボードの `[d]` で確認）。

バイナリ直叩きのフラグ（オーケストレーター開発・自己検証で使用。[70_sample-project.md](70_sample-project.md)／[docs/07_self-verification.md](../07_self-verification.md)）：

- `--workspace <dir>`：対象リポジトリのルート（既定は CWD）。サンプルへ向けるのに使う。
- `--instructions <dir>`：instruction テンプレートの上書きディレクトリ（既定はイメージ同梱）。ローカルの `orchestrator/instructions` を使う高速ループ用。
- `--start-executing`（**本改訂で追加する検証専用 affordance**）：`.orchestrator/plan.json` が `Ready=true` で存在する時だけ、壁打ちを飛ばして直接 `executing` から開始する。ready な seed plan が無ければ無効（通常の壁打ち開始へフォールバック）。決定論的な非対話検証（S1〜S5）のために用意し、通常運用の既定挙動（壁打ち開始）は変えない。

## テスト方針

`*_test.go`（docker-proxy の `main_test.go` 同様に純ロジックを単体テスト）：

- `trigger_test.go`：各トリガー条件の発火/非発火（特に stuck_limit 境界、NeedsHuman 受理、重大操作の事前審査）。
- `state_test.go`：State/Plan/Control の JSON ラウンドトリップ、audit.jsonl 追記、再開時の継続点算出。
- `plan_test.go`：依存解決順・並行起動可否・状態遷移（pending→…→done/failed）。
- `controller_test.go`：並行実行（同時実行数 ≤ max_workers・依存順序）・**trigger 発火で当該タスクのみ `waiting_human` 化し peer は継続**・介入解決後の再ディスパッチ・revise エラー時の trigger3・assumptions 記録・**中断/再開で done タスクを再実行しない**・**`waiting_human` を再開時に保持**・`SessionID` 再開（`--resume`）・レビューのフォーマット違反で実作業を再ディスパッチしない。

外部プロセス（`claude` / `git`）に依存する部分はインタフェース化してモック可能にする。動作確認（実機・ユースケース）は同梱のサンプルサブプロジェクトに対して行う（[70_sample-project.md](70_sample-project.md)・[docs/07_self-verification.md](../07_self-verification.md)）。

## 06 未決事項に対する本仕様での決定

| 06 §12 の未決事項 | 本仕様での決定 |
|---|---|
| 実行モードの「次の一手」を計画実行に寄せるか適応的にするか | **計画実行を基本**とし、レビュー失敗・エスカレーション等の分岐点でのみ `claude -p` 脳呼び出しで適応する |
| トリガー 3 の規定回数 | `stuck_limit` 既定 **3**（config 変更可） |
| 状態ストアのファイル構成 | 本書「状態ストアのファイル構成」で確定（`/workspace/.orchestrator/`） |
| 行き詰まり時の「別アプローチ」自動化範囲 | 失敗情報を付帯して worker を再ディスパッチ（別アプローチ）。最大 `stuck_limit` 回まで Attempt を重ね、なお未解決なら trigger 3（§試行回数とエスカレーション） |
| Slack 双方向（軽微選択の非同期化） | フェーズ 1 は一方向通知のみ。双方向は将来検討 |
| オーケストレーター用 LLM 選定 | worker/reviewer は config（既定 `sonnet`）。壁打ち脳は対話 `claude` の設定に従う |
| 介入の単位（peer を止めるか） | **タスク単位**。発火タスクのみ `waiting_human`、peer は継続。最上位 `intervening` 状態は廃止（06 §2.2/§6） |
| 中断・再開でのやり直し | done は再実行しない／worker の中間コミット＋`--resume` セッション再開で作業保全／Ctrl-C はクリーン中断（06 §4.3） |
| レビュー誤採点・パース失敗 | タスク固有 `completion` で採点・構造化出力・フォーマット違反は実作業を再実行せずゲート不具合介入（06 §8） |

> 上記は実装着手のために置いた決定であり、レビューで変更しうる。異論があれば指摘されたい。

## 実装状況

本書が記述する成果物の実装状況を明示する（「ドキュメントにあるのに動かない」を無くすため）。本改訂で**設計を更新したが未実装**の項目は、ドキュメント先行（CLAUDE.md の開発フロー）に従い「設計確定・実装待ち」として明示する。

**v1 で実装済み（コードで動作するが、一部は本改訂で挙動を変更予定）**：
- 外部制御ループと状態機械、状態ストア一式（state/plan/control/summary/assumptions/interventions/audit、intervention/<id>/、workers/<id>.log、worktrees/<id>/）。
- 再開と新規開始の判定（中断 run のみ再開、done/不在/未知は新規）、`--fresh`、`CleanOrchWorktrees`。
- 端末モード制御（`term.go`：raw/カノニカル復元）、`claude` 実行ファイル解決と PATH 補完（`claudebin.go`）。
- 壁打ち/介入の対話 `claude` 起動（instruction 注入・`ORCHESTRATOR.md` 前置）、handoff（control.json）、`control.json` 不在時の端末確認（続ける/実行/終了）。
- worker 並行ディスパッチ（`max_workers`）、worktree 生成/再接続、`claude -p`（`stream-json --verbose`・`--permission-mode`・ライブ tee）、結果解析、作業ブランチ統合（merge/rebase）。
- 品質ゲート（review→revise、`max_review_rounds`）、介入トリガー 5 条件、Slack 通知（コントローラ一本化）。
- ダッシュボード：状態ラベル・経過時間・試行回数、`[d]` ライブ worker 出力、`[p]` 一時停止、`[q]` 中断。
- 完了時の助言的な自然言語完了検証（`checkCompletion`、ブロックしない）。

**本改訂で実装済み（コードに反映。`go build`/`vet`/`test`（`-race` 含む）緑・gofmt 済み。実機 E2E 検証は自己検証サンプルで実施予定）**：
- **介入のタスク単位化**：トリガー発火で全 worker を `runCancel()` する旧挙動を廃止し、発火タスクのみ `waiting_human`・`intervention/open.json` キュー化、peer は継続。最上位 `intervening` 状態の廃止と `[i]` オンデマンド介入対応（§制御フロー／§モード切替／§並行性）。
- **中断・再開のやり直し最小化**：done を絶対に再実行しない正規化、`waiting_human` の保持、worker の中間コミット指示＋`SessionID`（`--session-id`/`--resume`）による同一 Attempt 再開、Ctrl-C を `[q]` と等価のクリーン中断にする（`log.Fatal` 廃止・`worker_grace_seconds` 猶予）。
- **品質ゲートの是正**：タスク固有 `completion` 必須化とプラン検証（lint）、`completion` のみで採点（プランゴールへのフォールバック禁止）、フォーマット違反と内容不合格の分離（`review_format_error_limit`・`review_gate_defect`）、実作業を再実行しないレビュー専用リトライ（§品質ゲート 8.1–8.3。[../MODIFICATION.md](../MODIFICATION.md) を本書へ統合済み）。※レビュア出力は現状 JSON 最終行方式＋パース失敗の構造的ハンドリングで実現。厳密なスキーマ強制（tool-forced structured output）は将来強化点。
- **自己検証のためのサンプルサブプロジェクト**：[70_sample-project.md](70_sample-project.md)／[docs/07_self-verification.md](../07_self-verification.md)。`examples/orch-sample/`・`scripts/orch-sample.sh`・Makefile `orch-sample`／`build-orchestrator -o` を実装。

> **残（実機 E2E）**: 実 `claude -p` を用いた S1〜S5（[docs/07_self-verification.md](../07_self-verification.md)）の動作確認は、`make build-orchestrator && make orch-sample SEED=1` 後に `orchestrator/orchestrator --workspace workspace/orch-sample --instructions orchestrator/instructions --start-executing` で実施し、結果を `docs/reviews/` に記録する。

**未実装（明示的に将来フェーズ／意図的に範囲外）**：
- `reviewer_vendor: codex`（別ベンダーレビュー）— **フェーズ 2**。v1 は値を読み込むのみで常に Claude を使用。
- Slack 双方向（interactive ボタンによる軽微選択／要判断のスレッド回答）— **フェーズ 2 以降**。
- Docker Agent / MCP 連携 — **フェーズ 3（必要なら）**。
- 完了基準未充足時の**不足分の自動タスク化**（現状は助言通知のみ。人間が判断）。
- 旧「Config B（worker ログ専用 tmux ウィンドウ）／`--workers-window`」は**廃止**（`[d]` ライブ表示に一本化）。`--workers-window` フラグは存在しない。

## 関連して更新した既存文書

本機能の実装に伴い、次の既存実装仕様・利用者文書を更新済み：

- [10_cli.md](10_cli.md)：`orchestrate` サブコマンド
- [40_devcontainer.md](40_devcontainer.md)：Dockerfile.claude の Go ビルドステージ（`orch-builder`）とバイナリ/instructions の COPY
- [20_makefile.md](20_makefile.md)：`build-orchestrator` ターゲット
- [docs/04_cli-reference.md](../04_cli-reference.md)：利用者向け `orchestrate` 説明
- [70_sample-project.md](70_sample-project.md)：本オーケストレーターの自己検証用サンプルサブプロジェクトと scaffold（本改訂で新規）
- [docs/07_self-verification.md](../07_self-verification.md)：自己検証の設計（本改訂で新規）
