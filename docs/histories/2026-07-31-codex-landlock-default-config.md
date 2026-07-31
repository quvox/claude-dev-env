---
slug: codex-landlock-default-config
layer: history
title: Codex サンドボックスは既定で無効化しつつ、読み取り専用用途だけ landlock で生かす（D-27 ⑥ 改訂）
date: 2026-07-31
trigger: 不具合起因の仕様変更（コンテナ内 claude から codex に読み取り専用で依頼する経路が全滅していることの発見）
origin_layer: request
affected:
  - doc: docs/00-requests/decisions.md
    version: 1.6.0 -> 1.7.0
    change: D-27 ⑥ を書き換え。既定 3 鍵（`sandbox_mode`/`approval_policy`/`features.use_legacy_landlock`）、
      既存 config.toml は不足鍵のみ追記、workspace-write を伴う QA は danger-full-access で走らせてよい旨を追加。
      理由欄に landlock 実測（読み取り成功・書き込み拒否・名前解決不可・review 動作）と deprecated 注意を追記
  - doc: docs/00-requests/glossary.md
    version: 1.2.0 -> 1.3.0
    change: 用語「Codex サンドボックス」を 2 バックエンド（bubblewrap / landlock）構成に改訂。
      紛らわしい概念の区別も landlock を残す方針に合わせて更新
  - doc: docs/00-requests/acceptance.md
    version: 1.2.0 -> 1.3.0
    change: AS-6 の操作に「読み取り専用で調査だけを依頼する」を追加し、期待する結果に読み取り成功＋書き込み拒否、
      不合格条件に「読み取り専用を指定すると読み取りまで失敗する」を追加
  - doc: docs/01-requirements/core.md
    version: 1.8.0 -> 1.9.0
    change: 要件12 の受け入れ基準 12-5 を既定 3 鍵に改訂、12-6 を「既存の鍵と値は不変・不足鍵のみ追記・冪等」に改訂、
      12-9（明示 `--sandbox read-only` での成功。workspace-write は対象外）を追加。他の要件は変更なし
  - doc: docs/02-design/system.md
    version: 1.8.0 -> 1.9.0
    change: 判断5 を「既定は無効化・読み取り専用のみ landlock で生かす」へ差し替え（却下案④添付方式固定・⑤起動時疎通確認を追加）。
      データモデルの config.toml 行、entrypoint モジュール行と要件カバレッジの対応要件に 12-9、テスト戦略 core/12 備考、
      E2Eシナリオ一覧 E2E-6 に landlock 疎通確認を追記。モジュール分割定義そのものは変更なし
  - doc: docs/03-impl/entrypoint.md
    version: 1.6.0 -> 1.8.0
    change: （フェーズ2）手順10 を既定 3 鍵の保証＋不足鍵追記に改訂、データアクセス表の config.toml 行を更新、
      テスト対応表に 12-9 の確認行を追加。（フェーズ3 の実装同期）手順10 の判定・追記を `tomllib` による
      「候補を作る→意味的に検証する→通ったときだけ `os.replace` で原子的に置き換える」方式として書き直し、
      追記位置の 2 戦略・見出し検出の許容範囲・属性復元の順序・パーサ非在時の挙動を明記。テスト対応表の
      12-5/12-6/12-9 の 3 行を「実施済み・観測内容」へ更新（15 ケースのハーネス＋実機）。既知の制限に
      POSIX ACL/拡張属性が引き継がれないこと、インラインテーブルの features には補完できないことを追加
  - doc: docs/03-impl/e2e.md
    version: 1.3.0 -> 1.5.0
    change: （フェーズ2）E2E-6 の検証内容に landlock 疎通確認 2 コマンドと read-only 明示依頼を追加。既知の制限に
      「`codex exec` の終了コードは内部コマンド全滅でも 0」「deprecated フラグの回帰検知はイメージ更新時に再実行」を追記。
      （フェーズ3 の実装同期）landlock 疎通確認の本体を「entrypoint が置いた既定 config.toml があるコンテナで
      **フラグを付けずに** `codex sandbox -- /bin/true` が exit 0」に改め、`--enable` 明示形はフラグ経路の回帰確認として
      位置づけ直した（実装により config 経由で効くようになったため）
  - doc: scripts/entrypoint-claude.sh（コード）
    change: （フェーズ3）`ensure_codex_config()` を新設。既定 3 鍵の生成と、既存ファイルへの不足鍵補完を
      `tomllib` で実装（判定→候補生成→意味的検証→`os.replace`）。commit acfdc62 / 6189876 / d33b9ce
  - doc: docs/_steering/tech.md
    change: 「Codex実行設定」の QA 方針行を「`danger-full-access` で走らせる（不変条件5 からの意図的な逸脱・コンテナ内限定）」に更新
---

# 変更記録:Codex サンドボックスは既定で無効化しつつ、読み取り専用用途だけ landlock で生かす（D-27 ⑥ 改訂）

## 変更理由・背景

D-27 ⑥（同日先行）で `config.toml` の既定に `sandbox_mode = "danger-full-access"` を置き、開発者の
対話利用は復旧していた。しかし `--sandbox read-only` のようにサンドボックスを**明示指定する呼び出し**
——コードレビューや文書監査を codex に依頼する経路——は config の既定を上書きするため bwrap 経路に
戻り、読み取りコマンドまで全滅していた。コンテナ内の claude から独立監査を起動した際に
「サンドボックス疎通確認の失敗」として実際に現れた。

調査で codex 0.146.0 に bubblewrap 以外の legacy landlock バックエンドがフィーチャフラグ
（`features.use_legacy_landlock`）で残っていることが判明した。landlock はユーザー名前空間を必要と
しないため、コンテナの seccomp/AppArmor を緩めずに（D-1・要件 core/12-7 を保ったまま）内側の隔離を
生かせる。2026-07-31 に稼働中の claude コンテナ（codex-cli 0.146.0）で実測した結果:

| 確認 | フラグ付き | フラグ無し（既定=bwrap） |
|---|---|---|
| `codex sandbox -- /bin/true` | exit 0 | exit 1 `bwrap: No permissions to create new namespace` |
| 読み取り / 書き込み / ネットワーク | 読み取り成功・`/tmp` と `/workspace` への書き込み拒否・名前解決不可 | 全滅 |
| `codex exec -s read-only` でファイルを読ませる | 正答 | 読み取りコマンド全失敗 |
| `codex exec review --uncommitted -c sandbox_mode="read-only"` | 仕込んだバグに P1 指摘 | 無指摘 |
| `codex exec -s workspace-write` | 書き込み失敗（apply_patch・シェルとも） | 失敗 |
| 上記いずれの失敗時も `codex exec` の終了コード | — | **0** |

`workspace-write` は landlock でも成立しないため、書き込みを伴う自動化・QA は
`danger-full-access` で走らせる方針を人間が決定した（理由「コンテナ自体が隔離空間だから、これ以上の
隔離は不要」＝ D-1 の一貫適用）。これは CLAUDE.md 不変条件5 からの意図的な逸脱であり、プロセス設定
なので steering に理由付きで記録した（経緯は
`docs/knowledge/container-is-the-only-isolation-boundary-for-agent-qa.md`）。

## 変更内容の要約

- **00-requests/decisions.md**: D-27 ⑥ を「既定では無効化し、読み取り専用要求のために landlock を
  有効化しておく」へ書き換え。既定 3 鍵、既存 `config.toml` は不足鍵のみ追記（既存の鍵と値は不変・
  冪等）、`workspace-write` を伴う QA は `danger-full-access` 可。理由欄に上表の実測、却下理由
  （添付方式固定・起動時疎通確認）、`use_legacy_landlock` が deprecated であることと撤去時の退避先を追記。
- **00-requests/glossary.md**: 用語「Codex サンドボックス」を 2 バックエンド構成に改訂。
- **00-requests/acceptance.md**: AS-6 に読み取り専用での依頼を追加（期待結果・不合格条件とも）。
- **01-requirements/core.md**: 要件12 の 12-5（既定 3 鍵）・12-6（不足鍵のみ追記・冪等）を改訂し、
  12-9（明示 `--sandbox read-only` での成功、`workspace-write` は対象外）を追加。
- **02-design/system.md**: 判断5 を差し替え（却下案を①〜⑤に整理）。データモデル・entrypoint 行・
  要件カバレッジ・テスト戦略備考・E2E-6 を更新。
- **03-impl/entrypoint.md**: 手順10 の生成/補完仕様、データアクセス表、テスト対応表（12-9 の行追加、
  12-5/12-6 の未検証部分の明記）。
- **03-impl/e2e.md**: E2E-6 の検証内容に landlock 疎通確認と read-only 明示依頼、既知の制限に
  終了コード 0 問題と版更新時の再確認を追記。
- **_steering/tech.md**: 「Codex実行設定」の QA 方針行を更新（逸脱の明示と適用範囲の限定）。

## コード反映

未実施。`scripts/entrypoint-claude.sh` の既定生成ブロック（`config.toml` 分岐）を 3 鍵＋不足鍵補完へ
拡張する作業がフェーズ3として残る（作業ドキュメント `docs/tasks/codex-landlock-sandbox.md`）。
反映後、本エントリの affected に 03-impl の version 遷移を追記する。
