# orch-sample

AI オーケストレーターの**自己検証用**サンプルサブプロジェクト（使い捨ての開発対象）。

- 目的: オーケストレーター自身を実際に走らせ、並行実行・介入・中断/再開といった制御挙動を、実プロジェクトを犠牲にせず再現性高く検証するための小さな題材。詳細は [docs/07_self-verification.md](../../docs/07_self-verification.md) / [docs/impl/70_sample-project.md](../../docs/impl/70_sample-project.md)。
- 題材: 外部依存のない小さな Python ユーティリティ `mathkit`（独立3モジュール＋pytest）。テンプレートには**テスト（期待仕様）だけ**を置き、実装はスタブにして worker が完成させる。

## 使い方

`examples/orch-sample/` はテンプレート（正本）であり、直接開発しない。scaffold で使い捨て作業コピーへ展開する。

```sh
make orch-sample          # workspace/orch-sample/ へ scaffold（既存なら FORCE=1 で再生成）
make orch-sample SEED=1   # 決定論的検証用の seed plan (.orchestrator/plan.json) も配置
```

scaffold は冪等で、`FORCE=1`（`scripts/orch-sample.sh --force`）でクリーンな初期状態に戻せる。展開後は
`docs/impl/70_sample-project.md` の「実行方法」に従い `claude-dev orchestrate --workspace workspace/orch-sample` 等で走らせる。
