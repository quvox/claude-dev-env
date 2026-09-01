---
id: 2026-09-01-pyenv-nvm-in-claude-image
date: 2026-09-01
record: docs/build-records/pyenv-nvm-in-claude-image.md
critical: false
origin_layer: 03
issue: なし
summary: claude イメージの base ステージへ CPython 3本(3.11.11/3.13.14/3.14.7)と nvm v0.40.6(Node 22/24/26 系列)を入れた
---

# 2026-09-01 claude イメージに Python 3系統と nvm(Node 3系列)を入れた

## 変更理由

### R-01 コンテナ内で Python と Node の版を切り替えて使えるようにする

- 起点層・根拠: 人間の要望(`.claude/missions/2026-09-01-pyenv-nvm-docker/requests.md` 001、
  2026-09-01)。「claudeコンテナのdocker imageに、pyenvを入れて、3.11.11、3.13.14、3.14.7 を
  入れておいて。また、nvmも入れておいて。v0.40.6で。そして、nodeのv22,v24,v26それぞれの
  stableの最新も入れておいて」
- 変更が必要になった条件: pyenv は CPython を1本(`PYTHON_VERSION=3.13` の系列の最新)しか
  入れておらず、Node の版管理は fnm 一本で 22 系・24 系だけだった。
- 起点層を 03-impl とした理由: `RQ-env-02`(開発ツール入りコンテナイメージ)が既に覆っており、
  目的・対象ユーザー・スコープ・受け入れシナリオのどれも動かない。イメージに積む開発ツールの
  中身を持っている層は `docs/03-impl/environments/images.md` だけであり(02 の
  「コンテナ・実行環境」は起動するサービスの表で、pyenv も fnm も名前が出てこない)、
  ステージ構成・契約・モジュール分割は変わらない。したがって 00 / 01 / 02 は変更なしである。

## 変更内容の要約

- pyenv が入れる CPython を1本から3本(3.11.11 / 3.13.14 / 3.14.7)にし、`pyenv global` の既定を
  3.13.14 に固定した。ビルド引数を `PYTHON_VERSION` から `PYTHON_VERSIONS` +
  `PYTHON_GLOBAL_VERSION` の2本に置き換えた。
- nvm v0.40.6 を `base` ステージへ入れ、Node の 22 / 24 / 26 系列それぞれの最新を導入した。
  シェル初期化では `--no-use` で読み込むだけにし、`node` の既定の解決先は fnm のまま変えていない。
- Node 26 系が要求する `libatomic1` を apt の一覧へ明示した。

## 更新した仕様ドキュメント

| 理由ID | 仕様ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/03-impl/environments/images.md | 1.3.0 → 1.4.0 | 「言語ランタイムのバージョン管理(pyenv / fnm / nvm)」の節を新設(併存の理由・検証の仕方・実装上の判断6件)。ビルド引数の表から `PYTHON_VERSION` を落とし、`PYTHON_VERSIONS` / `PYTHON_GLOBAL_VERSION` / `NVM_VERSION` / `NODE_LINES` / `NODE_DEFAULT_LINE` の5行を足した。落とし穴に4行を足した。frontmatter の `id` を `images` → `container-images` に改めた(下記) |

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| R-01 | .devcontainer/Dockerfile.claude(base ステージ) | fnm の直後に nvm 導入ブロックを新設(`NVM_VERSION` / `NODE_LINES` / `NODE_DEFAULT_LINE`)。pyenv 導入部を3本ビルド + `pyenv global` 固定へ。シェル初期化(`/etc/zsh/zshrc`・`/etc/bash.bashrc`)へ nvm の `--no-use` 読み込みを追加。apt の一覧へ `libatomic1` を追加 | (段5 のコミット) |

## 実施した移行

| 理由ID | 対象 | 手順(実行したコマンド / スクリプト) | 実行日 | 結果・確認方法 |
|---|---|---|---|---|
| — | — | なし | — | — |

### ロールバック・復旧記録

適用外(`critical: false`。認証・決済・不可逆・個人データ・監査可能性のいずれにも触れない)。

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| — | — | なし(`.devcontainer/Dockerfile.claude` を `impl` に持つ機能間連携仕様書は無い。イメージの実装仕様は `docs/03-impl/environments/images.md` が持つ) |

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| nvm と fnm のどちらが `node` の既定を持つか | fnm のまま(nvm は `--no-use` で併存) | nvm を既定にし、fnm を残すだけにする | `codex` と `chrome-devtools-mcp` の `/usr/local/bin` ランチャーが fnm の `aliases/default/bin` を PATH に前置して実体を exec しており、`FR-env-12-2`(対話シェル・非対話シェル・`docker exec` のいずれからも `codex` が解決できること)はこの経路で満たされている。既定を移すと非対話シェルからこの2つが解決できなくなる / 崩れる条件: fnm をやめると決めたとき |
| 同上 | fnm の 22 系・24 系はそのまま残す | nvm が 22/24/26 を持つので fnm 側の Node を削る | 要望は「nvm も入れて」であって置き換えではない。fnm の既定エイリアスが上のランチャーの依存先であり、削ると同じ条項が壊れる。重複するぶんイメージは太るが、上流に大きさの制約は無い |
| Node の「stable 最新」の固定方法 | 系列(`NODE_LINES`)で指定し、ビルド時にその系列の最新へ解決する | CI が具体版へ解決して build-arg で渡す(同梱エージェント CLI と同じ形) | その形は `D0-dist-03` / `D0-dist-04` / `D0-dist-06` が**同梱エージェント CLI について**定めたものであり、開発ツールチェインには及んでいない。同じイメージの `fnm install 24` と `pyenv latest -k` が既に系列解決であり、ここだけ別の流儀にすると保守者が2つ覚えることになる / 崩れる条件: 版が勝手に上がって困る事故が起きたとき(そのときは `NODE_LINES` に具体版を渡せば釘付けできる) |
| Python の版の指定 | 具体的な MAJOR.MINOR.PATCH で固定 | Node と同じく系列で指定する | 要望が patch まで名指ししている。CPython はソースビルドなので、系列の最新に任せると再ビルドのたびに結果が変わる |
| `pyenv global` の既定 | 3.13.14 | 3.14.7(いちばん新しいもの) | これまでの既定が 3.13 系であり、今回の指定にも 3.13.14 が含まれる。既定を動かさないほうが利用者にとって驚きが少ない / 崩れる条件: 3.14 系を既定にする指示が出たとき |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 知見 | 今回限り(理由: この要望が答えたのは「どの版を入れるか」という値そのものであり、次に同種の要望が来ても値は毎回違う。判断の仕方を固定する余地が無い) | 人間の指定した版はすべて実在を確かめてから実装した(Node 22/24/26 系の最新 v22.23.2 / v24.20.0 / v26.8.1、nvm v0.40.6、CPython 3本の書庫) |
| 解消した残務 | docs/residual.md(2026-08-10 の行を削除) | `docs/03-impl/tests/images.md` と `docs/03-impl/environments/images.md` の `id` 重複を、後者を `container-images` へ改めて解消した。**キットの雛形2本が同じ `id` を導く根は残っている**ので、その1行だけを残務へ書き直した(直すなら `/kit-improve`) |
| 気づき | 履歴のこの行のみ | `pyenv global` を設定しても `${PYENV_ROOT}/shims` が PATH に無いと `python` は解決できない(`bin` に在るのは `pyenv` 本体だけ)。今回足した検証の1行がこれで落ち、1回目の `make build-claude` が失敗した。PATH に shims を前置して直し、`docs/03-impl/environments/images.md` の落とし穴へ1行残した |
| 気づき | 履歴のこの行のみ | nvm の導入ブロックだけを ubuntu:24.04 上で単独ビルドしたところ、**Node 26 系だけが `libatomic.so.1` を要求して起動しない**ことが分かった。導入直後に `node --version` を確かめる手順(基本要件 BR-02 の落とし先)がこれを捕まえた。現行イメージには `g++` 経由で入っていたが、暗黙の依存を避けて `libatomic1` を明示した |
