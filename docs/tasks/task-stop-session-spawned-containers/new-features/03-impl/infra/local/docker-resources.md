---
target: docs/03-impl/infra/local/docker-resources.md
change: replace
sections:
  - "## リソース一覧"
  - "## ネットワーク"
deletes: []
reason: 'ホストの Docker 上に存在する資源の一覧に、**セッション由来のコンテナとネットワーク**の行が無いため足す(名前は利用者が決めるので固定名を書けず、`所有者ラベル` で識別することを「誰が作るか」欄に書く)。あわせて「ネットワーク」の表に、セッション内から `docker network create` で作られるネットワークの行を足す(compose 既定ネットワークだけが書かれていて、単独作成の経路が無かった)。**この2表は行番号を持たない構成値の表**なので実装前に書ける(行番号つきの事実表を持つ `03-impl/contracts/` とは扱いが違う)。値そのものは `DSN-env-04` と `CTR-cli-container`「管理ラベル」が正であり、ここはローカル環境に何が存在するかの一覧である'
---

## リソース一覧

| リソース | 種別 | 用途 | 誰が作るか |
|---|---|---|---|
| `claude-dev-net` | ネットワーク | Claude コンテナと docker-proxy の通信。**全プロジェクトで共有**(分離しない) | `MODULE-cli-common-ensure-infrastructure` / `MODULE-makefile-network` |
| `claude-dev-auth` | ボリューム | 認証の共有(Claude 直下 / Codex は `codex/` サブディレクトリ) | 同上 / `MODULE-makefile-volumes` |
| `claude-dev-config` | ボリューム | シェル設定の共有 | 同上 |
| `claude-dev-history` | ボリューム | コマンド履歴の永続化 | 同上 |
| `claude-dev-chrome-<name>` | ボリューム | Chrome プロファイル。**コンテナごとに分離**(共有すると同時起動でプロファイルが壊れる) | `MODULE-cli-start` |
| `claude-dev-vm-<name>` | ボリューム | VM モードのゲストディスク | `MODULE-cli-start`(`--vm` 時) |
| `claude-dev-<project>` | コンテナ | プロジェクトごとの Claude コンテナ | `MODULE-cli-start` |
| `claude-dev-docker-proxy` | コンテナ | Docker API の検査プロキシ。**全プロジェクトで共有** | `MODULE-cli-start`(必要時に起動) |
| `fwd-<name>-<port>` | コンテナ | ポート中継(使い捨て) | `MODULE-cli-forward` |
| **(利用者が付けた任意の名前)** | **コンテナ / ネットワーク** | **セッション由来の資源**。Claude コンテナの中から `docker run` / `docker create` / `docker compose up` / `docker network create` で作られたもの。**名前は利用者が決めるので固定名を持たず、ラベル `claude-dev.role=spawned` と `claude-dev.owner-project-dir=<起動ディレクトリの絶対パス>` で識別する**(`DSN-env-04`)。`claude-dev stop` は所有者が一致するものを、`claude-dev reset` は所有者を問わず全部を削除する | 利用者(コンテナ内の docker クライアント)。**ラベルを付けるのは `MODULE-docker-proxy-serve`** |
| **(利用者が付けた任意の名前)** | **ボリューム** | セッション内から作られた名前付きボリューム。**所有者ラベルを付けず、`stop` / `reset` の削除対象にもしない**(利用者のデータであるため。`D0-env-05` 項2) | 利用者(コンテナ内の docker クライアント) |
| `claude-dev-claude` / `claude-dev-claude-vnc` / `claude-dev-docker-proxy` | イメージ | 配布・ビルド成果物 | `MODULE-makefile-build*` / `MODULE-cli-pull` |

## ネットワーク

| 項目 | 値 |
|---|---|
| ネットワーク名 | `claude-dev-net`(共有。プロジェクトごとに分離しない) |
| docker-proxy の公開 | **ホストへ公開しない**。`claude-dev-net` 内でのみ到達可能 |
| Claude コンテナの公開ポート | 既定は無し。ブラウザ確認ありのときだけ noVNC を 6080 番台から動的に割り当てる |
| フォワードのホスト側ポート | 8100〜8999 から動的に割り当てる |
| compose のプロジェクト名 | コンテナ名を compose 互換へ正規化した値に**起動ディレクトリの絶対パスのハッシュ短縮値**を足した `COMPOSE_PROJECT_NAME`(`DSN-env-03`)。共有ネットワークは分離しない |
| **セッション内から作られたネットワーク** | **名前は利用者が決める**(compose 既定ネットワーク `<一意化名>_default` と、`docker network create` で作られる単独のネットワークの両方がある)。**どちらも所有者ラベルを持つ**ので `stop` / `reset` が片付ける。**サブネットは Docker の既定プールから割り当てられる**(本システムは指定しない) |
