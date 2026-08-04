---
id: 048-modify-design-claims-shared-base-functions-never-call-each-other
type: modify
severity: 低
found: 2026-08-04
found_in: task-fix-destructive-scope の /doc-check(3回目)。PLAN-cli-common-* の連携の詳細を 02 の一覧表と突き合わせた際に確定
related: PLAN-cli-common-require-setup, PLAN-cli-common-image-exists, PLAN-cli-common-select-ssh-keys, PLAN-cli-common-write-project-ssh-keys, DSN-mod-03
summary: 02-design/relations.md の「共有基盤どうしは呼び合わない(相互依存を作らない)」が、同じ文書の一覧表にある2本の共有基盤どうしの辺と矛盾する(設計の宣言と設計自身の表が食い違う)
---

## 事象

`docs/02-design/relations.md` の `### PLAN-cli-common-*(共有基盤)` は、呼び出す先ごとの期待として

> 共有基盤どうしは呼び合わない(相互依存を作らない)。

と書いている。しかし**同じ文書の `## 一覧` の表に、共有基盤どうしの辺が2本ある**。

| PLAN-ID | 呼び出す先 |
|---|---|
| `PLAN-cli-common-require-setup` | `PLAN-cli-common-image-exists` |
| `PLAN-cli-common-select-ssh-keys` | `PLAN-cli-common-write-project-ssh-keys` |

03 側も同じである(`MODULE-cli-common-require-setup` の `callees` に
`MODULE-cli-common-image-exists`、`MODULE-cli-common-select-ssh-keys` の `callees` に
`MODULE-cli-common-write-project-ssh-keys`)。`check-relations.py` は対称性を検査するので
**辺そのものは整合しており、矛盾しているのは散文の宣言のほうである**。

`docs/03-impl/features.md` の「昇格させた共通基盤機能」も、`image_exists` を昇格させた理由として
**「`require_setup` を昇格させても `ensure_docker_proxy_container` から到達するのでファンイン2が
残る」**と述べており、共有基盤どうしの到達を前提にしている。

## 影響

- **実害は無い**(コードも relations も一貫しており、機械検査はすべて通る)。
- ただし **02 の宣言を根拠に判断すると誤る**。「共有基盤どうしは呼び合わない」を前提に
  新しい共有基盤機能を設計すると、既存の2本と整合しない構造を選びうる。
- `DSN-mod-03`(共有基盤は1モジュールに集約する)の意図は「モジュールを分けない」ことであって
  「関数どうしが呼び合わない」ことではないと読めるため、**宣言のほうが強すぎる**可能性が高い。

## どちらが正か(人間の判断が要る)

| 案 | 内容 | 影響 |
|---|---|---|
| A | **宣言を実態に合わせる**(「共有基盤どうしは原則として呼び合わない。例外は事前条件ゲートと保存系の2本で、いずれも一方向で循環しない」) | 文言だけ。`relations-query.py --health` の循環検査が0件であることが裏付けになる |
| B | **実装を宣言に合わせる**(`require_setup` から `image_exists` の呼び出しを外すなど) | 呼び出し元が増え、重複が生じる。`features.md` の昇格理由も書き換えになる |

**推奨は A**。循環が無い一方向の依存であり、`--health` の循環検査も0件である。
「相互依存を作らない」の本来の意図は循環の禁止であって、一方向の再利用の禁止ではないと読める。

## なぜ task-fix-destructive-scope で直さないか

同タスクは `### PLAN-cli-common-*(共有基盤)` を影響範囲に含むが、それは
**新設する `PLAN-cli-common-lock`(排他系)が「用意系だけが副作用を持つ」という記述に
収まらない**ためであり、本 issue の矛盾は `PLAN-cli-common-lock` とは無関係に**以前から存在する**。
CLAUDE.md 原則8「本タスクの範囲外の修正を混ぜない」に従い、起票にとどめる
(同タスクは当該箇所を「原則として呼び合わない」と改めたが、**例外2本の明示は本 issue に委ねる**)。
