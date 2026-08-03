---
target: docs/03-impl/relations/MODULE-cli-common-ensure-infrastructure.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-cli-common-ensure-infrastructure
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev::ensure_infrastructure, claude-dev-mac::ensure_infrastructure
callers: MODULE-cli-login, MODULE-cli-login-codex, MODULE-cli-start
callees: なし
contracts: CTR-cli-container
design: DSN-mod-01, DSN-mod-02, DSN-auth-01
requirements: FR-env-01, FR-env-03
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: docker network と共有 3 ボリュームを冪等に作成する
---

# MODULE-cli-common-ensure-infrastructure 共有インフラの冪等作成

## 目的

コンテナ起動と認証共有の前提になる docker リソース(専用ネットワークと共有ボリューム)を、
何度呼んでも同じ結果になる形で用意する(FR-env-01・FR-env-03)。契約
`CTR-cli-container` が定めるマウント元の実体はここで作られる。

## 処理の流れ

1. `docker network create claude-dev-net 2>/dev/null || true` — 既存ならエラーを握りつぶす。
2. `docker volume create claude-dev-auth` — 認証共有ボリューム(claude と codex の双方)。
3. `docker volume create claude-dev-history` — シェル履歴の共有ボリューム。
4. `docker volume create claude-dev-config` — 設定共有ボリューム。
5. 2〜4 はいずれも `>/dev/null 2>&1 || true` で冪等化する。
6. Chrome プロファイル用ボリューム(`claude-dev-chrome-<container>`)はここでは作らない
   (`docker run` の自動作成に任せる)。

## 呼び出され方

- 契機: `start` / `login` / `login-codex` が処理の前段で呼ぶ。
- 前提条件: `docker` が実行できること。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | 参照するのは定数 `NETWORK` / `VOL_AUTH` / `VOL_HISTORY` / `VOL_CONFIG` |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

連携先なし。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 常に 0(すべての docker 呼び出しを `|| true` で握りつぶす) |
| 永続化 | docker network `claude-dev-net`、docker volume `claude-dev-auth` / `claude-dev-history` / `claude-dev-config`。`claude-dev-auth` は claude 認証(直下)と codex 認証(`codex/`)を同居させる |
| 発火するイベント | なし |
| ログ | なし(docker の出力はすべて破棄する) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 既にネットワーク/ボリュームが存在する | エラー出力を破棄して 0 を返す(正常系) | なし |
| Docker デーモンに接続できない | すべて失敗するが `|| true` で 0 を返す | 呼び出し元は先へ進み、後続の `docker run` で失敗する |
| ネットワーク名が別用途で使われている | 作成が失敗し既存のものを使う | 意図しないネットワークへ接続する可能性がある |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | codex 認証を専用ボリュームにせず `claude-dev-auth` の `codex/` サブディレクトリへ相乗りさせる(ボリュームを増やさず `logout` / `reset` の分岐も増やさないため) | D0-auth-01 |
| 2 | Chrome プロファイルはコンテナごとに分離し、ここでは作らない(共有すると同時起動時に SingletonLock を奪い合いプロファイルが壊れる) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 失敗を握りつぶすため、作成できたかを呼び出し元が知る手段が無い | 異常時のエラーは後続の `docker run` まで遅延する | なし |
