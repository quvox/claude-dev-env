---
slug: dev-image-version-update
state: awaiting-verify
critical: false
origin: derived
issue: なし
started: 2026-11-23T09:18:04+09:00
updated: 2026-11-23T09:34:20+09:00
commit: 6d81429fecfb3fa0cf4589c0b3dddc771e574868
summary: 開発イメージ(Dockerfile.claude)の Go・Python・Node・nvm・noVNC・terraform を公式配布情報で引いた最新の安定版へ上げ、CI の部品が最新メジャーであることを確かめた
---

# dev-image-version-update — 開発イメージと CI の部品の版更新

## 目的・やらないこと

- 目的: 人間の要望(2026-11-23「goやpythonおよび依存モジュールなど全てについて確認して、アップデートして」— `.claude/missions/2026-11-23-version-update/requests.md`)に従い、`.devcontainer/Dockerfile.claude` の版の固定値と `.github/workflows/ghcr-images.yml` の部品を、その場で引いた最新の安定版へ揃える。
- やらないこと: docker-proxy の Go と基底(後続の作業指示 T2)。基底 OS の載せ替え(下の進捗メモの判断)。ビルド時に最新へ解決する部品(rustup stable・pnpm@latest・playwright@latest・AWS CLI・terraform・gcloud・fnm の導入スクリプト・apt の Chrome / docker-ce-cli / gh・cargo の rmcp-xdotool・同梱エージェント CLI)の解決方法の変更。

## 影響範囲(closure)

- .devcontainer/Dockerfile.claude
- docs/03-impl/environments/images.md

## 作業コミットに入れた入力

- なし

## 主張

- 触ったモジュールのテスト: **このタスクが触ったイメージのビルド定義には自動テストが無い**(`docs/03-impl/tests/images.md` は全件が「未検証(テスト未実装)」で実機確認で代替すると定めている)。代わりに、ビルドしたイメージを起動して確かめた(claude-cli / claude-vnc の両方で同じ結果):
  `docker run --rm -u devuser --entrypoint /bin/bash t1-verify:claude-cli -c 'export PS1=x; source /etc/bash.bashrc; terraform version; pnpm --version; node --version; python --version; go version; pyenv versions; nvm ls; fnm list'`
  → `Terraform v1.17.2` / `12.21.0`(取得の表示なし = 焼き込み済み)/ `v26.13.1` / `Python 3.13.18` / `go version go1.27.4 linux/amd64` / pyenv `3.11.18`・`* 3.13.18`・`3.14.10`・`3.15.2` / nvm `v22.23.5`・`v24.22.3`・`v26.13.1`・`default -> 26` / fnm `v22.23.5`・`v24.22.3`・`v26.13.1 default`。
  ランチャーの退行なし(シェル初期化の無い root の `bash -c`): `codex --version; chrome-devtools-mcp --version; agy --version` → `codex-cli 0.171.0` / `1.13.0` / `1.5.14`(`FR-env-12-2` の経路は無傷)。
  noVNC: `websockify --web /usr/share/novnc 6080 localhost:5999` を立てて `curl` → `vnc.html 200` / `index 200` / `rfb.js 200`、`package.json` は `"version": "1.7.0"`。
- lint / build: green(`docker build --target claude-vnc …` と `docker build --target claude-cli …`(タグ t1-verify:*)→ `exit=0`。ログは作業場の build3.log)。Dockerfile の lint の道具(hadolint)は未導入で走らせていない
- 資格情報の混入検査(secret_scan): 未設定(このリポジトリには `tests/` の宣言ファイル自体が無い。埋めるのはテスト基盤を入れるタスク)
- 版がビルドと揃った環境で走ったか: 未宣言(`02-design/environments.md` に版の固定の見出しが無い = 移行 `2026-11-05-build-test-version-pin` が未適用)。上の確認はビルドしたイメージそのものの中で行ったので、見比べられた範囲(Go・Python・Node)では一致
- 外部挙動の変化: あり(後方互換。コンテナ内の `node` の既定が 24 系→26 系、同梱 CPython に 3.15 系が増え各系列が最新パッチへ、Go が 1.27 系へ)
- 認証・決済・不可逆・個人情報・監査への接触: なし
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 及第ライン)

## 基本要件の点検

- R1: BR-01 / BR-05 / BR-06 / BR-07 / BR-09 / BR-10 / BR-11 / BR-13 — このタスクはイメージに入れる処理系の版の値だけを変え、アカウント・不可逆な操作・秘密の生成・認可・秘密の突き合わせ・ブラウザからの状態変更・保存先・画面のどれも作らず変えない

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | R1 | — |
| BR-02 | 該当 | 導入する版は外部の配布元(go.dev / python.org / nodejs.org / GitHub のタグ)からビルド時に取る値である | `docs/03-impl/environments/images.md`「言語ランタイムのバージョン管理」— 導入直後の `python --version` / `node --version` 照合でビルドを落とす(既存の仕組み。このタスクは値だけを変える) |
| BR-03 | 非該当 | 利用者が値を決める識別子を作らない。変えたのはビルド引数の既定の版文字列だけである | — |
| BR-04 | 非該当 | プロセス境界でスキーマを持つ値をやり取りする経路を足さない。取得するのは配布元の書庫と実行ファイルである | — |
| BR-05 | 非該当 | R1 | — |
| BR-06 | 非該当 | R1 | — |
| BR-07 | 非該当 | R1 | — |
| BR-08 | 該当 | ビルド引数の値をシェルの引数へ展開する経路がある(既存) | `.devcontainer/Dockerfile.claude` の pyenv / nvm 導入部 — 既存の二重引用を変えていない。方針は `docs/03-impl/environments/images.md` の [DS-04] の行 |
| BR-09 | 非該当 | R1 | — |
| BR-10 | 非該当 | R1 | — |
| BR-11 | 非該当 | R1 | — |
| BR-12 | 非該当 | 成果物の起動の入口(引数・下位コマンド・起動時の出力)にも、版の値・出し方にも触れない。イメージの版ラベル `IMAGE_VERSION` は変えていない | — |
| BR-13 | 非該当 | R1 | — |

## 決定シート(回答済み)

- 問いなし(開示のみ)。着手前の論点(@triage)は全件、取り消しが後続の普通の変更(ビルド引数・FROM の書き換えと再ビルド)で足りるため人間に問う基準を満たさず、決めて下の進捗メモに開示した。

## 質問キュー(出口のシートの種)

- なし

## 調査メモ

- check-ssot.py docs の凍結: 違反 38 件(すべてクロージャの外。images.md は 0 件)。手を付けない。
- relations-query.py --impact .devcontainer/Dockerfile.claude / .github/workflows/ghcr-images.yml: 機能 0 / 要件 0 / テスト 0(イメージは relations の外。ビルドそのものが検証)。
- `.devcontainer/Dockerfile.claude:11` FROM ubuntu:24.04 / `:158` GO_VERSION=1.26.1 / `:173` PYTHON_VERSIONS="3.11.11 3.13.14 3.14.7" / `:140` NVM_VERSION=v0.40.6 / `:142` NODE_DEFAULT_LINE=24 / `:394` noVNC v1.6.0(着手時)。
- CI の部品(着手時): actions/checkout@v7・docker/setup-buildx-action@v4・docker/login-action@v4・docker/build-push-action@v7・actions/upload-artifact@v7・actions/download-artifact@v8、実行機 ubuntu-latest / ubuntu-24.04-arm。

## 進捗メモ(再開点)

- 2026-11-23 09:18 版の確認(公式配布情報、2026-11-23 に取得):
  - Go 1.27.4 — https://go.dev/dl/?mode=json(stable の先頭。1.26 系の最新は 1.26.11)
  - Python 3.11.18 / 3.13.18 / 3.14.10 / 3.15.2 — https://www.python.org/api/v2/downloads/release/ (3.15.0 は 2026-10-09 公開)。系列の状態 https://peps.python.org/api/release-cycle.json: 3.15・3.14 bugfix、3.13 security(EOL 2029-10)、3.11 security(EOL 2027-10)。pyenv の定義は4本とも在る(pyenv master の python-build/share)
  - Node 26.13.1(LTS Lithium)/ 24.22.3(LTS Krypton)/ 22.23.5(LTS Jod)— https://nodejs.org/dist/index.json。最新 LTS は 26 系
  - nvm v0.41.0 / noVNC v1.7.0 / actions: checkout v7.0.1・setup-buildx v4.4.1・login v4.8.0・build-push v7.4.0・upload-artifact v7.0.2・download-artifact v8.0.2 — GitHub releases/latest(gh api)
  - ubuntu:26.04 が Docker Hub に在り、docker-ce の apt(resolute)・Playwright(ubuntu26.04)も対応済み。GitHub の実行機は ubuntu-latest が依然 24.04
- [DS-04] Go を 1.27.4 にする — 理由: 人間の更新指示 + delegation.md §2.3(最新の安定版)/ 見直す条件: 1.27 系で依存がビルドできないと判ったとき。**T2(docker-proxy)はこの版に揃える**
- [DS-04] Python は既存の3系列(3.11 / 3.13 / 3.14)を各最新パッチへ上げ、最新の安定系列 3.15.2 を足す — 理由: 「全てアップデート」と §2.3 から、最新の系列が入っていない状態は更新になっていない。3.11 は過去の要望(DS-04 の旧行)が名指した系列で、まだサポート中(EOL 2027-10)なので外さない / 見直す条件: 3.11 が EOL を迎えたとき(外す)、CPython 4本のソースビルドがビルド時間で問題になったとき
- [DS-04] `pyenv global` は 3.13 系のまま最新パッチ 3.13.18 にする — 理由: 旧 DS-04 の見直す条件が「3.14 系を既定にする指示が出たとき」であり、既定の系列を変える指示は出ていない。既定の系列を動かすと利用者のスクリプトの依存(3.15 に wheel が無いパッケージ等)が黙って壊れうる / 見直す条件: 既定の系列を上げる指示が出たとき、3.13 が EOL に近づいたとき
- [DS-04] Node の既定(fnm default・nvm default)を 24 系→26 系(最新 LTS)にし、fnm にも 22 / 24 / 26 を入れる。`NODE_LINES` は 22 24 26 のまま — 理由: §2.3「LTS の系列を持つ製品はその最新の LTS」。26 系は 2026-10 に LTS 入りしている。fnm の既定を上げても 24 系を残せば `fnm use 24` で戻れる / 見直す条件: 同梱の codex / chrome-devtools-mcp が 26 系で動かないと判ったとき
- [DS-04] nvm v0.41.0・noVNC v1.7.0 へ上げる — 理由: §2.3 / 見直す条件: 上げた版で導入か画面表示が壊れたとき
- [DS-04] 基底 ubuntu:24.04 を据え置く — 理由: 24.04 は LTS の標準サポート中。26.04 は coreutils(uutils)と sudo(sudo-rs)が Rust 実装へ置き換わっており、版の更新ではなくコンテナ内のあらゆるコマンドの振る舞いが変わる種類の変更である(エントリポイントの sudo・iptables 周りを含む)。ビルドが通っても E2E なしでは安全を言えない / 見直す条件: 人間が基底 OS の更新を明示したとき、または 24.04 の標準サポート終了(2029-04)が近づいたとき
- [DS-04] CI の actions は全件が最新メジャー(@vN は最新の小版へ追従する)なので変えない。arm64 実行機 `ubuntu-24.04-arm` は amd64 側 `ubuntu-latest`(= 24.04)と揃えて据え置く — 理由: 実行機の OS はイメージの中身に影響せず、amd64 / arm64 の実行機を揃えるほうが差の原因を減らせる / 見直す条件: GitHub が ubuntu-latest を 26.04 へ切り替えたとき
- 2026-11-23 09:18 Dockerfile.claude の版を更新し、claude-vnc / claude-cli の検証用ビルド(タグ t1-verify:*)を開始
- 2026-11-23 09:24 1回目のビルドが pnpm の導入部で失敗(`/bin/sh: 1: corepack: not found` — Node 25 以降は corepack を同梱しない)。CPython 4本と nvm の3系列(v22.23.5 / v24.22.3 / v26.13.1)はここまでで導入・照合済み
- [DS-06] pnpm の導入の前に `npm install -g corepack@latest` を足す — 理由: fnm の既定を 26 系にしたことで消えた既存の道具を、既存の導入手順(corepack 経由)を保ったまま補う。新しい依存ではなく、Node 24 までは同梱されていたものである / 見直す条件: pnpm を corepack 以外の方法で入れると決めたとき
- 2026-11-23 09:25 修正して再ビルドを開始
- 2026-11-23 09:28 2回目のビルドは成功。起動確認で2点を見つけた: ① terraform が v1.9.8 で入っている(最新は 1.17.2 — https://releases.hashicorp.com/terraform/index.json と https://checkpoint-api.hashicorp.com/v1/check/terraform で確認)。`index.json` の versions が版の順に並んでいないのに `last` を取っていたのが原因で、**基準コミット c007dc2 の既存イメージ(claude-dev-claude:latest)も v1.9.8 だった = 元からの不具合**。② pnpm 12 は初回起動時に本体を取りにいく(`Downloading the pnpm 12.21.0 binary`)
- [DS-04] terraform の版の解決を、正式版(X.Y.Z)だけを数値で並べ替えて最大を取る形に直す — 理由: 更新指示の対象であり、今の解決方法では最新が入らない / 見直す条件: HashiCorp が index.json の形を変えたとき
- [DS-04] pnpm の導入の `RUN` の最後で `pnpm --version` を1回打ち、本体をイメージに焼き込む — 理由: 利用者の初回起動を配布元への到達に依存させない / 見直す条件: pnpm が初回取得をやめたとき
- 2026-11-23 09:29 修正して3回目のビルドを開始(実行前の作業ツリーの指紋をスクラッチに控えた)
- 2026-11-23 09:33 3回目のビルドが成功(claude-vnc / claude-cli)。起動確認(主張の節)はすべて期待どおり。実行前の作業ツリーの指紋と実行後の指紋は一致(docs/ の外は動いていない)
- 2026-11-23 09:34 作業コミット 08d074d。履歴・残務の解消(images.md の `source:` の行を「直した」)・索引の再生成
- 2026-11-23 09:35 構築記録ゲートの指摘(節の欠落・差し込み記号)を直した。`check-baseline-verdicts.py` はリポジトリ直下に CLAUDE.md が無いため根の検出に失敗し(`前提エラー: docs/build-records が無い`)、走らなかった

## 直さなかった指摘(独立レビュー・探索的QA)

- なし

## 申し送り

- T2(docker-proxy の Go と基底): **Go は 1.27.4**(https://go.dev/dl/?mode=json、2026-11-23 確認)に揃える。
- 人間へ: 基底 OS(ubuntu:24.04 → 26.04)と `pyenv global` の系列(3.13 → 3.14/3.15)は据え置いた。上げるなら指示があれば別タスクで行う。
- `check-baseline-verdicts.py` がこのリポジトリで走らない(根の判定が CLAUDE.md の在り処に依存)。キットの側の事情で、このタスクでは直していない。
