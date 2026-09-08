package actions

import (
	"github.com/nosyliam/revolution/pkg/common"
)

type routineAction struct {
	name common.RoutineKind
}

func (a *routineAction) Execute(macro *common.Macro) error {
	macro.Routine(a.name)
	return nil
}

func Routine(kind common.RoutineKind) common.Action {
	return &routineAction{name: kind}
}

type subroutineAction struct {
	actions []common.Action
}

func (a *subroutineAction) Execute(macro *common.Macro) error {
	macro.Subroutine(a.actions)
	return nil
}

func Subroutine(args ...interface{}) common.Action {
	if len(args) < 1 {
		panic("invalid arguments")
	}
	if actions, ok := args[0].(common.Actions); ok {
		return &subroutineAction{actions: actions}
	}
	var actions []common.Action
	for _, arg := range args {
		actions = append(actions, arg.(common.Action))
	}
	return &subroutineAction{actions: actions}
}

type redirectAction struct {
	routine common.RoutineKind
}

func (a *redirectAction) Execute(macro *common.Macro) error {
	return &common.RedirectExecution{Routine: a.routine}
}

func Redirect(kind common.RoutineKind) common.Action {
	return &redirectAction{routine: kind}
}
