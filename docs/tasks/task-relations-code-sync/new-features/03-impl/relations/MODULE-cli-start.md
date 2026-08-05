---
target: docs/03-impl/relations/MODULE-cli-start.md
change: replace
sections:
  - "### MODULE-entrypoint-claude"
  - "## 戻り値・副作用"
  - "## 既知の制限"
deletes: []
reason: entrypoint の副作用(codex config.toml 補完・CLAUDE.md 自動更新・VNC 時の MCP 設定更新)が連携内容にも永続化にも無い(docs/issues/038 #9)。entrypoint 起動箇所として挙げる行番号が別の処理を指している(同 #26)
reflected: 2026-08-05
id: MODULE-cli-start
module: MOD-cli-start
kind: tool
sync: sync
impl: claude-dev::main#start, claude-dev-mac::main#start
callers: MODULE-cli-orchestrate
callees: MODULE-entrypoint-claude, MODULE-cli-common-container-exists, MODULE-cli-common-container-name, MODULE-cli-common-dev-agent-path, MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-get-novnc-url, MODULE-cli-common-image-exists, MODULE-cli-common-is-running, MODULE-cli-common-lock, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user, MODULE-cli-common-select-ssh-keys, MODULE-cli-common-write-project-ssh-keys
contracts: CTR-cli-container
design: DSN-mod-01, DSN-mod-02, DSN-arch-01, DSN-auth-01, DSN-dist-02, DSN-env-01, DSN-env-02, DSN-env-03
requirements: FR-env-01, FR-env-02, FR-env-03, FR-env-04, FR-env-05, FR-env-06, FR-env-07, FR-env-08, FR-env-11, FR-env-12
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-05
summary: カレントディレクトリで開発コンテナを起動する(VNC+Chrome が既定)
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。frontmatter は `updated` の日付以外変更なし。
     行番号の根拠は 2026-08-05 に再確認した: claude-dev:710 / claude-dev-mac:777 は docker-proxy の
     docker run、claude-dev:1381 / claude-dev-mac:1414 が主コンテナの docker run である。

     2026-08-05 /doc-check(task) の自動修正(独立レンズ Codex readiness が重大度「高」で検出):
     「### 並行性」の表の2行が同じ入力で相反していた — 1行目が「同じディレクトリ(または basename が
     同じ別ディレクトリ)なら後発はロックを取れない」と書き、2行目が「別のディレクトリなら
     ロックのキーも別なので独立に成功する」と限定なしで書いていたため、**basename が同じ別ディレクトリ**が
     両方に該当していた。コードで裏取りしたところプロジェクト単位のロックキーは
     `claude-dev:245`〜`:251`(`project_name` = pwd の basename を小文字化して正規化)を
     `:396`〜`:401` の `_lock_path` が使うので、**1行目が正**である(同じ事実は docs/issues/028 が
     「名前だけで同一性を決めるため NFR-scale-01 を満たさない」として追跡している)。
     2行目に「basename が異なる場合だけ」の限定とキーの定義を足した。**この矛盾は現行 SSOT
     (MODULE-cli-start.md:288〜:289)にもあり、本変更指示が同じ節を書き替えるため同時に直した。** -->

### MODULE-entrypoint-claude

- 何のために呼ぶか: コンテナ内の初期化(UID/GID 追従・認証コピー・ファイアウォール適用・
  VNC/Chrome・tmux・同期ループ・ポート同期)を行わせるため。`docker run` でコンテナを作ると
  イメージの `ENTRYPOINT` として起動する(主コンテナの `docker run -d` は
  `claude-dev:1381` / `claude-dev-mac:1414`。手順15 の再試行ループの中にある)。
- 何を渡すか: 契約 `CTR-cli-container` が定める環境変数一式とマウント、`NET_ADMIN` / `NET_RAW`。
- 何を受け取るか: 直接の戻り値は無い。tmux が立ち上がった状態のコンテナ。
  **プロジェクトディレクトリ配下への書き込みがこの経路で起きる**(`start` 自身の副作用ではないが、
  `start` を実行すると必ず起こる):
  `/workspace/.codex/config.toml` の作成と既定鍵の補完(`scripts/entrypoint-claude.sh:243`〜`:406`)/
  `/workspace/CLAUDE.md` のマーカー範囲(`<!-- claude-dev-auto-start -->` 〜)の削除と再生成
  (`:517`〜`:608`。ファイルが無ければ作る)/ VNC 有効時の `/workspace/.mcp.json` への
  `chrome-devtools` と `computer-use` の定義追加、`/workspace/.claude/.claude.json` の
  `enabledMcpjsonServers` 更新(`:611`〜`:674`)。詳細は `MODULE-entrypoint-claude` の
  手順17・18 と同ファイルの `永続化` 欄が正である。
- **失敗したときどうなるか**: `docker run` が非0なら起動失敗として扱う。entrypoint 内部の
  補助処理(ファイアウォール等)の失敗は `|| true` で握られ、起動は継続する。
- **注記**: これは関数呼び出しではなく**プロセス境界をまたぐ起動**である。コールグラフには
  現れないため `callgraph-check.py` は CG3「低」として出すが、実在する連携である。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(tmux 待ちタイムアウトでも 0)。前提不足・KVM 不在・リトライ上限超過・**同名コンテナとの衝突**・**ロックを取得できない**場合は 1 |
| 永続化 | コンテナ `<name>`(**管理ラベル `claude-dev.managed=1` / `claude-dev.role=claude` / `claude-dev.project-dir=<起動ディレクトリの絶対パス>` 付き**)。`${PROJECT_DIR}/.claude/`(認証・`host-hooks.json`・`host-local-bin/`)、`${PROJECT_DIR}/.codex/auth.json`、`${PROJECT_DIR}/.gitignore` への追記、`${PROJECT_DIR}/.claude-dev.yaml`。docker volume `claude-dev-auth` / `claude-dev-history` / `claude-dev-config` / `claude-dev-chrome-<name>` / (VM 時)`claude-dev-vm-<name>`。**ロックのシンボリックリンク `${HOME}/.claude-dev/locks/proj-<name>.lock` と `shared.lock` を作成・削除する**。macOS では `~/.claude-dev/agents/<name>.{sock,pid,bridge.pid,bridge.port}`。**docker-proxy にはラベルを付けない**。**さらに entrypoint がプロジェクト配下へ書く**: `/workspace/.codex/config.toml`(既定鍵の補完)・`/workspace/CLAUDE.md`(マーカー範囲の再生成)・VNC 時の `/workspace/.mcp.json` と `/workspace/.claude/.claude.json`(いずれも `MODULE-entrypoint-claude` の副作用。**`start` を実行すると必ず起きる**) |
| 発火するイベント | なし |
| ログ | 標準出力へイメージ名・バージョン・noVNC URL・進捗。失敗とロックの取得失敗・残骸の引き継ぎは stderr |

### 副作用の順序と、途中で失敗したときに残るもの

**トランザクションは無い。** スクリプトは `set -e`(`claude-dev:8`)で走るため、下表のいずれかで
失敗するとその時点で終了し、**それまでの副作用は残ったまま**になる。取り消し処理は無い。
**ただしロックだけは `trap` が必ず解放する。**

| # | 副作用 | 失敗したときに残るもの | 再実行での回復 |
|---|---|---|---|
| 1 | **プロジェクト単位のロックの取得**(手順3) | シンボリックリンク1本。`trap` が解放する | 取れなければ以降の副作用は1つも起きない |
| 2 | `require_setup` によるイメージのビルド(手順4) | ビルド済みのイメージ(冪等に作られる共有資源) | 既にあれば何も起きない |
| 3 | `.claude-dev.yaml` の作成(無いときだけ) | 作られたファイル | 既にあれば作り直さない |
| 4 | 停止中の同名コンテナの削除(**稼働中なら削除しない**) | 削除済みの状態。稼働中だった場合は何も変わらない | 影響なし |
| 5 | ネットワーク・共有ボリュームの作成 | 作られた資源(他プロジェクトと共有) | すべて `\|\| true` で握られ、再実行しても増えない |
| 6 | **共有資源単位のロックの取得**(手順9) | シンボリックリンク1本。`trap` が解放する | 取れなければ認証コピー以降は1つも起きない |
| 7 | `${PROJECT_DIR}/.claude` と `.codex` の作成 + 認証コピー(一時コンテナ) | 空または部分的な作業用ディレクトリ | `mkdir -p` と `cp` なので**再実行で上書きされる** |
| 8 | `host-hooks.json` の書き出し | 書き出されたファイル | 毎回書き直す |
| 9 | `host-local-bin/` へのコピー | コピー済みのファイル | 毎回 `cp -a` で上書きする。**ホスト側で消したファイルは残り続ける**(同期ではない) |
| 10 | `.gitignore` への追記 | 追記済みの行 | 既に記載があれば追記しない(冪等) |
| 11 | `~/.ssh/config` の一時コピー作成(`mktemp`) | `/tmp/claude-dev-ssh-config.XXXXXX` が残る | **削除しない。実行のたびに1つ増える** |
| 12 | macOS の専用 agent / TCP ブリッジ起動 | プロセスと `~/.claude-dev/agents/<name>.*` | 既存を再利用する |
| 13 | `docker run`(コンテナ作成。**管理ラベル3つ付き**) | 失敗時は作りかけを `docker rm -f` する。**名前衝突のときは何も削除せず、稼働中のコンテナも削除しない** | 再試行またはやり直しで作られる。残った停止中コンテナは次回の手順8 が消す |
| 14 | コンテナ内の初期化(entrypoint) | 起動済みのコンテナ | `--restart unless-stopped` で残る。再実行は再接続経路に入る |

**回復点は「もう一度 `claude-dev start` を実行すること」**である。手順はいずれも再入可能で、
稼働中なら再接続経路(手順7)に入るため二重にコンテナを作らない。

### 並行性

**2段のロックで直列化する**(`CTR-cli-container` の「排他(ロックキー)」)。プロジェクト単位は
全区間、共有資源単位は認証コピーからコンテナ作成の確定まで。**待たない**ので、取得できなければ
理由を表示して終了コード 1 で終わる。**別プロジェクトの `start` 同士は直列化しない**
(プロジェクト単位のキーが異なるため。`NFR-scale-01`)。

| 同時に起きること | 実際の結果 |
|---|---|
| **同じ**ディレクトリで `start` を2つ(または basename が同じ別ディレクトリ) | **後発はプロジェクト単位のロックを取得できず、`.claude-dev.yaml` すら作らずに終了コード 1 で終わる**。ロックを取れた側だけが進む |
| **別**のディレクトリで `start` を2つ(**basename が異なる場合だけ**。同じ basename なら上の行が適用される) | コンテナ名・compose プロジェクト名・Chrome ボリュームが別で、**ロックのキーも別**なので独立に成功する(プロジェクト単位のロックキーは**起動ディレクトリの basename を正規化した値**であり、絶対パスではない。`claude-dev:245`〜`:251` の `project_name` / `container_name` と `:396`〜`:401` の `_lock_path`)。**直列化されるのは共有資源単位のキーを取る区間(認証コピー〜コンテナ作成の確定)だけ**。もう一つの競合点は noVNC の空きポート選定で、これはポート競合の再試行(最大20回)で吸収する |
| `start` と `stop` が同時 | **同じキーのロックで直列化される**。後発は取得できずに終了コード 1。**起動直後のコンテナが消える経路は閉じた** |
| `start` と `reset` / `logout` / `login` が同時 | **共有資源単位のキーで直列化される**。`start` は認証コピーの手前で取得を試み、取れなければ**認証が空のコンテナを作らずに**終了コード 1 で終わる(`docs/issues/020`) |
| 別プロジェクトの `start` と共有インフラの作成が同時 | ネットワーク・ボリュームの作成はすべて `\|\| true` で握るため、どちらが作っても問題にならない(**ロックの保護対象外**) |
| 利用者が直接 `docker run` / `docker start` する | **保護されない**。そのため手順8 の「稼働中でないことの再確認」を二重の防護として残している |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **コンテナ名が起動ディレクトリ名から決まるため一意でない** | 別ディレクトリの同名プロジェクトと衝突する。**管理ラベル `claude-dev.project-dir` により、衝突時にどのディレクトリのものかを事実として示せるようになった**が、名前の一意性自体は未解決 | `docs/issues/028` |
| **compose 一意化名のハッシュ衝突を検出しない** | 異なる絶対パスの先頭6桁が一致すると、一方の `stop` が他方の compose 資源を削除しうる | `docs/pendings.md` **P-005** |
| **ロックはホスト CLI のプロセス間でしか有効でない** | 利用者が直接 `docker run` / `docker start` する経路は防げない。そのため手順8 の「稼働中でないことの再確認」を二重の防護として残している | なし(契約 `CTR-cli-container`「ロックが守れない範囲」が明示) |
| **プロジェクト単位のロックを `tmux attach` の前に解放する** | アタッチ中は排他が効かないので、別プロセスの `stop` が走りうる | なし(閾値の外: アタッチ中も保持すると利用者が自分のセッションを止められなくなる。`MODULE-cli-start` 判断10) |
| **共有資源単位のロックは `start` の全区間では保持しない** | 手順1〜8 と手順16 以降は保護されない | なし(閾値の外: 全区間で保持すると別プロジェクトの `start` が互いに待ち `NFR-scale-01`(5プロジェクト同時起動)を損なう。判断9) |
| **`MODULE-cli-common-lock` を含めた呼び出し先が 13 件になった** | `relations-query.py --health` の「呼び出し先が多い機能(> 7)」に載る | なし(閾値の外: 分割は 02 の分割定義の見直し事項である) |

