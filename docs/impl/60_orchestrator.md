---
summary: AI オーケストレーター（Go 製コントローラ）の実装仕様。tmux 常駐方式（コントローラは orch-<CNAME>-main セッション内で常駐）と独立ウィンドウ（ブレインストーミング/worker/介入）・ウィンドウ管理と復旧・状態ストア・worker 並行ディスパッチ・品質ゲート・介入・判断基準・Slack 通知・ビルド配置を定める。設計の意図は docs/06_orchestration.md を参照。
keywords: [ オーケストレーター, Go, tmux, セッション管理, 状態ストア, 介入, 並行実行 ]
---

# 実装仕様: orchestrator/（AI オーケストレーター）

> **この文書の役割**: プロジェクトごとに 1 体立てる AI オーケストレーター（Go 製コントローラ）の実装仕様。設計の意図・全体像は [docs/06_orchestration.md](../06_orchestration.md)、セキュリティ上の位置づけは [docs/03_security.md](../03_security.md) を参照。CLI 連携の正本は [10_cli.md](10_cli.md)、ビルド配置の正本は [40_devcontainer.md](40_devcontainer.md) / [20_makefile.md](20_makefile.md)（いずれも本機能の実装時に更新する）。

## 要件（なぜ必要か）

人間がオーケストレーター（進行管理）を兼ねるとプロジェクト並列度が上げられない。そこで、プロジェクトごとに「ブレインストーミング（検討）」と「実行（自律）」の 2 モードを持つ単一のコントローラを置き、人間はブレインストーミングと例外対応（介入）だけに関与する。コントローラは**外部制御ループ**としてループを所有し（Stop-hook の力技は採らない）、worker（`claude -p`）へ委譲し、結果を統合・レビューし、介入トリガー該当時のみ人間を呼ぶ。詳細根拠は 06 を参照。

## カバーするコード

```
orchestrator/                      ← 本書が正本（Go コンポーネント）
├── go.mod / go.sum / vendor/      独立モジュール。ダッシュボード TUI 用に **`bubbletea`/`lipgloss` へ依存**（従来の stdlib のみ方針を本 UI に限り変更）。依存は **vendoring（`vendor/`）** で取り込み、イメージビルドはネットワーク非依存（`-mod=vendor`）。go.work は用いない。ビルドは golang:1.24-alpine
├── main.go                        エントリ。引数解析（--fresh 等）・再開/新規判定・状態ストア初期化・モードブートストラップ
├── controller.go                  状態機械と run loop（中核）
├── state.go                       状態ストアの読み書きとスキーマ（JSON/JSONL）
├── mode.go                        モード切替（対話 claude の exec / WallbounceArgs での handoff_note 前置）。新アーキでは exec 先が該当 tmux ウィンドウ
├── session.go（新規・新アーキ）    tmux ウィンドウ管理（1 セッション配下：生成/終了/存在確認/再構築/mouse off/worker 選択切替/対話 claude のウィンドウ内投入）
├── term.go                        端末モード制御（stty による raw/カノニカル切替・復元）＋ selectMenu（矢印/番号選択メニュー）＋ printModeBanner（モード遷移バナー）
├── claudebin.go                   claude 実行ファイルの解決と子プロセス環境（PATH 補完）
├── handoff.go                     ブレインストーミング↔実行↔介入の受け渡しプロトコル（control.json）
├── worker.go                      worker ディスパッチ（claude -p）・worktree 管理・構造化出力
├── review.go                      品質ゲート（レビュー改訂ループ）
├── trigger.go                     介入トリガー判定
├── slack.go                       Slack 通知（chat.postMessage 直接 POST）
├── dashboard.go                   実行モードの共有状態（DashboardState）と純ヘルパ
├── dashtui.go（新規）             実行モードのダッシュボード＝カーソル選択式 TUI（bubbletea）
├── config.go                      設定・環境変数の読み込みと既定値
├── instructions/                  対話 claude 用テンプレート（イメージに同梱）
│   ├── brainstorming.md              ブレインストーミング脳の instruction
│   └── intervene.md               介入対応の instruction（question.md を前置して起動）
└── *_test.go                      trigger / state / plan / controller（並行・介入・lint 差し戻し）/ term（selectMenu）の単体テスト（§テスト方針）

（本機能の実装時に更新する既存コード。各々の正本は別文書）
claude-dev                         orchestrate サブコマンド追加（→ 10_cli.md）
.devcontainer/Dockerfile.claude    Go ビルドステージ追加＋バイナリ COPY（→ 40_devcontainer.md）
Makefile                           build-orchestrator / テストターゲット（→ 20_makefile.md）
```

イメージへは `claude-orchestrator` という名前のバイナリとして `/usr/local/bin/` に焼き込む（docker-proxy と同方式のマルチステージビルド）。docker-proxy のような独立コンテナではなく、**プロジェクトコンテナ内で実行**する（tmux・`claude` CLI・git worktree を同コンテナ内で扱うため）。

## 全体構成と責務

`claude-orchestrator` は単一プロセス。`main.go` が状態ストアを開き、現在の `Phase` に応じて `controller.go` の run loop を駆動する。

> **アーキテクチャ改訂（本改訂・実装は Phase③。tmux 常駐方式）**: コントローラは **`orch-<CNAME>-main` tmux セッション内で常駐**し（「常駐の器」は tmux サーバ＝クライアント全終了でもセッション保持）、ブレインストーミング・各 worker・介入を**同一セッション配下の独立した tmux ウィンドウ**として起こして制御する（06 §4.1/§4.2/§5.3/§5.9）。対話（ブレインストーミング/介入）は自分の pane ではなく該当ウィンドウ内で起動し、`control.json` のポーリングで `/exit` を検知する（自前景をブロックしない）。旧「run loop が端末前景を所有しモードで差し替える単一ウィンドウ方式」は廃止。詳細は下記「### 独立ウィンドウ方式（新アーキ）」。**現行のコード実装は tmux 常駐方式（実装済み）**。以降の本文で「`RunInteractive` で前景に exec」等と書かれた箇所は、**tmux が無い（headless/テスト）場合のフォールバック挙動**であり、実 tmux 環境では対話 claude は該当ウィンドウ内へ投入される（§実装状況が最新の成果物像）。

| モジュール | 責務 |
|---|---|
| controller | 状態機械（brainstorming/executing/done）と run loop の駆動。介入は executing 内のタスク単位イベントとして処理。**（新アーキ）`orch-<CNAME>-main` セッションの `dashboard` ウィンドウで常駐し、ブレインストーミング/worker/介入の tmux ウィンドウ群を生成・終了・復旧する** |
| state | `/workspace/.orchestrator/` 以下のファイル群の読み書き。監査ログ追記 |
| mode | ブレインストーミング/介入＝対話 `claude` を子プロセスで exec。**（新アーキ）exec 先は該当 tmux ウィンドウ（brainstorming / w-<taskID>）内** |
| session（新規・新アーキ） | tmux ウィンドウ（`orch-<project>-main` 配下の `dashboard`/`brainstorming`/`w-<taskID>`）の生成（new-window）・終了（kill-window）・存在確認（list-windows）・再構築・`mouse off`・worker 選択切替（select-window）・対話 claude のウィンドウ内投入 |
| handoff | 対話 claude（ブレインストーミング脳）からの遷移要求を `control.json` 経由で受け取る |
| worker | タスクを `claude -p` で worktree 上に実行し、構造化結果を回収。**（実装済み構成要素）各 worker に専用ウィンドウを起こしログを `tail -F` でライブ表示（実行・結果回収は従来経路のまま＝ウィンドウはビュー）。将来は `claude -p` 自体をウィンドウ内へ投入** |
| review | 実装 worker と別 worker による独立レビューと改訂ループ |
| trigger | 各ステップ（worker 起動前/実行後）で介入要否を明示的コードで判定 |
| slack | サマリ・介入アラートを Slack へ送る（発信源はコントローラに一本化） |
| dashboard / dashtui | 実行モードのダッシュボード＝**カーソル選択式 TUI（bubbletea・dashtui.go）**。`dashboard.go` は共有状態（DashboardState）と純ヘルパ、`dashtui.go` はモデル/描画/入力。**勝手にウィンドウを動かさず**、カーソル（↑↓/jk）で worker を選び **Enter で確定**したときだけ当該ウィンドウへ `select-window`（⏸ は介入）。毎秒全消去の旧描画は廃止（イベント駆動・差分描画。06 §5.3） |
| config | trigger 回数・モデル・並行度・最大レビュー周回などの設定 |

### 頭脳の所在（Claude か Go か）

オーケストレーターの「頭脳」（推論・判断）は**すべて Claude** が担う。Go コードは推論しない——ループの所有・順序付け・状態管理・ディスパッチ・機械的なトリガー判定（カウンタ／ハードルール）・Slack・描画という**決定論的な配管**に徹する（06 §3.1 の「L1 推論ループは自作せず Claude から借りる」の具体化）。

- **ブレインストーミング脳** ＝ 対話 `claude`：ゴール分解と計画（`plan.json`）の作成
- **worker 脳** ＝ `claude -p`：各タスクの実装・レビュー
- **適応判断** ＝ 分岐点（レビュー失敗時の再試行/エスカレーション等）でのみ `claude -p` を呼ぶ

したがって「タスクをどう分解するか」「何を実装するか」「指摘が妥当か」はすべて Claude の判断であり、Go は「次にどのタスクを誰へ渡し、いつ止めて人間を呼ぶか」という**段取り**だけを決める。

### 独立ウィンドウ方式（新アーキ。設計 06 §4.1/§4.2/§5.3/§5.9。実装済み）

コントローラを `orch-<CNAME>-main` セッションの `dashboard` ウィンドウで常駐させ、他コンポーネント（ブレインストーミング／各 worker／介入）を**同じセッション配下の tmux ウィンドウ**に分離する。以下が実装仕様。

- **tmux 常駐（setsid デーモンにはしない）**：`claude-orchestrator` は `claude-dev orchestrate` が起こす `orch-<CNAME>-main` セッションの `dashboard` ウィンドウで動き、その pane にダッシュボードを描画する。常駐性は tmux サーバが担保する——tmux クライアント（端末）が全終了しても切り離されたセッションは保持され、コントローラは走り続ける。よって setsid での完全デタッチ／`controller.log`／ダッシュボードの別プロセス化は**行わない**（完全デーモン化は端末を持てずダッシュボードを別プロセス＋ファイル IPC に分離する必要が生じ複雑化するため。06 §4.1 の判断）。**二重起動防止・復旧の生存判定は `claude-orchestrator` プロセスの生存**（`pgrep`。`has-session` ではない）：worker/brainstorming ウィンドウが `remain-on-exit on` のため、コントローラ〔`dashboard` 窓〕が死んでもセッションが空き殻として延命し得る＝`has-session` は生存信号にならない（06 §5.9）。判定は当該コンテナ内で `pgrep -f 'claude-orchestrator --workspace'` の結果から **cmdline が `claude-orchestrator` で始まるプロセス**だけを拾う（`tmux new-session …` 起動ラッパも同文字列を含むため除外）。`dashboard` ウィンドウは `remain-on-exit off`（他窓が無ければコントローラ終了でセッションも自然消滅＝正常完了 done の経路）。空き殻が残るのは `remain-on-exit on` 窓が在るまま中断/クラッシュした時のみ。tmux サーバごと落ちた場合はプロセスもセッションも消え、いずれも `.orchestrator/` の状態から resume（下記・復旧）。
- **命名と管理（`session.go`）**：唯一のセッション `orch-<CNAME>-main`、その配下のウィンドウを `session:window` ターゲットで表す——`orch-<CNAME>-main:dashboard`／`:brainstorming`／`:w-<taskID>`（`<CNAME>`＝正規化コンテナ名 `normalizeCName`）。コントローラ起動時に `SetupMainSession` が**自分のウィンドウを `dashboard` に改名**し、セッションに `mouse off`（全ウィンドウ波及）を設定。ウィンドウ生成は `tmux new-window -d -t <session> -n <win>`、終了は `tmux kill-window -t <target>`、切替は `tmux select-window -t <target>`（同一セッション内なので `switch-client` ではない）。**存在確認は `tmux list-windows -F '#{window_name}'` で窓名を厳密照合**する（`display-message -t session:window` は窓が無くてもセッションの現ウィンドウにフォールバックして成功を返すため、存在判定に使えない＝実機で判明した落とし穴）。
- **worker/brainstorming ウィンドウは「保持ウィンドウ」（`remain-on-exit on`）**：ウィンドウ内のコマンド（`claude -p` の tail ／対話 claude）が `/exit` で終了しても**ウィンドウは残る**ので、コントローラが `respawn-pane -k -t <target> "<cmd>"` で次のコマンドを投入できる：worker ウィンドウは `tail -F`（ビュー）→（要判断なら）対話 `claude`（介入）→再び `tail -F`（再ディスパッチのビュー）を順に投入。ライブ出力はそのウィンドウで直接見える（`prefix+w`／番号キーで到達）。※ダッシュボード内の `[d]` tail 表示は併存（`[d]`＝ダッシュボードで各 worker ログ末尾を一覧、番号キー＝個別 worker ウィンドウへ直接切替）。**タスク settle（done/failed/blocked）でコントローラが `kill-window`** する（メインセッションは常駐＝閉じない）。作業保全は従来どおり worktree。※worker の `claude -p` 自体はコントローラの子プロセスとして実行し結果を構造化回収する（ウィンドウはログ tail のビュー）。
- **ウィンドウの生成タイミング（事前審査トリガーを含む）**：`orch-<CNAME>-main:w-<taskID>` は、そのタスクが**dispatch されるとき、または pre-dispatch トリガー（条件1＝後戻り不可の事前審査）で `waiting_human` として保留されるとき**に生成する（＝⏸ になったタスクには必ずウィンドウが在る）。これによりセレクタから切り替える先のウィンドウが存在する。
- **ダッシュボード＝カーソル選択式 TUI（`dashboard` ウィンドウ）**：`orch-<CNAME>-main:dashboard` で `bubbletea` の TUI（`dashtui.go` の `dashModel`）が稼働 worker と要判断（⏸）を一覧描画する。**カーソル（↑↓/jk）で選び Enter で確定したときだけ移動**（勝手に動かさない）：実行中等はモデルが直接 `select-window`（ビュー切替）、⏸ は `actions` チャネルへ送りコントローラが当該ウィンドウで介入対話を起こす。`p`＝一時停止（`dash.Paused` トグル）・`d`＝出力 tail トグル（モデル内）・`q`＝中断・`i`＝先頭の要判断を介入。描画はイベント駆動・差分（毎秒全消去は廃止）。
- **介入＝当該 worker ウィンドウ内で対話**：要判断になったら、人間がセレクタで ⏸ を選ぶと、**その worker のウィンドウへ対話 `claude`（介入）を投入**し `select-window` で表示する（当該 1 件のみを seed）。回答（`answer.md`＋タスク更新＋`control.json`）後 `/exit` で `resolveOne` が突合、同ウィンドウへ `tail -F`（次 tick で再ディスパッチ）。**1 セッション/ウィンドウに全件 seed する旧方式は廃止し、要判断は worker ウィンドウ単位で個別処理**する。
- **ブレインストーミング**：コントローラは `orch-<CNAME>-main:brainstorming` ウィンドウを起こし、その中へ対話 `claude`（brainstorming.md 付き）を投入して `select-window` で表示する（自分の pane では起動しない）。`Handoff.WaitConsume`（`control.json` ポーリング＋`until`＝brainstorming ウィンドウ消滅/`pane_dead`、poll ごとに `select-window` で attach 済みクライアントを引き込む）で人間の `/exit` を待ち、戻ったら `dashboard` ウィンドウへ戻してメニュー（§handoff/§制御フロー step2）や実行遷移を行う。
- **単一コマンド復旧（`claude-dev orchestrate`）**：(1) コントローラプロセス生存 → `tmux attach -t orch-<CNAME>-main` するだけ。(2) 不在（クラッシュ・`[q]` 中断・tmux サーバ死）→ 延命した空き殻セッションが在れば `kill-session` してから、新しい `orch-<CNAME>-main` を `new-session -n dashboard` で作りその中で `claude-orchestrator` を起こす（状態から resume＝§4.3：executing の中断のみ継続、done/無しはブレインストーミング新規）→ 起動後コントローラが不足ウィンドウ（実行中タスクの `w-<taskID>`／ブレインストーミング中なら `brainstorming`）を再構築 → その後 attach。人間はこれ一発で端末破壊・中断・クラッシュから復旧する。コントローラは executing ループで数秒に一度、実行中/⏸ タスクの worker ウィンドウが消えていれば `openWorkerSession` で再作成する（誤 kill 復旧・06 §5.9）。
- **失われないことの担保**：ゴール/仕様=`docs/`、運用状態=`.orchestrator/`、実装=worktree コミット。tmux セッション/クライアントは使い捨てビュー。

## 状態ストアのファイル構成

プロジェクト内 `/workspace/.orchestrator/` に置き、永続化・再開・監査を担う。`.gitignore` に `/.orchestrator/` を追加する（成果物ではなく運用状態のため）。ブレインストーミングで固めた**仕様そのもの**は CLAUDE.md の規約に従い通常どおり `docs/`（実装仕様ドキュメント）へ書く。`.orchestrator/` は実行の運用状態を持つ。**原則（06 §4.3）：`.orchestrator/` 配下（`plan.json`・`control.json`・`state.json`・`handoff_note.md` 等）はブレインストーミング脳／介入脳／コントローラが読み書きする機械所有の内部状態であり、人間は手で編集しない。コントローラ・脳が出す文言も人間にこれらの編集を促してはならない**（修正が要る時はブレインストーミング＝対話へ誘導）。

```
/workspace/.orchestrator/
├── state.json            現在の Phase・RunID・現在タスク・タイムスタンプ
├── plan.json             タスク計画（ブレインストーミングの成果。タスク配列）
├── control.json          対話 claude → コントローラへの遷移要求（handoff）
├── handoff_note.md        lint 差し戻し理由の申し送り（コントローラが書き、次回ブレインストーミング instruction 先頭へ前置後に削除。機械所有・人間非編集）
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
    Phase       string `json:"phase"`        // "brainstorming"|"executing"|"done"（intervening は廃止）
    RunID       string `json:"run_id"`
    CurrentTask string `json:"current_task"` // 最後に着手したタスクID（情報用。並行実行のため一意ではない）
    StartedAt   string `json:"started_at"`   // RFC3339（コントローラが刻む）
    UpdatedAt   string `json:"updated_at"`
}

// plan.json
type Plan struct {
    Goal           string `json:"goal"`            // ゴールの要約（完了基準は completion へ）
    Completion     string `json:"completion"`      // プラン全体の完了基準（タスク採点には使わない。§品質ゲート）
    Ready          bool   `json:"ready"`           // ブレインストーミングで実行可と確定したか
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
    Request        string `json:"request"`        // "execute"|"resume"|"continue_brainstorming"|"abort"
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
[brainstorming] ──control.execute──▶ [executing] ──全タスク settled & 要判断 0──▶ [done]
                                    │  ▲
              タスクが要判断に該当     │  │ 人間が [i] で回答 → 該当タスクを再ディスパッチ
                                    ▼  │
              そのタスクのみ waiting_human（介入キューへ）。他タスクは executing 内で継続
（abort は brainstorming／介入対応中いずれからも done へ）

**最上位状態としての `intervening` は廃止**した（06 §2.2）。介入は `executing` の内部イベントとして、タスク単位で処理する。実行モードを離脱しないため、判断待ち以外の worker は止まらない。
```

run loop の擬似フロー：

0. 起動時、`main.go` は `--workspace` を **`filepath.Abs` で絶対パスに正規化**する。Store のパス（worktree パス含む）はこれに基づき、`git` は `cmd.Dir=workspace` で実行されるため、相対 workspace だと worktree パスが二重ネスト（`…/ws/ws/.orchestrator/worktrees/…`）して `git worktree add` が exit 128 → 「既に checked out」で stuck 化する。本番の `/workspace`（絶対）では顕在化しないが、任意パス起動の堅牢性として必須（[docs/reviews/2026-07-01_orchestrator-e2e.md](../reviews/2026-07-01_orchestrator-e2e.md)）。
1. 続いて `main.go` が `state.json` を読んで**再開か新規開始かを判定**する（§ 並行性・再開・エラー処理の「再開と新規開始の判定」）：中断された run（Phase=`executing`）のみ再開し、それ以外（不在／`done`／未知 Phase）または `--fresh` 指定時は実行状態を破棄して新規開始する。その後 `controller.go` の run loop は、新規開始なら Phase=brainstorming（RunID 採番）、再開なら永続化済みの Phase（executing）から動く。再開（executing）時は `plan.json`・`intervention/open.json` を正本とし、残存する `control.json` は無視して消す。
2. **brainstorming**：起動直前に**モードバナー**（§モード切替）を印字してから `mode.RunInteractive()` で対話 `claude` を前景に exec し、終了を待つ（人間が `/exit`／`Ctrl-D` で終了して初めて制御が戻る＝自動終了しない。06 §4.5/§5.4）。終了後 `control.json` を読む：
   - `execute` かつ `plan.Ready==true` かつ **lint clean**（全タスクに `completion` あり）→ executing へ。
   - `execute` だが **plan が実行不可**（`plan.Ready!=true` または lint 失敗）→ **メニューは出さず**、下記「実行不可の可視化」を行ってブレインストーミングへ差し戻す（`return nil`）。脳が execute を書いたが未完成なので、次回ブレインストーミングで `handoff_note.md` を見て補完させる。
   - `continue_brainstorming` → **メニューは出さず** Phase=brainstorming のまま `RunInteractive()` を再実行（脳が明示的に継続を選んだため。`return nil`）。
   - `abort` → done。
   - `control.json` 無・不明 → **終了後の選択メニュー**（下記。決定的な handoff が無いので人間に方向を確認）。
   - **終了後の選択メニュー**：`term.go` の `selectMenu`（矢印↑↓で移動＋Enter 確定、**番号キーは即確定**、各項目に一行説明。非 TTY は既定 **続ける** を返し勝手に実行しない）を提示。**`実行` は plan が実行可能（`ready` かつ全 completion）＝`canExecute` のときだけ含める**（`terminalConfirm(prompt, canExecute)`）：可なら「1. 続ける / 2. 実行 / 3. 終了」、不可なら「1. 続ける / 2. 終了」（ブレインストーミング未完了で実行を提示しない）。戻り値のマッピング＝`continue`→Phase=brainstorming のまま `RunInteractive()` 再実行／`execute`→再 lint し clean なら executing・不可なら「実行不可の可視化」して brainstorming 維持／`done`→done（06 §4.5 の値対応 continue_brainstorming/execute/abort）。
   - **実行不可の可視化（無言で戻らない。06 §4.5/§8.1）**：lint 失敗（or Ready 未確定）でブレインストーミングへ戻す際、`reportNotExecutable(plan, missing)` が **理由を端末（stderr）へ明示**し、`audit.jsonl` へ記録し、`Notifier`（Slack）にも送る。文言は**人間に `plan.json` を編集させない**（「ブレインストーミングに戻って対話で `completion` を補ってください」等の対話誘導のみ）。さらに理由を **次回ブレインストーミング脳へ引き渡す**ため `.orchestrator/handoff_note.md`（機械所有・人間非編集）へ書き、`mode.WallbounceArgs()` がその内容を次回 instruction 先頭に前置する（消費後に削除）。
3. **executing（スケジューラ・ループ）**：`dashboard` を前景に出し、ループを所有し続ける。1 tick ごとに：
   - 依存解決済みの `pending` タスクを並行度 `max_workers` まで起動。各タスクは pipeline：`worker 実装 → review → (重大指摘あり) revise → … → done`。各ステップで `trigger.Evaluate()`（条件1は worker 起動前、条件2/3/4/5〔stuck 含む〕は実行後）。
   - **トリガー発火はそのタスクだけに作用する**：発火タスクを `waiting_human` にして `intervention/open.json` へ積むだけ（トリガーは worker 起動前〔条件1〕か結果返却後〔条件2-5〕に評価されるため、発火時点で当該 worker は未起動または完了済み＝個別 kill も中間コミット猶予も不要。猶予は Ctrl-C/`[q]` 中断経路のみ＝§並行性）。**他 worker・ループは止めない**（旧 `runCancel()` による全停止は廃止）。
   - `[i]` キー（または `--resolve`）で人間が要判断に対応する時だけ、ループを止めずに（背景 worker は走らせたまま）対話 `claude` を前景に exec し、`open.json` 全件を seed。戻ったら回答済みエントリを解決し該当タスクを `pending` へ戻す。
   - `[p]`/`[q]` キー、SIGINT/SIGTERM の扱いは §モード切替・§並行性で定義。
   - **終了判定**：未解決の `waiting_human`／`open.json` エントリが 1 件でも残る間は run を終了しない。判断待ちが 0 かつ全タスク settled になったら完了検証（5）へ。
4. **介入対応（executing の内部イベント。最上位状態ではない）**：該当タスクを `waiting_human` にした時点で `intervention/<id>/question.md` を書き、`open.json` に積み、Slack で件数アラート。人間が `[i]` を押すまで対話 `claude` は起動しない（オンデマンド。06 §6.2／6.3）。`[i]` 時は対話 `claude`（文脈 seed 済、複数件はまとめて提示）を前景に exec。回答後 `control.json` を読む：`resume` なら answer.md のあるエントリを `interventions.jsonl` へ確定・`open.json` から除去・該当タスクを `pending` へ戻して executing 継続、`abort` なら done へ遷移。
5. 判断待ち 0 かつ全タスク settled → 完了検証 → **done**。完了時、`plan.completion`（自然言語の完了基準）が非空なら `claude -p` で**助言的な完了検証**を行う（`checkCompletion`）：完了基準と各タスクの結果サマリを渡し `{"satisfied":bool,"missing":string}` を読み取る。これは**ブロックしない助言**で、エラー・空・解析不能時は満たしたものとして扱い（`parseCompletionVerdict` が `(true,"")` を返す）run を止めない。未充足なら Slack 通知に不足点を添えて人間の最終確認を促す。未充足時の**不足分の自動タスク化**は意図的に範囲外（人間が判断）。`failed`/`blocked` を含み全 `done` でない場合は「未完了タスクあり」で done。最終サマリを Slack 送信。

## モード切替の実装（前景所有・子プロセス）

> **本節の「前景 exec／`[i]` 全件 seed」は tmux 無し時のフォールバック挙動の記述**。実 tmux 環境（現行の既定）では独立ウィンドウ方式（§「独立ウィンドウ方式（新アーキ）」）が動く＝対話 claude の投入先は該当 tmux ウィンドウ（brainstorming / w-<taskID> の保持ウィンドウ）、介入は ⏸ 選択で当該 1 件のみを対応（`IntervenePrompt`＋`WriteLaunchScript`）。最新の成果物像は §実装状況。

`mode.go` がコントローラの「前景の差し替え」を担う（06 §4.2）。

> **claude の実行ファイル解決（`claudebin.go`）**：オーケストレーターは `claude-dev orchestrate` から tmux ウィンドウの**非対話シェル（`zsh -c`）**で起動される。Claude Code のネイティブ導入先 `~/.local/bin` は**対話シェルの rc（`.zshrc`）でしか PATH に入らない**ため、非対話起動では `claude` が PATH に無く、素朴な `exec.Command("claude", …)` は「executable file not found」で失敗してブレインストーミング・介入・worker・レビュアの**すべてが動かない**。これを避けるため、対話モードと worker/レビュアの双方で `claudePath()`（`exec.LookPath`→無ければ `$HOME/.local/bin/claude` にフォールバック）で絶対パス解決し、子プロセスの環境は `claudeChildEnv()`（`SLACK_BOT_TOKEN` を除去しつつ claude の bin ディレクトリを PATH に補完）で渡す。

- **モード遷移バナー（UX。06 §5.4）**：各モードへ入る直前に、`term.go` の `printModeBanner(mode)` が端末へ一行のラベル付きバナー（現在モード名＋抜け方）を印字する。対話 claude は代替スクリーンで画面を占有するため**起動直前に印字**し、対話中は隠れるが `/exit` 後に scrollback として再表示される。少なくとも次を出す：ブレインストーミング入場「▶ ブレインストーミングモード。要件と plan を固め、済んだら `/exit` で実行へ」／介入入場「▶ 介入モード。要判断に回答し、済んだら `/exit` でダッシュボードへ戻る」／実行入場「▶ 実行モード（ダッシュボード）」。**終了メニュー**（続ける/実行/終了）は `selectMenu` 自身がタイトルと各項目の説明を表示するため、専用の printModeBanner は出さない（06 §5.4 の4モードのうち終了メニューは selectMenu が自己説明）。実装は日本語（06 §5.7）。
- **対話モード（ブレインストーミング/介入）** `RunInteractive(ctx)`：`exec.Command(claudePath(), args...)` を生成し、`Stdin/Stdout/Stderr = os.Stdin/os.Stdout/os.Stderr`（同一 TTY を共有）。`cmd.Run()` で**子の終了までブロック**する。これによりコントローラのループは自然に停止し、ブレインストーミング/介入中は実行が止まる。**対話モードから制御を戻す唯一の操作は子 claude の終了（`/exit`／`Ctrl-D`）**（自動では戻らない。06 §4.5/§5.4）。
  - **Ctrl-C（SIGINT）の授受**：対話 claude が前景（プロセスグループ前景）を占有する間、Ctrl-C はまず子 claude に届く。`main.go` の SIGINT ハンドラは ctx を cancel するため、子終了後にループは中断（suspend＝再開可）へ入る。すなわち **`/exit`＝そのモードだけ抜けてループへ戻る**、**Ctrl-C＝run 全体のクリーン中断**、と役割が分かれる（06 §5.2③）。**子の対話 `claude`（全画面 TUI）は共有 TTY を非カノニカル（raw）モードに切り替え、終了時にカノニカルへ戻さない**。コントローラは同じ TTY を使うため、`cmd.Run()` 復帰直後に `ttyRestoreSane()`（`term.go`）で**カノニカルな健全状態へ復元**する。これを怠ると、以降の行バッファ読み取り（`terminalConfirm` の確認入力、ダッシュボードのキー入力）が、raw モードでは Enter が `\n` ではなく `\r` を送るため `\n` を待ち続けて**永久にブロック**する。
  - ブレインストーミング：引数なしの対話起動＋オーケストレーター脳の instruction を投入（§ instruction 注入）。
  - 介入対応（`[i]` 押下時のみ）：`--resume` は使わず**フレッシュ起動**し、`intervention/open.json` の全件と各 `intervention/<id>/question.md` を初期プロンプト/コンテキストとして渡す（06 §6.2 ノブ1=フレッシュ再構成、ノブ3=常駐セッションを使わず controller が毎回新規 exec）。**旧「ノブ2=先に起動して待たせる」は廃止**——トリガー発火で自動起動して全実行をブロックする旧挙動をやめ、人間が `[i]` を押した時にオンデマンド起動する（06 §6.3）。複数件あればまとめて提示し、1 件ずつ回答させる（`ResolveArgs` が全 `open.json` の question を「`===== 介入 <id> =====`」区切りで seed）。コントローラは `cmd.Run()` でその終了までブロックするが、**背景の worker 子プロセスは前景占有中も走り続ける**。
    - **キューのナビゲーション（06 §5.5）**：複数件のとき `intervene.md` が進捗を口頭で明示する規約を持つ——各件冒頭「いま『<タスク名>』(k/N 件目) に回答中」、記録後「記録しました。次は『<次のタスク名>』(k+1/N)」、全件終了「全 N 件回答済み。`/exit` で戻ってください」。人間が「今どれ／次へ」を把握できるようにする。
    - **途中 exit の堅牢性（06 §5.2③）**：`resolveInterventions` の再突合は、各 open エントリについて `answer.md` が**非空のものだけ**を確定（`interventions.jsonl` 追記・`open.json` から除去・タスクを `pending` へ）し、**未回答（answer.md 空）は open のまま残す**。ゆえに途中 `/exit` は安全（未回答は消えず、再度 `[i]` で継続）。「回答した」の確定条件は**脳が `answer.md` に書いた時点**（口頭のみで記録前に exit すると未回答扱い）。
    - **abort**：介入脳が `control.json` に `abort` を書いて終了した場合、`resolveInterventions` は `aborted=true` を返し run を done へ（単なる離脱ではない）。
- **実行モード**：`dashtui.go` の bubbletea TUI（`dashModel`）が `dashboard` ウィンドウで差分描画し、controller が `worker.go` の goroutine 群を監督する。**ヘッダに現在モード（`● 実行中`／`⏸ 一時停止`）を明示**する（06 §5.4）。各タスク行は `待機中/実行中/レビュー中/修正中/要判断/完了/失敗/ブロック` のラベルと、実行中タスクの経過時間・試行回数を表示する（タスクが running になった時点で `syncDashboard` を呼ぶため「ずっと待機中に見える」ことはない）。`要判断`（`waiting_human`）は ⏸ で示す。**要判断は件数だけでなく開いているキューの一覧（タスク名）を表示**し（`open.json` の各 TaskID→タスク名）、`[i]` で対応する導線を示す（06 §5.5／§5.2②）。キー操作：
  - **VM 資源逼迫バナー（VM モード時）**：`render()` は描画のたびに `vm-healthd` の health ファイル（`$HOME/.claude-dev-vm/health`。正本 [80_vm-mode.md](80_vm-mode.md) §7.2）をベストエフォートで読み、`STATE=WARN` かつ `TS` が新しい（既定 120 秒以内）ときだけ画面上部へ赤の警告バナー（`⚠ VM資源逼迫（QEMU CPU …% / 上限 …%）…`）を出す。ファイルが無い／VM モードでない／鮮度切れ・パース失敗時は何も出さない（読取専用・エラーは無視）。**controller ループは非改変**で、追加は `dashboard.go`（`render` と補助 `readVMHealthBanner`）に限定する。
  - **`d`（worker 出力）**：詳細表示をトグルする。ON の間は実行中 worker の出力ログ（`workers/<taskID>.log`）の末尾をライブ表示する（`dashtui.go` の `detailTails`/`tailFile`）。worker は出力をログへ**ストリーム書き込み**する（§ worker ディスパッチ）ので、完了を待たずに進捗が見える。
  - **`p`（一時停止）**：新規スケジューリングを止める／再開するトグル（実行中 worker は走り続ける）。
  - **`i`（介入対応）**：`intervention/open.json` に未解決の要判断がある時だけ意味を持つ。対話 `claude` を前景に exec し、溜まっている要判断をまとめて回答させる（上記「介入対応」）。**他 worker は前景占有中も走り続ける**。回答済みタスクは executing で再ディスパッチされる。
  - **`q`（中断）/ Ctrl-C**：実行中 worker に**中間コミットの猶予**（`worker_grace_seconds`、既定 10 秒）を与えて停止し、**状態を `executing` のまま保存して終了する（done にしない）**。次回 `claude-dev orchestrate` は中断点から再開する（`controller.go` は `errSuspended` を返し `Run` がクリーン終了＝終了コード 0。`log.Fatal` しない。worktree のコミットと `session_id` は保全）。SIGINT/SIGTERM も同一経路で処理し、`[q]` と等価のクリーン中断とする。中断は破壊的ではない。
  
  実行モードのキー入力は **bubbletea が管理**する（生モード・代替スクリーンの設定/復元も bubbletea が担当。`WithContext(ctx)` で ctx キャンセル時に自動終了、`WithAltScreen` で復帰時に元画面へ戻す）。`term.go` の `rawKeyMode()`/`ttyRestoreSane()`（`stty`）は**ブレインストーミング後の確認メニュー（`selectMenu`。bubbletea 非経路）と、対話 claude〔brainstorming/intervene〕からの復帰時の端末復元**に用いる。`isig` は無効化しないため Ctrl-C はコントローラのシグナルハンドラへ届く。`main.go` は経路によらず `defer ttyRestoreSane()` で最終的に端末を健全状態へ戻す。

### instruction 注入

対話モードの `claude` は「オーケストレーター脳」として振る舞う必要がある。起動時に専用 instruction（役割・介入トリガー・サマリ方針・`control.json`/`plan.json` への書き出し規約）を与える。instruction はイメージ同梱のテンプレート（例 `/usr/local/share/claude-orchestrator/brainstorming.md`）を `mode.go` が `claude` の初期コンテキストへ渡す。テンプレートの正本は `orchestrator/instructions/brainstorming.md`・`intervene.md`（リポジトリ同梱＝カバーするコード §・[40_devcontainer.md](40_devcontainer.md) でイメージへ COPY）。規約の詳細は §「判断基準…の所在」。

### 判断基準（介入トリガー・仮定方針・サマリ方針）の所在

オーケストレーターに与える**判断基準は、プロジェクトの `CLAUDE.md` には置かない**。次に明文化する（環境リポジトリでバージョン管理し、イメージに同梱）：

- **共通の定性ポリシー**：`orchestrator/instructions/brainstorming.md`（ブレインストーミング脳）・`intervene.md`（介入脳）に、介入トリガー 5 条件・「軽微判断は最も妥当な仮定を置いて進め記録する」方針・状況サマリ定型・**開発フロー**（要件/設計/ユースケース → 整合性確認 → 実装仕様 → 実装 → ユースケース動作確認 → レビュー〔結果は `docs/reviews/`〕。CLAUDE.md と整合）を記述する。`plan.json` はこの開発フローを反映してタスク化する。**各タスクには `completion`（そのタスク単体で判定可能な完了基準。担当対象・唯一の成果物パス・満たすべき構造・責務外の明示）を必ず付与する**ようブレインストーミング脳に指示する（§品質ゲート 8.1。未設定はプラン検証で弾く）。加えて次の UX 規約を両テンプレへ明記する（06 §5.4–5.7）：
  - **`brainstorming.md`**：(1) **completion 自己検証**——全タスクに `completion` が揃うまで `plan.Ready=true` にせず `execute` handoff を書かない（completion 欠落のまま実行を提示しない。06 §8.1）。(2) 実行に足る状態になったら人間へ**「`/exit` で終了すると実行に移る」旨を明示**（06 §4.5）。(3) `handoff_note.md`（前回 lint 差し戻し理由）が前置されていたら、その不足 `completion` を最優先で補う。(4) **人間に `plan.json` 等の編集を促さない**（対話で詰める。06 §4.3）。
  - **`intervene.md`**：(1) **キュー進捗の口頭明示**（「いま『<タスク名>』(k/N)…／記録しました。次は…／全 N 件回答済み。`/exit` で戻る」。06 §5.5）。(2) 回答は `answer.md` に記録して初めて確定する旨と、済んだら `/exit` で戻る旨を人間へ伝える。
  - **両テンプレ共通**：(a) **人間に選択を求めるときは選択肢に必ず番号を付す**（`1. 2. 3.`。番号回答を受理。06 §5.6）。(b) **人間の判断・入力を求めるテキストは日本語**で提示する（内部作業は英語可。06 §5.7）。**役割分担**：worker は `needs_human` を日本語で起票するのが第一義（上記 worker 向け(d)）、介入脳は**保険**として万一英語で来ても日本語化して提示する（二重化。どちらが正かではなく、両方で「人間向けは日本語」を担保）。
- **worker 向けの判断ルール**：`worker.go` の `workerResultGuide`（worker プロンプトに付加）に、(a)「軽微は仮定して `assumptions` に記録／重大のみ `needs_human` でエスカレーション」、(b)**意味のある区切りで worktree に逐次コミットする**（中断時の作業保全。§worker ディスパッチ 5）、(c) 後戻り不可操作（push/deploy/削除/外部送信）は行わずエスカレーションする、(d) **`needs_human` の `question`／`options` は日本語で書く**（人間向けに提示されるため。これが第一義。06 §5.7）、を worker 視点で記述する。
- **定量しきい値**（`stuck_limit` 等）は config（§設定）で調整する。
- **プロジェクト固有の判断基準**（任意）：プロジェクトルートの `ORCHESTRATOR.md`（**コミット対象**。gitignore される `.orchestrator/` 運用状態とは別）。存在すれば、ブレインストーミング/介入の対話 instruction と worker/reviewer プロンプトの先頭に `mode.go`／`worker.go`／`review.go` が prepend する。CLAUDE.md とは独立で、CLAUDE.md には判断基準を書かない。
- **VM モード対応（正本 [80_vm-mode.md](80_vm-mode.md) / [docs/08_vm-mode.md](../08_vm-mode.md)）**：
  - **VM_DEV.md 前置（発見導線2）**：VM モード（環境変数 `CLAUDE_DEV_VM=1`）のとき、`LoadProjectPolicy`（`ORCHESTRATOR.md` 前置）と同じ仕組みで、ブレインストーミング/介入 instruction と worker/reviewer プロンプトの先頭に **VM モードの短いポインタ**（「docker はゲスト VM daemon（`DOCKER_HOST` 設定済）を指す・bind mount の source は `/workspace` 配下のみ・詳細は `/workspace/VM_DEV.md`」）を prepend する。実装は `state.go` の `VMModePreamble()`（`CLAUDE_DEV_VM=1` のとき定型文を返し、それ以外は空）を `mode.go`／`worker.go`／`review.go` の各プロンプト先頭で `LoadProjectPolicy` と並べて前置。CLAUDE.md には触れない。
  - **ゲスト `DOCKER_HOST` の継承**：orchestrator は `claude-dev orchestrate` が source した `/etc/claude-dev/vm.env` によりゲストの `DOCKER_HOST` を持ち、worker は `claudeChildEnv()`（`os.Environ()` 由来）でそれを継ぐ。よって Go 側の追加実装は不要（`DOCKER_HOST` を明示操作しない）。

CLAUDE.md に置かない理由：CLAUDE.md は worker を含む Claude Code 全般への指示であり、オーケストレーターのガバナンス（いつ人間を呼ぶか）を混在させると worker にも波及して責務が濁るため。オーケストレーター脳は自分の instruction（＋将来のプロジェクト固有 policy）だけを読む。

## ブレインストーミング/介入の受け渡しプロトコル（handoff）

対話 `claude` は前景の子プロセスであり、コントローラと**ファイル経由**で受け渡す（プロセス間でメモリ共有しない）。

- ブレインストーミング脳は決定を `plan.json` に書き、実行可と判断したら `plan.Ready=true` にし、`control.json` に `{"request":"execute"}` を書いてからセッションを終了する（人間が `/exit`、または instruction が終了を促す）。
- 介入時は、対話脳が回答を `intervention/<id>/answer.md` と該当タスクへ反映し、`control.json` に `{"request":"resume","intervention_id":"<id>"}` を書いて終了する。
- 書き込みは原子的に行う（一時ファイル → rename）。コントローラは前景を取り戻した直後に `control.json` を読み、**消費後に `controller.go` が削除する**。`control.json` が無い/不正な場合はコントローラが端末で**カーソル選択メニュー**で確認する（プロンプト依存にしない安全側。§制御フロー step2・06 §4.5）。再開時（Phase=executing）は `plan.json` を正本とし、残存する `control.json` は無視して消す（ブレインストーミング直後のクラッシュも `plan.Ready` と `plan.json` の整合だけで判断する）。
- **要判断 question の整形（`buildQuestion`）**：seed する質問は「`# 要判断: <タスク名>` → トリガー → このタスクの `completion` → 質問本文」で構成し、**選択肢がある場合は `1.` `2.` `3.` の連番**で出力する（`- ` の無番号箇条書きにしない。06 §5.6）。人間向けに提示される文字列であり**日本語**とする（06 §5.7）。
- **lint 差し戻し理由の申し送り（`handoff_note.md`）**：`.orchestrator/handoff_note.md`（機械所有・人間非編集）にコントローラ（`reportNotExecutable`）が実行不可理由（未設定 `completion` のタスク一覧等）を書き、次回 `mode.WallbounceArgs()` が instruction 先頭へ前置する。消費後に削除。これにより人間が内容を中継せずともブレインストーミング脳が欠けた `completion` を補える（06 §4.5）。

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
4. **レビュア出力は構造化出力で受ける**（findings[]：`severity`(`critical`|`major`|`minor`), file, message, aspect）。散文中の JSON を正規表現で拾う方式は補助フォールバックに留める。06 §8.2。**現状の実装は JSON 最終行方式＋パース失敗の構造的ハンドリング**で、tool による厳密なスキーマ強制は将来強化点（§実装状況）。
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

`trigger.go` の `Evaluate(ctx TriggerContext) (fire bool, reason string)` を各ステップで呼ぶ。`TriggerContext` は判定に要する `Task`・`Plan`・`State`・直前の `WorkerResult`・`Config` を保持する。条件 1（後戻り不可操作の事前審査）は worker 起動**前**に、条件 2/3/4/5（3=stuck 含む）は worker 実行**後**に評価する。06 §6.1 に対応：

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

送信契機：(a) 実行モードでサマリ更新時（`summary.md` 更新と同時）、(b) **タスクが要判断に該当し介入キューへ積まれた時**（要判断アラート「要判断 N 件。巡回時に attach し `[i]` で対応を」。run は止まらない旨を含意）、(c) 完了時。**発信源はコントローラに一本化**し、worker・ブレインストーミング中の対話 claude は送らない（06 §9）。worker・ブレインストーミング/介入の対話 claude いずれにも `SLACK_BOT_TOKEN` を渡さないことで技術的に封じる（加えて対話 claude は instruction でも抑止）。トークンは controller のみが保持して送信する。

## ステータス・ダッシュボード

`dashboard.go` は 06 §5.2 ② の画面を描画する：**ヘッダに現在モード（`● 実行中`／`⏸ 一時停止`）**、goal、各タスクの `[i/n] worker X (claude): 状態ラベル 経過時間 (試行N)`（`waiting_human` は ⏸ 要判断ラベル）、直近サマリ、仮定カウント・**未解決の要判断件数と一覧（`intervention/open.json` の各 TaskID→タスク名。件数だけでなくどのタスクが待っているかを列挙。06 §5.5）**・実行中数、キーヒント（`[d]`/`[p]`/`[i]`/`[q]`）。worker の実行内容は `[d]` 詳細表示でログ末尾をライブ確認できる（別ウィンドウ＝旧 Config B は廃止し、`[d]` に一本化した）。`[i]` は未解決の要判断がある時のみ有効。人間向け表示はすべて日本語（06 §5.7）。**（この段落は旧・全消去再描画方式の記述。現行は `dashtui.go` の bubbletea カーソル選択式 TUI＝`orch-<CNAME>-main:dashboard` ウィンドウで描画。カーソル↑↓/jk＋Enter で移動〔⏸ は介入・実行中はウィンドウ直視〕、`d` で出力 tail トグル。数字キー即移動は廃止。§「独立ウィンドウ方式（新アーキ）」／§実装状況）**

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
- **再開と新規開始の判定**：起動時に `state.json` を読み、**genuinely 中断された run（Phase=`executing`）のみ再開**する。それ以外（state.json 不在／Phase=`done`／未知の Phase）は**ブレインストーミングから新規開始**する（`main.go` の `isResumable`）。これにより、(a) 完了済みの run が Phase=`done` を残して次回起動が即終了する、(b) 古い `executing` 状態へ無言で再開してブレインストーミングを飛ばす、という 2 つの失敗を防ぐ。`--fresh` を付けると中断された run でも強制的に新規開始する（`Store.ResetRun()` で state/plan/control・intervention/open.json を削除し、`CleanOrchWorktrees` で前回の worktree と `orch/*` ブランチを撤去してからブレインストーミングへ）。新規開始時は標準出力に「🆕 新規セッションを開始します」、再開時は「↩️ 前回の executing フェーズから再開します」を表示し、挙動を可視化する。
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

正本は [10_cli.md](10_cli.md)。契約（tmux 常駐方式）：`claude-dev orchestrate [<ゴール>] [--fresh]` は実行中コンテナに対し、`docker exec -u <user> <name> tmux has-session -t orch-<CNAME>-main` を確認し——**在れば** `docker exec -it -u <user> <name> tmux attach -t orch-<CNAME>-main`（コントローラ常駐中）、**無ければ** 新しい `orch-<CNAME>-main` セッションを作りその中で `claude-orchestrator --workspace /workspace …` を起こして（状態から resume）から attach する。コンテナ起動は従来どおり `claude-dev start`。ゴール引数は任意（既定はブレインストーミングから開始、06 §5.1）。`--fresh` はそのままバイナリへ渡す（前回の実行状態を破棄してブレインストーミングから新規開始）。worker 出力は各 worker ウィンドウで直接確認（セレクタで切替。旧 `[d]` は縮退）。**これが単一コマンド復旧（06 §5.9）**。`<CNAME>` は正規化コンテナ名（`session.go` の `normalizeCName`）。

バイナリ直叩きのフラグ（オーケストレーター開発・自己検証で使用。[70_sample-project.md](70_sample-project.md)／[docs/07_self-verification.md](../07_self-verification.md)）：

- `--workspace <dir>`：対象リポジトリのルート（既定は CWD）。サンプルへ向けるのに使う。
- `--instructions <dir>`：instruction テンプレートの上書きディレクトリ（既定はイメージ同梱）。ローカルの `orchestrator/instructions` を使う高速ループ用。
- `--start-executing`（**本改訂で追加する検証専用 affordance**）：`.orchestrator/plan.json` が `Ready=true` で存在する時だけ、ブレインストーミングを飛ばして直接 `executing` から開始する。ready な seed plan が無ければ無効（通常のブレインストーミング開始へフォールバック）。決定論的な非対話検証（S1〜S5）のために用意し、通常運用の既定挙動（ブレインストーミング開始）は変えない。

## テスト方針

`*_test.go`（docker-proxy の `main_test.go` 同様に純ロジックを単体テスト）：

- `trigger_test.go`：各トリガー条件の発火/非発火（特に stuck_limit 境界、NeedsHuman 受理、重大操作の事前審査）。
- `state_test.go`：State/Plan/Control の JSON ラウンドトリップ、audit.jsonl 追記、再開時の継続点算出。
- `plan_test.go`：依存解決順・並行起動可否・状態遷移（pending→…→done/failed）。
- `controller_test.go`：並行実行（同時実行数 ≤ max_workers・依存順序）・**trigger 発火で当該タスクのみ `waiting_human` 化し peer は継続**・介入解決後の再ディスパッチ・revise エラー時の trigger3・assumptions 記録・**中断/再開で done タスクを再実行しない**・**`waiting_human` を再開時に保持**・`SessionID` 再開（`--resume`）・レビューのフォーマット違反で実作業を再ディスパッチしない・**lint 失敗（`completion` 欠落）で executing へ遷移せず `reportNotExecutable` が理由を出し `handoff_note.md` を書く**・**介入の部分回答（未回答は open のまま／回答済みのみ resolve）**・**`buildQuestion` が選択肢を連番（`1.`）で整形**。
- `term_test.go`（新規）：`selectMenu` の選択ロジック（矢印↑↓＋Enter／番号キー即確定→戻り値、非 TTY 既定=続ける）を、入力列→選択値の純関数部分としてテスト（TTY 依存部は分離）。※日本語ラベルのため「初文字選択」は設けない。

外部プロセス（`claude` / `git`）に依存する部分はインタフェース化してモック可能にする。動作確認（実機・ユースケース）は同梱のサンプルサブプロジェクトに対して行う（[70_sample-project.md](70_sample-project.md)・[docs/07_self-verification.md](../07_self-verification.md)）。

## 06 未決事項に対する本仕様での決定

| 06 §12 の未決事項 | 本仕様での決定 |
|---|---|
| 実行モードの「次の一手」を計画実行に寄せるか適応的にするか | **計画実行を基本**とし、レビュー失敗・エスカレーション等の分岐点でのみ `claude -p` 脳呼び出しで適応する |
| トリガー 3 の規定回数 | `stuck_limit` 既定 **3**（config 変更可） |
| 状態ストアのファイル構成 | 本書「状態ストアのファイル構成」で確定（`/workspace/.orchestrator/`） |
| 行き詰まり時の「別アプローチ」自動化範囲 | 失敗情報を付帯して worker を再ディスパッチ（別アプローチ）。最大 `stuck_limit` 回まで Attempt を重ね、なお未解決なら trigger 3（§試行回数とエスカレーション） |
| Slack 双方向（軽微選択の非同期化） | フェーズ 1 は一方向通知のみ。双方向は将来検討 |
| オーケストレーター用 LLM 選定 | worker/reviewer は config（既定 `sonnet`）。ブレインストーミング脳は対話 `claude` の設定に従う |
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
- ブレインストーミング/介入の対話 `claude` 起動（instruction 注入・`ORCHESTRATOR.md` 前置）、handoff（control.json）、`control.json` 不在時の端末確認（続ける/実行/終了。**本改訂でテキスト入力から矢印/番号のカーソル選択 `selectMenu` へ置換**＝下記 UX 改修）。
- worker 並行ディスパッチ（`max_workers`）、worktree 生成/再接続、`claude -p`（`stream-json --verbose`・`--permission-mode`・ライブ tee）、結果解析、作業ブランチ統合（merge/rebase）。
- 品質ゲート（review→revise、`max_review_rounds`）、介入トリガー 5 条件、Slack 通知（コントローラ一本化）。
- ダッシュボード：状態ラベル・経過時間・試行回数、`[d]` ライブ worker 出力、`[p]` 一時停止、`[q]` 中断。
- 完了時の助言的な自然言語完了検証（`checkCompletion`、ブロックしない）。

**本改訂で実装済み（コードに反映。`go build`/`vet`/`test`（`-race` 含む）緑・gofmt 済み。実機 E2E 検証は自己検証サンプルで実施予定）**：
- **介入のタスク単位化**：トリガー発火で全 worker を `runCancel()` する旧挙動を廃止し、発火タスクのみ `waiting_human`・`intervention/open.json` キュー化、peer は継続。最上位 `intervening` 状態の廃止と `[i]` オンデマンド介入対応（§制御フロー／§モード切替／§並行性）。
- **中断・再開のやり直し最小化**：done を絶対に再実行しない正規化、`waiting_human` の保持、worker の中間コミット指示＋`SessionID`（`--session-id`/`--resume`）による同一 Attempt 再開、Ctrl-C を `[q]` と等価のクリーン中断にする（`log.Fatal` 廃止・`worker_grace_seconds` 猶予）。
- **品質ゲートの是正**：タスク固有 `completion` 必須化とプラン検証（lint）、`completion` のみで採点（プランゴールへのフォールバック禁止）、フォーマット違反と内容不合格の分離（`review_format_error_limit`・`review_gate_defect`）、実作業を再実行しないレビュー専用リトライ（§品質ゲート 8.1–8.3。[../MODIFICATION.md](../MODIFICATION.md) を本書へ統合済み）。※レビュア出力は現状 JSON 最終行方式＋パース失敗の構造的ハンドリングで実現。厳密なスキーマ強制（tool-forced structured output）は将来強化点。
- **自己検証のためのサンプルサブプロジェクト**：[70_sample-project.md](70_sample-project.md)／[docs/07_self-verification.md](../07_self-verification.md)。`examples/orch-sample/`・`scripts/orch-sample.sh`・Makefile `orch-sample`／`build-orchestrator -o` を実装。

**本改訂で実装済み（オーケストレーター UX 改修。`go build`/`vet`/`test`〔-race 含む〕緑・gofmt 済み。06 §4.3/§4.5/§5.4–5.7/§8.1）**：
- `term.go`：`selectMenu`（矢印↑↓＋Enter／番号即確定・各項目説明・非TTY既定=続ける。v1 のテキスト `terminalConfirm` を置換）と `printModeBanner`（ブレインストーミング/介入/実行の入場バナー）。
- `controller.go`：`reportNotExecutable`（実行不可を端末＋audit＋Slack へ明示・無言差し戻し廃止）と `.orchestrator/handoff_note.md`（次回ブレインストーミングへ理由前置。人間非編集）。メニューは `control.json` 無/不明時のみ、`execute` だが実行不可は理由表示でブレインストーミング直帰。
- `buildQuestion`：選択肢を `1.` 連番で整形・日本語。ダッシュボード：ヘッダにモード明示＋要判断の一覧（タスク名）。
- 指示テンプレ（別途 §「判断基準…の所在」）：`brainstorming.md`（completion 自己検証で ready/execute を出す前に全 completion を揃える・`/exit` 案内・handoff_note 反映・plan.json を人間に編集させない）、`intervene.md`（キュー進捗の口頭明示・answer.md 記録後 `/exit`）、両者共通（選択肢は番号付き・人間向けは日本語）。`worker.go` の `needs_human` は日本語起票。

**本改訂で独立ウィンドウ方式を実装（tmux 常駐方式。06 §4.1/§4.2/§5.3/§5.9・本書「独立ウィンドウ方式（新アーキ）」）**：

*実装・単体テスト済み（`go build`/`vet` 緑・gofmt 済み・`go test -race` 全緑）*：
- `session.go`：`SessionManager`。唯一のセッション `MainSession()`＝`orch-<CNAME>-main`、その配下のウィンドウを `DashboardWindow()`/`WallbounceWindow()`/`WorkerWindow(taskID)`（`session:window` ターゲット）で表す。`SetupMainSession`〔起動時に自窓を `dashboard` に改名＋セッションへ `mouse off`〕・`Ensure`〔`new-window -d`＋`remain-on-exit on`。冪等〕・`Run`〔`respawn-pane -k` 投入〕・`Kill`〔`kill-window`〕・`Has`〔**`list-windows -F '#{window_name}'` で窓名を厳密照合**。`display-message` は窓不在でも現窓へフォールバックし成功を返すため使わない＝実機で判明した落とし穴〕・`SwitchTo`〔`select-window`〕・`PaneDead`〔`/exit` 検知の副信号〕・`LaunchInteractive`〔保持ウィンドウへ対話 claude を投入し `select-window`〕・`ExpectedWindows`/`EnsureAll`〔復旧〕・`splitTarget`・`tmuxAvailable`。`remain-on-exit on` により対話 claude の `/exit` 後もウィンドウが残り、`tail`→介入→再ディスパッチを同一ウィンドウで駆動できる。テスト：命名正規化・ウィンドウターゲット名（`TestSessionNames`）・`TestSplitTarget`・`TestExpectedWindows`。
- 対話のウィンドウ内投入（`mode.go`）：`brainstormingInstr`/`interveneInstr`（instruction 組立）・`IntervenePrompt`（1件の system/prompt ペア）・`WriteLaunchScript(key,sys,prompt)`（`.orchestrator/sessions/<key>.sh` に launcher を生成。VM env source・claude を PATH・`SLACK_BOT_TOKEN` strip・`cd` workspace・巨大 prompt は `.sys`/`.prompt` sidecar から `$(cat …)` で読む＝argv/quoting 肥大回避）・`shellSingleQuote`。テスト：`TestWriteLaunchScript`・`TestWriteLaunchScript_NoPromptOmitsPositional`・`TestShellSingleQuote`。
- ブレインストーミングのセッション化（`controller.go`）：`runWallbounce` は tmux 有り時 `runWallbounceSession`（brainstorming ウィンドウへ `LaunchInteractive`→`WaitConsume(until=!Has||PaneDead)→`dashboard` へ復帰）。attach クライアントの引き込みは `LaunchInteractive` の初回 `select-window` のみ（毎ポーリングでの再切替はしない＝ユーザが dashboard 等へ自由に移動できるようにするため）。実行/終了遷移時に `closeWallbounceSession`。tmux 無し（headless/テスト）は従来の `RunInteractive` 前景フォールバック（`RunInteractive` は当該フォールバック専用として残す）。
- 介入のセッション化（`controller.go`）：`resolveInterventionInSession(taskID)`＝当該 `w-<taskID>` へ `LaunchInteractive`→`WaitConsume`→`main` 復帰→`resolveOne`（回答突合→pending→次 tick で再ディスパッチ）。ダッシュボードは `main` で生きたまま（`stopDash` しない）、peer も継続。executing ループは `d.Resolve`（⏸ 選択）と `[i]`（先頭要判断、tmux 有り時は同経路／無し時は従来 `resolveInterventions` バッチ）で起動。`openIDForTask` で open キューから id 解決。
- worker ウィンドウ結線（`controller.go`）：dispatch と **pre-dispatch ⏸ 化**の両方で `openWorkerSession`（ログ tail のライブ表示。⏸ タスクに必ずウィンドウが在る不変条件）、settle で `closeWorkerSession`（`waiting_human` は残す）。executing ループは数秒に一度 `EnsureAll` 相当の点検で、実行中タスクの消えた worker ウィンドウを `openWorkerSession` で再構築（誤 kill 復旧・06 §5.9）。`main.go` は `Sessions` を常に注入。
- ダッシュボード＝カーソル選択式 TUI（`dashtui.go`・bubbletea）：`dashModel`（Init/Update/View）。カーソル（↑↓/jk）で選択、Enter で確定＝実行中はモデルが `select-window`／⏸ は `actions` チャネルへ `{resolve,taskID}`。`p`（`dash.Paused` トグル）・`d`（出力 tail トグル・モデル内）・`i`（先頭介入）・`q`（中断）。`newDashProgram` を controller が `isTTY()` 時のみ起動（`WithAltScreen`＋`WithContext(ctx)`）、非 TTY/テストは UI なし。旧 `render`/`renderString`/`readKeys`/`Dashboard`/`KeyEvent`/数字キー即移動/選択番号 `‹k›` は廃止。テスト：`TestDashView_RendersTasksAndCursor`・`TestDashCursor_MovesAndClamps`・`TestDashEnter_OnWaitingHumanSendsResolve`・`TestDashQuit_SendsQuit`（dashtui_test.go）、`TestSelectableWorkerID`/`TestSelectableWorkerStatus`。
- handoff 監視：`Handoff.WaitConsume`（control.json をポーリング＋`until` で /exit 検知）。テスト：出現検知・until 終了。
- CLI（`claude-dev orchestrate`）：`--print-main-session` で本体からメインセッション名を得て、**コントローラプロセス生存**（`pgrep` で cmdline が `claude-orchestrator` で始まるものを判定。tmux 起動ラッパを除外）で分岐——生存→`attach` のみ／不在→空き殻セッションを `kill-session`→新 `orch-<CNAME>-main`（`new-session -n dashboard`）で `claude-orchestrator` 起動（resume）→`mouse off`→attach（→[10_cli.md](10_cli.md)）。`has-session` は空き殻を誤検出するため使わない。従来の `tmux new-window -t main` 直起動は廃止。

*残（実機 E2E で最終確認）*：実 tmux＋実 claude の対話が必要なため自動テストでは検証不能。S1〜S5（[docs/07_self-verification.md](../07_self-verification.md)）を実機で確認し `docs/reviews/` に記録する（ブレインストーミング→execute 遷移、⏸ 選択→当該ウィンドウで介入→再ディスパッチ、端末 close→再 attach 復旧、worker ウィンドウ誤 kill→再構築）。

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
