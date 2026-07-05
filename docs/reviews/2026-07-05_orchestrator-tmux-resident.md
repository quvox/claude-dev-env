# レビュー: オーケストレーター「最終結線＝tmux常駐方式」

対象: `feature/orchestrator-session-arch` の 4fa33ee（独立セッション方式の最終結線）
日付: 2026-07-05
対象コード: `orchestrator/{session,mode,controller,dashboard,main,state}.go`, `claude-dev`（orchestrate）
対象ドキュメント: `docs/06_orchestration.md`, `docs/impl/10_cli.md`, `docs/impl/60_orchestrator.md`

## 背景・方式選択

コントローラの常駐を「setsid 完全デーモン化」と「tmux 常駐」のどちらで実装するかを確認し、
ユーザ判断で **tmux 常駐方式**（Model B）を採用。コントローラ＋ダッシュボードを 1 プロセスの
まま `orch-<CNAME>-main` セッション内で回し、tmux サーバを常駐の器とする。完全デーモン化で
必要になるダッシュボード別プロセス化＋ファイル IPC を回避でき、端末破壊耐性という本質要件は
満たせる（tmux server 死という稀な事象は状態からの resume で吸収）。

## 観点別所見

### 1. 要件・ユースケースに合致しているか
- **端末を閉じても作業継続**：controller が `orch-<CNAME>-main` 内で回るため、tmux クライアント
  終了＝detach でセッション（＝controller）は保持。✅ 実機で `has-session` 真＝常駐継続を確認。
- **単一コマンド復旧**：`claude-dev orchestrate` = has-session 真→attach のみ／偽→新 main で起動
  (resume)→attach。✅ `--print-main-session`／has-session 分岐を実機確認。
- **壁打ち/介入を専用セッションで**：`runWallbounceSession`／`resolveInterventionInSession` が
  該当セッションへ対話 claude を投入し `WaitConsume` で /exit を監視（自 pane を奪わない）。
  → 対話を伴う E2E（S1〜S5）は実 claude が要るため実機確認へ（下記「残」）。
- **メインループから worker 選択**：数字キーで ⏸ は当該セッションで介入、実行中はビュー切替。
  ✅ 選択番号 `‹k›` 表示・`[1-9]worker画面へ` を実機確認。

### 2. 無駄な処理
- 定期セッション復旧は 5 秒に 1 回へスロットル（tmux 呼び出し多発を回避）。妥当。
- 巨大 instruction/prompt を send-keys せず sidecar ファイル＋`$(cat)` で読む設計により、
  tmux への多 KB 文字列流し込みと引用符事故を回避。妥当。

### 3. 処理時間
- worker 実行・結果回収の経路は不変（セッションはビュー）。追加コストは tmux 制御呼び出しのみ
  でベストエフォート。ダッシュボード描画は従来どおり 1 秒 tick。問題なし。

### 4. セキュリティ
- launcher スクリプトは `unset SLACK_BOT_TOKEN`（Slack 発信はコントローラに一本化を維持）。
- パスは `shellSingleQuote` で単一引用符エスケープ。`WriteLaunchScript` は `.orchestrator/sessions/`
  配下（機械所有）に限定。問題なし。

## 改善した点（本レビュー中の指摘対応）
- 独立レビュア（2 並列）指摘を反映：
  - `60:219` の「トリガー発火で当該 worker を停止（中間コミット猶予）」は §並行性・06 と矛盾する
    誤記 → 「発火時点で worker は未起動/完了済みのため停止・猶予不要」に修正。
  - worker セレクタの「↑↓／番号」過剰約束（実装は数字キーのみ）→ 全該当箇所を「番号（数字キー）」へ統一。
  - `60` front matter に tmux/セッション管理/常駐/復旧 を反映。
  - `10_cli.md` の orchestrate を旧 `new-window -t main` から tmux常駐契約へ更新。
  - `.gitignore` に `/.orchestrator/` を追加（spec 記載どおり）。

## 見送り/残（要・実機 E2E）
- 対話を伴う S1〜S5（壁打ち→execute 遷移、⏸ 選択→当該セッションで介入→回答→再ディスパッチ、
  端末 close→再 attach、worker セッション誤 kill→再構築）は実 tmux＋実 claude が必要で自動化
  不能のため、実機で確認し追記する。
- テスト: `go build`/`vet`/`gofmt`/`go test -race` 全緑。純ロジック（WriteLaunchScript 生成物・
  selectableWorker の status 分岐・選択番号描画）は単体テスト追加済み。
