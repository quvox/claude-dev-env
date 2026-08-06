---
id: 072-modify-five-design-points-are-not-derivable-from-the-documents
type: modify
severity: 中
found: 2026-08-06
found_in: /doc-check full(check D13/D14 パス1。独立レビュー = サブエージェント readiness が 00〜02 と 03-impl/contracts だけを読んで検出。Claude 側が 03-impl/relations/ を含めて再確認し、そこでも決まっていないものだけを残した)
related: docs/02-design/system.md, docs/02-design/environments.md, docs/02-design/contracts/cli-orchestrator.md, docs/01-requirements/functional.md, docs/03-impl/relations/MODULE-cli-common-write-project-ssh-keys.md, docs/issues/002
pattern: value-or-policy-must-be-invented-by-implementer
pattern_survey: readiness レンズが挙げた未決点 10 件を、Claude が 03-impl/relations/ と 03-impl/infra/ まで含めて1件ずつ照合した。5 件は 03 側に事実が書かれていた(plan.json / state.json のスキーマ = MODULE-orchestrator-state、`.claude-dev.yaml` の書き出し = MODULE-cli-common-write-project-ssh-keys、`.env` のキー = MODULE-makefile-env と infra/local/ghcr.md、追記型ログの detail = MODULE-orchestrator-* の各異常系、E2E の後始末 = tests/e2e.md の手順)。**どこにも書かれていない 5 件**を本 issue に残した
summary: 仕様ドキュメント(03-impl を含む)のどこにも書かれておらず、実装者が値か方針を発明するしかない箇所が5件ある
---

# 072 ドキュメントだけからは決まらない設計事項が5件残る

## 事象

`/doc-check` の check D13(b)は「曖昧語が無くても、実装者に値や方針の発明を強いる基準・契約は
指摘」と定める。本実行の独立レビュー(readiness モード。**コードも 03-impl/relations/ も読まない**
制約下で 00〜02 と契約だけからタスク分解を試みる)が 10 件の未決点を報告した。
Claude 側が 03-impl まで含めて照合した結果、**5 件は 03 側に事実が書かれていた**ので落とし、
残る 5 件を以下に挙げる。

| # | 決まっていないこと | どこに書かれるべきか | 現状の記述 |
|---|---|---|---|
| 1 | **ホスト CLI 18 サブコマンド × フラグの文法表**(どのフラグがどのサブコマンドに有効か、位置引数の順序と型、「非対応の組み合わせ」の実体) | `02-design/system.md` の `SCR-01`(画面ごとの項目と状態) | `SCR-01` は「サブコマンド = 18 種の列挙」「フラグ = `--no-vnc` / `--kvm` / `--vm` / `--vm-fresh` / `--fresh` / `--yes`」「非対応の組み合わせは実行前に拒否する」とだけ書き、**組み合わせを1つも列挙していない** |
| 2 | **`.claude-dev.yaml` のスキーマ**(`ssh_keys` 以外に持ちうるキー、値の型、リストの書式) | `02-design` のどこか(契約または `SCR-01`) | `FR-env-04` 受入基準2 と `D0-sec-08` は `ssh_keys` というキーの存在だけを前提にする。03 側(`MODULE-cli-common-write-project-ssh-keys`)は**書き出す側の振る舞い**(全面上書き。`docs/issues/002`)だけを書き、ファイル形式そのものを定義していない |
| 3 | **`make setup` が作る `.env` のキー一覧と既定値** | `02-design/environments.md` または `03-impl/infra/local/` | `environments.md` のセットアップ手順に「`.env` の作成」と名前だけが出る。`infra/local/ghcr.md` が定義するのは **CI 側のワークフロー変数**(`REGISTRY` / `CLAUDE_VERSION` ほか)であって、ホストの `.env` ではない |
| 4 | **`max_workers` を超えたタスクのディスパッチ順** | `02-design/system.md` または `CTR-cli-orchestrator` | `FR-orch-03` 受入基準5 は「上限までしかディスパッチしてはならず、超過分は次の空きまで待たせる」と**量**だけを課し、**どれを先に出すか**(投入順 / 依存の浅い順 / plan の並び順)を定めていない |
| 5 | **`/workspace` が git リポジトリでないときの `orchestrate` の振る舞い** | `02-design/contracts/cli-orchestrator.md` の「エラーケース」 | `02-design/relations.md:161` の `PLAN-orchestrator-main` は前提条件として「`/workspace` が git リポジトリであること」を明記するが、**その前提が崩れたときの行を `CTR-cli-orchestrator` のエラーケース表が持っていない**(他のすべての前提には対応する行がある) |

## 影響

**この5件は、ドキュメントからの再実装を試みた時点で必ず止まる。** 03-impl はコードの鏡なので
「現物がどう動くか」は追えるが、#1〜#4 は 03 にも書かれていないため、**現物のコードを読む以外に
知る手段が無い**。これは 03-impl が掲げる「ドキュメントだけから再実装・再試験できる深度」
(`D0-scope-07`)に届いていないことを意味する。

#5 は性質が違う: **02 の中で前提と例外が食い違っている**(`relations.md` が課した前提に
契約側の受け皿が無い)。単独でも A2 の指摘になる。

severity は「中」とする — いずれも観測可能な振る舞いを壊しておらず、現に動いている実装があるため。

## 原因の見当

#1〜#3 は「利用者が触るファイル・入力の形式」で、実装が Bash に閉じているため
自動テストの対象にならず(`SR-32` / `DSN-test-01`)、**書かなくても機械検査に落ちない**位置にある(推測)。
#4 は実装が Go の内部にあり、`FR-orch-03` が量の制約だけを課したまま順序を書き落とした。
#5 は `02-design/relations.md` の「連携の詳細」を後から厚くしたときに、契約側へ降ろし忘れたもの(推測)。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| #1 CLI の文法 | 各 `MODULE-cli-*` が自分の引数だけを書く。**横断の表は無い** | `SCR-01` が「非対応の組み合わせ」の存在だけを述べる | **どちらにも無い。02 に足す** |
| #2 `.claude-dev.yaml` | 書き出す側の振る舞いだけ | キーの存在だけ | 同上 |
| #3 `.env` | `MODULE-makefile-env` が雛形からのコピーを書く。キー一覧は無い | 名前だけ | 同上 |
| #4 ディスパッチ順 | `MODULE-orchestrator-controller` は「着手可能タスクの抽出」とだけ書き、順序を書いていない | 量の制約だけ | **要確認**(実装が順序を持つなら 03 に書き、02 へ上げるかを決める) |
| #5 git でない `/workspace` | 未記載 | `relations.md` は前提として明記、契約は無言 | **02 の中の欠落**(自明に 02 起点) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | 5 件をまとめて1タスクにし、`/task-new` でフェーズ1から回す | 02 が主戦場。#4 だけコードの確認が要る |
| B(推奨) | #5 だけを先に 02 へ足し(単独で A2 の欠落であり、他の4件と独立している)、#1〜#4 は本 issue のまま残して次に 02 を触るタスクへ合流させる | #5 は `cli-orchestrator.md` 1行。#1〜#4 は据え置き |
| C | 5 件とも据え置く | 「ドキュメントだけから再実装できる」という 03 層の目標(`D0-scope-07`)が満たされないままになる |

## 経緯

- 2026-08-06 `/doc-check full` で起票。独立レビュー(サブエージェント / readiness)が
  00〜02 + 契約だけを読んで 10 件を報告し、Claude が 03-impl まで含めて照合して 5 件に絞った。
  落とした 5 件の行き先は frontmatter の `pattern_survey` に記録した。
- 2026-08-06 **人間が対処案 C(5件とも据え置き)を選択した。** 推奨していた案B(#5 だけ先に
  02 へ足す)は採らない。したがって `CTR-cli-orchestrator` のエラーケース表に
  「`/workspace` が git リポジトリでない」の行が無い状態は、本 issue が追跡したまま残る。
