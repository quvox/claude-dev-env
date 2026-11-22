---
id: 2026-11-23-agy-gemini-image
date: 2026-11-23
record: docs/build-records/agy-gemini-image.md
critical: true
origin_layer: 00
issue: なし
summary: agy(Google Antigravity CLI)を配布イメージへ同梱して更新経路に載せ、Google の認証トークンを claude / codex と同じ形で共有する。claude-dev に版の名乗りを足す
---

<!-- タスクごとに1ファイル。追記のみ(確定したエントリの文章は書き換えない)。
     タスク・進捗・TODO は書かない(それは構築記録の仕事)。 -->

# 2026-11-23 agy の同梱・更新経路と Google 認証の共有

## 変更理由

### R-01 同梱するエージェント CLI に agy を加え、認証をホストで共有する

- 起点層・根拠: 00(範囲の変更)。人間の要望(2026-11-23 01:20)「agyをコンテナイメージに追加して、こうしんもできるようにして。また、claudeと同じようにgeminiの認証情報も適切にコンテナにマウントして、コンテナ内から利用できるようにして」と、決定シートの回答「すべて推奨どおり」(2026-11-23)
- 変更が必要になった条件: 同梱するエージェント CLI が Claude Code と Codex CLI の2つに限られていた(`RQ-env-03`)

### R-02 新しいサブコマンドを足したので、claude-dev に版を名乗らせる

- 起点層・根拠: 01(`BR-12`。起動の入口 `login-gemini` に触れたため)
- 変更が必要になった条件: claude-dev が自分の版を名乗る手段を持っていなかった

## 変更内容の要約

- 配布イメージ2種へ agy を公式インストーラで導入し、CI と `make update-claude` が配布元の更新情報から版を解決して渡す(版は日次ビルド時点の最新に固定。過去の版の焼き直しは不可)
- `claude-dev login-gemini` で取った agy の認証トークン1本を共有ボリューム `gemini/` に置き、`start` のコピー・30秒の書き戻し・`logout` の削除・排他(7コマンド)へ載せた
- `claude-dev --version` / `-v` がリリース台帳から版を読み、無ければ「未リリース」と表示する
- 独立レビュー(review-230649)の所見で、agy の書き戻しを「手元のほうが新しいときだけ」にし、`.gemini` がシンボリックリンクなら認証を置かない(FR-env-03-31)、トークンを作る瞬間から 600、CI のログ出力を検査の後へ、版の各桁の先頭 0 を拒む、を足した

## 更新した仕様ドキュメント

| 理由ID | 仕様ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/00-requests/request.md | 1.6.0 → 1.7.0 | RQ-env-03 に agy と共有するのはトークン1本であることを足した。完成イメージと制約に agy |
| R-01 | docs/00-requests/acceptances.md | 1.6.1 → 1.7.0 | AC-09(agy の認証共有)を足した。summary の範囲表記をやめた(CS21) |
| R-01 | docs/00-requests/terminology.md | 1.7.0 → 1.8.0 | 用語 agy を足し、エージェント CLI の列挙に agy |
| R-01 | docs/00-requests/decisions/dist.md | 1.5.0 → 1.6.0 | D0-dist-07(同梱・版・認証・ログイン導線・自己更新を止めない・範囲)を新設 |
| R-01 | docs/00-requests/decisions/auth.md | 1.3.1 → 1.4.0 | D0-auth-03 の共有ファイルとコピー先に agy |
| R-01 | docs/00-requests/decisions/env.md | 1.7.0 → 1.8.0 | D0-env-08 項4(logout の削除対象)と項6(排他の7コマンド)に login-gemini / agy |
| R-01, R-02 | docs/01-requirements/functional.md | 1.24.0 → 1.25.0 | FR-env-01-16 を7コマンドに、FR-env-01-37〜40(版の名乗り・キーボードだけで完了)、FR-env-03-25〜31、FR-env-09-12〜14 と 09-7 から agy を除外、FR-env-12-15〜17 |
| R-01 | docs/01-requirements/usecases.md | 1.7.1 → 1.8.0 | UC-07 と UC-01 代替フロー A6 |
| R-01 | docs/01-requirements/system.md | 1.3.0 → 1.4.0 | SR-15 に Google アカウント、依存に Google と agy の配布元 |
| R-01, R-02 | docs/02-design/system.md | 2.21.0 → 2.22.0 | MOD-cli-login-gemini・MOD-cli-version、カバレッジ行、E2E-07 |
| R-01, R-02 | docs/02-design/relations.md | 1.12.0 → 1.13.0 | PLAN-cli-login-gemini・PLAN-cli-version と共有関数の呼び出し元 |
| R-01 | docs/02-design/architecture.md | 1.10.0 → 1.11.0 | DSN-auth-01・DSN-dist-01 に agy(版は一致の検査にだけ使う)、外部システムに Google |
| R-01 | docs/02-design/contracts/cli-container.md | 1.17.0 → 1.18.0 | 認証の受け渡しに gemini/、排他を7コマンドに |
| R-01 | docs/02-design/environments.md | 1.7.1 → 1.8.0 | 認証の手順に login-gemini |
| R-01 | docs/03-impl/environments/images.md | 1.4.0 → 1.5.0 | ビルド引数 AGY_VERSION と、版が一致しないときの落とし穴 |
| R-01 | docs/03-impl/infra/local/ghcr.md | 1.3.1 → 1.4.0 | AGY_VERSION の解決と検査、agy は切り戻しの版指定ができないこと |
| R-01 | docs/03-impl/infra/local/docker-resources.md | 1.2.0 → 1.3.0 | 認証ボリュームの gemini/ と ~/.gemini の symlink |
| R-01 | docs/03-impl/contracts/cli-container.md | 1.13.0 → 1.14.0 | 認証コピーの対象とロックを取る操作に login-gemini |
| R-01, R-02 | docs/03-impl/index.md | 1.39.0 → 1.40.0 | 網羅するモジュールに2つ足した(27モジュール) |
| R-01 | docs/03-impl/tests/cli-common.md / cli-start.md / entrypoint.md / images.md / e2e.md | 各 MINOR | 新しい条項の対応行と未検証の全件、E2E-07 の実機確認手順 |
| R-01, R-02 | docs/03-impl/tests/cli-login-gemini.md / cli-version.md | 新規 1.0.0 | 新モジュールのテスト対応 |
| R-01, R-02 | docs/ux/flows.md / policy.md / screens/SCR-01-cli-commands.md | (版なし) | UC-07 の流れ、画面を使える手段(BR-13)、19 種のサブコマンド・7コマンドの排他・版の表示の状態・達成条件 |

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| R-01 | `.devcontainer/Dockerfile.claude` | 両終端ステージに agy を導入し、渡した版と導入された版の一致を検査、`/usr/local/bin/agy` へ symlink | 96b8665 |
| R-01 | `.github/workflows/ghcr-images.yml` / `Makefile` | 配布元の更新情報から agy の版を解決し、数字と点だけ・3つ組の両方を確かめてから渡す | 96b8665 |
| R-01 | MODULE-cli-login-gemini / MODULE-cli-start / MODULE-cli-logout / MODULE-entrypoint-claude | ログイン・起動時のコピー(600)・書き戻し・ログアウトの削除対象 | 96b8665 |
| R-02 | MODULE-cli-version / `scripts/test-cli-version.sh` | `--version` / `-v` と自動テスト20件 | 96b8665 |

## 実施した移行

なし(データ移行もスキーマ変更も無い。既存の共有ボリュームは `gemini/` を起動時に作るだけで、既存の中身に触れない)

### ロールバック・復旧記録

| 理由ID | 不可逆点 | 切り戻し可能な条件・期限 | 切り戻し手順 / forward-fixのみの理由と復旧手順 | 復元元 | 確認日 | 復旧確認コマンド・結果 |
|---|---|---|---|---|---|---|
| R-01 | なし(認証トークンは Google が発行し、消えても `login-gemini` で取り直せる。既存の claude / codex の認証の置き場は変えていない) | いつでも | イメージは古いタグを `claude-dev pull <TAG>` で取得する。CLI はこのコミットを revert する。プロジェクトに残った `.gemini/` と共有ボリュームの `gemini/` は `claude-dev logout` で消える | 不要(取り直せる資格情報だけ) | 2026-11-23 | `claude-dev --version` → 「claude-dev 未リリース」(CLI が動くこと)。ログインの実経路は未確認(E2E-07) |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 追加 | MODULE-cli-login-gemini | agy の Google 認証を一時コンテナで取り、共有ボリュームの gemini/ へ置く |
| 追加 | MODULE-cli-version | リリース台帳から版を読んで名乗る |
| 変更 | MODULE-cli-common-lock / -ensure-infrastructure / -require-setup | callers に MODULE-cli-login-gemini を追加 |
| 変更 | MODULE-cli-start / MODULE-cli-logout / MODULE-cli-reset / MODULE-entrypoint-claude / MODULE-makefile-update-claude | agy の認証のコピー・削除・書き戻し、agy の版の解決 |

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| 要求の文書に agy を書き足すか | 書き足す(4点) | 書き足さずコードだけ入れる | 検証で agy を判定する基準が無くなる / Google が版を選べる導入手段を出したら版の項を改める |
| agy の版の固め方 | 日次ビルド時点の最新に固定し、渡した版は一致の検査に使う | 版を渡さず最新を入れる / 配布元の個別の版のファイルを直接取る | 前者はキャッシュが永久に当たって中身が凍結する。後者は公式の導入手段から外れ、検証の経路を自前で持つ |
| 自己更新 | 止めない(止めたい人は env ファイルに1行) | イメージで止める | Claude Code と扱いが割れる |
| login-gemini の既存ログイン | 引き継がない | codex と同じく引き継ぐ | agy はログイン済みだと認証の画面を出さず、別アカウントへ切り替えられない / 引き継いでほしいと言われたら見直す |
| agy の動作確認 | 実機の手順(E2E-07) | 自動スクリプト | 実ログインが要り無人で回せない |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 知見 | 今回限り(先行実装の検査で見つけた形の検査の穴。直した箇所に判断として記録済み) | 外から受け取った版の文字列を `case` の `[0-9]*` や行ごとの `grep` だけで確かめると、`1.2.3; …` や複数行の値が通る。文字種と形の両方を確かめる |
| 新規の課題票 | なし | — |
| 残務 | docs/residual.md | claude / codex の書き戻しが新しい認証を古いもので戻しうる・`.claude` / `.codex` がリンクだと先へ書く(独立レビューが見つけた既存の型)ほか、update-claude の codex の版・ホストの agy の複写・manifest の URL の二重記述 |
| 棚上げ | なし | — |
| 気づき | (申し送り)構築記録の申し送りへ | check-sheet の SH10 が「ログイン」の中の「ログ」に当たって誤検出する(キットの道具の側。`/kit-improve`) |
| 解消した課題票 | なし | — |

残務の判定(クロージャに path が在る行): `docs/03-impl/relations/MODULE-cli-start.md` の .gitignore の注意 — 持ち越す(範囲外)/
`docs/00-requests/decisions/` の見直す条件 — 持ち越す(人間の決定に書き足すもの。新設した D0-dist-07 は持っている)/
`docs/00-requests/terminology.md` の含む例 — 持ち越す(既存の8用語。新設した agy は埋めた)/
`docs/03-impl/infra/local/docker-resources.md` の chrome-data — 持ち越す(範囲外)/
`docs/00-requests/acceptances.md` の受け入れの判定 — 持ち越す(範囲外)/ `docs/02-design/architecture.md` の本数 — 持ち越す(範囲外)
