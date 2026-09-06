---
id: 2026-09-06-kit-migrate
date: 2026-09-06
record: なし(taskless — flow: kit-migrate)
critical: false
origin_layer: kit
issue: なし
summary: キットの版上げの据え付け。移行台帳のうち mechanical 1件(colabtmux.conf の discuss-1 除外)を適用し、docs/residual.md の1行を新しい版に照らして失効させた。judgment 4件は判断待ちのまま残す
---

# 2026-09-06 キット版上げの据え付け(kit-migrate)

## 版上げで失効させた残務

- 消した行(docs/residual.md より逐語):
  > 2026-09-01 .claude/skills/kit-migrate/SKILL.md:§1 が「版の名前を控える: `.claude/kit-manifest.json` の `generated`(と `kit`)」と指示し §7 の報告様式も `<前の generated> → <後の generated>` を要求するが、`kit-manifest.json` は自身の `_comment` で「版番号も生成日時も持たない(配布物の再現性を壊すため)」と宣言しており `generated` の欄が存在しない。版を名指す材料が `kit-patch.py` の控えの `kit` 指紋しか無く、報告の1行目が毎回書けない。基準コミット 69579da でも同じ(元からあった問題)。キット全体に掛かる欠陥なので直すのは `/kit-improve`(据え付けフロー)
  - 解消の在り処: 現在の `.claude/skills/kit-migrate/SKILL.md` §1・§7 は `generated` 欄を一切参照しない。版は「`kit-dist.json` の `kit` 名 + 展開前後のコミット」で名指す形に既に直っている(`grep -n generated .claude/skills/kit-migrate/SKILL.md` は0件)。報告様式も `<展開前の HEAD> → <展開を入れたコミット|未コミット>` の形に変わっている。

書き先: `docs/residual.md`
