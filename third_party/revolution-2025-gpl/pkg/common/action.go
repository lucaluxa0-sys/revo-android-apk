package common

import (
	revimg "github.com/nosyliam/revolution/pkg/image"
	"image"
)

type Actions []Action

func (a Actions) Register(kind RoutineKind) {
	Routines[kind] = a
}

type ActionResults struct {
	EditedScreenshot  *image.RGBA
	ImageSearchPoints []revimg.Point
}

type Action interface {
	Execute(macro *Macro) error
}

var Routines = make(map[RoutineKind]Actions)
