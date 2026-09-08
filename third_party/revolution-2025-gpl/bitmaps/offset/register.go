package offset

import (
	_ "embed"
	"github.com/nosyliam/revolution/bitmaps/registry"
)

func Register(registry registry.Registry) {
	registry.RegisterPng("tophoney", tophoney)
	registry.RegisterPng("roblox", roblox)
	registry.RegisterPng("roblox_alt", robloxalt)
	registry.RegisterPng("hotbar", hotbar)
}

//go:embed tophoney.png
var tophoney []byte

//go:embed roblox_alt.png
var robloxalt []byte

//go:embed roblox.png
var roblox []byte

//go:embed hotbar.png
var hotbar []byte
