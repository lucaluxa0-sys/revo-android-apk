package actions

import (
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/config"
)

type VariableName string

const (
	Initialized     VariableName = "initialized"
	PerformReset    VariableName = "perform-reset"
	RetryCount      VariableName = "retry-count"
	NewJoin         VariableName = "new-join"
	GameInstance    VariableName = "game-instance"
	HopServer       VariableName = "hop-server"
	UsePublicServer VariableName = "use-public-server"
	RestartSleep    VariableName = "restart-sleep"
	FullServerSleep VariableName = "full-server-sleep"
	Offset          VariableName = "offset"
	OffsetX         VariableName = "offset-x"
	OffsetY         VariableName = "offset-y"
	VicField        VariableName = "vic-field"
	NightDetected   VariableName = "night-detected"
)

// Get a variable as a concrete type
func V[T any](name VariableName) func(macro *common.Macro) T {
	return func(macro *common.Macro) T {
		return macro.Scratch.Get(string(name)).(T)
	}
}

// Get a variable as an interface
func VI(name VariableName) func(macro *common.Macro) interface{} {
	return func(macro *common.Macro) interface{} {
		return macro.Scratch.Get(string(name))
	}
}

// Get a setting path as a concrete type
func P[T any](path string) func(macro *common.Macro) T {
	return func(macro *common.Macro) T {
		return *config.Concrete[T](macro.Settings, path)
	}
}

// Get a macro state path as a concrete type
func MS[T any](path string) func(macro *common.Macro) T {
	return func(macro *common.Macro) T {
		return *config.Concrete[T](macro.MacroState, path)
	}
}

// Get a state path as a concrete type
func S[T any](path string) func(macro *common.Macro) T {
	return func(macro *common.Macro) T {
		return *config.Concrete[T](macro.State, path)
	}
}

func Index(depth ...int) func(macro *common.Macro) int {
	if len(depth) > 1 {
		panic("too many arguments")
	}
	var depthV = 0
	if len(depth) == 1 {
		depthV = depth[0]
	}
	return func(macro *common.Macro) int {
		return macro.Scratch.LoopState.Index[depthV]
	}
}

func PatternExecuting(macro *common.Macro) bool {
	return macro.GetRoot().CancelPattern != nil
}

func Window(macro *common.Macro) interface{} {
	return macro.Root.Window
}

func Capturing(macro *common.Macro) bool {
	return macro.Root.Window.Capturing()
}

func LastError(macro *common.Macro) interface{} {
	return macro.Scratch.LastError
}
