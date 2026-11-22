---
id: MODULE-cli-version
updated: 2026-11-23
module: MOD-cli-version
kind: tool
sync: sync
impl: claude-dev::main#--version, claude-dev-mac::main#--version
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01
tests: scripts/test-cli-version.sh
summary: claude-dev 自身の版をリリースの記録から読んで名乗る(--version / -v)
---

# MODULE-cli-version claude-dev の版の名乗り

## 目的

人が「どの版の claude-dev を使っているか」を尋ねられるようにする(FR-env-01-37〜39。`BR-12`)。

## 処理の流れ

1. `python3` が無ければ、版を読めないことと理由を stderr へ出して終了コード 1。
2. リポジトリの直下(`BASE_DIR`)で `python3 .claude/scripts/stamps.py release --current` を走らせる。
3. 終了コード 0 で標準出力が `major.minor.revision`(各桁は先頭に 0 を持たない)なら `claude-dev <版>` を出して 0。
4. 終了コード 1 で、標準エラーが「まだ1度もリリースしていない」なら `claude-dev 未リリース` を出して 0。
5. それ以外(台帳が壊れている・3つ組でない・python の例外)は、読めなかったことと理由を stderr へ出して 1。

## 呼び出され方

- 契機: 利用者が `claude-dev --version` または `claude-dev -v` を実行したとき。
- 前提条件: なし(Docker もセットアップも要らない)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 版または「未リリース」を出せたら 0。読めなければ 1 |
| 永続化 | なし(台帳を読むだけで書かない) |
| ログ | 標準出力へ1行 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 台帳が壊れている / 先頭の版が3つ組でない | 理由を stderr へ出して 1(`FR-env-01-39`。未リリースと同一視しない) | 版を名乗れない |
| `python3` が無い | 理由を stderr へ出して 1 | 版を名乗れない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | **版の値の持ち主はリリース台帳 `.claude/state/releases.json` の1箇所**で、`stamps.py release --current` が読む。CLI に版の文字列を書かない(手で2箇所に書かない) | BR-12 / DS-01 |
| 2 | 終了コード 1 を「未リリース」と読むのは**標準エラーが未リリースの文言のときだけ**(python の例外も 1 で終わるため、終了コードだけで読むと壊れた状態を未リリースと誤る) | DS-01 |
| 3 | Linux 版・macOS 版の両方に同じ形で入れる | D0-scope-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| リポジトリの外へ CLI だけを複写して使うと台帳を読めない | 「版を読めません」で 1 | なし(閾値の外: 導入は `make install` のシンボリックリンクで、CLI はリポジトリの中で動く) |
