---
slug: document-codex-sandbox-preconditions
state: building
critical: true
origin: human-report
issue: docs/issues/102-bug-colabtmux-refuses-to-launch-codex-on-a-nonzero-bwrap-probe.md
started: 2026-08-20T10:35:08+09:00
updated: 2026-08-20T11:10:00+09:00
commit: -
summary: コンテナで codex を起こす側が前提にしてよい環境を実測して 02 に明文化し、bwrap の非ゼロを故障と読む誤りを断つ
---

# document-codex-sandbox-preconditions — codex を起こす側の前提を実測して 02/03 へ降ろす

## 目的・やらないこと

- 目的: issue 102 の切り分け(対処案 A)を実機で行い、`02-design/environments.md` の
  Codex 実行設定にある**事実誤り**を実測値へ直し、**コンテナで codex を起こす側が前提に
  してよいこと**(bwrap の非ゼロは正常である・可否の判定は何で行うか・`workspace-write` は
  成立しない・置いた設定はホストからも見える)を明文化する。対処案 B に相当する。
- やらないこと: (1) コンテナの `--security-opt` を緩めること(`FR-env-12-7` が禁じ、
  `D0-dist-04` が却下済み)。(2) codex 設定の**置き場所を変えること** — `AC-06` の
  「設定と履歴はプロジェクトごとに独立している」と `CTR-cli-container` の「プロジェクト
  ディレクトリ配下」が現在の位置を定めており、変えるなら 00 の合意が要る(残務へ1行)。
  (3) `.claude/directions/orchestration.md` の修正 — キットは凍結中(CLAUDE.md §3)で
  `/kit-improve` の持ち物である(残務へ1行)。(4) `codex exec` の実機確認 —
  共有ボリュームに codex の認証が無く、デバイス認証はブラウザ操作を要する。

## 影響範囲(closure)

- docs/02-design/environments.md
- docs/03-impl/relations/MODULE-entrypoint-claude.md
- docs/03-impl/index.md
- docs/pendings.md
- docs/issues/102-bug-colabtmux-refuses-to-launch-codex-on-a-nonzero-bwrap-probe.md

## 主張

- 触ったモジュールのテスト: green(`cd docker-proxy && go test -count=1 ./...` →
  `ok  	github.com/quvox/claude-dev-env/docker-proxy	0.015s`)。**このタスクは製品コードを
  1行も変えていない**ので、触ったモジュールは無い(既存のテストが緑であることの確認である)
- lint: green(`cd docker-proxy && go vet ./...` → 出力なし・終了コード 0)
- build: 再実行していない。理由: `git status` が示す変更は Markdown だけで、Dockerfile・
  シェルスクリプト・Go のいずれも触っていないため、イメージのビルド結果は変わらない
- 仕様ドキュメントの一括検査: `python3 .claude/scripts/check-ssot.py docs` →
  `NG 違反 10 件`。**10 件すべてが closure の外の既存違反**(CS11 の参照実在6件と CS20 の
  起点層4件。どちらも `docs/pendings.md` の残務が既に持っている)。CS8(曖昧語)は OK で、
  今回書いた本文は違反を1件も増やしていない
- 外部挙動の変化: なし(コードを1行も変えない。文書の事実誤りの訂正と明文化のみ)
- 認証・決済・不可逆への接触: あり(critical: true)— 対象が「codex がサンドボックスと
  承認なしで走るかどうか」という権限境界の記述であるため。機械判定(BRC2)の語には
  当たらないので、これは自分の判断で上げたものである
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 収束契約)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | closure はドキュメント本文だけで、アカウント・権限・認証情報を作る/変える/消す機能を新設も変更もしない | — |
| BR-02 | 非該当 | 利用者や外部から値を受け取る口(画面・API・CLI 引数・ファイル取込)を新設も変更もしない | — |
| BR-03 | 非該当 | 利用者が値を決める識別子を新設しない | — |
| BR-04 | 非該当 | プロセス境界をまたぐ値のやり取りを変えない(コード変更なし) | — |
| BR-05 | 非該当 | 不可逆または影響の大きい操作を新設しない | — |
| BR-06 | 非該当 | トークン・鍵・初期パスワードなど推測されると困る値を作らない | — |

## 決定シート(回答済み)

- 問いなし(開示のみ)

## 調査メモ

- 実測(2026-08-20、コンテナ `issue102-probe` = `claude-dev-claude:latest`、codex 0.148.0):
  `bwrap --unshare-user --unshare-net --ro-bind / / /bin/true` は **exit 1**
  (`No permissions to create new namespace`)。既知・正常である。
- 実測: 既定3鍵が在る状態で `codex sandbox -- /bin/true` は **exit 0**。
  `codex sandbox --enable use_legacy_landlock -- /bin/true` も **exit 0**。
  `codex sandbox -- /bin/sh -c 'touch /tmp/x'` は **exit 1**(書き込み拒否)。
- 実測: `codex sandbox -c sandbox_mode=workspace-write -- /bin/true` は **exit 101** の panic
  (`permission profiles requiring direct runtime enforcement are incompatible with
  --use-legacy-landlock`)。`FR-env-12-9` が対象外と定めた帰結の実体である。
- 実測: 3鍵目(`[features] use_legacy_landlock = true`)を欠く CODEX_HOME では
  `codex sandbox -- /bin/true` も `-c sandbox_mode=read-only` も **exit 1**(bwrap)。
  **この旗は 0.148.0 でも依然として効いている**(`codex features list` の表示は `deprecated`)。
- 実測: `docs/02-design/environments.md:171` の「フラグ無しの `codex sandbox -- /bin/true` は
  exit 1(bubblewrap)で、これは既知・正常」は**誤り**。既定3鍵が置かれた状態(=本システムが
  保証する状態)では exit 0 である。`scripts/e2e6-codex.sh:159` の期待(exit 0)が正しい。
- 実測: `externals/amd64/colabtmux`(sha256 ba7cb13e…)・`externals/arm64/colabtmux`
  (9e4baee0…)・稼働中の `~/.local/bin/colabtmux`(81c8f4bd…)のいずれにも
  `bwrap` / `bubblewrap` / `landlock` / `sandbox` の文字列は**0件**。
  **issue 102 の「colabtmux が bwrap の可否を見ている」という前提は成り立たない。**
- 出どころの特定: 報告文の実体は `.claude/directions/orchestration.md:157-165` と
  `:280`(§1.1.1・§1.3)である。中央エージェントが codex を起こす前に
  `bwrap ...; echo $?` を見て「0 なら codex を使える」と判定するため、コンテナ内では
  正常な非ゼロを見て codex を起こさない。**キット側の欠陥であり、製品側の欠陥ではない。**
- 実測(ホスト側): このリポジトリ直下および `docs/` から `codex features list` を実行すると
  `use_legacy_landlock` が **true**、`/tmp` からだと **false**。同じくリポジトリ直下からの
  `codex sandbox -c sandbox_mode=workspace-write -- /bin/true` は **exit 101** の panic。
  ホストの `~/.codex/config.toml` に `[features]` は無く、この方向を持つ設定は
  `<プロジェクト>/.codex/config.toml`(entrypoint が置いた3鍵。101 バイト)だけである。
  **コンテナが置いた設定はホスト側の codex にも効いている。**
  ただし `.codex/config.toml` を置いただけの新規ディレクトリでは再現しなかったので、
  効く条件そのものは codex 側の解決規則であり、本システムが定めた仕様ではない。
- `check-backlog.py` / `check-debt.py`(`--for-issue`)はいずれも通過(bug 例外)。
- `relations-query.py --requirement FR-env-12` → 実装 7 モジュール / 検証テスト 0 件。

## 進捗メモ(再開点)

- 2026-08-20 10:35 構築記録を作成。closure を確定(上記5パス)。実機の切り分け(対処案 A)は
  完了しており、結論は対処案 B(02/03 の明文化)+ 残務2行。シートは開示のみで問いゼロ。
- 2026-08-20 10:40 決定シートを作成 → `check-sheet.py` が SH4 免除(「曖昧さなし」1件のみ・
  論点0件・委任0件 = 開示)。**問いなし(開示のみ)**として削除し、無人で続行した。
- 2026-08-20 10:45 `docs/02-design/environments.md` を 1.5.0 → 1.6.0。事実誤り3件を実測値へ
  直し、「codex を起こす側が前提にしてよいこと」の表(5行)を置いた。`verified` は触っていない
  (版が上がったので合格証は自動的に無効になる — 原則6)。
- 2026-08-20 10:50 `MODULE-entrypoint-claude.md` の「既知の制限」を2行更新・追加。
  `docs/03-impl/index.md` を 1.32.0 → 1.33.0(`relations/` を変えたため層の版を上げた)。
- 2026-08-20 10:55 `docs/pendings.md` の残務に2行追加(39 行 / 上限 50)。
  キット側の判定の修正は **`.claude/directions/orchestration.md` に手を入れず**残務1行にした
  (CLAUDE.md §3 の凍結。直せるのは `/kit-improve` だけ)。
- 2026-08-20 11:00 `docs/issues/102` を実測で書き直した(原因の確定・severity の根拠・
  対処案の結果・経緯3行)。**削除はしていない** — `closes_when` の3項目のうち1つは満たしたが、
  1つは凍結中のキット待ち、1つは codex の認証が無く無人では確認できない。
- 2026-08-20 11:05 履歴 `docs/histories/2026-08-20-document-codex-sandbox-preconditions.md` と
  気づき `docs/feedbacks/032-a-precondition-probe-must-measure-the-path-actually-used.md` を作成。
  closure に掛かる残務3行はいずれも **持ち越す** と裁定し、理由を履歴に書いた。

## override(人間の明示)

- なし(override 不使用)

## 申し送り

- **調査中に同梱物と稼働中の colabtmux が2回差し替わった**(`externals/amd64/colabtmux` が
  `ba7cb13e…` → `1dcb7bc8…`、`~/.local/bin/colabtmux` が `81c8f4bd…` → `1dcb7bc8…`)。
  **この差し替えはこのタスクのものではない**(`externals/amd64/colabtmux` は今も未コミットの
  変更として `git status` に出る)。4ビルドすべてを走査して結論は変わらなかった。
- **キット `.claude/directions/orchestration.md` §1.1.1 の修正が残っている。** 凍結が解けたら
  `/kit-improve` が持つ。残務1行に書いた。
- `docs/issues/102` の削除は人間の判断である(`issues-pendings.md` §8)。
