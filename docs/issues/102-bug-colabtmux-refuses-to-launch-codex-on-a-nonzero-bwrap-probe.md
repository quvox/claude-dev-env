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
summary: 同梱外部バイナリ colabtmux が codex を起こす前に bwrap の可否を見ており、コンテナ内では既知かつ正常な非ゼロを故障と読んで起動を拒む
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

**未確認の点**(報告からは決まらない):

- 同じコンテナで **素の `codex` が起動するか**(起動するなら故障は colabtmux の判定側に閉じる)。
- `codex sandbox --enable use_legacy_landlock -- /bin/true` が終了コード 0 を返すか
  (`docs/02-design/environments.md`「サンドボックス疎通確認」が定める確認)。
- `/workspace/.codex/config.toml` に既定3鍵(`sandbox_mode` / `approval_policy` /
  `[features] use_legacy_landlock`)が入っているか。

## 影響

**開発者がコンテナ内で codex を使う経路のうち、colabtmux を通るものが使えない。**
`AC-06`(Codex CLI をコンテナで使い、認証をホストと共有する)の不合格条件に
「`codex` が起こすコマンドが毎回失敗する」があり、colabtmux 経由はその手前で止まっている。

severity を「中」にした根拠: **素の `codex` が動くかどうかを確認できていない**ため、
`AC-06` が実機に対して落ちていると断定できない(`.claude/directions/issues-pendings.md` §3.0 は
severity「高」を「`AC-nn` が実機に対して落ちること」と定義している)。
利用者はメッセージを見て失敗に気づけるので、静かな失敗ではない。
**素の `codex` も同じ理由で起動しないことが確認できたら「高」へ上げる。**

## 原因の見当

**この報告文はこのリポジトリのどこにも無く、`externals/amd64/colabtmux` と
`externals/arm64/colabtmux` の両バイナリにも `bwrap` の文字列すら含まれていない**
(2026-08-19 に実測。バイト列で走査した)。したがって
**メッセージの出どころは、ここに同梱されているものより新しい colabtmux 自身である**(事実)。

そのうえで、原因の候補は2つある。**どちらも推測である。**

1. **推測: colabtmux の事前確認が landlock を指定していない。**
   このコンテナでは codex の既定サンドボックス(bubblewrap)は起動できないと決まっており
   (`D0-dist-04` 項6 / `DSN-dist-02`)、**フラグ無しの `codex sandbox -- /bin/true` が
   終了コード 1 と `bwrap: No permissions to create new namespace` を返すのは既知かつ正常である**
   (`docs/02-design/environments.md`「サンドボックス疎通確認」)。
   colabtmux がこの既知の非ゼロを故障と読んで起動を止めているなら、
   **直す場所は colabtmux 側**(事前確認をやめるか、`--enable use_legacy_landlock` /
   `-c features.use_legacy_landlock=true` を付ける)であり、このリポジトリの範囲外である
   (`D0-dist-05` 項4 は同梱物の射程を「コマンド名だけで起動できる状態」までと定めている)。
2. **推測: colabtmux が起こす codex に既定3鍵が届いていない。**
   既定3鍵は entrypoint が `/workspace/.codex/config.toml` へ置き、コンテナ内ユーザーのホームから
   `~/.codex` の symlink で参照させている(`MODULE-entrypoint-claude` 手順3)。
   **colabtmux が codex を別のユーザー・別の `HOME`・別の `CODEX_HOME` で起こしていると、
   この config が読まれず、codex は既定の bubblewrap 経路に戻る。**
   この場合は**このリポジトリ側の穴**であり、「どの起動経路でも既定3鍵が効く」ことを
   02 の契約(`CTR-cli-container`)か entrypoint の仕様が保証していないことになる。

**2 が当たっている場合に限り、`origin_layer` は 02 である**(既定3鍵の届く範囲を
契約が定めていないため)。1 が当たっているなら、このリポジトリでは
「同梱物が前提にしてよい環境」を `environments.md` に明文化するだけになる。
**切り分けは上の「未確認の点」を実機で確かめれば決まる。**

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| コンテナ内で bwrap が使えないこと | entrypoint が既定3鍵を置いて bubblewrap を迂回する | `D0-dist-04` 項6 / `DSN-dist-02` が「既定では自前サンドボックスを使わない」と決めている | **一致している。ここに食い違いは無い** |
| 既定3鍵がどの起動経路まで効くか | `~/.codex/config.toml`(= `/workspace/.codex/config.toml`)を読む経路にだけ効く | **どの層も「どの起動経路でも効く」とは書いていない** | **要確認** — 穴があるかどうかは上の切り分けで決まる |
| 同梱外部バイナリ自身の振る舞い | — | `D0-dist-05` 項4 が射程を「コマンド名だけで起動できる状態」までと定める | **仕様が正**(colabtmux 自身の判定はこのリポジトリの仕様ではない) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | まず切り分ける(素の `codex` / `codex sandbox --enable use_legacy_landlock -- /bin/true` / `config.toml` の3鍵 / colabtmux が codex を起こすときの `HOME` と実行ユーザー)。結果で B か C を選ぶ | 実機確認のみ。ドキュメントもコードも変えない |
| B | 原因が 1(colabtmux 側の事前確認)なら、**colabtmux のリポジトリで直す**。このリポジトリでは `environments.md` に「同梱物が前提にしてよい環境」として、フラグ無しの bwrap 確認が非ゼロを返すのは正常であることを明記する | `docs/02-design/environments.md` 1箇所 + `03-impl/environments/images.md` |
| C | 原因が 2(既定3鍵が届いていない)なら、**どの起動経路でも既定3鍵が効く形へ直す**(たとえばコンテナ全体に効く位置へ置く、または `CODEX_HOME` を固定する)。`CTR-cli-container` に取り決めを足し、entrypoint と 03 を降ろす | 00(`D0-dist-04` 項6 の射程)/ 01(`FR-env-12`)/ 02(`CTR-cli-container`)/ `MODULE-entrypoint-claude` / コード |

推奨は **A → 結果に応じて B か C**。**切り分けの前にコードを直さない**
(`D0-scope-07` の「推測を仕様として書いてはならない」と同じ理由)。

## 経緯

- 2026-08-19 人間が claude-dev コンテナ内で観測して報告。
  **`task-stop-cleanup-and-project-env` のフェーズ2(変更指示の作成)の最中に届いたため、
  そのタスクへは混ぜていない**(CLAUDE.md §4「進行中のタスクを分割・併合しない」)。
  同日、報告文が本リポジトリと同梱バイナリのどちらにも存在しないことをバイト列走査で確認した。
