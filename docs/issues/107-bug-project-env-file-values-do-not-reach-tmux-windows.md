---
id: 107-bug-project-env-file-values-do-not-reach-tmux-windows
type: bug
severity: 高
origin_layer: 01
found: 2026-08-19
found_in: 人間の指摘
related: AC-08, FR-env-14-1, FR-env-14-2, FR-env-07-13, CTR-cli-container, MODULE-entrypoint-claude, MODULE-cli-start, docs/03-impl/tests/e2e.md
closes_when: env ファイルに書いた組が、`claude-dev start` でアタッチした tmux の窓の中で `printenv <名前>` で見え、E2E-01 手順9-6 が合格する
pattern: env-not-carried-across-su-l
pattern_survey: 実機コンテナのプロセス環境(PID 1 系)と tmux サーバの `/proc/<pid>/environ` を突き合わせて走査(2026-08-19)。`su -l` を越えられない変数は、`task-fix-tmux-server-drops-reserved-env` が予約名(接頭辞 `CLAUDE_DEV_` と固定名5つ)を載せ直した後も **11 種類残る**: プロジェクト環境ファイルの組(本 issue)/ `TZ` / `LC_ALL` / `CONTAINER_USER` / `USER_HOME` / `GTK_IM_MODULE` / `QT_IM_MODULE` / `XMODIFIERS` / `IBUS_ENABLE_SYNC_MODE` / `DEBIAN_FRONTEND` / `HOSTNAME`。このうち**利用者から見える影響があるのは 3 群**(本 issue の組 / `TZ`(tmux の窓の時刻が UTC になる)/ `LC_ALL`(並び順と書式))で、残りは GUI の入力メソッドと内部参照である
summary: env ファイルに書いた環境変数が tmux の窓の中のプロセスから見えず、AC-08 が実機に対して不合格になる
---

# 107 env ファイルの値が tmux の窓の中で見えない

## 事象

`.claude-dev.yaml` の `env_file:` で渡した環境変数が、**`claude-dev start` がアタッチする
tmux の窓の中では参照できない**。`docker exec` 経由では参照できる。

再現手順:

1. 使い捨てディレクトリに `.claude-dev.yaml`(`env_file: .env.local`)と
   `.env.local`(`E2E_PLAIN=ok`)を置く。
2. `CLAUDE_DEV_NO_ATTACH=1 claude-dev start --no-vnc` を実行する。
3. `docker exec -u <user> <name> sh -c 'env | grep E2E_'` を実行する。
   → **`E2E_PLAIN=ok` と `E2E_QUOTED=it's fine` が出る**。
4. `docker exec -u <user> <name> tmux new-window -d -t main "sh -c 'env > /tmp/w.txt'"` の後
   `grep E2E_ /tmp/w.txt` を実行する。
   → **1件も出ない**。

2026-08-19 に実機で測定した(コンテナ `cdx-e2e-envmix`)。

## 影響

**`AC-08`(プロジェクトごとの環境変数がコンテナ内のツールに見える)が実機に対して不合格である。**
`AC-08` の操作4 は「**立ち上がった端末の中で**、書いた名前の環境変数を表示する」であり、
`claude-dev start` がアタッチするのは tmux なので、その端末は tmux の窓である。
不合格の条件として `AC-08` 自身が「**書いた値がコンテナの中で見えない**」を挙げている。

利用者から見ると、env ファイルに書いた接続先 URL・トークン・切り替えフラグが、
**自分が実際に作業する窓では効かない**。ビルド・テスト・エージェント CLI はその窓から起動するので、
`AC-08` が期待する「コンテナ内で動かすツールからも同じ値が見える」も成り立たない。
`docker exec` で確かめると見えるため、**確認の仕方によって合格に見えてしまう**のが厄介である。

severity の根拠: **`AC-nn` が実機に対して不合格**(`.claude/directions/issues-pendings.md` §3.0 の「高」の1つ目)。

## 原因の見当

`scripts/entrypoint-claude.sh` が tmux セッションを `su "$USERNAME" -s /bin/zsh -l -c "…"` で起こす。
**`su -l` はホストの `docker run -e` で渡された変数もイメージの `ENV` で付いた変数もまとめて捨てる。**
tmux サーバの環境はその配下の全ウィンドウ・全プロセスが継承するので、捨てられた変数は
tmux の中のどこからも見えない。`tmux` の `update-environment` の既定値8個
(`DISPLAY` / `SSH_AUTH_SOCK` ほか)だけがクライアント接続時に写されるため、
**`SSH_AUTH_SOCK` と `DISPLAY` だけが偶然生き残っている**。

起票時点の `task-fix-tmux-server-drops-reserved-env` は、この経路に
**予約名(接頭辞 `CLAUDE_DEV_` と固定名5つ)だけ**を明示的に載せ直す形を採っており、
プロジェクト環境ファイルの組は載せ直しの対象外だった。したがって本 issue は同タスクが
作り込んだものではなく、**同じ根の残り**である。
**2026-08-19 の人間の裁定でこの issue は同タスクへ畳み込まれ、同タスクは案 B(`su` から
`-l` を外す)へ差し替わった** — 列挙をやめたので env ファイルの組も引き継がれる(下記「経緯」)。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| env ファイルの組の到達範囲 | `MODULE-cli-start` 手順5-2・手順13 が `-e <名前>=<値>` で**コンテナへ**渡すとだけ書く。コンテナ内でどこまで届くかは書いていない | `AC-08` は「**立ち上がった端末の中で**…見える」「コンテナ内で動かすツールからも同じ値が見える」と要求する。`FR-env-14-1` は「コンテナへ環境変数として渡さなければならない」までしか書いておらず、**到達範囲の条項を持たない** | **要件・設計が正**(`AC-08` が求めていることを `FR-env-14` が条項として書き切っていない。`FR-env-07-13` が予約名について書いたのと同じ形が要る) |
| どの集合を載せ直すか | 予約名だけ(`FR-env-07-13` の範囲) | `AC-08` は利用者が書いた組も対象にしている | **要件・設計が正** |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `FR-env-14` に `FR-env-07-13` と同じ形の条項を足し、`CTR-cli-container` の到達の義務を「予約名 + プロジェクト環境ファイルの組」へ広げ、entrypoint の載せ直しに組を加える | 01・02・03 の1回の下降 + `scripts/entrypoint-claude.sh` の1箇所。載せ直す名前を entrypoint が知る手段が要る(現状 entrypoint は「どれが利用者由来か」を区別できないので、CLI が名前の一覧を1つの変数で渡すか、entrypoint が予約名以外もすべて載せるかを決める) |
| B | tmux を起こす `su` から **`-l` を外す**(同じファイルの `start-user-desktop.sh` の起動は `-l` 無しで環境をそのまま継いでいる)。載せ直しそのものが不要になり、`TZ` / `LC_ALL` など走査で挙げた他の変数も同時に解決する | `su -l` が設定していた `PATH` / `HOME` / 作業ディレクトリの扱いが変わるので、その3つを明示する必要がある。`task-fix-tmux-server-drops-reserved-env` の `[DS-05]` はこの案を「`-l` を外すと `PATH` / `HOME` / 作業ディレクトリまで同時に変わる」として退けた。**この理由は 2026-08-19 の実測で誤りだった** — `su <user> -s /bin/zsh -l -c` と `-l` 無しを並べて測ると `PATH` も `HOME` も同一で、違うのは `PWD` だけ(コマンドが `cd /workspace` するので影響しない)。`[DS-05]` は継続ではなく**更新**である(`delegation.md` §3.1) |
| C | 予約名以外もすべて載せ直す(A の変種で、CLI からの名前の受け渡しを要さない) | entrypoint の1箇所。ただし「コンテナに在る変数を全部 tmux へ渡す」ことの是非を 02 で決める必要がある |

**2026-08-19 に人間が案 B を選び、本 issue を `task-fix-tmux-server-drops-reserved-env` へ
畳み込んだ**(memo.md「決定シート(回答済み)」論点2。回答は逐語で「1.b。2.B。」)。

## 経緯

- 2026-08-19 起票。人間が「`.claude-dev.yaml` に env ファイルを指定できるようにした機能と、
  tmux へ予約環境変数を引き継ぐ修正は干渉しないか」と問うたことを受けて実機で測定し、
  **干渉はしない**(予約名は `FR-env-14-8` により差し替えられず、実測でも
  `DOCKER_HOST` / `COMPOSE_PROJECT_NAME` / `CLAUDE_DEV_INJECT` の3つが採用されずに表示された)一方で、
  **env ファイルの組が tmux の窓に届いていない**ことが分かった。
- 2026-08-19 人間の裁定「1.b。2.B。」により `task-fix-tmux-server-drops-reserved-env` へ畳み込み、
  直し方は**案 B**(tmux を起こす `su` から `-l` を外す)に決まった。同タスクの `FR-env-14-11` と
  `CTR-cli-container`「渡す環境変数」が到達の義務を持ち、確認は E2E-01 手順9-6 が担う。
  **本 issue を閉じるのは同タスクの `/task-close` である。**
</content>
