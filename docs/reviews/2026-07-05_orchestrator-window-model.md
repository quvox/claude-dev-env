# レビュー/E2E: オーケストレーター ウィンドウ方式（1 セッション＋ウィンドウ）＋生存判定修正

対象: feature/orchestrator-session-arch（別セッション→1 セッション＋ウィンドウ、及び復旧の生存判定修正）
日付: 2026-07-05
対象: orchestrator/{session,controller,dashboard,mode,main}.go, claude-dev(orchestrate), docs/06・impl/60・impl/10_cli

## 変更の要点
- worker/壁打ち/介入を「別セッション」から「唯一のセッション orch-<CNAME>-main 配下のウィンドウ」へ（親子＝ぶら下げ）。切替 select-window、生成 new-window、終了 kill-window、保持 remain-on-exit（dashboard=off / worker・wallbounce=on）。コントローラは dashboard 窓で常駐。
- 復旧の生存判定を has-session → コントローラプロセス（pgrep）へ（空き殻セッション誤検出の是正）。

## 徹底確認（独立エージェント）
- 設計層（06/10_cli）・design↔impl↔code を各2エージェント×複数ラウンドで確認。是正：Has の display-message 落とし穴（list-windows 厳密照合へ）、用語残骸（セッション→ウィンドウ）、[d] 併存（置換ではない）、未使用 daemon.go 削除、ReqAbort の closeWallbounceSession 対称化、命名統一、生存判定の波及（§4.1/§4.2/§5.1）。

## 実機 E2E（ビルド済みイメージ由来バイナリ）
1. 1 セッション配下に dashboard+worker ウィンドウ（prefix+w 一覧）… ✅
2. 番号キー：実行中→select-window／⏸→当該ウィンドウで介入 claude 起動 … ✅
3. worker ウィンドウ誤kill→定期復旧で再作成（~8s）… ✅
4. 完了 worker のウィンドウは閉じる（メイン常駐）… ✅
5. has-session=TRUE の空き殻状態を pgrep=ABSENT で正しく検出→kill+起こし直しで resume … ✅

## 所見
- 要件（worker をメインにぶら下げる・可視化・完了で閉じる・メインから選択・端末破壊耐性）を全レイヤで達成。
- 対話を伴う壁打ち/介入の「内容」E2E（回答品質）は人間が担当（本レビューは機構の E2E）。

## セキュリティ/無駄/処理時間
- launcher は SLACK_BOT_TOKEN strip 維持、パスは単一引用符エスケープ。復旧点検は 5 秒スロットル。worker 実行経路は不変（ウィンドウはビュー）。問題なし。
