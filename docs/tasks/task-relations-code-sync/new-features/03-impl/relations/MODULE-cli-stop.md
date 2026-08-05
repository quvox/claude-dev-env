---
target: docs/03-impl/relations/MODULE-cli-stop.md
change: replace
sections:
  - "## 実装上の判断"
  - "## 目的"
  - "## 処理の流れ"
  - "## 既知の制限"
deletes: []
reason: 判断4 に変更相対の言い回し「本変更前に起動した」が残っており、参照先の「本変更」が SSOT に存在しない(docs/issues/056 #5。CLAUDE.md §1)
id: MODULE-cli-stop
module: MOD-cli-stop
kind: tool
sync: sync
impl: claude-dev::main#stop, claude-dev-mac::main#stop
callers: なし
callees: MODULE-cli-common-container-exists, MODULE-cli-common-container-name, MODULE-cli-common-dev-agent-path, MODULE-cli-common-is-running, MODULE-cli-common-lock
contracts: CTR-cli-container
design: DSN-mod-01, DSN-mod-02, DSN-env-01, DSN-env-02, DSN-env-03
requirements: FR-env-01, FR-env-07
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-05
summary: セッションを停止し、遊休なら docker-proxy と ssh ブリッジも止める
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。frontmatter は `updated` の日付以外変更なし。
     変更点は判断4 の1語と判断8 の1句(2026-08-05 /doc-check(task) の自動修正。独立レンズ Codex docs が
     検出した「**現行も**同じ変換を二箇所に書いているが」という変更相対の言い回しを、
     「同じ変換が二箇所にあると…」という現状記述へ言い換えた。意味は変えていない)。

     残す判断: 判断の番号が 8 → 13 → 9 の順で並んでいるのは現行 SSOT のままである
     (`docs/03-impl/relations/MODULE-cli-stop.md:211`〜`:213`)。番号は他文書から参照されうるため
     並べ替えも振り直しもしない(重大度「低」として /doc-check のレポートに記録した)。 -->

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 名前付きボリューム・共有ネットワーク `claude-dev-net` は消さない(`docker compose down` 相当にとどめる) | D0-scope-02 |
| 2 | macOS の専用 ssh-agent は停止しない(鍵を読み込んだままにして、次の `start` で鍵の選択と読み込みをやり直さずに済ませる。停止するのはブリッジのみ) | D0-scope-03 |
| 3 | 中継コンテナ・compose コンテナ・compose ネットワークの削除は失敗を握って後続を続ける(片付けの途中で止まると、より中途半端な状態が残るため)。**`stop` は `D0-env-08` 項5 の対象外**であり、失敗を列挙して非0で終わるのは `logout` / `reset` だけである(`FR-env-01` 受入基準11 が「続行する」と定めている)。**ただし本体コンテナと docker-proxy の削除だけは握らない**: 本体は以降の片付けの前提であり、docker-proxy は最後の手順なので途中で止まることにならない(どちらも `docker rm -f` に `\|\| true` を付けていない) | D0-scope-02 |
| 4 | 遊休判定を**`claude-dev-net` への接続**で行う。ラベルでもイメージでもないのは、どちらも「数え落とす」方向に外すためである(ラベル: 管理ラベルを持たずに起動された既存コンテナが数え落とされる / イメージ: `latest` が動くと取りこぼす)。ネットワークへの接続は起動オプションの必須項目なので、起動経路によらず必ず成立する | D0-env-10(制約「共有資源を止めてよいかの判定を管理ラベルの有無に依存させない」) |
| 5 | 中継コンテナと docker-proxy の識別を**名前**(接頭辞 `fwd-` / 固定名 `claude-dev-docker-proxy`)で行い、ラベルを付けない。これらは本システムが決めた名前を持つので所有権が名前から読み取れ、ラベルを足しても情報が増えない一方、**既存分がラベルを持たないという移行問題を作り込むことになる** | D0-env-10 |
| 6 | 共有資源単位のロックを**遊休判定の直前**に取り、判定から削除までを同一区間に入れる。手順1〜8 を含めて取ると、別プロジェクトの `stop` が自プロジェクトの後片付けを待つことになり `NFR-scale-01` を損なうため。**この保護が成立するのは `start` が同じキーを `docker run` の完了まで保持するからである**(`MODULE-cli-start` 判断9)。`start` が認証コピーの直後に離すと、判定の直後に作られた docker-proxy を消す競合が残る | D0-env-09 |
| 7 | 共有資源単位のロックが取れなかったときは**全体を失敗させず**、docker-proxy に触れずに続行する。本体コンテナは既に削除済みで、docker-proxy が残ることの害は「使われていない proxy が残る」だけであり、次回の `stop` が回収する | D0-env-09 |
| 8 | compose プロジェクト名の**一意化名を再計算する関数を1つに集約し、`start` と `stop` の双方が同じ関数を呼ぶ**(同じ変換が二箇所にあると、ハッシュを含む名前では食い違いの被害が大きい)。ハッシュの計算は Linux が `sha256sum`、macOS が `shasum -a 256` で**同じ値**になることを確かめる。ハッシュ源は `printf '%s'`(改行を付けない)で与え、両 OS で同じ関数を通す | D0-scope-03(同じ成否・同じ出力)/ `DSN-env-03` |
| 13 | **正規化に小文字化を含める**(`tr '[:upper:]' '[:lower:]'` → `sed 's/[^a-z0-9_-]/-/g'`)。契約の「起動ディレクトリ名を**小文字化してから** `[a-z0-9_-]` 以外を置換」をそのまま1関数にしたものである。`start` の `NAME` は `MODULE-cli-common-container-name` が既に小文字化しているので値は変わらないが、`stop <name>` は利用者が大文字を渡せる唯一の経路であり、小文字化を落とすと `start` と `stop` で違う値になりうる | D0-scope-02(観測できる振る舞いを変えない)/ 契約「compose 資源の識別」 |
| 9 | 旧い名前の compose 資源を**削除せず表示だけ**にする。旧名は別ディレクトリと衝突しうるので、消すと `docs/issues/024` の欠陥がそのまま残る。表示は「その場で気づける」観測点を満たす | `FR-env-01` 受入基準20 / `D0-env-08` 項7 |
| 10 | **管理ラベルの読み取りを本体削除より前に置く**(手順4)。`stop` の入力は `NAME` だけで、compose 一意化名のハッシュ源(起動ディレクトリの絶対パス)は **`claude-dev.project-dir` ラベルにしか無い**。本体を先に消すとラベルも消えるため、順序が逆だと `stop <name>` を別のディレクトリから実行したときに compose を片付けられない。ラベルが無い場合は**推測せず案内に倒す** | D0-env-10(ラベルの用途)/ `FR-env-01` 受入基準6 |
| 11 | 遊休判定の結果で削除するのは **docker-proxy だけ**とし、共有ネットワーク `claude-dev-net` は遊休でも削除しない(`D0-env-05` 項2 / `FR-env-01` 受入基準6。`stop` は「`docker compose down` 相当」に留める)。`claude-dev-net` を消すのは `reset` だけである | `D0-env-05` 項2 |
| 12 | Linux 版・macOS 版の**両方に同じ形で**入れる(同じサブコマンドの成否・出力を OS で変えないため) | D0-scope-03 |

## 目的

1つのプロジェクトの Claude セッションと、そのセッションから作られた副産物
(ポートフォワード用コンテナ・compose 資源・共有 docker-proxy)を片付ける
(FR-env-01・FR-env-07)。**集合として列挙して消す資源は「自分が作った資源」に限る**
(`D0-env-08` 項1):
**本体コンテナだけは例外で、利用者が `<name>` で1つを指した削除なので管理ラベルの有無を問わない**
(`D0-env-08` 項1 の但し書き / `FR-env-01` 受入基準15。ラベルが無ければその旨を表示する)。
本体は名前で1件を指して削除し、`fwd-<name>-*` は固定接頭辞で識別し、共有 docker-proxy は
`claude-dev-net` への接続で遊休を判定してから削除する(契約 `CTR-cli-container`)。
compose 資源にはラベルが届かない(compose が Claude コンテナの中で作るため)ので、
**compose プロジェクト名そのものを一意化した名前**で識別する(`DSN-env-03`)。
**残る限界は「一意化名が導入される前に作られた compose 資源」だけ**で、これは旧い名前を持つため対象に
含めず、手動で片付ける方法を表示する(`FR-env-01` 受入基準20)。

## 処理の流れ

1. `MODULE-cli-common-container-name` で対象コンテナ名を決める(引数 `NAME` 優先)。
   **`NAME` が明示されている場合、`[A-Za-z0-9._-]` 以外の文字を含むなら何も削除せず、受理できない
   文字を含むことを表示して終了コード 1 で終わる**(`FR-env-01` 受入基準18。この名前が次の手順で
   ロックキー=パス要素になるため)。省略時の名前は既に `[a-z0-9._-]` へ正規化されている。
2. `MODULE-cli-common-lock` で**プロジェクト単位**のロック(キー = 手順1 のコンテナ名、操作名 `stop`)を
   取る。取得できなければ**削除を一切行わずに**非0で終わる(`FR-env-01` 受入基準16)。
3. `fwd-<name>-*` の中継コンテナを片付ける。**中継コンテナは本システムが決めた固定接頭辞 `fwd-` と
   対象コンテナ名から名前が一意に決まるため、管理ラベルではなく名前で識別する**
   (契約 `CTR-cli-container` の「識別の手段は資源ごとに違う」)。既存分にラベルが無いという
   移行問題は起きない。
4. **本体コンテナを削除する前に**、`docker inspect` で管理ラベルを読む(**この順序は固定**。
   削除するとラベルが失われ、以降 compose の一意化名を再現できない。契約
   `CTR-cli-container` の「compose 資源の識別」)。
   - `claude-dev.managed` の有無 → 手順5 の表示に使う。
   - **`claude-dev.project-dir` の値 → 手順6 の compose 一意化名のハッシュ源**にする。
   - **ラベルが無い、または対象コンテナが存在しない場合は `PROJECT_DIR` を得られないので、
     手順6・7 の compose 片付けを行わず、手動手順を案内する**(推測でハッシュを作ると
     別ディレクトリを巻き込む)。
5. `MODULE-cli-common-container-exists` で本体コンテナの存在を確認し、`docker rm -f "$NAME"` する。
   **本体は名前で1件を指した削除なので、管理ラベルの有無を問わず削除する**(規則B)。
   ラベルを持たない場合はその旨を表示する(`FR-env-01` 受入基準15)。
6. 当該コンテナ内から起動された compose コンテナ群をラベル
   `com.docker.compose.project=<一意化名>` で特定して `docker rm -f` する。**`<一意化名>` は
   `<正規化NAME>-<手順4 で読んだ `claude-dev.project-dir` の SHA-256 先頭6桁>`**(契約
   `CTR-cli-container` の「compose 資源の識別」。`start` が `COMPOSE_PROJECT_NAME` として渡したのと
   同じ値を、同じ関数で再計算する)。**旧い名前(ハッシュ無しの `<正規化NAME>`)を対象に含めてはならない**
   (別ディレクトリと衝突しうる。`docs/issues/024`)。
   ラベル `com.docker.compose.project=<正規化NAME>` のコンテナが**存在する場合は、削除せずに**
   「一意化名が導入される前に作られた compose 資源が残っている可能性」と確認・手動削除の方法
   (`docker ps --filter label=com.docker.compose.project=<正規化NAME>` → `docker compose down`)を
   表示する(`FR-env-01` 受入基準20)。
7. 当該プロジェクトの compose デフォルトネットワーク `<一意化名>_default` が残っていれば
   `docker network rm` する(`docker compose down` 相当。名前付きボリューム・共有
   `claude-dev-net`・docker-proxy は残す)。**他から使用中で削除できない場合は続行する**
   (`FR-env-01` 受入基準11。`D0-env-08` 項5 が明示する例外)。
8. **macOS 版のみ**: `stop_ssh_bridge <NAME>` で当該プロジェクトの socat ブリッジを停止する
   (専用 ssh-agent は鍵を保持するため残す)。`MODULE-cli-common-dev-agent-path` で
   `.bridge.pid` / `.bridge.port` の位置を得る。
9. `MODULE-cli-common-lock` で**共有資源単位**のロック(キー `shared`、操作名 `stop`)を取り、
   `stop_proxy_if_idle`(本機能に畳み込み)を実行する。**判定と削除を同一のロック区間の中で行う**
   ことで、他プロジェクトの `start` が docker-proxy を作った直後に消す競合を防ぐ。
   取得できなければ docker-proxy には触れず、その旨を表示する(手順3〜8 は済んでいるので
   全体は失敗させない)。
10. 遊休判定は次のとおり行う(`FR-env-01` 受入基準9 / 契約の「遊休判定」)。
   - **`claude-dev-net` に接続している稼働中コンテナ**を列挙する
     (`docker network inspect claude-dev-net` の接続コンテナと `docker ps` の稼働集合の積)。
   - そこから**名前が `claude-dev-docker-proxy` のもの**と**名前が `fwd-` で始まるもの**を除く
     (どちらも本システムが決めた固定名・固定接頭辞なので、ラベルの有無に依存しない)。
   - 残りが**0件のときだけ** `MODULE-cli-common-is-running` で docker-proxy の稼働を確かめ、
     `docker rm -f` する。**共有ネットワーク `claude-dev-net` は削除しない**(`stop` は
     `D0-env-05` 項2 のとおり共有ネットワークを残す。削除するのは `reset` だけである)。1件以上残るなら docker-proxy を残し、**残した理由(稼働中のコンテナ名)を
     表示する**。
   - **`docker ps --filter ancestor=<イメージ>` を判定に使わない。** イメージを再ビルド・再取得すると
     それ以前に起動したコンテナを数え落とし、稼働中の他プロジェクトから Docker が使えなくなる
     (`docs/issues/045` で実機観測)。
   - **問い合わせが失敗したら(ネットワークが存在しない / `docker` が応答しない)、遊休でないと
     判定して docker-proxy を残す**。判定できなかったことを表示する(安全側へ倒す。
     契約の「エラーケース」)。
11. 取得したロックを解放する(`trap` により異常終了時も解放される)。

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **一意化名が導入される前に作られた compose 資源は旧い名前(ハッシュ無し)を持つため片付けられない** | 移行期のあいだ、旧い compose 資源は手動で削除する必要がある(表示で気づける) | なし(閾値の外: 表示で気づける。**根本の欠陥=旧 `docs/issues/024` は解消済み**で、経緯は `docs/histories/2026-08-04-fix-destructive-scope.md`。これは移行期の残り) |
| **compose 一意化名のハッシュ衝突を検出しない** | 異なる絶対パスの先頭6桁が一致すると、一方の `stop` が他方の compose 資源を削除しうる(`024` と同じ事象が、確率は桁違いに低い形で残る) | `docs/pendings.md` **P-005**(2026-08-04 に人間が受容) |
| **`claude-dev.project-dir` ラベルを持たない対象では compose を片付けられない** | 管理ラベルが付く前に起動されたコンテナを `stop` すると compose 資源が残る | なし(閾値の外: 残ることと手動手順を**表示する**ので気づける) |
| **遊休判定が `claude-dev-net` への接続で行われるため、利用者がコンテナ内から `docker compose` で起動した資源も「稼働中」に数える** | docker-proxy が回収されにくくなる。**過剰に数える=消さない側**なので `FR-env-01` 受入基準9 は破らない | なし(2026-08-04 の決定シート #1 で人間が案A=現状のままと裁定) |
| **停止中のコンテナは `claude-dev-net` の接続情報に現れない** | 停止中のコンテナがあっても遊休と判定する | なし(閾値の外: 停止中のコンテナは Docker を使っておらず、proxy を消しても壊れない) |
| **共有ネットワーク `claude-dev-net` が存在しないと、遊休判定は「問い合わせ失敗」になる** | ネットワークを手で消したあとは docker-proxy が回収されない(安全側に倒れる) | なし(閾値の外: 契約「エラーケース」が「ネットワークが存在しない」を明示的に失敗として扱うと定めており、実装はそのとおり。判定できなかったことを表示する) |
| **ロックはホスト CLI のプロセス間でしか有効でない** | 利用者が直接 `docker rm -f` / `docker run` する経路と、別ホストから同じデーモンを操作する経路は防げない | なし(契約 `CTR-cli-container`「ロックが守れない範囲」が明示) |

