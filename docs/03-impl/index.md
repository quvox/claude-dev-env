---
id: index
version: 1.34.1
updated: 2026-08-20
source:
  - docs/02-design/system.md
  - docs/02-design/relations.md
summary: 03-impl 層の目次。機能間連携仕様書群の代表として層全体の版と合格証を持つ
keywords: [目次]
verified:
  at: 2026-08-20
  version: 1.34.0
  against:
    - {doc: docs/02-design/system.md, version: 2.17.0}
    - {doc: docs/02-design/relations.md, version: 1.12.0}
---

# 03-impl 目次

## この層の状態

| 項目 | 値 |
|---|---|
| 機能間連携仕様書の本数 | 61 |
| 網羅しているモジュール | MOD-cli-common, MOD-cli-setup, MOD-cli-start, MOD-cli-stop, MOD-cli-attach, MOD-cli-code, MOD-cli-list, MOD-cli-login, MOD-cli-login-codex, MOD-cli-logout, MOD-cli-forward, MOD-cli-unforward, MOD-cli-ports, MOD-cli-ssh-keys, MOD-cli-firewall, MOD-cli-pull, MOD-cli-upgrade, MOD-cli-reset, MOD-makefile, MOD-entrypoint, MOD-firewall, MOD-docker-proxy, MOD-portsync, MOD-vm-mode, MOD-container-tools(25モジュール) |
| `check-relations.py` 最終結果 | 合格(2026-08-20 の F3 実装整合フロー(`/verify-impl all`)で再実行。61 ファイル / 61 ID。対称性・参照実在・impl パス・必須項目・機能表との 1:1 すべて問題なし) |
| コードとの乖離として未解決のもの | **1 件** — `docs/issues/097`(CLI の `help\|*)` 分岐が実在するのに機能表にも relations にも無い。`claude-dev:2651` / `claude-dev-mac:2693`)。**2026-08-11 に原因を実測した**: シェル抽出器の決定 D「catch-all(`*` を含むラベル)は入口にしない」が**ラベル全体を落とす**ため、`help` の側も巻き添えで入口から外れる(`.claude/scripts/cgx/shell_regex.py:169`)。したがって機能表に行を足すと FT1 が重大度「高」で落ちる。解消にはコード側で `help)` と `*)` を分けるか抽出器を直すかが要り、どちらも `task-promote-shared-helpers` の範囲外だった。**戻り値の記述の食い違い4件は 2026-08-11 に修正して 0 件になった**(`MODULE-cli-logout` / `-reset` / `-start` / `-stop` の終了コード 130 の区間)。機能の欠落として数えていた 1 件(macOS のコントローラ生存判定が無い。issue `003`。対象ごと消えたため issue も削除した)は、`orchestrate` サブコマンドごと消えた。本文の叙述レベルの食い違いとして数えていた 17 件も、対象が `MODULE-orchestrator-*` の relations だけだったため対象ごと消えた(**2026-08-11 に実測して 0 件であることを確認し、これを追跡していた issue を閉じた**。「本文で `ctx` 等の定型引数を省略してよいかの規約が無い」という規約側の欠落だけが残るので、`docs/pendings.md` の残務が持つ)。**この集計そのものを維持する責任は本節にある**(以前は別の issue が追跡していたが、追跡先を本節へ一本化した) |
| 実装の欠陥として起票済み(コードは未修正) | **4件**(**2026-08-20 の `fix-start-auxiliary-halts-and-tmux-runtime-env` の完了時点**)。数え方は「`03-impl` のいずれかの `## 既知の制限` から参照されている `type: modify` / `type: bug` の issue」のうち、**本システムが未修正のもの**とする: `005`(docker-proxy が解釈できないボディを検査せず中継する)/ `010`(forward のホストポート選択の競合)/ `028`(名前の一意性が `NFR-scale-01` を満たさない)/ `055`(受入基準17 が停止中のラベル無しコンテナの列挙まで求めるが 02 は稼働中しか列挙できないとする)。**`106`(`~/.local/bin` のコピーと `~/.ssh/config` の加工が `set -e` の下で握られておらず、読めないと `start` が起動まで到達しない)は 2026-08-20 の `fix-start-auxiliary-halts-and-tmux-runtime-env` でコードを直して解消し、issue を削除した**ので 5件 → 4件になった(`MODULE-cli-start.md` の「既知の制限」からの参照も同時に外した)。**同タスクが `002`(`.claude-dev.yaml` の全面上書き。経緯は `docs/histories/2026-08-19-stop-cleanup-and-project-env.md`。issue は同日に削除した)をコードごと修正して外した**ので 5件 → 4件になり、**同タスクの範囲外だった同型の残り2箇所を `106` として起票した**ので 5件 になった。同タスクの3回の `/doc-check ssot` が検出した実装欠陥5件(`reset` が `--volumes` を解析しない / 既存の `.gitignore` へ書き込めない / `.gitignore` を新規作成できない / 読み取り権限の無い env ファイル / 壊れた `settings.json`)は、**いずれも同じタスクの中でコードを直して解消したので issue を残していない**(`.claude/directions/issues-pendings.md` §1 の行1)。**`102`(colabtmux が bwrap の非ゼロを理由に codex を起こさない)は 2026-08-20 に人間の裁定で削除した** — もともとどの `03-impl` の「既知の制限」からも参照されておらず、数え方の定義によりこの数に入っていなかったので、削除でこの数は変わらない(経緯は `docs/histories/2026-08-20-delete-issue-102-per-human-adjudication.md`)。**2026-08-08 のオーケストレーター削除で 10 件が対象の実装ごと消え、21 件から 11 件になった(2026-08-11 に `055` の数え漏れを加えて 12 件)。****2026-08-11 の `task-fix-logout-zero-target-path` で3件を修正して外し、同タスクが検出した3件を加えたので 11 件になった。続く `task-fix-logout-records-and-marker` でその3件を修正して外し `101` を加えたので 9 件になった。続く `task-issue-sweep` が5件を修正して外したので 5件 になっていた。** **`046`(list / make status / make clean の数え落とし)は 2026-08-20 の `fix-session-list-undercount` で修正し、issue を削除した**(どの「既知の制限」からも参照されていなかったため、この数は変わらない)。**この集計そのものを維持する責任は本節にある** |
| `relations-coverage.py` 最終結果 | 合格(2026-08-11 の `task-promote-shared-helpers` 反映後に再実行。機能間連携仕様書 61 本 / エントリポイント候補 0 件 / 未記載 0 件)。**あわせて「要確認 66 件(impl のファイルにエントリポイント候補が無い)」を出す** — これは合否とは独立の出力で、パターンが覆っていない領域の申告である(スクリプトはこれを不合格に数えない)。**2026-08-07 に検出していた未記載 30 件は、その全件が `scan-entrypoints.py` の Go `switch` 誤検出(orchestrator の設定キー・TUI のキー入力・JSON の型識別子・git のサブコマンド文字列)であり、対象の実装ごと消えた。** 残る Go は `docker-proxy/` だけで、コードとの一致は `callgraph-check.py` と `check-relations.py` が担保する。**ただし「未記載 0 件」は機械が拾える入口に限った主張である**: 2026-08-11 の独立レビューが `claude-dev:2651` / `claude-dev-mac:2693` の `help|*)` 分岐を検出し、これは shell 抽出器(Tier 3)が入口として取り出さないため FT2 にも本検査にも現れない(`docs/issues/097`) |

## 02 との差分(未解消のもの)

| 種別 | 対象 | 内容 | 対処 |
|---|---|---|---|

**未解消の差分は無い。** **2026-08-20 の `fix-start-auxiliary-halts-and-tmux-runtime-env` が
最後の1件(契約の守備範囲 — 環境変数の到達義務が受け側を `entrypoint` と名指していたため、
ホスト CLI が `docker exec` で tmux サーバを作り直す経路を覆っていなかった件。issue は解消して削除した)を
解消した**: 契約の義務の主語を「コンテナ内でプロセスの木を新しく起こす側」へ広げ、
`実行時に決まる環境変数の受け渡し(/etc/claude-dev/runtime.env)` を新設して両経路が同じ値を
使うようにした(経緯は `docs/histories/2026-08-20-fix-start-auxiliary-halts-and-tmux-runtime-env.md`)。

(以下は **2026-08-19 の `task-fix-tmux-server-drops-reserved-env` 反映後の再確認**で、いずれも今も成立する。同タスクは
entrypoint が tmux セッションを起こす形を `su -l` から `su`(`-l` なし)へ変え、コンテナへ渡した
環境変数が tmux の窓の中の全プロセスから参照できるようにしたが、**新しい機能を1本も作っていない**
(既存の `MODULE-entrypoint-claude` の内部に閉じる)。`PLAN-*` と `MODULE-*` は 61 対 61 のままで、
機械が出した辺も 88 本で反映の前後に増減が無い。`check-changeset.py` の CS9、`callgraph-check.py` の
CG3/CG4、`check-relations.py`、`check-contracts.py` で確認した。
以下は 2026-08-19 の `task-stop-cleanup-and-project-env` 反映後の確認で、いずれも今も成立する。同タスクは
`stop` / `reset` の片付けへ名前付きボリュームと匿名ボリュームを加え、プロジェクトごとの環境変数の
受け渡しを新設したが、**新しい機能を1本も作っていない**(環境ファイルの読み取りは `MOD-cli-start`
の内部に閉じ、共有基盤へ上げる条件〈ファンイン2以上〉を満たさない — `DSN-env-05` / `PLAN-cli-start`)。
`PLAN-*` と `MODULE-*` は 61 対 61 のままで、機械が出した辺も 88 本で反映の前後に増減が無い。
`check-changeset.py` の CS9、`callgraph-check.py` の CG3/CG4、`check-relations.py` で確認した。
以下は 2026-08-18 の `task-bundle-external-binaries` 反映後の確認で、いずれも今も成立する。同タスクは `FR-env-13`(同梱外部バイナリ)を新設したが、**実体はコンテナイメージの定義であり `DSN-mod-05` によりモジュールを持たない**ので、`PLAN-*` も `MODULE-*` も1本も増減していない〈機能 61 / 機械が出した辺 88 が反映の前後で同数〉。担い手は `03-impl/environments/images.md` である。以下は 2026-08-12 の `task-issue-sweep` 反映後の確認で、いずれも今も成立する。この反映は `PLAN-*` の辺を1本も増減させていない(機能 61 / 機械が出した辺 88 は反映の前後で同数)。`PLAN-*` と `MODULE-*` は
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
| [images](environments/images.md) | 1.2.0 | 2026-08-18 | 配布イメージ(claude-cli / claude-vnc)のステージ構成・ビルド引数・キャッシュの効かせ方 |
| [local-docker-resources](infra/local/docker-resources.md) | 1.2.0 | 2026-08-07 | ホスト上に作られる Docker リソース(ネットワーク・ボリューム・コンテナ)の一覧と命名規則 |
| [local-ghcr](infra/local/ghcr.md) | 1.2.0 | 2026-08-18 | 配布イメージの公開先 GHCR の構成(リポジトリ・タグ・マルチアーキ・認証の置き場所) |

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
| `callgraph-check.py` の未解決指摘 | 指摘 24 件・**重大度「高」ゼロ**(2026-08-11 に SSOT に対して実行。中3 = CG3 のプロセス跨ぎ連携 / 低8 = CG2 到達不能候補 / 低1 = CG3 の実装前の連携 / 参考12 = CG4 取りこぼし候補)。中3件は `MODULE-entrypoint-claude` が絶対パス起動するため shell 抽出器が辺を解決できないもので、根拠は `relations/MODULE-entrypoint-claude.md` の本文にある(2026-08-11 に `entrypoint-claude.sh:476` / `:487` / `:522` と `.devcontainer/Dockerfile.claude:260` / `:264` / `:268` で実在を再確認した)。低8 のうち `_destructive_done` / `_release_all_locks` の4件は、2026-08-11 に取りこぼしと判定して `features.md` の「到達しない関数についての判断」に記録した |
| Makefile を解析対象に含めるか | 含める(`callgraph-config.local.json` の `include_tooling: true`)。キット既定は Makefile を開発ツールとして外すが、`MOD-makefile` の 16 ターゲットは機能表が定義する境界の一部であり、外すと機能表と食い違う |
| 抽出器が無い領域 | Dockerfile と GitHub Actions。この2つはモジュールにせず `environments/images.md` と `infra/local/ghcr.md` が記述を持つ(`DSN-mod-05`) |
