package main

import "testing"

func TestFindReviewResultJSON_StrictAndTolerant(t *testing.T) {
	cases := []struct {
		name       string
		in         string
		wantOK     bool
		wantSevere bool
	}{
		{
			name:   "clean single line pass",
			in:     `{"findings":[]}`,
			wantOK: true,
		},
		{
			name:       "clean single line with severe",
			in:         `{"findings":[{"severity":"major","file":"a.go","message":"x","aspect":"security"}]}`,
			wantOK:     true,
			wantSevere: true,
		},
		{
			name:   "prose then json on last line",
			in:     "I reviewed the diff.\nLooks good.\n{\"findings\":[]}",
			wantOK: true,
		},
		{
			name:   "json wrapped in markdown fence",
			in:     "Here is my verdict:\n```json\n{\"findings\":[]}\n```",
			wantOK: true,
		},
		{
			name:   "prose prefix on same line as json",
			in:     `Result: {"findings":[]}`,
			wantOK: true,
		},
		{
			name:   "findings object with brace inside string value",
			in:     `prose {"findings":[{"severity":"minor","file":"a","message":"use {x} not y","aspect":"requirements"}]} trailing`,
			wantOK: true,
		},
		{
			name:   "pure prose (no json) fails",
			in:     "Review complete — no critical or major findings. Everything looks correct.",
			wantOK: false,
		},
		{
			name:   "unrelated json object without findings key is rejected",
			in:     `{"result":"ok","status":"done"}`,
			wantOK: false,
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			rr := findReviewResultJSON(c.in)
			if (rr != nil) != c.wantOK {
				t.Fatalf("findReviewResultJSON(%q): got ok=%v want %v", c.in, rr != nil, c.wantOK)
			}
			if rr != nil && rr.HasSevere() != c.wantSevere {
				t.Fatalf("HasSevere=%v want %v", rr.HasSevere(), c.wantSevere)
			}
		})
	}
}
