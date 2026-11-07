package planner

import (
	"os"
	"strings"
	"testing"
	"time"
)

func TestRecoveredELolIsEighteenMoves(t *testing.T) {
	source, err := os.ReadFile("../scripts/e_lol.lua")
	if err != nil {
		t.Fatal(err)
	}
	p, err := Compile(string(source), Options{Width: 2, Length: 8})
	if err != nil {
		t.Fatal(err)
	}
	if p.Pattern != "e_lol" || !p.DryRunOnly || len(p.Actions) != 18 {
		t.Fatalf("unexpected e_lol plan name=%q dryRun=%v steps=%d", p.Pattern, p.DryRunOnly, len(p.Actions))
	}
	checks := []struct {
		index int
		dir   string
		studs float64
	}{
		{0, "LEFT", 10}, {1, "BACKWARD", 20}, {2, "RIGHT", 5},
		{3, "FORWARD", 20}, {4, "RIGHT", 5}, {9, "BACKWARD", 20},
		{17, "RIGHT", 10},
	}
	for _, c := range checks {
		a := p.Actions[c.index]
		if a.Type != "walk" || a.Direction != c.dir || a.Studs != c.studs {
			t.Errorf("step[%d]=%+v want dir=%s studs=%v", c.index, a, c.dir, c.studs)
		}
	}
	if p.Actions[0].DurationMs != 625 {
		t.Fatal("wrong movement calibration")
	}
}
func TestWidthChangesLoopCount(t *testing.T) {
	source, err := os.ReadFile("../scripts/e_lol.lua")
	if err != nil {
		t.Fatal(err)
	}
	p, err := Compile(string(source), Options{Width: 3, Length: 8})
	if err != nil {
		t.Fatal(err)
	}
	if got := len(p.Actions); got != 26 {
		t.Fatalf("width=3 steps=%d want 26", got)
	}
}
func TestRectangle(t *testing.T) {
	source := "SetName('rectangle'); Pattern={Iteration=1, Length=4, Width=4}; Walk(Forward,Pattern.Length); Walk(Right,Pattern.Width); Walk(Backward,Pattern.Length); Walk(Left,Pattern.Width)"
	p, err := Compile(source, Options{})
	if err != nil {
		t.Fatal(err)
	}
	if len(p.Actions) != 4 || p.Actions[0].Studs != 4 || p.Actions[3].Direction != "LEFT" {
		t.Fatalf("not a rectangle: %+v", p.Actions)
	}
}
func TestRejectUnsupportedFunctions(t *testing.T) {
	for _, s := range []string{
		"SetName('a'); WalkAlign(Left,3)",
		"SetName('a'); WalkDetector('red_cannon',Right,30)",
		"SetName('a'); Walk({[0]=Forward,[100]=Left})",
	} {
		if _, err := Compile(s, Options{}); err == nil {
			t.Fatalf("accepted unsupported action: %s", s)
		}
	}
}
func TestBoundedActionsAndDistances(t *testing.T) {
	for _, s := range []string{
		"SetName('bad'); Walk(Left,-4)",
		"SetName('bad'); Walk(Left,1/0)",
		"SetName('bad'); for i=1,600 do Walk(Right,1) end",
		"SetName('bad'); KeyUp(Key.Right)",
		"SetName('bad'); KeyDown(Key.Right)",
	} {
		if _, err := Compile(s, Options{MaxActions: 512}); err == nil {
			t.Fatalf("invalid accepted: %s", s)
		}
	}
}
func TestBalancedKeysAndSleep(t *testing.T) {
	src := "SetName('key-probe'); KeyDown(Key.Right); SleepStuds(8); KeyUp(Key.Right); Sleep(120)"
	p, err := Compile(src, Options{MsPerStud: 62.5})
	if err != nil {
		t.Fatal(err)
	}
	if len(p.Actions) != 4 || p.Actions[1].DurationMs != 500 || p.Actions[3].DurationMs != 120 {
		t.Fatalf("unexpected input plan: %+v", p.Actions)
	}
}
func TestInfiniteLoopMustTimeOut(t *testing.T) {
	_, err := Compile("SetName('endless'); while true do end", Options{Timeout: 50 * time.Millisecond})
	if err == nil || !strings.Contains(strings.ToLower(err.Error()), "context") {
		t.Fatalf("loop not bounded: %v", err)
	}
}
