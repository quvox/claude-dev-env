---
id: 110-bug-bundled-arm64-binary-is-a-darwin-build
type: bug
severity: 高
origin_layer: 03
found: 2026-08-20
found_in: 実装中(別オーダーの作業中に実測されたものを、本タスクが `file` で再確認した)
related: AC-07, FR-env-13-1, FR-env-13-2, FR-env-13-3, RQ-dist-02
closes_when: 次のどれか1つが観測できたとき。(a) `file externals/arm64/colabtmux` が Linux/arm64 の ELF(`ELF 64-bit LSB ... ARM aarch64`)を返し、arm64 の配布イメージの中で `colabtmux --version` が終了コード 0 で応答する / (b) `externals/arm64/colabtmux` がリポジトリから削除されている(arm64 イメージには何も設置されない = `FR-env-13-5` の正常な状態)/ (c) 人間が「arm64 には同梱しない」と裁定し、`externals/README.md` と `docs/03-impl/environments/images.md` がその状態を述べている
pattern: bundled-binary-built-for-a-foreign-platform
pattern_survey: `find externals -type f`(2026-08-20)で3件を走査し1件ずつ `file` を実行 — 同型は1件(`externals/arm64/colabtmux` = Mach-O 64-bit arm64)。`externals/amd64/colabtmux` は ELF 64-bit LSB x86-64 で該当せず、`externals/README.md` は設置対象外(README は設置しない規約)
summary: externals/arm64/colabtmux が macOS(darwin/arm64)向けの Mach-O であり、arm64 配布イメージへ焼かれても実行できない
---

# 110 同梱物 `externals/arm64/colabtmux` が macOS 向けのビルドである

## 事象

`externals/arm64/colabtmux` は **Mach-O 64-bit arm64 executable**(macOS 向け)であり、
Linux コンテナでは実行形式として認識されない。

再現手順:

1. `file externals/arm64/colabtmux` を実行する。
   → `Mach-O 64-bit arm64 executable, flags:<|DYLDLINK|PIE>`
2. 同じ確認を HEAD の内容に対して行う(作業ツリーの差分ではないことの確認)。
   `git show HEAD:externals/arm64/colabtmux | file -`
   → `/dev/stdin: Mach-O 64-bit arm64 executable, flags:<|DYLDLINK|PIE>`(8,343,362 バイト)
3. 比較のため `file externals/amd64/colabtmux` を実行する。
   → `ELF 64-bit LSB executable, x86-64 ...`(こちらは Linux 向けで正しい)

## 影響

**arm64 の配布イメージ2種(`claude-dev-claude` / `claude-dev-claude-vnc`)の中で
`colabtmux` を打つと起動しない。**

`.devcontainer/Dockerfile.claude:522`-`:530`(および VNC 側の `:569`-`:577`)は、
`dpkg --print-architecture` が返す値のディレクトリの直下のファイルを**中身を見ずに**
`install -m 0755 -o root -g root` で `/usr/local/bin` へ設置する。したがって arm64 の
ビルドはこの Mach-O をそのまま `/usr/local/bin/colabtmux` として設置し、ビルドは成功する
(`FR-env-13-6` が求める「設置の失敗」は起きない — 設置そのものは成功するからである)。

`AC-07`(用意した外部実行ファイルがコンテナ内でそのまま使える)の**不合格の条件に逐語で
当たる**: 「**別のアーキテクチャ向けの実行ファイルが入っていて起動できない**」。
`FR-env-13-2`(設置したものはコンテナ内の利用者がコマンド名だけで実行できること)も
満たされない。

**severity 「高」の根拠**: `AC-nn` が落ちる(`.claude/directions/issues-pendings.md` §3.0 の
「高」の第1条件)。**ただし arm64 の実機はこの確認環境に無いため、コンテナ内での実行までは
観測していない。** 観測したのは (1) 同梱物が darwin 向けの Mach-O であること(上の手順)と
(2) Dockerfile が arm64 ビルドでそれを無条件に設置すること(上の行番号)の2点であり、
この2点から `AC-07` の不合格条件が成立する。実行での確認は arm64 ホストを要する
(`closes_when` の (a) がそれを求めている)。

**公開の観点**: `docs/03-impl/infra/local/ghcr.md` が定める日次ビルドは
`actions/checkout` したツリーを文脈にするため、この同梱物はコミットされている以上
公開 arm64 イメージへ入る。**一度公開したものは回収できない**
(`externals/README.md`「置く前に確認すること」項2)。

## 原因の見当

同梱の仕組みは「置いたものをそのまま入れる」設計であり(`externals/README.md`
「ビルドは外部から何も取得しません」)、**置く側が対象プラットフォーム向けにビルドしたか
どうかを検査する箇所がどこにも無い**。`FR-env-13-4` / `FR-env-13-5` が「何も無い」「片側だけ」
を正常として扱う一方で、「在るが別プラットフォーム向けである」状態は要件が触れていない。

macOS で `go build` した成果物を `externals/arm64/` に置いたものと**推測する**
(`externals/README.md` の使い方の例が `cp /path/to/mytool.arm64 externals/arm64/mytool` の形で
あり、アーキテクチャ名だけを手掛かりにしている。OS の区別を促す記述が無い)。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 同梱物が実行可能であること | `03-impl/environments/images.md`「同梱外部バイナリの設置(externals/)」は権限と設置先だけを規定し、実行形式の妥当性には触れない。実物は darwin 向けである | `FR-env-13-2` は「コンテナ内の利用者がコマンド名だけで実行でき」ることを求め、`AC-07` は「別のアーキテクチャ向けの実行ファイルが入っていて起動できない」を不合格とする | **要件・設計が正**(同梱物の側が誤っている) |
| 別プラットフォーム向けの同梱物を検出すべきか | 検査は1箇所も無い | 要件は「在るが実行できない」状態に言及していない | 要確認 |

## 対処案

**本タスクは起票のみで、修繕を行っていない**(同梱物の差し替え作業は不要と人間が述べている
ため、案 A は人間の裁定を待つ)。

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `externals/arm64/colabtmux` を Linux/arm64 向けにビルドし直して差し替える | 同ファイル1件。要件・設計・コードの変更なし |
| B | `externals/arm64/colabtmux` を削除する(arm64 イメージには何も同梱されない状態にする。`FR-env-13-5` が正常と定める状態) | 同ファイル1件 + `externals/README.md` の記述の確認 |
| C | 設置時に対象プラットフォーム向けかを検査し、違えばビルドを失敗させる(`FR-env-13-6` の射程を「設置の失敗」から「設置したものが実行できないこと」へ広げる) | `01-requirements/functional.md`(`FR-env-13` に条項追加)/ `03-impl/environments/images.md` / `.devcontainer/Dockerfile.claude` の2ステージ / `03-impl/tests/images.md` |

## 経緯

- 2026-08-20 起票(`fix-make-status-hides-docker-query-failure` の `/build` の中で、
  同じオーダーが指示した記録として作成した)。**修繕は行っていない。**
