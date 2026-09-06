---
slug: docs-ux-migrate
state: awaiting-verify
critical: false
origin: derived
issue: なし
started: 2026-09-06T09:12:00+09:00
updated: 2026-09-06T09:41:00+09:00
commit: ac23a0f94d88cdaf2cfa48001e9484a600f62add
summary: 移行 2026-08-28-docs-ux を当て、02-design/system.md の UI設計節の中身を docs/ux/ へ引っ越す
---

# docs-ux-migrate — UI/UX の記述を 02 から docs/ux/(UX 文書)へ移す

## 目的・やらないこと

- 目的: `.claude/migrations/2026-08-28-docs-ux.md` の手順どおりに、`docs/02-design/system.md` の
  UI設計節が持つ画面一覧・画面ごとの項目と状態・デザイン方針を `docs/ux/` へ移し、02 は
  UI の有無の宣言だけに薄くする。`docs/README.md` と 03 からの参照を追随させる。
- やらないこと: 実装コードを1バイトも触らない(振る舞いを変えない)。全画面ぶんの
  `screens/` を実装から書き起こさない。01 の条項 ID の一括付与をしない。
  `reviews/` に移行前の経緯を遡って書き起こさない(移行手順「移行時にしないこと」)。
  verify 系フローを回さない(作業指示8 の申し送り)。

## 影響範囲(closure)

- docs/02-design/system.md
- docs/ux/policy.md
- docs/ux/flows.md
- docs/ux/screens/SCR-01-cli-commands.md
- docs/ux/reviews/00.md
- docs/README.md
- docs/03-impl/relations/MODULE-cli-reset.md
- docs/03-impl/index.md(層の版。共有生成物 — orchestration.md §3.4.1)
- docs/03-impl/relations/index.md(build-index.py の生成物。同上)

## 主張

- 触ったモジュールのテスト: 該当なし(実装コードを1バイトも触っていない)
- lint / build: 該当なし(同上。段3 の最後以降 `docs/` の外が1つも動いていない —
  skills/build §5 の省略の規則)
- 外部挙動の変化: なし
- 認証・決済・不可逆への接触: なし(critical: false)
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 及第ライン)
- UX 文書の機械検査: green(`python3 .claude/scripts/check-ux.py` →
  `check-ux: 違反 0 件(対象 2 ファイル。reviews/ は対象外 — ux.md)`)
- 一括検査の母集団: 凍結時と完全一致(`python3 .claude/scripts/check-ssot.py docs` →
  `NG 違反 9 件`。9件はすべてクロージャ外で、凍結時の出力とバイト単位で同一 — 新しい違反ゼロ)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | このタスクは記述の置き場を移すだけで、認証情報を扱う機能を作らず変えない。単一利用者のホスト CLI であり、管理者・権限の概念を持たない | — |
| BR-02 | 該当 | 移送する SCR-01 の項目表が、CLI が受け取る値(サブコマンド・対象セッション名・フラグ)の型・制約・必須を持つ | 既存で充足。01 `FR-env-01-18` / 02 `docs/02-design/contracts/cli-container.md` 規則B。移送先 `docs/ux/screens/SCR-01-cli-commands.md` の項目表に保つ |
| BR-03 | 該当 | 同上。`stop` の名前引数の受理文字集合 `[A-Za-z0-9._-]` が移送対象に含まれる | 既存で充足。01 `FR-env-01-18` / 02 `docs/02-design/contracts/cli-container.md`「ロックキーとして使える文字」 |
| BR-04 | 非該当 | プロセス外との値のやり取りを作らず変えない(文書の移送のみ) | — |
| BR-05 | 該当 | 移送する状態記述に破壊的操作(`logout` / `reset`)の 確認 / 中止 / 一部失敗 / 残した資源 が含まれる | 既存で充足。01 `FR-env-03-14`〜`FR-env-03-19`。移送先 `docs/ux/screens/SCR-01-cli-commands.md` の状態に保つ |
| BR-06 | 非該当 | 推測されると困る値を作る経路を作らず変えない | — |
| BR-07 | 非該当 | 利用者ごとに見えるもの・触れるものが違う対象を持たない(単一利用者のホスト CLI) | — |
| BR-08 | 非該当 | 値を出す経路を作らず変えない。文書だけを動かす | — |
| BR-09 | 非該当 | 秘密を突き合わせる経路を作らず変えない | — |
| BR-10 | 非該当 | ブラウザから呼ばれて状態を変える経路が無い(`DSN-ui-01` — Web GUI を持たない) | — |
| BR-11 | 非該当 | 保存先を作らず、保存の形も保存する対象も変えない | — |
| BR-12 | 非該当 | 成果物の起動の入口(引数・下位コマンド・起動時の出力)にも版の値にも触れない | — |

## 決定シート(回答済み)

- 問いなし(開示のみ)

## 質問キュー(出口のシートの種)

- なし

## 調査メモ

- check-ssot.py `docs` の凍結(基準 d3c83b7): 違反9件。**クロージャの中は0件**(9件はすべて
  クロージャ外 — 手を付けない。F2 のものである)
- `docs/02-design/system.md:452-509` が UI設計節。`### 画面一覧` の台帳は `:467-469`、
  `#### SCR-01 cli-commands` は `:475-502`、`### デザイン方針` は `:504-508`
- `docs/03-impl/relations/MODULE-cli-reset.md:46` が `02-design/system.md` の
  SCR-01「残した資源」を参照している(その語は `system.md:485`)
- 移送する条項参照は 14 件すべて `01-requirements/functional.md` に実在し、`delete` でない
  (`FR-env-01-9/16/18/23/26/27/28/32` / `FR-env-03-14/15/17/18/19/24`)
- `docs/issues/094-...md:76` が SCR-01 の位置を `system.md:522`(現行513行)で持つ。
  作業指示8 が「このタスクでの対応は不要」と明記(②勘定外)

## 進捗メモ(再開点)

- 2026-09-06 09:12 段1: クロージャを確定し、作業指示8 の①②と突き合わせて外へ出ないことを確認。
  基本要件を12件すべて判定(該当3・非該当9)。問いゼロ
- 2026-09-06 09:30 段2: `docs/ux/{policy,flows,screens/SCR-01-cli-commands,reviews/00}.md` を作り、
  02 の UI設計節を `DSN-ui-01` + UI の有無の宣言1行に薄めた。@triage の論点(薄める1行の文言)は
  決めて閉じた — `DSN-ui-01` は設計判断なので 02 に残す(原則3。棄却案は履歴の「検討した代替案」)
- 2026-09-06 09:34 段2: `MODULE-cli-reset.md:46` の参照を移送先へ張り替え、`docs/README.md` に
  `ux/` の位置づけ・ツリー・読み場所の2行を足した
- 2026-09-06 09:38 段4: `check-ux.py` green / `check-ssot.py` が凍結時と完全一致。
  実装コードを触っていないので build/lint とテストは該当なし(段3 が無い)
- 2026-09-06 09:41 段5: 版を刻み(02 は 2.21.0、03 の層は 1.38.0)、履歴を書き、
  `build-index.py` を回して commit ac23a0f

## 申し送り

- 完了後、この変更を対象に増分の `/verify-docs` と `/verify-impl` が各1回要る
  (移行手順4 の「一度きりの検証コスト」)。人間の指示があったときに中央エージェントが出す
