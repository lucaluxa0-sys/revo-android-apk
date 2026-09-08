package alignment

import (
	"fmt"
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/config"
	lua "github.com/yuin/gopher-lua"
)

func LuaCheckpoint(L *lua.LState) int {
	macro := L.Context().Value("macro").(*common.Macro)
	data := L.CheckTable(1)
	detector := data.RawGetString("Detector")
	walk := data.RawGetString("Walk")
	nudge := data.RawGetString("Nudge")
	if detector == lua.LNil {
		panic("Detector and walk function required in call to Checkpoint")
	}
	if detector.Type() != lua.LTString {
		panic("Detector must be a string")
	}
	if walk.Type() != lua.LTFunction {
		panic("Walk must be a function")
	}
	if walk.Type() != lua.LTNil && walk.Type() != lua.LTFunction {
		panic("Nudge must be nil or a function")
	}
	detectorName := detector.(lua.LString)
	var maxAttempts = 3
	if maxAttemptsValue := data.RawGetString("MaxAttempts"); maxAttemptsValue.Type() != lua.LTNil {
		if maxAttemptsValue.Type() != lua.LTNumber {
			panic("MaxAttempts must be a number")
		}
		maxAttempts = int(maxAttemptsValue.(lua.LNumber))
	}
	var initialWalk = false
	for i := 0; i < maxAttempts; i++ {
		if nudge.Type() == lua.LTNil || !initialWalk {
			err := L.CallByParam(lua.P{
				Fn:      walk.(*lua.LFunction),
				NRet:    0,
				Protect: true,
			})
			if err != nil {
				L.RaiseError("error calling Walk function: %v", err)
				return 0
			}
			initialWalk = true
		}
		detected, err := Manager.PerformDetection(macro, string(detectorName))
		if err != nil {
			panic(fmt.Errorf("failed to perform detection: %w", err))
		}
		if detected {
			return 0
		}
		if nudge.Type() != lua.LTNil {
			err := L.CallByParam(lua.P{
				Fn:      nudge.(*lua.LFunction),
				NRet:    0,
				Protect: true,
			})
			if err != nil {
				L.RaiseError("error calling Nudge function: %v", err)
				return 0
			}
		}
	}
	panic("retryable error: alignment failed!")
}

func LuaExecuteWithAlignment(L *lua.LState) int {
	macro := L.Context().Value("macro").(*common.Macro)
	data := L.CheckTable(1)
	high := data.RawGetString("High")
	medium := data.RawGetString("Medium")
	low := data.RawGetString("Low")
	level := *config.Concrete[string](macro.Settings, "patterns.alignmentLevel")
	switch {
	case high.Type() == lua.LTFunction:
		if level == "High" {
			err := L.CallByParam(lua.P{
				Fn:      high.(*lua.LFunction),
				NRet:    0,
				Protect: true,
			})
			if err != nil {
				L.RaiseError("error calling high alignment function: %v", err)
				return 0
			}
		}
		fallthrough
	case medium.Type() == lua.LTFunction:
		if level == "High" || level == "Medium" {
			err := L.CallByParam(lua.P{
				Fn:      medium.(*lua.LFunction),
				NRet:    0,
				Protect: true,
			})
			if err != nil {
				L.RaiseError("error calling medium alignment function: %v", err)
				return 0
			}
		}
		fallthrough
	case low.Type() == lua.LTFunction:
		err := L.CallByParam(lua.P{
			Fn:      low.(*lua.LFunction),
			NRet:    0,
			Protect: true,
		})
		if err != nil {
			L.RaiseError("error calling low alignment function: %v", err)
			return 0
		}
	default:
		panic("alignment function expected!")
	}
	return 0
}
