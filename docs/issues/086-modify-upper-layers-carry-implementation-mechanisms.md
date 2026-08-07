---
id: 086-modify-upper-layers-carry-implementation-mechanisms
type: modify
severity: 中
found: 2026-08-07
found_in: 階層の点検(人間の指示、2026-08-07)。独立レビュー(サブエージェント)による 00-requests / 01-requirements の全文精読
related: docs/00-requests/decisions/auth.md, docs/00-requests/decisions/env.md, docs/00-requests/decisions/orch.md, docs/00-requests/decisions/sec.md, docs/00-requests/decisions/dist.md, docs/00-requests/terminology.md, docs/00-requests/acceptances.md, docs/01-requirements/functional.md, docs/01-requirements/non-functional.md, docs/01-requirements/usecases.md, docs/issues/083, docs/issues/085
pattern: requirement-states-the-mechanism-instead-of-the-observable
pattern_survey: docs/00-requests/ の全ファイル(request.md / acceptances.md / terminology.md / decisions/ 6件)と docs/01-requirements/ の functional.md / usecases.md / non-functional.md を独立レビューが全文精読し、機械検査 CS18 が見ていない機構を 59 件(00 に 25 / 01 に 34)。system.md は規範により対象外。CS18 が拾う 27 件は docs/issues/083、02-design 側の同型 11 件は docs/issues/085 が持つ。移し先(02/03)に事実が在ることは全件 grep で確認済みで、2件だけ移し先が無い(下記)
summary: 00 の決定・用語集と 01 の条項が実装の機構を持っている。CS18 が見ないパターン(実装ファイルの行番号・環境変数名・起動順・再試行回数・DSN-*/E2E-* の ID)で 59 件
---

# 086 上位層(00 / 01)が実装の機構を持っている

## 症状

`.claude/directions/00-requests.md` は 00 について
「**What it does NOT decide**: system behaviour (01), structure or technology (02), implementation (03)」、
`.claude/directions/01-requirements.md` は 01 について「外から観測できることだけ」と定める。
機械検査 `CS18` は **`MODULE-*` / `MOD-*` / `PLAN-*` / `CTR-*` の ID とコード識別子・パス**しか
見ないため、次の型は**機械にはまったく見えていない**。

### もっとも重い5件 — 00(人間の層)にコードの行番号と関数名がある

| # | 場所 | 原文 | 移し先(実在を確認済み) |
|---|---|---|---|
| 1 | `docs/00-requests/decisions/auth.md:69`(`D0-auth-03`) | 「**`/workspace` にバインドマウントされたホスト側のプロジェクトディレクトリ**である(`claude-dev:749`〜`:766`)」 | `docs/03-impl/contracts/cli-container.md:52` |
| 2 | 同 `:73` | 「**`~/.claude.json` はファイル単位の symlink**(`scripts/entrypoint-claude.sh:199`, `:212`)」 | 同上 / `docs/02-design/architecture.md:199`(`DSN-auth-01`) |
| 3 | `docs/00-requests/decisions/orch.md:237`(`D0-orch-18`) | 「すなわち **`orchestrator/trigger.go::Evaluate` が発火しない場合が「自律継続してよい判断」**である」 | `docs/03-impl/features.md:95` |
| 4 | `docs/00-requests/terminology.md:23`(ブロック対象ドメイン) | 「既定は `scripts/init-firewall-claude.sh` の `BLACKLIST_DOMAINS` 配列に同梱する16件」 | `docs/03-impl/relations/MODULE-firewall-init.md:36,68,82` |
| 5 | `docs/00-requests/terminology.md:26`(資源逼迫) | 「監視デーモンがヘルスファイルに `STATE=WARN` を書き」 | `docs/03-impl/relations/MODULE-vm-mode-healthd.md:21-22,85` |

**リファクタリング1回で 00 が嘘になる。** 00 は人間の層で、実装が変わっても書き換わらないはずの文書である。

### 残り(同型でまとめた件数)

| 群 | 件数 | 代表例 |
|---|---|---|
| 00 の決定が**実現手段そのもの**を固定している | 20 | `D0-env-06` の `container=docker` と「イメージのベースステージの `ENV` で付与」/ `D0-env-09` の委任範囲に `flock` / `mkdir` / `ln -s` を列挙 / `D0-orch-14` の `bubbletea` / `lipgloss` / `D0-orch-16` の `opus/high`・`sonnet/high` / `D0-sec-09` の内容欄が `iptables` しか書いていない(芯の「コンテナ内で制御する」が理由欄にしか無い) |
| `acceptances.md` の技術語(規範が「**No technical vocabulary**」と明記) | 4 | `AC-03`「解釈できない要求は**そのまま Docker へ渡され**、最終的な検証は **Docker 側**に委ねられる」(利用者には通った/止まったしか見えない) |
| 01 の内部トポロジ・内部資源名 | 5 | `FR-env-07-1` の `DOCKER_HOST=tcp://claude-dev-docker-proxy:2375` / `FR-env-02-3` の `claude-dev-config`・`claude-dev-history` ボリューム名 |
| 01 の内部手順・起動順・内部修復 | 6 | `FR-env-11-1`「**VNC サーバ → ウィンドウマネージャ → Chrome → noVNC** を起動し」(**内部プロセスの起動順そのもの**)/ `FR-env-02-4`「一時的な空き ID へ退避」 |
| 01 の再試行回数・ポーリング周期 | 4 | `FR-env-11-5`「最大 20 回まで再試行」/ `FR-env-03-3`「**30 秒ごとに**変更を検知し」— 規範が置き換えテストの代表例として名指しする型 |
| 01 の内部データ形式 | 2 | `FR-orch-05-9`「**追記型ログ(JSON Lines)**」「**追記時に同期書き込みを行わない**」「**製品コードはこれらのログを読み戻さない**」 |
| 01 がプロンプトの組み立て仕様を持つ | 1 | `FR-orch-02-3` の4種の列挙。**直後のコメントが「`DSN-prompt-03` の列挙と1項目も違えないこと」と 02 との二重管理を明文で要求している** |
| 用語集が「実装名」と宣言した語を 01 が使っている | 1(5箇所) | `terminology.md:30` が「bubblewrap / bwrap / landlock は実装名。方針を語るときは『Codex サンドボックス』と書く」と定めているのに、`functional.md:329,331,334` と `usecases.md:211,220` が landlock を使う |
| CS18 のパターン外の下位層 ID | 2(13箇所) | `DSN-env-03`(02 の設計判断 ID)を 01 が名指す / `E2E-05` `E2E-03` `E2E-04`(02 が UC から導出する ID)を `non-functional.md` と `decisions/dist.md` が名指す |
| `non-functional.md` の測定方法が白箱化 | 8 | `NFR-sec-03`「**`orchestrator` の単体テスト**が、起動スクリプトに **`unset SLACK_BOT_TOKEN`** が含まれることを固定している」(要件が「どのテストが在るか」まで抱えており、テストを追加すると 01 が古くなる)/ `NFR-ops-04`「**ポリシー定義が 1 ファイルに閉じている**」(コード構造の要求) |
| `usecases.md` のフロー記述 | 1(8箇所) | 「**403** で拒否」「**502** を返して」(02 の契約が既に持つ)/「`DOCKER_HOST` が docker-proxy を指す」 |

**移し先に事実が無いのは2件だけ**である: `D0-env-02` の **ControlMaster**(02/03 に記述なし)と、
`NFR-ops-02` の「**コンテナ内資産のコードに OS 判定が無い**ことを確認する」という測定
(03 のテスト側に受け皿が無い)。**残りはすべて 02/03 に同じ事実が在り、00/01 は重複を抱えている
だけである** — 落としても情報は失われない。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 認証の受け渡し・ファイアウォールの既定値・トリガの発火条件 | `03-impl/` が `path:line` つきで持つ | 00 が同じ事実を行番号ごと持っている | **要件・設計が正**(00 から落とす。事実は 03 に残る) |
| 起動順・再試行回数・ポーリング周期 | `03-impl/contracts/` と `MODULE-*` が持つ | 01 が条項として持っている | **要件・設計が正**(01 は観測できる結果だけを持つ) |

**実装の誤りではない。** コードは1行も動かない。

## 未解決の論点(人間の裁定が要る)

**00 の決定台帳に技術選定を書いてよいのか。** 規範は 00 について「technology は決めない」と書く
一方、`決定` は「人間が何をどう決めたか」を記録する器であり、**技術の選択そのものが人間の決定で
あることは実際にある**(`D0-orch-14` の TUI ライブラリ、`D0-env-03` の VM 方式)。この境界は
規範に明文が無い。**ここをどちらに倒すかで、上の 20 件と、01 側で「00 由来だから免責」とした
15 件前後の扱いが変わる**(00 を「技術を決めてよい」とするなら 01 の免除も失効し、01 の違反件数が
増える)。キット側の論点として `.claude/improvements/KIT-where-technology-decisions-belong.md` が
追跡する。

## どう直すか(案)

1. **00 の行番号5件は即座に落とせる**(移し先に事実が在り、決定の意味も変わらない)。
2. 01 の内部手順・再試行回数・起動順(15 件前後)は**観測できる言い方へ書き替える**。条項 ID は
   1つも動かさない(CS16)。
3. `acceptances.md` の4件と用語集の定義欄は、**利用者の言葉かどうか**の線引きが要るので人間の裁定。
4. 上の「未解決の論点」が決まるまでは、**00 の決定に技術名が在る 20 件は保留**する。

**着手はタスクとして起こすこと**(01 の条項本文が動くので `/doc-check` と 02 のカバレッジ表の
確認が要る)。`docs/issues/083` `085` と同じ点検の結果であり、3件は同時に扱うのが効率的である。
