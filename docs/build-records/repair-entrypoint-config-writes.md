---
slug: repair-entrypoint-config-writes
state: awaiting-verify
critical: false
origin: derived
issue: docs/issues/098-modify-entrypoint-writes-user-controlled-paths-as-root.md
started: 2026-08-22T19:05:00+09:00
updated: 2026-08-22T19:55:00+09:00
commit: cd32b995356837ef55eea102d7072f948a22b045
summary: 起動処理が /workspace 配下の設定を書くときの一時ファイルと chown を安全な形へ揃え、登録の有無の判定を値の真偽からキーの有無へ直す
---

# repair-entrypoint-config-writes — 設定ファイルの書き方を直す(課題票 098・099)

## 目的・やらないこと

- 目的: 課題票2件を閉じる。(a) root で `/workspace` 配下へ書くときに、固定名の一時ファイルと
  シンボリックリンクを追う `chown` をやめる(098)。(b) 登録の有無の判定を `jq -e` の真偽から
  キーの有無へ変え、`null` が書かれたエントリを上書きしないようにする(099)。
- やらないこと: 外から見える振る舞いの変更(どちらも受け入れ基準は既に在り、実装をそれへ合わせる)。
  `settings.json` 以外の、この closure に無い書き込み経路の見直し。

## 影響範囲(closure)

- scripts/entrypoint-claude.sh
- docs/03-impl/relations/MODULE-entrypoint-claude.md
- docs/issues/098-modify-entrypoint-writes-user-controlled-paths-as-root.md
- docs/issues/099-bug-mcp-entry-presence-test-treats-null-as-absent.md

## 主張

- 触ったモジュールのテスト: green(`cd docker-proxy && go test -count=1 ./...` → `ok  	github.com/quvox/claude-dev-env/docker-proxy	0.045s`)。
  entrypoint には自動テストが無いため、**再ビルドした実イメージで直接測った**:
  (a) `.mcp.json` に `"chrome-devtools": null` を書いた状態で起動 → **値は変わらず**、
      同じファイルの別エントリも無傷(課題票 099 の閉じ条件)、
  (b) `/workspace/.mcp.json.tmp` を `/etc/passwd` へのシンボリックリンクとして仕掛けた状態で起動 →
      コンテナ内の `/etc/passwd` は 22 行のまま(旧実装なら切り詰められる。課題票 098 の閉じ条件)、
  (c) 回帰: 旧値からの移行と codex への登録は従来どおり成立した。
- lint / build: green(`cd docker-proxy && go vet ./...` → 出力なし・終了コード 0 /
  `bash -n scripts/entrypoint-claude.sh` → 出力なし・終了コード 0 /
  `make build` → `✅ claude-dev-claude` `✅ claude-dev-claude-vnc` `✅ claude-dev-docker-proxy`)
- 外部挙動の変化: なし(受け入れ基準 `FR-env-11-2` / `FR-env-11-9` / `FR-env-12-14` が定める
  観測可能な振る舞いは変わらない。変わるのは、それを実現する書き方だけ)
- 認証・決済・不可逆への接触: なし
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 及第ライン)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | アカウント・権限・認証情報を作る/変える/消す機能に触れない | - |
| BR-02 | 該当 | 利用者が書いた JSON を読んで判定する。その判定の誤りを直すのが本タスクである | FR-env-11-9(既存条項) |
| BR-03 | 非該当 | 利用者が値を決める識別子を新設しない | - |
| BR-04 | 該当 | プロセスの外に保存された JSON を読んで使う。読めたことを検証してから書く形は維持する | MODULE-entrypoint-claude(実装上の判断) |
| BR-05 | 該当 | 利用者のファイルを書き換えうる。**本タスクはその範囲を狭める側の変更である** | FR-env-11-9(既存条項) |
| BR-06 | 非該当 | 推測されると困る値を作らない | - |

## 決定シート(回答済み)

- 問いなし(修繕モード。課題票2件が既に判断を担っている)

## 質問キュー(出口のシートの種)

- なし

## 調査メモ

- `scripts/entrypoint-claude.sh:759` / `:790` — `jq -e '.mcpServers[...]'` は値が `null` / `false` の
  ときに終了コード 1 を返す(2026-08-22 に `jq` で実測)
- `scripts/entrypoint-claude.sh:760` `:769` `:791` `:541` — `> "${...}.tmp"` の固定名リダイレクト
- `scripts/entrypoint-claude.sh:778` 付近 — `chown` に `-h` が無い
- `scripts/entrypoint-claude.sh:287` `ensure_codex_config` / `ensure_codex_mcp_entry` — 同じファイルの
  中に既に `tempfile.mkstemp` + `os.replace` + 所有者の復元という安全な形の先例がある
- `.devcontainer/Dockerfile.claude:106` — コンテナの利用者は `NOPASSWD:ALL` の sudo を持つ
  (098 の重大度を 中 と裁定した根拠)

## 進捗メモ(再開点)

- 2026-08-22 19:05 修繕モードで着手。計器: 課題票 8 / 残務 50 行 / 未検証記録 1 / 未回答シート 0
- 2026-08-22 19:15 `update_json_file` を新設し、JSON を書く5経路(`.mcp.json` ×3・`.claude.json`・`settings.json`)を通した。新規作成の2経路にもリンクの拒否を足した
- 2026-08-22 19:20 登録の有無の判定を `has()` へ(2箇所)。`bash -n` 合格
- 2026-08-22 19:30 **実機確認で旧イメージの振る舞いを測っていたことに気づいた** — `entrypoint-claude.sh` は `.devcontainer/Dockerfile.claude:261` でイメージに焼き込まれる。`make build` してから測り直した
- 2026-08-22 19:45 再ビルド後に (a)(b)(c) を実測。すべて期待どおり
- 2026-08-22 19:50 段4: 03 の手順18・実装上の判断・異常系を実装へ合わせた。既存の判断行8件を読み直し、いずれも 継続

## 申し送り

- なし
