---
target: docs/03-impl/index.md
change: add
sections: []
deletes: []
reason: 新体系では 03-impl 層の代表として index.md が版と合格証を持つ(`relations/MODULE-*.md` は個別の版を持たない)。旧構造にはこの代表が存在しなかったため新設する。
---

<!-- change: add。ファイル全体の最終内容。
     このファイルは 03-impl 層の代表であり、relations 群はここでまとめて認証される。
     「## 目次」以下の表は build-index.py が生成する。手書きしない。

     ★反映時の規則(曖昧さを残さないため明記する):
     「この層の状態」と「コールグラフ」の各数値は、**変更指示に書いてある値をそのまま採用しない**。
     /task-close が SSOT へ反映し、config の3キーをキット既定へ戻して生成物を作り直した**後**に、
     `docs/02-design/environments.md`「ドキュメント整合検査コマンド」の 1〜6 を順に実行し、
     その実測値で置き換える。下に書いてある値は「変更指示を書いた時点の観測値」であり、
     反映時点の値と食い違ったら**実測値が正**である(食い違いの事実は histories に残す)。 -->

# 03-impl 目次

## この層の状態

| 項目 | 値 |
|---|---|
| 機能間連携仕様書の本数 | 82 |
| 網羅しているモジュール | MOD-cli-common, MOD-cli-setup, MOD-cli-start, MOD-cli-stop, MOD-cli-attach, MOD-cli-code, MOD-cli-list, MOD-cli-login, MOD-cli-login-codex, MOD-cli-logout, MOD-cli-forward, MOD-cli-unforward, MOD-cli-ports, MOD-cli-ssh-keys, MOD-cli-firewall, MOD-cli-orchestrate, MOD-cli-pull, MOD-cli-upgrade, MOD-cli-reset, MOD-makefile, MOD-entrypoint, MOD-firewall, MOD-docker-proxy, MOD-portsync, MOD-vm-mode, MOD-orchestrator, MOD-hooks, MOD-container-tools, MOD-sample-project(29モジュール) |
| `check-relations.py` 最終結果 | /task-close で SSOT へ反映した直後に実行して記録する |
| コードとの乖離として未解決のもの | 1件: macOS のコントローラ生存判定が無い(`docs/issues/003-future-macos-orchestrator-scope.md`) |

## 02 との差分(未解消のもの)

| 種別 | 対象 | 内容 | 対処 |
|---|---|---|---|
| PLAN なし / MODULE あり | MODULE-orchestrator-* の内部関数18本、MODULE-sample-project-mathkit | 設計側は同一モジュール内部で完結する private helper を書かない取り決めのため、意図的な差分である | 対処不要(`02-design/relations.md` の網羅範囲に明記) |
| 契約の差異 | CTR-cli-orchestrator | macOS 版にコントローラの生存判定が無く、設計の期待(OS によらず同じ観測可能な結果)を満たしていない | `docs/issues/003-future-macos-orchestrator-scope.md` で追跡 |

上記2件を除いて差分なし。

## 目次

<!-- BEGIN GENERATED: build-index.py -->
<!-- END GENERATED -->

## 機能間連携仕様書

`docs/03-impl/relations/index.md` を参照(こちらも生成物)。**82機能** の境界は
`docs/03-impl/features.md`(人間が合意した機能表)が定義する。

## コールグラフ

`docs/03-impl/callgraphs/index.md` を参照。**ツールだけが書く場所**であり、機能間連携仕様書では
ない(`.claude/directions/callgraphs.md`)。版も合格証も持たない純粋な導出物で、鮮度は
`python3 .claude/scripts/build-callgraphs.py --check` で検査する。

| 項目 | 値 |
|---|---|
| 最終検査 `--check` | /task-close で再生成した直後の結果を記録する |
| `callgraph-check.py` の未解決指摘 | 重大度「高」ゼロ。低・参考のみ(CG2 到達不能候補15件 / CG3 プロセス跨ぎ連携3件 / CG4 参考20件) |
| 抽出器が無い領域 | Dockerfile と GitHub Actions。この2つはモジュールにせず `environments/images.md` と `infra/local/ghcr.md` が記述を持つ(`DSN-mod-05`) |
