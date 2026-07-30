---
slug: codex-sandbox-disabled-in-container
layer: history
title: Codex サンドボックスはコンテナ境界に委ねて無効化する（D-27 ⑥ 追加）
date: 2026-07-31
trigger: 不具合起因の仕様追加（コンテナ内で codex のシェル実行が全て失敗することの発見）
origin_layer: request
affected:
  - doc: docs/00-requests/decisions.md
    version: 1.5.1 -> 1.6.0
  - doc: docs/00-requests/glossary.md
    version: 1.1.0 -> 1.2.0
  - doc: docs/00-requests/acceptance.md
    version: 1.1.0 -> 1.2.0
  - doc: docs/01-requirements/core.md
    version: 1.6.0 -> 1.7.0
  - doc: docs/02-design/system.md
    version: 1.6.0 -> 1.7.0
  - doc: docs/03-impl/entrypoint.md
    version: 1.4.0 -> 1.5.0
  - doc: docs/03-impl/cli.md
    version: 1.7.2 -> 1.8.0
  - doc: docs/03-impl/e2e.md
    version: 1.2.0 -> 1.3.0
---

# 変更記録:Codex サンドボックスはコンテナ境界に委ねて無効化する（D-27 ⑥ 追加）

## 変更理由・背景

利用者から「AppArmor が原因で claude コンテナ内から codex を呼べないということは起こらないか。
`/usr/bin/bwrap` の名前空間作成を許可しなければ codex が呼べないのではないか」という指摘を受け、
配布イメージ `claude-dev-claude:latest` で実測して確認した。指摘は当たっており、**codex は起動して
認証も通るが、codex が起こすシェルコマンドが例外なく失敗する**状態だった。

- codex 0.146.0 の Linux サンドボックスは bubblewrap（`/usr/bin/bwrap`）実装で、ユーザー名前空間の
  作成とマウント伝播の変更を必要とする。
- Claude コンテナは Docker 既定 seccomp と `docker-default` AppArmor の下で動く（`--security-opt` は
  付けていない）。実測では (a) 既定 seccomp が `CLONE_NEWUSER` を拒否して `unshare -U` が EPERM、
  (b) seccomp を外しても AppArmor が `mount --make-rslave /` を拒否——の 2 段で bwrap が起動できない。
  `--security-opt apparmor=unconfined` 単独では解決せず、seccomp と AppArmor の両方を外して初めて
  bwrap が動いた（＝原因は AppArmor 単独ではなく既定 confinement の 2 層）。
- 既定 `sandbox_mode`（`read-only` / `workspace-write`）では `codex exec` の全コマンドが `exited 1` に
  なり、さらに**モデルが失敗を認識せず出力を捏造した**（`echo MARKER_ONE` が失敗したのに `MARKER_ONE`
  を回答）。`codex doctor` もこの故障を検知しない。
- `--sandbox danger-full-access` および `config.toml` の `sandbox_mode = "danger-full-access"` で
  正常動作することを実測で確認した。

D-27 ⑤ は本決定のスコープを「開発者がコンテナ内で codex を使える状態」までと定めているが、
**codex のサンドボックス方針という判断項目が台帳に無かった**ため、その状態に到達していなかった。
判断項目の欠落＝決定の追加であり、起点は 00-requests/decisions.md とした。E2E-6 の実機確認が
「`codex` が起動する」までしか観測していなかったことも、この取りこぼしの一因である。

## 変更内容の要約

- **00-requests/decisions.md**: D-27 に ⑥ サンドボックス方針を追加。`config.toml` へ
  `sandbox_mode = "danger-full-access"` / `approval_policy = "never"` を既定として置く（不在時のみ・
  既存ファイルは上書きしない）、コンテナ側の seccomp/AppArmor は緩めない（`--security-opt` を足さない）。
  理由欄に 2 段の confinement の実測、出力捏造の観測、D-1（隔離境界はコンテナ／ホスト間のみ）および
  claude 側 `bypassPermissions` との整合、コンテナを緩める案を却下した理由を記載。
- **00-requests/glossary.md**: 用語「Codex サンドボックス」を追加（bubblewrap 実装・`sandbox_mode`・
  コンテナ内では無効化）。紛らわしい概念の区別に「Codex サンドボックス / Claude コンテナの隔離」を追加。
- **00-requests/acceptance.md**: AS-6 の操作にファイル読み書きを伴う作業依頼を加え、期待する結果に
  「シェルコマンドが実際に成功し `/workspace` を読み書きできる」、不合格条件に「毎回 bwrap エラーで
  失敗する／失敗したのに成功したかのような応答が返る」を追加。
- **01-requirements/core.md**: 要件12 に受け入れ基準 4〜7 を追加（4: codex のシェルコマンドが成功する、
  5: 既定設定を起動時に置く、6: 既存 `config.toml` を上書きしない、7: seccomp/AppArmor を緩めない）。
  旧基準4（オーケストレーター常用は対象外）は 8 へ繰り下げ。要件3-9 に、既定設定の生成が
  「設定はコンテナ固有」と両立する旨を補足。
- **02-design/system.md**: データモデルに `config.toml` 行を追加。判断5「Codex サンドボックスは
  コンテナ境界に委ねて無効化する」を新設（却下案は confinement 緩和・現状放置・イメージ焼き込みの 3 つ）。
  entrypoint モジュール行の責務に既定設定生成、対応要件に core/12 を追加。テスト戦略の core/12 備考に
  12-5〜12-7 の確認観点と担当を追記。**E2E-6 の検証フローにシェル実行成功を追加**。
- **03-impl/entrypoint.md**: 手順10 に `config.toml` 既定生成（不在時のみ・既存は不変）を追加し、
  なぜ必要かを 2 段 confinement の事実で説明。データアクセス表に同行、テスト対応表に確認 2 件
  （既定生成・既存不変）を追加。
- **03-impl/cli.md**: `docker run` に `--security-opt` を付けないことを明記（要件 core/12-7。対処は
  コンテナ側ではなく codex 側で行う）。cli-mac は共通挙動のため cli.md を正本とし変更なし。
- **03-impl/e2e.md**: E2E-6 の検証内容にシェル実行成功を追加。既知の制限に「**codex 自身の応答を
  合否根拠にしてはならない**（出力捏造・`codex doctor` も検知しない）。判定は `exec` 行の終了コードと
  `/workspace` に残った成果物で行う」を追加。
