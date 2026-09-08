package actions

import (
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/movement"
)

type mouseMoveAction struct {
	x, y int
}

func (a *mouseMoveAction) Execute(macro *common.Macro) error {
	<-macro.EventBus.MoveMouse(macro, a.x, a.y)
	return nil
}

func MoveMouse(x, y int) common.Action {
	return &mouseMoveAction{x, y}
}

type keyPressAction struct {
	key common.Key
}

func (a *keyPressAction) Execute(macro *common.Macro) error {
	macro.Input.KeyPress(a.key)
	return nil
}

func KeyPress(key common.Key) common.Action {
	return &keyPressAction{key}
}

type keyDownAction struct {
	key common.Key
}

func (a *keyDownAction) Execute(macro *common.Macro) error {
	macro.Input.KeyDown(a.key)
	return nil
}

func KeyDown(key common.Key) common.Action {
	return &keyDownAction{key}
}

type keyUpAction struct {
	key common.Key
}

func (a *keyUpAction) Execute(macro *common.Macro) error {
	macro.Input.KeyPress(a.key)

	return nil
}

func KeyUp(key common.Key) common.Action {
	return &keyUpAction{key}
}

type walkAction struct {
	distance  float64
	direction movement.Direction
}

func (a *walkAction) Execute(macro *common.Macro) error {
	movement.Walk(a.direction, a.distance, macro)
	return nil
}

func Walk(key common.Key, distance float64) common.Action {
	var direction movement.Direction
	switch key {
	case common.Forward:
		direction = movement.Forward
	case common.Backward:
		direction = movement.Backward
	case common.Left:
		direction = movement.Left
	case common.Right:
		direction = movement.Right
	default:
		panic("invalid direction!")
	}
	return &walkAction{distance: distance, direction: direction}
}

type resetCharacterAction struct{}

func (a *resetCharacterAction) Execute(macro *common.Macro) error {
	macro.Input.ResetCharacter()
	return nil
}

func ResetCharacter() common.Action {
	return &resetCharacterAction{}
}
