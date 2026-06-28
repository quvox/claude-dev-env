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
├── main.go                        エントリ。引数解析・状態ストア初期化・モードブートストラップ
├── controller.go                  状態機械と run loop（中核）
├── state.go                       状態ストアの読み書きとスキーマ（JSON/JSONL）
├── mode.go                        前景所有とモード切替（対話 claude の exec / ダッシュボード描画）
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
| controller | 状態機械（wallbounce/executing/intervening/done）と run loop の駆動 |
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
├── intervention/<id>/    介入 1 件ごとの質問と回答（question.md / answer.md）
├── workers/<taskID>.log  worker ごとの生ログ
└── worktrees/<taskID>/   worker 用 git worktree（git worktree add で作成）
```

### 主要スキーマ

```go
// state.json
type State struct {
    Phase       string `json:"phase"`        // "wallbounce"|"executing"|"intervening"|"done"
    RunID       string `json:"run_id"`
    CurrentTask string `json:"current_task"` // 実行中タスクID（任意）
    StartedAt   string `json:"started_at"`   // RFC3339（コントローラが刻む）
    UpdatedAt   string `json:"updated_at"`
}

// plan.json
type Plan struct {
    Goal           string `json:"goal"`            // ゴールの要約（完了基準は completion へ）
    Completion     string `json:"completion"`      // 完了基準
    Ready          bool   `json:"ready"`           // 壁打ちで実行可と確定したか
    Tasks          []Task `json:"tasks"`
}
type Task struct {
    ID          string   `json:"id"`
    Title       string   `json:"title"`
    Description string   `json:"description"`     // worker へ渡す自己完結の指示
    Deps        []string `json:"deps"`            // 先行タスクID
    Status      string   `json:"status"`          // pending|running|review|revise|blocked|done|failed
    Irreversible bool    `json:"irreversible,omitempty"` // トリガー1: 計画段階で後戻り不可操作を含むと印付け
    IrrevApproved bool   `json:"irrev_approved,omitempty"` // 介入で承認済み。pre-dispatch trigger1 を再発火させない
    Attempts    int      `json:"attempts"`        // 実装ディスパッチ回数。revise では増やさない（§試行回数とエスカレーション）
    Worktree    string   `json:"worktree"`        // 相対パス
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
    InterventionID string `json:"intervention_id,omitempty"`
    TS             string `json:"ts"`
}

// assumptions.jsonl / interventions.jsonl / audit.jsonl の各行（1 行 1 レコード）
type Assumption   struct { TaskID, Description, Rationale, TS string }
type Intervention struct { ID, TaskID, TriggerReason, Question, Answer, TS string }
type AuditEntry   struct { TS, Event, TaskID string; Detail map[string]any; Usage *Usage }
```

**Task.Status の遷移**：`pending`（依存解決待ちを含む）→ `running`（controller が worker ディスパッチ時に設定）→ `review` →（重大指摘）`revise` → 解消で `done`。先行タスクが `failed` で起動不能なものは `blocked`。行き詰まり（§試行回数とエスカレーション）は介入へ回し、回復不能なら `failed`。

## 制御フロー（状態機械と run loop）

`controller.go` の状態遷移は 06 §2.2 に対応する。

```
[wallbounce] ──control.execute──▶ [executing] ──全タスクdone──▶ [done]
                                    │   ▲
                            trigger │   │ control.resume（解決）
                                    ▼   │
                               [intervening]
（abort は wallbounce/intervening いずれからも done へ）

介入は実行を一時停止する独立状態で、解決後は **executing へ復帰**する（wallbounce へは戻らない）。06 §2.2 に対応。
```

run loop の擬似フロー：

1. 起動時 `state.json` を読む。無ければ新規（Phase=wallbounce, RunID 採番）。既存で Phase=executing なら**再開**（§ 並行性・再開・エラー処理）。再開時は `plan.json` を正本とし、残存する `control.json` は無視して消す。
2. **wallbounce**：`mode.RunInteractive()` で対話 `claude` を前景に exec し、終了を待つ。終了後 `control.json` を読む：
   - `execute` かつ `plan.Ready==true` → executing へ
   - `continue_wallbounce` / Ready 未確定 → コントローラが端末で「続ける/実行/終了」を確認（『続ける』→ Phase=wallbounce のまま `mode.RunInteractive()` 再実行／『実行』→ executing／『終了』→ done）
   - `abort` → done
3. **executing**：`dashboard` を前景に出し、依存解決済みの `pending` タスクを並行度 `max_workers` まで起動。各タスクは pipeline：
   `worker 実装 → review → (重大指摘あり) revise → … → done`
   各ステップで `trigger.Evaluate()`（条件1は worker 起動前、条件2/4/5 は実行後）。発火したら loop を止め intervening へ。
4. **intervening**：該当タスクを保留し、`intervention/<id>/question.md` を書いて Slack でアラート、`mode.RunInteractive()` で対話 `claude`（文脈 seed 済）を**先に起動して待たせる**（06 §6.2）。人間の回答後、`control.json` を読む：`resume` なら解決を `interventions.jsonl` と該当タスクへ反映して executing へ復帰、`abort` なら done へ遷移。
5. 全タスク `done` → **done**（v1 では全タスク done を完了とみなす）。`completion`（実装仕様ドキュメント由来の自然言語の完了基準）の `claude -p` による最終検証と、未充足時の不足分の新規タスク化は、ClaudeRunner を用いた**拡張点として将来対応（v1 では未実装）**。最終サマリを Slack 送信。

## モード切替の実装（前景所有・子プロセス）

`mode.go` がコントローラの「前景の差し替え」を担う（06 §4.2）。

- **対話モード（壁打ち/介入）** `RunInteractive(ctx)`：`exec.Command("claude", args...)` を生成し、`Stdin/Stdout/Stderr = os.Stdin/os.Stdout/os.Stderr`（同一 TTY を共有）。`cmd.Run()` で**子の終了までブロック**する。これによりコントローラのループは自然に停止し、壁打ち/介入中は実行が止まる。
  - 壁打ち：引数なしの対話起動＋オーケストレーター脳の instruction を投入（§ instruction 注入）。
  - 介入：`--resume` は使わず**フレッシュ起動**し、`intervention/<id>/question.md` と関連状態を初期プロンプト/コンテキストとして渡す（06 §6.2 ノブ1=フレッシュ再構成、ノブ2=先に起動、ノブ3=常駐セッションを使わず controller が毎回新規 exec）。起動後、対話 claude は TTY で人間の入力を待つ（tmux が detach 中なら attach されるまで待機）。コントローラは `cmd.Run()` でその終了までブロックする。
- **実行モード** `RunDashboard(ctx)`：`dashboard.go` が ANSI で TTY を再描画しつつ、`worker.go` の goroutine 群を監督する。キー入力 `p`（一時停止）/`q`（中断）を処理する。`d`（worker ログ詳細）は tmux/CLI レイヤの affordance（ペイン分割＋tail）で、バイナリ内では受理するが **no-op**（リッチな分割表示は Config B／CLI レイヤの領分。対話 TUI を出すウィンドウは分割しない＝06 §5.3）。

### instruction 注入

対話モードの `claude` は「オーケストレーター脳」として振る舞う必要がある。起動時に専用 instruction（役割・介入トリガー・サマリ方針・`control.json`/`plan.json` への書き出し規約）を与える。instruction はイメージ同梱のテンプレート（例 `/usr/local/share/claude-orchestrator/wallbounce.md`）を `mode.go` が `claude` の初期コンテキストへ渡す。テンプレートは付録ドキュメント（06 §13 の「リードエージェント指示書テンプレート」相当）として別途管理する。

### 判断基準（介入トリガー・仮定方針・サマリ方針）の所在

オーケストレーターに与える**判断基準は、プロジェクトの `CLAUDE.md` には置かない**。次に明文化する（環境リポジトリでバージョン管理し、イメージに同梱）：

- **共通の定性ポリシー**：`orchestrator/instructions/wallbounce.md`（壁打ち脳）・`intervene.md`（介入脳）に、介入トリガー 5 条件・「軽微判断は最も妥当な仮定を置いて進め記録する」方針・状況サマリ定型・**開発フロー**（要件/設計/ユースケース → 整合性確認 → 実装仕様 → 実装 → ユースケース動作確認 → レビュー〔結果は `docs/reviews/`〕。CLAUDE.md と整合）を記述する。`plan.json` はこの開発フローを反映してタスク化する。
- **worker 向けの判断ルール**：`worker.go` の `workerResultGuide`（worker プロンプトに付加）に、上記の「軽微は仮定して `assumptions` に記録／重大のみ `needs_human` でエスカレーション」を worker 視点で記述する。
- **定量しきい値**（`stuck_limit` 等）は config（§設定）で調整する。
- **プロジェクト固有の判断基準**（任意）：プロジェクトルートの `ORCHESTRATOR.md`（**コミット対象**。gitignore される `.orchestrator/` 運用状態とは別）。存在すれば、壁打ち/介入の対話 instruction と worker/reviewer プロンプトの先頭に `mode.go`／`worker.go`／`review.go` が prepend する。CLAUDE.md とは独立で、CLAUDE.md には判断基準を書かない。

CLAUDE.md に置かない理由：CLAUDE.md は worker を含む Claude Code 全般への指示であり、オーケストレーターのガバナンス（いつ人間を呼ぶか）を混在させると worker にも波及して責務が濁るため。オーケストレーター脳は自分の instruction（＋将来のプロジェクト固有 policy）だけを読む。

## 壁打ち/介入の受け渡しプロトコル（handoff）

対話 `claude` は前景の子プロセスであり、コントローラと**ファイル経由**で受け渡す（プロセス間でメモリ共有しない）。

- 壁打ち脳は決定を `plan.json` に書き、実行可と判断したら `plan.Ready=true` にし、`control.json` に `{"request":"execute"}` を書いてからセッションを終了する（人間が `/exit`、または instruction が終了を促す）。
- 介入時は、対話脳が回答を `intervention/<id>/answer.md` と該当タスクへ反映し、`control.json` に `{"request":"resume","intervention_id":"<id>"}` を書いて終了する。
- 書き込みは原子的に行う（一時ファイル → rename）。コントローラは前景を取り戻した直後に `control.json` を読み、**消費後に `controller.go` が削除する**。`control.json` が無い/不正な場合はコントローラが端末で明示的に確認する（プロンプト依存にしない安全側）。再開時（Phase=executing）は `plan.json` を正本とし、残存する `control.json` は無視して消す（壁打ち直後のクラッシュも `plan.Ready` と `plan.json` の整合だけで判断する）。

## worker ディスパッチ

`worker.go` がタスク 1 件を `claude -p` で実行する。

1. **worktree 準備**：`git worktree add .orchestrator/worktrees/<taskID> -b orch/<taskID>`（ベースは現在の作業ブランチ）。タスクはこの worktree を CWD として走る（ファイル競合防止、06 §4.4）。
2. **プロンプト構築**：`Task.Description` ＋ 状態ストアから必要文脈（関連 docs/実装仕様の該当箇所、先行タスクの結果サマリ、制約・既決事項）を**過不足なく**注入（NFR-2）。巨大リポジトリ全体は渡さない。
3. **起動**：`claude -p "<prompt>" --output-format json`、CWD=worktree、出力を `workers/<taskID>.log` へも tee。`--permission-mode` は既存の bypass 前提に従う（コンテナ隔離・FW・proxy が外部被害を抑止、06 §10）。
4. **結果回収**：stdout の JSON を `WorkerResult` にデコード。`Usage` を `audit.jsonl` に記録。`NeedsHuman` が非 nil なら trigger へ（人間に直接問わせない＝06 §7）。`NeedsHuman.Options` は worker が提示する**候補データ**であり、worker 自身がレンダリングするのではなく、controller が intervening の対話モードで select→submit として人間に提示する（06 §7 と矛盾しない）。`WorkerResult.Assumptions`（軽微な仮定）は controller が `assumptions.jsonl` に追記する。
5. **取り込み**：worker は worktree 内で実装し**コミットまで行う**。レビュー合格後、**controller** が worktree のコミットを作業ブランチへ統合する（`merge`/`rebase` は `config.merge_strategy`。git 操作は orchestrator ユーザが実行し、worker の bypass とは独立）。コンフリクト・クラッシュ・タイムアウトは当該 Attempt の失敗として次の Attempt へ（§試行回数とエスカレーション）。

`claude -p` は worker のみが用いる。worker は Slack を送らず、結果は stdout でコントローラへ返す（06 §9）。technical control として worker プロセスには `SLACK_BOT_TOKEN` を渡さない。また worker には後戻りできない操作（push/deploy/削除/外部送信）を実行させず、必要なら `WorkerResult.NeedsHuman` でエスカレーションさせる。リモートへの push やデプロイ等の取り返しのつかない操作は controller のみが、介入で承認された場合に行う（トリガー1）。

## 品質ゲート（レビュー改訂ループ）

`review.go`：

1. 実装 worker と**別の** worker をレビュアとして起動（フェーズ 1 は同じ Claude、フェーズ 2 で Codex＝別ベンダー。06 §8/§11）。
2. レビュー入力は worktree の diff。観点を分ける：①要件充足・動作 ②セキュリティ・エラー処理・保守性（FR-9）。両観点のチェックリストを **1 回のレビュー呼び出し**に与え、findings を観点タグ付きで返させる（観点ごとに別呼び出しはしない）。レビュア出力は構造化（findings[]：`severity`(`critical`|`major`|`minor`), file, message, aspect）。
3. **重大** severity（`critical`/`major`）が残る間は実装 worker へ差し戻し（revise）、`max_review_rounds`（既定 3）まで反復する（この間 `Attempts` は増やさない。§試行回数とエスカレーション）。
4. 解消すれば `done`。上限到達でも重大指摘が残れば trigger 3（行き詰まり）として intervening（§試行回数とエスカレーション）。

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
| 4 | 方針の重大な分岐 | worker が `NeedsHuman`(`policy_branch`) を返す、または計画上のマーク |
| 5 | 前提の崩れ | worker が `NeedsHuman`(`prerequisite_broken`) で報告、または依存結果との矛盾検出 |

上記以外の軽微判断は fire せず、worker が置いた仮定を `assumptions.jsonl` に記録して続行する。

## Slack 通知

`slack.go`：`net/http` で `https://slack.com/api/chat.postMessage` に `Authorization: Bearer $SLACK_BOT_TOKEN` で JSON POST。`SLACK_BOT_TOKEN` 未設定なら no-op、送信失敗は握りつぶしてログのみ（既存 `sendslackmsg.sh` と同じ堅牢性方針）。`SLACK_CHANNEL`（既定は既存と同値）を宛先にする。これらの環境変数はホスト `~/.claude/settings.json` の `env` から entrypoint 経由でコンテナへ渡る（[30_scripts.md](30_scripts.md) §連携）。

送信契機：(a) 実行モードでサマリ更新時（`summary.md` 更新と同時）、(b) 介入トリガー発火時（要判断アラート「attach してください」）、(c) 完了時。**発信源はコントローラに一本化**し、worker・壁打ち中の対話 claude は送らない（06 §9）。worker・壁打ち/介入の対話 claude いずれにも `SLACK_BOT_TOKEN` を渡さないことで技術的に封じる（加えて対話 claude は instruction でも抑止）。トークンは controller のみが保持して送信する。

## ステータス・ダッシュボード

`dashboard.go` は 06 §5.2 ② の画面を描画する：goal、各タスクの `[i/n] worker X (claude): 状態 経過時間`、直近サマリ、仮定/介入カウント、キーヒント。ウィンドウ構成は既定で単一ウィンドウ（Config A）。`--workers-window` 指定時のみ Config B（`workers` ウィンドウに全 worker ログを prefix 付きで多重 tail）を tmux に作る（06 §5.3）。

## 設定（config / env）

`config.go` は設定を次の優先順位でマージする（下ほど強い）：**組み込み既定 → ユーザ全体 `~/.config/claude-dev.yaml` の `orchestrator:` セクション**（CLI と同ファイル、[10_cli.md](10_cli.md)）**→ プロジェクト `/workspace/.orchestrator/config.yaml`**。すべて任意で、無ければ既定値を使う。プロジェクト単位で並行度やモデルを変えられる。設定ファイルは `key: value` 形式の素朴な YAML サブセットで、外部ライブラリを使わず `config.go` 内の小さなパーサで読む（stdlib のみ）。

```yaml
# /workspace/.orchestrator/config.yaml（例）
max_workers: 5
stuck_limit: 3
max_review_rounds: 3
worker_model: sonnet
reviewer_vendor: claude      # フェーズ 2 で codex
merge_strategy: merge
```

| キー | 既定 | 用途 |
|---|---|---|
| `max_workers` | 5 | 並行 worker 数（コスト・競合の上限） |
| `stuck_limit` | 3 | トリガー 3 の規定回数（06 未決事項の解決） |
| `max_review_rounds` | 3 | レビュー改訂の最大周回 |
| `worker_model` | settings.json の既定（`sonnet`） | worker の `claude -p` モデル |
| `reviewer_vendor` | `claude`（フェーズ 2 で `codex`） | レビュア種別 |
| `merge_strategy` | `merge` | worktree 取り込み方式 |

環境変数：`SLACK_BOT_TOKEN` / `SLACK_CHANNEL`（Slack）。`ANTHROPIC_API_KEY` 等は既存どおり（イメージに焼かない、SEC-7）。

## 並行性・再開・エラー処理

- **並行性**：`executing` で依存解決済みタスクを `max_workers` まで goroutine 起動。各 worker は独立 worktree。共有状態（plan/Store/state）は排他制御し、作業ブランチへの統合（merge）は直列化する。長時間の外部呼び出し中はロックを保持しない（plan のスナップショットに対して実行）。trigger 発火時は新規起動を止め、実行中 worker を ctx キャンセルで停止・待機してから intervening へ遷移する（複数同時発火は abort 優先・次に task ID 昇順で 1 件採用）。
- **再開**：起動時 `state.json` の Phase=executing なら `plan.json` を読み、`done` 以外のタスクから継続（06 §4.3、状態はファイルに永続）。`done`/`failed`/`blocked` はスキップ。`running`/`review`/`revise` のまま落ちたタスクは、worktree の状態（コミット有無）を点検したうえで `pending` に戻して再ディスパッチする（途中結果があれば次の Attempt の入力に含める）。
- **エラー**：worker クラッシュ/タイムアウトは `Attempts++` で再試行、上限超過で trigger 3。Slack 失敗は無視。コントローラ自身の panic は state を flush してから終了し、次回再開できるようにする。

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

正本は [10_cli.md](10_cli.md)。契約のみ：既存 `cmd_code`（`tmux new-window -t main "claude"`）と同系統で、`claude-dev orchestrate [<ゴール>] [--workers-window]` は実行中コンテナに対し
`docker exec -it -u <user> <name> tmux new-window -t main "claude-orchestrator …"` → `tmux attach` する。コンテナ起動は従来どおり `claude-dev start`。ゴール引数は任意（既定は壁打ちから開始、06 §5.1）。`--workers-window` は Config B（worker ログの多重 tail ウィンドウ）を有効化する（既定は Config A＝単一ウィンドウ。06 §5.3）。

## テスト方針

`*_test.go`（docker-proxy の `main_test.go` 同様に純ロジックを単体テスト）：

- `trigger_test.go`：各トリガー条件の発火/非発火（特に stuck_limit 境界、NeedsHuman 受理、重大操作の事前審査）。
- `state_test.go`：State/Plan/Control の JSON ラウンドトリップ、audit.jsonl 追記、再開時の継続点算出。
- `plan_test.go`：依存解決順・並行起動可否・状態遷移（pending→…→done/failed）。
- `controller_test.go`：並行実行（同時実行数 ≤ max_workers・依存順序）・trigger 発火での intervening 遷移・介入解決後の再実行・revise エラー時の trigger3・assumptions 記録。

外部プロセス（`claude` / `git`）に依存する部分はインタフェース化してモック可能にする。

## 06 未決事項に対する本仕様での決定

| 06 §12 の未決事項 | 本仕様での決定 |
|---|---|
| 実行モードの「次の一手」を計画実行に寄せるか適応的にするか | **計画実行を基本**とし、レビュー失敗・エスカレーション等の分岐点でのみ `claude -p` 脳呼び出しで適応する |
| トリガー 3 の規定回数 | `stuck_limit` 既定 **3**（config 変更可） |
| 状態ストアのファイル構成 | 本書「状態ストアのファイル構成」で確定（`/workspace/.orchestrator/`） |
| 行き詰まり時の「別アプローチ」自動化範囲 | 失敗情報を付帯して worker を再ディスパッチ（別アプローチ）。最大 `stuck_limit` 回まで Attempt を重ね、なお未解決なら trigger 3（§試行回数とエスカレーション） |
| Slack 双方向（軽微選択の非同期化） | フェーズ 1 は一方向通知のみ。双方向は将来検討 |
| オーケストレーター用 LLM 選定 | worker/reviewer は config（既定 `sonnet`）。壁打ち脳は対話 `claude` の設定に従う |

> 上記は実装着手のために置いた決定であり、レビューで変更しうる。異論があれば指摘されたい。

## 関連して更新した既存文書

本機能の実装に伴い、次の既存実装仕様・利用者文書を更新済み：

- [10_cli.md](10_cli.md)：`orchestrate` サブコマンド
- [40_devcontainer.md](40_devcontainer.md)：Dockerfile.claude の Go ビルドステージ（`orch-builder`）とバイナリ/instructions の COPY
- [20_makefile.md](20_makefile.md)：`build-orchestrator` ターゲット
- [docs/04_cli-reference.md](../04_cli-reference.md)：利用者向け `orchestrate` 説明
