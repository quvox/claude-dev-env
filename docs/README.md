# docs/ — ドキュメント体系

直下の番号つき4階層(00〜03)=**仕様ドキュメント**は、常に「システムの現在あるべき姿」を表す
Single Source of Truth。変更時はインプレース更新し、経緯は `histories/`、作業計画は `tasks/` に置く
(仕様ドキュメントには書かない)。

**階層ごとに粒度が異なる。分割単位(モジュール)は設計の成果物である。**

```
docs/
├── 00-requests/           # 要求パッケージ(WHY+判断台帳): request.md(人間の言葉)必須
│   ├── request.md         #  + decisions.md(決定/委任/要確認)必須
│   └── decisions.md       #  + glossary.md / acceptance.md / examples/(推奨・任意)
├── 01-requirements/       # 要件(WHAT): 最初は core.md 1つ。大きければ業務領域で分割
│   └── core.md
├── 02-design/
│   ├── system.md          # 全体設計。★モジュール分割はここで定義する
│   └── <module>.md        # 大きいモジュールの詳細設計(任意)
├── 03-impl/
│   ├── <module>.md        # 実装説明書: モジュールごと。分割定義にないものは作らない
│   └── e2e.md             # E2Eテスト実装説明書(唯一の標準例外: 02のE2Eシナリオ一覧に従う)
├── histories/             # ドキュメント変更履歴(追記専用)
├── tasks/                 # AI作業用タスク(進行中のみ存在)
├── _steering/             # プロジェクト共通ルール(_付き=仕様ドキュメント本体ではなく前提・ひな形)
├── _templates/            # 各ドキュメントのテンプレート
├── WORKFLOW-GUIDE.md      # 運用ガイド(人間向け)
└── ONBOARDING.md          # メンバー向け説明資料(スライド原稿)
```

- 新規開発: 00-requests/ を人間が用意する(上流の要求定義ファクトリー製が理想)→ `/gen` を
  繰り返す(01→02で分割が決まる→03、各ゲートで人間が承認)→ `/implement`
- 変更: `/change <変更内容>`(起点階層をAIが判定)
- 未整備の既存コード: `/reverse-doc <module>`
- 進捗確認: `/doc-status`
