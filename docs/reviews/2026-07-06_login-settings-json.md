# レビュー: login の settings.json 生成不具合の修正（クォート/ブレース展開）

- 日付: 2026-07-06
- 対象: `claude-dev` / `claude-dev-mac` の `login` サブコマンド、`docs/impl/10_cli.md`
- ブランチ: `fix/login-settings-json-quoting`

## 背景（症状と根本原因)

`make login`（`claude-dev login`）が作る一時コンテナ内の `~/.claude/settings.json` が
`permissions:{defaultMode:bypassPermissions}` という不正 JSON になり、コンテナ内 Claude Code が
設定ファイル破損を報告する（macOS 実機で確認。Linux 版も同一コード）。

根本原因は 3 段ネストのクォート破綻:

1. `docker run ... -c '...'` のコンテナ内スクリプトはホスト側シングルクォートで括られている
2. その内側 `su -c "..."` 内の `echo '{\"permissions\":...}'` の最初の `'` が外側の引用を閉じ、JSON がホストシェルに裸で露出
3. ホストシェルが `\"`→`"` を消費し、トップレベル `{A,B}` をブレース展開して `docker run` の `-c` 引数が 2 つのスクリプトに分裂（`docker inspect` の `Cmd` で確認）。実行された側のスクリプトの `echo "permissions":{...}` がクォート除去され不正テキストを書き込む

## 修正内容

- `settings.json` 生成を `su -c "..."` の内側から root 実行部（`su` の前）へ移動し、`\"` エスケープの
  二重引用符で生成 + `chown "$CUSER"` する（ネストが 1 段減り、シングルクォート不要になる）
- `claude-dev` / `claude-dev-mac` に同一修正
- `docs/impl/10_cli.md` の `login` 節を成果物に合わせて更新し、「-c スクリプト内でシングルクォート使用禁止」のクォート制約を明記。履歴は `docs/impl/histories/10_cli.md` に追記

## 動作確認

ホストシェル解釈 → コンテナ bash → su 内 bash の 3 段を再現する検証ハーネス
（`docker`/`su`/`chown`/`claude` をスタブ化し、login の docker run ブロックを抽出・実行）で確認:

| 対象 | ホスト解釈（-c 引数数） | 生成される settings.json |
|---|---|---|
| 修正前 claude-dev / claude-dev-mac | **3 個に分裂（NG）** | 不正 JSON |
| 修正後 claude-dev / claude-dev-mac | 2 個（`-c` + スクリプト 1 個） | `{"permissions":{"defaultMode":"bypassPermissions"},"model":"sonnet"}`（jq で valid・期待値一致） |

`bash -n` による構文チェックも両ファイルで通過。

## 観点ごとの所見

1. **要件・ユースケースに合致**: login コンテナに `bypassPermissions` + `model:sonnet` の settings.json を
   生成するという docs/impl/10_cli.md の仕様どおりの動作が回復した。仕様自体の変更はない（生成タイミングを
   su 前の root 部に移した点のみ仕様書へ反映）。
2. **無駄な処理**: なし。むしろネスト 1 段削減で単純化。既存ファイルがある場合は生成しない挙動は従来どおり。
3. **処理時間**: 影響なし（echo 1 回 + chown 1 回）。
4. **セキュリティ**: root が書いたファイルを即 `chown` するため所有権は従来と同一。内容は固定リテラルで
   外部入力を含まず、インジェクションの余地はない。`bypassPermissions` はコンテナ隔離下でのみ効かせる
   本環境の設計どおり（docs/03_security.md）。

## 対応（改善した点／見送った点）

- 改善: 上記修正一式。
- 見送り: 検証ハーネスのリポジトリへの常設（scripts/ or tests/）。login ブロックの行構造に依存する抽出方式で
  壊れやすく、今回の単発検証には十分だが常設するなら抽出をより頑健にする必要があるため見送った。
  同種の再発防止は 10_cli.md へのクォート制約の明記で担保する。
