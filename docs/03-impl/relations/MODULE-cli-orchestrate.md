---
id: MODULE-cli-orchestrate
module: MOD-cli-orchestrate
kind: tool
sync: sync
impl: claude-dev::main#orchestrate, claude-dev-mac::main#orchestrate
callers: なし
callees: MODULE-cli-common-container-name, MODULE-cli-common-is-running, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user, MODULE-cli-start
contracts: CTR-cli-orchestrator
design: DSN-mod-01, DSN-mod-02, DSN-orch-02
requirements: FR-orch-01, FR-orch-02
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: コンテナ内で orchestrator を起動する(ゴール指定・--fresh 対応)
---

# MODULE-cli-orchestrate オーケストレータの起動と再接続

## 目的

コンテナ内の `claude-orchestrator` を起動し、既に走っている run があればそこへ戻す
(FR-orch-01・FR-orch-02)。契約 `CTR-cli-orchestrator` のホスト側の実装であり、
tmux 常駐方式(DSN-orch-02)の入口である。

## 処理の流れ(Linux 版)

1. `MODULE-cli-common-require-setup` → `MODULE-cli-common-container-name`。
2. `MODULE-cli-common-is-running` が偽なら、`CLAUDE_DEV_NO_ATTACH=1 "$SCRIPT_PATH" start` を呼んで
   `start` の全ロジックを再利用して起動する(attach は抑止する)。
3. 引数を走査し、`--fresh` を取り除いた残りを `<ゴール>` として連結する。
4. `MODULE-cli-common-resolve-container-user` で exec ユーザを解決する。
5. メインセッション名を `claude-orchestrator --print-main-session` から取得する
   (取得できなければ `orch-main`)。
6. **コントローラの生存判定**を `pgrep -f "claude-orchestrator --workspace"` で行い、cmdline が
   `claude-orchestrator` で始まるものだけを生存とみなす(空き殻セッションの誤検出を避ける)。
   生存していれば `tmux attach -t <sess>` して終わる。
7. 不在なら空き殻セッションを `kill-session` し、
   `tmux new-session -d -s <sess> -n dashboard -c /workspace "<cmd>"` で新規起動してから
   `tmux set-option mouse on` → attach する。
   `<cmd>` は `[ -f /etc/claude-dev/vm.env ] && . /etc/claude-dev/vm.env;
   claude-orchestrator --workspace /workspace [--fresh] ["<goal>"]`。

## 処理の流れ(macOS 版の差分)

- 未起動でも自動起動しない。`is_running` が偽なら「`claude-dev start` を先に実行」と表示して `exit 1`。
- コントローラの生存判定を行わない(`pgrep` 相当の分岐が無い)。毎回新規に起動する。
- 専用セッションを作らず、既存の `main` セッションへ
  `tmux new-window -t main -c /workspace "<cmd>"` でウィンドウを足して `tmux attach -t main` する。
- `/etc/claude-dev/vm.env` の読み込みを挟まない(VM モード非対応)。

## 呼び出され方

- 契機: 利用者が `claude-dev orchestrate ["<ゴール>"] [--fresh]` を実行したとき。
- 前提条件: Linux 版は無し(未起動なら自動で `start` する)。macOS 版はコンテナが稼働中であること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `<ゴール>` | 文字列 | 任意 | `--fresh` を除いた残りの引数を空白で連結したもの |
| `--fresh` | フラグ | 任意 | 既存の run 状態を捨てて開始する |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-require-setup

- 何のために呼ぶか: イメージ前提を満たすため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: `set -e` で非0終了する。

### MODULE-cli-common-container-name

- 何のために呼ぶか: 対象コンテナ名の決定。 / 何を渡すか: なし。 / 何を受け取るか: コンテナ名。
- **失敗したときどうなるか**: 想定されない。

### MODULE-cli-common-is-running

- 何のために呼ぶか: 起動済みかを判定して自動起動(Linux)か拒否(macOS)かを分けるため。
- 何を渡すか: コンテナ名。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: Linux 版は `start` を呼び直す。macOS 版は `exit 1`。

### MODULE-cli-common-resolve-container-user

- 何のために呼ぶか: `docker exec -u` のユーザ決定。 / 何を渡すか: コンテナ名。 / 何を受け取るか: ユーザ名。
- **失敗したときどうなるか**: `CUSER` へフォールバックする。

### MODULE-cli-start

- 何のために呼ぶか: **Linux 版のみ**。コンテナが未起動のとき、起動ロジックを二重に持たずに済ませる
  ため、自分自身を `start` サブコマンドで再帰実行する(`claude-dev:1017`)。
- 何を渡すか: 環境変数 `CLAUDE_DEV_NO_ATTACH=1`(起動後の attach を抑止する)。引数は `start` のみ。
- 何を受け取るか: 終了ステータス。コンテナが起動した状態。
- **失敗したときどうなるか**: 「❌ コンテナ起動に失敗しました」を表示して `exit 1`。
- **注記**: これは関数呼び出しではなく `"$SCRIPT_PATH" start` による**自プロセスの再帰起動**である。
  shell 抽出器はこの辺を検出できないため `callgraph-check.py` は CG3「低(実装前)」として出すが、
  実在する連携である(根拠: 上記の行番号)。本リポジトリで自己再帰呼び出しはこの1箇所だけ。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `tmux attach` の終了ステータス。macOS 版で未起動のときは 1 |
| 永続化 | コンテナ内 tmux セッション `orch-<project>-main`(Linux)。run の状態は orchestrator が `/workspace/.orchestrator/` に持つ |
| 発火するイベント | なし |
| ログ | 標準出力へ起動/再接続の案内 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| コンテナ未起動(Linux) | `CLAUDE_DEV_NO_ATTACH=1 start` で自動起動してから続行する | 起動に時間がかかる |
| コンテナ未起動(macOS) | 「`claude-dev start` を先に実行」と表示して `exit 1` | 利用者が手動で `start` する |
| セッションはあるがコントローラが死んでいる(Linux) | 空き殻とみなして `kill-session` し、新規起動する | run は `--fresh` を付けなければ状態から再開される |
| 実行中の run に再接続したい(macOS) | 生存判定が無いため新しいウィンドウで `claude-orchestrator` がもう1つ起動しうる | `claude-dev attach` で `main` へ入り直す運用でしのぐ |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 生存判定に `tmux has-session` ではなく `pgrep` を使う(空き殻セッションを生存と誤検出しないため) | D0-orch-01 |
| 2 | 未起動時に `start` を再帰呼び出しして起動ロジックを再利用する(起動処理を二重に持たない) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **macOS 版は生存判定・attach/resume を実装していない** | 契約 `CTR-cli-orchestrator` が定める「生存判定による attach/resume」が macOS では成立せず、既存 run への再接続が保証されない。2026-07-31 の人間判断で「後日あらためて開発する」として据え置いている | `docs/issues/003-future-macos-orchestrator-scope.md` |
