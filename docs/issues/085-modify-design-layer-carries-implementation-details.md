---
id: 085-modify-design-layer-carries-implementation-details
type: modify
severity: 中
found: 2026-08-07
found_in: 階層の点検(人間の指示、2026-08-07)。独立レビュー(サブエージェント)による 02-design 全文の精読
related: docs/02-design/contracts/cli-container.md, docs/02-design/contracts/cli-orchestrator.md, docs/02-design/relations.md, docs/02-design/system.md, docs/02-design/logging.md, docs/03-impl/contracts/cli-container.md, docs/03-impl/relations/MODULE-entrypoint-claude.md, docs/03-impl/features.md, .claude/directions/02-design.md, .claude/directions/03-impl.md
pattern: design-layer-carries-implementation-details
pattern_survey: docs/02-design/ の全 11 ファイル(architecture.md / system.md / relations.md / logging.md / environments.md / contracts/ 5件)を独立レビューが全文精読し、24 件。うち 13 件は task-stop-session-spawned-containers が置き換える節の中にあり、同タスクの変更指示で移した。**残るのは 11 件**で、いずれもそのタスクが触らない節にある。あわせて 01 側の同型は docs/issues/083、03 側(tests/relations/infra の置き場違い)は同タスクの変更指示で解消済み
summary: 02-design の11箇所が実装のシンボル名・実行順序・出力文言・03 の実数を持っており、実装が動くと 02 が黙って古くなる
---

# 085 設計(02)が実装の細部を持っている

## 症状

`.claude/directions/02-design.md` は 02 を「**合意**」の層と定め、
`.claude/directions/03-impl.md` は 03 を「**コードの鏡**」と定める。
`docs/02-design/` の **11 箇所**がこの線を越えており、**実装が変わると 02 が黙って古くなる**。

| # | 場所 | 原文の該当部分 | どの層のものか |
|---|---|---|---|
| 1 | `docs/02-design/contracts/cli-container.md:393`(排他(ロックキー)) | 「`start` の docker-proxy 作成(`ensure_docker_proxy_container`)と競合して」 | 03(シェル関数名) |
| 2 | 同 `:397` | 「**イメージのビルド**(`require_setup`。…)」 | 03(同上) |
| 3 | 同 `:399` | 「**ネットワーク `claude-dev-net` と共有ボリューム3本の作成**(`ensure_infrastructure`)」 | 03(資源の固定名は 02 でよいが、作る関数の名前は 03) |
| 4 | 同 `:406-407` | 「`start` / `login` / `login-codex` がこの2つをロックの取得より前に置くのはこの理由による(各機能の「実装上の判断」)」 | 03(実行順序) |
| 5 | `docs/02-design/relations.md:143-144`(`PLAN-entrypoint-claude`) | 「UID/GID 追従 → 認証コピー → 既定設定の補完 → ファイアウォール → VNC/Chrome → tmux の順に進む」 | 03(6段の実行順序。`MODULE-entrypoint-claude` が同じ流れを 20 手順で持つ) |
| 6 | `docs/02-design/relations.md:176`(`PLAN-cli-common-*`) | 「循環が無いことは `relations-query.py --health` の循環検査が担保する」 | 03 / `environments.md`(ツール名と引数。**`environments.md` の検査コマンド表にこの行は無い**) |
| 7 | `docs/02-design/system.md:514`(画面ごとの項目と状態) | 「受理できない文字を含む場合は**何も削除せず**理由を表示して終了コード 1 で終わる」 | 01(`FR-env-01-18` の文面の書き直し) |
| 8 | 同 `:521-525` | 破壊的操作の4状態(確認 / 中止 / 一部失敗 / 残した資源)で何を表示するかの全文 | 01(`FR-env-03-14` / `-15` / `-17` / `-18` の書き直し) |
| 9 | 同 `:527-530` | 「保持している操作の名前とプロセス ID と再実行の方法を表示し、終了コード 1 で終わる」 | 01(`FR-env-01-16` の書き直し) |
| 10 | `docs/02-design/contracts/cli-orchestrator.md:79` / `:81-83` | 「実装側で DEPRECATED と明示」/「**製品コードから一度も参照されておらず**」 | 03(コードを読んで初めて言える事実) |
| 11 | 同 `:105-110` | macOS の未適合の**内容**の記述(「生存判定を持たず、…もう1つ起動しうる」) | 03(自ら「実装側の事実は 03 が持つ」と書いている) |

## なぜ問題か

**02 が実装の事実を写すと、02 ⇄ 03 の比較が意味を失う。** この仕組みの中心は
「02 が期待を書き、03 が事実を書き、突き合わせて欠落を見つける」ことなので、02 が事実側を
持つとその差が消える(#10・#11 はまさに 02 が 03 の事実を先取りしている)。
また #1〜#4 の関数名と #5 の実行順序は、**リファクタリングで無言に古くなる**。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| ロック解除・ソケット待ちなどの手段 | `03-impl/contracts/cli-container.md` と `MODULE-*` が `path:line` つきで持つ | 02 が関数名と値を先に書いている | **要件・設計が正**(02 から落として 03 を残す) |
| macOS の未適合 | `03-impl/contracts/cli-orchestrator.md`「設計との差異」が持つ | 02 が同じ内容を書いている | **要件・設計が正**(02 は方針だけ持つ) |

**実装の誤りではない。** コードは1行も動かない。

## どう直すか(案)

1. #1〜#4・#5・#6 は**関数名・順序・ツール名を落として指し先に replace する**(移し先はすべて実在
   することを確認済み。#6 だけは `environments.md` の検査コマンド表に行を足す必要がある)。
2. #7〜#9 は **UI 設計節を「項目と状態の名前」までに戻す**。表示の内容は `logging.md`、
   終了コードは 01 の受入基準が正である。
3. #10・#11 は **02 から事実の記述を落とし、方針(「Linux 実装を正とし macOS を追随させる」)
   だけを残す**。事実は既に 03 にある。

**いずれも 00/01 の意味を変えないので決定シートは要らないが、`docs/02-design/` の版が動くので
`/doc-check` が要る。** タスクとして起こすか、それぞれの節を触るタスクのついでに直すかは人間が決める。

## 影響範囲

- `docs/02-design/` の5ファイル。**契約の意味は変わらない**(落とすのは実現手段の記述だけ)
- `docs/03-impl/` は変更なし(移し先に事実が既に在る)
- 例外は #6 で、`docs/02-design/environments.md` の検査コマンド表に1行足す必要がある
- 同型の 01 側は `docs/issues/083`、`03-impl/tests/strategy.md` の `go test -cover ./...` が
  `environments.md` に無い件も #6 と同じ形(**02 の実コマンド表の取りこぼし**)
