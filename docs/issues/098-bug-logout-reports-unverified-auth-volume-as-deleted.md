---
id: 098-bug-logout-reports-unverified-auth-volume-as-deleted
type: bug
origin_layer: 03
severity: 中
found: 2026-08-11
found_in: /implement task-fix-logout-zero-target-path(C-0 の隔離ハーネスで受入基準18 を確認した際に観測)
related: docs/03-impl/relations/MODULE-cli-logout.md, docs/02-design/logging.md, claude-dev, claude-dev-mac
closes_when: 消去を確認できなかった共有ボリュームが「削除した資源」に列挙されなくなり、E2E-01 手順8-18 の `--yes` 側でそれを確認できたとき
summary: logout の手順10 で消去を確認できなかったとき、同じ共有ボリュームが「削除した資源」と「削除できなかった資源」の両方に列挙される
---

# 098 消去を確認できなかった共有ボリュームが「削除した資源」にも現れる

## 事象

`claude-dev logout --yes` が手順10 で共有ボリュームの消去を確認できなかった場合
(印 `__CLAUDE_DEV_AUTH_LISTED__` が出ない = 一時コンテナを起動できていない)、
**同じ資源が `destructive_failed` と `destructive_deleted` の両方に記録される**。
結果として、認証が1バイトも消えていないのに結果表示の「削除した資源:」に
「共有ボリューム claude-dev-auth の認証情報」が現れる。

2026-08-11 に隔離ハーネス(`claude-dev` の資源名を書き換えた複製 + `IMG_CLAUDE` を
`busybox` に差し替えて一時コンテナを起動できない状態にしたもの)で観測した実出力:

```
❌ 共有ボリューム cdx-e2e-auth の消去を確認できませんでした（一時コンテナを起動できていません）。
❌ 削除できなかった資源があります。
   削除した資源:
     - 共有ボリューム cdx-e2e-auth の認証情報          ← 消えていないのに現れる
   削除できなかった / 未削除のまま残った資源:
     - 共有ボリューム cdx-e2e-auth の認証情報（消去を確認できず）
```

実行後にボリュームの中身を確認すると `.credentials.json` は残っていた
(= 「削除した資源」の記述は事実に反する)。

## 原因

`claude-dev:1150`〜`:1164`(`claude-dev-mac` の同一箇所)。印が無い経路で
`destructive_failed` を呼んだあと **`_auth_left=""` を置く**ため、直後の
`if [ -n "$_auth_left" ]` が偽になり、else 節の `destructive_deleted` に落ちる。
「残ったパスが無い」と「消去を確認できていない」の2つが同じ空文字列で表現されている。

## 何が仕様に反するか

- `docs/02-design/logging.md`「破壊的操作の出力に共通して課す制約」(`D0-env-08` 項5):
  **成功を表す文言は、列挙した削除対象がすべて消えたことを確認したときにだけ出す。**
  「削除した資源」への列挙は、その資源が消えたという表示である。
- `docs/03-impl/relations/MODULE-cli-logout.md` 手順10 は「消去を確認できなかった」として
  **失敗に数える**とだけ定めており、削除済みにも記録するとは書いていない
  (= 実装が 03 の記述を超えている。だから `origin_layer: 03`)。

`FR-env-03` 受入基準18 が禁じる「削除しました」「完了」の見出しは出ておらず、終了コードは 1 で、
失敗の列挙も出ている。したがって `D0-scope-07` の「利用者が失敗に気づけない」には**当たらない**
(気づけるが、同時に矛盾した行を読む)。severity を「高」ではなく「中」としたのはこの理由による。

## 範囲外とした理由

`task-fix-logout-zero-target-path` の変更指示は手順6(削除対象0件の経路)を対象としており、
手順10 の記録の仕方は closure に入っていない。原則8 に従い、この欠陥は本タスクで直さず起票する。
**同型の全件列挙は行っていない**(severity が「高」ではないため。原則8)。`reset` の共有ボリューム
削除は `docker volume rm -f` で器ごと消す別経路であり、この形は持たない。
