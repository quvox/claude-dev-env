---
id: 102-bug-colabtmux-refuses-to-launch-codex-on-a-nonzero-bwrap-probe
type: bug
severity: 中
origin_layer: 02
found: 2026-08-19
found_in: 人間の指摘
related: FR-env-12, AC-06, D0-dist-04, DSN-dist-02, MODULE-entrypoint-claude, docs/02-design/environments.md
closes_when: claude-dev コンテナ内の colabtmux から codex を起動でき、「bwrap が非ゼロのため codex を起こせず」の報告が出ないこと。あわせて、同じコンテナで `codex sandbox --enable use_legacy_landlock -- /bin/true` が終了コード 0 を返し、`codex exec` が起こすシェルコマンドが成功することを実機で確認できること
pattern: なし
pattern_survey: ""
summary: 起動の可否を bwrap の終了コードで判定する規範がキット側に在り、コンテナ内では既知かつ正常な非ゼロを故障と読んで codex を起こさない(同梱の colabtmux は判定に関与していない)
---

# 102 colabtmux が bwrap の非ゼロを理由に codex を起こさない

## 事象

claude-dev コンテナの中で **colabtmux から codex を呼ぼうとすると
「bwrap が非ゼロのため codex を起こせず」という報告が出て、codex が起動しない**
(2026-08-19 の人間の指摘)。

再現手順:

1. `claude-dev start` でコンテナを起動する。
2. コンテナ内で `colabtmux` を起動する。
3. colabtmux から codex を呼ぶ操作を行う。→ 上のメッセージが出て codex が起動しない。

**起票時に未確認だった3点は、2026-08-20 に実機で確かめた**(結果は「原因」と「経緯」):
素の `codex` はコンテナ内で動く / `codex sandbox --enable use_legacy_landlock -- /bin/true` は
終了コード 0 / `/workspace/.codex/config.toml` に既定3鍵が入っている。

## 影響

**開発者がコンテナ内で codex を使う経路のうち、colabtmux を通るものが使えない。**
`AC-06`(Codex CLI をコンテナで使い、認証をホストと共有する)の不合格条件に
「`codex` が起こすコマンドが毎回失敗する」があり、colabtmux 経由はその手前で止まっている。

severity を「中」に留める根拠(2026-08-20 に実測で確定した): **素の `codex` はコンテナ内で
動く**ので、`AC-06` は実機に対して落ちていない(`.claude/directions/issues-pendings.md` §3.0 は
severity「高」を「`AC-nn` が実機に対して落ちること」と定義している)。
利用者はメッセージを見て失敗に気づけるので、静かな失敗ではない。
**引き上げの条件(素の `codex` も起動しないこと)は満たされないことが確定した。**

## 原因(2026-08-20 に確定した)

**この報告文はこのリポジトリのどこにも無く、`externals/amd64/colabtmux` と
`externals/arm64/colabtmux` の両バイナリにも `bwrap` の文字列すら含まれていない**
(2026-08-19 に実測。バイト列で走査した)。**2026-08-20 に、稼働中の
`~/.local/bin/colabtmux` まで含めて `bwrap` / `bubblewrap` / `landlock` / `sandbox` を走査し、
いずれも0件だった。走査したのは4ビルド**(sha256 `ba7cb13e…` / `9e4baee0…` / `81c8f4bd…` /
`1dcb7bc8…`。調査中に同梱物と稼働中のバイナリが2回差し替わったため、そのすべてを測った)。
したがって **colabtmux は codex の起動可否を判定していない** — 起票時の推測1・推測2 はどちらも
外れである。

**出どころはキットの規範 `.claude/directions/orchestration.md` である。** §1.1.1 は
「起こす前に1回だけ確かめる2行」として
`bwrap --unshare-user --unshare-net --ro-bind / / /bin/true; echo $?` を挙げ、
「0 なら codex を使える」と定める。§1.3 の表は非ゼロを「このホストでは砂箱そのものが成立しない。
workspace-write で起こせる環境ではない」として claude へフォールバックさせる。
**claude-dev コンテナ内でこの1行が exit 1 を返すのは正常であり**
(`D0-dist-04` 項6 / `DSN-dist-02` がその経路を使わないと決めている)、
その環境では codex がまったく起こされない。中央エージェントがこの規範に従った結果が
「bwrap が非ゼロのため codex を起こせず」である。

**推測2 も否定された**: 既定3鍵は現に届いている。コンテナ内で `~/.codex` は
`/workspace/.codex` への symlink であり、`codex sandbox -- /bin/true` は旗を付けずに exit 0 を
返す(2026-08-20 実測)。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| コンテナ内で bwrap が使えないこと | entrypoint が既定3鍵を置いて bubblewrap を迂回する | `D0-dist-04` 項6 / `DSN-dist-02` が「既定では自前サンドボックスを使わない」と決めている | **一致している。ここに食い違いは無い** |
| 既定3鍵がどの起動経路まで効くか | `~/.codex/config.toml`(= `/workspace/.codex/config.toml`)を読む経路に効く。**この位置はホストのプロジェクトディレクトリそのものなので、ホスト側の `codex` にも効く**(2026-08-20 実測) | `AC-06` が「設定と履歴はプロジェクトごとに独立している」と定め、`CTR-cli-container` が置き場所をプロジェクトディレクトリ配下と定めている | **穴は無い**(位置は 00 と 02 が定めたもの)。ホスト側にも効くことは `docs/02-design/environments.md` と `MODULE-entrypoint-claude` の「既知の制限」に記録し、位置を変えるかは `docs/pendings.md` の残務1行が持つ |
| 同梱外部バイナリ自身の振る舞い | — | `D0-dist-05` 項4 が射程を「コマンド名だけで起動できる状態」までと定める | **仕様が正**(colabtmux 自身の判定はこのリポジトリの仕様ではない) |

## 対処案

| 案 | 内容 | 結果 |
|---|---|---|
| A | まず切り分ける | **2026-08-20 に実施した。** 上の「原因」がその結果である |
| B | `environments.md` に「同梱物が前提にしてよい環境」を明記する | **2026-08-20 に実施した**(`document-codex-sandbox-preconditions`)。`docs/02-design/environments.md` に「codex を起こす側が前提にしてよいこと」を置き、事実誤り3件を実測値へ直した |
| C | 既定3鍵が届いていないなら届く形へ直す | **不要**(届いている。上の「原因」の最後の段落) |

**残る作業はキット側だけである** — `.claude/directions/orchestration.md` §1.1.1 の判定を
`codex sandbox -- /bin/true` に替え、コンテナ内では既定3鍵のまま(`--sandbox workspace-write` を
付けずに)起こす形にすること。**キットは CLAUDE.md §3 により製品 DoD 未達の間は凍結されており、
直せるのは `/kit-improve` だけである。**`docs/pendings.md` の残務に1行で残した。

## 経緯

- 2026-08-19 人間が claude-dev コンテナ内で観測して報告。
  **`task-stop-cleanup-and-project-env` のフェーズ2(変更指示の作成)の最中に届いたため、
  そのタスクへは混ぜていない**(CLAUDE.md §4「進行中のタスクを分割・併合しない」)。
  同日、報告文が本リポジトリと同梱バイナリのどちらにも存在しないことをバイト列走査で確認した。
- 2026-08-20 `/build`(構築記録 `docs/build-records/document-codex-sandbox-preconditions.md`)で
  実機の切り分けを行った。コンテナ `claude-dev-claude:latest`(codex 0.148.0)での実測:
  `bwrap ...` = exit 1 / `codex sandbox -- /bin/true` = **exit 0** /
  `codex sandbox --enable use_legacy_landlock -- /bin/true` = **exit 0** /
  `codex sandbox -- /bin/sh -c 'touch /tmp/x'` = exit 1(書き込み拒否) /
  `codex sandbox -c sandbox_mode=workspace-write -- /bin/true` = exit 101 の panic /
  `/workspace/.codex/config.toml` に既定3鍵あり。
  **「素の `codex` も同じ理由で起動しない」という severity 引き上げの条件は満たされない**ので
  severity は「中」に留める。`AC-06` はこの経路では落ちていない。
- 2026-08-20 `closes_when` の充足状況: 「`codex sandbox --enable use_legacy_landlock -- /bin/true`
  が終了コード 0」は**満たした**(実測)。「`codex exec` が起こすシェルコマンドが成功すること」は
  **未確認** — 共有ボリューム `claude-dev-auth` の `codex/` が空で、`claude-dev login-codex` の
  デバイス認証はブラウザ操作を要するため無人では実行できない。「colabtmux から codex を起動でき、
  報告が出ないこと」は**未達** — 直す先が凍結中のキットだからである。
  **したがってこの issue は削除していない。削除の判断は人間のものである**
  (`.claude/directions/issues-pendings.md` §8)。
