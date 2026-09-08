package actions

import (
	"fmt"
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/movement"
)

type SleepAction struct {
	ms      int
	seconds bool
}

func (a *SleepAction) Seconds() *SleepAction {
	a.seconds = true
	return a
}

func (a *SleepAction) Execute(macro *common.Macro) error {
	var ms = a.ms
	if a.seconds {
		ms *= 1000
	}
	movement.Sleep(ms, macro)
	return nil
}

func Sleep(ms int) *SleepAction {
	return &SleepAction{ms, false}
}

type executePatternAction struct {
	name  interface{}
	id    string
	async bool
}

func (e *executePatternAction) Execute(macro *common.Macro) error {
	var computed string
	switch val := e.name.(type) {
	case func(macro *common.Macro) string:
		computed = val(macro)
	case string:
		computed = val
	}
	if e.async {
		go func() {
			if err := macro.Pattern.Execute(macro, nil, computed); err != nil {
				macro.Action(Error(fmt.Sprintf("Async pattern execution failed: %v", err))(Discord))
			}
		}()
		return nil
	}
	return macro.Pattern.Execute(macro, nil, computed)
}

func (e *executePatternAction) Async() common.Action {
	e.async = true
	return e
}

func ExecutePattern(name interface{}) *executePatternAction {
	return &executePatternAction{name: name}
}

type cancelPatternAction struct{}

func (e *cancelPatternAction) Execute(macro *common.Macro) error {
	if macro.GetRoot().CancelPattern != nil {
		macro.GetRoot().CancelPattern()
	}
	return nil
}

func CancelPattern() common.Action {
	return &cancelPatternAction{}
}

type waitForPatternStartAction struct{}

func (e *waitForPatternStartAction) Execute(macro *common.Macro) error {
	for macro.GetRoot().CancelPattern == nil {
		movement.Sleep(10, macro)
	}
	return nil
}

func WaitForPatternStart() common.Action {
	return &waitForPatternStartAction{}
}
