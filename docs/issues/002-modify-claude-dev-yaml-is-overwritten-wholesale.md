---
id: 002-modify-claude-dev-yaml-is-overwritten-wholesale
type: modify
severity: 低
found: 2026-08-02
found_in: task-docs-restructure の relations 起草(claude-dev の SSH 鍵まわりのコード精読)
related: MODULE-cli-common-write-project-ssh-keys, MODULE-cli-ssh-keys-reset, FR-env-04
summary: .claude-dev.yaml が全面上書き・全リスト行削除される実装で、ssh_keys 以外のキーを持てない
---

# 002 `.claude-dev.yaml` が `ssh_keys` 以外のキーを保持できない

## 事象

プロジェクト直下の `.claude-dev.yaml` を触る実装が2か所あり、どちらも「このファイルは
`ssh_keys` しか持たない」という前提に依存している。

1. **書き出し(全面上書き)**: `write_project_ssh_keys`(`claude-dev:112`・`claude-dev-mac:140`)は
   `> "$file"` でファイルを丸ごと作り直す。既存の他キーは失われる。
2. **削除(セクション境界を見ない)**: `ssh-keys reset`(`claude-dev:1301`)は
   `grep -vE '^ssh_keys:|^[[:space:]]*-[[:space:]]|^# claude-dev プロジェクト設定|^# 再選択は'`
   で行を落とす。`ssh_keys:` 配下かどうかを判定していないため、**ファイル中のすべてのリスト項目
   (`- ` で始まる行)が消える**。

再現手順:

1. 任意のプロジェクトで `claude-dev ssh-keys` を実行し `.claude-dev.yaml` を作る。
2. そのファイルに `ssh_keys` 以外のリスト形式のキー(例: `extra_mounts:` とその配下の `- ...`)を
   手で足す。
3. `claude-dev ssh-keys reset` を実行する。→ `extra_mounts` の項目行が消える。
   `claude-dev ssh-keys` を実行した場合は、ファイル全体が `ssh_keys` だけの内容に置き換わる。

## 影響

現在の `.claude-dev.yaml` は `ssh_keys` しか持たないため、**利用者に見える実害は無い**。
severity は「低」。ただしこのファイルに設定項目を足す変更をするときは、先にこの2か所を直さないと
静かにデータが失われる。既知の地雷として記録しておく。

## 原因の見当

**推測**: `.claude-dev.yaml` を「CLI が所有する単一目的のファイル」として設計したため、
YAML パーサを持たず簡易な行操作で済ませている(`_parse_ssh_keys_yaml` も同様の簡易パーサ)。
bash から YAML を正しく扱う手段を持ち込みたくなかった判断と思われる。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| `.claude-dev.yaml` の所有者と拡張性 | CLI が所有し `ssh_keys` のみ。全面上書き・全リスト行削除 | FR-env-04 は「プロジェクト単位で転送する鍵を明示選択する」ことだけを求めており、ファイルの拡張性には触れていない | 実装が正(要件を満たしている)。将来キーを増やすときに問題になる |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | 今は直さず、既知の制限として relations に記録するだけにする(現状の選択) | なし |
| B | `ssh_keys` 以外のキーを足す変更が発生した時点で、`ssh-keys reset` の行削除をセクション境界を見る実装へ直し、書き出しもマージ方式に変える | `MODULE-cli-common-write-project-ssh-keys` / `MODULE-cli-ssh-keys-reset` / `_parse_ssh_keys_yaml` |

## 経緯

- 2026-08-02 task-docs-restructure の relations 起草時に起票(委任 d: 見つけた乖離・制限は issue へ、本タスクでは直さない)。
