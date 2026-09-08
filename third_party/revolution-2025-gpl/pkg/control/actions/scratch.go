package actions

import "github.com/nosyliam/revolution/pkg/common"

type setVariableAction struct {
	name VariableName
	val  interface{}
}

func (a *setVariableAction) Execute(macro *common.Macro) error {
	var computed = a.val
	switch val := a.val.(type) {
	case func(macro *common.Macro) int:
		computed = val(macro)
	case func(macro *common.Macro) bool:
		computed = val(macro)
	case func(macro *common.Macro) string:
		computed = val(macro)
	}
	macro.Scratch.Set(string(a.name), computed)
	return nil
}

func Set(name VariableName, val interface{}) common.Action {
	return &setVariableAction{name: name, val: val}
}

type resetVariableAction struct {
	name VariableName
}

func (a *resetVariableAction) Execute(macro *common.Macro) error {
	macro.Scratch.Reset(string(a.name))
	return nil
}

func Reset(name VariableName) common.Action {
	return &resetVariableAction{name: name}
}

type incrementVariableAction struct {
	name VariableName
}

func (a *incrementVariableAction) Execute(macro *common.Macro) error {
	macro.Scratch.Increment(string(a.name))
	return nil
}

type decrementVariableAction struct {
	name VariableName
}

func (a *decrementVariableAction) Execute(macro *common.Macro) error {
	macro.Scratch.Decrement(string(a.name))
	return nil
}

func Increment(name VariableName) common.Action {
	return &incrementVariableAction{name: name}
}

func Decrement(name VariableName) common.Action {
	return &decrementVariableAction{name: name}
}

type clearVariableAction struct {
	name VariableName
}

func (a *clearVariableAction) Execute(macro *common.Macro) error {
	macro.Scratch.Clear(string(a.name))
	return nil
}

func Clear(name VariableName) common.Action {
	return &clearVariableAction{name: name}
}

type subtractVariableAction struct {
	name  VariableName
	value int
}

func (a *subtractVariableAction) Execute(macro *common.Macro) error {
	macro.Scratch.Subtract(string(a.name), a.value)
	return nil
}

func Subtract(name VariableName, value int) common.Action {
	return &subtractVariableAction{name: name, value: value}
}
