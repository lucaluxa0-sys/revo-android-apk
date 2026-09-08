//go:build darwin

package platform

import (
	. "github.com/nosyliam/revolution/pkg/common"
)

var KeyCodeMap = map[Key]int{
	Forward:  0x0D,
	Backward: 0x01,
	Left:     0x00,
	Right:    0x02,
	RotLeft:  0x2B,
	RotRight: 0x2F,
	RotUp:    0x74,
	RotDown:  0x79,
	ZoomIn:   0x22,
	ZoomOut:  0x1F,
	E:        0x0E,
	R:        0x0F,
	L:        0x25,
	Esc:      0x35,
	Enter:    0x24,
	LShift:   0x38,
	Space:    0x31,
	One:      0x12,
	Two:      0x13,
	Three:    0x14,
	Four:     0x15,
	Five:     0x17,
	Six:      0x16,
	Seven:    0x1A,
}
