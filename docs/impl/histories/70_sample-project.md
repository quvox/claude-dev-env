## 2026-06-29（新規作成）
- 新規作成。自己検証用サンプルサブプロジェクト（`examples/orch-sample/` テンプレート）と scaffold（`scripts/orch-sample.sh`・Makefile `orch-sample`）、決定論検証用 seed plan、検証用 CLI affordance `--start-executing` の実装仕様。
- 開発対象は小さな Python ユーティリティ `mathkit`（独立 3 モジュール＋pytest）。seed plan に irreversible タスク（trigger1 で決定論的に介入発火）を含め、S1〜S5 を再現性高く踏ませる。
- scaffold は冪等（再実行でクリーン初期状態）。作業コピーは `.gitignore` 済みの `workspace/` 配下に独立 git リポジトリとして materialize。設計の正本は docs/07_self-verification.md。
