---
id: 092-modify-01-says-stop-halts-docker-proxy-while-the-code-deletes-it
type: modify
origin_layer: 00
severity: 中
found: 2026-08-07
found_in: /doc-check ssot task-stop-session-spawned-containers(独立レビュー(サブエージェント)の再監査 検査項目1)
related: FR-env-01, D0-env-08, docs/02-design/contracts/cli-container.md, MODULE-cli-stop, MODULE-cli-logout, MODULE-cli-reset, claude-dev, claude-dev-mac
pattern: same-resource-described-with-different-verbs-across-layers
pattern_survey: "docker-proxy・共有ネットワーク・Claude コンテナ・セッション由来の資源・`fwd-*`・共有ボリューム・イメージの7資源について、00 / 01 / 02 / 03 / コード / 利用者向け出力の6箇所の動詞を突き合わせた。層をまたいで動詞が割れているのは **docker-proxy の1件だけ**(他6資源はすべて「削除」で一致し、Claude コンテナは 2026-08-07 に 01 側を「削除」へ揃えた)"
summary: docker-proxy について 00・01 は「停止」、02・03・実装は「削除」(`docker rm -f`)と書いており、利用者向け出力も「停止しました」なのでコンテナが残らないことが伝わらない
---

# 092 docker-proxy を「停止」と書く層と「削除」する実装

## 事象

同じ資源に3通りの動詞が当たっている。

| 層 | 記述 | 場所 |
|---|---|---|
| 00 | 「共有ネットワークと docker-proxy を**停止**してよい条件」 | `docs/00-requests/decisions/env.md`(`D0-env-05` 項2 / `D0-env-08` 項2) |
| 01 | 「docker-proxy も**停止**しなければならない」 | `docs/01-requirements/functional.md` の `FR-env-01-6` / `FR-env-01-9` |
| 02 | 節見出しが「**削除**してよい条件」 | `docs/02-design/contracts/cli-container.md` |
| 03 | 「`docker rm -f` する」 | `docs/03-impl/relations/MODULE-cli-stop.md` |
| コード | `docker rm -f "$DOCKER_PROXY_CONTAINER"` | `claude-dev:626` |
| 利用者向け出力 | 「🐳 Docker Socket Proxy コンテナを**停止**しました(Claude コンテナなし)」 | `claude-dev:627` |

01 は「停止」と「削除」を意図的に区別している(`FR-env-01-9` は共有ネットワークについてだけ
「削除」を使う)ので、単なる言い回しの揺れとして読み飛ばせない。

## 影響

利用者は「停止した(あとで再開できる)」と読むが、実際にはコンテナごと消えていて
`docker ps -a` にも現れない。**次に必要になったときは作り直される**ので実害は無いが、
`docker ps -a` で確認する利用者には事実と違う説明になる。
また 00 の決定の文言が実装と食い違うため、`D0-env-08` 項2 を根拠に判断する後続の変更が
誤った前提から出発しうる。severity は「中」。

## 原因の見当

docker-proxy は「必要になれば `ensure_docker_proxy_container` が作り直す」ため、
実装者にとって「止める」と「消す」の区別が観測差にならなかったと推測する(推測)。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| docker-proxy を消すのか止めるのか | `docker rm -f`(削除) | 00・01 は「停止」、02 は「削除」 | **要確認** — 実装を `docker stop` に寄せる案と、00・01 の語を「削除」に揃える案のどちらも成り立つ |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | 00・01 の docker-proxy に掛かる語を「削除」へ統一し、`claude-dev:627` / `claude-dev-mac` の出力文言も「削除しました」に直す | 00 2箇所 + 01 2箇所 + コード2箇所 + 03 の対応表。**00 の意味に触れるので人間の裁定が要る** |
| B | 実装を `docker stop` に寄せる | 停止済みコンテナが名前を占有し、`ensure_docker_proxy_container` の作り直しと衝突しうる。`MODULE-cli-start` まで波及する |
| C | 何もしない(受容) | `docs/pendings.md` へ。ただし 00 と実装が食い違ったままになる |

推奨は A(実装の振る舞いは妥当で、語だけが揃っていない)。

## 人間の裁定(2026-08-07)— 案 A で確定。ただし **02 が抜けている**

**回答は A**。人間の指示(「どの層に書くのかを考えよ」)により層を分解したところ、
**上の案 A の「影響範囲の見込み」欄(00 + 01 + コード + 03)には 02 が無い**。
`docker stop` ではなく `docker rm -f` を選んだことは**設計判断**であり、02 に `DSN-*` が無いと
「なぜ削除なのか」がコードにしか存在しない状態が残る(それは本 issue と同じ欠陥の再生産である)。

| # | 何を書くか | 層 | 具体的な置き場 | なぜその層か |
|---|---|---|---|---|
| 1 | 「遊休になったら共有基盤を残さない」という**方針**。**動詞を機構に固定しない** | **00** | `docs/00-requests/decisions/env.md`(`D0-env-05` 項2 / `D0-env-08` 項2) | 00 が決めるのは「残すか残さないか」。`stop` か `rm` かは実現方式で、00 が持つと実装を変えるたびに 00 が古くなる |
| 2 | 「`docker ps -a` にも残らない」という**観測可能な結果** | **01** | `docs/01-requirements/functional.md`(`FR-env-01-6` / `FR-env-01-9`) | 01 は「停止」と「削除」を**意図的に区別している**(`-9` は共有ネットワークについてだけ「削除」を使う)。したがって語の揺れではなく条項の誤りであり、01 で直す |
| 3 | **`docker stop` ではなく `docker rm -f` を選んだ設計判断**(`ensure_docker_proxy_container` が冪等に作り直すので停止である必要がない。停止済みコンテナは名前を占有して作り直しと衝突する) | **02** | `docs/02-design/architecture.md`「設計判断」に `DSN-*` を新設 | **案 A が落としていた層**。選択の理由の置き場 |
| 4 | 利用者向け出力の文言(「停止しました」→「削除しました」)と実装 | **03 + コード** | `claude-dev:627` / `claude-dev-mac` の同一箇所、`MODULE-cli-stop` の対応表 | コードの鏡 |

**コードに触るので本 issue は独立したタスクにする**(`/task-new docs/issues/092`)。
1〜3 だけを先に直すことは**してはならない** — 直した瞬間に 01 と実装が食い違い、
`/doc-check` が新しい「高」を出す。**4 と同じタスクで降ろすこと。**

## 経緯

- 2026-08-07 起票。`/doc-check ssot task-stop-session-spawned-containers` の再監査
  (`lens: subagent`)が検出。**本タスクより前から存在する食い違いで、影響範囲の外**
  (`FR-env-01-6` / `-9` は本タスクが触った条項ではあるが、docker-proxy の動詞は触っていない)。
  **00 への意味のある編集を伴うので AI は決めない**(`.claude/directions/delegation.md` §1)。
  同実行の決定シートに論点として載せた。
