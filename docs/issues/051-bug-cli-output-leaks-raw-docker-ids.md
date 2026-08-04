---
id: 051-bug-cli-output-leaks-raw-docker-ids
type: bug
severity: 低
found: 2026-08-04
found_in: task-fix-destructive-scope のフェーズ3(実機確認中に stop と start の出力で観測)
related: MODULE-cli-stop, MODULE-cli-common-ensure-infrastructure, docs/02-design/logging.md
summary: CLI の利用者向け出力に生の Docker ID が混じる(docker network create と xargs docker rm -f の標準出力を捨てていない)。本変更より前から存在する
---

# 051 CLI の出力に生の Docker ID が混じる

## 事象

利用者向けの出力の中に、意味の説明がない 12〜64 桁の 16 進文字列が単独の行として現れる。

```
✅ my-app を停止しました
cdae190639c7                      ← これ
ℹ️  旧い名前の compose 資源が残っています（プロジェクト名 my-app）。
```

```
🐳 Docker Socket Proxy コンテナ起動
b71f0dbb81bbd8e5680b09b07709b425b4cabe8d7647e12de5ad8c76b19c5a35   ← これ
```

## 原因

標準出力を捨てていない箇所が 2 種類ある。**どちらも本 issue の発見時点より前から存在する**
（`task-fix-destructive-scope` の変更で入ったものではない。変更前のコミット `d2c55e7` でも同じ）。

| 箇所 | コード | 何が出るか |
|---|---|---|
| `ensure_infrastructure` | `claude-dev:353` / `claude-dev-mac:418`<br>`docker network create "$NETWORK" 2>/dev/null \|\| true` | ネットワークを新規作成したときだけ、64 桁のネットワーク ID |
| `stop` の中継コンテナ・compose コンテナの片付け | `claude-dev:1593` / `:1624` と macOS 版の対応箇所<br>`... -q \| xargs -r docker rm -f 2>/dev/null \|\| true` | 削除したコンテナごとに 12 桁の短縮 ID |

いずれも `2>/dev/null` で標準エラーだけを捨てており、標準出力を捨てていない。

## なぜ問題か

`docs/02-design/logging.md` の「主要イベントのログ仕様」は、利用者向けの出力を
イベントごとに定めている。生の ID は**どのイベントにも対応しない**うえ、
利用者が次に取るべき操作を何も示さない。破壊的操作（`stop`）の出力の中に
説明のない ID が並ぶと、**何が消えたのかを読み取りにくくする**。

重大度が「低」なのは、動作そのものは正しく、誤った操作を誘発しないためである。

## 直し方（案）

`>/dev/null` を足す。`ensure_infrastructure` は
`docker network create "$NETWORK" >/dev/null 2>&1 || true`、
`stop` の 2 箇所は `xargs -r docker rm -f >/dev/null 2>&1 || true`。
Linux 版と macOS 版の両方に同じ形で入れる（`D0-scope-03`）。

**観測できる振る舞い（出力）が変わるので、`D0-scope-02` の委任範囲には収まらない。**
`docs/02-design/logging.md` に「これらの ID は出さない」ことを書くか、
出力の一覧に載っていないものは出さないという共通制約を置くかの判断が要る。

## 本タスクで直さない理由

`task-fix-destructive-scope` の範囲は「破壊的操作の**対象**を自分が作った資源に限ること」で
あって、出力の整形ではない。かつ `ensure_infrastructure` は `stop` / `logout` / `reset` の
どれからも呼ばれず、本タスクの影響範囲（closure）に入っていない。
