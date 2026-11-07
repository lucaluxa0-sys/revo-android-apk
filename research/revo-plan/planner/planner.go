package planner

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"math"
	"strings"
	"time"

	lua "github.com/yuin/gopher-lua"
)

// Action represents an observed macro command, not a simulated game result.
// These are command plans only; no game input is sent by the planner.
type Action struct {
	Type       string  `json:"type"`
	Direction  string  `json:"direction,omitempty"`
	Studs      float64 `json:"studs,omitempty"`
	DurationMs int64   `json:"durationMs,omitempty"`
	Key        string  `json:"key,omitempty"`
	Yaw        float64 `json:"yaw,omitempty"`
}

type Plan struct {
	Schema            string   `json:"schema"`
	Pattern           string   `json:"pattern"`
	SourceSHA256      string   `json:"sourceSha256"`
	MovementMsPerStud float64  `json:"movementMsPerStud"`
	DryRunOnly        bool     `json:"dryRunOnly"`
	Actions           []Action `json:"actions"`
}

type Options struct {
	Width, Length, Iteration float64
	MsPerStud                float64
	MaxActions               int
	Timeout                  time.Duration
}

func defaults(o Options) Options {
	if o.Width <= 0 {
		o.Width = 2
	}
	if o.Length <= 0 {
		o.Length = 8
	}
	if o.Iteration <= 0 {
		o.Iteration = 1
	}
	if o.MsPerStud <= 0 {
		o.MsPerStud = 62.5
	}
	if o.MaxActions <= 0 {
		o.MaxActions = 512
	}
	if o.MaxActions > 4096 {
		o.MaxActions = 4096
	}
	if o.Timeout <= 0 {
		o.Timeout = 3 * time.Second
	}
	return o
}

func Compile(source string, opts Options) (Plan, error) {
	opts = defaults(opts)
	if !finitePositive(opts.Width) || !finitePositive(opts.Length) || !finitePositive(opts.Iteration) ||
		!finitePositive(opts.MsPerStud) || opts.Width > 100 || opts.Length > 1000 || opts.MsPerStud > 1000 {
		return Plan{}, fmt.Errorf("invalid pattern dimensions or movement calibration")
	}
	sha := sha256.Sum256([]byte(source))
	plan := Plan{Schema: "revo.action-plan.v1", SourceSHA256: hex.EncodeToString(sha[:]), MovementMsPerStud: opts.MsPerStud, DryRunOnly: true, Actions: []Action{}}
	l := lua.NewState(lua.Options{SkipOpenLibs: true})
	defer l.Close()
	// Deliberately do not open OS, IO, package, debug or external loaders.
	lua.OpenBase(l)
	lua.OpenMath(l)
	lua.OpenTable(l)
	lua.OpenString(l)
	l.SetGlobal("dofile", lua.LNil)
	l.SetGlobal("loadfile", lua.LNil)
	l.SetGlobal("load", lua.LNil)
	ctx, cancel := context.WithTimeout(context.Background(), opts.Timeout)
	defer cancel()
	l.SetContext(ctx)

	dirs := []string{"Forward", "Backward", "Left", "Right"}
	directionTable := l.NewTable()
	keyTable := l.NewTable()
	for _, d := range dirs {
		value := lua.LString(strings.ToUpper(d))
		l.SetGlobal(d, value)
		l.SetField(directionTable, d, value)
		l.SetField(keyTable, d, value)
	}
	l.SetGlobal("Direction", directionTable)
	l.SetField(keyTable, "Space", lua.LString("SPACE"))
	l.SetField(keyTable, "E", lua.LString("E"))
	l.SetGlobal("Key", keyTable)
	fields := l.NewTable()
	l.SetField(fields, "Width", lua.LNumber(opts.Width))
	l.SetField(fields, "Length", lua.LNumber(opts.Length))
	l.SetField(fields, "Iteration", lua.LNumber(opts.Iteration))
	l.SetGlobal("Pattern", fields)

	held := make(map[string]bool)
	record := func(action Action, l *lua.LState) {
		if len(plan.Actions) >= opts.MaxActions {
			l.RaiseError("action limit exceeded (%d)", opts.MaxActions)
			return
		}
		plan.Actions = append(plan.Actions, action)
	}
	validKey := func(v lua.LValue) string {
		s := strings.ToUpper(v.String())
		switch s {
		case "FORWARD", "BACKWARD", "LEFT", "RIGHT", "SPACE", "E":
			return s
		}
		return ""
	}
	register := func(name string, fn lua.LGFunction) {
		l.SetGlobal(name, l.NewFunction(fn))
	}
	register("SetName", func(L *lua.LState) int {
		name := strings.TrimSpace(L.CheckString(1))
		if len(name) == 0 || len(name) > 100 {
			L.RaiseError("invalid pattern name")
			return 0
		}
		plan.Pattern = name
		return 0
	})
	register("Walk", func(L *lua.LState) int {
		direction := validKey(L.Get(1))
		if direction == "" || direction == "SPACE" || direction == "E" {
			L.RaiseError("unsupported Walk direction / timed table route")
			return 0
		}
		studs := float64(L.CheckNumber(2))
		if !finitePositive(studs) || studs > 1000 {
			L.RaiseError("invalid Walk distance")
			return 0
		}
		milliseconds := int64(math.Round(studs * opts.MsPerStud))
		if milliseconds < 50 {
			milliseconds = 50
		}
		if milliseconds > 10000 {
			L.RaiseError("Walk exceeds 10-second Android gesture limit")
			return 0
		}
		record(Action{Type: "walk", Direction: direction, Studs: studs, DurationMs: milliseconds}, L)
		return 0
	})
	register("Sleep", func(L *lua.LState) int {
		milliseconds := float64(L.CheckNumber(1))
		if math.IsNaN(milliseconds) || math.IsInf(milliseconds, 0) || milliseconds < 0 || milliseconds > 600000 {
			L.RaiseError("invalid Sleep duration")
			return 0
		}
		record(Action{Type: "sleep", DurationMs: int64(math.Round(milliseconds))}, L)
		return 0
	})
	register("SleepStuds", func(L *lua.LState) int {
		studs := float64(L.CheckNumber(1))
		if !finitePositive(studs) || studs > 1000 {
			L.RaiseError("invalid SleepStuds")
			return 0
		}
		record(Action{Type: "sleep", Studs: studs, DurationMs: int64(math.Round(studs * opts.MsPerStud))}, L)
		return 0
	})
	register("SetYaw", func(L *lua.LState) int {
		yaw := float64(L.CheckNumber(1))
		if math.IsNaN(yaw) || math.IsInf(yaw, 0) || yaw < 0 || yaw > 12 {
			L.RaiseError("unsupported yaw")
			return 0
		}
		record(Action{Type: "yaw", Yaw: yaw}, L)
		return 0
	})
	register("KeyDown", func(L *lua.LState) int {
		key := validKey(L.Get(1))
		if key == "" {
			L.RaiseError("unsupported key")
			return 0
		}
		if held[key] {
			L.RaiseError("duplicate KeyDown: %s", key)
			return 0
		}
		held[key] = true
		record(Action{Type: "keyDown", Key: key}, L)
		return 0
	})
	register("KeyUp", func(L *lua.LState) int {
		key := validKey(L.Get(1))
		if key == "" || !held[key] {
			L.RaiseError("KeyUp without KeyDown")
			return 0
		}
		delete(held, key)
		record(Action{Type: "keyUp", Key: key}, L)
		return 0
	})
	// Fail closed. In particular, detectors, alignment, parachute and combat have
	// not been recreated; treating them as no-ops would be deceptive and unsafe.
	for _, name := range []string{
		"WalkAlign", "WalkAsync", "WalkDetector", "Checkpoint", "Parachute",
		"ExecuteWithAlignment", "CheckDetector", "SetZoom", "Panic", "Exit",
		"Rejoin", "Collect", "RunRoutine", "Jump", "Teleport",
	} {
		op := name
		register(op, func(L *lua.LState) int { L.RaiseError("unsupported Revolution operation: %s", op); return 0 })
	}
	if err := l.DoString(source); err != nil {
		return Plan{}, fmt.Errorf("Revo Lua compile rejected: %w", err)
	}
	if len(held) > 0 {
		return Plan{}, fmt.Errorf("script finishes with %d held key(s)", len(held))
	}
	if plan.Pattern == "" {
		return Plan{}, fmt.Errorf("source did not call SetName")
	}
	if len(plan.Actions) == 0 {
		return Plan{}, fmt.Errorf("source emitted no actions")
	}
	return plan, nil
}

func finitePositive(v float64) bool { return !math.IsNaN(v) && !math.IsInf(v, 0) && v > 0 }
