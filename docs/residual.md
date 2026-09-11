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
- 2026-09-11 .claude/scripts/build-facts.py:83 開始の印を拾う `BEGIN_RE` が、コードスパン(バッククォート)の中に**引用として**書かれた印も本物の区画として数えるため、印の書式そのものを説明した文書が「終端が無い」違反になる。実測: `docs/histories/2026-09-06-facts-json-close.md:30` が `id=...`(`.` は `[\w.\-]+` に一致する)を引用しており、F3 の合格条件「`build-facts.py check` が 0」を塞いでいた。本 run は引用の綴りを印に一致しない形へ直して回避したが、道具の側は次に配られた先でも同じ穴を持つ(印の書式を説明する文書は、どのプロジェクトにも書かれうる)。直すなら `/kit-improve`(CLAUDE.md §6)。直しかたの候補: コードスパンの中を走査から除く、または `id` が `docs/facts.json` に宣言済みの区画だけを区画と数える(F3 実装整合フロー)
- 2026-09-11 .claude/scripts/check-ssot.py:CS21 ID の範囲の主張の検査が、summary に在る範囲を**1つずつ独立に**評価するため、正しく2つの範囲を書いた summary が偽の違反を出す。実測4件(`docs/00-requests/acceptances.md` の「AC-01〜AC-03 と AC-06〜AC-08」で2件、`docs/01-requirements/usecases.md` の「UC-01〜UC-03 と UC-06」、`docs/03-impl/tests/e2e.md` の「E2Eシナリオ E2E-01〜E2E-03 と E2E-06」)。どの文書も実体と一致しており、直す先は検査の側である。直しかたの候補: 1つの summary に在る範囲と単独 ID を**和集合**にしてから外側を数える。直すなら `/kit-improve`(CLAUDE.md §6)(F2 文書整合フロー)
- 2026-09-11 docs/03-impl/infra/local/docker-resources.md:リソース一覧 `Makefile:37` が定義し `make setup`(:124-128)が作り `make clean`(:302)が消すボリューム `claude-dev-chrome-data` が、この一覧に1行も無い。`claude-dev` / `claude-dev-mac` はこれをどのコンテナにもマウントしておらず(実体は `claude-dev-chrome-<name>` のコンテナ別ボリューム)、`MODULE-makefile-volumes.md:25,51` と `MODULE-makefile-clean.md:34,72` だけが触れている。この取りこぼしが原因で直前の F3 が `docs/02-design/architecture.md:109` の共有ボリュームを 3本→4本 と書き換えたが、02 の他の2文書とこの一覧は 3本 のままで、本 run は 3本 へ戻した。**この一覧が決着しない限り次の F3 が再び 4本 へ倒しうる**(F3 実装整合フロー)
- 2026-09-11 docs/issues/:frontmatter 課題票6件のうち5件(`005` `010` `028` `055` `094`)が `closes_when:` を持たない(原則8 と `.claude/directions/issues-pendings.md` §1 が課題票に要求する項目。`097` だけが持つ)。本 run は同じ5件に欠けていた `origin_layer:` のうち4件を課題票自身の裁定から埋めたが、`closes_when:` は「何が起きたら閉じるか」の裁定であって転記では決まらないので、起票者の判断が要る(F2 文書整合フロー)
- 2026-09-11 docs/02-design/architecture.md:環境一覧 共有ボリュームの**本数**が `architecture.md:109`・`environments.md:67`・`contracts/cli-container.md:719` の3箇所と `docs/03-impl/relations/MODULE-cli-reset.md:233` に手書きで独立に書かれている(`.claude/directions/conventions.md` §4 の「同じ事実を2箇所に手で書かない」に反する)。本 run の 高 の所見(architecture.md だけが 4本 になっていた)はこの重複が原因であり、所有者は `docs/03-impl/infra/local/docker-resources.md` のリソース一覧である。直しかたの候補: 3箇所を参照に置き換えるか、`docs/facts.json` に宣言して `build-facts.py` の機械の欄にする(F2 文書整合フロー)
- 2026-09-11 docs/00-requests/decisions/:D0-* `区分: 決定` の20件のうち16件が `見直す条件` を持たない(`.claude/templates/decisions.md:34` が決定の必須項目として並べ、`.claude/directions/00-requests.md:106` が「新しい決定・触れた決定は必ず持つ」と定める)。欠けているのは `D0-env-01`〜`06` `D0-env-08` `D0-sec-06`〜`10` `D0-auth-03` `D0-dist-02`〜`04`(いずれも規則の成立より前に書かれたもの)。前提が崩れたことを誰も判定できない状態が続く。書き足すのは人間の決定そのものなので、00 起点の変更タスクが要る(F2 文書整合フロー / 独立レビュー review-112055(codex) の所見)
- 2026-09-11 docs/00-requests/terminology.md:用語表 8用語(28〜35行)の「含む例」「含まない例」が空である(`/verify-docs` の A0 が全数の run でだけ見る項目)。例が無い用語は、境界の判定が読み手ごとに割れる(F2 文書整合フロー / 独立レビュー review-112055(codex) の所見)
