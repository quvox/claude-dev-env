---
target: docs/03-impl/index.md
change: replace
version_bump: minor
sections:
  - "## この層の状態"
deletes: []
reason: 'issue 009 と issue 030 を閉じるための 03 層。**どちらも指摘の実体が消えている**: 009 が数えた「relations 本文のシグネチャ不一致 約27件」は対象が `MODULE-orchestrator-*` だけで、2026-08-08 のオーケストレーター削除でその relations ごと消えた(現在 `docs/03-impl/relations/` に `MODULE-orchestrator-*` は0本)。030 は「この節の乖離件数の記述が開いている issue と食い違う」という指摘で、根拠に挙げていた `013` / `014` は既に削除済みである。**本節はこの2つの issue を名指して「追跡はそちらが持つ」と書いているので、閉じると参照先が実在しなくなる**(CS11)。集計を維持する責任が本節自身にあることを書き、名指しを外す。あわせて「実装の欠陥として起票済み」の 9 件から、本タスクが修正する `023` / `047` / `087` / `088` / `101` の5件を外して **5件** にし、「この数に含めない」側に挙がっていた `051` / `054`(本タスクで解消・削除する)も外す。**この節は `build-index.py` の生成範囲ではなく手で保守する節である**(`.claude/directions/03-impl.md` の Files)'
reflected: 2026-08-12
---

## この層の状態

| 項目 | 値 |
|---|---|
| 機能間連携仕様書の本数 | 61 |
| 網羅しているモジュール | MOD-cli-common, MOD-cli-setup, MOD-cli-start, MOD-cli-stop, MOD-cli-attach, MOD-cli-code, MOD-cli-list, MOD-cli-login, MOD-cli-login-codex, MOD-cli-logout, MOD-cli-forward, MOD-cli-unforward, MOD-cli-ports, MOD-cli-ssh-keys, MOD-cli-firewall, MOD-cli-pull, MOD-cli-upgrade, MOD-cli-reset, MOD-makefile, MOD-entrypoint, MOD-firewall, MOD-docker-proxy, MOD-portsync, MOD-vm-mode, MOD-container-tools(25モジュール) |
| `check-relations.py` 最終結果 | 合格(2026-08-11 の `task-promote-shared-helpers` 反映後に再実行。61 ファイル / 61 ID。対称性・参照実在・impl パス・必須項目・機能表との 1:1 すべて問題なし) |
| コードとの乖離として未解決のもの | **1 件** — `docs/issues/097`(CLI の `help\|*)` 分岐が実在するのに機能表にも relations にも無い。`claude-dev:2183` / `claude-dev-mac:2207`)。**2026-08-11 に原因を実測した**: シェル抽出器の決定 D「catch-all(`*` を含むラベル)は入口にしない」が**ラベル全体を落とす**ため、`help` の側も巻き添えで入口から外れる(`.claude/scripts/cgx/shell_regex.py:169`)。したがって機能表に行を足すと FT1 が重大度「高」で落ちる。解消にはコード側で `help)` と `*)` を分けるか抽出器を直すかが要り、どちらも `task-promote-shared-helpers` の範囲外だった。**戻り値の記述の食い違い4件は 2026-08-11 に修正して 0 件になった**(`MODULE-cli-logout` / `-reset` / `-start` / `-stop` の終了コード 130 の区間)。機能の欠落として数えていた 1 件(macOS のコントローラ生存判定が無い。issue `003`。対象ごと消えたため issue も削除した)は、`orchestrate` サブコマンドごと消えた。本文の叙述レベルの食い違いとして数えていた 17 件も、対象が `MODULE-orchestrator-*` の relations だけだったため対象ごと消えた(**2026-08-11 に実測して 0 件であることを確認し、これを追跡していた issue を閉じた**。「本文で `ctx` 等の定型引数を省略してよいかの規約が無い」という規約側の欠落だけが残るので、`docs/pendings.md` の残務が持つ)。**この集計そのものを維持する責任は本節にある**(以前は別の issue が追跡していたが、追跡先を本節へ一本化した) |
| 実装の欠陥として起票済み(コードは未修正) | **5件**(2026-08-11 の `task-issue-sweep` 反映後)。数え方は「`03-impl` のいずれかの `## 既知の制限` から参照されている `type: modify` / `type: bug` の issue」のうち、**本システムが未修正のもの**とする: `docs/issues/002`(`.claude-dev.yaml` が全面上書きされる)/ `005`(docker-proxy が解釈できないボディを検査せず中継する)/ `010`(forward のホストポート選択の競合)/ `028`(名前の一意性が `NFR-scale-01` を満たさない)/ `055`(受入基準17 が停止中のラベル無しコンテナの列挙まで求めるが 02 は稼働中しか列挙できないとする。`MODULE-cli-reset.md` の「既知の制限」から参照。**コードの欠陥ではなく 01 ⇄ 02 の食い違いだが、数え方の定義を満たすためこの数に含める** — 2026-08-11 に数え漏れを是正した)。**2026-08-08 のオーケストレーター削除で 10 件(`001` / `011` / `012` / `013` / `015` / `021` / `022` / `026` / `057` / `058`)が対象の実装ごと消え、21 件から 11 件になった(2026-08-11 に `055` の数え漏れを加えて 12 件)。**2026-08-11 の `task-fix-logout-zero-target-path` で `052` / `053` / `089` の3件を修正して外し、同タスクが検出した `098` / `099` / `100` の3件を加えたので 11 件になった。続く `task-fix-logout-records-and-marker` でその3件を修正して外し、同タスクが検出した `101` を加えたので 9 件になった。**続く `task-issue-sweep` が `023` / `047` / `087` / `088` / `101` の5件を修正して外したので **5件** である。** `014` / `046` は、どの「既知の制限」からも参照されていないためこの数に含めない(いずれもコードは未修正である。集計の対象は「既知の制限」から参照されているものに限る、という数え方の定義による)。**この集計そのものを維持する責任は本節にある** |
| `relations-coverage.py` 最終結果 | 合格(2026-08-11 の `task-promote-shared-helpers` 反映後に再実行。機能間連携仕様書 61 本 / エントリポイント候補 0 件 / 未記載 0 件)。**あわせて「要確認 66 件(impl のファイルにエントリポイント候補が無い)」を出す** — これは合否とは独立の出力で、パターンが覆っていない領域の申告である(スクリプトはこれを不合格に数えない)。**2026-08-07 に検出していた未記載 30 件は、その全件が `scan-entrypoints.py` の Go `switch` 誤検出(orchestrator の設定キー・TUI のキー入力・JSON の型識別子・git のサブコマンド文字列)であり、対象の実装ごと消えた。** 残る Go は `docker-proxy/` だけで、コードとの一致は `callgraph-check.py` と `check-relations.py` が担保する。**ただし「未記載 0 件」は機械が拾える入口に限った主張である**: 2026-08-11 の独立レビューが `claude-dev:2183` / `claude-dev-mac:2207` の `help|*)` 分岐を検出し、これは shell 抽出器(Tier 3)が入口として取り出さないため FT2 にも本検査にも現れない(`docs/issues/097`) |
