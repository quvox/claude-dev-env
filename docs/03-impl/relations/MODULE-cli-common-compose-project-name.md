---
id: MODULE-cli-common-compose-project-name
updated: 2026-08-11
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev::compose_project_name, claude-dev::compose_project_name_legacy, claude-dev::sha256_hex, claude-dev-mac::compose_project_name, claude-dev-mac::compose_project_name_legacy, claude-dev-mac::sha256_hex
callers: MODULE-cli-start, MODULE-cli-stop
callees: なし
contracts: CTR-cli-container
design: DSN-env-03, DSN-mod-02, DSN-mod-03, DSN-mod-07
requirements: FR-env-01, FR-env-07
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
summary: compose プロジェクト名の一意化名と旧い名前を、両 OS で同じ値になる1機能で導出する
---

# MODULE-cli-common-compose-project-name compose 一意化名の導出

## 目的

全プロジェクトが `/workspace` にマウントされるため compose の既定名が衝突する。
これを避けるため `COMPOSE_PROJECT_NAME` を**起動ディレクトリごとに衝突しにくい名前**にする(**一意性は保証しない** — 先頭6桁しか使わないので衝突は残る。`docs/pendings.md` P-005)
(`DSN-env-03` / `FR-env-01-19` / `FR-env-07-5`)。

**`start` が渡す値と `stop` が再計算する値が1バイトでも違うと `stop` が何も消せない**ので、
両者は必ずこの1関数を通す。値の形式の正は契約 `CTR-cli-container`「compose 資源の識別」である。

## 処理の流れ

1. `compose_project_name_legacy <名前>` — `<名前>` を小文字化してから `[a-z0-9_-]` 以外を `-` へ
   置換した**正規化名**を返す(`claude-dev:548`-`:551`)。これは**本要件の一意化より前の形式**であり、
   別ディレクトリと衝突しうるので削除対象の識別には使わない。**`stop` はこれを、旧い名前の
   compose 資源が残っている可能性を案内するためだけに直接呼ぶ**(`claude-dev:1615` / `:1692`)。
2. `sha256_hex <文字列>` — 文字列の SHA-256 を16進小文字で返す。**分岐は OS ではなく
   `command -v sha256sum` の成否**である(`claude-dev:539`-`:546` / `claude-dev-mac:604`-`:611` は同一の
   `if command -v sha256sum; then … else shasum -a 256; fi`)。macOS でも `sha256sum` があれば前者を、
   Linux でも無ければ後者を使う。どちらを通っても同じ入力に対して同じ値になる。
   **入力は `printf '%s'` で与えるので、ハッシュ源に改行は混じらない。**
   **戻り値の末尾には `cut` が付ける改行がある**(`compose_project_name` はコマンド置換で受けるので、
   そこでは落ちる)。
3. `compose_project_name <名前> <起動ディレクトリの絶対パス>` —
   `<正規化名>-<絶対パスの SHA-256 先頭6桁>` を返す(`claude-dev:555`-`:557`)。
   手順1・2 を内部で呼ぶ。**ハッシュ源は起動ディレクトリの絶対パスであり、コンテナ名ではない。**

## 呼び出され方

- 契機: `start` の `COMPOSE_PROJECT_NAME` の組み立て(`claude-dev:1318`)と、
  `stop` の compose 資源の特定(`claude-dev:1617`)・旧い名前の案内(`:1615` / `:1692`)。
- 前提条件: `compose_project_name` を呼ぶ側が**起動ディレクトリの絶対パスを持っている**こと。
  `stop` はそれを管理ラベル `claude-dev.project-dir` から読む(`MODULE-cli-common-container-project-dir`)
  ため、**ラベルを読めなければこの機能を呼ばずに compose の片付けを中止する**。
- 引数: 制約の正は契約 `CTR-cli-container`「compose 資源の識別」。
- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

`callees` は「なし」。`compose_project_name` が同一機能内の `compose_project_name_legacy` と
`sha256_hex` を呼ぶが、**統合により3関数とも本機能の入口である**ためモジュール境界をまたがない。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 標準出力へ1つの文字列。`compose_project_name` = `<正規化名>-<6桁>`(`printf` なので**改行なし**)、`compose_project_name_legacy` = `<正規化名>`(`sed` なので**末尾に改行あり**)、`sha256_hex` = 64桁の16進小文字(`cut` なので**末尾に改行あり**)。**呼び出し元はいずれもコマンド置換で受けるため、末尾の改行は落ちる** |
| 永続化 | **なし**(状態を持たない純粋な導出)。導出した値は `start` が `COMPOSE_PROJECT_NAME` 環境変数としてコンテナへ渡し、compose が `com.docker.compose.project` ラベルとして Docker 資源に付ける |
| 発火するイベント | なし |
| ログ | なし(呼び出し元が表示する) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| **`sha256sum` も `shasum` も無い** | `command -v sha256sum` が偽になり `shasum -a 256` を起動して失敗する。パイプの終了コードは `cut` のものになるため**空文字列が返り、失敗が伝わらない** | 一意化名が `<正規化名>-` になり、`start` と `stop` は同じ値を得るので互いには食い違わないが、**別ディレクトリと衝突する**。**この2コマンドは `start` 手順1 の前提コマンド検査(`docker` / `jq` / macOS は `socat`)に含まれていない**ので、事前に止まる経路は無い(`claude-dev:319`-`:333` / `claude-dev-mac:384`-`:399`) |
| **異なる絶対パスの SHA-256 先頭6桁が一致した** | 検出しない。両ディレクトリが同じ一意化名を得る | 一方の `stop` が他方の compose 資源を削除しうる(`docs/pendings.md` **P-005**。2026-08-04 に人間が受容) |
| **`<名前>` に大文字が含まれる**(`stop <NAME>` で利用者が渡せる唯一の経路) | 小文字化してから置換するので `start` 側と同じ値になる | なし |
| **起動ディレクトリの絶対パスに空白や多バイト文字が含まれる** | `printf '%s'` に引用付きで渡すので語分割されず、そのままハッシュ源になる | なし |

## 実装上の判断

- [DS-05] `compose_project_name` / `compose_project_name_legacy` / `sha256_hex` の3関数を1機能へ統合する — 理由: 3つで1つの命名規則を成しており、`compose_project_name` だけを昇格させても `compose_project_name_legacy` が `stop` から直接呼ばれる分でファンイン2が残る。分けて昇格させると「一意化名の規則」の説明が3文書に散る / 見直す条件: `stop` が `compose_project_name_legacy` を直接呼ばなくなったとき(そのときは `sha256_hex` とともに本機能へ畳み込める)
- [D0-scope-03] ハッシュコマンドの選択を **OS 名ではなく `command -v sha256sum` の成否**で行い、分岐を1関数の中に閉じる — 理由: 既定の macOS に `sha256sum` は無いが、導入されている環境もある。OS 名で分けると「Linux だが `sha256sum` が無い」「macOS だが在る」の両方で外す。**同じ変換が二箇所にあると、ハッシュを含む名前では食い違いの被害が大きい**ので、分岐は1関数に閉じる / 見直す条件: `shasum -a 256` と `sha256sum` が同じ入力に対して違う値を返すようになったとき
- [DS-02] `sha256_hex` の失敗を握って空文字列を返す形になっている(`cut` がパイプの終了コードを決める) — 理由: **これは意図した設計ではなく、パイプラインの構造から生じている**。呼び出し元が空ハッシュを検出する経路は無く、`start` と `stop` が同じ空ハッシュを得るため互いには食い違わない / 見直す条件: `sha256sum` / `shasum` を持たない実行環境を支援対象に入れるとき(そのときは検査を足すコード変更が要る)
- 判断なし(**桁数について**): ハッシュを**先頭6桁(24 ビット)**に切ることは AI の委任判断ではない。**この値は `COMPOSE_PROJECT_NAME` と `com.docker.compose.project` ラベルに現れる外部から見える値**であり、`DS-04` の「外部契約・画面・保存データに現れる値」の対象外である。**決めたのは設計判断 `DSN-env-03`(桁を増やすと `docker ps` の出力から人がプロジェクトを見分けにくくなるため)と、衝突を検出しないことを受容した人間の判断(`docs/pendings.md` P-005。2026-08-04)**であり、形式の正は契約 `CTR-cli-container`「compose 資源の識別」が持つ
- [DS-02] ハッシュ源を `printf '%s'` で与える(`echo` を使わない) — 理由: `echo` は末尾に改行を付けるので、改行の有無で値が変わる。両 OS で同じ値になることが本機能の存在理由である / 見直す条件: なし(この判断が崩れると機能の目的そのものが崩れる)
- [D0-scope-02] 旧い名前(`compose_project_name_legacy` の値)を**削除対象の識別に使わない** — 理由: 旧名は別ディレクトリと衝突しうるので、消すと別プロジェクトを巻き込む。`stop` はこれを案内の表示にだけ使う(`FR-env-01-20`) / 見直す条件: 移行期が終わり旧名の資源が存在しなくなったとき

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **ハッシュ衝突を検出しない** | 異なる絶対パスの先頭6桁が一致すると、一方の `stop` が他方の compose 資源を削除しうる | `docs/pendings.md` **P-005**(2026-08-04 に人間が受容。`FR-env-01-19` / `FR-env-07-5` の充足が `部分`) |
| **正規化が非可逆である** | `~/work/My.App` と `~/other/my-app` は同じ正規化名になる。一意化名はハッシュで分かれるが、**旧い名前の案内は両方に出る** | なし(閾値の外: 案内は削除を伴わない) |
| **`sha256sum` / `shasum` の不在を誰も検出しない** | どちらも無い環境では空のハッシュを返し、`<正規化名>-` という一意化されない名前になる。**`start` の前提コマンド検査は `docker` / `jq`(macOS は `socat`)しか見ていない**ので、事前に止まらない | なし(閾値の外: 両方とも標準的な実行環境に付属し、本システムが前提とする環境(`SR-01`)では欠けない。**検査を足すのはコード変更なので本タスクの範囲外**) |
