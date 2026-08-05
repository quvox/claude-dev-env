---
id: task-spec-measurability-memo-3
rotated_from: memo.md
rotated_at: 2026-08-05
phase_at_rotation: 実装 → 反映(フェーズ3 末)
summary: フェーズ1〜3 で帰着した未決点8件と、フェーズ2・/doc-check の調査メモ(実測値・独立レンズの裁定)
---

# memo-3(フェーズ3 末のローテーション)

`memo.md` から転出した**解決済みの内容**である。`memo.md` が唯一の入口であり、
このファイルは `memo.md` の「未決点」節と「調査メモ」節からのポインタで到達する。

**転出の理由**: 8件の未決点はすべて帰着し(3件は `/task-close` の手順としてタスクリスト
5・6・7 番が引き継ぎ、3件はキット課題として `.claude/improvements/` が引き継いだ)、
調査メモの実測値は変更指示 26 件の本文へ書き込み済みである。

## 未決点

| # | 未決点 | 帰着 | 検出元 |
|---|---|---|---|
| 1 | **`02-design/logging.md:97`・`:98`(追記型ログの `dispatch` / `result`)の対応要件が `NFR-ops-01` だけ**である。廃止後にこの2行をどうするか。行ごと削除すると**実装は `audit.jsonl` へ出し続けるのに 02 の方針に無い**状態になり、02⇄03 の差分になる。`FR-orch-05` 受入基準8・9 は追記型ログの一貫性・耐久性を定めるが、**ログの存在そのものは要求していない**(実測) | フェーズ2 の下降で解決する。**方針**: 行は残し「対応要件: なし(`NFR-ops-01` 廃止に伴う。実装は出力を継続)」と明記して差分を可視化し、`docs/issues/` へ起票する(原則8・原則2)。**この方針で不都合なら質問キュー#1 としてフェーズ2 末に提示する** | 2026-08-05 フェーズ1(概念#6 の回答の波及を実測) |
| 2 | **`request.md` の MINOR 更新で失効する合格証の範囲**。`source` に `request.md` を持つのは `terminology.md` / `acceptances.md` / `decisions/` 6本 / `01-requirements/` 3本。うち `decisions/auth.md` / `dist.md` / `01-requirements/system.md` は**本文を触らない**が再認証が要る | closure に「本文は変更なし・合格証の再発行が要る」として計上済み(`source:` にも入れたので `close-task.py` のゲート (b) が数える)。フェーズ2 の `/doc-check` で確認する | 2026-08-05 フェーズ1(概念#5 の回答の波及を実測) |
| 3 | **`terminology.md` の「安全」の定義に含まれる「ホストのあらゆる情報を破壊しないこと」が、そのままでは測定不能語に近い**。用語集は全層の規範なので、`NFR-sec-01` の4項目(生ソケット・秘密鍵・イメージ焼き込み・confinement)と `FR-env-07`(Docker 操作の拒否規則)を参照する形にして観測可能にする必要がある | **ドキュメント記載で解決済み**(委任 b)。用語集の定義に「観測可能な形は `NFR-sec-01` と `D0-env-08` が定める」を付し、含む例・含まない例を2件ずつ置いた。人間の定義の文言そのものは変えていない | 2026-08-05 フェーズ1(概念#5 の回答を書き下すときに検出) |
| 4 | **`docs/03-impl/index.md:85` の「01(要件)との差異」表が `NFR-ops-01` をキーにしている**。同要件を削除すると実在しない ID を指す行が残る。`index.md` は生成物であり**変更指示の `target` にできない**(`.claude/directions/03-impl.md`) | **手順で解決する**(ドキュメント記載でも委任決定でもない)。`/task-close` §2 と `/doc-check` が `index.md` を書く担当なので、**タスクリスト 5 番**として明示し、追跡先を `docs/issues/014`(追記型ログの必須フィールド)へ寄せる。014 は 02⇄03 の差分として別行が既に追跡しているので、差異表の当該行は削除でよい | 2026-08-05 フェーズ2 パス1(2 NFR の参照を全文走査して検出) |
| 6 | **`00-requests/decisions/sec.md:29` の検証履歴コメントが、本タスクが削除する `docs/issues/041` を参照する。** 変更指示の対象にしない設計(コメントは `/doc-check` の持ち物)だが、**タスクリストに追跡項目が無かった**(#5 は `index.md` 専用)。task モードの `/doc-check` は SSOT を書けないので、放置すると反映後に宙吊り参照が残る | **手順で解決する**。タスクリスト **6番**を新設し、`/task-close` の反映後の認証で当該1行を削除する担当を明示した | 2026-08-05 フェーズ2 `/doc-check`(委任 c の実行漏れを全数走査で検出) |
| 7 | **`check-changeset.py` の CS9(02 PLAN ⇄ 03 MODULE)が一度も走っていない**。正規表現が PLAN-ID をバッククォートで囲んだ表行だけを拾うのに対し、`docs/02-design/relations.md` の「一覧」表 64 行は囲んでいないため、毎回「未検査」を返す(`/doc-check` の検査 E の機械側が丸ごと無効) | **記録済み**。`docs/issues/060` の「追加(2026-08-05)」節と `.claude/improvements/KIT-changeset-cs2-closure-and-deletes-as-sections.md` の両方が既に持っている。**2026-08-05 の `/doc-check` は同じ照合を手で実行して代替した**(合成ビューの PLAN 64 行 × callers/callees/contracts = 実質違反0件。唯一の差分 `PLAN-orchestrator-main` は callees セルの散文をカンマ分割した解析上の見かけで、集合としては一致する) | 2026-08-05 `/doc-check`(独立レンズも同じものを独立に検出) |
| 8 | **コールグラフの生成先を規範どおり(`new-features/03-impl/callgraphs/`)にすると `check-changeset.py` の CS1 が 25 件落ちる**。`change-set.md` は「変更指示ではない」と書き `close-task.py` は除外しているのに、`check-changeset.py` だけが除外していない。「B6 を staged で回すこと」と「CS1 を通すこと」が同時に成立しない | **キット側の課題**。`.claude/improvements/KIT-callgraph-output-during-task.md` の「追加(2026-08-05)」節に実測つきで記録した。**本タスクでは CS1 を優先して staged を生成しない状態に戻し**、`build-callgraphs.py --check` は SSOT 側に対して実行した(コード差分が空なので staged と SSOT は byte 一致する。`go.md` の `diff` で確認済み)。SSOT 側は `index.md` の HTML コメント文面だけが抽出器の現行テンプレートと違うが、**コードの内容は同一**であり `/task-close` の再生成で自然に解消する | 2026-08-05 `/doc-check`(B6 を規範どおり実行しようとして検出) |
| 5 | **`check-changeset.py` の CS2 が違反1件を返し続ける**(`MODULE-firewall-init: caller が存在しない: MODULE-entrypoint-claude`)。CS2 は caller/callee を `new-features/` の中だけで解決するため、**部分的な relations 編集は原理的に通せない**(満たすには推移閉包で 83 本すべての変更指示が要る) | **キット側の課題**。`.claude/improvements/KIT-changeset-cs2-closure-and-deletes-as-sections.md` に記録した。ドキュメントを歪めて通すことはしない。`/doc-check` の検査 F で同じ違反が出るので、**既知の誤検出として申し送る** | 2026-08-05 フェーズ2 §4(CS1〜CS10 の実行) |


### 2026-08-05 の再実測(タスクリスト0番。1本目・2本目の反映後の SSOT に対して)

**`017` の残存(語境界なしの一括 grep。`callgraphs/` を除外)= 10 箇所**。2本目の申し送りどおり
`03-impl/relations/` の「安全に」「素早く」は **0 件**で、旧 memo が挙げた4ファイルのうち
実際に受け皿があるのは `MODULE-makefile-update-claude` と `MODULE-vm-mode-healthd` の2本だけである。

| 箇所 | 語 | 起点層 | 扱い |
|---|---|---|---|
| `00-requests/request.md:7` | 安全な | 00 | 概念シート #5 |
| `00-requests/decisions/scope.md:80`,`:84` | 軽微な | 00 | 概念シート #3 |
| `00-requests/decisions/env.md:106` | 安全に | 00 | 委任 b |
| `01-requirements/usecases.md:98` | 安全な操作 | 01 | 委任 b |
| `01-requirements/functional.md:332` | 必要な文脈だけ | 01 | 概念シート #4 |
| `02-design/relations.md:92` | 高速更新 | 02 | 論点5 → 03 の3箇所へ波及 |
| `02-design/logging.md:69`,`:107` | 必要な範囲を超えて出さない | 02 | 論点5 |
| `03-impl/relations/MODULE-vm-mode-healthd.md:21`,`:89` | RAM 逼迫 | 03 | 論点5 |

**`資源逼迫` の下降先(`044` の残作業 (b)(c))= 6 箇所**:
`functional.md:221`(`FR-env-08` #4)/ `architecture.md:87` / `system.md:61` /
`logging.md:102`,`:129` / `relations.md:99`。
**`non-functional.md:67`(`NFR-ops-01`)は既に `terminology.md` を参照済み**なので対象外。
03 側(`features.md:102` / `MODULE-vm-mode-healthd.md:14`,`:17`,`:36` / `relations/index.md:89`)は
**定義のある語なので書き替え不要**(`RAM 逼迫` の2箇所だけが対象)。

**`043` の5件の現状**(`non-functional.md`。3列を再確認済み)と、**`NFR` のテスト対応表 15 行が
全件「未検証(テスト未実装)」**であること(`DSN-test-01` により自動テストランナーを設けない方針)。
したがって測定可能化とは **`測定方法` 列を実機確認の手順として具体化すること**であり、
**新しいテスト行は増えない**(論点1 が案B なら2行の状態だけが変わる)。

**`041` の実装再確認**: `scripts/init-firewall-claude.sh` の `BLACKLIST_DOMAINS` は
**paste 系9 / webhook テスト系3 / トンネル系4 = 有効20件ではなく16件**、加えて本番環境の雛形2件が
コメントアウトされている。**旧 memo の「既定20件」は実測と食い違う**ので、変更指示では
実測値(16件 + 雛形2件)を書くこと。

**`042` と `049` は同一事象**(`AC-02` の期待結果と不合格条件)。`049` の修正案は
「**Web アプリ用のポート**は公開されない」で、`042` の案A(「利用者のアプリケーションが待ち受ける
ポート」)と同義。**`AC-02` の主題が「Web アプリをクライアントのブラウザで確認」である**ため
`049` の言い回しを採る。

### 2026-08-05 フェーズ2 独立レンズの指摘と裁定(不変則2)

**レンズ: サブエージェント**(`Explore` / `sonnet`。reasoning は Agent ツールに指定口が無いので
セッションの値)。**Codex ではない**(利用上限。復旧 2026-08-11)。読み取り 54 ファイル、
`git status` に変異なし(Explore は書き込み不可)。verdict は `fail`(指摘6件)。

| # | 重大度 | 指摘 | 裁定 | 対処 |
|---|---|---|---|---|
| F1 | 高 | `contracts/entrypoint-firewall.md` の `sections` が H1 なので、配下の5節が反映後に消えるのか残るのか一意でない | **誤検知(記法の解釈)+ 妥当な危険の指摘**。節は「次の見出しの直前まで」であり `terminology.md` の `# 用語集` も同じ規則で書いている。ただし反映者が H1 を「文書全体」と解釈する余地は実在し、契約の異常系・設計判断が消えると 02⇄03 が壊れる | **自動修正**: 5節を「変更対象ではない・1節も削除しない」と本文の注記で明示した |
| F2 | 高 | `02-design/system.md` の要件カバレッジ節の総括文が「**NFR 15 件**」のまま。2件削除したので 13 が正しい | **確認済み・自動修正可能**(私の書き漏らし。同じ節の中にあるのに追随していなかった) | **自動修正**: 13 件へ訂正 |
| F3 | 中 | `tests/orchestrator.md` の全件表で #35 が欠番になり、冒頭の「48 行 / 表の行数は 49」も食い違う | **確認済み・自動修正可能**(私が行削除後の繰り上げを途中で止めていた) | **自動修正**: 旧#36 以降を繰り上げて連番 1〜48 にし、冒頭を「47 行 / #37 が例外 / 行数 48」へ訂正 |
| F4 | 中 | `03-impl/index.md` が実在しなくなる `NFR-ops-01` を指し続けるのに、26 ファイルのどれも対象にしていない | **確認済み(既知)**。パス1 で同じものを検出済み(未決点#4)。`index.md` は生成物で変更指示の `target` にできないため、closure に理由付きで記載し**タスクリスト5番**で `/task-close` に処理させる | 対処済み(手順) |
| F5 | 低 | `features.md` の概要だけ「(ビルドキャッシュを使う)」を欠き、`relations.md` / MODULE `summary` と食い違う | **確認済み・自動修正可能** | **自動修正**: 3箇所を同一文言へ揃えた |
| F6 | 中 | frontmatter 直後の HTML コメントの更新指示が「対応する行を削除する」だけで、削除後の文面が反映者の解釈に委ねられている | **確認済み・自動修正可能**(指摘のとおり再現できない粒度だった) | **自動修正**: `non-functional.md`(6行)と `functional.md`(3行)について**削除する行を逐語で引用**し、コメントの閉じ方まで書いた |

**weakest_point の指摘(F1 と同じ箇所)は妥当**だったので、注記を足す形で潰した。
残存リスクとして挙がった「ブロック対象ドメインの実件数はコードからしか検証できない」は、
本レポート作成者がコードを読まない設定だったことによる(こちらはパス2 で実測済み。調査メモ参照)。

### 2026-08-05 フェーズ2 パス2(技術調査。1行1事実・`path:line`)

- `orchestrator/claudebin.go:78` — `claudeChildEnv()` が `stripEnv(os.Environ(), "SLACK_BOT_TOKEN")` を返す。
- `orchestrator/worker.go:386` — 子プロセスに `cmd.Env = claudeChildEnv()` を設定する。
  **worker とレビューアーはこの `RunPrompt` 経路を共有する**(`ClaudeRunner` インターフェース経由)。
- `orchestrator/mode.go:136` — 対話 Claude の起動スクリプトが `unset SLACK_BOT_TOKEN` を書き込む。
  → **3種すべてで通知トークンが除かれる**ことをコードで確認した(`NFR-sec-03` の新しい目標値が実装と一致する)。
- `orchestrator/config.go:85`〜`:86` — `SLACK_BOT_TOKEN` / `SLACK_CHANNEL` をコントローラが読む。
  **環境変数から読む秘密はこの1つだけ**である(他の `os.Getenv` は `COMPOSE_PROJECT_NAME` /
  `TMUX` / `CLAUDE_DEV_VM` で秘密ではない)。認証情報は共有ボリューム上のファイルとして渡る。
  → `NFR-sec-03` の目標値を「`02-design/logging.md` が挙げる秘密すべて」と書くと**実装より厳しくなる**
  ので、**`SLACK_BOT_TOKEN` 1つに限り、それが唯一の環境経由の秘密である理由を添える形へ直した**
  (memo の「やらないこと」= 目標値を新しく厳しくしない、に従った)。
- `docs/03-impl/relations/MODULE-vm-mode-healthd.md` の引数表 — `VM_HEALTH_INTERVAL` / `_CPU_PCT` /
  `_SUSTAIN` / `_COOLDOWN` の既定 15 / 60 / 12 / 600 を**既に記載済み**。
  → 00 の用語集から環境変数名を落として「上書き手段は 03-impl」と書いても、**指す先は実在する**。
- `scripts/init-firewall-claude.sh:38`〜`:64` — 有効16件(paste 系9 / webhook 系3 / トンネル系4)+
  コメントアウトされた本番雛形2件。**旧 memo の「20件」は誤り**。

**`054`(削除済み issue への参照)**: 前タスクの申し送りが挙げた `decisions/orch.md:199` は
**2026-08-05 に解消済み**(`058`/`059` へ付け替え)。本タスクに残るのは、**本タスクが削除する
6 issue を参照している検証履歴コメント8箇所**(委任 c)である。

### 2026-08-05 `/doc-check`(2回目)のパス2(技術調査。1行1事実・`path:line`)

- `scripts/init-firewall-claude.sh:133` — `echo "Blocked domains: ${#BLACKLIST_DOMAINS[@]}"`。
  `:134` — `echo "Blocked IPs in ipset: $(ipset list blacklisted-domains … | grep -c '^[0-9]')"`。
  → **`FR-env-05` に新設した受入基準7(件数2つを起動ログへ出す)は既存の実装の写しである**。
  コード変更は要らない(本タスクの「やらないこと」を守れている)。
- `scripts/init-firewall-claude.sh:38`〜`:64` — 本番雛形2件は**配列要素ではなくシェルのコメント**である。
  したがって `${#BLACKLIST_DOMAINS[@]}` は 16 であり、`:65`〜 のループにある
  `[[ "$domain" =~ ^#.*$ ]] && continue` は**この2件には作用しない**(防御的な保険)。
  → `MODULE-firewall-init` の変更指示が「配列の読み出しがコメント行を飛ばすため登録されない」と
  書いているのは**機序の説明としては不正確**だが、結論(16件が塞がれる集合)は正しい。**低**として報告した。
- `orchestrator/claudebin.go:77`〜`:79` — `claudeChildEnv()` は
  `augmentPathForClaude(stripEnv(os.Environ(), "SLACK_BOT_TOKEN"))`。
  `orchestrator/worker.go:386` と `orchestrator/mode.go:50` が両方これを使う。
- `orchestrator/mode_test.go:36`〜`:39` — **対話 Claude の起動スクリプトに `unset SLACK_BOT_TOKEN` が
  含まれることを固定する単体テストはある**。
  一方 **`claudeChildEnv()` を直接固定する単体テストは1件も無い**(`orchestrator/*_test.go` を全数走査)。
  → `NFR-sec-03` の測定方法が「worker とレビューアーは単体テスト、対話 Claude は実機確認」と
  **実態と逆に書かれていた**。本実行で実態に合わせて直した(自動修正#1)。
- `orchestrator/dashtui.go:180` / `MODULE-orchestrator-dashboard.md`「処理の流れ」8 —
  ダッシュボードは `$HOME/.claude-dev-vm/health` を読み `STATE=WARN` で赤いバナーを出す。
  単体テスト4件(`orchestrator/dashboard_test.go::TestReadVMHealthBanner_*`)つき。
  だが**この正常系を要求する受入基準はどこにも無い**(`FR-orch-08` 受入基準7 は異常系だけ)。
  → 本タスクの範囲外なので `docs/issues/063` を起票した。
- `scripts/vm-healthd.sh:28`〜`:31` — 既定 `INTERVAL=15` / `CPU_PCT=60` / `SUSTAIN=12` / `COOLDOWN=600`。
  用語集「資源逼迫」の3数値(60% / 15 秒 / 12 回)と一致する。
- `.devcontainer/Dockerfile.claude:318`〜`:465` — `vnc-base` ステージ(`FROM base`)が導入するのは
  **VNC 系だけではない**。`tigervnc-standalone-server`(**`x11vnc` ではない**)/ `python3-websockify` /
  `openbox` / `lxterminal` `xterm` `xclip` `x11-xserver-utils` `xdotool` /
  `ibus` `ibus-mozc` `ibus-gtk*` `mozc-utils-gui` `dbus-x11` `im-config` /
  `libglib2.0-bin` `dconf-cli` `dconf-gsettings-backend` `dbus-user-session` /
  `libxss1` `libatspi2.0-0` / `fonts-noto-cjk-extra` `fonts-dejavu-core` /
  `google-chrome-stable`(amd64)/ noVNC v1.6.0 / `rmcp-xdotool`(cargo)/ `ja_JP.UTF-8` ロケール。
  **ウィンドウマネージャは `FR-env-11` 受入基準1、日本語入力は同受入基準3 が要求している。**
  → `NFR-perf-02` の目標値(2)を「VNC 系(`x11vnc`)・Chrome・その依存以外は1件も現れないこと」と
  書くと、**`FR-env-11` が要求する資産を禁じることになり必ず不合格になる**。本実行で6カテゴリの
  割り当て方式へ直した(自動修正#4)。
- `.devcontainer/Dockerfile.claude:506`(`claude-cli`)と `:534`(`claude-vnc`)— **両ステージが
  等しく Claude Code と Codex CLI を導入する**。したがって同梱エージェント CLI の層は
  「ブラウザ確認ありだけが持つ追加層」ではない。目標値にその旨を明記した。
- `orchestrator/worker.go` の `Worker.BuildPrompt` — 4種の前に `VMModePreamble()` と
  `LoadProjectPolicy(w.Workspace)`(= `ORCHESTRATOR.md` の内容)を、末尾に固定文字列
  `workerResultGuide` を必ず書き込む。`orchestrator/mode.go:74`・`:91`・`:167` も同じ3種を前置する。
  **`FR-orch-08` 受入基準5 が `ORCHESTRATOR.md` の前置を要求している**ので、
  「4種だけ」と書くと 01 が 01 と衝突する。本実行で「**タスク固有の文脈**を4種だけ」へ直した(自動修正#5)。
  02 側の `DSN-prompt-03` も同じ「だけ」を持つが本タスクの影響範囲外なので `docs/issues/064` を起票した。

