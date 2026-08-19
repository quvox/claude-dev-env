---
target: docs/03-impl/tests/e2e.md
change: replace
version_bump: minor
sections:
  - "### E2E-01"
  - "## E2Eシナリオ ⇄ テスト対応表"
  - "## テスト設計の判断"
deletes: []
reason: '`FR-env-07-13`(本システムが使う環境変数は、コンテナ内で起動したどのプロセスからも参照できること)の**実機確認手順を作る**。**変更点は3つ**: (1) E2E-01 に**手順9** を足した — tmux の窓で `env` を見る / 非対話シェル(`zsh -c` / `bash -c`)で見る / **新しく作った窓**で見る / その窓で `docker ps` が通る / `docker compose` の資源名が `workspace` に落ちない、の5つを確かめる。**不合格の条件を2つ明記した** — `unix:///var/run/docker.sock` を指したまま失敗すること(`FR-env-07-1`)と、compose 名が `workspace-…` になること(`FR-env-07-5`)。これは 2026-08-19 に実機で観測された状態そのものである。(2) E2Eシナリオ ⇄ テスト対応表の E2E-01 行のシナリオ欄に手順9 を足した。(3) テスト設計の判断に `[DS-01]` の開示行を1行足した(手順8 の部分手順にせず末尾に手順9 を立てる理由。**既存の手順番号を1つも動かさない**という、この節に既に在る判断と同じ理由による)。**既存の判断9件はすべて読み直し、いずれも継続と判断した。** 既存の手順は1つも変えていない。**2026-08-19 に範囲を広げた**: 手順9 の題を「本システムが使う環境変数」から「コンテナへ渡した環境変数」へ改め、**手順9-6(env ファイルに書いた組が同じ窓で見えること。`FR-env-14-11` / `AC-08`)と手順9-7(本システムが使う名前が利用者の指定で差し替わらないこと)を足した**。9-6 には「`docker exec` で確かめて済ませないこと」を明記した — **`docker exec` 経由ではコンテナの環境をそのまま継ぐので、tmux の窓が壊れていても合格に見える**。これは 2026-08-19 に実際に起きた誤検出の形である(`docs/issues/107`)'
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
   2. **遊休判定がイメージに依存しないこと**(受入基準9。`docs/histories/2026-08-04-fix-destructive-scope.md` が解消した欠陥の再現):
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
      「管理ラベルが付く前に起動した可能性がある」旨が表示されることを確認する。
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
      あわせて **`logout` が削除に失敗した実行でもラベル無しコンテナの表示を出すこと**
      (`FR-env-03` 受入基準17。決定シート 論点1)を確認する:
      `docker run -d --name legacy-fail --network claude-dev-net busybox sleep 600` でラベル無しの
      稼働中コンテナを立て、共有ボリュームを使用中のコンテナを残したまま `claude-dev logout --yes` を
      実行する。**期待する結果**: 消えなかった資源が列挙されて終了コード 1 になり、**かつ
      `legacy-fail` の名前と認証の書き戻しの警告も表示される**。
      **不合格の条件**: 失敗の列挙だけが出てラベル無しコンテナの名前と警告が出ない
      (**まさに認証が書き戻される状況で警告が消える**)。後片付けは `docker rm -f legacy-fail`。
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
      **さらに (f)**: **終了コード 1 で終わるこの実行でも、`legacy2` の名前と
      「停止中のものは列挙していない」限界が表示される**ことを確認する
      (`FR-env-03` 受入基準17 は表示を削除の成否で条件づけていない)。
      **不合格の条件**: docker-proxy または `claude-dev-net` が消える(残した `legacy2` の中から
      Docker が使えなくなる)/ 「全リセット完了」と表示される /
      **削除に失敗して終了コード 1 になった実行で `legacy2` の名前が表示されない**。
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
      1. **`--volumes` が無いときにボリュームを残すこと**(`FR-env-01-33`):
         上と同じ前提で、`aaa` / `bbb` のそれぞれのコンテナ内で
         `docker volume create vol-a3` / `docker volume create vol-b3` を実行してから
         `claude-dev reset` を実行する。**期待する結果**: **確認プロンプトの一覧に
         ボリュームが現れず**、両方のボリュームが残り、**残したことと「完全な初期化に
         なっていない」旨**が表示される。**不合格の条件**: ボリュームが消える /
         残っているのに何も表示されない。
      2. **`--volumes` があるとき所有者を問わず消すこと**(`FR-env-01-32`):
         続けて `claude-dev reset --volumes` を実行する。**期待する結果**:
         **確認プロンプトの一覧に `vol-a3` と `vol-b3` の両方が種別つきで現れ**、
         `y` で進めると両方が削除される。**不合格の条件**: 一覧に出ないまま消える
         (`FR-env-03` 受入基準14 に反する)/ 片方しか消えない。
      **あわせて VM モードのゲストディスクが削除対象に入ること**(`02-design/logging.md`
      「破壊的操作の削除対象の確認」)を確認する: **`docker volume create claude-dev-vm-aaa` で
      ゲストディスクと同じ名前のボリュームを作り**、`claude-dev reset` を実行する。
      **VM の起動は要らない** — `reset` は名前の接頭辞 `claude-dev-vm-` で列挙するので、
      空のボリュームでも同じ経路に入る。
      **期待する結果**: 確認プロンプトの一覧に `claude-dev-vm-aaa` が現れ、`y` で進めると削除され、
      `docker volume ls` から消える。**不合格の条件**: 一覧に出ない / `reset` の後も残る。
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
      **期待する結果 (a)**: **「削除対象がありません」を表示して 0 で終わらない。**
      共有ボリュームの状態を確かめられなかった旨が表示され、削除対象の列挙と確認へ進む
      (標準入力が TTY でないので `--yes` が無ければ**終了コード 1 で中止**する —
      受入基準15)。続けて `claude-dev logout --yes` を実行した場合は削除を試み、
      **消去を確認できないので消えなかった資源として列挙し終了コード 1 で終わる**(受入基準18)。
      **このとき共有ボリュームが「削除した資源」の一覧に現れないこと**も確認する
      (消えたことを確認できていない資源を削除済みと表示しないことの確認。経緯は `docs/histories/2026-08-11-fix-logout-records-and-marker.md`)。
      **不合格の条件**: 「削除対象がありません」と表示して**終了コード 0** で終わる
      (共有ボリュームに認証が残っているのに、利用者は消えたと解釈する)。
      **(b) 印は出るが列挙そのものが失敗する状態**(受入基準19 の「空であることを確認できた」の
      3条件のうち、**一時コンテナの終了ステータスが 0** だけが欠ける場合。(a) では印も出ないので
      この条件は確かめられない)。**一時コンテナが起動でき、印を出したうえで `ls` が非0で終わる**
      イメージへ差し替える:
      ```
      docker tag claude-dev-claude claude-dev-claude.e2e-backup
      printf 'FROM claude-dev-claude.e2e-backup\nUSER root\nRUN mv /bin/ls /bin/ls.orig \
        && printf "#!/bin/sh\\nexit 2\\n" > /bin/ls && chmod +x /bin/ls\n' \
        | docker build -t claude-dev-claude -f - .
      ```
      (`/auth` の権限を落とす方法は使えない — このイメージの既定ユーザは `root` なので
      `chmod 000` でも `ls` が成功する。実測で確認済み。**満たすべき条件は「`require_setup` が通る」
      「印が出る」「列挙が非0で終わる」の3つ**であり、同じ状態を作れる別の手段でもよい。)
      この状態で、共有ボリュームに認証を置いたまま `claude-dev logout < /dev/null` を実行する。
      **期待する結果 (b)**: (a) と同じ — **「削除対象がありません」を表示して 0 で終わらず**、
      確かめられなかった旨を表示して確認へ進み、非 TTY なので終了コード 1 で中止する。
      **不合格の条件**: 終了コード 0 で「削除対象がありません」と表示する
      (= 印だけを見て終了ステータスを見ていない。`MODULE-cli-logout` 判断15 が委任 DS-02 のもとで
      閉じたはずの経路である)。
      続けて**同じ壊れた状態で `claude-dev logout --yes`** を実行する(手順10 の側の確認)。
      **期待する結果**: 消去のあとの列挙も非0で終わるので、**共有ボリュームを「消えなかった資源」として
      列挙し、「削除した資源」には出さず、終了コード 1** で終わる。
      **不合格の条件**: 「認証情報を削除しました」と表示する / 共有ボリュームが「削除した資源」に
      現れる(= 印が出た直後に列挙が失敗した場合を、消去に成功して空になった場合と読み替えている)。
      **(c) 管理ラベル付きコンテナの集合を引けない状態**(`FR-env-03` 受入基準19・18 /
      経緯は `docs/histories/2026-08-11-fix-logout-records-and-marker.md`)。**イメージは元に戻してから**((a)(b) の後片付けを先に済ませる)、
      `docker ps` の問い合わせだけが失敗する状態を作る。**満たすべき条件は
      「共有ボリュームの検査は成功する」かつ「管理ラベル付きコンテナの列挙が非0で終わる」の2つ**である
      (前者が失敗すると (a) の経路で止まり、(c) を確かめられない。**daemon を止める方法は使えない** —
      両方が失敗する)。**`docker` を包む実行ファイルを PATH の先頭に置いて、その1つの問い合わせだけを
      失敗させる**:
      ```
      mkdir -p /tmp/e2e-shim
      cat > /tmp/e2e-shim/docker <<'SH'
      #!/bin/sh
      # 管理ラベル付きコンテナの列挙だけを失敗させ、それ以外は本物へ渡す
      for a in "$@"; do
        case "$a" in label=claude-dev.managed=1) exit 1 ;; esac
      done
      exec /usr/bin/docker "$@"
      SH
      chmod +x /tmp/e2e-shim/docker
      PATH=/tmp/e2e-shim:$PATH claude-dev logout --yes
      ```
      (`/usr/bin/docker` は `command -v docker` で確かめた実体のパスに置き換える。
      同じ状態を作れる別の手段でもよい。)
      この状態で `claude-dev logout --yes` を実行する。
      **期待する結果 (c)**: **「削除対象がありません」を表示して 0 で終わらない。**
      集合を引けなかった旨が表示され、**引けなかったことが「消えなかった資源」として列挙されて
      終了コード 1** で終わる。**不合格の条件**: 終了コード 0 で終わる / 引けなかったことが
      どこにも出ない(= 0件と同一視している)。
      **後片付け**: (a) と (b) と (c) のいずれを実行した場合も
      `docker tag claude-dev-claude.e2e-backup claude-dev-claude` で元へ戻し、
      `docker rmi claude-dev-claude.e2e-backup` と `docker rmi busybox`(他の手順で使っていなければ)
      を実行する。そのうえで `claude-dev logout --yes` を実行して共有ボリュームを実際に空にする。
   19. **`/auth` に印と同名のファイルがあっても「空」と判定しないこと**
      (`FR-env-03` 受入基準19・18。経緯は `docs/histories/2026-08-11-fix-logout-records-and-marker.md`)。**この手順は壊れていない環境で行う**
      (一時コンテナが正常に起動し、印を出し、列挙も成功したうえで、中身の1件が印と同名であることを見る。
      手順8-18 の後片付けが済んだ状態から始める)。
      **前提**: 管理ラベルを持つコンテナを1つも動かさず、カレントディレクトリに認証コピーも置かない。
      共有ボリュームに**印と同名のファイルだけ**を置く:
      `docker run --rm -v claude-dev-auth:/auth --entrypoint bash claude-dev-claude
      -c 'rm -rf /auth/* /auth/.[!.]*; touch /auth/__CLAUDE_DEV_AUTH_LISTED__'`。
      この状態で `claude-dev logout < /dev/null` を実行する。
      **期待する結果**: **「削除対象がありません」を表示して 0 で終わらない**
      (共有ボリュームは空ではないので削除対象があり、非 TTY で `--yes` が無いため終了コード 1 で中止する
      — 受入基準15)。続けて `claude-dev logout --yes` を実行すると、そのファイルが削除され、
      削除結果に共有ボリュームが「削除した資源」として現れて終了コード 0 で終わる。
      **不合格の条件**: 「削除対象がありません」と表示して**終了コード 0** で終わる
      (= 印と同名の行を印と読み替えている。**認証が残っていても同じことが起きる**)。
      **後片付け**: 上の `--yes` を実行しない場合は
      `docker run --rm -v claude-dev-auth:/auth --entrypoint bash claude-dev-claude
      -c 'rm -f /auth/__CLAUDE_DEV_AUTH_LISTED__'` を実行する。
   20. **ホスト側から指定された SSH agent 中継ポートが受理できない値のとき**(`FR-env-04-8`。
      **macOS 版だけの経路**): macOS の実行機で、空のディレクトリに移動し
      `CLAUDE_DEV_SSH_BRIDGE_PORT=0 claude-dev start` を実行する(`70000` / `abc` でも同じ)。
      **期待する結果**: (a) 受理できない値であることと受理する範囲(1〜65535)が表示される、
      (b) **「SSH agent 転送」が有効であるかのような表示が出ない**、(c) コンテナは起動する
      (終了コードは成功した起動と同じ)、(d) コンテナ内で `ssh-add -l` が鍵を返さない。
      **不合格の条件**: 転送が有効であるかのように表示される / 起動が中止される。
      後片付け: `claude-dev stop` と `docker volume rm claude-dev-chrome-<name>`。
      **Linux 版にはこの経路が無い**(agent の転送はソケットのマウントで行う)ので実施しない。
   21. **セッションが作った名前付きボリュームの片付け**(`FR-env-01-28`〜`-31`)。
      **前提**: 使い捨てのディレクトリ `vol-a` で `claude-dev start` し、その中で
      `services` が名前付きボリュームを1つ使う compose ファイルを書いて `docker compose up -d` する。
      ホスト側で `docker volume ls --filter label=claude-dev.role=spawned` に
      そのボリュームが現れることを確認する(現れなければ所有者ラベルの注入が効いていない)。
      1. **`--volumes` を付けずに** `claude-dev stop <name>` を実行する。
         **期待する結果**: コンテナとネットワークは消え、**ボリュームは残る**。出力に
         残っているボリュームの**名前**と**削除する方法**が現れる。
         **不合格の条件**: ボリュームが消える / 残っているのに何も表示されない。
      2. 続けて `claude-dev start` → `docker compose up -d` → `claude-dev stop <name> --volumes` を実行する。
         **期待する結果**: ボリュームが消え、削除した資源の列挙に**種別「ボリューム」つきで**現れる。
         `docker volume ls` にそのボリュームが無い。
         **不合格の条件**: 残る / 種別が付かない / 他のセッションのボリュームまで消える
         (別ディレクトリ `vol-b` で同じ compose を上げておき、そちらが無傷であることを確認する)。
      3. **対象が0件のとき**: ボリュームを作らないセッションで `claude-dev stop <name>` を実行する。
         **期待する結果**: ボリュームに関する表示が**1行も出ない**。
      4. **起動元ディレクトリを読み取れないとき**: 管理ラベルを持たないコンテナを
         `docker run -d --name spawn-nolabel --network claude-dev-net claude-dev-claude sleep 600` で
         作り、`claude-dev stop spawn-nolabel` を実行する。
         **期待する結果**: ボリュームの列挙も削除も行わず、片付けを行わなかった旨が表示される。
      5. **名前無しのボリューム(匿名ボリューム)も消えること**(`FR-env-01-28`)。
         **匿名ボリュームは紐づくコンテナの削除でしか消えない**ので、**2回の実行それぞれで
         匿名ボリュームを作り直す**(1回目で `anon-a` が消えると、その匿名ボリュームは
         どのコンテナにも紐づかなくなり、後から `--volumes` を付けても消えない)。
         - **1回目**: `claude-dev start` の中で `docker run -d --name anon-a -v /data busybox sleep 600`
           を実行し、ホスト側で `docker inspect anon-a --format '{{range .Mounts}}{{.Name}}{{end}}'` で
           自動生成された名前を控える。**`--volumes` を付けずに** `claude-dev stop <name>` する。
           **期待する結果**: 控えた匿名ボリュームは**残る**。
         - **2回目**: 再び `claude-dev start` して同じ `docker run` を実行し、**新しく**
           自動生成された名前を控えてから `claude-dev stop <name> --volumes` する。
           **期待する結果**: 控えた名前が `docker volume ls` に**無い**。
         **どちらの実行でも共通の期待**: 匿名ボリュームの名前が「削除しました」「残っています」の
         どちらの列挙にも**現れない**(`FR-env-01-29`)。
         **後片付け**: 1回目で残した匿名ボリュームを `docker volume rm` で消す。
         **不合格の条件**: `--volumes` 無しで消える / 付けても残る / 自動生成の名前が列挙に出る。
      **後片付け**: `docker volume ls --filter label=claude-dev.role=spawned` が空になるまで
      `docker volume rm` する。`vol-b` 側は `claude-dev stop <name> --volumes`。
   22. **存在しなかった資源を「削除できなかった」と表示しないこと**(`FR-env-01-34`)。
      **前提**: 使い捨てのディレクトリで `claude-dev start` し、**compose 既定ネットワークを
      使わない構成**(`services` が自前のネットワークだけを `networks:` で宣言する compose ファイル)で
      `docker compose up -d` する。この構成では `<一意化名>_default` は**作られない**。
      `claude-dev stop <name>` を実行する。
      **期待する結果**: 出力に「削除できませんでした」の行が**1行も出ない**。
      作られたコンテナと自前のネットワークは「削除しました」の列挙に現れる。
      **不合格の条件**: `<一意化名>_default` が「削除できませんでした」として現れる
      (= 存在しなかったことと削除に失敗したことを区別していない。**2026-08-18 に実測で再現した欠陥**)。
   23. **プロジェクトごとの環境変数の受け渡し**(`FR-env-14`)。使い捨てのディレクトリで行う。
      1. `.claude-dev.yaml` に env ファイルの場所を書き、その env ファイルに `E2E_PLAIN=ok` を書いて
         `claude-dev start` する。**期待する結果**: コンテナ内で `printenv E2E_PLAIN` が `ok` を返す。
      2. **別プロジェクトへ漏れないこと**: 別のディレクトリで `claude-dev start` し、
         そのコンテナで `printenv E2E_PLAIN` が何も返さないことを確認する。
      3. **値が出力に現れないこと**: 手順1 の起動時の端末出力と `docker logs <name>` の双方を
         `grep ok` して、**値が1件も現れない**ことを確認する(名前が出るのは構わない)。
      4. **版管理の追跡から外れること**: そのディレクトリを `git init` した状態で
         `git check-ignore -q <env ファイル>` が 0 を返すことを確認する。
      5. **指定が無いとき**: `.claude-dev.yaml` から env ファイルの指定を消して `claude-dev start` する。
         **期待する結果**: 環境変数に関する表示が**1行も出ない**。
      6. **ファイルが無いとき**: 指定は残したまま env ファイルを消して `claude-dev start` する。
         **期待する結果**: 読めなかったことが表示され、**コンテナは起動する**。
      7. **読めない行があるとき**: env ファイルに `これは組ではない` の行を足して `claude-dev start` する。
         **期待する結果**: **何行目**を採用しなかったかが表示され、他の組は渡る。
      8. **予約した名前**: env ファイルに `COMPOSE_PROJECT_NAME=hijacked` と
         `CLAUDE_DEV_VNC=1` を足して `claude-dev start` する。
         **期待する結果**: どちらも採用されず、採用しなかった**名前**が表示される。
         コンテナ内の `printenv COMPOSE_PROJECT_NAME` が `<正規化名>-<ハッシュ6桁>` のままである。
         **不合格の条件**: `hijacked` になっている(= `stop` の片付けが空振りする状態)。
      9. **外を指す指定**: `.claude-dev.yaml` の指定を `../outside.env` にして `claude-dev start` する。
         **期待する結果**: 受理しないことと受理する範囲が表示され、**コンテナは起動する**。
      10. **同じ名前が重なるとき**: env ファイルに `E2E_DUP=1` と `E2E_DUP=2` をこの順で書く。
         **期待する結果**: コンテナ内の `printenv E2E_DUP` が `2` を返し、採用しなかった名前が表示される。
      **後片付け**: `claude-dev stop <name> --volumes` と、使い捨てディレクトリの削除。
9. **コンテナへ渡した環境変数が、tmux の窓の中でも参照できること**
   (`FR-env-07-13` = 本システムが使う名前 / `FR-env-14-11` = 利用者が env ファイルに書いた組)。
   使い捨てのディレクトリで行う。**この手順は `.claude-dev.yaml` に `env_file:` を書いた状態で始める**
   (手順9-6 で使う。書き方は手順8-23 と同じ)。
   1. `claude-dev start` して tmux にアタッチした状態から、**その窓で**
      `env | grep -E '^(DOCKER_HOST|COMPOSE_PROJECT_NAME|NODE_OPTIONS|container|SSH_AUTH_SOCK|CLAUDE_DEV_)'`
      を実行する。**期待する結果**: 固定名4件(`DOCKER_HOST` / `COMPOSE_PROJECT_NAME` /
      `NODE_OPTIONS` / `container`)と、ブラウザ確認ありの構成では `CLAUDE_DEV_VNC=1` が出る。
      ホスト側で SSH agent が動いているときは `SSH_AUTH_SOCK` も出る。
      `COMPOSE_PROJECT_NAME` の値は `<正規化名>-<ハッシュ6桁>` であり `workspace` ではない。
   2. **非対話シェルでも参照できること**: 同じ窓で
      `zsh -c 'echo $DOCKER_HOST'` と `bash -c 'echo $container'` を実行する。
      **期待する結果**: どちらも値を返す(空行ではない)。
   3. **新しく作った窓でも参照できること**: `tmux new-window -d 'sh -c "env > /tmp/e2e-env.txt"'`
      を実行し、`grep -E '^(DOCKER_HOST|COMPOSE_PROJECT_NAME|container)=' /tmp/e2e-env.txt` を見る。
      **期待する結果**: 3件すべてが出る。
   4. **docker がその窓から使えること**: 同じ窓で `docker ps` を実行する。
      **期待する結果**: コンテナ一覧が返る。
      **不合格の条件**: `unix:///var/run/docker.sock` を指したまま失敗する
      (= 検査つきの中継を経由できていない。`FR-env-07-1`)。
   5. **compose 資源が既定名に落ちないこと**: `/workspace/compose-e2e.yml` に
      `services: {e2e: {image: alpine, command: sleep 60}}` を置き、同じ窓で
      `docker compose -f /workspace/compose-e2e.yml up -d` を実行して
      `docker ps --format '{{.Names}}'` を見る。
      **期待する結果**: 名前が `<正規化名>-<ハッシュ6桁>-e2e-1` である。
      **不合格の条件**: `workspace-e2e-1` になっている
      (= 別プロジェクトの同名 compose 資源と衝突する状態。`FR-env-07-5`)。
   6. **env ファイルに書いた組も同じ窓で見えること**(`FR-env-14-11` / `AC-08`)。
      env ファイルに `E2E_PLAIN=ok` と `E2E_QUOTED=it's fine` を書いておき、**tmux の窓で**
      `printenv E2E_PLAIN` と `printenv E2E_QUOTED` を実行する。
      **期待する結果**: それぞれ `ok` と `it's fine` を返す。
      **不合格の条件**: どちらかが空で返る(= `AC-08` の「書いた値がコンテナの中で見えない」に当たる)。
      **`docker exec` で確かめて済ませないこと** — `docker exec` 経由ではコンテナの環境をそのまま継ぐので、
      **tmux の窓が壊れていても合格に見える**(2026-08-19 に実測した誤検出の形そのものである)。
   7. **本システムが使う名前は利用者の指定で差し替わらないこと**(`FR-env-14-8` との組み合わせ)。
      env ファイルに `DOCKER_HOST=hijacked` を足し、`claude-dev stop <name>` してから
      `claude-dev start` し直して、tmux の窓で
      `printenv DOCKER_HOST` を実行する。
      **期待する結果**: 起動時に採用しなかった名前として `DOCKER_HOST` が表示され、
      窓の中の値は中継先(`tcp://claude-dev-docker-proxy:2375`)のままである。
      **不合格の条件**: `hijacked` になっている。
   **後片付け**: `docker compose -f /workspace/compose-e2e.yml down`、`/tmp/e2e-env.txt` と
   `/workspace/compose-e2e.yml` の削除、`claude-dev stop <name> --volumes`、
   Chrome プロファイルのボリューム(`claude-dev-chrome-<name>`)の削除、使い捨てディレクトリの削除。
   - macOS(`claude-dev-mac`)でも同じ手順を実行する。実行できない場合は
     **未実施であることを記録する**(手順を省いたことを黙って残さない)。

## E2Eシナリオ ⇄ テスト対応表

| E2E ID | 対応 UC | シナリオ | テスト識別子 | 状態 |
|---|---|---|---|---|
| E2E-01 | UC-01 | `claude-dev start`(ブラウザ確認あり / `--no-vnc`)→ `/workspace` マウント・認証・ファイアウォール・tmux → `claude` 起動 → 再実行での再接続 → **同名衝突で稼働中のコンテナを失わないこと(手順7)→ 破壊的操作が「自分が作った資源」にだけ効くこと(手順8: 管理ラベル・遊休判定・排他ロック・ラベル無しコンテナの保護・compose 資源の隔離・受理しない名前・プロジェクト配下の認証コピー・確認と非対話時の中止・削除失敗の列挙・**セッション由来の資源の片付け(手順8-14・8-15)・`logout` 後に回収できないこと(手順8-16)**) → **コンテナへ渡した環境変数が tmux の窓の中でも参照できること(手順9)**** | 手順のみ(下記「実機確認の手順」E2E-01) | 未検証(テスト未実装) |
| E2E-02 | UC-02 | `claude-dev forward` → 8100 番台の割当と SSH トンネル → クライアントのブラウザで表示 → `claude-dev ports` で確認 | 手順のみ(同 E2E-02) | 未検証(テスト未実装) |
| E2E-03 | UC-03 | コンテナ内で危険な `docker run` → 拒否 / `/workspace` bind の許可 / 拒否条件に当たらない要求の透過 / **作られたコンテナとネットワークに所有者ラベルが付くこと** | 手順のみ(同 E2E-03)。判定ロジックは `cd docker-proxy && go test ./...` が単体で検証済み。**条項ごとに単体でどこまで検証済みかは `03-impl/tests/docker-proxy.md` が正である** | 未検証(テスト未実装) |
| E2E-06 | UC-06 | `claude-dev login-codex` → デバイス認証 → 別プロジェクトで `start` → 再ログイン不要で `codex` が起動し、シェルコマンドが成功して `/workspace` を読み書きできる。landlock の疎通確認が通り、読み取り専用の明示指定で読み取りが成功する | `scripts/e2e6-codex.sh`(実機で実行する検証スクリプト。自動テストランナーからは呼ばれない) | 未検証(テスト未実装) |

## テスト設計の判断

<!-- 実機確認の手順そのものをどう組んだかの判断。何を確認するか(受入基準)は 01 が正である。 -->

- [DS-01] セッション由来の資源の確認を **`stop` 側(手順8-14)と `reset` 側(手順8-15)に分ける** — 理由: `reset` は所有者を問わず消すので、`stop` が「別セッションの資源を消さないこと」を確かめるために立てた2つ目のセッションを、同じ手順の中では生かしておけない / 見直す条件: `reset` の削除範囲が所有者付きへ変わり、同じ前提で連続して流せるようになったとき
- [DS-01] 手順8-14 を**7つの部分手順に割り**、対応表の識別子が**実際に確認する単位**を名指す形にする。1回のコマンド実行で複数の条項を観測できる部分手順は分割せず、**記号付きの期待結果((a)(b)…)を識別子に添えて条項ごとに分ける**(部分手順3 は 1 回の `claude-dev stop aaa` で `FR-env-01-22` を (a)(c) で、`FR-env-01-26` を (b) で観測するため、これを2つの部分手順に割ると同じコマンドを2度流すだけになる) — 理由: `03-impl/tests/cli-stop.md` の識別子欄が確認単位を名指すので、粒度が粗いと「その手順では実際には確認しない条項」を表が受け入れてしまう / 見直す条件: 1つの**記号付き期待結果**が2条項以上を兼ねるようになったとき(そのときは識別子欄が確認単位を一意に指せなくなる)
- [DS-01] 新設した手順が作った資源の**後片付けを各シナリオの末尾の手順として明示する**(E2E-01 手順8-17 / E2E-03 手順7) — 理由: 手順5 以降は `-d ... sleep 60` と `--name` で名前を占有するので、片付けないと**2回目の実行が同名衝突で落ちる** / 見直す条件: 手順が名前付きの資源を作らなくなったとき
- [DS-01] **手順8-19(印と同名のファイル)は手順8-18 の後片付けが済んだ状態から始める** — 理由: この確認は**壊れていない環境でしか成立しない**(一時コンテナが起動し、印を出し、列挙も成功したうえで、中身の1件が印と同名であることを見る)。手順8-18 は Docker 側を壊した状態を要するので、混ぜると前提が両立しない / 見直す条件: 共有ボリュームの中身を一時コンテナ以外の手段で読む実装へ変わったとき
- [DS-01] **手順8-18 は後片付け(手順8-17)より後に置き、自分の後片付けを自分で持つ** — 理由: この手順だけが **Docker 側を意図的に壊した状態**(一時コンテナを起動できない)を要し、その状態では他のどの部分手順も実行できない。途中に置くと以降の手順の前提を壊し、末尾の共通後片付けに寄せると壊した状態のまま後片付けを走らせることになる。**既存の手順番号を動かさない**ためにも末尾への追加が要る(`docs/pendings.md` P-006 と `03-impl/tests/cli-logout.md` が手順8-15・8-16 を名指している)/ 見直す条件: 共有ボリュームの中身を一時コンテナ以外の手段で読む実装へ変わり、壊す対象が Docker でなくなったとき
- [DS-01] このホストで実行できない部分手順(2セッション同時・`reset` の破壊・macOS)を**手順から外さず、未実施として記録する形にする** — 理由: 手順を消すと「確認しなくてよい」と読めるが、実際には専有環境があれば確認できる。未実施の理由と代替として確認したことは、本ファイルの「未検証(テスト未実装)の全件」と `docs/pendings.md` に残す / 見直す条件: 専有できるホストで一通り流し切ったとき(そのときは未実施の記録を消す)
- [DS-01] **`FR-env-03-24` の確認を手順8-15(`reset`)より後の部分手順16 に置く** — 理由: この確認は `logout` で Claude コンテナを消してから `stop` を走らせるので、**先に置くと以降の部分手順が使うセッション `aaa` が失われる**。手順8-15 までの前提を壊さない位置は末尾しかない / 見直す条件: `logout` が Claude コンテナを削除しなくなったとき(そのときは順序の制約が消える)
- [DS-01] **`reset` 側の名前付きボリュームの確認を手順8-15 の中の部分手順(8-15-1・8-15-2)として置き、新しい番号の手順を立てない** — 理由: `reset` は他の資源と一続きに流さないと前提(所有者の違う資源が同時に在ること)を作れない。番号を分けると同じ前提を2回作ることになる / 見直す条件: `reset` の確認を専有ホスト以外でも流せるようになったとき
- [DS-01] **手順8-21・8-22・8-23 を手順8 の末尾へ足し、既存の部分手順の番号を動かさない** — 理由: `03-impl/tests/*.md` の対応表と `docs/pendings.md` が既存の部分手順の番号を外から参照しており、番号を詰めると参照が**解決したまま別の手順を指す**(条項 ID を動かさないのと同じ理由)/ 見直す条件: 部分手順の番号を参照する外部の表が無くなったとき
- [DS-01] **`FR-env-07-13` の確認を手順8 の部分手順にせず、新しい手順9 として末尾に足す** — 理由: 手順8 は「破壊的操作が自分が作った資源にだけ効くこと」を通しで確かめる一続きの手順で、セッション `aaa` を作って壊す前提を共有している。環境変数の到達確認はその前提を要さず、混ぜると手順8 の前提が1つ増えるだけである。**末尾に足すので既存の手順番号は1つも動かない**(`03-impl/tests/*.md` の対応表と `docs/pendings.md` が既存番号を外から参照しているため。同じ理由の判断がこの節に既に在る)/ 見直す条件: 手順8 が環境変数を前提に置くようになったとき、または手順9 が破壊的操作の検証を含むようになったとき(後片付けの `stop` は全手順が使うので該当しない)
