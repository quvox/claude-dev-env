---
target: docs/03-impl/tests/e2e.md
change: replace
version_bump: minor
sections:
  - "### E2E-01"
  - "## テスト設計の判断"
deletes: []
reason: 'E2E-01 手順8 に `FR-env-03` 受入基準19 の3つの確認を足す。(1) 手順8-5 に、**セッション由来のコンテナが「管理ラベルを持たない」の列に現れないこと**の確認を足す(`docs/issues/089` の除外の確認先)。(2) 手順8-8 に (e) を足し、**ラベル無しの稼働中コンテナがあるときは0件の経路((d) の状態)でもその名前と書き戻しの警告が出ること**を確認する(`docs/issues/052`)。(3) **手順8-18 を新設**し、共有ボリュームの中身を読めない状態(一時コンテナが起動できない)では0件の経路に入らず確認を求めることを確かめる(`docs/issues/053`)。手順8-18 は Docker 側を意図的に壊した状態を要して他の部分手順の前提を壊すため、後片付け(手順8-17)より後に置き、自分の後片付けを自分で持つ。**既存の手順番号は1つも動かさない**(`docs/pendings.md` P-006 と `03-impl/tests/cli-logout.md` が手順8-15・8-16 を名指しているため)。あわせて「テスト設計の判断」の `[DS-01]` 後片付けの行に、手順8-18 が自分の後片付けを持つことを書き足す'
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
      **さらにセッション由来のコンテナが混じらないこと**(`docs/02-design/contracts/cli-container.md`
      「残したものをどう列挙するか」の4つ目の除外)を確認する。**この確認は Claude コンテナの
      中から資源を作る必要があるが、`aaa` は部分手順4 の `claude-dev stop aaa` で既に消えている**
      ので、まず `/tmp/e2e-y/aaa` で `CLAUDE_DEV_NO_ATTACH=1 claude-dev start` して立て直す。
      その `aaa` のコンテナ内で
      `docker run -d --name spawn-unmanaged --network claude-dev-net busybox sleep 600` を実行して
      所有者ラベル付きのコンテナを作り(docker-proxy が `claude-dev.role=spawned` を付ける)、
      ホスト側で `claude-dev logout` を実行する。**期待する結果**: `spawn-unmanaged` が
      「管理ラベルを持たない次のコンテナは削除しません」の列に**現れない**
      (`legacy-claude` はこの列に現れる)。
      **不合格の条件**: `spawn-unmanaged` がその列に現れる(**本変更より後に作られた資源なので
      事実に反する表示である**)。**後片付け**: `docker rm -f spawn-unmanaged`
      (`aaa` の Claude コンテナは `logout` が削除済みである)。
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
      **(e)** **(d) の状態で、ラベル無しの稼働中コンテナがあるときの表示**(受入基準19)を確認する:
      **部分手順5 の `legacy-claude` はその手順の末尾で `claude-dev stop legacy-claude` により
      消えている**ので、`docker run -d --name legacy-claude --network claude-dev-net busybox sleep 600`
      で立て直す。稼働させたまま (d) を再実行し、
      **`legacy-claude` の名前と、稼働している限り認証が共有ボリュームへ書き戻される旨の警告が
      表示される**ことを確認する(終了コードは 0 のまま)。
      **不合格の条件**: 「削除対象がありません」だけが表示され、`legacy-claude` の名前も
      書き戻しの警告も出ない(**利用者が `logout` の効果が戻る理由に到達できない**)。
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
   18. **共有ボリュームが空かを確かめられない状態では0件の経路に入らないこと**
      (`FR-env-03` 受入基準19)。**この部分手順は Docker 側を意図的に壊した状態を要し、
      その状態では他のどの部分手順も実行できないため、後片付け(手順8-17)より後に置く。
      自分が作った状態は自分で元に戻す。**
      **前提**: 手順8-17 で環境を戻した状態から始める。`claude-dev login` で共有ボリューム
      `claude-dev-auth` に認証を置き、**管理ラベルを持つコンテナを1つも動かさず、カレント
      ディレクトリに認証コピーも置かない**(= 削除対象が0件になる状態)。
      **本体**: **`require_setup` を通り抜けたうえで一時コンテナだけが起動できない**状態を作る。
      **イメージを削除する方法は使えない**: `require_setup` は `claude-dev-claude` と
      `claude-dev-claude-vnc` の**それぞれの有無を独立に検査して、無ければその場でビルドし直す**
      ので、消しても再ビルドされて起動できてしまう(`claude-dev` の `require_setup`)。
      代わりに**名前はそのままで中身を差し替える**:
      `docker tag claude-dev-claude claude-dev-claude.e2e-backup` で退避し、
      `docker pull busybox && docker tag busybox claude-dev-claude` を実行する。
      **イメージ名は実在するので `require_setup` は何もせず素通りし**、
      `docker run --entrypoint bash …` は busybox に `bash` が無いので**起動に失敗する** —
      これが「中身を読む手段が起動できなかった」状態である。
      (確かめたいのは「中身を読めないときにこの経路へ入らないこと」であって壊し方そのものでは
      ないので、同じ状態を作れる別の手段でもよい。**満たすべき条件は
      「`require_setup` が通る」かつ「一時コンテナが起動できない」の2つ**である。)
      この状態で `claude-dev logout < /dev/null` を実行する。
      **期待する結果**: **「削除対象がありません」を表示して 0 で終わらない。**
      共有ボリュームの状態を確かめられなかった旨が表示され、削除対象の列挙と確認へ進む
      (標準入力が TTY でないので `--yes` が無ければ**終了コード 1 で中止**する —
      受入基準15)。続けて `claude-dev logout --yes` を実行した場合は削除を試み、
      **消去を確認できないので消えなかった資源として列挙し終了コード 1 で終わる**(受入基準18)。
      **不合格の条件**: 「削除対象がありません」と表示して**終了コード 0** で終わる
      (共有ボリュームに認証が残っているのに、利用者は消えたと解釈する)。
      **後片付け**: `docker tag claude-dev-claude.e2e-backup claude-dev-claude` で元へ戻し、
      `docker rmi claude-dev-claude.e2e-backup` と `docker rmi busybox`(他の手順で使っていなければ)
      を実行する。そのうえで `claude-dev logout --yes` を実行して共有ボリュームを実際に空にする。
   - macOS(`claude-dev-mac`)でも同じ手順を実行する。実行できない場合は
     **未実施であることを記録する**(手順を省いたことを黙って残さない)。


## テスト設計の判断

<!-- 実機確認の手順そのものをどう組んだかの判断。何を確認するか(受入基準)は 01 が正である。 -->

- [DS-01] セッション由来の資源の確認を **`stop` 側(手順8-14)と `reset` 側(手順8-15)に分ける** — 理由: `reset` は所有者を問わず消すので、`stop` が「別セッションの資源を消さないこと」を確かめるために立てた2つ目のセッションを、同じ手順の中では生かしておけない / 見直す条件: `reset` の削除範囲が所有者付きへ変わり、同じ前提で連続して流せるようになったとき
- [DS-01] 手順8-14 を**7つの部分手順に割り**、対応表の識別子が**実際に確認する単位**を名指す形にする。1回のコマンド実行で複数の条項を観測できる部分手順は分割せず、**記号付きの期待結果((a)(b)…)を識別子に添えて条項ごとに分ける**(部分手順3 は 1 回の `claude-dev stop aaa` で `FR-env-01-22` を (a)(c) で、`FR-env-01-26` を (b) で観測するため、これを2つの部分手順に割ると同じコマンドを2度流すだけになる) — 理由: `03-impl/tests/cli-stop.md` の識別子欄が確認単位を名指すので、粒度が粗いと「その手順では実際には確認しない条項」を表が受け入れてしまう / 見直す条件: 1つの**記号付き期待結果**が2条項以上を兼ねるようになったとき(そのときは識別子欄が確認単位を一意に指せなくなる)
- [DS-01] 新設した手順が作った資源の**後片付けを各シナリオの末尾の手順として明示する**(E2E-01 手順8-17 / E2E-03 手順7) — 理由: 手順5 以降は `-d ... sleep 60` と `--name` で名前を占有するので、片付けないと**2回目の実行が同名衝突で落ちる** / 見直す条件: 手順が名前付きの資源を作らなくなったとき
- [DS-01] **手順8-18 は後片付け(手順8-17)より後に置き、自分の後片付けを自分で持つ** — 理由: この手順だけが **Docker 側を意図的に壊した状態**(一時コンテナを起動できない)を要し、その状態では他のどの部分手順も実行できない。途中に置くと以降の手順の前提を壊し、末尾の共通後片付けに寄せると壊した状態のまま後片付けを走らせることになる。**既存の手順番号を動かさない**ためにも末尾への追加が要る(`docs/pendings.md` P-006 と `03-impl/tests/cli-logout.md` が手順8-15・8-16 を名指している)/ 見直す条件: 共有ボリュームの中身を一時コンテナ以外の手段で読む実装へ変わり、壊す対象が Docker でなくなったとき
- [DS-01] このホストで実行できない部分手順(2セッション同時・`reset` の破壊・macOS)を**手順から外さず、未実施として記録する形にする** — 理由: 手順を消すと「確認しなくてよい」と読めるが、実際には専有環境があれば確認できる。未実施の理由と代替として確認したことは、本ファイルの「未検証(テスト未実装)の全件」と `docs/pendings.md` に残す / 見直す条件: 専有できるホストで一通り流し切ったとき(そのときは未実施の記録を消す)
- [DS-01] **`FR-env-03-24` の確認を手順8-15(`reset`)より後の部分手順16 に置く** — 理由: この確認は `logout` で Claude コンテナを消してから `stop` を走らせるので、**先に置くと以降の部分手順が使うセッション `aaa` が失われる**。手順8-15 までの前提を壊さない位置は末尾しかない / 見直す条件: `logout` が Claude コンテナを削除しなくなったとき(そのときは順序の制約が消える)
