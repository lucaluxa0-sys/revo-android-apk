package movement

import (
	"fmt"
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/config"
	"github.com/nosyliam/revolution/pkg/logging"
	"math"
	"slices"
)

type InputManager struct {
	macro *common.Macro
	pitch int // Up, Down
	yaw   int // Left, Right
	zoom  int
}

func NewInputManager(macro *common.Macro) *InputManager {
	return &InputManager{macro: macro, zoom: 2}
}

func (i *InputManager) Reset() {
	i.pitch = 0
	i.yaw = 0
	i.zoom = 2
	i.SetZoom(0)
	i.SetZoom(2)
}

func (i *InputManager) KeyDown(key common.Key) {
	if slices.Contains([]common.Key{common.RotDown, common.RotUp, common.RotLeft, common.RotRight}, key) {
		i.macro.Logger.Log(0, logging.Warning, "Ignoring key event for rotation key: SetPitch or SetYaw must be used")
		return
	}
	<-i.macro.EventBus.KeyDown(i.macro, key)
}

func (i *InputManager) KeyUp(key common.Key) {
	<-i.macro.EventBus.KeyUp(i.macro, key)
}

func (i *InputManager) KeyPress(key common.Key) {
	if slices.Contains([]common.Key{common.RotDown, common.RotUp, common.RotLeft, common.RotRight}, key) {
		i.macro.Logger.Log(0, logging.Warning, "Ignoring key event for rotation key: SetPitch or SetYaw must be used")
		return
	}
	<-i.macro.EventBus.KeyDown(i.macro, key)
	Sleep(*config.Concrete[int](i.macro.Settings, "macro.keyDelay"), i.macro)
	<-i.macro.EventBus.KeyUp(i.macro, key)
}

func (i *InputManager) SetPitch(pitch int) {
	if pitch > 3 {
		return
	} else if pitch < -6 {
		i.macro.Logger.Log(0, logging.Warning, "Ignoring set pitch: pitch must greater than -7")
		return
	} else if pitch == i.pitch {
		return
	}
	dir := common.RotDown
	if pitch > i.pitch {
		dir = common.RotUp
	}
	for x := 0; x < int(math.Abs(float64(pitch-i.pitch))); x++ {
		<-i.macro.EventBus.KeyDown(i.macro, dir)
		Sleep(10, i.macro)
		<-i.macro.EventBus.KeyUp(i.macro, dir)
	}
	i.pitch = pitch
}

func (i *InputManager) SetYaw(yaw int) {
	if yaw < 0 {
		i.macro.Logger.Log(0, logging.Warning, "Ignoring set yaw: must be greater than or equal to zero")
		return
	}
	if yaw > 7 {
		i.macro.Logger.Log(0, logging.Warning, "Ignoring set yaw: must be less than 8")
		return
	}
	if yaw == i.yaw {
		return
	}
	distance := (yaw - i.yaw + 8) % 8
	dir := common.RotRight
	if counter := (i.yaw - yaw + 8) % 8; counter < distance {
		dir = common.RotLeft
		distance = counter
	}
	fmt.Println(distance, dir)
	for x := 0; x < distance; x++ {
		<-i.macro.EventBus.KeyDown(i.macro, dir)
		Sleep(10, i.macro)
		<-i.macro.EventBus.KeyUp(i.macro, dir)
	}

	i.yaw = yaw
}

func (i *InputManager) SetZoom(zoom int) {
	if zoom < 0 || zoom > 5 {
		i.macro.Logger.Log(0, logging.Warning, "Ignoring set zoom: zoom must be between 0 and 5")
		return
	}
	if zoom == i.zoom {
		return
	}
	dir := common.ZoomIn
	if zoom > i.zoom {
		dir = common.ZoomOut
	}
	for x := 0; x < int(math.Abs(float64(zoom-i.zoom))); x++ {
		<-i.macro.EventBus.KeyDown(i.macro, dir)
		Sleep(10, i.macro)
		<-i.macro.EventBus.KeyUp(i.macro, dir)
	}
	i.zoom = zoom
}

func (i *InputManager) Sleep(ms int) {
	Sleep(ms, i.macro)
}

func (i *InputManager) Zoom() int {
	return i.zoom
}

func (i *InputManager) Pitch() int {
	return i.pitch
}

func (i *InputManager) Yaw() int {
	return i.yaw
}

func (i *InputManager) ResetCharacter() {
	i.KeyPress(common.Esc)
	i.KeyPress(common.R)
	i.KeyPress(common.Enter)
	i.Sleep(7000)
	i.Reset()
	// TODO: Spawn detection via health bar
}
