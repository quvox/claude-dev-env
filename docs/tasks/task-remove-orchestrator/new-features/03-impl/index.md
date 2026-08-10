---
target: docs/03-impl/index.md
change: replace
version_bump: minor
sections:
  - "## この層の状態"
  - "## 02 との差分(未解消のもの)"
  - "## 01(要件)との差異(未解消のもの)"
  - "## 機能間連携仕様書"
  - "## コールグラフ"
deletes: []
reason: 'オーケストレーターの全面削除にともなう 03-impl 層の状態の更新(決定シート 概念1・概念2)。(1) `## 02 との差分(未解消のもの)` の 4 行のうち 3 行を削除する: 「PLAN なし / MODULE あり = `MODULE-orchestrator-*` の内部関数18本・`MODULE-sample-project-mathkit`」(対象の機能ごと消える)/ 「契約の差異 = `CTR-cli-orchestrator`(macOS にコントローラの生存判定が無い)」(契約と実装の双方が消えるので `docs/issues/003` を削除する)/ 「ログ仕様の差異 = 通知の送信失敗 ⇄ `MODULE-orchestrator-slack`」(`docs/issues/013` を削除する)。**「ログ仕様の差異 = 必須フィールド ⇄ 追記型ログ3本」も削除する** — `02-design/logging.md` の `## 必須フィールド` と追記型ログそのものが消えるので、比べる両辺が無くなる(`docs/issues/014` を削除する)。**結果として 02 との差分は 0 件になる。** 締めの段落もそれに合わせる。(2) `## 01(要件)との差異(未解消のもの)` の 5 行のうち 3 行を削除する: `FR-orch-05` 受入基準7(`docs/issues/057`)/ `FR-orch-06` 受入基準3(`docs/issues/058`)/ 「要件が存在しない ⇄ `dispatch` と `result`」(`docs/issues/061`)。**残るのは `NFR-scale-01`(`docs/issues/028`)と `AC-03` / `FR-env-07` 受入基準8(`docs/issues/005`)の 2 行**で、どちらもオーケストレーターに依存しない。(3) `## 機能間連携仕様書` の「**83機能**」を「**56機能**」へ改める。(4) **`## この層の状態` と `## コールグラフ` を 2026-08-10(フェーズ3 の末尾、タスクリスト14)に実測値で書いた。** 値の出どころは、実装を削除したあとの再生成コールグラフと、`compose-changeset.py --preview` が作った合成ビュー(SSOT + 本タスクの変更指示)に対する各ツールの実行結果である: `check-relations.py` = 合格(56 ファイル / 56 ID)/ `relations-coverage.py` = 合格(機能間連携仕様書 56 本 / エントリポイント候補 0 件)/ `check-contracts.py` = 合格(02:3 件 / 03:3 件)/ `relations-query.py --health` = 循環 0 件・呼び出し元が無い function-call 0 件・対応要件が無い機能 0 件 / `callgraph-check.py --to-be task-remove-orchestrator` = 指摘 24 件・重大度「高」ゼロ。**起票済みの実装欠陥は 21 → 11 件になった**(削除した 21 issue のうち `001` / `011` / `012` / `013` / `015` / `021` / `022` / `026` / `057` / `058` の 10 件がこの集計に入っていた)。`docs/issues/003` の削除で「機能の欠落 1 件」も消える。(5) `## 目次` は `build-index.py` の生成物なので触らない'
reflected: 2026-08-10
---

## 02 との差分(未解消のもの)

| 種別 | 対象 | 内容 | 対処 |
|---|---|---|---|
| なし | — | — | — |

**02(設計)との差分は 0 件である。** **`DSN-env-04`(セッション由来の資源の識別)は
2026-08-07 に実装され、「設計済み・未実装」の行は1件も無い**(`MODULE-cli-stop` / `MODULE-cli-reset` /
`MODULE-docker-proxy-serve` と `CTR-cli-container` / `CTR-docker-api` が実装の事実を持つ)。
**2026-08-08 のオーケストレーター削除で、それまでの差分4件はいずれも比べる対象を失って消えた**
(内部関数の PLAN 欠落 / `CTR-cli-orchestrator` の macOS 未適合 / 追記型ログの必須フィールド /
通知の送信失敗の記録。経緯は `docs/histories/` が持つ)。

## 01(要件)との差異(未解消のもの)

**すべて人間が裁定済み**(実装の修正は別タスク)。「要件との差異が無い」わけではないので、
ここに明記する。

| 要件 | 実装 | 裁定と追跡 |
|---|---|---|
| `NFR-scale-01`「コンテナ名・compose プロジェクト名がプロジェクト間で衝突しない(衝突 0 件)」 | コンテナ名・compose プロジェクト名・中継コンテナ名をディレクトリ名だけから導くため、別パスの同名ディレクトリが同一セッション扱いになる | **設計が正**(2026-08-04)。コード修正は別タスク。`docs/issues/028` |
| `AC-03` / `FR-env-07` 受入基準8「危険な操作は拒否される」 | docker-proxy は解釈できないボディを検査せず中継する | `D0-sec-05`(Docker API 検査の厳密さの委任)の範囲内で「中」と裁定。`docs/issues/005` |

## 機能間連携仕様書

`docs/03-impl/relations/index.md` を参照(こちらも生成物)。**56機能** の境界は
`docs/03-impl/features.md`(人間が合意した機能表)が定義する。

## この層の状態

| 項目 | 値 |
|---|---|
| 機能間連携仕様書の本数 | 56 |
| 網羅しているモジュール | MOD-cli-common, MOD-cli-setup, MOD-cli-start, MOD-cli-stop, MOD-cli-attach, MOD-cli-code, MOD-cli-list, MOD-cli-login, MOD-cli-login-codex, MOD-cli-logout, MOD-cli-forward, MOD-cli-unforward, MOD-cli-ports, MOD-cli-ssh-keys, MOD-cli-firewall, MOD-cli-pull, MOD-cli-upgrade, MOD-cli-reset, MOD-makefile, MOD-entrypoint, MOD-firewall, MOD-docker-proxy, MOD-portsync, MOD-vm-mode, MOD-container-tools(25モジュール) |
| `check-relations.py` 最終結果 | 合格(2026-08-10 に再実行。56 ファイル / 56 ID。対称性・参照実在・impl パス・必須項目・機能表との 1:1 すべて問題なし) |
| コードとの乖離として未解決のもの | **0 件**。機能の欠落として数えていた 1 件(macOS のコントローラ生存判定が無い。`docs/issues/003`)は、`orchestrate` サブコマンドごと消えた。本文の叙述レベルの食い違いとして数えていた 17 件(`docs/issues/009` の (a))も、対象が `MODULE-orchestrator-*` の relations だけだったため対象ごと消えた。**`docs/issues/009` 自体は「本文で `ctx` 等の定型引数を省略してよいかの規約が無い」という規約側の欠落として残る**(指摘の実体は 0 件)。集計の維持そのものは `docs/issues/030` で追跡する |
| 実装の欠陥として起票済み(コードは未修正) | **11件**。数え方は「`03-impl` のいずれかの `## 既知の制限` から参照されている `type: modify` / `type: bug` の issue」のうち、**本システムが未修正のもの**とする: `docs/issues/002`(`.claude-dev.yaml` が全面上書きされる)/ `005`(docker-proxy が解釈できないボディを検査せず中継する)/ `010`(forward のホストポート選択の競合)/ `023`(`CLAUDE_DEV_SSH_BRIDGE_PORT` を無検証で採る)/ `028`(名前の一意性が `NFR-scale-01` を満たさない)/ `047`(`reset` が `claude-dev-vm-*` ボリュームを消さない)/ `052`(`logout` が削除対象0件の経路でラベル無しコンテナの警告を出さない)/ `053`(`logout` が列挙できない共有ボリュームを「空」と判定する)/ `087`(所有者ラベルの注入失敗がコンテナ経路でログに出ない)/ `088`(`stop` が compose 既定ネットワークの削除失敗を表示しない)/ `089`(`logout` がセッション由来のコンテナを「管理ラベルを持たない」と誤表示する)。**2026-08-08 のオーケストレーター削除で 10 件(`001` / `011` / `012` / `013` / `015` / `021` / `022` / `026` / `057` / `058`)が対象の実装ごと消え、21 件から 11 件になった。** `014` / `046` / `051` / `054` は、どの「既知の制限」からも参照されていないためこの数に含めない(いずれもコードは未修正である。集計の対象は「既知の制限」から参照されているものに限る、という数え方の定義による)。集計の維持そのものは `docs/issues/030` で追跡する |
| `relations-coverage.py` 最終結果 | 合格(2026-08-10 に再実行。機能間連携仕様書 56 本 / エントリポイント候補 0 件 / 未記載 0 件)。**2026-08-07 に検出していた未記載 30 件は、その全件が `scan-entrypoints.py` の Go `switch` 誤検出(orchestrator の設定キー・TUI のキー入力・JSON の型識別子・git のサブコマンド文字列)であり、対象の実装ごと消えた。** 残る Go は `docker-proxy/` だけで、コードとの一致は `callgraph-check.py` と `check-relations.py` が担保する |

## コールグラフ

`docs/03-impl/callgraphs/index.md` を参照。**ツールだけが書く場所**であり、機能間連携仕様書では
ない(`.claude/directions/callgraphs.md`)。版も合格証も持たない純粋な導出物で、鮮度は
`python3 .claude/scripts/build-callgraphs.py --out "$(python3 .claude/scripts/resolve-callgraph-out.py)" --check`
で検査する(**生成先を自分で決めない** — 進行中タスクがあるときの置き場は
`.claude/directions/callgraphs.md` §3.1)。

| 項目 | 値 |
|---|---|
| 最終検査 `--check` | 最新(2026-08-10 に再生成。go 14シンボル/17辺 / shell 170/261 / make 16/21 / python 0/0 / typescript 0/0 / infra 0/0。エントリポイント 63) |
| `callgraph-check.py` の未解決指摘 | 指摘 24 件・**重大度「高」ゼロ**(2026-08-10 に `--to-be task-remove-orchestrator` で実行。中3 = CG3 のプロセス跨ぎ連携 / 低8 = CG2 到達不能候補 / 低1 = CG3 の実装前の連携 / 参考12 = CG4 取りこぼし候補)。中3件は `MODULE-entrypoint-claude` が絶対パス起動するため shell 抽出器が辺を解決できないもので、根拠は `relations/MODULE-entrypoint-claude.md` の本文にある |
| Makefile を解析対象に含めるか | 含める(`callgraph-config.local.json` の `include_tooling: true`)。キット既定は Makefile を開発ツールとして外すが、`MOD-makefile` の 16 ターゲットは機能表が定義する境界の一部であり、外すと機能表と食い違う |
| 抽出器が無い領域 | Dockerfile と GitHub Actions。この2つはモジュールにせず `environments/images.md` と `infra/local/ghcr.md` が記述を持つ(`DSN-mod-05`) |
