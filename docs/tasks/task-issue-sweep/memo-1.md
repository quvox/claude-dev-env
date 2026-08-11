# task-issue-sweep memo-1(調査メモ)

> memo.md から移動した調査メモ。フェーズ2のドライラン パス2 までに集めた事実で、1行1事実・`path:line` つき。**タスクとともに消える派生キャッシュであり SSOT ではない**(コードや 03-impl と矛盾したらコード側が正)。
## 調査メモ

| # | 調べたこと | 判明した事実 | 出どころ |
|---|---|---|---|
| 1 | 051 が生きているか | `docker network create` の標準出力(ネットワーク ID)を捨てておらず利用者向け出力に混じる。stderr だけを捨てている | `claude-dev:353` / `claude-dev:761` |
| 2 | 088 が生きているか | compose 既定ネットワークの削除は成功時だけ `_spawned_deleted` へ積み、失敗を記録する経路が無い | `claude-dev:1728` |
| 3 | 023 が生きているか | ホスト環境変数を無検証で受け、非空ならブリッジの接続先として使う。Linux 版には無く macOS 版だけの経路 | `claude-dev-mac:274` |
| 4 | 047 の削除対象 | `claude-dev-vm-<name>` を消すのは `--vm-fresh` の経路だけで、`reset` の削除対象には無い | `claude-dev:1476` |
| 5 | 契約は VM ボリュームを本システムの資源と認めているか | 共有ボリュームの識別手段の行が接頭辞 `claude-dev-vm-` を挙げている(名前で所有権が読み取れる資源) | `docs/02-design/contracts/cli-container.md:340` |
| 6 | 047 で書き換える列挙の正はどこか | `reset` の削除対象の列挙は logging.md の当該行が正で、共有ボリュームは `claude-dev-auth` / `-history` / `-config` / `claude-dev-chrome-*` の4つしか挙げていない | `docs/02-design/logging.md:61` |
| 7 | 101 の仕様側 | 「残したものの表示は削除の成否で条件づけない。失敗して終了コード 1 で終わる実行でも表示する」と既に定めている(実装が仕様に追いついていない = 起点 03) | `docs/02-design/logging.md:109` |
| 8 | 088 の仕様側 | 「セッション由来の資源の削除に失敗した」WARN 行が消えなかった資源の名前と種別を求めている | `docs/02-design/logging.md:71` |
| 9 | 087 の仕様側 | 「所有者ラベルを付与せずに中継した」INFO 行が付与しなかった理由の出力を求めている | `docs/02-design/logging.md:85` |
| 10 | 056 の文言がどこに逐語で在るか | 受入基準・契約・ログ仕様・relations・E2E 手順の5層に「本変更より前に起動した可能性がある」が逐語で在る | `docs/01-requirements/functional.md:121` / `docs/02-design/contracts/cli-container.md:127` / `docs/02-design/logging.md:64` |
| 11 | 009 / 030 の実体 | `docs/03-impl/relations/` に `MODULE-orchestrator-*` は 0 本(全 64 本を機械計数) | `ls docs/03-impl/relations/` |
| 12 | 054 の母集団(凍結) | CS11 の参照切れは **16 箇所 / 11 ファイル**(00: auth.md 1・env.md 2・sec.md 1 / 02: contracts/cli-container.md 3 / 03: contracts/cli-container.md 1・MODULE-cli-login-codex 1・MODULE-cli-login 1・MODULE-cli-logout 1・MODULE-cli-reset 1・MODULE-cli-start 2・tests/cli-pull 1・tests/e2e 1) | `check-changeset.py --ssot docs` の CS11 |
| 13 | 077 の母集団(凍結) | 旧表記「受入基準 N」は **19 ファイル 188 箇所**(起票時の「23 ファイル 181 箇所」は陳腐化) | `grep -rl "受入基準 [0-9]" docs/03-impl/tests/*.md` |
| 14 | 084 の母集団(凍結) | 「## テスト設計の判断」の欠落は **19 ファイル**(起票時 32 → 26 → 19) | `check-changeset.py --ssot docs` の CS19 |
| 15 | 095 の母集団(凍結) | 程度語「通常」は **1 箇所**(起票時の「24 箇所」は陳腐化) | `docs/03-impl/relations/MODULE-cli-unforward.md:49` |
| 16 | 066 の母集団 | 挙げられた6件のうち `NFR-perf-03` は 2026-08-08 に廃止済みで、現存は5件 | `docs/01-requirements/non-functional.md:25` |
| 17 | 048 の実体 | 02 の宣言は既に「共有基盤どうしの呼び出しは一方向で循環しないものに限る」へ改まっており、issue が問題にした「呼び合わない」という宣言は本文に無い。残るのは追跡の1文だけ | `docs/02-design/relations.md:227` / `:232` |
| 18 | 065 の実体 | 「代替レビュー(サブエージェント)のモデル・reasoning」の行は既に在るが、**代替してよいかという可否**を書く欄が無い | `docs/02-design/environments.md:144` |
| 19 | 004 の被参照 | 00 層の `D0-scope-07` の 関連 行が「**閉じずに残る**」と書いており、降格すると 00 の記述と食い違う | `docs/00-requests/decisions/scope.md:140` |
| 20 | 009 / 030 の被参照 | `docs/03-impl/index.md:27` と `:28` が両方を名指して「集計の維持そのものは `docs/issues/030` で追跡する」と書いている | `docs/03-impl/index.md:27` |
| 21 | 合格証の状態 | closure 内を含む SSOT 全 125 ファイルで、`verified.version` が自身の MAJOR.MINOR と食い違うものは 0 件 | frontmatter の機械照合 |
| 22 | SSOT 全体検査の母集団(凍結) | `check-changeset.py --ssot docs` は 125 ファイル・違反 75 件(CS8 11 / CS11 16 / CS19 19 / CS20 29)。CS20 の 29 件は「issue に `origin_layer` が無い」で、24 件は本タスクで削除され、5 件は範囲外の issue に残る | `check-changeset.py --ssot docs` |
| 23 | `reset` の下流 | `MODULE-cli-reset` を呼ぶ上流は 0 件(入口機能)。`FR-env-03` を実装する機能は 14 件で、うち `reset` に関わるのは `MODULE-cli-common-destructive` / `-lock` / `-net-other-running-containers` / `-spawned-resources` / `MODULE-makefile-clean` | `relations-query.py --upstream MODULE-cli-reset` / `--requirement FR-env-03` |
| 25 | 077 の母集団の訂正(**重要**) | 旧表記 188 箇所のうち**条項ID へ機械変換できるのは 18 ファイル 127 箇所**で、いずれも「未検証(テスト未実装)の全件」節の「対象」列にある(issue 077 が名指す場所そのもの)。残り **61 箇所は `e2e.md`(43)と `cli-logout.md`(8)ほかの散文中の参照**で、`FR-env-01` 受入基準 14〜27 のような**範囲表記**を含み条項ID へ機械変換できない | `grep` + 変換可能性の機械判定 |
| 26 | 101 の実装位置 | `destructive_report >&2` の直後に `exit 1` があり、ラベル無しコンテナの表示(`_rc_unmanaged`)はその**後ろ**にあるので、失敗した実行では到達しない | `claude-dev:2264`〜`:2272` |
| 27 | 047 の実装位置 | `reset` の削除対象ボリュームは `_rc_volumes` に集める。固定3本を `docker volume inspect` で確かめ、`claude-dev-chrome-*` を列挙して足している。`claude-dev-vm-*` を列挙する行が無い | `claude-dev:2059`〜`:2064` |
| 28 | 051 の実装位置 | `docker network create "$NETWORK" 2>/dev/null \|\| true` が4箇所(Linux 2・macOS 2)。いずれも標準エラーだけを捨てている | `claude-dev:353` / `:761` / `claude-dev-mac:418` / `:828` |
| 29 | 088 の実装位置 | compose 既定ネットワークの削除は `if docker network rm ... ; then _spawned_deleted+=(...)` の形で、`else` 節が無い | `claude-dev:1728` / `claude-dev-mac:1737` |
| 30 | 087 の実装位置 | ネットワーク経路は `owner == ""` と「書き換えられない」の2つを `NO-OWNER-LABEL` として出すが、コンテナ経路は `labelled` と `owner == ""` の2分岐しかない | `docker-proxy/main.go:357`〜`:363` / `:707`〜`:710` |
| 31 | 023 の実装位置 | `ensure_ssh_bridge` が `local port="${CLAUDE_DEV_SSH_BRIDGE_PORT:-}"` でホスト環境変数を読む。**Linux 版にこの経路は無い** | `claude-dev-mac:274` |
| 24 | テストの有無 | `claude-dev` / `claude-dev-mac` を変更したときに走らせるべき自動テストは 0 件(シェルは実機確認。`SR-32` / `DSN-test-01`)。`docker-proxy/main.go` は 39 件 | `relations-query.py --impact` |

