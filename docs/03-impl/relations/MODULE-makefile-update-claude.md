---
id: MODULE-makefile-update-claude
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::update-claude
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-dist-01
requirements: FR-env-09, FR-env-12
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-11-23
summary: コンテナイメージを作り直さずに Claude Code と agy だけを更新する(ビルドキャッシュを使う)
---

# MODULE-makefile-update-claude make update-claude

## 目的

エージェント CLI(FR-env-12)だけを入れ替える(FR-env-09)。**イメージ全体を作り直さず**、
Go / Rust / Playwright 等の重い層は**ビルドキャッシュを再利用する**ため、
再ビルドの対象は `DSN-dist-01` が配布ステージの終端に置いた CLI 導入層だけになる。

## 処理の流れ

1. `curl -fsSL https://downloads.claude.ai/claude-code-releases/latest` で最新バージョンを解決する。
   失敗したら「解決できないままビルドすると更新されない」と表示して `exit 1`(フォールバックしない)。
2. 解決結果が `MAJOR.MINOR.PATCH` 形式でなければ `exit 1`。
3. 解決した値を `--build-arg CLAUDE_VERSION=<version>` として渡し、`claude-dev-claude`
   (`--target claude-cli`)をビルドする。値そのものが終端レイヤーのキャッシュキーになるため、
   新版が無ければキャッシュヒットで即終わり、新版があれば必ず失効する。
   **agy も同じ1回で解決して渡す**(2026-11-23): `uname -m` から配布元の更新情報(`manifests/linux_amd64.json` か
   `linux_arm64.json`)を選び、`version` を取り出す。**数字と点以外が1文字でも在るか `MAJOR.MINOR.PATCH` でなければ `exit 1`**
   (形の検査を通った値だけを、二重引用した `--build-arg "AGY_VERSION=<version>"` として渡す — `BR-04` / `BR-08`)。
4. 同じ値で `claude-dev-claude-vnc`(`--target claude-vnc`)もビルドする。
5. 「実行中のコンテナは claude-dev stop → claude-dev start で反映」と案内する。

## 呼び出され方

- 契機: 利用者が `make update-claude` を実行したとき。
- 前提条件: リポジトリのルートで実行すること(`BASE_DIR` は Makefile の位置から解決する)。
- 引数: なし(変数で調整する場合は下表)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: リポジトリを操作できるホストユーザ。

## 連携先と連携内容

連携先なし。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(解決失敗・形式不正・ビルド失敗は非0) |
| 永続化 | イメージ `claude-dev-claude` / `claude-dev-claude-vnc` |
| 発火するイベント | なし |
| ログ | 解決したバージョンと docker build の出力 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| バージョン解決に失敗(ネットワーク不通等) | 理由を表示して `exit 1`。**`latest` へフォールバックしない**(フォールバックするとキャッシュヒットで「更新したつもりで何も変わらない」状態になるため) | イメージは更新されない |
| 解決結果が `MAJOR.MINOR.PATCH` でない | 値を表示して `exit 1` | 同上 |
| agy の版を解決できない / 形が合わない / 未対応のアーキテクチャ | 理由を表示して `exit 1`(**値そのものは表示しない** — 外部の応答をそのまま端末へ出さない) | 同上 |
| docker build が失敗 | `set -e` により非0で停止する | 前のイメージが残る |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |
| 2 | agy の版も解決して渡す(渡さないと Claude Code に新版が無い日に agy の導入層がキャッシュヒットして agy が更新されない)。**codex の版を渡さない既存の癖は今回直さない** — 要望の範囲外(`docs/residual.md`) | DS-01(見直す条件: codex の手元更新を求められたとき) |
| 3 | 外部から受け取った版の文字列は、**文字の種類(数字と点だけ)と形(3つ組)の両方**を確かめてからだけ `docker build` へ渡し、二重引用する(`case` の `[0-9]*` だけでは `1.2.3; …` のような値も通るため) | BR-04 / BR-08 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |
