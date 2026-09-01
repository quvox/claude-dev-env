---
slug: pyenv-nvm-in-claude-image
state: building
critical: false
origin: human-report
issue: なし
started: 2026-09-01T13:57:55+09:00
updated: 2026-09-01T13:57:55+09:00
commit: -
summary: claude イメージの base ステージへ pyenv の3系統(3.11.11/3.13.14/3.14.7)と nvm v0.40.6(Node 22/24/26 系列の最新)を入れる
---

# pyenv-nvm-in-claude-image — claude イメージに Python 3系統と nvm(Node 3系列)を入れる

## 目的・やらないこと

- 目的: 配布イメージの `base` ステージに、pyenv で CPython 3.11.11 / 3.13.14 / 3.14.7 の3本を、
  nvm v0.40.6 で Node の 22 / 24 / 26 系列それぞれの最新版を導入し、コンテナ内で切り替えて使える
  状態にする。
- やらないこと: 既存の fnm を置き換えない(削除も、既定 Node の移管もしない)。Node/Python の
  版を CI が解決して build-arg で渡す経路は増やさない(既存の同梱エージェント CLI の経路と
  混ぜない)。イメージのステージ構成を変えない。

## 影響範囲(closure)

- .devcontainer/Dockerfile.claude
- docs/03-impl/environments/images.md
- docs/03-impl/index.md(索引。build-index.py が再生成する共有生成物)

## 主張

- 触ったモジュールのテスト: green(`cd docker-proxy && go test ./...` → `ok  	github.com/quvox/claude-dev-env/docker-proxy	0.063s`)。
  **このタスクが触ったイメージのビルド定義には自動テストが無い**(`SR-32` / `docs/03-impl/tests/images.md` は全件が「未検証(テスト未実装)」で、実機確認で代替すると定めている)。
  代わりに、ビルドしたイメージを実際に起動して確かめた:
  `docker run --rm -u 1000:1000 -e HOME=/home/t-kubo --entrypoint /bin/bash claude-dev-claude:latest -c 'export PS1=x; source /etc/bash.bashrc; pyenv versions; python --version; nvm ls; node --version; nvm use 26 && node --version'`
  → `3.11.11` / `* 3.13.14 (set by …/.pyenv/version)` / `3.14.7`、`Python 3.13.14`、
  `v22.23.2` / `v24.20.0` / `v26.8.1`、`default -> 24 (-> v24.20.0 *)`、
  既定の `node --version` → `v24.20.0`(解決先は fnm の `fnm_multishells/…/bin/node`)、
  `nvm use 26` → `v26.8.1`(解決先は `.nvm/versions/node/v26.8.1/bin/node`)。
  ランチャーの退行が無いことも確かめた: `docker run --rm --entrypoint /bin/bash claude-dev-claude:latest -lc 'codex --version; chrome-devtools-mcp --version'`
  → `codex-cli 0.152.0` / `1.8.0`(シェル初期化の無い経路から解決できている = `FR-env-12-2` の経路は無傷)。
- lint / build: green(`cd docker-proxy && go vet ./...` → 出力なし・終了コード 0 /
  `make build-claude` → `✅ claude-dev-claude`・終了コード 0)
- 外部挙動の変化: あり(コンテナ内で `pyenv versions` が3本を、`nvm ls` が3系列を返すようになる。
  `python` / `node` の既定解決先は変えない)
- 認証・決済・不可逆への接触: なし
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 及第ライン)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | アカウント・権限・認証情報を作る/変える/消す経路をこのクロージャは持たない(イメージへの言語ランタイムの追加のみ) | — |
| BR-02 | 該当 | 導入する版は外部の配布元(nodejs.org / python.org)からビルド時に解決される値である | `docs/03-impl/environments/images.md`「言語ランタイムのバージョン管理」— 導入直後に `node --version` / `python --version` で解決結果を検証し、想定の系列でなければビルドを失敗させる |
| BR-03 | 非該当 | 利用者が値を決める識別子を、このタスクは1つも作らない。`.devcontainer/Dockerfile.claude:17` の `ARG USERNAME` はこのタスクより前から在るビルド引数で、値を決めるのはビルドする保守者である(このタスクは触っていない)。今回足した `NODE_LINES` / `PYTHON_VERSIONS` などは識別子ではなくバージョン文字列であり、`node --version` / `python --version` による突き合わせで検証している(BR-02 の落とし先) | — |
| BR-04 | 非該当 | プロセス境界でやり取りする構造化データ(API・キュー・保存された JSON)を扱わない。取得するのは配布元の実行ファイルとソース書庫であり、スキーマを持つ値ではない | — |
| BR-05 | 非該当 | 不可逆または影響の大きい操作を利用者に見せる経路が増えない。`.devcontainer/Dockerfile.claude:69` ほかの `rm -rf` はビルド中の一時ファイルの後始末であり、利用者の操作で起きるものではない(いずれもこのタスクより前から在る) | — |
| BR-06 | 非該当 | 推測されると困る値を生成しない | — |
| BR-07 | 非該当 | 主体ごとに可否が変わる対象を扱わない | — |
| BR-08 | 該当 | ビルド引数の値をシェルコマンドの引数として展開する経路がある | `.devcontainer/Dockerfile.claude` の pyenv / nvm 導入部 — すべての展開を二重引用で囲む。方針は `docs/03-impl/environments/images.md`「環境変数(ビルド引数)」に1行で記す |
| BR-09 | 非該当 | 秘密を突き合わせる経路が増えない | — |
| BR-10 | 非該当 | ブラウザから呼ばれる状態変更の経路を持たない | — |
| BR-11 | 非該当 | 失われるとサービスが続かない値の保存先を作らない・変えない(イメージは作り直せる) | — |

## 決定シート(回答済み)

- 問いなし(開示のみ)。`docs/sheets/pyenv-nvm-in-claude-image.md` は
  「曖昧さなし」1件・論点0件・委任0件で `check-sheet.py` SH4 の免除に当たったため、
  人間の回答を待たずに削除した(2026-09-01)。

### 作業指示が挙げた3つの論点を、シートに載せなかった理由(原則5)

| 論点 | 判定 | 理由 |
|---|---|---|
| nvm と fnm の共存方針(どちらが `node` の PATH 解決と既定版を持つか) | 載せない | **問う基準の条件2(後から戻しにくい)を満たさない** — 誤りはビルド定義の数行で戻り、データ移行も外部への再連絡も要らない。加えて答えは上流から一意に導ける: `FR-env-12-2` が「`codex` は対話シェル・非対話シェル・`docker exec` のいずれからも解決できること」を要求し、`.devcontainer/Dockerfile.claude:515-520` の実装がそれを fnm の `aliases/default/bin` で満たしている。`node` の解決先を nvm へ移すとこの条項が壊れる。よって fnm が既定を持ち続ける、が導出された事実である |
| Node の「stable 最新」の固定方法(CI 解決でピン留めするか、ビルド時に系列から解決するか) | 載せない | **条件2 を満たさない**(版の固定方法はビルド定義1行で切り替わる)。同層の前例も一意である: 同じイメージの `fnm install 24` と `pyenv latest -k ${PYTHON_VERSION}` はどちらもビルド時に系列から解決している。CI が版を解決して build-arg で渡す経路は `D0-dist-03`/`D0-dist-04`/`D0-dist-06` が**同梱エージェント CLI に限って**定めたものであり、開発ツールチェインには及んでいない(`docs/00-requests/decisions/dist.md:195-199` が2つの経路を混ぜないと述べている) |
| pyenv の `global` の既定をどれにするか | 載せない | **条件2 を満たさない**うえ、上流が答えている — 現行の既定は `PYTHON_VERSION=3.13` の系列であり、要望の3本にも 3.13.14 が含まれる。既定を動かさない選択が一意に決まる |

## 質問キュー(出口のシートの種)

- なし(出口でも空だった = お伺いする事項なし)

## 調査メモ

- `.devcontainer/Dockerfile.claude:136-149` — pyenv は `ARG PYTHON_VERSION=3.13` を `pyenv latest -k` で
  解決して1本だけ導入し `pyenv global` にしている。
- `.devcontainer/Dockerfile.claude:116-125` — fnm は `fnm install 24` / `fnm default 24` / `fnm install 22`。
  既定 Node は fnm の 24 系列である。
- `.devcontainer/Dockerfile.claude:515-520, 525-530, 581-586, 591-596` — `codex` と `chrome-devtools-mcp` の
  `/usr/local/bin` ランチャーは `${USER_HOME}/.local/share/fnm/aliases/default/bin` を PATH に前置して
  実体を exec する。`FR-env-12-2`(codex が対話・非対話・`docker exec` のいずれからも解決できること)は
  この経路に依存している。
- `.devcontainer/Dockerfile.claude:226-250` — シェル初期化は `/etc/zsh/zshrc` と `/etc/bash.bashrc` に
  書かれ、fnm → pyenv の順で初期化する。`ENV PATH=` の行はファイル中に1つも無い。
- `docs/03-impl/environments/images.md:148-163` — ビルド引数の表。`PYTHON_VERSION` は既定 `3.13`。
  Node/fnm の版はこの表に無い。
- `docs/01-requirements/non-functional.md:23`(NFR-perf-02)— ブラウザ確認ありイメージだけが持つ層に
  「開発ツール・言語ランタイム」が1件でも現れたら不合格。したがって pyenv/nvm は `base` に置くほかない。
- `docs/00-requests/request.md:63`(やらないこと6)— ビルド時の自動取得を禁じているのは
  **同梱する外部実行ファイル**(`externals/`、`D0-dist-05`)についてである。
  `docs/00-requests/decisions/dist.md:195-199` が、公開パッケージを版解決して導入する経路を
  それとは別物として明示している。開発ツールチェインの導入(既存の pyenv/fnm/Go)はこの禁止の対象外。
- 版の実在をビルド前に確認した: Node 22 系最新 v22.23.2 / 24 系 v24.20.0 / 26 系 v26.8.1、
  nvm `v0.40.6` の install.sh が HTTP 200、CPython 3.11.11 / 3.13.14 / 3.14.7 の書庫が HTTP 200。
- `check-ssot.py docs` の凍結: 違反9件。**クロージャの中に在るものは0件**
  (内訳は issues の `origin_layer` 欠落4件、`00-requests/acceptances.md` ほかの件数の主張4件、
  `02-design/environments.md:58` の E2E 台本の置き場1件)。手を付けない。
- 負債の計器(着手時): 課題票 6 件 / 残務 50 行 / 未検証の構築記録 2 件 / 未回答シート 0 件。

## 進捗メモ(再開点)

- 2026-09-01 13:57 クロージャを確定。起点層を 03-impl と判定した(00/01/02 は変更なし。理由は下記)。
- 2026-09-01 14:20 `.devcontainer/Dockerfile.claude` を実装。fnm の直後に nvm の導入ブロックを足し、
  pyenv を1本から3本(`PYTHON_VERSIONS`)へ、シェル初期化に nvm の `--no-use` 読み込みを足した。
- 2026-09-01 14:25 [DS-04](設定を AI が決めてよい委任) nvm を `base` ステージへ置く — 理由:
  `NFR-perf-02` が「ブラウザ確認ありイメージだけが持つ層に言語ランタイムが1件でも現れたら不合格」と
  定めており、置ける場所が `base` しかない / 見直す条件: `NFR-perf-02` の6カテゴリが変わったとき
  (記録先: `docs/03-impl/environments/images.md`)
- 2026-09-01 14:30 nvm 導入ブロックだけを ubuntu:24.04 上で単独ビルドして検証したところ、
  **Node 26 系が `libatomic.so.1` を要求して起動しない**ことが分かった(22/24 系は要求しない)。
  現行イメージには g++ 経由で入っているが、依存が暗黙なので `libatomic1` を apt の一覧へ明示した。
  BR-02 の落とし先(導入直後に `node --version` で解決結果を検証する)がこの不具合を捕まえた。
- 2026-09-01 14:32 単独ビルドの再実行で v22.23.2 / v24.20.0 / v26.8.1 の3本と
  `default -> 24` を確認した。
- 2026-09-01 14:40 `docs/03-impl/environments/images.md` を 1.3.0 → 1.4.0 で更新
  (言語ランタイムのバージョン管理の節を新設、ビルド引数の表と落とし穴を更新)。
  合わせて `id: images` の重複(2026-08-10 の残務)を `id: container-images` で解消し、
  残務は雛形の根の1行へ書き直したうえで `doc-health.py --rotate` を回した。
- 2026-09-01 14:45 `go vet ./...` と `go test ./...`(docker-proxy)が green。
  `make build-claude` を実行中。実ビルドの中で nvm が v22.23.2 / v24.20.0 / v26.8.1 を
  導入したところまで確認済み。pyenv が CPython 3本をソースビルド中。
- 2026-09-01 14:45 履歴 `docs/histories/2026-09-01-pyenv-nvm-in-claude-image.md` を作成。
- 2026-09-01 15:25 再ビルドが `✅ claude-dev-claude`(終了コード 0)。実機のイメージで
  CPython 3本・Node 3系列・既定の解決先(fnm のまま)・`codex` / `chrome-devtools-mcp` の
  ランチャー無傷を確認した。`docs/03-impl/environments/images.md` に落とし穴を1行足した。
- 2026-09-01 15:05 1回目の `make build-claude` が失敗した(終了コード 2)。CPython 3本は
  すべて導入できていて、落ちたのは**今回足した検証の1行**である —
  `${PYENV_ROOT}/shims` を PATH に置いていなかったので `python` が解決できず、
  `test "$(python --version 2>&1)" = "Python 3.13.14"` が偽になった。
  PATH に shims を前置して直し、再ビルド中。

## 申し送り

- なし
