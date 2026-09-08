package reconnect

import (
	_ "embed"
	"github.com/nosyliam/revolution/bitmaps/registry"
)

func Register(registry registry.Registry) {
	registry.RegisterPng("loading", loading)
	registry.RegisterPng("science", science)
	registry.RegisterPng("disconnected", disconnected)
	registry.RegisterPng("fullserver", fullserver)
	registry.RegisterPng("restricted", restricted)
}

//go:embed loading.png
var loading []byte

//go:embed science.png
var science []byte

//go:embed disconnected.png
var disconnected []byte

//go:embed fullserver.png
var fullserver []byte

//go:embed restricted.png
var restricted []byte
