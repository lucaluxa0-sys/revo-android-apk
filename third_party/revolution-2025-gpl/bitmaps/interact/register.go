package interact

import (
	_ "embed"
	"github.com/nosyliam/revolution/bitmaps/registry"
)

func Register(registry registry.Registry) {
	registry.RegisterPng("press_e", e)
}

//go:embed press_e.png
var e []byte
