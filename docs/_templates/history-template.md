---
slug: <変更slug>               # ファイル名 YYYY-MM-DD-<slug>.md の slug 部分
layer: history
title: <変更の一言タイトル>
date: YYYY-MM-DD
trigger: <変更のきっかけ>      # 例: 要件変更(顧客要望) / バグ起因の仕様修正 / リファクタリング / 逆生成
origin_layer: requirements     # 変更の起点階層: request | requirements | design | impl | steering
affected:                      # この変更で更新した全ドキュメント(更新のたびに追記)
  - doc: docs/01-requirements/core.md
    version: 1.0 -> 1.1
  - doc: docs/02-design/system.md
    version: 1.1 -> 1.2
  - doc: docs/03-impl/auth.md
    version: 1.2 -> 1.3
  - doc: docs/_steering/tech.md          # steeringも対象(versionを持たないので change で一言)
    change: 横断的設計判断にセッション管理方式を追加
---

# 変更記録:<タイトル>

<!--
histories は「ドキュメントの変更履歴」である。対象は docs/ の4階層(00〜03)すべてと
docs/_steering/(product/tech/structure)。それ以外のもの(タスク・作業計画・進捗)は書かない
(タスクは docs/tasks/ の管轄)。
1つの変更(1つの理由による一連のドキュメント更新)につき1エントリを
docs/histories/YYYY-MM-DD-<slug>.md に置く(変更はモジュールをまたぎうるため、フラットに
時系列で並べる。どのドキュメントに関わる変更かは affected が示す)。
追記専用で、確定したエントリは以後書き換えない(訂正は新エントリで行う)。
初版作成(1.0.0)とPATCHのみの変更(軽微修正)はエントリ不要。MINOR以上の変更から記録する。
-->

## 変更理由・背景

(なぜこの変更が必要になったか。要望・不具合・判断の経緯)

## 変更内容の要約

(各ドキュメントに加えた変更の要約。「01の要件3に受け入れ基準を2つ追加、02のAuthServiceにMFA検証を追加、03を実装結果に同期」)
