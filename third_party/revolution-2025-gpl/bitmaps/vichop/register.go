package vichop

import (
	_ "embed"
	"github.com/nosyliam/revolution/bitmaps/registry"
)

func Register(registry registry.Registry) {
	registry.RegisterPng("vicdefeated", vicdefeated)
	registry.RegisterPng("giftedvicdefeated", giftedvicdefeated)
}

//go:embed vicdefeated.png
var vicdefeated []byte

//go:embed giftvicdefeated.png
var giftedvicdefeated []byte
