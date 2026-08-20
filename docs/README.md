# docs/ — ドキュメント体系

`00-requests/` `01-requirements/` `02-design/` `03-impl/` の4層を総称して**仕様ドキュメント**と
呼び、これが唯一の真実(SSOT)である。SSOT には**「現在のシステムの姿」だけ**を書く。計画・願望・
TODO・タスクは書かない。

変更は `/build` が**その1タスクの影響範囲(closure)の中で SSOT を直接書き換える**。別紙の
変更指示は作らない。フローの途中では SSOT が実装より先に進むことがあるが、**フローを抜けるときには
そのタスクが触った文書とコードが一致している**(タスク内整合確認がそれを保証する)。
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
├── build-records/         # 1タスク=1ファイル。closure・主張・進捗と検証の状態
├── histories/             # 変更の記録(追記のみ)
├── issues/                # タスク化前の課題・バグ
├── pendings.md            # 不完全でも一旦 OK としたもの(棚上げ + 残務)
├── reverification.md      # 生成物(doc-health.py)。再検証候補と鮮度確認の候補
├── sheets/                # 決定シート(朝のシートを含む)。答えられたら消える
├── feedbacks/             # 人間の判断から得た気づき(1件1ファイル)
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

フェーズ方式は廃止した。作業は**4つの独立したフロー**として、いつでも何度でも走る。品質を守るのは
**収束契約** — デプロイの時点で、すべての検証が現在の状態に対して green であること
(`python3 .claude/scripts/stamps.py check`)。デプロイの間の状態は正当に「収束中」である。

| フロー | スキル | 何をする | 人間の関与 |
|---|---|---|---|
| F1 構築 | `/build <説明>` | closure 確定 → 決定シート → SSOT を直接書く → 実装 → タスク内整合確認 → 構築記録 | 決定シート最大2回(問いがゼロなら不在) |
| F2 文書整合 | `/verify-docs [all]` | SSOT 内部の整合を独立コンテキストで検査し、合格証を書く | 不在 |
| F3 実装整合 | `/verify-impl [all]` | コード ⇄ 03-impl ⇄ 02 の一致。コールグラフ再生成と事実差分の自動修正 | 不在 |
| F4 試験 | `/verify-tests [scope]` | 全件テスト・受け入れ基準の照合・探索的ブラウザQA | 不在 |

F2〜F4 は人間に問わない。指摘は**自動修正 / キュー(issues・残務)/ 朝のシート**の3チャネルへ出る。
1タスクの進行状況は `build-records/<slug>.md` が持ち、`building` → `awaiting-verify` → `verified`
と動く。

その他: `/browser-qa`(探索的な独立QA)/ `/relations`(コードから機能間連携を導出)/
`/retrofit`(既存実装から上流を逆生成)/ `/setup`(骨格の作成)/ `/mission`(中央エージェントによる
配車)/ `/kit-improve`(この仕組み自体の改善)。

**このディレクトリのルール・記法の正は `CLAUDE.md` と `.claude/directions/` である。**
ここに二重に書かない。
