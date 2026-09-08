//go:build windows

package platform

import (
	. "github.com/nosyliam/revolution/pkg/common"
	"syscall"
)

var (
	user32            = syscall.NewLazyDLL("user32.dll")
	procMapVirtualKey = user32.NewProc("MapVirtualKeyW")
)

var KeyCodeMap = map[Key]int{
	Forward:  0x57,
	Backward: 0x53,
	Left:     0x41,
	Right:    0x44,
	RotLeft:  0xBC,
	RotRight: 0xBE,
	RotUp:    0x21,
	RotDown:  0x22,
	ZoomIn:   0x49,
	ZoomOut:  0x4F,
	E:        0x45,
	R:        0x52,
	L:        0x4C,
	Esc:      0x1B,
	Enter:    0x0D,
	LShift:   0x10,
	Space:    0x20,
	One:      0x31,
	Two:      0x32,
	Three:    0x33,
	Four:     0x34,
	Five:     0x35,
	Six:      0x36,
	Seven:    0x37,
}

func init() {
	for key, vk := range KeyCodeMap {
		sc := mapVirtualKey(uint32(vk), 0)

		if key == RotUp || key == RotDown {
			sc |= 0xE000
		}

		KeyCodeMap[key] = int(sc)
	}
}

func mapVirtualKey(vk uint32, mapType uint32) uint32 {
	ret, _, _ := procMapVirtualKey.Call(uintptr(vk), uintptr(mapType))
	return uint32(ret)
}
