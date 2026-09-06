---
slug: gitignore-recovery
state: awaiting-verify
critical: true
origin: human-report
issue: なし
started: 2026-09-06T08:31:04+09:00
updated: 2026-09-06T09:05:00+09:00
commit: daf4170207a255dc3ecd7afb552c3678be86032d
summary: .claude/ 配下が git に1件も追跡されていない状態を、許可リスト方式で直す(認証情報は除外を維持)
---

# gitignore-recovery — `.claude/` を git の追跡へ戻す(認証情報は出さない)

## 目的・やらないこと

- 目的: `.gitignore:4` の `.claude` により `.claude/` 配下が1件も追跡されていない状態を直し、
  `.claude/state/stamps.json` を含むキットの資産を git で共有できるようにする。
  あわせて未コミットの `.colabtmux/*` / `!.colabtmux/colabtmux.conf` の編集を精査して整理する。
- やらないこと: `CLAUDE.md` / `AGENTS.md` の無視の解除(2026-08-02 commit 976960c で人間が
  意図的に git から外した。この作業指示は名指していない)。`.codex` の無視の解除(`auth.json` を持つ)。
  製品(`claude-dev start` 手順12)のコードの変更。

## 影響範囲(closure)

- .gitignore(このタスクの主題。**下の注記のとおり、ゲートはこの行を読めていない**)
- docs/residual.md(解消した1行を掃き出し、発見した3行を足した)
- docs/build-records/index.md(索引。build-index.py が再生成する共有生成物)
- docs/histories/2026-09-06-gitignore-recovery.md(このタスクの履歴)

<!-- **注意 — `check-buildrecord.py` BRC3 は `.gitignore` の行を数えていない。**
     判定に使う正規表現 `^[-*]\s+`?([\w][\w./-]*)`?`(:68)は先頭が単語文字であることを
     要求するので、`.` で始まるパスは1件残らず落ちる。BRC2(critical パターンの照合)も
     同じ `paths` を読むので、dotfile だけのクロージャは「空」かつ「critical パターンに
     掛からない」と読まれる(fail-open)。この記録が BRC3 を通るのは、上の docs/ の3行が
     在るからであって、主題である `.gitignore` が数えられたからではない。
     前例でも同じことが起きている: pyenv-nvm-in-claude-image.md の
     `.devcontainer/Dockerfile.claude` も落ちていた。残務に1行を残した。

     段3 でクロージャを1本に縮めた経緯。当初は `.claude/.gitignore` も含めていたが、
     そのファイルは `.claude/scripts/kit-dist.json` の include に載る**キットの構成要素**であり、
     キットを編集できるのは `/kit-improve` だけである(CLAUDE.md §6)。
     加えて `missions/` を外す判断は本リポジトリが公開であることに依存するプロジェクト固有の
     事情なので、キットへ入れてはならない(CLAUDE.md §3 の一般性の制約)。
     ルートの `.gitignore` はプロジェクトのファイルであり、`/.claude/...` の形で
     同じことを全部書けるため、キットに触れずに完結した。パスは増えていない(縮んだだけ)。 -->

## 主張

- 触ったモジュールのテスト: green(`cd docker-proxy && go test ./...` → `ok  	github.com/quvox/claude-dev-env/docker-proxy	(cached)`)
- lint / build: green(`cd docker-proxy && go vet ./...` → 出力なし・終了コード0 / `make build` → 終了コード0、最終行 `✅ claude-dev-docker-proxy`。独立レビューの所見④を直した後に回し直した値である)
- 外部挙動の変化: なし
  (製品のコードを1バイトも変えない。変わるのは本リポジトリが git で追跡する集合だけである)
- 認証・決済・不可逆への接触: あり(critical: true) — `.claude/.credentials.json`(OAuth 資格情報)を
  持つディレクトリの無視を解除する作業であり、公開リポジトリへの追加は事実上不可逆である
- E2E・全件テスト・ブラウザQA: 実施していない(/verify-tests に委ねる — 及第ライン)

## 基本要件の点検

| ID | 判定 | 理由 | 落とし先 |
|---|---|---|---|
| BR-01 | 非該当 | クロージャは `.gitignore` 2本のみ。アカウント・権限・認証情報を作る/変える/消す機能を持たない | - |
| BR-02 | 非該当 | 利用者または外部から値を受け取る画面・API・CLI・ファイル取込を持たない(実行されるコードが無い) | - |
| BR-03 | 非該当 | 利用者が値を決める識別子を持たない | - |
| BR-04 | 非該当 | プロセスの外と値をやり取りしない | - |
| BR-05 | 非該当 | 利用者の操作で起きることを何も変えない(製品のコードは不変) | - |
| BR-06 | 非該当 | 推測されると困る値を作らない | - |
| BR-07 | 非該当 | 利用者ごとに中身の違う対象を読む/書く経路を持たない | - |
| BR-08 | 非該当 | 値を画面・URL・SQL・シェル引数として出す経路を持たない | - |
| BR-09 | 非該当 | 秘密を突き合わせる経路を持たない | - |
| BR-10 | 非該当 | ブラウザから呼ばれる経路を持たない | - |
| BR-11 | 非該当 | 保存先を作らず、保存の形も対象も変えない | - |
| BR-12 | 非該当 | 成果物を作らず、起動の入口にも版にも触れない | - |

<!-- 基本要件12件はいずれも非該当だが、このタスクの危険は
     `docs/01-requirements/non-functional.md:40` の NFR-sec-01(認証情報をイメージへ焼き込まない)と
     `docs/01-requirements/system.md:26` の SR-03 が守っている領域と同種である。
     基本要件の一覧はリポジトリへの秘密の混入を覆っていないので、
     このタスクは許可リスト方式(既定で全部除外し、名指したものだけ戻す)と
     秘密の走査(調査メモ)でその穴を自前で塞ぐ。 -->

## 決定シート(回答済み)

- 2026-09-06 論点1(`.claude/` の中の「どこまで」を、この公開リポジトリに載せるか)への回答。
  人間の発言を逐語で引用する:

  > A

  すなわち選択肢 A —「道具一式を載せ、『ミッションの記録』だけ外す」。
  よって `.claude/missions/` は追跡しない。ログイン資格情報・会話履歴・過去セッション全文は
  A・B・C いずれでも公開しない(許可リスト方式で機械的に保証する)。

## 質問キュー(出口のシートの種)

- なし

## 調査メモ

- .gitignore:4 `.claude` — `git check-ignore -v .claude/state/stamps.json` が
  `.gitignore:4:.claude` を返す。`git ls-files .claude` は0件、`git log --all -- .claude` も空で、
  `.claude/` 配下は**一度も追跡されたことがない**
- .gitignore の `.claude` 行は 2026-03-31 commit 36a1a89 で入っており、キットが `.claude/` へ
  入居するより前である(ignore が後からキットを飲み込んだ)
- docs/00-requests/decisions/auth.md:70 「`.gitignore` へ `.claude` / `.codex` を自動追記して
  git の追跡から外す。」 — **この行は製品 `claude-dev start` の機能である**(FR-env-14-4)
- claude-dev:1567 `if ! grep -qxF "$_ig" ... && ! grep -qxF "${_ig}/" ...` — 追記の冪等判定は
  `.claude` **または** `.claude/` の**完全一致する行**の有無だけを見る。
  よって `.claude` の行を消すと、次の `claude-dev start` が黙って書き戻す
- .claude/.gitignore は `.claude/scripts/kit-dist.json` の include に載るキットの構成要素であり、
  その冒頭が「git で共有するものと、配布物に入れるものは別である」「`scripts/*.local.json`・
  `settings.local.json`・`missions/` は…**git では共有する**」と定めている。
  **このファイルの存在自体が「git は `.claude/` の中へ降りる」を前提にしている**
- .claude/scripts/kit-dist.json の `_comment`: 「include は allowlist である。除外リストではない。
  理由: `.claude/` はキットの置き場であると同時に、環境によっては Claude Code 自身の実行状態
  (sessions/ projects/ history.jsonl .credentials.json cache/ file-history/ 等)の置き場でもある。
  除外リストで書くと列挙し忘れたものが…事故になる。allowlist なら知らないものは決して入らない。」
  — **git 側も同じ理由で同じ形(許可リスト)を採るべき**である
- 実際に `.claude/` 直下に在る Claude Code の実行状態: `.credentials.json`(中身は
  `claudeAiOauth` の1鍵)・`.claude.json`・`history.jsonl`・`projects/`(8.5MB)・`sessions/`・
  `file-history/`(2.2MB)・`shell-snapshots/`・`cache/`・`backups/` ほか。
  **`~/.claude` とは別のディレクトリである**(`realpath` が異なる)が、中身は同種である
- `gh repo view` → `{"isPrivate":false,"visibility":"PUBLIC"}`(`quvox/claude-dev-env`)。
  **公開リポジトリである** — 追加したものは公開され、取り消しには履歴の書き換えが要る
- 許可リスト案で追跡対象になるのは 239 ファイル / 3,132 KB
  (内訳 — scripts 60本 1,404KB / directions 18本 784KB / skills 12本 333KB /
  missions 86本 323KB / templates 39本 143KB / roles 7本 39KB / migrations 10本 34KB / 他)
- その 239 ファイルに対する秘密の走査(`sk-` `ghp_` `github_pat_` `AKIA` `BEGIN PRIVATE KEY`
  `xox[baprs]-` JWT)は**実質0件** — 検出された7行はすべて `task-` が `sk-` に一致した
  誤検出(例 `kit-manifest.json:191` の `KIT-close-task-...`)
- .gitignore:14 `.colabtmux/` — `git check-ignore -v .colabtmux/colabtmux.conf` が
  `.gitignore:14:.colabtmux/` を返す。**未コミットの `!.colabtmux/colabtmux.conf` は死んでいる**
  (親ディレクトリが除外されているので git は中へ降りず、否定は決して効かない)
- .colabtmux/colabtmux.conf:1 「`# colabtmux の設定(書式は TOML)。このファイルはコミットして共有する。`」
  — **追跡する意図はファイル自身が逐語で宣言している**ので、これは問いではなく事実である
- check-ssot.py docs の凍結: 違反9件(CS20 4件 / CS21 4件 / CS22 1件)。
  **いずれもクロージャ(`.gitignore` 2本)の外**であり、手を付けない(F2 のもの)
- 許可リスト方式の実挙動を使い捨ての git リポジトリで実証済み:
  ルートに `.claude` + `!/.claude/`、`.claude/.gitignore` に `/*` + 個別の否定を置くと、
  `directions/` `scripts/` `skills/` `state/` は追跡され、
  `.credentials.json` `history.jsonl` `projects/` `__pycache__/` `skills/colabtmux/` は除外された

<!-- 独立レビューの所見と裁定は 進捗メモ の末尾に在る。 -->

## 進捗メモ(再開点)

- 2026-09-06 段0 完了: guard-branch.py OK(work/2026-09-06-kit-migrate)。
  計器 — 課題票6件 / 残務7行 / 未検証記録0件 / 未回答シート0件
- 2026-09-06 段1 完了: クロージャを `.gitignore` `.claude/.gitignore` の2本に確定。
  作業指示の非交差の見込みの外へは出ていない。基本要件12件を判定(全件 非該当)。
  公開リポジトリであることが判明したため、許可リストの広さを1件だけシートに載せた
- 2026-09-06 段1 で停止(回答待ち): シート docs/sheets/gitignore-recovery.md を提示。
  check-sheet.py は SH4(未回答)のみ NG で、他は通過。
  エージェントからの相談 .claude/missions/2026-09-06-kit-migrate/questions/3.md を自ウィンドウへ提示し、
  中央へ1行、質問音を1回。**回答が来たら逐語 + 日付で「決定シート(回答済み)」へ転記し、シートを削除する**
- 2026-09-06 critical: true のため独立レビューは免除に当たらない(対象2ファイルだが critical)。
  対象集合の確定時点で @review を中央へ1行で要求済み(colabtmux メッセージ7)
- 2026-09-06 08:34 独立レビュー役として `review-060834` が用意された(人間から自ウィンドウへ通知)。
  **依頼はまだ出していない** — 成果物(`.gitignore` 2本の最終形)が人間の回答で確定してから、
  対象・範囲・基準・形式だけを与えて出す(こちらの所見と期待する判定は渡さない)
- 2026-09-06 人間の回答「A」を受領。逐語 + 日付で「決定シート(回答済み)」へ転記し、
  docs/sheets/gitignore-recovery.md を削除した
- 2026-09-06 段2: **SSOT の変更は0件**。起点層の判定 — 00: 変更なし(目的・対象利用者・スコープ・
  受け入れシナリオのどれも動かない。製品コードは不変)/ 01: 変更なし(観測される振る舞いが変わらない)/
  02: 変更なし(構造・分割・契約が変わらない)/ 03: 変更なし(製品の実装詳細ではなく、
  本リポジトリ自身が git で何を記録するかであり、00〜03 のどの層も所有していない事実である)
- 2026-09-06 段3 完了: `.gitignore` を書き換えた。`code_roots` は見直したうえで**足さない** —
  `.gitignore` を変えても製品の振る舞いもテストの結果も変わらない(`.dockerignore` が無いので
  Docker のビルド文脈にも影響しない。製品の試験は一時的な試験用プロジェクトの `.gitignore` を見る)
- 2026-09-06 [DS-04](実行系・コマンドなど環境まわりの選択は AI が決めてよい)
  許可リストをルートの `.gitignore` に置き、キットの `.claude/.gitignore` には触れないと決めた —
  理由: キットの編集は `/kit-improve` だけが行える(CLAUDE.md §6)うえ、`missions/` を外す判断は
  公開リポジトリという本プロジェクト固有の事情に依存する(CLAUDE.md §3 の一般性の制約) /
  見直す条件: キット側が許可リストを持つようになったとき(記録先: `.gitignore` のコメントと残務1行)
- 2026-09-06 段4(タスク内整合確認)完了: SSOT を1文字も書いていないので、文書とコードの差異は
  構造上ゼロ。調査で当たった SSOT の記述(`decisions/auth.md:70`・`MODULE-cli-start.md` 手順12・
  `images.md:159`)はいずれも**製品の振る舞い**を述べたもので、製品コードは不変だから偽にならない。
  `.claude/` を追跡することは `decisions/auth.md:70`(資格情報を git に入れない)と衝突しない —
  資格情報は許可リストで引き続き除外され、20件の `git check-ignore` で実証した
- 2026-09-06 段5: 残務から 2026-09-01 の `.gitignore:4` の行を「直した」として掃き出し、
  発見した2件(キットの `.claude/.gitignore` の穴 / `MODULE-cli-start.md` 手順12 の注意の欠落)を
  1行ずつ足した。原則8 のとおり、範囲外の2件は記録するだけで手を付けていない
- 2026-09-06 段5 の先送り禁止で `make build` を実行 → 終了コード0。
  `.dockerignore` が無いため `.gitignore` は Docker のビルド文脈に影響しないが、規範どおり回した
- 2026-09-06 [DS-04](環境まわりの選択は AI が決めてよい)**`.claude/settings.local.json` は
  追跡しないと決めた** — 理由: 公開集合の最終確認で、この1本にだけ利用者名を含む機械固有の
  絶対パス(`/tmp/claude-1000/-home-<利用者名>-...`、過去のセッション ID つき)が残っていた。
  キットの `.claude/.gitignore` 冒頭は「git では共有する」としているが、そこが挙げている理由は
  「どの複製でも同じ値でなければ同じコードに対して違う判定が出る」ことであり、それに当たるのは
  検証の判定を変える `scripts/*.local.json` である(この2本は追跡し、機械固有の値が無いことを確認済み)。
  settings.local.json は道具の許可リストで判定を変えない /
  見直す条件: 当該の死んだ行が消えたとき(記録先: `.gitignore` のコメントと残務1行)。
  最終確認: 公開される155ファイル全件に対する `grep -lI 't-kubo'` が0件

## 申し送り

- **`workspace/.gitkeep` は実在しないので、複製先に `workspace/` ディレクトリは現れない。**
  パターンは直したので、ファイルを1つ置けば意図どおりに追跡される。置くかどうかは
  「`workspace/` が複製先に存在せねばならないか」という要求の問題であり、
  それを述べた仕様ドキュメントは無い(原則4 により、こちらでは作らない)。
- 独立レビューが挙げた weakest point: `.claude/` の許可はディレクトリ単位なので、
  将来そこへ置かれる未知のファイルも追跡候補になる。現存152本では秘密を検出しなかったが、
  追加時の走査に依存する。ファイル単位の許可に落とすと、キットが1本増えるたびに
  `.gitignore` の更新漏れで黙って取りこぼすので、ディレクトリ単位のままにした。
- 2026-09-06 独立レビュー(`review-060834` / codex)を受領。5点中4点 合格、1点 不合格。
  **合格**: ①秘密の漏洩(資格情報・履歴・実行状態9種はすべて `.gitignore:19` に一致し
  `git ls-files` に0件、追跡152本の秘密走査も0件)②取りこぼし(`stamps.json` を追跡中)
  ③自己復元(`grep -qxF '.claude'` が成功し `claude-dev:1567` は追記しない)
  ⑤人間の決定「A」との一致(道具152本を追跡、missions は0本)。
  **不合格(低)**: ④`.gitignore:2-3` の `workspace/` + `!workspace/.gitkeep` が、
  `.colabtmux` とまったく同じ理由で死んでいる。
- 2026-09-06 所見④の裁定: **直した(実装を直した)**。`.gitignore` はこのタスクのクロージャ
  そのものであり、作業指示も「`.gitignore` の編集を精査し、意図と衝突しないよう整理する」ことを
  求めている。同じ誤りを1つのファイルの中で片方だけ直して残すのは筋が通らない。
  `/workspace/*` + `!/workspace/.gitkeep` に改めた。
  **`workspace/.gitkeep` は作らない** — 一度も存在せず、`workspace/` が複製先に存在せねば
  ならないと述べた仕様ドキュメントも無いので、作れば上流に無いものを作ることになる(原則4)。
  実地に確認: ファイルを置くと `git status` が `?? workspace/.gitkeep` を出す(確認後に削除)。
  `workspace/` 配下の他のものは従来どおり無視される

