---
slug: agy-gemini-image
state: awaiting-verify
critical: true
origin: derived
issue: なし
started: 2026-11-23T01:37:21+09:00
updated: 2026-11-23T08:20:00+09:00
commit: 7c40a6a3c569a2ee5aaff80d2a72c2b72665cf5b
summary: Antigravity CLI(agy)を配布イメージへ同梱して更新経路に載せ、Google(gemini)の認証を claude / codex と同じ形で共有する
---

# agy-gemini-image — agy の同梱・更新経路と gemini 認証の共有

## 目的・やらないこと

- 目的: 要望1(`.claude/missions/2026-11-23-agy-gemini-image/requests.md` 2026-11-23 01:20 逐語:
  「agyをコンテナイメージに追加して、こうしんもできるようにして。また、claudeと同じようにgeminiの認証情報も適切にコンテナにマウントして、コンテナ内から利用できるようにして」)。
  先行した汎用エージェントの未コミット実装8ファイルを土台として引き取り、検査し、SSOT を追いつかせる。
- やらないこと: Gemini CLI(`gemini` コマンド)の同梱 / `update-claude` が codex の版を渡さない既存の癖の修正 /
  `start` がホストの `~/.local/bin` を丸ごと運ぶ既存挙動の変更(いずれも申し送り・残務へ)。

## 影響範囲(closure)

- .devcontainer/Dockerfile.claude
- .github/workflows/ghcr-images.yml
- .gitignore
- Makefile
- README.md
- claude-dev
- claude-dev-mac
- docs/00-requests/acceptances.md
- docs/00-requests/decisions/auth.md
- docs/00-requests/decisions/dist.md
- docs/00-requests/decisions/env.md
- docs/00-requests/request.md
- docs/00-requests/terminology.md
- docs/01-requirements/functional.md
- docs/01-requirements/system.md
- docs/01-requirements/usecases.md
- docs/02-design/architecture.md
- docs/02-design/contracts/cli-container.md
- docs/02-design/environments.md
- docs/02-design/relations.md
- docs/02-design/system.md
- docs/03-impl/contracts/cli-container.md
- docs/03-impl/environments/images.md
- docs/03-impl/features.md
- docs/03-impl/index.md
- docs/03-impl/infra/local/docker-resources.md
- docs/03-impl/infra/local/ghcr.md
- docs/03-impl/relations/MODULE-cli-common-ensure-infrastructure.md
- docs/03-impl/relations/MODULE-cli-common-lock.md
- docs/03-impl/relations/MODULE-cli-common-require-setup.md
- docs/03-impl/relations/MODULE-cli-login-gemini.md
- docs/03-impl/relations/MODULE-cli-logout.md
- docs/03-impl/relations/MODULE-cli-reset.md
- docs/03-impl/relations/MODULE-cli-start.md
- docs/03-impl/relations/MODULE-cli-version.md
- docs/03-impl/relations/MODULE-entrypoint-claude.md
- docs/03-impl/relations/MODULE-makefile-update-claude.md
- docs/03-impl/tests/cli-common.md
- docs/03-impl/tests/cli-login-gemini.md
- docs/03-impl/tests/cli-start.md
- docs/03-impl/tests/cli-version.md
- docs/03-impl/tests/e2e.md
- docs/03-impl/tests/entrypoint.md
- docs/03-impl/tests/images.md
- docs/ux/flows.md
- docs/ux/policy.md
- docs/ux/screens/SCR-01-cli-commands.md
- scripts/entrypoint-claude.sh
- scripts/test-cli-version.sh

## 作業コミットに入れた入力

- なし

## 主張

- 触ったモジュールのテスト: `scripts/test-cli-version.sh` → 「結果: 成功 24 / 失敗 0」(版の名乗り。欠陥注入で赤を確認済み)。書き戻しの判定と一時コンテナの判定は切り出して確かめた(段5 の進捗メモ)。login-gemini・認証の共有の実ログイン経路は自動テストを持たず、**実ログインは未実施**(E2E-07 の実機手順を書いた)
- lint / build: `bash -n` を claude-dev / claude-dev-mac / scripts/entrypoint-claude.sh / scripts/test-cli-version.sh に → 4本とも出力なし(OK)。shellcheck は未導入で走らせていない。`make -n update-claude` OK。`yaml.safe_load(ghcr-images.yml)` OK。イメージの全ビルドはしていない — 既存イメージへ agy の導入手順を当てて `agy 1.5.14` / 版の一致 / `/usr/local/bin/agy` の解決を確認
- 資格情報の混入検査(secret_scan): **未設定**(このリポジトリには `tests/` の宣言ファイル自体が無い。埋めるのはテスト基盤を入れるタスク)。代わりに差分へ既知のトークン形の grep を当てて 0 件
- 版がビルドと揃った環境で走ったか: 未宣言(`02-design/environments.md` に版の固定の見出しが無い。版の名乗りのテストはホストの python3 で走らせた)
- 外部挙動の変化: あり(後方互換。agy の同梱・`login-gemini` サブコマンド・版の表示を足した)
- 認証・決済・不可逆・個人情報・監査への接触: あり(critical: true)
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 及第ライン)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | 本システムは利用者アカウントも管理者も持たない。作る/消すのは外部(Google)が発行した OAuth トークンの写しだけで、消しても `login-gemini` で取り直せる(締め出される主体が無い) | — |
| BR-02 | 該当 | ビルド引数 `AGY_VERSION` と、配布元の manifest から解決した版文字列を受け取る | 01 FR-env-09 の agy の条項(形式検証)+ `docs/03-impl/environments/images.md` |
| BR-03 | 非該当 | 利用者が値を決める識別子を新設しない | — |
| BR-04 | 該当 | 外部サービス(agy の配布 manifest。JSON)の応答から版を取り出して使う | `docs/03-impl/infra/local/ghcr.md` + `MODULE-makefile-update-claude`(取り出した値を MAJOR.MINOR.PATCH で検証し、外れたら中断) |
| BR-05 | 該当 | `logout` の削除対象に agy の認証ファイルが加わる | 01 FR-env-03-20 の改訂 + `docs/ux/screens/SCR-01-cli-commands.md`(既存の確認の状態) |
| BR-06 | 非該当 | 推測されると困る値を生成しない(トークンは Google が発行する) | — |
| BR-07 | 非該当 | 主体ごとに可否が変わる対象を扱わない | — |
| BR-08 | 該当 | 解決した版文字列をシェル(docker build の引数)へ渡す | `MODULE-makefile-update-claude` の実装上の判断(二重引用・形式検証の後にだけ渡す) |
| BR-09 | 非該当 | 秘密を突き合わせる経路を持たない(認証の照合は Google 側) | — |
| BR-10 | 非該当 | ブラウザから呼ばれる状態変更の経路を持たない | — |
| BR-11 | 非該当 | 共有ボリュームに足すのは取り直せる OAuth トークンだけで、失うとサービスが続かない値ではない | — |
| BR-12 | 該当 | 起動の入口に下位コマンド `login-gemini` を足す | 01 の受け入れ基準(版の表示)+ `MODULE-*` の実装上の判断(`claude-dev --version` がリリース台帳から読む) |
| BR-13 | 該当 | CLI の画面(SCR-01)に操作を1つ足す | 01 の受け入れ基準 + `docs/ux/policy.md`「画面を使える手段(BR-13)」 |

## 決定シート(回答済み)

- 2026-11-23 人間の回答(この作業ウィンドウで、逐語): 「すべて推奨どおり」
  - 概念1「gemini の認証情報」= agy が保存する Google の認証トークン `~/.gemini/antigravity-cli/antigravity-oauth-token` 1本 → AI推奨どおり
  - 論点1 → A(要求の文書に4点を書き足す: ①同梱 CLI に agy ②受け入れシナリオ1本 ③版は日次ビルド時点の最新に固定・過去版の焼き直し不可 ④agy の自動更新は止めない)
  - 方針合意: 異議なし(全方針に合意)

## 質問キュー(出口のシートの種)

- なし

## 調査メモ

- check-ssot.py の凍結(2026-11-23 01:3x): NG 違反 42 件(CS21 4件 / CS28 38件)。クロージャに入りうるもの:
  `00-requests/acceptances.md` の summary が AC 族より狭い(CS21。着手前から在る)。他はクロージャの外。
- 公式 install.sh(2026-11-23 取得): `DOWNLOAD_BASE_URL="https://antigravity-cli-auto-updater-974169037036.us-central1.run.app"`(:11)、
  `MANIFEST_URL="$DOWNLOAD_BASE_URL/manifests/$platform.json"`(:102)。版を選ぶ引数は無い(`-d/--dir` と `-h` のみ)。
  CI と Makefile のハードコードは公式 install.sh と同じ URL である(先行報告の主張を確認)。
- ホストの `~/.gemini/` は `antigravity-cli/` と `config/` のみ(Gemini CLI の資格情報 `oauth_creds.json` は無い)。
  ホストの `~/.local/bin/agy` は 273,240,776 バイトの実ファイル。
- Claude Code の自己更新はイメージで止めていない(`Dockerfile.claude` / entrypoint に DISABLE_AUTOUPDATER 無し)。
- `start` の `~/.local/bin` 取り込みは entrypoint で `cp -a --update=none`(`scripts/entrypoint-claude.sh:620`)なので、
  ホストの agy がイメージの agy を上書きすることはない(無駄なコピーが起きるだけ)。

## 進捗メモ(再開点)

- 2026-11-23 01:40 段0〜1: 入口(guard-branch OK)、計器(課題票6/残務17/未検証記録2/未回答シート1)、クロージャ確定中。
  00 の層を変えるため着手時のシートを提示する。
- 2026-11-23 01:39 シート docs/sheets/agy-gemini-image.md を提示(相談 .claude/missions/2026-11-23-agy-gemini-image/questions/1.md)。回答待ち。
- 2026-11-23 回答「すべて推奨どおり」を転記し、シートを削除。段2(00→01→02→03+ux)へ。
- 2026-11-23 06:40 段2 00: RQ-env-03 に agy、AC-09、D0-dist-07(同梱・版・認証・ログイン・自己更新・範囲)、D0-auth-03 / D0-env-08 項4・6、用語 agy。
- 2026-11-23 06:50 段2 01: FR-env-01-16(7コマンド)/ 01-37〜40(版の名乗り・BR-13)/ FR-env-03-25〜30 / FR-env-09-12〜14・09-7 の除外 / FR-env-12-15〜17、UC-07、SR-15 と依存の表。
  [DS-01] login-gemini は既存のログインを引き継がない — 理由: agy はログイン済みだと認証画面を出さない / 見直す条件: 引き継いでほしいと言われたとき
  [DS-01] `claude-dev --version` は台帳から読み、無ければ「未リリース」 — 理由: BR-12 / 見直す条件: 版の置き場が変わったとき
- 2026-11-23 07:00 段2 02: MOD-cli-login-gemini・MOD-cli-version、カバレッジ行、E2E-07、PLAN-cli-login-gemini・PLAN-cli-version、契約の7コマンド、DSN-auth-01・DSN-dist-01 に agy。
- 2026-11-23 07:20 段3: `--version` を両 CLI に実装、`scripts/test-cli-version.sh`(期待値は受入基準から自分で書いた。隔離執筆はしていない — 表示の正常系・境界と台帳の異常系で、版の名乗りは認証・決済などに当たらないため。欠陥注入済み)。
  先行実装の検査で直したもの: Makefile と CI の agy の版の検査が `[0-9]*` の glob / 行ごとの grep で `1.5.14; …` や複数行を通していた(BR-04/BR-08)→ 文字種と3つ組の両方を確かめ、build-arg を二重引用。ヘルプ・logout の文言の「Gemini」単独を agy に。
  [DS-01] agy の E2E は自動スクリプトを作らず手順だけ — 理由: 実ログインが要る / 見直す条件: 無人で通せる認証の手段ができたとき
  [DS-01] update-claude は agy の版も渡し、codex の版を渡さない癖は直さない — 理由: 範囲外 / 見直す条件: codex の手元更新を求められたとき
- 2026-11-23 07:35 段3: 既存イメージ(2か月前)に agy の導入手順を当てた — install.sh で 1.5.14、`AGY_VERSION=1.5.14` と一致、`/usr/local/bin/agy` が非ログインの sh から解決。check-ux 0件、check-ssot は凍結時から新規の違反なし(CS21 を 4→0 に直した)。

- 2026-11-23 07:50 段5: 版の繰り上げ(MINOR)、残務3行追記、履歴 docs/histories/2026-11-23-agy-gemini-image.md、build-index。出口のシート: お伺いする事項なし。
  UX 文書の検索: 改訂した FR-env-01-16 / FR-env-03-20 — SCR-01 の該当(7コマンド)を直した。
  独立レビューを review-230649 へ直接依頼(メッセージ 5)。返りを待って記録を閉じる。
- 2026-11-23 08:10 レビュー(メッセージ 6)の所見6件を裁定し、F1/F2/F4/F5/F6 を直した(下の節)。書き戻しの判定と一時コンテナの判定を切り出して確かめた(新しい共有側を上書きしない / 644 の元でも 600 で作る / リンクの先へ書かない)。テスト 24/24、`bash -n` 4本、YAML、check-ux 0、check-ssot 新規違反なし。

- 2026-11-23 08:20 段5 閉じ: 索引を更新、記録を awaiting-verify にした(commit 7c40a6a)。

## 直さなかった指摘(独立レビュー・探索的QA)

独立レビュー review-230649(claude・同一エンジン別文脈。2026-11-23、範囲 8fc4eba..96b8665)の所見6件の裁定:
- F1【中】書き戻しが新しいトークンを古いもので上書きする — **直した**(手元が新しいときだけ書く。FR-env-03-27 に追記)。claude / codex の同型は残務へ
- F2【中】`.gemini` がリンクだとリンク先へトークンを書く — **直した**(FR-env-03-31。start と entrypoint の両方で拒む)。`.claude` / `.codex` の同型は残務へ
- F3【低】`.gemini` を追跡しているリポジトリと ~/.gemini・.gitignore 追記がぶつかる — **直さない**。理由: `.claude` と同じ形を選んだ帰結で、D0-dist-07 項3 が `~/.gemini` の置き場を claude と揃えると決めている。既知の制限として MODULE-entrypoint-claude に記録済み / 見直す条件: Gemini CLI を同梱するとき(D0-dist-07 見直す条件(b))
- F4【低】600 を作る瞬間に保証しない / agy の書き直し後の権限 — **直した**(`umask 077` で作り、ループで手元も毎回 600 に戻す)。ホストの agy は 600 で書くことを確認(`stat` → 600)
- F5【nit】CI が検査の前に版の値をログへ出す — **直した**(検査の後へ移した)
- F6【nit】`--version` が `01.2.3` を通す — **直した**(各桁の先頭 0 を拒む。テストを1ケース足して24件)
- 確認できなかった点(`agy --version` の出力形)— 段3 で実測済み: 飾りのない `1.5.14`。tests/images.md #25 に書き足した
- 一番弱い点(`curl … install.sh | bash`、配布元から独立した完全性の保証が無い)— **直さない**。理由: 公式の導入手段を使うと D0-dist-07 で決め、Claude Code も同じ形(`claude.ai/install.sh | bash`)で入れている。受け入れた危険 / 見直す条件: 配布元が署名か独立したチェックサムを出したとき

## 申し送り

- なし
