---
target: docs/03-impl/relations/MODULE-cli-ssh-keys-reset.md
change: replace
version_bump: minor
reason: '**`docs/issues/002` の後半(`ssh-keys reset` の行削除がセクション境界を見ず、ファイル中のすべてのリスト項目行を消す)を閉じる**。`RQ-env-07` により `.claude-dev.yaml` が `env_file` キーを持つようになるため、この欠陥は実害を持つ(鍵選択を初期化するとプロジェクト環境ファイルの指定が消える)。行の除去を **`ssh_keys` 節だけを取り除く形**へ直し、節の判定は書く側(`MODULE-cli-common-write-project-ssh-keys`)と同じ規則を使う。ファイルごと削除するかどうかの判定も「非空白文字が残っているか」から「字下げの無いキー行が残っているか」へ改める(案内のコメントだけのファイルを置き去りにしないため)。**呼び出し元・呼び出す先・要件は1つも増減していない**'
id: MODULE-cli-ssh-keys-reset
module: MOD-cli-ssh-keys
kind: tool
sync: sync
impl: claude-dev::main#ssh-keys.reset, claude-dev-mac::main#ssh-keys.reset
callers: なし
callees: MODULE-cli-common-container-name, MODULE-cli-common-dev-agent-path
contracts: CTR-cli-container
design: DSN-mod-01, DSN-mod-02, DSN-env-05
requirements: FR-env-04
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-19
summary: このプロジェクトの SSH 鍵選択を初期化する(他のキーは保存する)
reflected: 2026-08-19
---

# MODULE-cli-ssh-keys-reset SSH 鍵選択の初期化

## 目的

プロジェクトの鍵選択をやり直せるようにする(FR-env-04)。設定ファイルの記述だけでなく、
すでに鍵を抱えている専用 ssh-agent も落として登録済み鍵をクリアする。

## 処理の流れ

1. `.claude-dev.yaml` があれば、**`ssh_keys` 節だけ**を取り除いた内容を一時ファイルに書く。
   節の範囲は `MODULE-cli-common-write-project-ssh-keys` と**同じ判定**を使う
   (`ssh_keys:` の行から、次に現れる字下げの無い行の直前まで)。
   **節の外にある行は、`env_file` も利用者が書いたコメントも1行も落とさない**
   (`docs/issues/002` が記録していた「`- ` で始まる行がすべて消える」欠陥の解消)。
2. 残りに**キーが1つも無ければ**ファイルごと削除し、`env_file` などが残っていれば元ファイルへ `mv` する。
   **判定は「非空白文字が残っているか」ではなく「字下げの無いキー行が残っているか」で行う** —
   案内のコメントだけが残ったファイルを置き去りにしないためである。
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
| 永続化 | `.claude-dev.yaml` の **`ssh_keys` 節だけ**を削除(**他のキーは保存する**。残りにキーが1つも無ければファイルごと削除)。`~/.claude-dev/agents/<NAME>.sock` / `.pid`(macOS はブリッジ関連も)を削除 |
| 発火するイベント | なし |
| ログ | 標準出力へ完了メッセージ |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `.claude-dev.yaml` が無い | 何もせず agent の掃除へ進む | なし |
| kill / rm が権限などで失敗する | すべて `\|\| true` で握りつぶし、**残骸の有無を再確認せずに完了メッセージを出す** | 成功表示にもかかわらず残骸が残ることがある。次回 `start` の agent 準備で検出・案内される |
| `.claude-dev.yaml` に他のキー(`env_file`)がある | **保存する**(`ssh_keys` 節だけを取り除く) | 鍵選択の初期化でプロジェクト環境ファイルの指定が失われない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 掃除を best-effort にする(`set -e` 下で `rm` の失敗が `reset` 全体を落とすのを避ける) | D0-scope-02 |
| 2 | 旧・単一 agent の残骸も掃除する(後方互換。macOS 版のみ) | D0-scope-03 |
| 3 | **節の判定を `MODULE-cli-common-write-project-ssh-keys` と同じ規則にし、書く側と消す側で別々に持たない**(片方だけ直すと、書けるが消せない/消せるが書けない状態になる) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **節の判定を字下げの有無で行うため、YAML の入れ子には対応しない** | `ssh_keys` の下に入れ子の写像を書くと節の終わりを誤る。契約が書式を1階層のリストに限っている | なし(閾値の外: 契約が書式を限っている) |
| 掃除の失敗を検知しない | 残骸が残っても成功として表示する | なし |
