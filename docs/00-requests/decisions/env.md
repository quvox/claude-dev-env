---
id: env
version: 1.0.0
updated: 2026-08-03
source:
  - docs/00-requests/request.md
summary: 開発環境・実行環境の構成に関する決定事項(D0-env-*)
keywords: [開発環境, 決定事項]
verified:
  at: 2026-08-03
  version: 1.0.0
  against:
    - doc: docs/00-requests/request.md
      version: 1.2.0
---

# 開発環境の決定事項

## D0-env-01 ブラウザ確認はコンテナ内 Chrome + noVNC で行う

- 区分: 決定
- 決めた日: 2026-07-30
- 内容: ブラウザ確認ありのイメージにコンテナ内 Chrome を統合し、chrome-devtools MCP(localhost 直結)
  で操作する。noVNC のポートは 6080 番台から動的に割り当てる。
- 理由: プロジェクトごとに独立させるため。共有 Chrome コンテナ方式は競合し、中継の段数も増えて複雑だった。
- 却下した案: 共有 Chrome コンテナ + 二段リレー — プロジェクト間で競合する。ホスト側ブラウザへの
  リモート接続 — ホストへ経路を開くことになる。
- 関連: RQ-env-02 / FR-env-11

## D0-env-02 ポートは起動時に公開せず、必要なときだけ開く

- 区分: 決定
- 決めた日: 2026-07-30
- 内容: `claude-dev start` の時点では Web アプリ用のポートマッピングを行わない(ブラウザ確認ありの
  noVNC ポートを除く)。`claude-dev forward` で socat のプロキシコンテナを立て、ホスト側ポートを
  8100 番台から動的に割り当てる。クライアントは SSH の ControlMaster 経由でトンネルを張る。
- 理由: 不要なホスト公開を避け、必要なときだけ最小限を公開する。
- 却下した案: 起動時に固定ポートを公開する — 意図しない公開が常時発生し、プロジェクト間でも衝突する。
- 関連: RQ-env-01 / FR-env-06

## D0-env-03 重い Docker 案件はオプトインの VM モードで扱う

- 区分: 決定
- 決めた日: 2026-07-30
- 内容: `--vm` を指定したときだけ QEMU+virtiofs のゲスト VM を起動し、その中でネイティブ Docker を
  使う。Claude コンテナは privileged にしない。`/workspace` は virtiofs で同一パスに共有し、
  ゲストの Docker は `DOCKER_HOST` 経由で使う。
- 理由: bind/compose/privileged が必要な案件と、軽量な既定構成(DooD + docker-proxy)を両立させる。
- 却下した案: Claude コンテナを privileged にする — 隔離境界を壊す。DinD — 同じく特権が必要。
  常に VM モードにする — 起動が重く、大半の案件では不要。
- 関連: RQ-env-05 / FR-env-08

## D0-env-04 macOS 対応はホスト CLI の差し替えで行う

- 区分: 決定
- 決めた日: 2026-07-30
- 内容: ホスト CLI を `claude-dev-mac` に差し替える(`make install` が `uname -s` で判定して symlink を
  張る)。SSH agent は TCP ブリッジで転送し、ポートは直結(SSH トンネル不要)、VM/KVM は非対応、
  Apple Silicon では arm64 ネイティブで動かす。
- 理由: OS 依存をホスト CLI に閉じ、コンテナ内資産(イメージ・entrypoint・firewall・docker-proxy)を
  OS 非依存に保つ。
- 却下した案: 1つの CLI に OS 分岐を書く — 分岐が全体に散り、片方の変更が他方を壊す。
  コンテナ側で OS 差分を吸収する — コンテナ資産が OS 依存になる。
- 関連: RQ-env-06 / FR-env-10

## D0-env-05 複数プロジェクト同時実行時の compose 分離とライフサイクル

- 区分: 決定
- 決めた日: 2026-07-31
- 内容:
  1. **分離**: 各プロジェクトのコンテナ内 `docker compose` が作るネットワーク名・コンテナ名を
     プロジェクト間で衝突させない。`COMPOSE_PROJECT_NAME` を起動ディレクトリ名で一意化する。
     Claude コンテナと docker-proxy をつなぐ共有ネットワークは共有のまま分離しない。
  2. **ライフサイクル**: compose で作られたコンテナ群を親の Claude コンテナに束ね、
     `claude-dev stop` 時にラベル `com.docker.compose.project=<正規化名>` を持つコンテナと当該
     プロジェクトの compose 既定ネットワークを削除する(名前付きボリュームは保持する)。
     共有ネットワークと docker-proxy は削除しない。VM モードは compose がゲスト内で完結するため対象外。
- 理由: 全プロジェクトが `/workspace` にマウントされるため compose の既定プロジェクト名が
  `workspace` に衝突する。分離は compose 層で足りる。停止後に compose コンテナが孤児として残り
  続けるのを防ぐ一方、ボリューム削除は破壊的なため行わない。共有リソースは他プロジェクトが
  使用中のため残す。
- 却下した案: 共有ネットワークもプロジェクトごとに分ける — 単一の共有 docker-proxy 前提と両立しない。
  停止時に名前付きボリュームも消す — 破壊的で、利用者のデータを失う。
- 関連: FR-env-01 / FR-env-07

## D0-env-06 コンテナ内動作の判定マーカーをイメージに焼き込む

- 区分: 決定
- 決めた日: 2026-07-31
- 内容: 全 Claude コンテナに環境変数 `container=docker` を持たせ、コンテナ内で動作するプロセスが
  「自分がコンテナ内か」を判定できるようにする。名前と値は systemd/podman の標準慣習
  (`container=<runtime>`)に合わせる。イメージのベースステージの `ENV` で付与し、
  ブラウザ確認あり版も継承で同じ値を持つ。
- 理由: 内部プロセス(entrypoint・各スクリプト・オーケストレーター)が環境依存の分岐を安全に
  行えるようにする恒久マーカーが要る。起動時の `-e` 付与は起動経路に依存して漏れうるため、
  イメージ側で常時保証する。
- 却下した案: 起動時に `-e container=docker` を付ける — `docker run` 以外の経路(一時コンテナ等)で
  漏れる。独自の変数名を使う — 外部ツールとの互換を失う。
- 関連: FR-env-01

## D0-env-07 MCP ツールの本格導入

- 区分: 要確認
- 論点: chrome-devtools MCP 以外の MCP ツールをどこまで導入するか。stdio 方式から段階導入する方針は
  あるが、対象と時期は未決。Docker MCP(DinD/ソケット共有)はセキュリティ要件を満たせる場合に限る。
- 選択肢: 当面追加しない / stdio 方式のものだけ追加する / Docker MCP まで含めて検討する
- 誰が・いつまでに: 人間(必要が生じた段階で判断) / 期限なし
- これが決まらないと何が止まるか: 何も止まらない(現状 chrome-devtools MCP のみで要件を満たしている)。
- 関連: FR-env-11
