package actions

import (
	"fmt"
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/config"
)

type logicAction struct {
	exec func(*common.Macro) error
}

func (a *logicAction) Execute(macro *common.Macro) error {
	return a.exec(macro)
}

func Logic(logic interface{}) common.Action {
	switch fn := logic.(type) {
	case func():
		return &logicAction{func(*common.Macro) error { fn(); return nil }}
	case func() error:
		return &logicAction{func(*common.Macro) error { return fn() }}
	case func(macro *common.Macro):
		return &logicAction{func(macro *common.Macro) error { fn(macro); return nil }}
	case func(macro *common.Macro) error:
		return &logicAction{fn}
	default:
		panic("unknown logic type")
	}
}

type (
	conditionType int
	loopType      int
	PredicateFunc func(macro *common.Macro) bool
)

const (
	ifConditionType conditionType = iota
	elseConditionType
)

const (
	whileLoopType loopType = iota
	untilLoopType
	forLoopType
)

type condition struct {
	Predicate PredicateFunc
	Exec      []func(macro *common.Macro) error
	Type      conditionType
}

type conditionalAction struct {
	conditions []*condition
}

type ConditionPredicate interface {
	Predicate() PredicateFunc
	Type() conditionType
}

func (a *conditionalAction) Execute(macro *common.Macro) error {
	for _, cond := range a.conditions {
		if cond.Predicate(macro) {
			for _, exec := range cond.Exec {
				if err := exec(macro); err != nil {
					return err
				}
				if len(macro.Redirect) > 0 {
					return <-macro.Redirect
				}
				if len(macro.Stop) > 0 {
					return nil
				}
				if len(macro.Pause) > 0 {
					<-<-macro.Pause
				}
				if macro.Scratch.LoopState.Unwind != nil {
					return nil
				}
			}
			return nil
		}
	}
	return nil
}

func Condition(conds ...interface{}) common.Action {
	var activeCond *condition
	var conditions []*condition
	for _, cond := range conds {
		switch fn := cond.(type) {
		case ConditionPredicate:
			if activeCond != nil {
				conditions = append(conditions, activeCond)
			}
			activeCond = &condition{}
			activeCond.Type = fn.Type()
			if activeCond.Type != elseConditionType {
				activeCond.Predicate = fn.Predicate()
			} else {
				activeCond.Predicate = func(*common.Macro) bool { return true }
			}
		case common.Action:
			activeCond.Exec = append(activeCond.Exec, func(macro *common.Macro) error { return fn.Execute(macro) })
		case func() error:
			activeCond.Exec = append(activeCond.Exec, func(macro *common.Macro) error { return fn() })
		case func(macro *common.Macro) error:
			activeCond.Exec = append(activeCond.Exec, fn)
		default:
			panic(fmt.Sprintf("unknown predicate type: %T", fn))
		}
	}
	if activeCond != nil {
		conditions = append(conditions, activeCond)
	}
	return &conditionalAction{conditions}
}

type ifPredicate struct {
	predicate PredicateFunc
}

func (p *ifPredicate) Type() conditionType      { return ifConditionType }
func (p *ifPredicate) Predicate() PredicateFunc { return p.predicate }

func If(predicate PredicateFunc) ConditionPredicate {
	return &ifPredicate{predicate}
}

type elsePredicate struct{}

func (p *elsePredicate) Type() conditionType      { return elseConditionType }
func (p *elsePredicate) Predicate() PredicateFunc { return nil }

func Else() ConditionPredicate {
	return &elsePredicate{}
}

func And(fns ...PredicateFunc) PredicateFunc {
	return func(macro *common.Macro) bool {
		for _, fn := range fns {
			if !fn(macro) {
				return false
			}
		}
		return true
	}
}

func Or(fns ...PredicateFunc) PredicateFunc {
	return func(macro *common.Macro) bool {
		for _, fn := range fns {
			if fn(macro) {
				return true
			}
		}
		return false
	}
}

type LoopPredicate interface {
	Predicate() PredicateFunc
	Step() func(*common.Macro)
	Start() func(*common.Macro)
}

type loopAction struct {
	loop LoopPredicate
	exec []common.Action
}

func (a *loopAction) Execute(macro *common.Macro) error {
	state := macro.Scratch.LoopState
	defer func() {
		state.Index = state.Index[1:]
	}()
	if state.Unwind != nil {
		panic("invalid loop state: cannot start a new loop while unwinding")
	}
	state.Index = append([]int{0}, state.Index...)
	if start := a.loop.Start(); start != nil {
		start(macro)
	}
	pred := a.loop.Predicate()
	var breakLoop = false
	for {
		if pred(macro) {
			for _, exec := range a.exec {
				if err := macro.Action(exec); err != nil {
					return err
				}
				if len(macro.Redirect) > 0 {
					return <-macro.Redirect
				}
				if len(macro.Stop) > 0 {
					return nil
				}
				if len(macro.Pause) > 0 {
					<-<-macro.Pause
				}
				if unwind := state.Unwind; unwind != nil {
					breakLoop = true
					break
				}
			}
			if step := a.loop.Step(); step != nil {
				step(macro)
			} else {
				state.Index[0]++
			}
			if unwind := state.Unwind; unwind != nil {
				if unwind.Depth == 0 {
					state.Unwind = nil
					if unwind.Continue {
						continue
					}
					break
				}
				unwind.Depth--
				break
			}
		} else {
			break
		}
		if breakLoop {
			break
		}
	}
	return nil
}

type forLoop struct {
	start, end, step interface{}
}

func (l *forLoop) Predicate() PredicateFunc {
	return func(macro *common.Macro) bool {
		end := ComputeValue[int](macro, l.end)
		if macro.Scratch.LoopState.Index[0] < end {
			return true
		}

		return false
	}
}

func (l *forLoop) Step() func(*common.Macro) {
	return func(macro *common.Macro) {
		step := ComputeValue[int](macro, l.step)
		if l.step != 0 {
			macro.Scratch.LoopState.Index[0] += step
		} else {
			macro.Scratch.LoopState.Index[0]++
		}
	}
}

func (l *forLoop) Start() func(*common.Macro) {
	return func(macro *common.Macro) {
		start := ComputeValue[int](macro, l.start)
		macro.Scratch.LoopState.Index[0] = start
	}
}

func For(args ...interface{}) LoopPredicate {
	if len(args) > 3 {
		panic("invalid arguments")
	}
	switch len(args) {
	case 3:
		return &forLoop{args[0], args[1], args[2]}
	case 2:
		return &forLoop{args[0], args[1], 1}
	case 1:
		return &forLoop{0, args[0], 1}
	default:
		panic("invalid arguments")
	}
}

type whileLoop struct {
	predicate PredicateFunc
}

func (l *whileLoop) Predicate() PredicateFunc {
	return func(macro *common.Macro) bool {
		return l.predicate(macro)
	}
}

func (l *whileLoop) Step() func(*common.Macro) {
	return func(macro *common.Macro) {}
}

func (l *whileLoop) Start() func(*common.Macro) {
	return func(macro *common.Macro) {}
}

func While(predicate PredicateFunc) LoopPredicate {
	return &whileLoop{predicate: predicate}
}

type foreverLoop struct{}

func (l *foreverLoop) Predicate() PredicateFunc {
	return func(macro *common.Macro) bool {
		return true
	}
}

func (l *foreverLoop) Step() func(*common.Macro) {
	return func(macro *common.Macro) {}
}

func (l *foreverLoop) Start() func(*common.Macro) {
	return func(macro *common.Macro) {}
}

func Forever() LoopPredicate {
	return &foreverLoop{}
}

type untilLoop struct {
	predicate PredicateFunc
}

func (l *untilLoop) Predicate() PredicateFunc {
	return func(macro *common.Macro) bool {
		return !l.predicate(macro)
	}
}

func (l *untilLoop) Step() func(*common.Macro) {
	return func(macro *common.Macro) {}
}

func (l *untilLoop) Start() func(*common.Macro) {
	return func(macro *common.Macro) {}
}

func Until(predicate PredicateFunc) LoopPredicate {
	return &untilLoop{predicate: predicate}
}

func Loop(predicate LoopPredicate, actions ...interface{}) common.Action {
	var actionFns []common.Action
	for _, action := range actions {
		switch fn := action.(type) {
		case common.Action:
			actionFns = append(actionFns, fn)
		case func() error:
		case func(macro *common.Macro) error:
			actionFns = append(actionFns, Logic(fn))
		default:
			panic("unknown action type")
		}
	}
	return &loopAction{predicate, actionFns}
}

type continueAction struct {
	depth int
}

func (a *continueAction) Execute(macro *common.Macro) error {
	macro.Scratch.LoopState.Unwind = &config.UnwindLoop{Depth: a.depth, Continue: true}
	return nil
}

func Continue(depth ...int) common.Action {
	if len(depth) > 1 {
		panic("invalid arguments")
	}
	var depthV int
	if len(depth) == 1 {
		depthV = depth[0]
	}
	return &continueAction{depth: depthV}
}

type breakAction struct {
	depth int
}

func (a *breakAction) Execute(macro *common.Macro) error {
	macro.Scratch.LoopState.Unwind = &config.UnwindLoop{Depth: a.depth}
	return nil
}

func Break(depth ...int) common.Action {
	if len(depth) > 1 {
		panic("invalid arguments")
	}
	var depthV int
	if len(depth) == 1 {
		depthV = depth[0]
	}
	return &breakAction{depth: depthV}
}

type Cases[T comparable] map[T]common.Action

type switchAction struct {
}

type stepBackAction struct{}

func (r *stepBackAction) Execute(*common.Macro) error { return common.StepBackSignal }
func StepBack() common.Action                         { return &stepBackAction{} }

type restartAction struct{}

func (r *restartAction) Execute(*common.Macro) error { return common.RestartSignal }
func Restart() common.Action                         { return &restartAction{} }

type terminateAction struct{}

func (r *terminateAction) Execute(*common.Macro) error { return common.TerminateSignal }
func Terminate() common.Action                         { return &terminateAction{} }

func ComputeValue[T any](macro *common.Macro, value interface{}) T {
	switch v := value.(type) {
	case func(macro *common.Macro) T:
		return v(macro)
	case T:
		return v
	default:
		panic(fmt.Sprintf("invalid value: %T", value))
	}
}
