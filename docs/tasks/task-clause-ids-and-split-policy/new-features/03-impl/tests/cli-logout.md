---
target: docs/03-impl/tests/cli-logout.md
change: replace
sections:
  - "## 受入基準 ⇄ テスト対応表"
deletes: []
reason: '旧2列形式(要件 ID + 受入基準 #)の対応表を条項 ID(FR-<domain>-nn-#)キーの5列形式へ移行する(docs/issues/060。決定シート論点1=A「30ファイルを今回まとめて移行」)。列の併合のみの機械的な置換で、行の増減・種別/レベル/テスト識別子/状態の値の変更は無い。非機能要件の行は条項に分けないため要件 ID のまま(受入基準 # の「—」を落とす)。'
reflected: 2026-08-07
---

## 受入基準 ⇄ テスト対応表


<!-- 受入基準 14〜18 は `logout` と `reset` の双方に効く共通の振る舞いである。
     重複を作らないため、対応表は主担当である本ファイルだけが持つ
     (`tests/cli-reset.md` の受入基準表は「対象外」を維持する)。
     実機確認の手順は `logout` と `reset` の両方について実施する。
     受入基準22 は `reset` 側の振る舞い(プロジェクト配下を触らない)だが、`logout` の
     受入基準20 と対になる非対称なので、重複を作らないためこの表で持つ。 -->

| 受入基準 ID | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|
| FR-env-01-9 | 境界値 | — | -(実機確認手順。**`logout` 側**。`docs/03-impl/tests/e2e.md` の E2E-01 手順8-5) | 未検証(テスト未実装) |
| FR-env-01-9 | 境界値 | — | -(実機確認手順。**`reset` 側**(docker-proxy と `claude-dev-net` の両方)。`docs/03-impl/tests/e2e.md` の E2E-01 手順8-12) | 未検証(テスト未実装) |
| FR-env-03-5 | 正常系 | — | - | 未検証(テスト未実装) |
| FR-env-03-14 | 正常系 | — | -(実機確認手順。`logout` / `reset` の両方。`docs/03-impl/tests/e2e.md` の E2E-01 手順8) | 未検証(テスト未実装) |
| FR-env-03-15 | 境界値 | — | -(実機確認手順。`logout` / `reset` の両方。`docs/03-impl/tests/e2e.md` の E2E-01 手順8) | 未検証(テスト未実装) |
| FR-env-03-16 | 正常系 | — | -(実機確認手順。`logout` / `reset` の両方。`docs/03-impl/tests/e2e.md` の E2E-01 手順8) | 未検証(テスト未実装) |
| FR-env-03-17 | 正常系 | — | -(実機確認手順。`logout` / `reset` の両方。`docs/03-impl/tests/e2e.md` の E2E-01 手順8) | 未検証(テスト未実装) |
| FR-env-03-18 | 異常系 | — | -(実機確認手順。`logout` / `reset` の両方。`docs/03-impl/tests/e2e.md` の E2E-01 手順8) | 未検証(テスト未実装) |
| FR-env-03-19 | 境界値 | — | -(実機確認手順。`docs/03-impl/tests/e2e.md` の E2E-01 手順8) | 未検証(テスト未実装) |
| FR-env-03-20 | 正常系 | — | -(実機確認手順。`docs/03-impl/tests/e2e.md` の E2E-01 手順8) | 未検証(テスト未実装) |
| FR-env-03-21 | 境界値 | — | -(実機確認手順。`docs/03-impl/tests/e2e.md` の E2E-01 手順8) | 未検証(テスト未実装) |
| FR-env-03-22 | 正常系 | — | -(実機確認手順。`docs/03-impl/tests/e2e.md` の E2E-01 手順8。`reset` について確認する) | 未検証(テスト未実装) |
| FR-env-03-23 | 異常系 | — | -(実機確認手順。`logout` / `reset` の両方。`docs/03-impl/tests/e2e.md` の E2E-01 手順8-13) | 未検証(テスト未実装) |
