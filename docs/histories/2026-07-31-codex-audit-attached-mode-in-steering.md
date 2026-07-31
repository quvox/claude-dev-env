---
slug: codex-audit-attached-mode-in-steering
layer: history
title: コンテナ内の Codex 監査を legacy landlock 経路で使える状態にし、tech.md に「Codex実行設定」を記入
date: 2026-07-31
trigger: 不具合起因（claude コンテナ内から /codex-audit を走らせた際にサンドボックス疎通確認が失敗）
origin_layer: steering
affected:
  - doc: docs/_steering/tech.md
    change: 「Codex実行設定」節を新設（節名はテンプレート固定）。監査・QA の codex 呼び出しに
      `-c features.use_legacy_landlock=true` を必須化、実行方式はスコープ渡しを既定（添付方式は予備）、
      疎通確認コマンドと 2026-07-31 の実測結果、QA(workspace-write) はサブエージェント代替、
      danger-full-access の監査利用禁止、イメージ更新時の再確認、フェーズ1、CDP 9222 を記載
# 併せて docs/knowledge/nested-agent-sandbox-blocked-by-container-confinement.md に追記したが、
# knowledge は仕様ドキュメントではないため affected の対象外（要約に記載）
---

# 変更記録:コンテナ内の Codex 監査を legacy landlock 経路で使える状態にし、tech.md に「Codex実行設定」を記入

## 変更理由・背景

claude コンテナ内の Claude Code から `/codex-audit` を起動したところ、プリフライトの
サンドボックス疎通確認（`codex sandbox -- /bin/true`）が失敗し、監査が走らなかった。

D-27 ⑥ で入れた `config.toml` の `sandbox_mode = "danger-full-access"` は開発者の対話利用を救うが、
`/codex-audit` は監査要件として `--sandbox read-only` を明示指定するため config の既定を上書きし、
bubblewrap が再び使われて失敗する。つまり「対話利用は直っていたが監査経路は直っていなかった」。
加えて `/codex-audit` が実行方式の記録先として定めている `docs/_steering/tech.md` の
「Codex実行設定」節が未記入で、毎セッションが疎通確認から再発見する状態だった。

調査の結果、**codex 0.146.0 には bubblewrap を使わない legacy landlock バックエンドが
フィーチャフラグとして残っている**ことが分かった（`features.use_legacy_landlock`）。landlock は
user namespace を必要としないため、コンテナの seccomp/AppArmor を緩めずに codex 自前の
サンドボックスを動かせる。2026-07-31、稼働中の claude コンテナ（codex-cli 0.146.0）で実測:

| 確認 | 結果 |
|---|---|
| `codex sandbox --enable use_legacy_landlock -- /bin/true` | exit 0（フラグ無しは exit 1 / bwrap エラー） |
| landlock 経路での読み取り / 書き込み / ネットワーク | 読み取り成功、`/tmp`・`/workspace` への書き込み拒否、名前解決不可＝読み取り専用が実効的に強制 |
| `codex exec -s read-only`（スコープ渡し）でファイルを読ませる | フラグ付きで正答。フラグ無しは全読み取りが bwrap で失敗 |
| `codex exec review --uncommitted -c sandbox_mode="read-only"`（diff モード） | フラグ付きで仕込んだバグに P1 指摘。フラグ無しの対照実行は無指摘 |
| `codex exec -s workspace-write`（QA 相当） | landlock 経路でも書き込み失敗（apply_patch・シェル書き込みとも） |
| いずれの失敗でも `codex exec` の終了コード | **0**（終了コードは合否根拠にならない） |

フラグは呼び出し時に渡すだけで足りるため、**イメージ・entrypoint・仕様ドキュメント（00〜03）の
変更は不要**で、プロセス設定（steering）だけで解決した。`config.toml` の既定に焼き込む案は採らなかった
（フラグが deprecated であり、撤去時に外しやすい呼び出し側指定のままにしておくため。
D-27 ⑥ と要件 core/12-5・12-6 は変更なし）。

## 変更内容の要約

- **docs/_steering/tech.md**: 「Codex実行設定」節を新設。必須フラグ
  `-c features.use_legacy_landlock=true`（付け忘れると全読み取りが失敗するのに終了コードは 0 という
  注意つき）、実行方式＝スコープ渡し既定／添付方式は予備、疎通確認の 2 コマンドと合格条件、
  上表の実測結果、QA レーンはサブエージェント代替（不変条件7）、seccomp/AppArmor を緩めない・
  監査での `danger-full-access` 禁止、`--skip-git-repo-check`、イメージ更新時に疎通確認を再実行
  （`CODEX_VERSION` は build 時 latest 解決、フラグは deprecated）、未定項目（プロファイル・
  モデル固定値・QA 関連）、CDP `:9222`、ロールアウトフェーズ 1。frontmatter の `updated` と
  `summary`/`keywords` も更新。
**追記（同日）:** 本エントリの後、人間の判断で「既定 `config.toml` へ landlock を焼き込む（全プロジェクトの
コンテナで素で動く状態にする）」方針を採ったため、仕様ドキュメント 00〜03 の変更を伴う別の変更を起こした
（→ `2026-07-31-codex-landlock-default-config.md`）。本エントリ時点の「仕様ドキュメントの変更は不要」という
判断はその決定で置き換わっている。steering の記入内容（必須フラグ・疎通確認・実測表）はそのまま有効。

- **docs/knowledge/nested-agent-sandbox-blocked-by-container-confinement.md**: 教訓3 に、失敗しても
  `codex exec` の終了コードが 0 だった実測を追記（応答も終了コードも根拠にしない）。教訓4 に系を追記
  ——「内側を諦める」の前に**そのCLIに user namespace を要らないサンドボックス実装（landlock 等）が
  無いか確認する**。あればコンテナを緩めずに内側の隔離を生かせる。実行方式は steering に記録する。
