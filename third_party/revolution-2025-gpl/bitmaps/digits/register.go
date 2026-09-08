package digits

import (
	_ "embed"
)

import "github.com/nosyliam/revolution/bitmaps/registry"

func Register(registry registry.Registry) {
	registry.RegisterPng("digit_zero", zero)
	registry.RegisterPng("digit_one", one)
	registry.RegisterPng("digit_two", two)
	registry.RegisterPng("digit_three", three)
	registry.RegisterPng("digit_four", four)
	registry.RegisterPng("digit_five", five)
	registry.RegisterPng("digit_six", six)
	registry.RegisterPng("digit_seven", seven)
	registry.RegisterPng("digit_eight", eight)
	registry.RegisterPng("digit_nine", nine)
}

//go:embed digit_0.png
var zero []byte

//go:embed digit_1.png
var one []byte

//go:embed digit_2.png
var two []byte

//go:embed digit_3.png
var three []byte

//go:embed digit_4.png
var four []byte

//go:embed digit_5.png
var five []byte

//go:embed digit_6.png
var six []byte

//go:embed digit_7.png
var seven []byte

//go:embed digit_8.png
var eight []byte

//go:embed digit_9.png
var nine []byte
