---
target: docs/README.md
change: replace
sections:
  - "# docs/ — ドキュメント体系"
deletes: []
reason: 旧3フェーズ体系の索引(存在しないスキル `/gen` `/change` と旧ディレクトリ構成を案内している)を、新4層体系の索引へ書き直す。
---

<!-- このファイルは H1 の下に H2 を持たない。したがって `sections` に H1 を挙げることが
     「ファイル全体の置き換え」を意味する(H1 とその配下すべてが対象)。 -->

# docs/ — ドキュメント体系

`00-requests/` `01-requirements/` `02-design/` `03-impl/` の4層を総称して**仕様ドキュメント**と
呼び、これが唯一の真実(SSOT)である。SSOT には**「現在のシステムの姿」だけ**を書く。計画・願望・
TODO・タスクは書かない。

変更は SSOT を直接書き換えず、`tasks/task-<slug>/new-features/` に**変更指示**として書く。
SSOT が書き換わるのは作業の最後(`/task-close`)の1回だけで、しかも完成した実装から書き換える。
運用の規範は**リポジトリルートの `CLAUDE.md`** が正である。

```
docs/
├── 00-requests/           # 要求(WHY)。人間のもの
│   ├── request.md         #   やること(RQ-*)/やらないこと/対象ユーザー/完成イメージ
│   ├── acceptances.md     #   受け入れ基準(AC-*)。利用者の言葉で書く
│   ├── terminology.md     #   用語集。全層がこれに従う
│   └── decisions/         #   決定台帳(D0-*)。決定 / 委任 / 要確認 の3区分
├── 01-requirements/       # 要件(WHAT)
│   ├── functional.md      #   機能要件(FR-*)。受け入れ基準は EARS。境界値と異常系を必ず書く
│   ├── non-functional.md  #   非機能要件(NFR-*)。6分類すべてに節を置く
│   ├── usecases.md        #   ユースケース(UC-*)。E2E シナリオの唯一の上流
│   └── system.md          #   システム・環境の要件(SR-*)
├── 02-design/             # 基本設計(HOW)
│   ├── architecture.md    #   全体構成・データの流れ・設計判断(DSN-*)
│   ├── system.md          #   ★モジュール分割定義・テスト戦略・UI設計
│   ├── relations.md       #   ★想定機能連携(PLAN-*)。03 との差分が取りこぼしの検出手段
│   ├── contracts/         #   契約(CTR-*)。03 と同一 ID
│   ├── environments.md    #   開発環境。**lint/テストの実コマンドはここが正**
│   └── logging.md         #   ログ戦略
├── 03-impl/               # 現実装の実装仕様。**コードから導出する**
│   ├── index.md           #   この層の代表(版と合格証を持つ)
│   ├── features.md        #   ★機能表。どこを1機能とみなすかの定義(人間が合意する)
│   ├── feature-graph.md   #   生成物(cluster-features.py)
│   ├── callgraphs/        #   ★ツールだけが書く。手で編集しない
│   ├── relations/         #   ★機能間連携仕様書(MODULE-*)。コードと 1:1
│   ├── contracts/         #   実装されている契約(CTR-*)
│   ├── tests/             #   受入基準 ⇄ テストの対応表
│   ├── environments/      #   開発環境の「仕組み」(イメージの作り方など)
│   └── infra/local/       #   環境ごとの「構成値」
├── histories/             # 変更の記録(追記のみ)
├── issues/                # タスク化前の課題・バグ
├── pendings.md            # 不完全でも一旦 OK としたもの
├── feedbacks/             # 人間の判断から得た気づき(1件1ファイル)
├── tasks/                 # 進行中のタスクだけ。完了時にディレクトリごと消える
└── ONBOARDING.md          # メンバー向けの説明資料
```

## どこを見ればよいか

| 知りたいこと | 見る場所 |
|---|---|
| なぜこれを作るのか / やらないこと | `00-requests/request.md` |
| 決まっていること・AI に任せてよいこと・未決のこと | `00-requests/decisions/` |
| システムが満たすべきこと(受け入れ基準つき) | `01-requirements/functional.md` |
| モジュールの一覧と責務 | `02-design/system.md`(モジュール分割定義) |
| lint・テストの実コマンド | `02-design/environments.md` |
| ある機能が何を呼び、何から呼ばれるか | `03-impl/relations/MODULE-<slug>.md` |
| これを変えると何に響くか | `python3 .claude/scripts/relations-query.py --impact <path>` |
| テストがある/無い | `03-impl/tests/index.md` |
| 既知の未対処・棚上げ | `issues/index.md` / `pendings.md` |
| 過去の変更 | `histories/` |

## 作業の進め方

1タスク=4フェーズ。人間が立ち会うのは**フェーズ1の決定シートに答える1回だけ**で、以降は
無人で進む(残件がある場合だけフェーズ末に一括で質問する)。

| フェーズ | スキル | 抜ける条件 |
|---|---|---|
| 1 宣言・決定 | `/task-new <説明>` | 影響範囲の確定と決定シートの回答 |
| 2 変更指示 | `/task-doc` → `/doc-check` | `new-features/` を 00→03 の1回の下降で書き切り、未決点ゼロで PASS |
| 3 実装 | `/implement` | lint・テストがグリーン |
| 4 反映・完了 | `/task-close` | SSOT へ反映・認証・記録し、タスクディレクトリを削除 |

その他: `/doc-status`(状態の一覧)/ `/relations`(コードから機能間連携を導出)/
`/reverse-doc`(既存実装から上流を逆生成)/ `/codex-audit`・`/codex-qa`(独立監査・独立QA)/
`/kit-improve`(この仕組み自体の改善)。

**このディレクトリのルール・記法の正は `CLAUDE.md` と `.claude/directions/` である。**
ここに二重に書かない。
