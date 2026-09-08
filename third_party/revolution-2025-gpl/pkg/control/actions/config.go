package actions

import (
	"github.com/nosyliam/revolution/pkg/common"
)

type setStateAction struct {
	path string
	val  interface{}
}

func (a *setStateAction) Execute(macro *common.Macro) error {
	var computed = a.val
	switch val := a.val.(type) {
	case func(macro *common.Macro) int:
		computed = val(macro)
	case func(macro *common.Macro) bool:
		computed = val(macro)
	case func(macro *common.Macro) string:
		computed = val(macro)
	}
	return macro.Root.MacroState.SetPath(a.path, computed)
}

func SetState(path string, val interface{}) common.Action {
	return &setStateAction{path: path, val: val}
}
