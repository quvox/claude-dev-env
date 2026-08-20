---
id: 109-bug-make-status-treats-a-failed-docker-query-as-zero-sessions
type: bug
severity: 中
origin_layer: 03
found: 2026-08-20
found_in: verify 系フロー(F3 実装整合フローの独立レビュー — lens: claude)
related: CTR-cli-container, MODULE-makefile-status, FR-env-01-35
closes_when: Docker への2回の問い合わせのどちらかが非ゼロで終わったとき、`make status` が「一覧が不完全である可能性」を1行表示する(`claude-dev list` と同じ扱いになる)。確認は `docker` を PATH から外すか応答しない `DOCKER_HOST` を指して `make status` を実行し、「(実行中のセッションはありません)」だけが出ないことを見る
pattern: なし
pattern_survey: なし
summary: make status は docker ps の失敗を 0 件と同一視して「(実行中のセッションはありません)」と表示し、02 の契約が禁じる読み違えを利用者に起こさせる
---

# 109 `make status` が問い合わせの失敗を0件として表示する

## 事象

`docs/02-design/contracts/cli-container.md` の「稼働中セッションの一覧の列挙」節(表題に
`make status` を含む)は**問い合わせが失敗したときは 0 件と同一視しない**ことを定め、表示側が
一覧が不完全である可能性を出すよう求めている。`claude-dev list` はこれを実装している
(`claude-dev:2206`-`:2211` が `_q_failed` を立て、`⚠️  Docker への問い合わせが失敗したため、
この一覧は不完全である可能性があります。` を表示する)。

`make status` は実装していない。`Makefile:256`-`:258` は

```
@ids=$$( { docker ps --filter "label=claude-dev.managed=1" --format '{{.ID}} {{.Names}}'; \
           docker ps --filter "ancestor=$(IMG_CLAUDE)" --filter "ancestor=$(IMG_CLAUDE_VNC)" --format '{{.ID}} {{.Names}}'; } 2>/dev/null \
         | awk 'NF && $$2 !~ /^fwd-/ && !seen[$$1]++ { print $$1 }' );
```

の形で、`ids=` の代入が**パイプ末尾の `awk` の終了状態**を取るため `docker ps` の非ゼロは消える。
結果 `$$ids` が空になり `Makefile:263` の `echo "  (実行中のセッションはありません)"` に落ちる。

## 影響

Docker が応答しない状態で `make status` を実行した利用者は、**稼働中のセッションが無い**と
読む。出力は正常時の0件と1バイトも変わらないので、問い合わせが失敗したことに気づく手段が無い。
`claude-dev list` とは違う答えを同じホストで返すため、`MODULE-makefile-status` が
「`claude-dev list` と同じ集合を表示する」と書いた前提も崩れる。

`FR-env-01-35` / `FR-env-01-36` は `claude-dev list` を名指しており `make status` を含まないので、
受け入れ基準は落ちない。落ちているのは 02 の契約である。

## 対処案

`ids=` を2つの `docker ps` に分け、それぞれの終了コードを見て失敗があれば警告行を出す
(`claude-dev` の `_q_failed` と同じ形)。`Makefile` はレシピの各行が別のシェルなので、
1つのレシピ行の中で `_q_failed` を立てて分岐する形になる。
