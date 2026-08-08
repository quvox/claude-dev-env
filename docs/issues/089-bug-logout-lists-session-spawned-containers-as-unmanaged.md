---
id: 089-bug-logout-lists-session-spawned-containers-as-unmanaged
type: bug
origin_layer: 03
severity: 中
found: 2026-08-07
found_in: /doc-check ssot task-stop-session-spawned-containers(独立レビュー(サブエージェント)の A3 / C12 照合)
related: MODULE-cli-logout, CTR-cli-container, FR-env-03, DSN-env-04, claude-dev, claude-dev-mac, docs/issues/055
pattern: exclusion-rule-declared-for-two-commands-implemented-in-one
pattern_survey: "`02-design/contracts/cli-container.md`「残したものをどう列挙するか」が定める4つの除外(管理ラベル付き / `fwd-*` / docker-proxy / `claude-dev.role=spawned`)を、`logout`(`claude-dev:968`〜`:980`)と `reset`(`claude-dev:2086`〜`:2093`)の実装で1つずつ照合した。4つ目の `spawned` 除外を持たないのは `logout` だけ(1件)。他の3つは両方が持つ"
summary: 02 が logout と reset の双方に課した「セッション由来の資源を除外して列挙する」を logout だけが実装しておらず、spawned コンテナを「管理ラベルを持たない」と事実に反して表示する
---

# 089 `logout` がセッション由来のコンテナを「管理ラベルを持たない」と誤表示する

## 事象

`docs/02-design/contracts/cli-container.md`「残したものをどう列挙するか」は
**4つの除外はいずれも `logout` と `reset` の双方に掛かる**と定め、
「`logout` はセッション由来の資源を削除しない(規則 D を使わない)が、
**削除しないことと『ラベルを持たない』と表示することは別である** — 表示すると事実に反する」
と明記している。

実装では `reset` だけがこの除外を持つ。

- `reset`(`claude-dev:2091`): `for _t in "${_rc_spawned_c[@]}"; do [ "$_t" = "$_c" ] && _known=1; done`
- `logout`(`claude-dev:968`〜`:980` / `claude-dev-mac` の同一箇所): 除外は管理ラベル付きの
  `_targets` だけで、`claude-dev.role=spawned` を見ていない。

`docs/03-impl/relations/MODULE-cli-logout.md` は `spawned` を1度も含まず、
この除外を記述も否定もしていない。

再現手順:

1. Claude コンテナの中から `docker run --network claude-dev-net ...` でコンテナを作る
   (docker-proxy が `claude-dev.role=spawned` を付ける)。
2. `claude-dev logout` を実行する。
3. そのコンテナが「管理ラベルを持たない次のコンテナは削除しません(本変更より前に起動した
   可能性があります)」の列に現れることを確認する。**本変更より後に作られた資源なので事実に反する。**

## 影響

利用者は「古いコンテナが残っている」と読み違え、手で消そうとする(消すべきはセッション由来の
資源であって、消し方も回収経路も違う)。02 が名指しで禁じた状態がそのまま出るので severity は「中」。
`docs/issues/055`(受入基準17 の 01 ⇄ 02 の食い違い)と同じ表示経路にある。

## 原因の見当

`DSN-env-04` の導入で4つ目の除外が 02 に増えたとき、本タスクの影響範囲が
`MOD-cli-stop` / `MOD-cli-reset` / `MOD-docker-proxy` の3つだったため、
`MOD-cli-logout` の実装と 03 が更新されなかった(推測ではなく、影響範囲の表がそう記録している)。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| `logout` の列挙からの `spawned` 除外 | 実装にも `MODULE-cli-logout` にも無い | 02 の「4つの除外はいずれも `logout` と `reset` の双方に掛かる」が明示 | **設計が正**(実装と 03 の取りこぼし) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `logout` 側に `reset`(`claude-dev:2091`)と同形の除外を入れ、`MODULE-cli-logout` の処理の流れと異常系に1行足す | `claude-dev` / `claude-dev-mac` 各1箇所 + `MODULE-cli-logout.md` + `tests/cli-logout.md`。`MOD-cli-logout` を影響範囲に持つ新タスクが要る |
| B | 02 を「`logout` はこの除外を持たない」へ緩める | 02 が自分で「表示すると事実に反する」と書いているので、緩めるには `D0-env-08` 項8 まで戻る |

推奨は A。**本タスクでは直さない** — `MOD-cli-logout` は影響範囲の外で、
フェーズ1 で固定した境界を越えるため(CLAUDE.md §3「フェーズ1 が済んだら境界は固定」)。

## 経緯

- 2026-08-07 起票。`/doc-check ssot task-stop-session-spawned-containers` の独立レビュー
  (`lens: subagent`)が検出し、`claude-dev:968`〜`:980` と `claude-dev:2086`〜`:2093` の
  差で事実を確認した。
