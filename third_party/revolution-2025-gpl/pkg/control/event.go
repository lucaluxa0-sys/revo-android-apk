package control

import (
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/window"
)

type Event struct {
	window *window.Window
}

type MouseMoveEvent struct {
	Event
	x, y int
}

func (e *MouseMoveEvent) Execute(backend common.Backend) {
	if e.window.Activate() == nil {
		backend.MoveMouse(e.x, e.y)
	}
}

type MouseScrollEvent struct {
	Event
	x, y int
}

func (e *MouseScrollEvent) Execute(backend common.Backend) {
	if e.window.Activate() == nil {
		backend.ScrollMouse(e.x, e.y)
	}
}

type KeyDownEvent struct {
	Event
	key common.Key
}

func (e *KeyDownEvent) Execute(backend common.Backend) {
	if e.window.Activate() == nil {
		backend.KeyDown(e.window.PID(), e.key)
	}
}

type KeyUpEvent struct {
	Event
	key common.Key
}

func (e *KeyUpEvent) Execute(backend common.Backend) {
	if e.window.Activate() == nil {
		backend.KeyUp(e.window.PID(), e.key)
	}
}
