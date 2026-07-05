package main

import "strings"

// models.go — the SINGLE place that decides which model + reasoning effort each
// unit of orchestrator work uses. Change the two profiles / the kind mapping
// below and the whole system follows; nothing else needs editing (docs/06
// §モデル選択, docs/impl/60 §モデル選択). This is intentionally plain code (not a
// config file) so the policy lives with the design/impl docs and is trivial to
// tweak.

// ModelProfile is a (model, effort) pair passed to `claude` via --model/--effort.
//   - Model: an alias for the latest of a family ("opus", "sonnet", "haiku") or a
//     full id ("claude-sonnet-5"). Aliases track the newest model automatically.
//   - Effort: reasoning effort — one of low | medium | high | xhigh | max.
type ModelProfile struct {
	Model  string
	Effort string
}

// ==========================================================================
// ▼▼▼ ポリシーはここだけ編集する ▼▼▼
//
// 方針（2026-07 時点）:
//   - 思考が重い工程（ブレスト・設計・実装仕様の作成・レビュー・介入）= opus / high
//   - それ以外（実装・テスト・雑タスク等）                          = sonnet / high
// ==========================================================================
var (
	// profileDeep — 熟考が要る工程用。
	profileDeep = ModelProfile{Model: "opus", Effort: "high"}
	// profileDefault — 上記以外の既定。
	profileDefault = ModelProfile{Model: "sonnet", Effort: "high"}
)

// deepTaskKinds は「熟考工程」に分類する plan タスクの kind。ブレスト脳が各タスクへ
// 付与する（brainstorming.md）。ここに無い kind／空は profileDefault になる。
var deepTaskKinds = map[string]bool{
	"design":       true, // 設計
	"spec":         true, // 実装仕様
	"impl_spec":    true,
	"impl-spec":    true,
	"requirements": true, // 要件
	"usecase":      true, // ユースケース
	"adr":          true,
	"doc":          true, // 設計系ドキュメント
	"docs":         true,
	"review":       true,
}

// ==========================================================================
// ▲▲▲ ここまで編集ポイント ▲▲▲
// ==========================================================================

// taskKindProfile maps a plan task's Kind to its profile. Unknown/empty → default.
func taskKindProfile(kind string) ModelProfile {
	if deepTaskKinds[strings.ToLower(strings.TrimSpace(kind))] {
		return profileDeep
	}
	return profileDefault
}

// workerTaskProfile returns the profile for a worker implementing a plan task.
func workerTaskProfile(t *Task) ModelProfile {
	if t == nil {
		return profileDefault
	}
	return taskKindProfile(t.Kind)
}

// Role/phase profiles (these are not plan tasks):
func brainstormingProfile() ModelProfile { return profileDeep }    // ブレスト
func interveneProfile() ModelProfile     { return profileDeep }    // 介入対応（判断）
func reviewerProfile() ModelProfile      { return profileDeep }    // レビュー
func completionProfile() ModelProfile    { return profileDefault } // 完了検証（助言・軽量）
