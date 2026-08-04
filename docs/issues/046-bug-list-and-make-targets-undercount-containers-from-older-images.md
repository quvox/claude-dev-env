---
id: 046-bug-list-and-make-targets-undercount-containers-from-older-images
type: bug
severity: 中
found: 2026-08-04
found_in: task-fix-destructive-scope のフェーズ2(docs/issues/045 と同根の箇所を 03-impl 全体へ掃引した際に確定)
related: MODULE-cli-list, MODULE-makefile-status, MODULE-makefile-clean, FR-env-01, docs/issues/045
summary: list / make status / make clean が `--filter ancestor` でコンテナを列挙するため、イメージを再取得・再ビルドした後は「稼働中なのに一覧に出ない」セッションが生じる(利用者は欠落に気づけない)
---

## 事象

`docs/issues/045` は `stop` の遊休判定が `--filter ancestor=<イメージ>` を使うため、イメージ更新前に
起動したコンテナを数え落とすという内容である。**同じ書き方が他に3箇所ある。**

| 箇所 | 実装 | 数え落としたときに起きること |
|---|---|---|
| `MODULE-cli-list`(`claude-dev list`) | `docker ps` を `--filter ancestor=claude-dev-claude` / `--filter ancestor=claude-dev-claude-vnc` で絞る(`MODULE-cli-list.md` の処理の流れ1) | **稼働中のセッションが一覧に出ない。** noVNC URL もフォワード状況も表示されないので、利用者はそのセッションへ到達する手段を一覧から得られない |
| `MODULE-makefile-status`(`make status`) | 同じ `ancestor` フィルタで実行中セッションを表示する(処理の流れ2) | 同上 |
| `MODULE-makefile-clean`(`make clean`) | `ancestor` フィルタで全 Claude コンテナ(停止中を含む)を削除する(処理の流れ2) | **削除されずに残る**(数え落としは削除しない方向に外れるので害は小さいが、`make clean` が「全部消えた」と読める表示をする) |

`docker ps --filter ancestor=<名前>` は**その名前が今指しているイメージ ID から作られたコンテナ**
にしか一致しない。`make upgrade` / `claude-dev pull` / イメージの再ビルドで `latest` が別の
イメージ ID を指すと、それ以前に起動したコンテナはすべて一致しなくなる。

再現手順:

1. 任意のディレクトリで `claude-dev start` する。`claude-dev list` に出ることを確認する。
2. `make upgrade`(またはイメージの再ビルド)を実行し、`latest` が別のイメージ ID を指す状態にする。
   `docker inspect -f '{{.Image}}' <コンテナ名>` と `docker images -q claude-dev-claude-vnc` が
   食い違うことで確認できる。
3. `claude-dev list` を実行する。**手順1 のセッションが一覧に出ない**ことを確認する
   (`docker ps` には出ている)。`make status` でも同じことを確認する。

## 影響

- **`claude-dev list` の一覧が不完全になる。** `FR-env-01` 受入基準5「WHEN `claude-dev list` を
  実行したとき、システムは実行中セッションの一覧(noVNC URL とフォワード状況を含む)を表示しなければ
  ならない」を満たさない(「実行中セッション」の一部が欠ける)。
- **利用者は欠落に気づけない。** 出力は正常時と同じ形で、件数が少ないだけである。終了コードも 0。
  `D0-scope-07` の観測点の定義における「利用者が失敗に気づけない」に当たる。
- 実害の例: 別のディレクトリで作業していたセッションを `list` から見つけられず、`stop` の対象名も
  分からないため、`docker ps` を直接叩くまで到達できない。
- `make clean` は削除漏れなのでデータは失われない。表示と実態が食い違うだけである。

severity を「中」とした根拠: データは壊れず、`docker ps` で確認すれば回復できる。一方で
**要件(`FR-env-01` 受入基準5)との不一致**であり、**失敗が静か**である。

## 原因の見当

**推測ではなく `MODULE-cli-list` の「実装上の判断」1 に明記されている**: 「列挙条件を
`ancestor`(イメージ由来)にする。コンテナ名の接頭辞では判定できない(コンテナ名 = ディレクトリ名の
ため)」(`D0-scope-02`)。つまり**当時は所有権を表す印が無く、イメージしか手段が無かった**。
`ancestor` がタグではなくイメージ ID で照合するという性質と、`latest` が動く運用が噛み合っていない。

## 正はどちらか

**実装が誤り。** `FR-env-01` 受入基準5 は「実行中セッションの一覧」を求めており、どちらが正かの
裁定は要らない。数え方の欠陥である。

## 対処案

`task-fix-destructive-scope` が `D0-env-08` / `D0-env-10` で **Claude コンテナへの管理ラベル**
(`claude-dev.managed=1` / `claude-dev.role=claude` / `claude-dev.project-dir=<絶対パス>`)を
導入するため、**その印を使えば `ancestor` を置き換えられる**。

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | 列挙条件を `--filter label=claude-dev.managed=1` に変える。**本変更より前に起動した既存コンテナはラベルを持たないため、移行期は `ancestor` との論理和にする**(列挙は「多く出す」方向に外すのが安全) | `MODULE-cli-list` / `MODULE-makefile-status` / `MODULE-makefile-clean`、`claude-dev` / `claude-dev-mac` / `Makefile`、`tests/cli-list.md` / `tests/makefile.md` |
| B | 列挙条件を `claude-dev-net` への接続に変える(`stop` の遊休判定と同じ手段。ラベルに依存しない) | 同上。ただし `login` の一時コンテナや `fwd-*` を除外する条件が要る |
| C | `ancestor` に `docker images -q <名前>` の全イメージ ID を並べる | 同上。削除済みイメージから作られたコンテナは依然取りこぼす |

推奨は **A**(`task-fix-destructive-scope` が導入する印をそのまま使え、移行期も論理和で守れる)。
`make clean` は破壊的操作なので、あわせて `D0-env-08`(対象の限定・確認)の対象に含めるかを
判断する必要がある(**現在 `make clean` は確認なしに全 Claude コンテナを削除する**)。

## 経緯

- 2026-08-04 起票(`task-fix-destructive-scope` のフェーズ2)。`docs/issues/045`(`stop` の遊休判定)を
  直す設計を書く過程で、同じ `--filter ancestor` の書き方が他に3箇所あることを
  `docs/03-impl/relations/` の走査で確定した。`045` の「事象」は `stop` の遊休判定に限られており
  **本件を含まない**ため、`D0-scope-07` の起票の閾値 (a)(要件との不一致 / 利用者が失敗に
  気づけない)・(b)(既存 issue で説明できない)に従って別 issue として起票した。
  **本タスクの範囲外なので修正しない**(本タスクは `stop` / `logout` / `reset` に限る)。
