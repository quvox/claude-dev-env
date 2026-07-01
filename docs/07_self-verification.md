---
summary: 本オーケストレーター自身を、リポジトリ同梱の小さなサンプルサブプロジェクトに対して実際に動かし、ユースケースに沿って検証・改善するための設計文書。実プロジェクトを犠牲にせず高速・再現可能にオーケストレーターの不具合を発見/修正する開発ループを定める。
keywords: [ 自己検証, ドッグフーディング, サンプルプロジェクト, 再現性, 介入, 中断再開, 動作確認 ]
---

# 自己検証（オーケストレーターのドッグフーディング）設計

> **この文書の役割**: AI オーケストレーター（[docs/06_orchestration.md](06_orchestration.md) / [docs/impl/60_orchestrator.md](impl/60_orchestrator.md)）**自身**を検証・改善するための仕組みを設計する。実装仕様の正本は [docs/impl/70_sample-project.md](impl/70_sample-project.md)。

## 1. 背景と要件（なぜ必要か）

現状、オーケストレーターの不具合は「**他の実プロジェクトを開発させて偶然見つける**」方法でしか発見できない。これは遅く・高コストで、再現も難しい。実機検証で見つかった構造的不具合（介入で全 worker が止まる／中断後にやり直しになる／レビュー誤採点。[MODIFICATION.md](MODIFICATION.md) と 06 §2.2・§4.3・§8）も、この非効率な経路で顕在化した。

そこで、**リポジトリに小さなサンプルサブプロジェクトを同梱**し、それに対してオーケストレーターを実際に走らせて検証・修正できるようにする。要件：

- **実プロジェクトを巻き込まない**：検証は使い捨ての作業コピーで完結する。
- **高速・低コスト**：サンプルは小さく、worker 呼び出し回数・トークンを抑える。
- **再現可能**：いつでも同じ初期状態から開始でき、何度でもやり直せる。
- **ユースケース準拠**（CLAUDE.md「動作確認」）：単体テストの通過で満足せず、**実際の振る舞い**（並行実行・介入・中断/再開）を確認する。
- **不具合再現がしやすい**：本改訂で直す 3 系統の不具合を**意図的に・決定論的に**踏ませるシナリオを持つ。

## 2. 方式

### 2.1 サンプルは「テンプレート」と「使い捨て作業コピー」を分ける

```
claude-dev-env/
├── examples/orch-sample/      ← テンプレート（git 追跡・正本）。小さな開発対象＋ORCHESTRATOR.md/CLAUDE.md/seed plan
└── workspace/                 ← .gitignore 済み。claude-dev が実プロジェクトを置く場所
    └── orch-sample/           ← scaffold で materialize した使い捨て作業コピー（独立 git リポジトリ）
```

- テンプレートを `examples/orch-sample/` に**コミット**し正本とする。
- scaffold（`make orch-sample` 等）でテンプレートを `workspace/orch-sample/` へ複製し、**独立した git リポジトリとして初期化**（`git init` ＋初期コミット）する。`workspace/` は元から gitignore されており、claude-dev が実プロジェクトをマウントする場所と同じ＝**本番と同じ条件**で検証できる。
- 親リポジトリにネストした生きた git リポジトリを置かない（worktree 操作が親リポジトリを汚さない）。やり直しは「作業コピーを消して再 scaffold」で**クリーンな初期状態**に戻せる。

### 2.2 二つの実行モードで回す

1. **イメージ同梱バイナリで**（本番同等）：`claude-dev start` → `claude-dev orchestrate`（`--workspace workspace/orch-sample`）。利用者体験そのものを確認する。
2. **ローカルビルドで**（オーケストレーター開発の高速ループ）：`make build-orchestrator` → `orchestrator/orchestrator --workspace workspace/orch-sample --instructions orchestrator/instructions "<ゴール>"`。**イメージ再ビルド不要**でコード変更を即検証できる。`--workspace`・`--instructions` は既存フラグ（[docs/impl/60_orchestrator.md](impl/60_orchestrator.md)）。

人間は noVNC のダッシュボード（06 §5.2）でリアルタイムに挙動を観察し、`audit.jsonl`・`plan.json`・`git log` で結果を確認する。

### 2.3 サンプルの設計要件

サンプルの「開発対象」は、検証に必要な性質を最小コストで満たすよう設計する：

- **複数の独立タスク**に分解できる（並行実行＝`max_workers` を踏む）。
- **決定論的に介入を起こせる**タスクを含む。具体的には、seed plan に **`irreversible: true` のタスク**を 1 つ置く。trigger1 は worker の判断に依存せず**ディスパッチ前に必ず発火**するため、「1 件が `waiting_human` で待つ間に peer が走り続ける」ことを再現性高く確認できる。
- 各タスクは**タスク固有の `completion`** を持つ（06 §8.1。レビュー採点の検証）。
- 成果物が**機械的に検証可能**（テスト or 明確なファイル成果）。

実体は小さなユーティリティ（例：数個の独立した純関数モジュール＋単体テスト、あるいは小さな静的サイト）とし、worker が数分で終わる規模にする。具体構成は [70_sample-project.md](impl/70_sample-project.md) で確定する。

## 3. 検証シナリオ（本改訂で直す不具合に対応）

| # | シナリオ | 手順 | 合格条件（観察点） |
|---|---|---|---|
| S1 | **介入で peer を止めない**（バグ2） | サンプルを実行。`irreversible` タスクが `waiting_human` になる | 当該タスクのみ ⏸。他 worker は走り続け、独立タスクが `done` まで進む。`[i]` で承認 → 当該タスクも完遂。`audit.jsonl` に全停止の痕跡が無い |
| S2 | **中断/再開でやり直さない**（バグ1） | 実行途中で Ctrl-C → 再度 orchestrate | 終了コード 0 でクリーン中断。再開時に `done` タスクが再ディスパッチされない（`plan.json` の `done` 保持・`audit.jsonl` の `dispatch` が重複しない）。in-flight は `--resume` で継続 |
| S3 | **完了タスクを再実行しない**（バグ1） | 一部タスク完了後に kill → 再開 | `git log` で完了タスクのコミットが二重に積まれない。完了済みの worktree/ブランチが再生成されない |
| S4 | **レビューはタスク固有 completion で採点**（MODIFICATION） | 部分タスク（責務が限定）を実行 | 別タスク責務の欠落で誤って不合格にならない。レビュー結果は構造化出力でパースされ、フォーマット違反（`review_gate_defect`）化しない |
| S5 | **複数同時介入**（バグ2 派生） | 介入を 2 件同時に発生させる | 2 件とも `intervention/open.json` に並ぶ。`[i]` でまとめて回答でき、peer は終始継続 |

各シナリオの結果は CLAUDE.md「動作確認」に従い記録し、問題があれば [docs/06_orchestration.md](06_orchestration.md) / [docs/impl/60_orchestrator.md](impl/60_orchestrator.md) に立ち返って修正する（ドキュメント先行）。レビュー結果は `docs/reviews/` に残す。

## 4. 範囲外・限界

- サンプルは**オーケストレーターの制御挙動**（並行・介入・中断/再開・ゲート）の検証が主目的であり、サンプル自体の機能網羅は目的ではない。
- 実 `claude -p` を呼ぶため**完全な決定論ではない**（worker の出力は揺れる）。決定論が要る単体ロジックは引き続き `orchestrator/*_test.go`（60 §テスト方針）で担保し、本サンプルは**実機・ユースケース確認**を担う（両者は補完関係）。
- 課金・レート上限に配慮し、サンプルは小さく保つ。CI への常時組み込みは将来検討（実 API 依存のため）。

## 5. 関連ドキュメント

- [docs/06_orchestration.md](06_orchestration.md)：検証対象の設計（介入のタスク単位化・中断再開・品質ゲート）
- [docs/impl/60_orchestrator.md](impl/60_orchestrator.md)：検証対象の実装仕様（正本）
- [docs/impl/70_sample-project.md](impl/70_sample-project.md)：サンプルサブプロジェクトと scaffold の実装仕様（正本）
- [MODIFICATION.md](MODIFICATION.md) の指摘は本改訂で 06/60 へ統合済み
