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
- 2026-09-01 .gitignore:4 `.claude` を丸ごと無視しているため `.claude/state/stamps.json` を git で共有できない(`git check-ignore` が `.gitignore:4` を返し、`.claude` 配下の追跡ファイルは0件)。CLAUDE.md §4 と `flows.md` §2 は鮮度スタンプを git で追跡すると定めており、追跡されないと clone 先・CI・別 checkout ではデプロイゲートが「スタンプ皆無」と判定する。基準コミット 69579da でも同じ(元からあった問題)。直すには `!.claude/state/stamps.json` の例外を足すなど .gitignore 側の裁定が要る(F2 文書整合フロー)
- 2026-09-01 docs/00-requests/acceptances.md:`/verify-tests e2e` が要求する「AC-nn 全件を実システムに対して判定」(`.claude/skills/verify-tests/SKILL.md` §1)が、この project の履歴上 一度も実行された記録が無い(`docs/histories/` `docs/issues/` `docs/pendings.md` を検索して確認。`docs/kit-report.md:112` も同じ欠落を既に指摘している)。AC-02(クライアント PC 経由の SSH トンネル)と AC-06(実 OpenAI アカウントでのブラウザ認証)はこの実行環境だけでは判定できず、AC-01/03/08 のフル実機手順(`docs/03-impl/tests/e2e.md` E2E-01 手順8)も「他に作業中のセッションが無い専有ホスト」を前提とし艦隊運用の現状と両立しない(P-006 と同型)。基準コミット 69579da より前から在る取りこぼしである。今回の run(`.devcontainer/Dockerfile.claude` / `.github/workflows/ghcr-images.yml` の増分)はこの2ファイルが AC-01〜08 のどのコード経路にも触れていないと確認したうえで対象外として扱った(F4 試験フロー)
- 2026-09-01 .claude/skills/kit-migrate/SKILL.md:§1 が「版の名前を控える: `.claude/kit-manifest.json` の `generated`(と `kit`)」と指示し §7 の報告様式も `<前の generated> → <後の generated>` を要求するが、`kit-manifest.json` は自身の `_comment` で「版番号も生成日時も持たない(配布物の再現性を壊すため)」と宣言しており `generated` の欄が存在しない。版を名指す材料が `kit-patch.py` の控えの `kit` 指紋しか無く、報告の1行目が毎回書けない。基準コミット 69579da でも同じ(元からあった問題)。キット全体に掛かる欠陥なので直すのは `/kit-improve`(据え付けフロー)
