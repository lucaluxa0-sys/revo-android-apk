package common

import (
	"github.com/nosyliam/revolution/pkg/config"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"image"
)

type Key int
type Receiver <-chan struct{}

var Send = struct{}{}

const (
	Forward Key = iota
	Backward
	Left
	Right
	RotLeft
	RotRight
	RotUp
	RotDown
	ZoomIn
	ZoomOut
	E
	R
	L
	Esc
	Enter
	LShift
	Space
	One
	Two
	Three
	Four
	Five
	Six
	Seven
)

type InterruptKind int

const (
	DelayedInterrupt InterruptKind = iota
	IntervalInterrupt
)

type Backend interface {
	KeyDown(pid int, key Key)
	KeyUp(pid int, key Key)
	MoveMouse(x, y int)
	ScrollMouse(x, y int)
	Sleep(ms int, interrupt Receiver)
	SleepAsync(ms int, interrupt Receiver) Receiver
	AttachInput(pid int)
}

type EventBus interface {
	Start()
	KeyDown(window *Macro, key Key) Receiver
	KeyUp(macro *Macro, key Key) Receiver
	MoveMouse(macro *Macro, x, y int) Receiver
	ScrollMouse(macro *Macro, x, y int) Receiver
}

type InputManager interface {
	Reset()
	ResetCharacter()
	KeyDown(key Key)
	KeyUp(key Key)
	KeyPress(key Key)
	SetPitch(pitch int)
	SetYaw(yaw int)
	SetZoom(zoom int)
	Pitch() int
	Yaw() int
	Zoom() int
	Sleep(ms int)
}

type Scheduler interface {
	Execute(interruptType InterruptKind)
	Start()
	Close()
	Initialize(macro *Macro)
	RequestFrame() <-chan *image.RGBA
}

type Event interface {
	Execute(backend Backend)
}

type BuffDetector interface {
	Tick(origin *revimg.Point, screenshot *image.RGBA)
	MoveSpeed() float64
	Watch() chan struct{}
	Unwatch(chan struct{})
}

type Alignment interface {
	PerformDetection(macro *Macro)
}

type PatternLoader interface {
	Start() error
	Patterns() []string
	Exists(pattern string) bool
	Execute(macro *Macro, meta *config.PatternMetadata, pattern string) error
}

type VicHop interface {
	Tick(macro *Macro)
	ReadQueue(macro *Macro)
	BattleDetect(macro *Macro)
	StopBattleDetect(macro *Macro)
	BattleActive(macro *Macro) bool
	Detect(macro *Macro, field string) (bool, error)
	FindServer(macro *Macro) (string, error)
}
