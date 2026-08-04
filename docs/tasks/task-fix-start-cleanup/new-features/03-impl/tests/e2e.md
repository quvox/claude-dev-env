---
target: docs/03-impl/tests/e2e.md
change: replace
sections:
  - "### E2E-01"
deletes: []
reason: FR-env-01 受入基準12・13(docs/issues/036)の実機確認手順を置く場所が無い。E2E-01(UC-01 = start)の手順に、basename が同じ2ディレクトリでの同時起動の確認を1手順として足す
---

<!-- 変更指示。記法の正は .claude/directions/change-set.md
     ・手順1〜6 は現行のまま。手順7 が追加分である
     ・E2E シナリオ一覧(02-design/system.md の E2E-01〜06)は増やさない
       (E2E-nn は UC-nn と 1:1 で、本件は UC-01 の境界値にあたる)
     ・E2E-01 の行の状態(未検証)は変えない。手順7 が確認するのは
       FR-env-01 受入基準12・13 であり、その状態は tests/cli-start.md 側で「実装済み」になる -->

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
   同名コンテナが稼働中なら手順6 の再接続経路に入って `exit 0` するからである
   (`claude-dev:715`)。衝突が起きるのは**手順6 の稼働判定を通り抜けたあと、手順13 の
   `docker run` に達するまでの数秒の間に同名コンテナが現れたとき**だけなので、
   その窓を意図的に作って確認する。
   1. 専用の空ディレクトリ(例: `/tmp/e2e-x/web`)を作る。同名の `web` コンテナが**無い**ことを
      `docker ps -a --filter name=^web$` で確かめる。
   2. そのディレクトリで `CLAUDE_DEV_NO_ATTACH=1 claude-dev start` を**バックグラウンドで**起動し、
      出力をファイルへ落とす。
   3. 出力に `SSH 鍵が未設定` の行(`claude-dev:167`。手順4 の時点)が現れたら、**すぐに**
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
      `claude-dev start` が**通常どおり成功する**(終了コード 0)こと、もう一度実行すると
      「`web` は実行中。接続します...」の再接続経路に入ること(`FR-env-01` 受入基準4)を確かめる。
   7. 後片付け: `claude-dev stop web` を実行し、`docker volume rm claude-dev-chrome-web` と
      一時ディレクトリを削除する。**`stop` は共有 docker-proxy を止めることがある**ので
      (`docs/issues/045`)、他に稼働中の Claude コンテナがあるときは
      `docker ps --filter name=claude-dev-docker-proxy` で残っていることを確認し、
      消えていたら `claude-dev:418`〜`:426` と同じ `docker run` で作り直す。
   - macOS(`claude-dev-mac`)でも同じ手順を実行する。実行できない場合は
     **未実施であることを記録する**(手順を省いたことを黙って残さない)。
