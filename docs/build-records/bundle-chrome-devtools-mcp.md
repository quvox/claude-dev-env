---
slug: bundle-chrome-devtools-mcp
state: awaiting-verify
critical: false
origin: human-report
issue: なし
started: 2026-08-22T17:30:00+09:00
updated: 2026-08-22T18:40:00+09:00
commit: b6a7256b9f6348924a977dfe414ab5bcc543a3f7
summary: chrome-devtools MCP を配布イメージへピン留めで同梱し、claude と codex の双方から実行時ダウンロードなしで使えるようにする
---

# bundle-chrome-devtools-mcp — chrome-devtools MCP を配布イメージへ同梱する

## 目的・やらないこと

- 目的: `chrome-devtools-mcp` を配布イメージ2種へビルド時にピン留めして導入し、コンテナ起動時の
  MCP 設定を同梱バイナリへ向ける。あわせて codex 側の設定にも同じ MCP サーバーを登録し、
  claude と codex の双方から使えるようにする。
- やらないこと: chrome-devtools 以外の MCP サーバーの追加(`D0-env-07` は要確認のまま動かさない)。
  ブラウザ確認なしの構成で Chrome を起動できるようにすること(同梱はするが、既定の設定書き出しは
  ブラウザ確認ありの構成のままにする)。

## 影響範囲(closure)

- docs/00-requests/decisions/dist.md
- docs/01-requirements/functional.md
- docs/02-design/architecture.md
- docs/02-design/system.md
- docs/02-design/contracts/cli-container.md
- docs/03-impl/environments/images.md
- docs/03-impl/infra/local/ghcr.md
- docs/03-impl/relations/MODULE-entrypoint-claude.md
- docs/03-impl/contracts/cli-container.md
- .devcontainer/Dockerfile.claude
- scripts/entrypoint-claude.sh
- .github/workflows/ghcr-images.yml

## 主張

- 触ったモジュールのテスト: green(`cd docker-proxy && go test -count=1 ./...` → `ok  	github.com/quvox/claude-dev-env/docker-proxy	0.072s`)。
  **entrypoint と Dockerfile には自動テストが無い**(`docs/03-impl/tests/entrypoint.md` の未実装理由表が正)。
  代わりに次を実測した:
  (a) 追記する TOML の処理を抜き出して単体で流し、正常・既存登録あり・配列テーブル・壊れた TOML・
      末尾改行なし・2回目(冪等)の6件が仕様どおりであること、
  (b) `.mcp.json` の移行判定を `jq` で流し、旧値は一致・利用者が書き換えた値は不一致になること、
  (c) 実イメージ `claude-dev-claude:latest` の上に**今回足した層と同じ命令だけ**を積んだ試験ビルドが
      通り、`chrome-devtools-mcp --version` が fnm 初期化の無いシェルからも `1.7.0` を返すこと。
- lint / build: green(`cd docker-proxy && go vet ./...` → 出力なし・終了コード 0)。
  `bash -n scripts/entrypoint-claude.sh` → 出力なし・終了コード 0。
  `.github/workflows/ghcr-images.yml` は Python の YAML パーサで読めることを確認した。
  **配布イメージの全ビルド(`make build`)は実行していない** — 変更した層だけを実イメージの上で
  積んで確かめた(上の (c))。全ビルドは `/verify-tests` に委ねる。
- 外部挙動の変化: あり(コンテナ内の `.mcp.json` の chrome-devtools エントリが同梱バイナリを指し、
  codex の `config.toml` に MCP サーバー1件が増える)
- 認証・決済・不可逆への接触: なし
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 及第ライン)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | アカウント・権限・認証情報を作る/変える/消す機能に触れない(触るのは MCP の設定だけ) | - |
| BR-02 | 該当 | 利用者が書いた `.mcp.json` と `config.toml` を読んで書き足す。壊れた入力を受け取りうる | FR-env-11-2 / FR-env-12-13(異常系条項) |
| BR-03 | 非該当 | 利用者が値を決める識別子を新設しない(サーバー名 `chrome-devtools` は本システムが決める固定値) | - |
| BR-04 | 該当 | プロセスの外に保存された JSON / TOML を読んで使う。読めたことを検証してから書く | FR-env-11-2 / FR-env-12-13 + MODULE-entrypoint-claude |
| BR-05 | 該当 | 利用者のファイルにある既存エントリを書き換えうる。書き換えは本システムが以前書いた値と完全一致するときだけに限る | FR-env-11-2(移行の条件を条項に書く) |
| BR-06 | 非該当 | 推測されると困る値を作らない | - |

## 決定シート(回答済み)

- 論点1(ブラウザ操作用ツールを決定台帳へ加えるか): **推奨 A を承認**。
  人間の回答(2026-08-22、チャット)逐語: 「すべて推奨どおり」
- 概念1(曖昧さなし): 推奨を承認(同上の1行が全ブロックを決着させる)
- 分割可否(FR-env-11 / FR-env-12 はいずれも 不可分): 推奨を承認(同上)

## 質問キュー(出口のシートの種)

- なし

## 調査メモ

- `scripts/entrypoint-claude.sh:648` — 現在の登録値は
  `{"command":"npx","args":["-y","chrome-devtools-mcp@latest","--browserUrl","http://localhost:9222"]}`
  (実行時ダウンロードに依存している)
- `scripts/entrypoint-claude.sh:645` — MCP 設定は `CLAUDE_DEV_VNC=1` のときだけ実行される
- `scripts/entrypoint-claude.sh:655` — 既存 `.mcp.json` に `chrome-devtools` が在れば何もしない
  (= 既存プロジェクトは npx のまま残る)
- `scripts/entrypoint-claude.sh:287` — `ensure_codex_config` は既定3鍵だけを扱い、MCP は扱わない
- `.devcontainer/Dockerfile.claude:494-498` / `541-545` — 配布2ステージが同じ内容で
  claude / codex を導入している(終端レイヤー方式。`DSN-dist-01`)
- `.devcontainer/Dockerfile.claude:505-511` — codex は fnm 既定 bin を PATH へ足す
  `/usr/local/bin/codex` ランチャー経由で解決している(`docker exec` から使えるようにするため)
- `.github/workflows/ghcr-images.yml:73-91` — codex の版は prepare が npm registry から
  具体バージョンへ解決して build-arg で渡す
- npm registry 実測(2026-08-22): `chrome-devtools-mcp` の最新は `1.7.0`、bin 名は
  `chrome-devtools-mcp`(と `chrome-devtools`)、`engines.node` は `^20.19.0 || ^22.12.0 || >=23`
  (イメージの既定 Node は 24 — `Dockerfile.claude:118-125`)
- `docs/00-requests/request.md:63`「やらないこと」6 は **`externals/` の同梱外部バイナリ**を
  対象にした規則であり、npm/インストーラで入るエージェント CLI 類は対象外(claude / codex が
  既にビルド時取得である)。本件は後者と同類である
- 本件が解消する課題票・棚上げは無い(`docs/issues/index.md` 6件、`docs/pendings.md` の残務を確認)

## 進捗メモ(再開点)

- 2026-08-22 17:30 クロージャ確定・構築記録作成。計器: 課題票 6 / 残務 48 行 / 未検証記録 0 / 未回答シート 0
- 2026-08-22 17:45 シート回答を転記し docs/sheets/bundle-chrome-devtools-mcp.md を削除。段2(SSOT の下降)へ
- 2026-08-22 17:50 00 に `D0-dist-06` を新設。01 に条項3件(`FR-env-11-9` / `FR-env-12-13` / `FR-env-12-14`)を追加し `FR-env-11-2` を改訂。**この変更以前から欠けていた「今回決めた既定(開示)」節(CS19 違反)も同時に新設した**
- 2026-08-22 17:55 02 の `DSN-dist-01` の射程へ MCP サーバーを追加(項1')。要件カバレッジ3行と E2E 一覧2件を更新
- 2026-08-22 18:00 03(images / ghcr / MODULE-entrypoint-claude / tests 3本)を更新。[DS-05] MCP の登録名を `chrome-devtools` のまま据え置く — 理由: 名前は利用者の設定に既に書かれており、変えると既存プロジェクトで有効化が外れる / 見直す条件: 同じ名前で別の MCP サーバーを登録したい要望が出たとき
- 2026-08-22 18:10 Dockerfile の配布2ステージへ導入とランチャーを追加。実イメージの上で同じ命令だけを積む試験ビルドが通ることを実測(`chrome-devtools-mcp --version` → `1.7.0`)
- 2026-08-22 18:20 entrypoint: `.mcp.json` を同梱物へ向け、旧値と完全一致するときだけ置き換える移行を追加。`ensure_codex_mcp_entry` を新設しブラウザ確認ありの初期化から呼ぶ。TOML 追記の6件と `jq` 判定を実測
- 2026-08-22 18:25 CI(prepare の版解決・build-arg・手動入力)を追加。YAML の読み取りを確認
- 2026-08-22 18:35 段4: 差異2件を裁定(codex 登録を別関数にした→03 の記述と判断行を実装へ合わせた / 登録をブラウザ確認ありに限った→`FR-env-12-14` に条件を明示)。`MODULE-entrypoint-claude` の既存の判断行8件を読み直し、いずれも 継続(今回の変更で前提が動いたものは無し)

## 申し送り

- **配布イメージの全ビルドは未実施**。変更した層だけを実イメージの上で積んで確かめた(主張の (c))。
  `make build` / 日次 CI の通しは `/verify-tests` の担当である。
- `docs/03-impl/relations/MODULE-entrypoint-claude.md` が **31,131 バイト**で、CLAUDE.md §7 の
  24,000 バイトを超えている(この変更の前から超過。今回さらに約 1.2KB 増えた)。分割提案は
  `docs/pendings.md` の残務が既に「24,000 バイト超が 13 件在るのに分割提案の記録が無い」として
  記録している。
- `docs/pendings.md` `:172` の残務(`README.md` が旧いドキュメント表を指したまま)は、
  **このタスクの直前に別途 README を書き直したため、記述として既に古い**。クロージャの外なので
  この記録では消化していない — `/verify-docs` の掃き出しで判定されたい。
