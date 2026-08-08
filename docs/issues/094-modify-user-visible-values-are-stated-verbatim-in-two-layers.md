---
id: 094-modify-user-visible-values-are-stated-verbatim-in-two-layers
type: modify
origin_layer: 02
severity: 中
found: 2026-08-08
found_in: /doc-check task-layer-placement(独立レビュー(サブエージェント)2本の A4 指摘を裁定して確定。合成ビューの走査)
related: FR-env-12-5, FR-orch-03-3, FR-env-01-18, FR-env-01-16, D0-dist-04, D0-env-06, DSN-dist-02, CTR-cli-orchestrator, CTR-cli-container, docs/02-design/logging.md
pattern: 利用者が見る値(既定値・文字集合・鍵と値の組)が、上流の層と下流の層に逐語で独立に書かれている
pattern_survey: "`.claude/scripts/` に専用の検査は無いため、バッククォート語の層またぎ出現を機械で洗い出した(下の「同型の全件」に手順を記録)。**2026-08-08 に走査条件を直して再実行した**: 起票時の走査は「01 を必ず含む組」だけを見ており **00⇄02 の重複を構造的に見落としていた**。00⇄02 のみの候補 35 件を追加で数え、名前(対象外)を除いた結果 **値の重複は 5 件・のべ 15 箇所**である(起票時は 4 件・13 箇所)"
summary: 既定値・受理する文字集合・設定の鍵と値の組が 2 つ以上の層に逐語で書かれており、どちらを直せば正になるかが決まらない
---

# 094 利用者が見る値が複数の層に逐語で在る(所有者が2つ以上)

## 事象

`.claude/directions/layer-fit.md` §0 は「**同じことが2つの層に在る**」を「所有者が2つになり、必ずずれる。
ずれた後、**どちらが正かを決める根拠がどこにも無い**」として §3 の重大度「高」の第1条件に挙げている。
仕様ドキュメントには、**利用者が見る値**についてこの状態が 4 件ある。

**鍵や環境変数の「名前」が複数層に現れるのは本 issue の対象ではない。** 名前は外部インターフェース
そのものであり、01 が約束し 02 が契約として列挙するのは正しい。問題になるのは**値**である。

## 同型の全件(5 件 / のべ 15 箇所)

走査手順(再実行できる形で残す):

```bash
# 01 と 00/02 の両方に現れるバッククォート語を出し、値らしいもの(= を含む / 数値 / 文字クラス /
# アンダースコア付きの設定キー)に絞る。ID(FR-*/DSN-* など)は除外する。
python3 - <<'PY'
import re,glob,collections
pat=re.compile(r"`([^`\n]{3,60})`")
layers={"00":glob.glob("docs/00-requests/**/*.md",recursive=True),
        "01":glob.glob("docs/01-requirements/**/*.md",recursive=True),
        "02":glob.glob("docs/02-design/**/*.md",recursive=True)}
idx=collections.defaultdict(lambda: collections.defaultdict(list))
for L,fs in layers.items():
    for f in fs:
        if f.endswith("index.md"): continue
        for n,l in enumerate(open(f),1):
            for tok in pat.findall(l):
                if re.match(r"^(FR|NFR|SR|UC|AC|RQ|D0|D1|DSN|CTR|MODULE|MOD|PLAN|E2E|P-)[-0-9]", tok): continue
                idx[tok][L].append(f"{f}:{n}")
for t,d in idx.items():
    if len(d)>=2 and "01" in d and ("00" in d or "02" in d):
        print(t, dict((k,v[:3]) for k,v in d.items()))
PY
```

結果は候補 29 件。うち 25 件は**名前**(`--vm` / `--yes` / `DOCKER_HOST` / `max_workers` など)で対象外。
残る 4 件が値の重複である。

**★2026-08-08 の走査条件の訂正**(`/doc-check ssot task-layer-placement`)。上の走査は最終行の
`if len(d)>=2 and "01" in d and (...)` で **`01` を必ず含む組だけ**を出しており、
**`00` と `02` にだけ在る重複を構造的に見落としていた**。同じスクリプトの最終行を
`if "00" in d and "02" in d and "01" not in d` に替えて再実行すると候補 35 件が出る。
うち 34 件は**名前**(`claude-dev.managed` / `DOCKER_HOST` / `--security-opt` / `~/.claude` など)、
および**選択を裏づける実測の引用**(`CLONE_NEWUSER` / `mount --make-rslave /` / `docker-default`。
`D0-dist-04` の理由と `DSN-dist-02` の理由が同じ実測を引くのは、実測が判断の根拠であって
値の重複ではない)で対象外である。**値の重複として残るのは #5 の 1 件**で、これは
**トークン単位の走査では原理的に出ない**(00 は `container=docker` と 1 トークンで書き、
02 は変数名の欄と既定値の欄に分けて書くため、同じトークンにならない)。
**したがってこの型の走査はトークン一致だけでは閉じない** — 値が表の列に分かれて書かれる形は
人が読んで拾う必要がある。

| # | 何が重複しているか | 層と `path:line` | 重大度 |
|---|---|---|---|
| 1 | **Codex サンドボックスの既定 3 鍵と値**(`sandbox_mode = "danger-full-access"` / `approval_policy = "never"` / `[features] use_legacy_landlock = true`)と「書かれていない鍵だけを追記する」規則 | **00** `docs/00-requests/decisions/dist.md:85`(`D0-dist-04` 項6)/ **01** `docs/01-requirements/functional.md:343`(`FR-env-12-5`)/ **02** `docs/02-design/architecture.md:236`(`DSN-dist-02`) | 高(**3層**) |
| 2 | orchestrator の設定 6 キーの**既定値**(`5` / `3` / `10` / `2` / `10` / `merge`) | **01** `docs/01-requirements/functional.md:403`(`FR-orch-03-3`)/ **02** `docs/02-design/contracts/cli-orchestrator.md:42`〜`:47`(受け渡す設定の表の「既定値」欄) | 中 |
| 3 | `stop <name>` が受理する**文字集合** `[A-Za-z0-9._-]` | **01** `docs/01-requirements/functional.md:99`(`FR-env-01-18`)/ **02** `docs/02-design/system.md:522`(SCR-01 の型欄)・`docs/02-design/logging.md:95`・`docs/02-design/contracts/cli-container.md:130`(規則 B)・同「ロックキーとして使える文字」 | 中(**5箇所**) |
| 4 | 排他待ちで中止したときに出す**保持者の表し方**(プロセス ID) | **02 の内部で矛盾**: `docs/02-design/contracts/cli-container.md:125`(エラーケース。プロセス ID を固定)/ 同「排他(ロックキー)」の末尾(「**保持者をどう記録するかは実装手段の選択であり `D0-env-09` で AI に委任している**」と書く)/ `docs/02-design/logging.md:80`(プロセス ID を必須の出力項目にする) | 中 |
| 5 | **コンテナ内動作の判定マーカーの値** `container` = `docker` | **00** `docs/00-requests/decisions/env.md:139`(`D0-env-06` の「内容」欄が値そのものを書く)/ **02** `docs/02-design/contracts/cli-container.md:65`(「渡す環境変数」表の `container` 行。型・値域も既定値も `docker`)。**`D0-env-06` は同じ項目の末尾で「変数の名前と値の形式は 02 の契約 `CTR-cli-container` が定める」と書いており、1 つの決定事項の中で所有者が 2 つになっている** | 中 |

## なぜ今すぐ直さないか

`task-layer-placement`(2026-08-07〜08)は 4 件すべてを**現物で確認した**が、直すには
`docs/02-design/architecture.md`(#1)・`docs/02-design/logging.md`(#3・#4)を影響範囲へ入れる必要があり、
どの層を所有者にするかは**規範側の判断**(01 は約束・02 は契約の欄・00 は人間の選択、のどれが値を持つか)である。
同タスクの決定シートは「語の**種類**」の線(概念1)は引いたが、「**同じ語が複数層に在るときどこが所有者か**」の線は
引いていない。**その線を引くのが本 issue の起点であり、起点層は 02 である**(01 は約束を持ち続けてよく、
落とす/残すを決めるのは設計の側だから)。

## どう直すか

1. **#1**: 00 は人間の選択(「既定では自前サンドボックスを使わない / 読み取り専用要求のために
   バックエンドを有効化する」)だけを持ち、鍵と値は 01 の `FR-env-12-5` を所有者にする。
   02 の `DSN-dist-02` は列挙を `FR-env-12-5` への指し先へ替える。
2. **#2**: 既定値の所有者を 01 と 02 のどちらにするかを決める。**02 の契約表は「既定値」を欄として
   持つのが仕様の形**なので、01 側を「設定ファイルで変更できること(既定値は 02 の契約が定める)」へ
   寄せる案が有力。
3. **#3**: 文字集合の literal を `CTR-cli-container`「ロックキーとして使える文字」1 箇所に寄せ、
   他の 4 箇所はそこへの指し先にする(01 は観測できる約束なので literal を持ってよい、という
   反対案もある。決めるのが本 issue)。
4. **#4**: `CTR-cli-container` の「エラーケース」と `logging.md:80` を「保持者を特定できる情報」へ
   揃え、プロセス ID という具体は `MODULE-cli-common-lock` の「実装上の判断」に置く
   (`D0-env-09` の委任範囲に戻す)。
5. **#5**: `D0-env-06` の「内容」欄から値 `container=docker` を落とし、決定としては
   「systemd/podman の慣習に沿った恒久マーカーをイメージ側で常時付与する」という**選択**だけを残す
   (末尾の「値の形式は 02 が定める」がそのまま生きる)。値の所有者は
   `CTR-cli-container`「渡す環境変数」の `container` 行 1 箇所にする。**00 の意味に触れる編集なので
   決定シートが要る**(`.claude/directions/layer-fit.md` §2.1)。

## 経緯

- 2026-08-08 起票。`/doc-check task-layer-placement` の独立レビュー(`lens: subagent`)2 本が
  #1・#2 を重大度「高」、#3・#4 を「中」で独立に検出。裁定の結果、**いずれも本タスクより前から
  在る SSOT 側の矛盾**であり、`/doc-check` §0 の書き込み表に従って本 issue へ記録した
  (task モードは SSOT を直さない)。
- 2026-08-08 `/doc-check ssot task-layer-placement`(反映後)。**#5 を追加し、走査条件の欠陥を記録した。**
  独立レビュー(`lens: subagent`)2 本が #1 を**再び重大度「高」で独立に検出**し(A 層のレンズは
  `FR-env-12-5` 側、02 層のレンズは `DSN-dist-02` 側)、うち 1 本が `D0-env-06` の自己矛盾(#5)を
  新規に検出した。#5 は**起票時の走査が構造的に見落とす集合**(00⇄02 のみ、かつ値が表の列に
  分かれている)に属していたため、走査条件を直して再実行し、母集団を 4 件 → 5 件へ訂正した。
  **#1 の severity は起票時の裁定どおり「中」に据え置いた**(理由: 直しが 00 の意味に触れるため
  この実行では閉じられず、`.claude/directions/layer-fit.md` §3 が既存文書の置き場の誤りを
  「数えて順に片づける」機構(`issues-pendings.md` §3.1)に委ねている。**この据え置きは
  AI の裁定であり、人間は下の「どう直すか」に答えることで覆せる**)。
