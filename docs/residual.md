<!-- docs/residual.md の雛形。**残務(1件1行)だけを持つ。**
     記録先の振り分け(何が課題票で何が残務か)の正は .claude/directions/issues-pendings.md §1、
     この台帳の規則の正は同 §2.1。
     ・棚上げ(P-nnn)はここではない(docs/pendings.md)
     ・仕様ドキュメントではない(version / verified なし、検証対象外) -->

# 残務

<!-- 記録先の振り分けの行4(issues-pendings.md §1): 文書整合の抜け・言い回し・カバレッジ表の穴など、
     不具合でも完了定義を阻害するものでもないもの。**1件1行**。ID・重大度・追跡義務なし。
     検証(verify 系)はこの一覧を読み直さない — 指摘へ還流させない。

       - <YYYY-MM-DD> <path:節> <一文>

     **日付が先頭なのは飾りではない。** doc-health.py はこの形で残務行を認識する。
     **規則の正は issues-pendings.md §2.1**:
       ・鍵は <path:節> + 一文(空白を詰め、末尾の。を落としたもの)。書く前に grep して、
         同じ鍵が在れば**何も書かない**(日付も更新しない)
       ・同じ節の**別の問題**は別の行である(鍵に一文が入っているのはそのため)
       ・**行数の上限は無い。** 50行以上になったら**ローテーションする**(1行も落とさない):
           python3 .claude/scripts/doc-health.py --rotate
         このファイルが docs/residual-<3桁>.md へ押し出され、同じ名前の新しいファイルが作られる。
         **打つのは残務へ書いたフロー自身**で、権限の制限は無い。50 は厳密でなくてよい
         (まとめて書いて超えたら、そのままローテーションする)
       ・**押し出されたファイルはどのフローも読まない。** だから、消えては困るものをここに置かない
         (人間の回答の着地へのポインタは課題票である — issues-pendings.md §2.1)
       ・落ちるのは**同じ鍵の重複**と**対象が実在しない行**の2つだけ。落とすのは /verify-docs で、
           python3 .claude/scripts/doc-health.py --as-of=<日付> --sweep --record=docs/histories/<履歴>.md
         --record 無しの --sweep は拒まれる(落とした行は docs/histories/ へ写る。
         reverification.md は毎回生成し直されるので記録先にならない)
       ・タスクを閉じるとき、クロージャに載る path の行は /build が
         直した / 不要と裁定 / 持ち越す のどれかを付け、前2つだけ消す -->

## 残務(文書整合ほか)

- 2026-09-01 docs/build-records/pyenv-nvm-in-claude-image.md:基本要件の点検 BR-08 の落とし先が「方針は `docs/03-impl/environments/images.md`「環境変数(ビルド引数)」に1行で記す」と書かれているが、その方針の1行は実際には `docs/03-impl/environments/images.md:95`(「言語ランタイムのバージョン管理」の「実装上の判断」)に在る。方針そのものは書かれておりコードの引用も一致しているので、BR-08 の充足は損なわれていない。誤っているのは節の名前だけである(F3 実装整合フロー)
- 2026-09-01 docs/03-impl/environments/images.md:frontmatter `source:` が `docs/02-design/environments.md` だけを挙げているが、同ファイルはサービスとポートの表しか持たず、イメージのステージ構成の設計意図は `docs/02-design/architecture.md` の `DSN-dist-01` に在る(本文もその ID を引いている)。上流が動いたときにこの文書が失効することを機械が言えない。基準コミット 69579da より前から在る取りこぼしである(F3 実装整合フロー)
- 2026-09-01 docs/build-records/bundle-chrome-devtools-mcp.md:基本要件の点検 `check-baseline-verdicts.py` の BR-03 の疑いが、この記録と `fix-make-status-hides-docker-query-failure.md` / `fix-session-list-undercount.md` / `fix-start-auxiliary-halts-and-tmux-runtime-env.md` / `repair-entrypoint-config-writes.md` の計5本に出ている。根はいずれも `USERNAME=` を含む行であり、それはビルド引数かシェル変数の代入であって利用者が値を決める識別子ではない。この run の対象集合の外なので裁定していない(F3 実装整合フロー)
- 2026-09-01 docs/build-records/bundle-chrome-devtools-mcp.md:基本要件の点検 BR-06 の疑い(`.github/workflows/ghcr-images.yml:143` の `secrets.`)が残っている。`.github/workflows/ghcr-images.yml` は前回の verify-impl の green 以降変わっていないためこの run の対象集合の外であり、裁定していない(F3 実装整合フロー)
- 2026-09-01 docs/build-records/fix-make-status-hides-docker-query-failure.md:基本要件の点検 `check-baseline-verdicts.py` の BR-05 の疑いが、この記録と `fix-start-auxiliary-halts-and-tmux-runtime-env.md` に出ている(`Makefile:302` の `docker volume rm`、`claude-dev:337` の `rm -rf`)。どちらもこの run の対象集合の外なので裁定していない(F3 実装整合フロー)
- 2026-09-01 docs/00-requests/acceptances.md:`/verify-tests e2e` が要求する「AC-nn 全件を実システムに対して判定」(`.claude/skills/verify-tests/SKILL.md` §1)が、この project の履歴上 一度も実行された記録が無い(`docs/histories/` `docs/issues/` `docs/pendings.md` を検索して確認。`docs/kit-report.md:112` も同じ欠落を既に指摘している)。AC-02(クライアント PC 経由の SSH トンネル)と AC-06(実 OpenAI アカウントでのブラウザ認証)はこの実行環境だけでは判定できず、AC-01/03/08 のフル実機手順(`docs/03-impl/tests/e2e.md` E2E-01 手順8)も「他に作業中のセッションが無い専有ホスト」を前提とし艦隊運用の現状と両立しない(P-006 と同型)。基準コミット 69579da より前から在る取りこぼしである。今回の run(`.devcontainer/Dockerfile.claude` / `.github/workflows/ghcr-images.yml` の増分)はこの2ファイルが AC-01〜08 のどのコード経路にも触れていないと確認したうえで対象外として扱った(F4 試験フロー)
- 2026-09-06 .claude/.gitignore:冒頭 キットが配る `.claude/.gitignore` は、ツール環境(`.venv/` `.tools/` `__pycache__/` `*.pyc` `.kit-snapshot.tar.gz` `improvements/`)しか宣言しておらず、**Claude Code 自身の実行状態**(`.credentials.json` `.claude.json` `history.jsonl` `projects/` `sessions/` `cache/` `file-history/` `shell-snapshots/` `backups/`)を1件も宣言していない。同じキットの `scripts/kit-dist.json` は配布物について「除外リストで書くと列挙し忘れたものが混入して事故になる。allowlist なら知らないものは決して入らない」として許可リストを採っているのに、git 側の語彙だけが除外リストのままである。本タスクは本リポジトリのルート `.gitignore` 側に許可リストを置いて回避したが、キット自体は次に配られた先でも同じ穴を持つ。直すなら `/kit-improve`(キットの編集はそれだけが行える — CLAUDE.md §6)
- 2026-09-06 docs/03-impl/relations/MODULE-cli-start.md:手順12 `.gitignore` へ `.claude` / `.codex` を追記する手順の異常系の表が、「その `.claude/` に開発キットなど追跡したい資産が同居している場合、それらもまとめて追跡から外れる」ことを述べていない。同じ節は「env ファイルが既にリポジトリの追跡下にあると、追跡からは外せない」という対になる注意は持っている(:451)。本リポジトリで実際にこの取りこぼしが起き、`.claude/` 配下が一度も追跡されない状態が 2026-03-31 から続いていた(F2 文書整合フロー)
- 2026-09-06 .claude/settings.local.json:permissions.allow 道具の許可リストに、過去のセッション ID と利用者名を含む機械固有の絶対パス(`Bash(mkdir -p /tmp/claude-1000/-home-<利用者名>-...)`)が1件残っている。既に死んだ項目(そのセッションの一時ディレクトリは存在しない)であり、本リポジトリが公開であるため gitignore-recovery ではこのファイルを追跡対象から外した。この行を削れば、キットの `.claude/.gitignore` 冒頭が定めるとおり git で共有できる(F2 文書整合フロー)
- 2026-09-06 .claude/scripts/check-buildrecord.py:68 クロージャのパスを拾う正規表現 `CLOSURE_PATH = ^[-*]\s+`?([\w][\w./-]*)`?` が先頭に単語文字を要求するため、`.` で始まるパス(`.gitignore` `.devcontainer/Dockerfile.claude` `.github/workflows/*` `.env.example` など)が1件残らず落ちる。影響は2つで、①BRC3 が dotfile だけのクロージャを「実パスが1件も無い」と判定する ②**BRC2 の critical パターンの照合も同じ `paths` を読むので、dotfile に掛かる critical パターンが検出されない**(fail-open。`critical: false` の記録がゲートを素通りしうる)。実測: 本タスク(クロージャが `.gitignore` のみ)で BRC3 が落ち、既存の docs/build-records/pyenv-nvm-in-claude-image.md でも `.devcontainer/Dockerfile.claude` が数えられていない。キット全体に効く一般の欠陥なので、直すのは `/kit-improve` である(CLAUDE.md §6)
