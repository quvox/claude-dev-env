---
id: <category-or-type>
version: 1.0.0
updated: <YYYY-MM-DD>
source:
  - docs/00-requests/request.md
summary: <1行。このファイルが扱う決定の範囲>
keywords: []
# 層跨ぎ同名時は id が層を名乗る(00-auth / 01-auth)— 正は CLAUDE.md §7
# verified: verify 系フロー(/verify-docs、03層代表は /verify-impl)だけが書く
---

<!-- 決定台帳。規則の正は .claude/directions/00-requests.md の decisions 節
     (01 側も同じ規則: .claude/directions/01-requirements.md)。
     00-requests/decisions/ なら ID は D0-<category>-nn、
     01-requirements/decisions/ なら D1-<type>-nn。
     すべてのエントリは 決定 / 委任 / 要確認 のいずれかに仕分ける。この仕分けが無人の検証フローの鍵。
     ・委任には「委任範囲」と「制約(ガードレール)」が必須(欠けていれば重大度「高」の所見)
     ・要確認には「論点」と「誰が・いつまでに」が必須。要確認は検証をブロックしない
     ファイルが大きくなりすぎないよう分割する(コンテキストを食う)。
     ・**人間が実使用で示した既定を貯めるときは、内容を「DS-nn の導出既定。…」で書き出し、
       関連: に DS-ID を書く**(.claude/directions/delegation.md §5.1)。次のタスクの導出が
       `grep -rn "DS-0" docs/00-requests/decisions/` でここを最初に読む。
       1つの DS-ID について5件を超えたら、それは 01 の受け入れ基準か 02 の方針へ昇格させる兆候である -->

# <カテゴリ名> の決定事項

## D0-<category>-01 <一行タイトル>

- 区分: 決定
- 決めた日: <YYYY-MM-DD>
- 内容: <何をどう決めたか。数値・条件で書く>
- 理由: <>
- 見直す条件: <この決定の前提が崩れる観測可能な条件。恒久なら「なし(恒久である理由)」>
- 却下した案: <案と却下理由>
- 関連: RQ-<category>-01 / FR-<domain>-01

## D0-<category>-02 <一行タイトル>

- 区分: 委任
- 決めた日: <YYYY-MM-DD>
- 委任範囲: <AI が自律的に決めてよい範囲。境界を具体的に>
- 制約(ガードレール): <守るべき条件。これを外れる判断は委任ではない>
- 報告義務: 決めた内容を書いた仕様ドキュメントに `D0-<category>-02` と共に記録する
- 関連: <>

## D0-<category>-03 <一行タイトル>

- 区分: 要確認
- 論点: <何が決まっていないのか>
- 選択肢: <A / B / ...>
- 誰が・いつまでに: <> / <YYYY-MM-DD>
- これが決まらないと何が止まるか: <>
- 関連: <>

<!-- 要確認が回答されたら「決定」に移し、理由を書く(MINOR 変更)。
     繰り返し出てくる質問は、次の決定シートで「委任」にすることを提案する。 -->
