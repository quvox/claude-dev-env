---
target: docs/03-impl/tests/e2e.md
change: replace
sections:
  - "### E2E-01"
  - "### E2E-04"
  - "## E2Eシナリオ ⇄ テスト対応表"
  - "## テスト設計の判断"
deletes: []
reason: '`docs/issues/090` の裁定で 01 に新設する条項 `FR-env-03-24`(`logout` の後にセッション由来の資源が `stop` では回収できなくなる)の**実機確認手順**を作る。**フェーズ2 の下降はこの受け皿を作っていなかった** — `03-impl/tests/cli-logout.md` の対応表は「E2E-01 手順8」を指しているが、手順8 の部分手順1〜16 に `logout` の後で `stop` を走らせる並びは1つも無く、**指し先が空の状態だった**(`/doc-check` の独立レビュー3本が独立に検出)。`.claude/directions/layer-fit.md` §2「移送で最も多い誤りは片側だけで終わること」に当たるので、条項を足す下降と同じ回で閉じる。内訳: (a) 手順8 に部分手順16 を新設する(**前提は自分で用意する形にした** — 手順8-15 の `reset` を実行していると `aaa` / `bbb` のセッションもイメージも残っていないため。手順8-11 の `nolabel` と同じ書き方である)(所有者ラベル付きの資源を作る → `logout --yes` → `stop` で回収されないことと「削除できなかった資源」として表示されないことを確認 → `reset` で回収できることを確認)。(b) 既存の後片付けを部分手順17 へ繰り下げ、その本文の「手順10・12・15 の `reset`」を「手順10・12・15・16」へ直す(**部分手順16 が `reset` を実行しうるため**)。**手順8-14 / 8-15 の番号は動かさない**(`03-impl/tests/cli-stop.md` と`cli-reset.md` の識別子欄が名指しているため)。`8-16` を名指す記述は本ファイル以外に無いことを確認済みである。(c) E2E シナリオ対応表の E2E-01 行の手順8 の内訳に、新設した部分手順16 を1項目足す。(d) `CS19` の要求により「テスト設計の判断」を再読し、**後片付けの手順番号を `8-16` → `8-17` へ直し**(繰り下げの反映)、新設した部分手順16 をどう組んだかの判断を1行足した。**既存の4件の判断はいずれも継続(内容は変えない)**。(e) `CS8` が本文の程度語「通常」3件を検出したので、意味を保って直した(`通常操作の透過` → `拒否条件に当たらない要求の透過` / `通常どおり成功する` → `成功する` / `通常どおり起動する` → `起動が成功する`)。**凍結した母集団の CS8 が3件減る方向にしか動かない**。**上記 (a)〜(e) 以外、既存の部分手順の中身は1文字も変えない**。**本文は「深い見出しを先に」の順で並べてある** — `### E2E-01` を `## E2Eシナリオ ⇄ テスト対応表` の後ろに置くと本文の中で `##` の子として読め、反映時に**同じ節が2箇所へ書き込まれる**(合成ビューで実際に2箇所に出ることを確認して直した)。(f) **同型の欠陥をもう1件、同じ下降で閉じた** — `NFR-sec-03` の測定方法から落とす「E2E-04 の実機確認手順で当該 worker ウィンドウ内の `env` を確認する」も、**E2E-04 の手順に `env` を見る部分手順が1つも無い**という同じ空手形だった(`/doc-check` の再監査が検出)。E2E-04 に手順8 を新設して、worker とレビューアーの環境に `SLACK_BOT_TOKEN` が無いことを確認する手順にした。**この2件で、`03-impl/tests/` の識別子欄が指す実機確認手順が実在しない箇所は 0 件になる**(`手順8-N` の指し先 全件と `E2E-04` を機械照合して確認した)'
---

### E2E-01

1. 空のディレクトリを作り、その中で `claude-dev start` を実行する。
2. コンテナが起動し、noVNC の URL が表示され、tmux にアタッチされることを確認する。
3. コンテナ内で `ls /workspace` がホスト側のディレクトリと一致すること、`id` の UID/GID が
   ホストと一致すること、`docker inspect` にホストの秘密鍵ファイルと Docker 生ソケットの
   マウントが無いことを確認する。
4. 起動ログにファイアウォールのサマリが出ていることを確認する。
5. tmux をデタッチし、SSH を切断してから入り直し、`claude-dev start` を再実行して同じコンテナへ
   再接続することを確認する。
6. `--no-vnc` でも同様に起動し、noVNC の URL が表示されないことを確認する。
7. **同名コンテナの衝突で稼働中のコンテナが失われないこと**(`FR-env-01` 受入基準12・13)を
   確認する。
   **★衝突は「basename が同じ2つのディレクトリで順番に `start` する」だけでは起きない。**
   同名コンテナが稼働中なら再接続の経路に入って `exit 0` するからである。
   衝突が起きるのは**稼働判定を通り抜けたあと、コンテナ作成に達するまでの数秒の間に
   同名コンテナが現れたとき**だけなので(窓の位置は `MODULE-cli-start` の処理の流れ)、
   その窓を意図的に作って確認する。
   1. 専用の空ディレクトリ(例: `/tmp/e2e-x/web`)を作る。同名の `web` コンテナが**無い**ことを
      `docker ps -a --filter name=^web$` で確かめる。
   2. そのディレクトリで `CLAUDE_DEV_NO_ATTACH=1 claude-dev start` を**バックグラウンドで**起動し、
      出力をファイルへ落とす。
   3. 出力に `SSH 鍵が未設定` の行が現れたら、**すぐに**
      同名の代役コンテナを立てる: `docker run -d --name web busybox sleep 600`。ID を控える。
      さらに `docker exec web touch /tmp/marker-a` で目印を作る(削除の判別に使う)。
   4. `start` の終了を待つ。**期待する結果**: (a) 終了コードが 1、
      (b) 出力に**同名のコンテナが稼働中である旨**・**別ディレクトリの同名プロジェクトである
      可能性**・**既存のコンテナに手を触れていないこと**が含まれる、
      (c) 3 で控えた ID が**そのまま稼働している**、
      (d) `docker exec web ls /tmp/marker-a` が成功する。
   5. **不合格の条件**: 代役コンテナが消えている / ID が変わっている / `marker-a` が無い /
      終了コードが 0 になる。
   6. **回帰の確認**: 代役コンテナを消し(`docker rm -f web`)、同じディレクトリで
      `claude-dev start` が**成功する**(終了コード 0)こと、もう一度実行すると
      「`web` は実行中。接続します...」の再接続経路に入ること(`FR-env-01` 受入基準4)を確かめる。
   7. 後片付け: `claude-dev stop web` を実行し、`docker volume rm claude-dev-chrome-web` と
      一時ディレクトリを削除する。他に稼働中の Claude コンテナがあるときは、
      `docker ps --filter name=claude-dev-docker-proxy` で共有 docker-proxy が**残っている**ことを
      確認する(遊休判定が `claude-dev-net` への接続で行われるため、稼働中のコンテナがあれば
      消えないのが正しい。消えていたら `FR-env-01` 受入基準9 違反であり不合格)。
   - macOS(`claude-dev-mac`)でも同じ手順を実行する。実行できない場合は
     **未実施であることを記録する**(手順を省いたことを黙って残さない)。
8. **破壊的操作が自分が作った資源にだけ効くこと**(`FR-env-01` 受入基準 9・14〜27 /
   `FR-env-03` 受入基準 14〜23)を確認する。**専用の空ディレクトリを2つ**(例: `/tmp/e2e-y/aaa` と
   `/tmp/e2e-y/bbb`)使い、他に作業中のセッションが無い時間帯に行う。
   1. **管理ラベルの付与**(`FR-env-01` 受入基準14): `aaa` で
      `CLAUDE_DEV_NO_ATTACH=1 claude-dev start` を実行し、
      `docker inspect -f '{{json .Config.Labels}}' aaa` に `claude-dev.managed=1` /
      `claude-dev.role=claude` / `claude-dev.project-dir=/tmp/e2e-y/aaa` の3つが含まれることを
      確認する。`docker inspect -f '{{json .Config.Labels}}' claude-dev-docker-proxy` に
      `claude-dev.` で始まるラベルが**含まれない**ことも確認する(`DSN-env-01`: 固定名を持つ資源にはラベルを付けない)。
   2. **遊休判定がイメージに依存しないこと**(受入基準9。`docs/issues/045` の再現):
      `bbb` でも `start` する。`make upgrade`(またはイメージの再ビルド)を行い、`latest` が
      別のイメージ ID を指す状態を作る(`docker inspect -f '{{.Image}}' aaa` と
      `docker images -q claude-dev-claude-vnc` が食い違うことで確認できる)。そのうえで
      `claude-dev stop bbb` を実行し、**`claude-dev-docker-proxy` が残っている**ことと、
      出力に docker-proxy を残した理由として `aaa` の名前が出ることを確認する。
      **不合格の条件**: docker-proxy が消える / 「Claude コンテナなし」と表示される。
   3. **排他**(受入基準16。**6コマンドすべてについて確認する**):
      `sleep 600 &` で生きているプロセスを作り、その PID を控える(`$LIVE`)。
      **ロックは「向き先に `<PID> <操作名>` を入れたシンボリックリンク」である**ので、
      `ln -s "$LIVE stop" ~/.claude-dev/locks/proj-aaa.lock` で保持中の状態を作れる
      (`readlink ~/.claude-dev/locks/proj-aaa.lock` で確認できる)。
      **ファイル名はプロジェクト単位が `proj-<キー>.lock`、共有資源単位が `shared.lock`** である
      (種別で名前空間を分けている。理由は `MODULE-cli-common-lock` 判断13)。
      - **プロジェクト単位のキー**: 上の状態で `aaa` のディレクトリで `claude-dev start` を
        実行する。**期待する結果**: 待たずに終了コード 1、出力に保持している操作名(`stop`)と
        PID と再実行の方法が出る、生成物が増えない。同じ状態で `claude-dev stop aaa` も
        同じ結果になることを確認する(プロジェクト単位のキーを取るのは `start` と `stop` の2つ)。
      - **共有資源単位のキー**: `rm -f ~/.claude-dev/locks/proj-aaa.lock` してから
        `ln -s "$LIVE logout" ~/.claude-dev/locks/shared.lock` を作る。この状態で
        **`start` / `logout` / `reset` / `login` / `login-codex` の5つをそれぞれ実行**し、
        **いずれも待たずに終了コード 1 で終わり、保持者(`logout` と PID)と再実行の方法が
        表示される**ことを確認する。`start` については**認証コピーの手前で**止まること
        (**認証が空のコンテナが起動したら不合格**)、`logout` / `reset` については
        **何も削除されていない**こと、`login` / `login-codex` については
        **共有ボリュームに何も書かれていない**ことをあわせて確認する。
      - **プロジェクト名が `shared` のとき**: `/tmp/e2e-y/shared` を作って
        `CLAUDE_DEV_NO_ATTACH=1 claude-dev start --no-vnc` を実行する。**期待する結果**:
        起動が成功する(`proj-shared.lock` と `shared.lock` は別のファイルなので衝突しない)。
        **不合格の条件**: 「排他ロックを取得できませんでした(キー: shared)」で終了コード 1 になる
        (プロジェクト単位のキーと共有資源単位の固定キーが同じファイルを指している)。
      - 後片付け: `rm -f ~/.claude-dev/locks/shared.lock` と `kill $LIVE`。
      **不合格の条件**: どれかが待つ(固まる)/ 終了コードが 0 になる /
      ロックを取れないまま削除・作成が行われる。
   4. **ロック残骸の引き継ぎ**(受入基準17): `ln -s "999999 stop" ~/.claude-dev/locks/proj-aaa.lock`
      で**存在しない PID** を保持者とするロックを作ってから `claude-dev stop aaa` を
      実行する。**期待する結果**: 残骸を引き継いだ旨が表示され、処理が完了する(終了コード 0)。
      **`~/.claude-dev/locks/` に `proj-aaa.lock.stale.*` が残っていない**ことも確認する
      (引き取った側が消す)。
   5. **ラベルを持たない既存コンテナを巻き込まないこと**(`FR-env-03` 受入基準17):
      `docker run -d --name legacy-claude --network claude-dev-net busybox sleep 600` で
      ラベル無しのコンテナを立てる。`claude-dev logout` を実行し、**確認プロンプトの一覧に
      `legacy-claude` が削除対象として出ないこと**、削除されずに残ること、
      「本変更より前に起動した可能性がある」旨が表示されることを確認する。
      **さらに `logout` の遊休判定**(`FR-env-01` 受入基準9 の `logout` 側)を確認する:
      `legacy-claude` が `claude-dev-net` に接続したまま稼働しているので、`claude-dev logout` の
      あとに **`claude-dev-docker-proxy` が残っている**ことと、**残した理由として
      `legacy-claude` の名前が表示される**ことを確認する。
      **不合格の条件**: docker-proxy が消える(残したコンテナの中から Docker が使えなくなる)。
      あわせて `claude-dev stop legacy-claude`(名前指定)では**削除される**こと、
      その際に管理ラベルを持たないことが表示されること(`FR-env-01` 受入基準15)を確認する。
   6. **compose 資源が別プロジェクトを巻き込まないこと**(`FR-env-01` 受入基準 19・20):
      `/tmp/e2e-y/My.App` と `/tmp/e2e-y/my-app` の2ディレクトリを作る(正規化すると**どちらも
      `my-app`** になる)。両方で `CLAUDE_DEV_NO_ATTACH=1 claude-dev start` し、それぞれの
      コンテナ内で `docker compose up -d`(最小の compose ファイルでよい)を実行する。
      `docker ps --format '{{.Names}}\t{{.Label "com.docker.compose.project"}}'` で、
      **2つの compose プロジェクト名が異なる**(`my-app-<ハッシュA>` と `my-app-<ハッシュB>`)ことを
      確認する。次に `/tmp/e2e-y/my-app` 側で `claude-dev stop` を実行し、
      **`My.App` 側の compose コンテナが残っている**ことを確認する。
      **不合格の条件**: 2つのプロジェクト名が同じ / `My.App` 側の compose コンテナが消える。
      あわせて `docker run -d --label com.docker.compose.project=my-app --name legacy-compose
      busybox sleep 600` で**旧い名前の資源**を作り、`claude-dev stop my-app` が
      **それを削除せず**、残っている可能性と手動削除の方法を表示することを確認する(受入基準20)。
   7. **`stop` が受理しない名前**(`FR-env-01` 受入基準18):
      `claude-dev stop '../../etc'` を実行し、**何も削除されず**、受理できない文字を含む旨が
      表示されて終了コード 1 になることを確認する。`~/.claude-dev/locks/` に新しいロックが
      作られていないことも確認する。
   8. **`logout` がプロジェクト配下の認証コピーを消すこと**(`FR-env-03` 受入基準 20・21):
      `claude-dev login` 後に `aaa` で `start` し、`/tmp/e2e-y/aaa/.claude/.credentials.json` が
      できていることを確認する。`bbb` でも `start` して同じファイルを作る。
      `/tmp/e2e-y/aaa` へ移動して `claude-dev logout --yes` を実行し、
      **(a)** `aaa` 側の `.claude/.credentials.json` / `.claude/.claude.json` /
      `.codex/auth.json` が消え、削除したパスが表示される、
      **(b)** `.claude/` ディレクトリ自体と `.claude/settings.json` / `host-hooks.json` は**残る**、
      **(c)** **`bbb` 側のコピーは残っている**(他ディレクトリに触らない)、
      **(d)** 認証コピーが1つも無い状態で再度 `claude-dev logout` を実行すると、対象が無い旨を
      表示して終了コード 0 になる(受入基準19・21)ことを確認する。
      続けて `claude-dev reset --yes` が **`bbb` 側の `.claude/` を消さない**ことを確認する
      (`FR-env-03` 受入基準22。非対称の根拠は `D0-env-08` 項4)。
   9. **確認と非対話時の中止**(`FR-env-03` 受入基準 14〜16): `claude-dev logout` で `n` を
      入力すると何も削除されず終了コード 0 になること、`claude-dev logout < /dev/null` が
      **何も削除せず終了コード 1** で終わり `--yes` の指定方法を表示すること、
      `claude-dev logout --yes` が確認なしで実行されることを確認する。`claude-dev reset` でも
      同じ3つを確認する(**`reset` は非 TTY で 0 ではなく 1 を返すのが正しい**。確認の免除は `--yes` で行う)。
   10. **削除失敗の列挙**(`FR-env-03` 受入基準18): 共有ボリュームを使用中のコンテナを1つ残した
      状態(`aaa` を稼働させたまま)で `claude-dev reset --yes` を実行し、**消えなかった資源が
      1件ずつ列挙され、終了コード 1 になる**ことを確認する。
      **不合格の条件**: 「全リセット完了」と表示される / 終了コード 0 になる。
   11. **`stop` を別ディレクトリから実行しても compose を取り違えないこと**(`FR-env-01` 受入基準 19・21):
      `/tmp/e2e-y/aaa` で `start` し、コンテナ内で `docker compose up -d` する。
      **`/tmp` など無関係なディレクトリへ移動してから** `claude-dev stop aaa` を実行し、
      **`aaa` の compose コンテナが消える**ことを確認する(カレントディレクトリに依存しない。理由は `MODULE-cli-stop` の実装上の判断)。
      次に、ラベルを持たないコンテナで同じことを試す:
      `docker run -d --name nolabel --network claude-dev-net busybox sleep 600` を立て、
      `claude-dev stop nolabel` を実行し、**compose の削除を試みず**、compose 資源が残っている
      可能性と手動手順が表示されることを確認する。
      **不合格の条件**: 別ディレクトリからの `stop` で compose コンテナが残る / ラベル無しの対象で
      推測したハッシュ名の削除が走る。
   12. **`reset` も遊休判定を通すこと**(`FR-env-01` 受入基準9 の `reset` 側):
      `docker run -d --name legacy2 --network claude-dev-net busybox sleep 600` で
      ラベル無しの稼働中コンテナを立て、`claude-dev reset --yes` を実行する。
      **期待する結果**: (a) `legacy2` が削除されない、(b) **`claude-dev-docker-proxy` が残る**、
      (c) **ネットワーク `claude-dev-net` が残る**、(d) 残した理由(`legacy2` の名前)と
      **「完全な初期化になっていない」旨**が表示される、(e) ボリューム・イメージの削除は続行され、
      使用中で消せなかったものが列挙されて終了コード 1 になる。
      **不合格の条件**: docker-proxy または `claude-dev-net` が消える(残した `legacy2` の中から
      Docker が使えなくなる)/ 「全リセット完了」と表示される。
   13. **中断時の終了コードと部分削除の報告**(`FR-env-03` 受入基準23):
      稼働中コンテナを複数用意して `claude-dev logout --yes` を実行し、削除が始まった直後に
      `Ctrl-C`(または別端末から `kill -INT <PID>`)を送る。**期待する結果**: 進行中の1件が
      終わってから中断し、**そこまでに削除した資源と未削除の資源が1件ずつ列挙**され、
      **終了コード 130** で終わる。`~/.claude-dev/locks/` にロックが残っていないことも確認する
      (`trap` が解放する)。`claude-dev reset --yes` でも同じ3点を確認する。
      **不合格の条件**: 「削除しました」「完了」と表示される / 終了コードが 0 になる /
      ロックが残る。
   14. **セッション由来の資源が `stop` で消えること**(`FR-env-01` 受入基準 22〜24・26・27):
      `aaa` と `bbb` の両方で `CLAUDE_DEV_NO_ATTACH=1 claude-dev start` する。
      1. **`aaa` のコンテナ内で** `docker run -d --name spawn-a busybox sleep 600` と
         `docker network create spawn-net-a` を実行する。
         **`bbb` のコンテナ内で** `docker run -d --name spawn-b busybox sleep 600` を実行する。
      2. ホスト側で
         `docker inspect -f '{{json .Config.Labels}}' spawn-a` に
         **`claude-dev.role=spawned` と `claude-dev.owner-project-dir=/tmp/e2e-y/aaa`** が
         含まれることを確認する。`docker network inspect -f '{{json .Labels}}' spawn-net-a` にも
         同じ2つが含まれることを確認する(`FR-env-07` 受入基準11)。
      3. `claude-dev stop aaa` を実行する。**期待する結果**:
         (a) `spawn-a` と `spawn-net-a` が**消えている**、
         (b) 出力に**削除した資源の名前が種別(コンテナ / ネットワーク)つきで1行ずつ**出る、
         (c) **`spawn-b` は消えていない**(別セッションの資源に触らない)、
         (d) 確認プロンプトは出ない(`stop` は確認を求めない)。
      4. **0件のときに表示が出ないこと**(受入基準27): `bbb` のコンテナ内で何も作らない状態で
         別の空ディレクトリ `/tmp/e2e-y/ccc` を `start` → `claude-dev stop ccc` を実行し、
         **セッション由来の資源に関する行が1行も出ない**ことを確認する。
      5. **所有者ラベルを持たない資源が消えないこと**: ホスト側で
         `docker run -d --name nospawn busybox sleep 600` を立て(docker-proxy を通らないので
         ラベルが付かない)、`claude-dev stop bbb` の後も**残っている**ことを確認する。
      6. **ラベルを読めない対象では片付けを試みないこと**(受入基準23):
         **この手順は対象を自分で用意する**(手順8-11 の `nolabel` は、その手順の中で
         `claude-dev stop nolabel` により既に削除されている)。
         `docker run -d --name nolabel2 --network claude-dev-net busybox sleep 600` で
         管理ラベルを持たないコンテナを立て、`claude-dev stop nolabel2` を実行する。
         **期待する結果**: `nolabel2` 自身は削除される(規則B)一方、
         **セッション由来の資源の削除を試みず**、片付けを行わなかった旨と
         `docker ps --filter label=claude-dev.role=spawned` で確認できることが表示される。
         **不合格の条件**: 推測した所有者の値で `docker rm -f` が走る /
         片付けを行わなかったことが表示されない。
      7. **削除に失敗しても続行すること**(受入基準24): `bbb` で `start` し、**`bbb` の
         コンテナ内で** `docker network create spawn-net-b` と
         `docker run -d --name spawn-b3 --network spawn-net-b busybox sleep 600` を実行する。
         次にホスト側で `docker run -d --name netholder busybox sleep 600` を立て、
         `docker network connect spawn-net-b netholder` を実行して
         **そのネットワークを `bbb` の外からも使用中にする**
         (`aaa` は部分手順3 の `claude-dev stop aaa` で既に消えているので使えない)。
         `claude-dev stop bbb` を実行する。**期待する結果**: `spawn-b3` は削除され、
         `spawn-net-b` の `docker network rm` は失敗するが**処理は続行し、終了コード 0 で終わる**。
         失敗した名前が stderr に出る。
         **不合格の条件**: 終了コードが非0になる / 失敗した名前が出ない /
         後続の手順(macOS のブリッジ停止・遊休判定)が実行されない。
      **手順8-14 全体の不合格の条件**: **部分手順3 の時点で** `spawn-b` が消える
      (他セッションを巻き込む。部分手順5 の `claude-dev stop bbb` で消えるのは正しい)/
      部分手順5 の後に `nospawn` が消える / 削除した名前が表示されない / 0件でも行が出る。
   15. **`reset` が所有者を問わず消すこと**(`FR-env-01` 受入基準25):
      `aaa` と `bbb` の両方で `start` し、それぞれのコンテナ内で
      `docker run -d --name spawn-a2 busybox sleep 600` / `docker run -d --name spawn-b2 busybox sleep 600`
      を実行する。`claude-dev reset` を実行し、**確認プロンプトの削除対象の一覧に
      `spawn-a2` と `spawn-b2` の両方が出る**ことを確認してから `y` で進める。
      **期待する結果**: 両方が削除され、削除した名前が種別つきで表示される。
      **不合格の条件**: 一覧に出ない(消える前に知る手段が無い)/ 片方しか消えない。
   16. **`logout` の後にセッション由来の資源が `stop` で回収できないこと**
      (`FR-env-03` 受入基準24)。**前提**: 手順8-15 の `reset` を実行した場合は、
      イメージと共有資源が消えているので**先に `claude-dev setup`(またはイメージの再取得)で
      環境を戻してから始める**。`aaa` / `bbb` のセッションはこの時点でどちらも残っていないため、
      この部分手順は**自分で対象を用意する**。
      `/tmp/e2e-y/aaa` で `claude-dev start` し、**`aaa` のコンテナ内で**
      `docker run -d --name spawn-a3 busybox sleep 600` を実行して所有者ラベル付きの資源を作る。
      ホスト側の同じディレクトリで `claude-dev logout --yes` を実行し、
      **`aaa` の Claude コンテナが削除される**ことを確認する(`FR-env-03` 受入基準5)。
      続けて同じディレクトリで `claude-dev stop aaa` を実行する。
      **期待する結果**: `spawn-a3` は**削除されずに残る**(所有者を照合する値の在り処である
      `claude-dev.project-dir` ラベルが、削除された Claude コンテナと一緒に失われているため。
      `CTR-cli-container`「削除対象の決め方(4つの規則)」)。かつ **`spawn-a3` を
      「削除できなかった資源」として表示しない**(受入基準18 の対象ではない)。
      その後 `claude-dev reset` を実行すると `spawn-a3` が削除対象の一覧に現れ、削除される。
      **不合格の条件**: `stop` が `spawn-a3` を削除する(所有者を推測している)/
      `stop` が `spawn-a3` を「削除できなかった資源」として列挙して非0で終わる /
      `reset` の一覧に `spawn-a3` が出ない。
      **後片付け**: 上の `reset` を実行しない場合は `docker rm -f spawn-a3` を実行する。
   17. 後片付け。**手順10・12・15・16 の `reset` を実行したかどうかで分かれる**:
      - **実行した場合**: `reset` が Claude コンテナ・`claude-dev-chrome-*`・セッション由来の資源・
        イメージを既に消しているので、**残っているのは所有者ラベルを持たない資源だけ**である
        (`docker rm -f nolabel nolabel2 nospawn` / `docker network rm` の残り)。そのうえで
        `claude-dev setup`(またはイメージの再取得)で環境を戻し、`rm -rf ~/.claude-dev/locks` と
        一時ディレクトリを削除する。**`claude-dev stop` は対象が無いので実行しない**。
      - **実行していない場合**: `docker rm -f legacy-claude legacy-compose legacy2 nolabel nolabel2
        nospawn spawn-a spawn-b spawn-a2 spawn-b2 spawn-b3 netholder` /
        `docker network rm spawn-net-a spawn-net-b` / `claude-dev stop aaa` / `claude-dev stop bbb` /
        `claude-dev stop ccc` /
        `docker volume rm claude-dev-chrome-aaa claude-dev-chrome-bbb claude-dev-chrome-ccc` /
        `rm -rf ~/.claude-dev/locks` / 一時ディレクトリの削除。
   - macOS(`claude-dev-mac`)でも同じ手順を実行する。実行できない場合は
     **未実施であることを記録する**(手順を省いたことを黙って残さない)。

### E2E-04

1. `make orch-sample` で題材を配置する。
2. 題材のディレクトリで `claude-dev orchestrate` を実行する。
3. ブレインストーミングで plan を確定し、実行モードへ入ることを確認する。
4. 複数の worker が並行して動くこと、要判断が出たタスクだけが待機し他が継続することを確認する。
5. 待機中のタスクへ回答し、そのタスクが復帰することを確認する。
6. 完了時に成果が統合され、完了が通知されることを確認する。
7. `.orchestrator/*.jsonl` に委譲・結果・仮定・介入が記録されていることを確認する。
8. **秘密情報が worker とレビューアーの環境に無いこと**(`NFR-sec-03`): 手順4 で worker が
   動いている間に、その worker ウィンドウと、レビューを走らせているウィンドウで `env` を実行し、
   **`SLACK_BOT_TOKEN` が1つも出ない**ことを確認する。**期待する結果**: どちらの環境にも当該変数が
   無い。**不合格の条件**: いずれかの環境に現れる(コントローラとフックだけが持ってよい)。
   **対話 Claude の経路は単体テストが固定しているのでここでは確認しない**(`docs/03-impl/tests/orchestrator.md` の該当行が正である)。

## E2Eシナリオ ⇄ テスト対応表

| E2E ID | 対応 UC | シナリオ | テスト識別子 | 状態 |
|---|---|---|---|---|
| E2E-01 | UC-01 | `claude-dev start`(ブラウザ確認あり / `--no-vnc`)→ `/workspace` マウント・認証・ファイアウォール・tmux → `claude` 起動 → 再実行での再接続 → **同名衝突で稼働中のコンテナを失わないこと(手順7)→ 破壊的操作が「自分が作った資源」にだけ効くこと(手順8: 管理ラベル・遊休判定・排他ロック・ラベル無しコンテナの保護・compose 資源の隔離・受理しない名前・プロジェクト配下の認証コピー・確認と非対話時の中止・削除失敗の列挙・**セッション由来の資源の片付け(手順8-14・8-15)・`logout` 後に回収できないこと(手順8-16)**)** | 手順のみ(下記「実機確認の手順」E2E-01) | 未検証(テスト未実装) |
| E2E-02 | UC-02 | `claude-dev forward` → 8100 番台の割当と SSH トンネル → クライアントのブラウザで表示 → `claude-dev ports` で確認 | 手順のみ(同 E2E-02) | 未検証(テスト未実装) |
| E2E-03 | UC-03 | コンテナ内で危険な `docker run` → 拒否 / `/workspace` bind の許可 / 拒否条件に当たらない要求の透過 / **作られたコンテナとネットワークに所有者ラベルが付くこと** | 手順のみ(同 E2E-03)。判定ロジックは `cd docker-proxy && go test ./...` が単体で検証済み。**条項ごとに単体でどこまで検証済みかは `03-impl/tests/docker-proxy.md` が正である** | 未検証(テスト未実装) |
| E2E-04 | UC-04 | `orchestrate` → ブレインストーミング → plan 確定 → worker 並列 → 要判断1件のみ待機・他は継続 → 回答で復帰 → 完了 | 手順のみ(同 E2E-04)。`make orch-sample` で題材を配置して実走する | 未検証(テスト未実装) |
| E2E-05 | UC-05 | 実行中に端末を全終了 → `orchestrate` 再実行 → 合流/再開・完了済みの非再実行・plan と履歴の保持 | 手順のみ(同 E2E-05) | 未検証(テスト未実装) |
| E2E-06 | UC-06 | `claude-dev login-codex` → デバイス認証 → 別プロジェクトで `start` → 再ログイン不要で `codex` が起動し、シェルコマンドが成功して `/workspace` を読み書きできる。landlock の疎通確認が通り、読み取り専用の明示指定で読み取りが成功する | `scripts/e2e6-codex.sh`(実機で実行する検証スクリプト。自動テストランナーからは呼ばれない) | 未検証(テスト未実装) |

## テスト設計の判断

<!-- 実機確認の手順そのものをどう組んだかの判断。何を確認するか(受入基準)は 01 が正である。 -->

- [DS-01] セッション由来の資源の確認を **`stop` 側(手順8-14)と `reset` 側(手順8-15)に分ける** — 理由: `reset` は所有者を問わず消すので、`stop` が「別セッションの資源を消さないこと」を確かめるために立てた2つ目のセッションを、同じ手順の中では生かしておけない / 見直す条件: `reset` の削除範囲が所有者付きへ変わり、同じ前提で連続して流せるようになったとき
- [DS-01] 手順8-14 を**7つの部分手順に割り**、1つの部分手順が1条項に対応する形にする — 理由: `03-impl/tests/cli-stop.md` の識別子欄が部分手順を名指すので、粒度が粗いと「その手順では実際には確認しない条項」を表が受け入れてしまう/ 見直す条件: 1つの部分手順が2条項以上を兼ねるようになったとき(そのときは対応表の識別子欄が一意でなくなる)
- [DS-01] 新設した手順が作った資源の**後片付けを各シナリオの末尾の手順として明示する**(E2E-01 手順8-17 / E2E-03 手順7) — 理由: 手順5 以降は `-d ... sleep 60` と `--name` で名前を占有するので、片付けないと**2回目の実行が同名衝突で落ちる** / 見直す条件: 手順が名前付きの資源を作らなくなったとき
- [DS-01] このホストで実行できない部分手順(2セッション同時・`reset` の破壊・macOS)を**手順から外さず、未実施として記録する形にする** — 理由: 手順を消すと「確認しなくてよい」と読めるが、実際には専有環境があれば確認できる。未実施の理由と代替として確認したことは、本ファイルの「未検証(テスト未実装)の全件」と `docs/pendings.md` に残す / 見直す条件: 専有できるホストで一通り流し切ったとき(そのときは未実施の記録を消す)
- [DS-01] **`FR-env-03-24` の確認を手順8-15(`reset`)より後の部分手順16 に置く** — 理由: この確認は `logout` で Claude コンテナを消してから `stop` を走らせるので、**先に置くと以降の部分手順が使うセッション `aaa` が失われる**。手順8-15 までの前提を壊さない位置は末尾しかない / 見直す条件: `logout` が Claude コンテナを削除しなくなったとき(そのときは順序の制約が消える)
