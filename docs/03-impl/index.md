---
id: index
version: 1.24.0
updated: 2026-08-11
source:
  - docs/02-design/system.md
  - docs/02-design/relations.md
summary: 03-impl 層の目次。機能間連携仕様書群の代表として層全体の版と合格証を持つ
keywords: [目次]
verified:
  at: 2026-08-11
  version: 1.24.0
  against:
    - {doc: docs/02-design/system.md, version: 2.11.0}
    - {doc: docs/02-design/relations.md, version: 1.10.0}
---

# 03-impl 目次

## この層の状態

| 項目 | 値 |
|---|---|
| 機能間連携仕様書の本数 | 61 |
| 網羅しているモジュール | MOD-cli-common, MOD-cli-setup, MOD-cli-start, MOD-cli-stop, MOD-cli-attach, MOD-cli-code, MOD-cli-list, MOD-cli-login, MOD-cli-login-codex, MOD-cli-logout, MOD-cli-forward, MOD-cli-unforward, MOD-cli-ports, MOD-cli-ssh-keys, MOD-cli-firewall, MOD-cli-pull, MOD-cli-upgrade, MOD-cli-reset, MOD-makefile, MOD-entrypoint, MOD-firewall, MOD-docker-proxy, MOD-portsync, MOD-vm-mode, MOD-container-tools(25モジュール) |
| `check-relations.py` 最終結果 | 合格(2026-08-11 の `task-promote-shared-helpers` 反映後に再実行。61 ファイル / 61 ID。対称性・参照実在・impl パス・必須項目・機能表との 1:1 すべて問題なし) |
| コードとの乖離として未解決のもの | **1 件** — `docs/issues/097`(CLI の `help\|*)` 分岐が実在するのに機能表にも relations にも無い。`claude-dev:2183` / `claude-dev-mac:2207`)。**2026-08-11 に原因を実測した**: シェル抽出器の決定 D「catch-all(`*` を含むラベル)は入口にしない」が**ラベル全体を落とす**ため、`help` の側も巻き添えで入口から外れる(`.claude/scripts/cgx/shell_regex.py:169`)。したがって機能表に行を足すと FT1 が重大度「高」で落ちる。解消にはコード側で `help)` と `*)` を分けるか抽出器を直すかが要り、どちらも `task-promote-shared-helpers` の範囲外だった。**戻り値の記述の食い違い4件は 2026-08-11 に修正して 0 件になった**(`MODULE-cli-logout` / `-reset` / `-start` / `-stop` の終了コード 130 の区間)。機能の欠落として数えていた 1 件(macOS のコントローラ生存判定が無い。issue `003`。対象ごと消えたため issue も削除した)は、`orchestrate` サブコマンドごと消えた。本文の叙述レベルの食い違いとして数えていた 17 件(`docs/issues/009` の (a))も、対象が `MODULE-orchestrator-*` の relations だけだったため対象ごと消えた。**`docs/issues/009` 自体は「本文で `ctx` 等の定型引数を省略してよいかの規約が無い」という規約側の欠落として残る**(指摘の実体は 0 件)。集計の維持そのものは `docs/issues/030` で追跡する |
| 実装の欠陥として起票済み(コードは未修正) | **9件**。数え方は「`03-impl` のいずれかの `## 既知の制限` から参照されている `type: modify` / `type: bug` の issue」のうち、**本システムが未修正のもの**とする: `docs/issues/002`(`.claude-dev.yaml` が全面上書きされる)/ `005`(docker-proxy が解釈できないボディを検査せず中継する)/ `010`(forward のホストポート選択の競合)/ `023`(`CLAUDE_DEV_SSH_BRIDGE_PORT` を無検証で採る)/ `028`(名前の一意性が `NFR-scale-01` を満たさない)/ `047`(`reset` が `claude-dev-vm-*` ボリュームを消さない)/ `055`(受入基準17 が停止中のラベル無しコンテナの列挙まで求めるが 02 は稼働中しか列挙できないとする。`MODULE-cli-reset.md` の「既知の制限」から参照。**コードの欠陥ではなく 01 ⇄ 02 の食い違いだが、数え方の定義を満たすためこの数に含める** — 2026-08-11 に数え漏れを是正した)/ `087`(所有者ラベルの注入失敗がコンテナ経路でログに出ない)/ `088`(`stop` が compose 既定ネットワークの削除失敗を表示しない)/ `101`(`reset` が削除に失敗した実行でラベル無しコンテナの表示を出さない)。**2026-08-08 のオーケストレーター削除で 10 件(`001` / `011` / `012` / `013` / `015` / `021` / `022` / `026` / `057` / `058`)が対象の実装ごと消え、21 件から 11 件になった(2026-08-11 に `055` の数え漏れを加えて 12 件)。**2026-08-11 の `task-fix-logout-zero-target-path` で `052` / `053` / `089` の3件を修正して外し、同タスクが検出した `098` / `099` / `100` の3件を加えたので 11 件になった。続く `task-fix-logout-records-and-marker` でその3件を修正して外し、同タスクが検出した `101` を加えたので **9件** である。** `014` / `046` / `051` / `054` は、どの「既知の制限」からも参照されていないためこの数に含めない(いずれもコードは未修正である。集計の対象は「既知の制限」から参照されているものに限る、という数え方の定義による)。集計の維持そのものは `docs/issues/030` で追跡する |
| `relations-coverage.py` 最終結果 | 合格(2026-08-11 の `task-promote-shared-helpers` 反映後に再実行。機能間連携仕様書 61 本 / エントリポイント候補 0 件 / 未記載 0 件)。**あわせて「要確認 66 件(impl のファイルにエントリポイント候補が無い)」を出す** — これは合否とは独立の出力で、パターンが覆っていない領域の申告である(スクリプトはこれを不合格に数えない)。**2026-08-07 に検出していた未記載 30 件は、その全件が `scan-entrypoints.py` の Go `switch` 誤検出(orchestrator の設定キー・TUI のキー入力・JSON の型識別子・git のサブコマンド文字列)であり、対象の実装ごと消えた。** 残る Go は `docker-proxy/` だけで、コードとの一致は `callgraph-check.py` と `check-relations.py` が担保する。**ただし「未記載 0 件」は機械が拾える入口に限った主張である**: 2026-08-11 の独立レビューが `claude-dev:2183` / `claude-dev-mac:2207` の `help|*)` 分岐を検出し、これは shell 抽出器(Tier 3)が入口として取り出さないため FT2 にも本検査にも現れない(`docs/issues/097`) |

## 02 との差分(未解消のもの)

| 種別 | 対象 | 内容 | 対処 |
|---|---|---|---|
| なし | — | — | — |

**差分なし**(2026-08-11 の `task-fix-logout-records-and-marker` 反映後に再確認。`PLAN-*` と `MODULE-*` は
61 対 61 で、`呼び出し元` / `呼び出す先` / `契約` の食い違いは無い — `check-changeset.py` の CS9 と
`callgraph-check.py` の CG3/CG4 で確認した。同タスクが増やした辺
`PLAN-cli-logout` → `PLAN-cli-common-spawned-resources` は 02・03 の両方に入っている)。

**02(設計)との差分は 0 件である。** **`DSN-env-04`(セッション由来の資源の識別)は
2026-08-07 に実装され、「設計済み・未実装」の行は1件も無い**(`MODULE-cli-stop` / `MODULE-cli-reset` /
`MODULE-docker-proxy-serve` と `CTR-cli-container` / `CTR-docker-api` が実装の事実を持つ)。
**2026-08-08 のオーケストレーター削除で、それまでの差分4件はいずれも比べる対象を失って消えた**
(内部関数の PLAN 欠落 / `CTR-cli-orchestrator` の macOS 未適合 / 追記型ログの必須フィールド /
通知の送信失敗の記録。経緯は `docs/histories/` が持つ)。

## 01(要件)との差異(未解消のもの)

**3件のうち2件は人間が裁定済み、1件は未裁定である**(実装の修正は別タスク)。
「要件との差異が無い」わけではないので、ここに明記する。

| 要件 | 実装 | 裁定と追跡 |
|---|---|---|
| `FR-env-03` 受入基準17「ラベル無しの Claude コンテナの名前を表示して残す」(稼働中に限定していない) | 表示できるのは `claude-dev-net` に接続している**稼働中**のものだけで、停止中のラベル無しコンテナは表示にも削除にも現れない | **未裁定**。01 を実態へ合わせるか 02 を拡張して停止中も列挙するかを人間が決める(受入基準の意味を変える判断のため)。`docs/issues/055` |
| `NFR-scale-01`「コンテナ名・compose プロジェクト名がプロジェクト間で衝突しない(衝突 0 件)」 | コンテナ名・compose プロジェクト名・中継コンテナ名をディレクトリ名だけから導くため、別パスの同名ディレクトリが同一セッション扱いになる | **設計が正**(2026-08-04)。コード修正は別タスク。`docs/issues/028` |
| `AC-03` / `FR-env-07` 受入基準8「危険な操作は拒否される」 | docker-proxy は解釈できないボディを検査せず中継する | `D0-sec-05`(Docker API 検査の厳密さの委任)の範囲内で「中」と裁定。`docs/issues/005` |

## 目次

<!-- BEGIN GENERATED: build-index.py -->

| ファイル | version | 更新 | 概要 |
|---|---|---|---|
| [features](features.md) | - | 2026-08-11 | claude-dev 開発環境の機能一覧と入口。CLI サブコマンド・Makefile ターゲット・常駐スクリプト・Go バイナリの入口を列挙する |
| [images](environments/images.md) | 1.1.0 | 2026-08-10 | 配布イメージ(claude-cli / claude-vnc)のステージ構成・ビルド引数・キャッシュの効かせ方 |
| [local-docker-resources](infra/local/docker-resources.md) | 1.2.0 | 2026-08-07 | ホスト上に作られる Docker リソース(ネットワーク・ボリューム・コンテナ)の一覧と命名規則 |
| [local-ghcr](infra/local/ghcr.md) | 1.1.0 | 2026-08-04 | 配布イメージの公開先 GHCR の構成(リポジトリ・タグ・マルチアーキ・認証の置き場所) |

件数: 4

<!-- END GENERATED: build-index.py -->

## 機能間連携仕様書

`docs/03-impl/relations/index.md` を参照(こちらも生成物)。**61機能** の境界は
`docs/03-impl/features.md`(人間が合意した機能表)が定義する。

## コールグラフ

`docs/03-impl/callgraphs/index.md` を参照。**ツールだけが書く場所**であり、機能間連携仕様書では
ない(`.claude/directions/callgraphs.md`)。版も合格証も持たない純粋な導出物で、鮮度は
`python3 .claude/scripts/build-callgraphs.py --out "$(python3 .claude/scripts/resolve-callgraph-out.py)" --check`
で検査する(**生成先を自分で決めない** — 進行中タスクがあるときの置き場は
`.claude/directions/callgraphs.md` §3.1)。

| 項目 | 値 |
|---|---|
| 最終検査 `--check` | 最新(2026-08-11 に再生成。書き換えなし。go 14シンボル/17辺 / shell 170/261 / make 16/21 / python 0/0 / typescript 0/0 / infra 0/0。エントリポイント 63) |
| `callgraph-check.py` の未解決指摘 | 指摘 24 件・**重大度「高」ゼロ**(2026-08-11 に SSOT に対して実行。中3 = CG3 のプロセス跨ぎ連携 / 低8 = CG2 到達不能候補 / 低1 = CG3 の実装前の連携 / 参考12 = CG4 取りこぼし候補)。中3件は `MODULE-entrypoint-claude` が絶対パス起動するため shell 抽出器が辺を解決できないもので、根拠は `relations/MODULE-entrypoint-claude.md` の本文にある(2026-08-11 に `entrypoint-claude.sh:471` / `:482` / `:513` と `.devcontainer/Dockerfile.claude:260` / `:264` / `:268` で実在を再確認した)。低8 のうち `_destructive_done` / `_release_all_locks` の4件は、2026-08-11 に取りこぼしと判定して `features.md` の「到達しない関数についての判断」に記録した |
| Makefile を解析対象に含めるか | 含める(`callgraph-config.local.json` の `include_tooling: true`)。キット既定は Makefile を開発ツールとして外すが、`MOD-makefile` の 16 ターゲットは機能表が定義する境界の一部であり、外すと機能表と食い違う |
| 抽出器が無い領域 | Dockerfile と GitHub Actions。この2つはモジュールにせず `environments/images.md` と `infra/local/ghcr.md` が記述を持つ(`DSN-mod-05`) |
