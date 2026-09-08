package hive

import (
	_ "embed"
	"github.com/nosyliam/revolution/bitmaps/registry"
)

func Register(registry registry.Registry) {
	registry.RegisterPng("makehoney", makehoney)
	registry.RegisterPng("claimhive", claimhive)
	registry.RegisterPng("tomake", tomake)
	registry.RegisterPng("sendtrade", sendtrade)
	registry.RegisterPng("tradedisabled", tradedisabled)
	registry.RegisterPng("tradelocked", tradelocked)
}

//go:embed makehoney.png
var makehoney []byte

//go:embed claimhive.png
var claimhive []byte

//go:embed tomake.png
var tomake []byte

//go:embed sendtrade.png
var sendtrade []byte

//go:embed tradedisabled.png
var tradedisabled []byte

//go:embed tradelocked.png
var tradelocked []byte
