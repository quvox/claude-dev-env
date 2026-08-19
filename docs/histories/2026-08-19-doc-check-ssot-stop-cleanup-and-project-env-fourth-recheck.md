---
id: 2026-08-19-doc-check-ssot-stop-cleanup-and-project-env-fourth-recheck
date: 2026-08-19
task: task-stop-cleanup-and-project-env(フェーズ4 の `/doc-check ssot` 4回目。タスクは未完了のまま)
lane: critical
origin_layer: 03
issue: なし(新規の起票なし)
summary: 3回目の後のコード修正が生んだ +3 / +6 行のずれで腐ったコード引用 76 トークンを closure の6文書で取り直し、closure 外に残る 190 トークンを実測して既存の残務行の在庫を事実へ直した
---

# 2026-08-19 `/doc-check ssot task-stop-cleanup-and-project-env`(同日4回目・増分再実行)

## 変更理由

### R-01 3回目の検証の後にコードが動き、その下流の引用が腐った

- 起点層・根拠: 原則2(コード ⇄ 03-impl は完全に一致する)。
- 変更が必要になった条件: コミット `0b26b56` が `claude-dev` / `claude-dev-mac` の**2箇所**を
  直した(`load_project_env_file` の判定を `[ ! -f ]` → `[ ! -r ]` / ホスト設定の取り込みを
  `|| _overlay=""` で握る)。どちらも 1 行を 4 行に置き換えたため、
  **`claude-dev` は 165 行目より下が +3、1521 行目より下が +6**(`claude-dev-mac` は 164 / 1596 が境)
  ずれた。**同じコミットが 03 の記述も直しているが、その引用は「コミット直前のコード」に
  当てた値であり、コミット自身が加えた行を差し引いていない** — 確定と同時に偽になった。
- 増分の判定: `git log` と `git show 0b26b56` で、3回目の検証以降に動いたのが上記2ハンクと
  `docs/03-impl/index.md` / `MODULE-cli-start.md` / `docs/issues/106`(新規)/ `docs/issues/index.md` /
  `docs/03-impl/callgraphs/index.md` だけであることを確認し、**A〜E をその差分と下流に絞って**
  再実行した(`/doc-check` SKILL.md §0)。00・01・02 と `03-impl/tests/*.md` は1バイトも
  動いておらず、合格証は版が一致したまま有効なので再検証していない(原則6)。

## 変更内容の要約

- **コード引用を実コードで取り直した — 76 トークン / 6 文書。** 内訳:
  `MODULE-cli-start` 29 / `MODULE-cli-common-spawned-resources` 16 / `MODULE-cli-reset` 11 /
  `MODULE-cli-common-write-project-ssh-keys` 8 / `MODULE-cli-stop` 7 / `03-impl/index.md` 4。
  **旧版のコードと現行コードの行対応を `difflib` で機械的に作り、置換後に全 76 件を
  `sed` で実コードに当てて内容一致を確認した**(すべて `path:line` の付け替えのみ。PATCH)。
- **closure の外に残っているずれを実測した — 10 文書 190 トークン。**
  `contracts/cli-container.md`(87)/ `contracts/docker-api.md`(38)/
  `MODULE-cli-common-compose-project-name`(18)/ `MODULE-cli-common-destructive`(12)/
  `features.md`(9)/ `MODULE-cli-logout`(8)/ `MODULE-cli-common-net-other-running-containers`(7)/
  `contracts/entrypoint-firewall.md`(6)/ `MODULE-cli-common-container-project-dir`(4)/
  `MODULE-cli-common-lock`(1)。**これは本増分が生んだものではなく、本タスクのフェーズ3 の実装
  (`claude-dev` が +309 行)で腐ったまま3回の検証が触らなかった分である。**
  `docs/pendings.md` の残務がこの型を既に持っているので**新しい issue も新しい残務行も作らず**
  (`issues-pendings.md` §2.1 の重複キー)、**その行の在庫が偽になっていたのを実測値へ差し替えた** —
  「closure 内の3件は取り直した」と書かれていた `contracts/cli-container.md` と
  `MODULE-cli-logout` は取り直されていない。
- **`docs/pendings.md` の程度語の残務行の引用 `:264` を `:266` へ直した**(独立レビューの指摘)。
  同じコミットが `MODULE-cli-start.md` に行を足したことによる2行のずれである。
- 畳んだ残務1行を落とした(`docs/03-impl/contracts/docker-api.md` の `validateExecCreate` の
  引用ずれ。上のコード引用ずれの行が件数つきで持つようになったため。残務は 38 行 → 37 行)。
- **コードは1バイトも変更していない。**

## 更新したドキュメント

| 理由ID | ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/03-impl/index.md | 1.29.0 → **1.29.1** | `help\|*)` の引用 `:2598`・`:2640` → `:2604`・`:2646`(2箇所ずつ) |
| R-01 | docs/03-impl/relations/MODULE-cli-start.md | (版を持たない) | コード引用 29 トークン |
| R-01 | docs/03-impl/relations/MODULE-cli-common-spawned-resources.md | (版を持たない) | コード引用 16 トークン |
| R-01 | docs/03-impl/relations/MODULE-cli-reset.md | (版を持たない) | コード引用 11 トークン |
| R-01 | docs/03-impl/relations/MODULE-cli-common-write-project-ssh-keys.md | (版を持たない) | コード引用 8 トークン |
| R-01 | docs/03-impl/relations/MODULE-cli-stop.md | (版を持たない) | コード引用 7 トークン |
| R-01 | docs/pendings.md | — | 残務行の在庫を実測値へ / 程度語の行の引用を `:266` へ / 畳んだ1行を削除 |

**合格証を発行し直していない 19 文書**(00・01・02 の全部と `03-impl/tests/*.md`): この再実行では
1バイトも動いておらず、`version` と `verified.version` が一致したまま有効である(原則6)。

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| — | なし | `/doc-check` はコードを変更しない | - |

## 実施した移行

なし

### ロールバック・復旧記録

| 理由ID | 不可逆点 | 切り戻し可能な条件・期限 | 切り戻し手順 / forward-fix のみの理由と復旧手順 | 復元元 | 確認日 | 復旧確認コマンド・結果 |
|---|---|---|---|---|---|---|
| R-01 | なし(ドキュメントの編集だけで、外部副作用も公開契約の変更もデータの書き換えも無い) | 期限なし | `git checkout -- docs/` で全量を戻せる | git(作業ツリーは直前のコミット `0b26b56` から追跡可能) | 2026-08-19 | `git status --porcelain` → 変更は `docs/` 配下 7 ファイルのみ。`claude-dev` / `claude-dev-mac` / `docker-proxy/` に差分なし |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | MODULE-cli-start / -stop / -reset / -common-spawned-resources / -common-write-project-ssh-keys | 本文のコード引用のみ(`callers` / `callees` / `contracts` は変更なし) |
| 変化なし | 他 56 本 | 61 本のまま(`check-relations.py` 合格) |

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| closure 外の 190 トークンを本実行で直すか | **直さず、既存の残務行の在庫を実測値へ直すだけにする** | この場で 10 文書すべてを取り直す | 本増分(コミット `0b26b56`)が生んだずれではなく、3回の検証が触らなかった既存の腐りである。1件ずつ意味を当て直す必要があり(機械的な一律補正が成立しない区間を含む)、4回目の検証で 190 トークンを書き換えるのは CLAUDE.md §3 の健全性シグナル(製品コードの割合)に正面から反する。**崩れる条件**: これらの文書のいずれかが closure に入るタスクが始まったとき(そのタスクの同じ降下で直す) |
| 取り直しの機械化 | **旧版と現行版の行対応を `difflib` で作り、置換後に全件を実コードへ当て直して検証する** | 一律 `+3` / `+6` の加算 | 2つのハンクの境界で加算幅が変わるうえ、境界の行そのものは置換されているので一律加算では当たらない。**崩れる条件**: コードの変更が行の移動ではなく再配置を含むとき(そのときは対応が一意に決まらないので1件ずつ意味で当てる) |
| 独立レビューのレンズ | **Codex が 900 秒で時間切れになったので、同じプロンプトを読み取り専用サブエージェントへ回した** | Codex を再実行する | 環境の失敗ではなく**依頼の範囲が予算を超えた**ためで、同じ依頼を送り直しても同じ結果になる(`/doc-check` §0.5「同じ依頼を二度送らない」)。**崩れる条件**: レンズへ渡す対象集合を1文書単位まで絞れるとき |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 知見 | 今回限り(理由: 検証手順の気づきであり、製品の決定にはならない) | **同じコミットでコードと 03 を同時に直すと、03 に書く行番号は「そのコミットの後」の値でなければならない。** 3回目の追記も本記録が直した6文書も、例外なく「コミット直前の値」を書いていた。**取り直しは編集の後に、確定したコードへ当て直して確認する。** |
| 新規 issue | なし | 実装欠陥は検出していない(コードは前回のコミットで直っている) |
| 残務 | docs/pendings.md | **新規行なし。** 既存のコード引用ずれの行の在庫を実測値へ、程度語の行の引用を `:266` へ、畳んだ1行を削除(38 行 → 37 行) |
| 鮮度の報告 | 本記録 | `P-005` は未発火。**`P-006` の3つ目の発火条件(「`reset` のセッション由来資源の削除で不具合が観測されたとき」)は 2026-08-19 の1回目の検証で発火しており、まだ人間の裁定を得ていない**(専有ホストが無く required な手順を実行できない)。新しい issue にも残務にもしていない(`issues-pendings.md` §8) |
| 解消した issue | なし | `002` と `092` は本タスクの実装で解消済みだがファイルは残っている(削除は `/task-close` の裁定) |
