package control

import (
	"fmt"
	"github.com/nosyliam/revolution/pkg/common"
)

const MainRoutineKind common.RoutineKind = "main"

type Routine struct {
	macro   *common.Macro
	kind    common.RoutineKind
	actions []common.Action

	depth       int
	redirectLoc *common.RedirectExecution
	parent      *Routine

	err chan<- string
}

func (r *Routine) Copy(routine *Routine) {
	r.err = routine.err
}

func (r *Routine) Execute() {
	for {
		for i := 0; i < len(r.actions); i++ {
			if err := r.actions[i].Execute(r.macro); err != nil {
				if redirect, ok := err.(*common.RedirectExecution); ok {
					if r.parent != nil {
						r.macro.Scratch.Redirect = true
						r.parent.redirectLoc = redirect
						return
					} else {
						r.macro.Scratch.Redirect = true
						r.redirectLoc = redirect
						err = nil
					}
				}
				switch err {
				case common.RetrySignal:
					i -= 1
				case common.StepBackSignal:
					i -= 2
				case common.RestartSignal:
					i = -1
				case common.TerminateSignal:
					return
				case nil:
				default:
					r.err <- err.Error()
					<-<-r.macro.Pause
				}
			}
			if len(r.macro.Redirect) > 0 && (r.parent == nil || r.parent.redirectLoc == nil) {
				kind := <-r.macro.Redirect
				if kind.Routine != r.kind {
					if r.parent == nil {
						r.macro.Scratch.Redirect = true
						r.redirectLoc = kind
					} else {
						r.macro.Scratch.Redirect = true
						r.parent.redirectLoc = kind
						return
					}
				}
			}
			if len(r.macro.Stop) > 0 {
				<-r.macro.Stop
				if r.depth != 0 {
					r.macro.Stop <- struct{}{}
				}
				return
			}
			if r.redirectLoc != nil {
				fmt.Println(r.redirectLoc, r.depth)
				if r.depth != 0 && r.parent != nil {
					r.parent.redirectLoc = r.redirectLoc
					return
				}
				r.macro.Routine(r.redirectLoc.Routine)
				r.redirectLoc = nil
				break
			}
			if r.macro.Scratch.LoopState.Unwind != nil {
				if r.depth == 0 {
					panic("invalid loop state: not in a loop")
				}
				break
			}
			if len(r.macro.Pause) > 0 {
				<-<-r.macro.Pause
			}
		}
		r.macro.Results = &common.ActionResults{}
		if r.depth != 0 {
			break
		}
	}
}

func ExecuteRoutine(
	macro *common.Macro,
	actions common.Actions,
	status chan<- string,
	err chan<- string,
) {
	routine := &Routine{
		macro:   macro.Copy(),
		actions: actions,
		err:     err,
		kind:    MainRoutineKind,
	}
	macro.Scratch.Stack = []string{"Main"}
	var execSub func(routine *Routine, macro *common.Macro) common.SubroutineExecutor
	var exec func(routine *Routine, macro *common.Macro) common.RoutineExecutor
	execSub = func(routine *Routine, macro *common.Macro) common.SubroutineExecutor {
		return func(actions []common.Action) {
			subMacro := macro.Copy()
			subMacro.Logger = macro.Logger
			subMacro.Status = macro.Status
			subMacro.Routine = exec(routine, subMacro)
			subMacro.Subroutine = execSub(routine, subMacro)
			subMacro.Action = func(action common.Action) error {
				return action.Execute(subMacro)
			}
			subRoutine := &Routine{macro: subMacro, actions: actions, depth: routine.depth + 1, parent: routine.parent}
			subRoutine.Copy(routine)
			subRoutine.Execute()
		}
	}
	exec = func(routine *Routine, macro *common.Macro) common.RoutineExecutor {
		return func(kind common.RoutineKind) {
			subActions, ok := common.Routines[kind]
			if !ok {
				panic(fmt.Sprintf("unknown subroutine %s", string(kind)))
			}
			macro.Scratch.Stack = append([]string{string(kind)}, macro.Scratch.Stack...)
			macro.Scratch.Redirect = false
			subMacro := macro.Copy()
			subMacro.Logger = subMacro.Logger.Child(string(kind))
			subMacro.Results = &common.ActionResults{}
			subMacro.Status = macro.Status
			subMacro.Routine = exec(routine, subMacro)
			subMacro.Action = func(action common.Action) error {
				return action.Execute(subMacro)
			}
			subRoutine := &Routine{macro: subMacro, actions: subActions, depth: routine.depth + 1, parent: routine, kind: kind}
			subRoutine.Copy(routine)
			subRoutine.Execute()
			macro.Scratch.Stack = macro.Scratch.Stack[1:]
		}
	}
	routine.macro.Routine = exec(routine, routine.macro)
	routine.macro.Subroutine = execSub(routine, routine.macro)
	routine.macro.Action = func(action common.Action) error {
		return action.Execute(routine.macro)
	}
	routine.macro.Status = func(stat string) {
		status <- stat
	}
	macro.Scheduler.Initialize(routine.macro)
	routine.Execute()
}
