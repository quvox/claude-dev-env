---
id: task-fix-tmux-server-drops-reserved-env
phase: 反映
lane: standard
origin_layer: 01
external_behavior: true
irreversible_data: false
security_payment_privacy: false
public_contract_breaking: false
shared_resource_format: true
unresolved_impact: false
rollback_defined: true
issue: docs/issues/107-bug-project-env-file-values-do-not-reach-tmux-windows.md
origin: human-report
date: 2026-08-19
updated: 2026-08-19
source:
  - docs/01-requirements/functional.md
  - docs/02-design/contracts/cli-container.md
  - docs/02-design/system.md
  - docs/03-impl/contracts/cli-container.md
  - docs/03-impl/relations/MODULE-entrypoint-claude.md
  - docs/03-impl/relations/MODULE-cli-start.md
  - docs/03-impl/tests/entrypoint.md
  - docs/03-impl/tests/e2e.md
  - docs/03-impl/index.md
summary: entrypoint が tmux セッションを su -l で起こすため、コンテナに渡した環境変数(予約名と env ファイルの組の両方)が tmux 窓の中の全プロセスに届いていないのを直す
---

# task-fix-tmux-server-drops-reserved-env tmux 窓に予約環境変数が届かないのを直す

> 解決済みの経緯: (まだ無し)

## 目的

`entrypoint` が tmux セッションを `su -l` で起こすため、`docker run -e` とイメージの `ENV` で
渡した予約環境変数(`DOCKER_HOST` / `COMPOSE_PROJECT_NAME` / `container` / `NODE_OPTIONS` /
`CLAUDE_DEV_*`)が tmux サーバの環境から落ち、**tmux 窓の中で動く全プロセスに届いていない**。
本システムの主たる使い方は tmux 窓の中で `claude` / `codex` を動かすこと(`FR-env-01-1` /
`UC-01` 基本フロー4)なので、`FR-env-07`(コンテナ内から Docker を使える)と `FR-env-07-5`
(compose 資源をプロジェクト間で衝突させない)が主経路で満たされていない。これを直す。

**2026-08-19 に範囲を広げた(人間の裁定)。** 同じ `su -l` が **`.claude-dev.yaml` の `env_file:` で
渡した組も落としており、`AC-08`(プロジェクトごとの環境変数がコンテナ内のツールに見える)が
実機に対して不合格**であることが実測で分かった(`docs/issues/107`)。人間は
「いまのタスクに畳み込む」「案 B(tmux を起こす `su` から `-l` を外す)」を選んだので、
**このタスクは「コンテナに渡した環境変数が、起動経路を問わず tmux の窓の中でも参照できる」ことを
一度に満たす**。影響するファイルは1つも増えていない。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | **予約環境変数**(`FR-env-07-13`)と **env ファイルで渡した組**(`FR-env-14` に新設する条項)の両方が **tmux 窓の中で起動したプロセスにも届く**ことを 01 の受入基準として明文化し、02 の契約に受け渡しの義務を書き、03 に機構を書き、`scripts/entrypoint-claude.sh` の tmux 起動から **`-l` を外す**(案 B)。誤った断定(「`-e` なら対話・非対話シェルと `docker exec` の全てで有効」)を事実へ直す |
| やらないこと(このタスクの範囲外) | `-l` を外した副産物として直る `TZ` / `LC_ALL` / 入力メソッドの各変数について、**条項を新設すること**(直るが要件として書き足さない — `AC-08` と `FR-env-07-13` が要求しているのは env ファイルの組と予約名であり、それ以外を要件にすると次に変数が増えるたびに条項が要る)。tmux 以外の起動経路の見直し(`su` を使う他の1箇所は `-l` が無く環境を保っていることを実測で確認済み)。`SSH_AUTH_SOCK` の受け渡し方式の変更(現に届いており、届いている理由は別機構)。稼働中コンテナへの応急処置(製品の変更ではない)。`docs/pendings.md` P-005(ハッシュ短縮値6桁の衝突)の解消 |

## 影響範囲(closure)

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | docs/00-requests/decisions/env.md | - | 変更なし(理由: `D0-env-06` の「起動経路によらず常に付いている」という意図は既に正しく、実装が満たしていないだけ) |
| 00 | docs/00-requests/request.md | - | 変更なし(理由: 「やらないこと」7 が予約名を失ったときの害を既に述べている) |
| 00 | docs/00-requests/acceptances.md | - | 変更なし(理由: `AC-03` も `AC-08` も本文は変わらない。**`AC-08` は既に「立ち上がった端末の中で…見える」を要求しており、本タスクはそれを満たすだけ**である) |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | modify(`FR-env-07` と `FR-env-14` の2節) |
| 01 | docs/01-requirements/usecases.md | - | 変更なし(理由: `UC-01` の基本フローは tmux の開始を既に持ち、フローも代替・例外も変わらない) |
| 02 | docs/02-design/contracts/cli-container.md | new-features/02-design/contracts/cli-container.md | modify |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | modify |
| 02 | docs/02-design/relations.md | - | 変更なし(理由: 連携の相手も向きも同期性も変わらない) |
| 03 | docs/03-impl/contracts/cli-container.md | new-features/03-impl/contracts/cli-container.md | modify |
| 03 | docs/03-impl/relations/MODULE-entrypoint-claude.md | new-features/03-impl/relations/MODULE-entrypoint-claude.md | modify |
| 03 | docs/03-impl/relations/MODULE-cli-start.md | new-features/03-impl/relations/MODULE-cli-start.md | modify |
| 03 | docs/03-impl/tests/entrypoint.md | new-features/03-impl/tests/entrypoint.md | modify |
| 03 | docs/03-impl/tests/e2e.md | new-features/03-impl/tests/e2e.md | modify |
| 03 | docs/03-impl/index.md | -(§3-4 で版のみ更新) | 版のみ更新 |

**変更の起点層は 01 である。** 理由: `FR-env-12-2`(同梱 Codex CLI が対話シェル・非対話シェル・
`docker exec` のいずれからも解決できること)という**同層の前例**が、本システムでは「どの起動文脈で
有効か」を 01 の受入基準として列挙する形を既に採っている。今回の欠陥はまさにその列挙から
**tmux 窓**が漏れていたことなので、同じ形で 01 に条項を足すのが起点である。ただしこの判断そのものは
シートの論点1 に載せてある(上流 `FR-env-07-1` は「コンテナ内からの Docker 操作」と無限定に書いて
おり、それだけを読めば 02 以下の修正で足りるとも読めるため — 三方向が食い違うので問う)。
**論点1 が「足さない」で回答された場合、01 の行は「変更なし」になり起点層は 02 へ下がる**
(closure はそのぶん狭まるだけで、他の行は変わらない)。

## 読む範囲(読了記録)

<!-- lane: standard。closure 表とその上流・下流を覆う(CLAUDE.md §4)。
     まとまった読み取りは bulk-read サブエージェントへ委譲した(CLAUDE.md §8)。 -->

- 全文読了: 2026-08-19
  - docs/00-requests/request.md@1.6.0
  - docs/00-requests/decisions/env.md@1.7.0
  - docs/01-requirements/functional.md@1.19.1
  - docs/02-design/contracts/cli-container.md@1.13.0
  - docs/03-impl/tests/entrypoint.md@1.2.1
  - docs/03-impl/tests/e2e.md@1.11.0
  - docs/03-impl/contracts/cli-container.md@1.10.0
  - docs/03-impl/index.md@1.29.1
  - docs/02-design/system.md@2.15.0
  - docs/03-impl/relations/MODULE-entrypoint-claude.md@-
  - docs/03-impl/relations/MODULE-cli-start.md@-
- 不要: docs/00-requests/decisions/auth.md@1.3.1 — 理由: 読んだが影響しない(認証情報の保管・共有・破棄のみを扱い、環境変数の到達範囲に触れない)
- 不要: docs/00-requests/decisions/dist.md@1.3.0 — 理由: 読んだが影響しない(イメージ配布と外部 CLI 同梱のみ)
- 不要: docs/00-requests/decisions/scope.md@1.2.1 — 理由: 読んだが影響しない(記述粒度と実装範囲のみ)
- 不要: docs/00-requests/decisions/sec.md@1.4.0 — 理由: 読んだが影響しない(`DOCKER_HOST` / `tmux` / シェルのいずれにも言及が無いことを機械検索で確認済み。信頼境界は動かない)
- 不要: docs/00-requests/terminology.md@1.7.0 — 理由: 読んだが影響しない(新しい語を導入しない)
- 不要: docs/00-requests/acceptances.md@1.6.1 — 理由: 読んだが影響しない。`AC-03` も **`AC-08`(プロジェクトごとの環境変数がコンテナ内のツールに見える)も本文は変わらない** — `AC-08` は既に「立ち上がった端末の中で…見える」を求めており、本タスクはそれを満たしていない状態を直すだけである(受け入れ基準の側を動かす必要はない)
- 不要: docs/01-requirements/decisions/split.md@1.5.0 — 理由: 読んだが影響しない(`FR-env-07` の分割可否 `D1-split-01` は既に「他の11条項は不可分」と定めており、条項の追加はこの判断を動かさない)
- 不要: docs/01-requirements/non-functional.md@1.8.0 — 理由: 読んだが影響しない(目標値も測定方法も変わらない)
- 不要: docs/01-requirements/system.md@1.3.0 — 理由: 読んだが影響しない(`tmux` / シェル / 環境変数への言及が無いことを機械検索で確認済み)
- 不要: docs/01-requirements/usecases.md@1.7.0 — 理由: 読んだが影響しない(フローも代替・例外も変わらない)
- 不要: docs/02-design/architecture.md@1.7.0 — 理由: 読んだが影響しない(構成図の `DOCKER_HOST` の矢印は向きも相手も変わらない)
- 不要: docs/02-design/contracts/docker-api.md@1.2.0 — 理由: 読んだが影響しない(docker-proxy の検査・書き換え規則は変わらない)
- 不要: docs/02-design/contracts/entrypoint-firewall.md@1.0.1 — 理由: 読んだが影響しない(ファイアウォール適用の取り決めに触れない)
- 不要: docs/02-design/environments.md@1.5.0 — 理由: 読んだが影響しない(lint/テスト/ビルドのコマンド文字列は変わらない)
- 不要: docs/02-design/logging.md@1.9.0 — 理由: 読んだが影響しない(端末出力も常駐プロセスログも変えない)
- 不要: docs/02-design/relations.md@1.11.1 — 理由: 読んだが影響しない(`PLAN-*` の相手・向き・同期性が変わらない)

<!-- `MODULE-*.md` は frontmatter に `version:` を持たない(層代表 `docs/03-impl/index.md@1.29.1` が
     層全体の版と合格証を持つ。`.claude/directions/03-impl.md`「Frontmatter」)ので `@-` と書く。
     まとまった読み取りは bulk-read サブエージェントへ委譲し、`path:line` と原文の逐語引用で受け取った。 -->

## 決定シート(回答済み)

> 回答済み: sheet.md(転記済み)

- チャット回答(2026-08-19)「推奨どおりで」 — 対象: 一括 — 反映先: 下表のとおり
- チャット回答(2026-08-19)「1.b。2.B。3.タスクが終わってからcommit」 — 対象: 論点2(および進め方) — 反映先: 下表の論点2 の行。**1.b** = `docs/issues/107` をいまのタスクへ畳み込む / **2.B** = tmux を起こす `su` から `-l` を外す / **3** = コミットはタスク完了後(仕様ドキュメントへは反映しない運用上の指示)
  (人間はチャットで回答したので `sheet.md` の「★あなたの記入」は空のままである。
  `.claude/directions/task-memo.md` §1.2 の第3の経路)

| # | 論点 | 回答 | 反映先 |
|---|---|---|---|
| 概念1 | 曖昧さなし(守備範囲 = コンテナ内の全プロセス / 対象 = 予約名の集合全体) | 推奨を承認 | `new-features/02-design/contracts/cli-container.md`(契約の義務として書く) |
| 論点2 | env ファイルの値も tmux の窓へ届けるか、届けるならどの直し方にするか | **案 B を明示指定**(`su` から `-l` を外す)。あわせて `docs/issues/107` を本タスクへ畳み込む | `FR-env-14-11`(`new-features/01-requirements/functional.md`)と `new-features/03-impl/relations/MODULE-entrypoint-claude.md` 手順20 |
| 論点1 | 01 に「起動経路によらず予約環境変数が届くこと」を条項として書き足すか | 推奨を承認(**案 A = 書き足す**) | `FR-env-07-13`(`new-features/01-requirements/functional.md`)。連動して `new-features/02-design/system.md` の要件カバレッジ表に主担当 `MOD-entrypoint` の行、`new-features/03-impl/tests/entrypoint.md` に対応行、`new-features/03-impl/tests/e2e.md` に E2E-01 の手順 |

## 未決点

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| 1 | VM モードでは `DOCKER_HOST` がゲスト VM を指すが、`entrypoint` 自身の環境は上書きされていない。手順20 はどちらの値を引き継ぐのか | **ドキュメント記載** — 02 の契約が「VM モードでは entrypoint が上書きする」と1つの値しか認めていないので上流が答えている。手順15 が自身の環境にも `export` し、手順20 は自分の環境を載せる、と `MODULE-entrypoint-claude` へ書いた | 実装ドライラン パス1 |
| 2 | macOS 経路では `SSH_AUTH_SOCK` がホストの `-e` で渡ってこない(手順4 が作ったソケット)。手順20 は何を載せるのか | **ドキュメント記載** — 手順5 が rc へ書くのと同じ値を自身の環境にも `export` する、と `MODULE-entrypoint-claude` へ書いた | 実装ドライラン パス1 |
| 3 | 値にシェルのメタ文字が入りうるのに、`su -l -c "…"` はシェル文字列として渡る | **委任決定(DS-05)** — 引用する。前例が同じファイルの `:513` にある(`DOCKER_HOST='…' setsid …`)。`MODULE-entrypoint-claude` 手順20 に書いた | 実装ドライラン パス1 |
| 4 | 該当する変数が1つも無いとき、列挙が非ゼロを返して `set -e` が初期化を止めうる | **委任決定(DS-02)** — 止めない形にする。`MODULE-entrypoint-claude` の実装上の判断へ開示行を書いた | 実装ドライラン パス2 |
| 5 | 「値を持っているものだけを載せる」の境界(空文字と未設定の区別) | **ドキュメント記載** — `CLAUDE_DEV_VM` のように未設定と空で意味が違うものがあるので空文字で作らない、と手順20 に書いた | 実装ドライラン パス1 |

**人間判断へ回した未決点は0件。** 問う基準(`.claude/directions/delegation.md` §1)を満たすものが無かった —
5件とも上流が答えているか、標準委任の中で決まる。

## 調査メモ

| # | 調べたこと | 判明した事実 | 出どころ |
|---|---|---|---|
| 1 | tmux サーバの起動方法 | `su "$USERNAME" -s /bin/zsh -l -c "cd /workspace && tmux -f ~/.tmux.conf new-session -d -s main 'exec zsh -l'"`。**`-l` が付いている** | `scripts/entrypoint-claude.sh:774`-`:776` |
| 2 | 同じ entrypoint の別の `su` | `su "$USERNAME" -s /bin/bash -c "/tmp/start-user-desktop.sh" &`。**`-l` が無い** | `scripts/entrypoint-claude.sh:767` |
| 3 | 実測: tmux サーバの環境 | pid 278 の environ は `HOME LANG LOGNAME MAIL OLDPWD PATH PWD SHELL SHLVL TERM USER _` の12個のみ。`DOCKER_HOST` / `COMPOSE_PROJECT_NAME` / `container` / `NODE_OPTIONS` / `CLAUDE_DEV_VNC` が無い | 実機コンテナ `ct_matchsupport`(2026-08-19 実測) |
| 4 | 実測: `-l` 無しの `su` の環境 | pid 274(`start-user-desktop.sh`)は `DOCKER_HOST` / `COMPOSE_PROJECT_NAME` / `container` / `NODE_OPTIONS` / `CLAUDE_DEV_VNC` を**すべて持つ** | 同上 |
| 5 | 実測: tmux 窓の中のプロセス | pid 685(`claude`)の environ に `DOCKER_HOST` / `COMPOSE_PROJECT_NAME` / `container` / `NODE_OPTIONS` が無い。`SSH_AUTH_SOCK` と `DISPLAY` は在る | 同上 |
| 6 | `SSH_AUTH_SOCK` と `DISPLAY` だけ届く理由 | tmux の `update-environment` の既定値が `DISPLAY KRB5CCNAME SSH_ASKPASS SSH_AUTH_SOCK SSH_AGENT_PID SSH_CONNECTION WINDOWID XAUTHORITY` で、クライアント接続時にこの8個だけをセッション環境へ写す。予約名は1つも入っていない | 実機 `tmux show-options -g update-environment`(2026-08-19 実測) |
| 7 | 実測: `docker exec` 経由なら届くか | 届く。`docker exec` はコンテナ設定の env を継承するので `DOCKER_HOST` も `container` も在る。**壊れているのは tmux 経由だけ** | 同上 |
| 8 | tmux セッションを作る経路は2つある | (a) entrypoint の `su -l`(壊れている)、(b) `start` の再接続経路 `docker exec ... tmux new-session -d -s main`(env を継承するので壊れていない)。**同じ製品が2通りに作り、片方だけが壊れている**のが気づかれなかった理由 | `scripts/entrypoint-claude.sh:774`, `claude-dev:1464`-`:1465` |
| 9 | `container=docker` の出どころ | イメージの `ENV container=docker`。`D0-env-06` が「起動経路によらず常に付いている」ことを条件として `-e` を却下した経緯どおりだが、`su -l` はイメージ由来の `ENV` も落とす | `.devcontainer/Dockerfile.claude:287`, `docs/00-requests/decisions/env.md:162`-`:171` |
| 10 | 03 の記述が事実と違う箇所(1) | 「`-e` なら対話・非対話シェルと `docker exec` の全てで有効」— tmux 窓の中では有効でないので**偽**である | `docs/03-impl/relations/MODULE-cli-start.md:413` |
| 11 | 03 の記述が事実と違う箇所(2) | 手順7「`COMPOSE_PROJECT_NAME` はここでは設定しない: rc への追記は非対話シェル(`bash -c`)に効かない」— 前半の理由は真だが、`-e` で足りるという結論が #10 に依存している | `docs/03-impl/relations/MODULE-entrypoint-claude.md:49` |
| 12 | 03 の記述が事実と違う箇所(3) | `SSH_AUTH_SOCK` 行の「entrypoint が両 rc へ `export` を追記して**全シェルで有効にする**」— rc は非対話シェルに効かないので偽。実際に届いているのは #6 の別機構による | `docs/03-impl/contracts/cli-container.md:40` |
| 13 | 破っている上流の条項 | `FR-env-07` の内容「コンテナ内から Docker を使える」、`FR-env-07-5`「複数プロジェクトのコンテナで同時に `docker compose` を実行したときネットワーク名・コンテナ名を衝突させてはならない」。全プロジェクトが `/workspace` にマウントされるため、`COMPOSE_PROJECT_NAME` が無い tmux 窓では compose 既定名が `workspace` に落ちて**プロジェクト間で確実に衝突する** | `docs/01-requirements/functional.md:201`-`:225` |
| 14 | 同層の前例 | `FR-env-12-2`「コマンドは対話シェル・非対話シェル・`docker exec` のいずれからも解決できなければならない」— 起動文脈を 01 で列挙する前例。ただし tmux が抜けている | `docs/01-requirements/functional.md:314` |
| 15 | 自動テストの扱い | `SR-32` / `DSN-test-01` により Bash 実装に自動テストランナーを設けない。`MOD-entrypoint` の受入基準は全件が E2E-01 実機確認手順で、`relations-query.py --impact` の「テストが無い」は既決の方針どおり | `docs/03-impl/tests/entrypoint.md`(全文) |
| 16 | `relations-query.py --impact scripts/entrypoint-claude.sh` | 直接: `MODULE-entrypoint-claude` / 波及: `MODULE-cli-start`(距離1) / 要件11件(FR-env-01〜08, 11, 12, 14) / 契約2件(CTR-cli-container, CTR-entrypoint-firewall) / テスト0件。**影響の集合は閉じている** | 2026-08-19 実行 |
| 17 | 差し戻しの5点(`rollback_defined` の根拠) | (a) 不可逆な点: 無い(環境変数の受け渡し経路だけを変え、破壊も移行も外部副作用も起こさない) (b) 差し戻す条件と窓: 修正後の `claude-dev start` で既存の対話シェルの動作が壊れた場合、次の `start` まで (c) 手順: `scripts/entrypoint-claude.sh` の該当行を戻して `claude-dev start`(コンテナ再作成) (d) 復元元: git(本リポジトリ) (e) 検証コマンド: コンテナ内の新規 tmux 窓で `env \| grep -E 'DOCKER_HOST\|COMPOSE_PROJECT_NAME\|^container='` と `docker ps`。**フェーズ2 はこの5点を変更指示に書くこと**(書けなければ lane を critical へ昇格させる) | 本タスクの判断 |
| 18 | 仕様ドキュメントの一括検査(母集団の凍結) | 125 ファイル。CS8 OK / CS11 違反5件 / CS12 OK / CS18 OK / CS19 OK / CS20 違反8件。変更相対語の候補7件(違反ではない) | `python3 .claude/scripts/check-changeset.py --ssot docs`(2026-08-19 実行) |
| 19 | CS11 違反5件の内訳 | `02-design/architecture.md:192`(`docs/issues/092`)/ `02-design/contracts/cli-container.md:141`(`docs/issues/002`)/ `03-impl/index.md:28`(同)/ `03-impl/relations/MODULE-cli-common-write-project-ssh-keys.md:86`(同)/ `03-impl/relations/MODULE-cli-ssh-keys-reset.md:30`(同)。**5件とも本タスクの変更指示では直らない** — closure に入っている2件も、参照が在るのは置き換える節の外だからである(`02-design/contracts/cli-container.md:141` は「プロジェクト設定ファイルとプロジェクト環境ファイル」節で、置き換えるのは「渡す環境変数」節。`03-impl/index.md` には変更指示が無く §3-4 の版のみ更新である)。5件は `docs/pendings.md` の残務が持つ(2026-08-19 の `/doc-check` が記録した) | 同上 |
| 20 | バックログのゲート | 未クローズ issue 12 / 上限 30、残務 36 行 / 上限 50。合格 | `python3 .claude/scripts/check-backlog.py`(2026-08-19 実行) |
| 21 | closure が乗る条項の充足(`/task-new` §2★) | `docs/02-design/system.md:277` は `FR-env-07-1` を `完全`(主担当 `MOD-cli-start`)、`:281` は `FR-env-07-5` を **`部分(P-005)`** とする。`P-005` の解消条件は「同時に扱うプロジェクト数が数百規模になったとき、または衝突が実際に観測されたとき」で、**どちらも発火していない**(観測された衝突は無く、規模は数十のオーダー)。**本タスクはこの未充足部分(ハッシュ短縮値6桁の衝突)には乗っていない** — 今回の欠陥は変数が丸ごと欠落することであって、値の衝突ではないからである。したがって充足の範囲を人間に問う必要は無い | `docs/02-design/system.md:277`, `:281` / `docs/pendings.md` P-005 |
| 22 | `FR-env-07-1` の主担当が実態と合っていない | 充足表は主担当を `MOD-cli-start`(ホスト CLI 側)とするが、今回壊れているのは `MOD-entrypoint`(コンテナ内の初期化)側である。**新しく足す条項の主担当は `MOD-entrypoint` にする** | `docs/02-design/system.md:277` |
| 23 | 実機確認手順に該当手順が無いこと | `E2E-01` の 23 手順のうち、tmux の窓の中で環境変数が見えるかを踏む手順は1つも無い(`tmux` を含むのは手順2 と手順5 だけで、どちらもアタッチできることの確認)。**検証の担い手が無かったことが、この欠陥が残った理由である** | `docs/03-impl/tests/e2e.md:58`, `:63` |
| 24 | パス2: 直す1行 | `su "$USERNAME" -s /bin/zsh -l -c "cd /workspace && tmux -f ~/.tmux.conf new-session -d -s main 'exec zsh -l'"` | `scripts/entrypoint-claude.sh:774`-`:776` |
| 25 | パス2: 同じファイルにある前例 | `su "$USERNAME" -c "DOCKER_HOST='${DOCKER_HOST}' setsid /usr/local/bin/dood-portsync.sh --loop …"` — **`su` に渡すコマンドの中で1つだけ引き継いでいる**。今回はこれを予約名の集合へ広げる形になる | `scripts/entrypoint-claude.sh:513` |
| 26 | パス2: `set -e` | スクリプト冒頭で `set -e` を掛けている。列挙が非ゼロを返すと初期化がそこで止まる(`docs/issues/106` と同型) | `scripts/entrypoint-claude.sh:11` |
| 27 | パス2: rc へ書き出す2箇所 | `SSH_AUTH_SOCK` は `:105`-`:116`、`DOCKER_HOST` は `:118`-`:131`。**どちらも entrypoint 自身の環境には `export` していない** | `scripts/entrypoint-claude.sh:105`, `:118` |
| 28 | パス2: VM モードの上書き | `:484` が `/etc/claude-dev/vm.env` を書き、`:485`-`:493` が両 rc へ source フックを足す。**自身の環境は上書きしていない** | `scripts/entrypoint-claude.sh:484` |
| 29 | パス2: `tmux.conf` | キット同梱の `scripts/tmux.conf` に `update-environment` の設定は無い(既定の8個のまま) | `scripts/tmux.conf`(全文) |
| 30 | パス2: コード注釈にも同じ誤りがある | `claude-dev:1599`-`:1601` の注釈が「`-e` で渡し、対話・非対話を問わず全シェル(Claude Code の `bash -c` 実行含む)と `docker exec` で有効にする」と書いている。**注釈は SSOT ではないが、実装時に同じ降下で直す** | `claude-dev:1599` |

## 質問キュー(未提示)

| # | 論点 | 何が止まるか | 推奨する回答(暫定) |
|---|---|---|---|
| - | なし | - | - |

## タスクリスト

<!-- フェーズ3(`/implement`)が確定させる下書き。1タスク = 1コミット -->

<!-- 2026-08-19 の `/doc-check`(再実行)が案 B へ書き直した。旧版は案 A(予約名を列挙して
     載せ直す)のままで、人間の裁定「2.B」と変更指示・実コードのいずれとも食い違っていた。
     コードは既に案 B で書き換わっている(作業ツリー・未コミット)ので、フェーズ3 は
     この4件を「実装済みかどうか」の確認として流し、DoD を取り直す。 -->

- [ ] 1. `scripts/entrypoint-claude.sh` の手順5(`SSH_AUTH_SOCK` 節)と手順15(VM モード)で、rc へ書き出す値を **entrypoint 自身の環境にも `export`** する(手順6 の `DOCKER_HOST` は `docker run -e` で既に entrypoint の環境に在るので不要) _要件:_ FR-env-07-13 / FR-env-14-11 _Boundary:_ `scripts/entrypoint-claude.sh` _Depends:_ -
- [ ] 2. `scripts/entrypoint-claude.sh` の tmux 起動(`:791`)の `su` から **`-l` を外す**(案 B。列挙して載せ直す形は採らない — コンテナに渡っている変数がそのまま全部引き継がれ、利用者の env ファイルの組も届く) _要件:_ FR-env-07-13 / FR-env-14-11 _Boundary:_ 同上 _Depends:_ 1
- [ ] 3. `claude-dev:1596`-`:1604` / `claude-dev-mac:1672`-`:1680` の**事実と違うコード注釈**を直す(「`-e` なら全シェルで有効」は偽) _要件:_ FR-env-07-13 _Boundary:_ `claude-dev` / `claude-dev-mac` _Depends:_ - (P)
- [ ] 4. `scripts/entrypoint-claude.sh:122` と `:139` の注釈も同じ降下で直す(`:122` は「`docker run -e` で渡された `DOCKER_HOST` は `su -l` でリセットされるため」、`:139` は「`DOCKER_HOST` と同様に全シェル・`docker exec` で有効」。どちらも `-l` を外した後は偽) _要件:_ FR-env-07-13 _Boundary:_ `scripts/entrypoint-claude.sh` _Depends:_ 2
- [ ] 5. E2E-01 手順9 を実機で流す(`docs/03-impl/tests/e2e.md` の変更指示が定める **7項目**。9-6 の env ファイルの組と 9-7 の予約名の非差し替えを含む) _要件:_ FR-env-07-13 / FR-env-14-11 _Depends:_ 2

## Definition of Done

<!-- 2026-08-19 フェーズ3 C-4 で1件ずつ実際に実行して確認した。
     `git rev-parse HEAD` = c3ae87f2c1a58ff119e54be042a87053d22ad4bd(**作業ツリーは未コミット** —
     人間の指示が無いのでコミットしていない。ブランチは main)。 -->

| # | 項目 | コマンド | 結果(最終行の逐語) |
|---|---|---|---|
| 1 | lint | `go vet ./...`(`docker-proxy/` で) | 出力なし・終了コード 0 |
| 2 | 単体・結合テスト | `cd docker-proxy && go test ./...` | `ok  	github.com/quvox/claude-dev-env/docker-proxy	(cached)` |
| 3 | シェルの構文検査 | `bash -n scripts/entrypoint-claude.sh` / `claude-dev` / `claude-dev-mac` | 3本とも出力なし・終了コード 0 |
| 4 | 受入基準のテストが全て存在し通る | — | **適用外**。`SR-32` / `DSN-test-01` により Bash 実装に自動テストランナーを設けない。`FR-env-07-13` の確認は E2E-01 手順9(下記5)が担う |
| 5 | 影響する E2E | **E2E-01 手順9(拡張版7項目)を実機で実行**(使い捨てディレクトリ `cdx-e2e-b`。`env_file:` 指定あり) | **7項目すべて合格**。9-1/9-3 新規窓に `DOCKER_HOST` / `COMPOSE_PROJECT_NAME=cdx-e2e-b-0ab4e3` / `container` / `NODE_OPTIONS` / `CLAUDE_DEV_VNC` / **`TZ=Asia/Tokyo`** / **`LC_ALL=en_US.UTF-8`**。9-2 `zsh -c`・`bash -c` とも値を返す。9-4 `docker ps` が一覧を返す。9-5 compose 名が **`cdx-e2e-b-0ab4e3-e2e-1`**。**9-6 `E2E_PLAIN=ok` / `E2E_QUOTED=it''s fine`(= `AC-08` が満たされた)**。9-7 env ファイルの `DOCKER_HOST=hijacked` は採用されず窓の中は中継先のまま。**回帰確認**: tmux サーバの `PATH` と `HOME` は `-l` があったときと同一 |
| 6 | 探索的ブラウザQA(`/browser-qa`) | — | **適用外(UI 無し — `docs/02-design/system.md:445` `DSN-ui-01`「UI はホスト CLI に限り、Web GUI を持たない」)** |
| 7 | コールグラフ再生成 + `callgraph-check.py --to-be` の重大度「高」ゼロ | `build-callgraphs.py --out $CG_OUT` → `callgraph-check.py --to-be task-fix-tmux-server-drops-reserved-env` | `### 指摘 24 件` / **重大度「高」 0 件**(中0 / 低9 / 参考15。いずれも本タスクと独立の既存状態) |
| 8 | `check-relations.py` | `python3 .claude/scripts/check-relations.py` | `合格: 対称性・参照実在・impl パス・必須項目・機能表との 1:1すべて問題なし。` |
| 9 | 変更指示の機械検査 | `check-changeset.py <new-features>` | `合格: 不変条件の違反なし(ただし未検査: CS5, CS6, CS7, CS9, CS10, CS21 — **未検査は合格ではない**)` |
| 10 | `new-features/` の全変更指示を SSOT へ反映済み | — | **`/task-close` で実施** |
| 11 | `/doc-check` が影響範囲を PASS | — | フェーズ2 で **PASS** 済み。反映後に `/task-close` §6 が再実施 |
| 12 | `docs/histories/` に記録 | — | **`/task-close` で実施** |
| 13 | 範囲外の問題を記録済み | — | **この行はフェーズ3 で取り直す(下の進捗メモ)。** `docs/issues/107` は 2026-08-19 の人間の裁定で**本タスクへ畳み込み済み**であり、範囲外ではない — `/task-close` が閉じる。範囲外として残るのは `docs/issues/108`(CLI が作り直す tmux セッションに entrypoint の実行時の値が届かない。severity 中 / origin_layer 02)と `docs/pendings.md` 残務の各行である |

## 進捗メモ

- 2026-08-19 `docs/issues/108`(ホスト CLI が作り直す tmux セッションが entrypoint の実行時の値を引き継がない。severity 中 / origin_layer 02)は**本タスクへ畳み込まない**と判断した。理由: `AC-03` も `AC-08` もこの経路では落ちず(コンテナ設定の env はそのまま届くので予約名も env ファイルの組も窓の中で見える)、壊れるのは entrypoint が実行時に決めた2値だけで、コンテナを作り直せば揃う。**畳み込まなくても失うものが無い**(issue はディスクに残り `/task-new 108-…` で起こせる)一方、畳み込むと 02 の再降下でもう一度フェーズ1 へ戻ることになる。107 を畳み込んだのは `AC-08` が実機で落ちていたためで、事情が違う。
- 2026-08-19 フェーズ3 完了 → `phase:` を 反映 へ。`close-task.py --check` の残り NG はすべてフェーズ4 の項目((a) SSOT 未反映 /(c) DoD の残項目 /(e) 反映後の再同期 /(g) 履歴の知見の行 /(h) closure に載る残務の裁定)。
- 2026-08-19 フェーズ3(案 B)完了: `/doc-check`(2回目)**判定 PASS / ブロッキング残存0**(独立レビューは Codex `gpt-5.6-sol` effort high。高4件のうち3件を確認済みで修正、1件は誤検知)。その指摘のうち**私の取り残し**だった `scripts/entrypoint-claude.sh` のコード注釈3箇所(「`su -l` でリセットされるため」「全シェル・`docker exec` で有効」)を事実へ直した。**E2E-01 手順9 を拡張版7項目で実機実行し全項目合格** — 9-6(env ファイルの組 `E2E_PLAIN=ok` / `E2E_QUOTED=it's fine` が tmux の窓で見える = `AC-08` が満たされた)と 9-7(env ファイルに `DOCKER_HOST=hijacked` を書いても採用されず窓の中は中継先のまま)を含む。副産物として `TZ=Asia/Tokyo` と `LC_ALL=en_US.UTF-8` も引き継がれることを確認(走査で挙げた3群がすべて解決)。**回帰なし** — tmux サーバの `PATH` と `HOME` は `-l` があったときと完全に同一。`go vet` / `go test` / `bash -n`×3 / コールグラフ再生成 + `callgraph-check.py --to-be` 重大度「高」0 すべて通過。
- 2026-08-19 `/doc-check` 時点の残作業(`python3 .claude/scripts/close-task.py task-fix-tmux-server-drops-reserved-env --check` の逐語): 「→ 削除を拒否した(不合格 19 件)。」「(a) 未反映 → /task-close の反映ステップを完了させること」「(c) 未達   → DoD の残項目を実際に実行すること(チェックだけ付けるのは完了の偽装)」「(e) 未同期 → build-callgraphs.py で再生成し、callgraph-check.py の重大度「高」を解消すること(CLAUDE.md §4 の完了条件)」「(g) 知見なし → 履歴の副産物の表に「知見」の行を足すこと」。(h) の残務8件も裁定待ちである。**いずれもフェーズ3・4 が閉じるもので、フェーズ2 の抜ける条件ではない。**
- 2026-08-19 `/doc-check`(task / lane: standard / 反復 1周目で停止。2周目は不要)**判定: PASS**。独立レビュー: **あり(Codex `gpt-5.6-sol` / effort high)** — 指摘15件。**高4件を個別裁定**(L-01 issue 107 の記述が案 B に追随していない=確認済み・修正 / L-02 `MODULE-cli-start` 判断3 が手順20 を `su -l` と書いている=確認済み・修正(ブロッキング) / L-03 CLI が作り直す tmux セッションに entrypoint の実行時の値が届かない=確認済み・`docs/issues/108` を起票 / L-04 `[DS-01]` の見直す条件が発火している=**誤検知**(見直す条件が指すのは「破壊的操作の検証を含むこと」であって後片付けの `stop` ではない。手順7 と手順8-23 の後片付けも同じ `stop` を使うので、レンズの読み方だとこの条件はどの手順でも常に発火して空語になる。誤解を招く語だったので条件文を限定した))。中/低11件は修正または原則8 のゲートで記録した。**ブロッキング残存 0 件。**
- 2026-08-19 `/doc-check` が直した項目と版の区分: **MINOR** = (a) `MODULE-cli-start` 判断3 の本文 — 「`su -l` で環境を作り直す経路(手順20 の tmux サーバ起動)を越えられない」は**案 B 適用後のコードと合成ビュー自身の手順20 に対して偽**(`scripts/entrypoint-claude.sh:791` に `-l` は無い)。届く範囲の事実と、手順20 が `-l` 無しで引き継ぐ事実へ書き替えた。(b) `tests/e2e.md` の E2E-01 ⇄ テスト対応表の要約を手順9 の題(「コンテナへ渡した環境変数」)へ揃えた — 旧文は `FR-env-14-11` と `AC-08` を含んでおらず、同じ手順9 が確認する範囲を取りこぼしていた。**PATCH** = `MODULE-entrypoint-claude` の `requirements` に `FR-env-14` を追加(02 のカバレッジ表が `FR-env-14-11` の主担当を `MOD-entrypoint` とした上流に追随)/ `02-design/system.md` の `FR-env-07-13` 行と reason の「環境を作り直す経路」を「プロセスの木を起こす」へ(案 B 後の事実)/ 同「機能要件の全 164 条項」→ **166**(本タスクが2条項を足すため)/ `02-design/contracts/cli-container.md` reason の「変更点は1つ」→「1箇所」(本文は3点を数えている)/ `tests/e2e.md` の「手順23」→「**手順8-23**」(トップレベルの手順は1〜9 しか無く、参照先は手順8 の部分手順)/ 同 手順9-7 に `claude-dev stop <name>` を明記(稼働中コンテナへ再接続する経路では env ファイルを読み直さないので、書いたままでは観測できない)/ 同 `[DS-01]` の見直す条件を「破壊的操作の**検証**を含むようになったとき」へ限定 / **コード引用の行番号17箇所**(下記)。
- 2026-08-19 `/doc-check` 検査 B(コード引用の取り直し。原則2): **本タスクの実装が入ったことで、HEAD では正しかった引用17箇所が腐った**(`scripts/entrypoint-claude.sh` は +4/+8/+16 行、`claude-dev` / `claude-dev-mac` は当該箇所以降が +3 行)。`git show HEAD` と作業ツリーを1件ずつ突き合わせて確認したうえで取り直した — `03-impl/contracts/cli-container.md`: `claude-dev:1612`→`:1615`(2箇所)/ `entrypoint:476`→`:480`(2箇所)/ `:556,:613,:678`→`:564,:621,:686` / `:509`〜`:515`→`:517`〜`:523` / `:449`→`:453` / `:471`→`:475`。`MODULE-cli-start.md`: `claude-dev:1685`→`:1688`(2箇所)/ `:1688`→`:1691` / `claude-dev-mac:1736`→`:1739` / `:1739`→`:1742` / `entrypoint:243`〜`:406`→`:247`〜`:410`。**HEAD の時点で既に腐っていた引用(`claude-dev:1501`〜`:1529` / `:1573`〜`:1599` / `:1741` / `:1751` / `:1810` / `:2079` / `:2084` / `claude-dev-mac:1750` / `:1760` / `:2103` / `:2108` / `.devcontainer/Dockerfile.claude:307`)には触れていない** — 本タスクが作ったずれではなく、`docs/pendings.md` 残務の 2026-08-12 の行(「コード引用の行番号のずれ」。`contracts/cli-container.md` 87 トークンと明記)が同じキーで既に持っているので1行も足していない。この残務は closure に載るので `/task-close` が裁定する(`close-task.py --check` の (h))。
- 2026-08-19 `/doc-check` が原則8 のゲートで記録したもの: **issue 1件** = `docs/issues/108`(稼働中コンテナで tmux セッションが失われたときに**ホスト CLI が `docker exec ... tmux new-session` で作り直す経路**(`claude-dev:1465` / `claude-dev-mac:1542`)は、entrypoint が実行時に `export` した VM の `DOCKER_HOST` と macOS の `SSH_AUTH_SOCK` を引き継がない。`CTR-cli-container` の到達の義務が受け側を「entrypoint」と名指しているため経路2 を覆えていない。severity 中 / origin_layer 02 / 独立レビュー L-03)。**残務2行**(41 → 43 行 / 上限 50) = `02-design/system.md`「モジュール分割定義」と `02-design/contracts/cli-container.md`「対応要件」が `FR-env-14` を欠く(02 側の2節は変更指示に無く、足すには 10,782 バイトの節をまるごと置き換えることになるため見送った。03 側は揃えた)/ `02-design/system.md`「要件カバレッジ確認」の SR 行19件が充足欄に `-` を書いている。**既に同じキーが在るもの(NFR 行の主担当が複数 / E2E-01 手順7-3 の「すぐに」/ コード引用の行番号のずれ)は1行も足していない。**
- 2026-08-19 `/doc-check` が `docs/issues/107` を現状へ揃えた: `closes_when` を「E2E-01 手順**23-1**」から「**手順9-6**」へ(変更指示が作る確認の担い手はそちら)。「原因の見当」末尾の「予約名だけを載せ直す修正を入れた/組は対象外である」と、「対処案」B の「`-l` を外すと `PATH`/`HOME`/作業ディレクトリまで変わる。その理由は今も真であり `[DS-05]` は継続」を、**実測で誤りだった事実**(`PATH` も `HOME` も同一。`[DS-05]` は更新)へ差し替え、「どの案を採るかは決めない」を人間の裁定(案 B・畳み込み)へ差し替えて、経緯に1行足した。**閉じるのは `/task-close`。**
- 2026-08-19 `/doc-check` 検査 F のバイトゲートの裁定(前回と同じ結論を再測定): **`new-features/03-impl/relations/*.md` の 4,000 バイト上限は本タスクには適用しない** — 2本とも**実装済みモジュールの全文 `replace`**(`change-set.md` §1 例外2。`sections:` を持たない)であり、**何も変えない `replace` の下限は `MODULE-cli-start.md` = 57,908 バイト / `MODULE-entrypoint-claude.md` = 19,538 バイト**でどちらも 4,000 を超える。下限が上限を超える以上、このゲートは対象を取り違えている。現在値は 59,929 / 26,589 バイト。`tests/strategy.md` は変更指示に無い。
- 2026-08-19 `/doc-check` 変更指示の総バイト: 224,899 → **225,220(+321)**。内訳は上の MINOR 2件と PATCH のうち説明を足した3箇所(`requirements` の追加・手順9-7 の停止手順・`[DS-01]` の条件の限定)で、**行番号17箇所の取り直しは桁数が同じなので 0 バイト**である。修飾語の追記はしていない。
- 2026-08-19 `/doc-check` 変更指示のハッシュ(sha256 先頭12桁): `01-requirements/functional.md`=431e1fd53107 / `02-design/contracts/cli-container.md`=e30f23e25b0f / `02-design/system.md`=b6aacd9c9f55 / `03-impl/contracts/cli-container.md`=76be9f0caeb8 / `03-impl/relations/MODULE-cli-start.md`=0714574c0393 / `03-impl/relations/MODULE-entrypoint-claude.md`=ad7fb49c142f / `03-impl/tests/e2e.md`=021dc3ea4768 / `03-impl/tests/entrypoint.md`=5c16f59565be。closure の版: `01-requirements/functional.md`@1.19.1 / `02-design/contracts/cli-container.md`@1.13.0 / `02-design/system.md`@2.15.0 / `03-impl/contracts/cli-container.md`@1.10.0 / `03-impl/tests/entrypoint.md`@1.2.1 / `03-impl/tests/e2e.md`@1.11.0 / `03-impl/index.md`@1.29.1(7文書とも `verified.version` が自身の MAJOR.MINOR と一致し、合格証は有効)。**この PASS は PATCH 級の編集では失効せず、変更指示への MINOR 以上の編集か、closure の SSOT が動いたときにだけ失効する。**
- 2026-08-19 `/doc-check` 機械検査: `build-callgraphs.py --check` は最初 **index.md が古い**(shell の LOC 2690→2687。案 B で載せ直しブロックを削ったぶん)ので `--out <new-features>/03-impl/callgraphs` へ**再生成した**(シンボル 178 / 辺 273 は不変)。以後 `--check` は最新。`cluster-features.py --check` 最新 / `callgraph-check.py --to-be` 指摘24件・**重大度「高」0件**(低9・参考15。いずれも本タスクと独立の既存状態)/ `check-contracts.py` 合格 / `check-relations.py` 合格 / `check-changeset.py` 合格(未検査 CS5・CS6・CS7・CS9・CS10・CS21)/ `compose-changeset.py --diff` 合格 / `check-sheet.py` 合格 / `check-lane.py` 合格(standard)。`relations-query.py --health`: テストが無い機能60件(`SR-32`/`DSN-test-01` の既決方針)・呼び出し先が多い機能2件・循環0。
- 2026-08-19 `/doc-check` 鮮度(A2): closure が開く棚上げは **P-005** の1件。解消条件「同時に扱うプロジェクト数が数百規模になったとき、または衝突が実際に観測されたとき」のうち、**衝突の観測は未発火**(文書・コードのどこにも記録が無い)、**規模は判定不能**(実際の同時プロジェクト数は手元の文書から独立に確かめられない)。新しい issue も残務も作っていない(`issues-pendings.md` §8)。
- 2026-08-19 `/doc-check` 実装ドライラン(D14/D15)の再実行: 未決点は**新たに0件**。案 B は列挙をやめたので前回記録した「集合が空だと構文で壊れる」懸念そのものが消えている。`su` に `-l` が残っている箇所はコード全体で0(`scripts/entrypoint-claude.sh:98`・`:486`・`:521`・`:777`・`:791` のいずれも `-l` 無し)。`-l` を外した副産物として `TZ` / `LC_ALL` / `CONTAINER_USER` / `USER_HOME` / `DEBIAN_FRONTEND` / `HOSTNAME` ほかも窓へ届くが、**`docs/issues/107` の `pattern_survey` が「利用者から見える影響があるのは3群」と既に走査済み**で、`[DS-05]` の見直す条件(tmux の窓へ渡してはならない変数が現れたとき)が受け皿になっている。
- 2026-08-19 フェーズ2(再実行)完了 + 実装を案 B へ差し替え: 変更指示8本を書き直した(01 は `FR-env-07` と `FR-env-14` の2節 / 02 契約の到達の義務を「渡した環境変数の全体」へ / 02 カバレッジ表に `FR-env-14-11` / 03 契約の tmux 行を「`-l` を付けない」へ / `MODULE-entrypoint-claude` 手順20 を全面差し替えと `[DS-05]` の**更新**・`[DS-02]` の**削除** / `tests/entrypoint.md` に `FR-env-14-11` / `tests/e2e.md` の手順9 に 9-6・9-7)。`check-changeset.py` 合格・`compose-changeset.py --diff` 合格(214行差分)。コードも `scripts/entrypoint-claude.sh` の tmux 起動から `-l` を外し、載せ直しブロックを丸ごと削除した(手順5・手順15 の自身の環境への `export` は macOS 経路と VM モードのために残す)。**タスクリストと DoD はフェーズ3 でやり直す。**
- 2026-08-19 **範囲を広げてフェーズ1へ戻し、フェーズ2 を再実行する**。人間の裁定「1.b。2.B。3.タスクが終わってからcommit」により、`docs/issues/107`(env ファイルの組が tmux の窓に届かず `AC-08` が実機で不合格)を本タスクへ畳み込み、直し方は**案 B(tmux を起こす `su` から `-l` を外す)**に決まった。sheet.md に論点2 を追記して回答を転記済み。**closure はファイルが1つも増えない**(`FR-env-14` は `FR-env-07` と同じ `functional.md`、他はすべて既に触っているファイル)。`check-sheet.py` / `check-lane.py` ともに合格(lane は standard のまま)。
- 2026-08-19 **`[DS-05]` の理由が実測で誤りだと判明した**(原則2 の事実の食い違い。コードを正とする)。「`-l` を外すと `PATH` / `HOME` / 作業ディレクトリまで同時に変わる」と書いていたが、実機で `su dev -s /bin/zsh -l -c` と `su dev -s /bin/zsh -c` を並べて測ると **`PATH` も `HOME` も完全に同一**で、違うのは `PWD` だけ(`/home/<user>` → `/workspace`。コマンドが `cd /workspace` するので影響しない)。`-l` 無しでは `DOCKER_HOST` と `TZ` が引き継がれる。**この判断は 継続 ではなく 更新 である**(`.claude/directions/delegation.md` §3.1)。
- 2026-08-19 フェーズ3 C-3 追記: 人間の問い「`.claude-dev.yaml` の env ファイル機能と今回の修正は干渉しないか」を受けて実機で測定した(使い捨てコンテナ `cdx-e2e-envmix`)。**干渉はしない** — 予約名を env ファイルに書いても `FR-env-14-8` により採用されず(`DOCKER_HOST` / `COMPOSE_PROJECT_NAME` / `CLAUDE_DEV_INJECT` の3件が「採用しませんでした」と表示され、tmux の窓でも `DOCKER_HOST` は中継先のまま)、接頭辞つきの名前を実行時に拾う処理へ**利用者由来の値が混入する経路は無い**。**ただし別の穴が出た**: env ファイルの組(`E2E_PLAIN` ほか)は `docker exec` からは見えるが **tmux の窓の中では1件も見えない**。`AC-08` の操作4 は「立ち上がった端末の中で」表示することを求めており、その端末は tmux なので **`AC-08` は実機に対して不合格**である。同じ根(`su -l`)だが**本タスクが作り込んだものではなく、予約名の外に残っていた分**なので、`docs/issues/107`(severity 高 / origin_layer 01 / found_in 人間の指摘)として起票した。同型の走査も記録済み — 予約名を載せ直した後も `su -l` を越えられない変数は11種類残り、利用者から見える影響があるのは3群(env ファイルの組 / `TZ` / `LC_ALL`)である。
- 2026-08-19 フェーズ3 C-4: DoD 13項目を1件ずつ実行して記録(上表)。`phase:` を 反映 へ。**作業ツリーは未コミット**(コミットは人間の指示があってから。ブランチは `main`)。
- 2026-08-19 フェーズ3 C-1: コールグラフを `new-features/03-impl/callgraphs/` へ再生成(shell 178シンボル/273辺)。`cluster-features.py` で `feature-graph.md` を生成(機能61 / 辺88 / 未到達8)。`callgraph-check.py --to-be` は指摘24件・**重大度「高」ゼロ**。`check-relations.py` 合格。**作ったものへ変更指示を合わせた** — 手順20 の記法を「`&&` で繋ぐ」から**「`tmux` の直前の代入の並び」**へ直し(1件も無いときに空になっても構文が壊れない形。`/doc-check` が「集合が空だと構文で壊れる」と指摘していた懸念そのものが消える)、異常系に2行を足した。
- 2026-08-19 フェーズ3 C-0.5: 探索的ブラウザQA は **適用外(UI 無し)**。根拠は `docs/02-design/system.md:445` の `DSN-ui-01`「UI はホスト CLI に限り、Web GUI を持たない」。画面一覧も `SCR-01 cli-commands` だけである。
- 2026-08-19 フェーズ3 C-0: **E2E-01 手順9 を実機で実行し5項目すべて合格**。イメージ2本(`claude-dev-claude` / `claude-dev-claude-vnc`)を再ビルドし(entrypoint は `Dockerfile.claude:261` で焼き込まれるため)、使い捨てディレクトリ `cdx-e2e-tmuxenv` で `CLAUDE_DEV_NO_ATTACH=1 claude-dev start` → 検査 → `claude-dev stop cdx-e2e-tmuxenv --yes --volumes` → Chrome プロファイルのボリュームを手で削除(E2E-01 手順7-7 が定める片付けと同じ)→ ディレクトリ削除。**修正前は tmux サーバの environ が12個だったが、修正後は予約環境変数がすべて載っている。**
- 2026-08-19 フェーズ3 C-0 で見つけた範囲外の事象2件を `docs/pendings.md` 残務へ(41行 / 上限50): (a) `.gitignore` が `.DS_Store` を無視していない、(b) **`claude-dev stop --yes --volumes` のようにフラグを名前より前に書くと `--yes` が `<name>` と解釈され、セッションが止まらないまま終了コード 0 になる**(`--yes` は `[A-Za-z0-9._-]` の範囲内なので `FR-env-01-18` は発火せず、`FR-env-01-8` の経路に入る = **仕様には違反していない**)。
- 2026-08-19 フェーズ3 B: 実装3タスク完了。(1) `scripts/entrypoint-claude.sh` の `SSH_AUTH_SOCK`(手順5)と VM モードの `DOCKER_HOST`(手順15)を **entrypoint 自身の環境にも `export`**、(2) tmux 起動で**予約環境変数を代入の並びとして載せ直す**(接頭辞つきは `compgen -v | grep '^CLAUDE_DEV_' || true` で実行時に拾う。値を持つものだけ。`'` は `'\''` へ退避)、(3) `claude-dev:1598` と `claude-dev-mac:1675` の**事実と違うコード注釈**(「`-e` なら対話・非対話を問わず全シェルで有効」)を訂正。引用の正しさは使い捨てスクリプトで単体確認済み(`'` / `$` / バッククォート / 二重引用符 / 空白を含む値が逐語で通ることと、集合が空でも壊れないこと)。
- 2026-08-19 フェーズ3 開始: 入場ゲート3条件を確認して合格 — (1) closure の SSOT 7文書すべて `verified.version` が自身の MAJOR.MINOR と一致、進捗メモに `/doc-check(task) 判定: PASS` あり、(2) 未決点は5件とも帰着済みで**未帰着0件・人間判断0件**、(3) `02-design/environments.md` の lint(`go vet ./...`)と単体テスト(`cd docker-proxy && go test ./...`)が「未定」でない。
- 2026-08-19 `/doc-check`(task / lane: standard / 反復 1・2周目は不要)**判定: PASS**。独立レビュー: **あり(Codex `gpt-5.6-sol` / effort high)** — 指摘11件を裁定(確認済み5 / 誤検知3 / 既存の残務へ差し戻し3)。ブロッキング1件を直して解消:**`new-features/03-impl/tests/e2e.md` の本文で `### E2E-01` を置換対象の `## E2Eシナリオ ⇄ テスト対応表` の直下に書いていたため合成ビューが一意に決まらず、`compose-changeset.py --diff` が「親本文経由の新規子見出しは禁止」で落ちていた**(`change-set.md` §2 が測定済みの失敗として名指す形そのもの)。`### E2E-01` を本文の先頭(根の直下)へ移し、`sections:` の並びも合わせた(合成の結果は変わらない。移動前後で 34,309 バイトのまま)。
- 2026-08-19 `/doc-check` が直した項目と版の区分: **MINOR** = `tests/e2e.md` 手順9-1 の観測対象を予約集合の全体(接頭辞 `CLAUDE_DEV_` と `SSH_AUTH_SOCK`)へ広げた(独立レビュー L-03。固定名4件しか見ておらず新設条項 `FR-env-07-13` の守備範囲を覆っていなかった)。**PATCH** = `tests/e2e.md` の節の並べ替え / `03-impl/contracts/cli-container.md` の `SSH_AUTH_SOCK` 行のコード引用を実コードへ取り直し(`claude-dev:1426`〜`:1429` → **`claude-dev:1612`**。原則2)/ `MODULE-entrypoint-claude` 手順20 の3点(「手順6 も自身の環境へ `export` している」は偽 — `DOCKER_HOST` は `-e` で既に在る / 「ここが唯一の到達点」の守備範囲を tmux 経路に限定 / 「引用する」を「単引用符を含む値でも壊れない形で引用する」へ)/ `tests/entrypoint.md` の `FR-env-07-13` 行を条項 ID の昇順へ戻した / memo.md の事実誤り1件(下記)。
- 2026-08-19 `/doc-check` 検査 F のバイトゲートの裁定: **`new-features/03-impl/relations/*.md` の 4,000 バイト上限は本タスクには適用しない** — 2本とも**実装済みモジュールの全文 `replace`**(`change-set.md` §1 例外2。`sections:` を持たない形)であり、**何も変えない `replace` の下限は `MODULE-cli-start.md` = 57,908 バイト / `MODULE-entrypoint-claude.md` = 19,538 バイト**でどちらも 4,000 を超える。下限が上限を超える以上、このゲートは対象を取り違えている。現在値は 59,786 / 26,587 バイト。
- 2026-08-19 `/doc-check` 変更指示の総バイト: 214,743 → **215,274**(+531)。増分は上の MINOR 1件(手順9-1 の観測対象の拡張)と「唯一の到達点」の限定の2箇所だけで、いずれも**修飾語の追記ではなく記述の置き換え**である。
- 2026-08-19 `/doc-check` 変更指示のハッシュ(sha256 先頭12桁): `01-requirements/functional.md`=ef66f5ab3258 / `02-design/contracts/cli-container.md`=77289d0b6977 / `02-design/system.md`=6242f78898d2 / `03-impl/contracts/cli-container.md`=70cff1b22940(修正後) / `03-impl/relations/MODULE-cli-start.md`=7b54b427b0d0 / `03-impl/relations/MODULE-entrypoint-claude.md`=151e03c55341(修正後) / `03-impl/tests/e2e.md`=c8e0ff7d3b28(修正後) / `03-impl/tests/entrypoint.md`=09e37ed429d0(修正後)。closure の版: `01-requirements/functional.md`@1.19.1 / `02-design/contracts/cli-container.md`@1.13.0 / `02-design/system.md`@2.15.0 / `03-impl/contracts/cli-container.md`@1.10.0 / `03-impl/tests/entrypoint.md`@1.2.1 / `03-impl/tests/e2e.md`@1.11.0 / `03-impl/index.md`@1.29.1。**この PASS は PATCH 級の編集では失効せず、変更指示への MINOR 以上の編集か、closure の SSOT が動いたときにだけ失効する。**
- 2026-08-19 `/doc-check` が `docs/pendings.md` の残務へ足した3行(36 → 39 行 / 上限 50): 削除済み issue への参照11件 / `UC-01` の関連要件に `FR-env-07` が無い / E2E-01 手順7-3 の「すぐに」。**`docs/03-impl/contracts/cli-container.md`「実装上の事実」のコード引用のずれ(`claude-dev:1501`〜`:1529` は実際には `:1685`〜`:1712`、`.devcontainer/Dockerfile.claude:307` は実際には `:287` ほか)は 2026-08-12 の残務が既に同じキーで持っている**ので1行も足していない(`issues-pendings.md` §2.1)。この残務は closure に載るので **`/task-close` が裁定する**(`close-task.py --check` の (h) が現に要求している)。
- 2026-08-19 `/doc-check` 実装ドライラン(D14/D15)の再実行結果: memo の未決点5件はいずれも(a)上流が答える形でドキュメントに書かれているか(b)標準委任で決まっており、**人間判断へ回すものは0件**。新たに1点だけ確認した — 手順20 の載せ直しの集合が空になると `su -c "cd /workspace && … && tmux …"` が構文で壊れ、行末の `2>/dev/null || true` がそれを握りつぶして **tmux セッションが1つも立たない**。ただし `container=docker` がイメージの `ENV` で常に在る(`.devcontainer/Dockerfile.claude:287`)ため集合が空になることは無く、未決点にはならない。実装時の注意として記録する。
- 2026-08-19 フェーズ2: 01 完了(`FR-env-07` に受入基準13 を新設。内容の1文と分割可否の条項数を追随)。
- 2026-08-19 フェーズ2: 02 完了(契約 `CTR-cli-container` の「渡す環境変数」に到達の義務。`02-design/system.md` のカバレッジ表に主担当 `MOD-entrypoint` の行。「分割の根拠」7件を読み直して継続)。
- 2026-08-19 フェーズ2: 03 完了(実装側契約の `SSH_AUTH_SOCK` 行の誤りを訂正+引き継ぎの行を新設 / `MODULE-entrypoint-claude` 手順5・6・7・15・20 / `MODULE-cli-start` 実装上の判断3 の誤った断定 / `tests/entrypoint.md` に条項行 / `tests/e2e.md` に E2E-01 手順9)。
- 2026-08-19 フェーズ2: 実装ドライラン パス1・パス2 を実施。未決点5件はすべてドキュメント記載か委任決定で帰着し、**人間判断は0件**。`check-changeset.py` 合格(CS5/CS6/CS7/CS9/CS10/CS21 は未検査 = 未設定または対象外)。
- 2026-08-19 行使した標準委任(`.claude/directions/delegation.md` §3): [DS-05] 引き継ぎを `su` に渡すコマンドの中で載せ直す形にする(記録先: `MODULE-entrypoint-claude` 実装上の判断)/ [DS-02] 載せ直しの非ゼロ終了で初期化を止めない(同上)/ [DS-01] 手順8 の部分手順にせず新しい手順9 を末尾に足す(記録先: `tests/e2e.md` テスト設計の判断)。
- 2026-08-19 フェーズ1完了: 人間がチャットで「推奨どおりで」と回答(逐語転記済み)。**論点1 は案 A** — 01 に条項 `FR-env-07-13` を足す。起点層は 01 のまま、closure も変更なし。`check-sheet.py` は SH4 を含め全項目合格。`phase:` を ドキュメント へ進め、`/task-doc` に入る。
- 2026-08-19 フェーズ1: バックログのゲート合格 → 現状調査(frontmatter 一括抽出・`relations-query.py --impact`・`check-changeset.py --ssot`)→ 実機コンテナ `ct_matchsupport` で原因を特定(`su -l` が tmux サーバの環境を落とす。`tmux update-environment` の既定に予約名が無いため `SSH_AUTH_SOCK` と `DISPLAY` だけが偶然届いている)→ closure と lane を確定 → memo.md と sheet.md を作成。次は人間の回答待ち。

## 申し送り事項

- **`docs/issues/002` を指す参照が3件、closure の外に残っている**(`02-design/architecture.md:192` は `docs/issues/092`、`MODULE-cli-common-write-project-ssh-keys.md:86` と `MODULE-cli-ssh-keys-reset.md:30` は `docs/issues/002`)。どちらの issue も既に削除済みで、読者が根拠を辿れない。`/doc-check ssot` の CS11 が毎回報告する。**closure に入っている2件も、参照が在るのは置き換える節の外なので本タスクでは直らない**(`02-design/contracts/cli-container.md:141` は「プロジェクト設定ファイルとプロジェクト環境ファイル」節、`03-impl/index.md` は変更指示なし)。**5件とも `docs/pendings.md` の残務が持つ**ので、次に同ファイルを触るタスクが同じ降下で直す。
- **`docs/pendings.md` 残務の最終行が古くなっている**: 「残る issue 12 件のうち 9 件に `origin_layer` が無く」と書かれているが、`docs/issues/002` が削除されたため `check-changeset.py --ssot` の CS20 は現在 **8 件**を報告する。件数だけのずれで、指摘の中身は依然として真である。
- 稼働中の実機コンテナ `ct_matchsupport` には、本修正が入るまでの応急処置として `tmux set-environment -g` で3変数(`DOCKER_HOST` / `COMPOSE_PROJECT_NAME` / `container`)を入れてある(2026-08-19)。**これは製品の変更ではない**ので closure に入れていない。コンテナを作り直せば消える。
</content>
</invoke>
