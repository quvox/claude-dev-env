---
target: docs/03-impl/relations/MODULE-cli-ssh-keys-reset.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-cli-ssh-keys-reset
module: MOD-cli-ssh-keys
kind: tool
sync: sync
impl: claude-dev::main#ssh-keys.reset, claude-dev-mac::main#ssh-keys.reset
callers: なし
callees: MODULE-cli-common-container-name, MODULE-cli-common-dev-agent-path
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-04
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: このプロジェクトの SSH 鍵選択を初期化する
---

# MODULE-cli-ssh-keys-reset SSH 鍵選択の初期化

## 目的

プロジェクトの鍵選択をやり直せるようにする(FR-env-04)。設定ファイルの記述だけでなく、
すでに鍵を抱えている専用 ssh-agent も落として登録済み鍵をクリアする。

## 処理の流れ

1. `.claude-dev.yaml` があれば、`grep -vE
   '^ssh_keys:|^[[:space:]]*-[[:space:]]|^# claude-dev プロジェクト設定|^# 再選択は'`
   で該当行を除去した内容を一時ファイルに書く。
2. 残りに非空白文字があれば元ファイルへ `mv` し、無ければファイルごと削除する。
3. 専用 ssh-agent を停止する: `<DEV_AGENT_DIR>/<NAME>.pid` があればその PID を `kill` し、
   `<NAME>.sock` を `rm -rf`、`<NAME>.pid` を `rm -f` する。
   **macOS 版は `MODULE-cli-common-dev-agent-path` でこれらのパスを解決し、旧・単一 agent
   (`LEGACY_*`)の残骸も併せて掃除する。Linux 版はパスを直接組み立てる**
   (`MODULE-cli-common-container-name` は macOS 版がこの分岐内で呼ぶ)。
4. 「✅ このプロジェクト(<NAME>)の SSH 鍵選択をリセットしました」と再設定方法を表示する。

## 呼び出され方

- 契機: 利用者が `claude-dev ssh-keys reset` を実行したとき。
- 前提条件: なし。
- 引数: なし(対象は常にカレントプロジェクト)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | 対象は `$(pwd)/.claude-dev.yaml` と `~/.claude-dev/agents/<NAME>.*` |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-container-name

- 何のために呼ぶか: 専用 agent のファイル名(= プロジェクト名)を決めるため(macOS 版はこの分岐内で呼ぶ)。
- 何を渡すか: なし。 / 何を受け取るか: コンテナ名。
- **失敗したときどうなるか**: 想定されない。

### MODULE-cli-common-dev-agent-path

- 何のために呼ぶか: macOS で `.sock` / `.pid` / `.bridge.pid` / `.bridge.port` の位置を解決するため。
- 何を渡すか: コンテナ名と種別。 / 何を受け取るか: ファイルパス。
- **失敗したときどうなるか**: 空パスとなり、その残骸が消されずに残る。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0 |
| 永続化 | `.claude-dev.yaml` の `ssh_keys` 関連行を削除(残りが空白のみならファイルごと削除)。`~/.claude-dev/agents/<NAME>.sock` / `.pid`(macOS はブリッジ関連も)を削除 |
| 発火するイベント | なし |
| ログ | 標準出力へ完了メッセージ |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `.claude-dev.yaml` が無い | 何もせず agent の掃除へ進む | なし |
| kill / rm が権限などで失敗する | すべて `\|\| true` で握りつぶし、**残骸の有無を再確認せずに完了メッセージを出す** | 成功表示にもかかわらず残骸が残ることがある。次回 `start` の agent 準備で検出・案内される |
| `.claude-dev.yaml` に他のリスト形式のキーがある | **セクション境界を解釈しないため、`- ` で始まる行がすべて消える** | 他キーのリストが失われる |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 掃除を best-effort にする(`set -e` 下で `rm` の失敗が `reset` 全体を落とすのを避ける) | D0-scope-02 |
| 2 | 旧・単一 agent の残骸も掃除する(後方互換。macOS 版のみ) | D0-scope-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 行除去がセクション境界を見ない | `.claude-dev.yaml` に他のリスト形式キーを足すと壊れる。現状は `ssh_keys` しか持たないため実害は無い | `docs/issues/002-modify-claude-dev-yaml-is-overwritten-wholesale.md` |
| 掃除の失敗を検知しない | 残骸が残っても成功として表示する | なし |
