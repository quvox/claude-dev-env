---
slug: <変更slug>               # ファイル名 YYYY-MM-DD-<slug>.md の slug 部分
layer: history
title: <変更の一言タイトル>
date: YYYY-MM-DD
trigger: <変更のきっかけ>      # 例: 要件変更(顧客要望) / バグ起因の仕様修正 / リファクタリング / 逆生成
origin_layer: requirements     # 変更の起点階層: request | requirements | design | impl | steering
affected:                      # この変更で更新した全ドキュメント(更新のたびに追記)
                               # change は全ドキュメント必須。**どの節・要件・契約を変えたか**まで
                               # 具体的に書く(/doc-check の差分検証がこの一行を読んで、下流に
                               # 影響が及ぶかを判定する。「見直した」等の曖昧な一行は、下流の
                               # 全面再検証を招くコストとして跳ね返る)
  - doc: docs/01-requirements/core.md
    version: 1.0.0 -> 1.1.0
    change: 要件3(ログイン)にMFAの受け入れ基準2件を追加。他の要件と非機能要件は変更なし
  - doc: docs/02-design/system.md
    version: 1.1.0 -> 1.2.0
    change: AuthService契約にverifyMfa()を追加、モジュール分割定義は変更なし
  - doc: docs/03-impl/auth.md
    version: 1.2.0 -> 1.3.0
    change: MFA検証の実装詳細とテスト対応表2行を追加
  - doc: docs/_steering/tech.md          # steeringも対象(versionを持たないので change のみ)
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
追記専用で、確定したエントリは以後書き換えない(訂正は新エントリで行う)。ただし**同じ変更理由の
続きとして affected に行を追加すること(および既存行のversion遷移を最終値に更新すること)は「追記」に
含まれる** — 実装フェーズで03-implを同期した結果などは、新エントリを作らずこのエントリのaffectedに
足す(1変更理由=1エントリを保つため。理由が別なら新エントリ)。
初版作成(1.0.0)とPATCHのみの変更(軽微修正)はエントリ不要。MINOR以上の変更から記録する。
-->

## 変更理由・背景

(なぜこの変更が必要になったか。要望・不具合・判断の経緯)

## 変更内容の要約

(各ドキュメントに加えた変更の要約。「01の要件3に受け入れ基準を2つ追加、02のAuthServiceにMFA検証を追加、03を実装結果に同期」)
