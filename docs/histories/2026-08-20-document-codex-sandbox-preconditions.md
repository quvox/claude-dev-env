---
id: 2026-08-20-document-codex-sandbox-preconditions
date: 2026-08-20
record: docs/build-records/document-codex-sandbox-preconditions.md
critical: true
origin_layer: 02
issue: docs/issues/102-bug-colabtmux-refuses-to-launch-codex-on-a-nonzero-bwrap-probe.md
summary: codex を起こす側が前提にしてよい環境を実機で測って 02 に明文化し、Codex 実行設定の事実誤り3件を実測値へ直した
---

# 2026-08-20 codex を起こす側の前提を実測して 02/03 へ降ろす

## 変更理由

### R-01 コンテナ内で codex が起動しないという報告の切り分けが、02 の記述の誤りを露わにした

- 起点層・根拠: `docs/issues/102`(`origin_layer: 02`。人間が実機で観測して報告)。
  対処案 A(まず切り分ける)→ 結果に応じて B か C、という起票時の指示に従った。
- 変更が必要になった条件: 実機で測ったところ、`docs/02-design/environments.md` の
  Codex 実行設定に**事実として誤っている記述が3件**あり、かつ「コンテナの外から codex を
  起こす側が、起動の前に何を確かめてよいか」をどの層も持っていなかった。

## 変更内容の要約

- 実機(コンテナ `claude-dev-claude:latest` / codex 0.148.0)で issue 102 の切り分けを行い、
  報告文の出どころがキットの規範 `.claude/directions/orchestration.md` §1.1.1 であることを
  確定した。同梱の colabtmux は起動可否の判定に関与していない(4ビルドを走査して文字列0件)。
- `docs/02-design/environments.md` の事実誤り3件を実測値へ直し、
  「codex を起こす側が前提にしてよいこと」の表を置いた。
- `MODULE-entrypoint-claude` の「既知の制限」に、旗の版(0.148.0 でも未撤去)と、
  既定3鍵がホストのプロジェクトディレクトリに在るためホスト側の codex にも効くことを書いた。
- コードは1行も変えていない。

## 更新したドキュメント

| 理由ID | ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/02-design/environments.md | 1.5.0 → 1.6.0 | 「必須フラグ」の行と理由を「既定3鍵で landlock が効く」へ、「サンドボックス疎通確認」の期待値を旗なしで exit 0 へ、「イメージ更新時の注意」を 0.148.0 の実測へ。あわせて「codex を起こす側が前提にしてよいこと」の表(5行)を追加 |
| R-01 | docs/03-impl/relations/MODULE-entrypoint-claude.md | 版は層代表が持つ | 「既知の制限」: 旗の版を 0.146.0 → 0.148.0(未撤去)へ直し、既定3鍵の置き場所がホストから見えることを1行追加 |
| R-01 | docs/03-impl/index.md | 1.32.0 → 1.33.0 | `relations/` を変えたため層の版を上げた |
| R-01 | docs/issues/102-bug-...-bwrap-probe.md | 仕様ドキュメントではない | 確定した原因で「原因の見当」を置き換え、`summary` と severity の根拠と対処案の結果を実測値へ直し、経緯に3行追記 |
| R-01 | docs/pendings.md | 仕様ドキュメントではない | 残務2行を追加(キット側の判定の修正 / codex 設定の置き場所の裁定) |

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| R-01 | なし | このタスクは製品コードを1行も変えていない(文書の事実訂正と明文化のみ) | — |

## 実施した移行

| 理由ID | 対象 | 手順(実行したコマンド / スクリプト) | 実行日 | 結果・確認方法 |
|---|---|---|---|---|
| R-01 | なし | なし | — | — |

### ロールバック・復旧記録

| 理由ID | 不可逆点 | 切り戻し可能な条件・期限 | 切り戻し手順 / forward-fixのみの理由と復旧手順 | 復元元 | 確認日 | 復旧確認コマンド・結果 |
|---|---|---|---|---|---|---|
| R-01 | なし(変更は Markdown 本文だけで、外部副作用・公開契約・実行される設定を一切動かさない) | 期限なし。いつでも戻せる | `git revert` で戻る。切り戻しても製品の振る舞いは変わらない | git | 2026-08-20 | `cd docker-proxy && go vet ./...` → 出力なし・終了コード 0 / `go test -count=1 ./...` → `ok github.com/quvox/claude-dev-env/docker-proxy 0.015s` |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | MODULE-entrypoint-claude | 「既知の制限」を2行更新・追加(frontmatter は変えていない) |

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| issue 102 の対処 | B(実測に合わせて 02/03 を直す) | C(既定3鍵が届く形へ直す) | 既定3鍵は現に届いている(コンテナ内で旗なしの `codex sandbox -- /bin/true` が exit 0)。直す対象が無い。崩れる条件: codex が `<プロジェクト>/.codex` を読まなくなったとき |
| codex 設定の置き場所 | 現状(プロジェクトディレクトリ配下)を維持し、ホストからも見えることを 02/03 に記録する | コンテナだけに閉じた位置へ移す | `AC-06`(設定と履歴がプロジェクトごとに独立していること)と `CTR-cli-container` が現在の位置を定めており、変えるには 00 の合意が要る。`docs/pendings.md` の残務1行が裁定を持つ |
| キットの判定の修正 | 入れずに残務1行にする | `.claude/directions/orchestration.md` §1.1.1 を直す | CLAUDE.md §3 により製品 DoD 未達の間キットは凍結で、直せるのは `/kit-improve` だけである |
| 3鍵目を外して非推奨の旗から離れる | 外さない | `[features] use_legacy_landlock` を落とす | 3鍵目だけを欠いた設定では `codex sandbox -- /bin/true` も `-c sandbox_mode=read-only` も exit 1 になる(実測)。`FR-env-12-4` と `FR-env-12-6` が落ちる |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 知見 | docs/feedbacks/032-a-precondition-probe-must-measure-the-path-actually-used.md | 起動前の可否判定は、使わないと決めた下位機構の状態ではなく、実際に通る経路を1コマンドで測る。報告文の出どころを名指しする前に原因を推測しない |
| 残務 | docs/pendings.md 残務 | キット `orchestration.md` §1.1.1 の bwrap 判定 / コンテナが置く3鍵がホスト側の codex にも効くこと |
| 解消した issue | なし | `docs/issues/102` は削除していない。`closes_when` の「colabtmux から codex を起動でき、報告が出ないこと」は直す先が凍結中のキットなので未達で、「`codex exec` が起こすコマンドが成功すること」は共有ボリュームに codex の認証が無く無人では確認できない。削除の判断は人間のものである |
| 残務の裁定 | docs/pendings.md 残務(2026-08-20 の `compose-changeset.py` 参照の行) | **持ち越す** — closure に入っているのは `docs/03-impl/index.md` の版行だけで、この残務が指す `:41`・`:48`・`:50` は日付で固定された検証記録である(書き換えると当時の事実でなくなる)。裁定が要るのは `docs/02-design/system.md:465` で、これは closure の外 |
| 残務の裁定 | docs/pendings.md 残務(2026-08-20 の `features.md` の「確認済みの境界辺」の行) | **持ち越す** — `MODULE-entrypoint-claude` の callees 3件が CG3 に出る件だが、節を足す先は `docs/03-impl/features.md` であり closure の外。関係仕様書側は文言を持つだけで、この残務は解けない |
| 残務の裁定 | docs/pendings.md 残務(2026-08-11 の `path:line` のずれの行) | **持ち越す** — このタスクはコードを1行も変えていないのでずれは増えていない。取り直しは引用を実コードに当てる作業で、closure がコードを含まないこのタスクでは根拠が取れない |
