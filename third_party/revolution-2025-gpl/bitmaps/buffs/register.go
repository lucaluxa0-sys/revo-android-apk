package buffs

import (
	_ "embed"
	"github.com/nosyliam/revolution/bitmaps/registry"
)

func Register(registry registry.Registry) {
	registry.RegisterPng("black_bear", blackbear)
	registry.RegisterPng("brown_bear", brownbear)
	registry.RegisterPng("gummy_bear", gummybear)
	registry.RegisterPng("mother_bear", motherbear)
	registry.RegisterPng("panda_bear", pandabear)
	registry.RegisterPng("polar_bear", polarbear)
	registry.RegisterPng("science_bear", sciencebear)
	registry.RegisterPng("melody", melody)
	registry.RegisterPng("oil", oil)
	registry.RegisterPng("smoothie", smoothie)
}

//go:embed black_bear.png
var blackbear []byte

//go:embed brown_bear.png
var brownbear []byte

//go:embed gummy_bear.png
var gummybear []byte

//go:embed mother_bear.png
var motherbear []byte

//go:embed panda_bear.png
var pandabear []byte

//go:embed polar_bear.png
var polarbear []byte

//go:embed science_bear.png
var sciencebear []byte

//go:embed melody.png
var melody []byte

//go:embed oil.png
var oil []byte

//go:embed smoothie.png
var smoothie []byte
