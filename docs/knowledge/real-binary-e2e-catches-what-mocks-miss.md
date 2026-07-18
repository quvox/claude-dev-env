---
title: 実機バイナリ E2E でしか顕在化しない不具合類型
summary: mock/tempdir を使う単体テストが構造的に見逃すバグは、実バイナリを実環境（実 claude・制限 PATH・絶対/相対パス・stream-json）で回して初めて出る
---

## 状況

オーケストレーターの一連の実機検証で、`go test ./...` が全て緑なのに実運用では全く動かない、
という不具合が繰り返し発覚した。いずれも単体テストの前提（mock・`t.TempDir()` の絶対パス・
固定入出力）が本番環境と食い違うことが原因で、テストの構造上検出不可能だった。

観測された代表例:

- **`claude` が PATH に無い**: `claude-dev orchestrate` は tmux ウィンドウの非対話シェル
  （`zsh -c`）で起動する。`claude` の導入先 `~/.local/bin` は対話シェルの `.zshrc` でしか
  PATH に入らないため、起動環境に `claude` が無く全 `exec("claude")` が "executable file not found"。
  「壁打ちが飛ぶ／worker が何もしない」の実体はこれだった。
- **worker の権限拒否**: ヘッドレス `claude -p` は `--permission-mode` 未指定だと全 Write/Bash を
  拒否（`permission_denials`）。無言で空回りする。
- **相対 `--workspace` で worktree パスが二重ネスト**（exit 128）: Store のパスが相対だと
  `git` の `cmd.Dir` 配下に相対 worktree が解決され二重化。単体テストは `t.TempDir()`（絶対）
  を使うため未検出、本番の絶対 `/workspace` でも未発生、相対指定時のみ発生。
- **`ParseReviewResult` が stream-json を解釈できない**: worker 側と非対称で `resultFromStream`
  を通していなかった。
- **`--resume` が実際には渡らない**: mock が `RunOpts.Resume/SessionID` を無視するため、
  「クラッシュ→再開で作業を捨てない」という主目的の core が壊れていても単体テストは緑のまま。

## 判断

単体テストの緑を完了条件にせず、**配布イメージ同梱のバイナリを、本番と同じ制限環境
（実 `claude`、`~/.local/bin` 無しの制限 PATH、非対話シェル、実 tmux）で通しで回す**ことを
検証の必須段とした。発見した不具合はコードへ反映し、mock が `RunOpts` を記録する回帰テスト
（`TestResume_UsesResumeFlagAfterCrash` 等）を後付けした。

## 一般化した教訓（今後どう活かすか）

- **外部プロセスを起動する箇所は、mock 単体テストが構造的に嘘をつく領域**と心得る。PATH 解決・
  権限・パス正規化・子プロセスの実出力フォーマット（stream-json）・実行オプションの伝播は、
  mock では前提ごと検証をすり抜ける。
- 完了判定には「実バイナリ × 実依存 × 本番相当の制限環境」の E2E を 1 本以上必ず入れる。特に
  **絶対 vs 相対パス**と**対話 vs 非対話シェルの PATH** は定番の落とし穴。
- 実機で見つけた不具合は、再発防止として「mock が実オプションを記録する」形の単体テストへ
  落とし込む（mock が無視していた値こそがバグの温床だったため）。
