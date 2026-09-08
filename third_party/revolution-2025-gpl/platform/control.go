package platform

// #include "control.h"
import "C"

import (
	"github.com/nosyliam/revolution/pkg/common"
	"runtime"
	"unsafe"
)

var ControlBackend common.Backend = &controlBackend{}

type controlBackend struct{}

func (c controlBackend) AttachInput(pid int) {
	C.attach_input_thread(C.int(pid))
}

func (c controlBackend) KeyDown(pid int, key common.Key) {
	var extended = 0
	if runtime.GOOS == "darwin" {
		extended = pid
	} else {
		if key == common.RotUp || key == common.RotDown {
			extended = 1
		}
	}
	C.send_key_event(C.int(extended), true, C.int(KeyCodeMap[key]))
}

func (c controlBackend) KeyUp(pid int, key common.Key) {
	var extended = 0
	if runtime.GOOS == "darwin" {
		extended = pid
	} else {
		if key == common.RotUp || key == common.RotDown {
			extended = 1
		}
	}
	C.send_key_event(C.int(extended), false, C.int(KeyCodeMap[key]))
}

func (c controlBackend) MoveMouse(x, y int) {
	C.move_mouse(C.int(x), C.int(y))
}

func (c controlBackend) ScrollMouse(x, y int) {
	C.scroll_mouse(C.int(x), C.int(y))
}

func (c controlBackend) SleepAsync(ms int, interrupt common.Receiver) common.Receiver {
	sleepDone := make(chan struct{})

	go func() {
		intV := 0
		done := make(chan bool)

		go func() {
			select {
			case <-interrupt:
				intV = 1
			case <-done:
			}
		}()

		C.microsleep(C.int(ms), (*C.int)(unsafe.Pointer(&intV)))
		close(done)
		sleepDone <- struct{}{}
	}()

	return sleepDone
}

func (c controlBackend) Sleep(ms int, interrupt common.Receiver) {
	intV := 0
	done := make(chan bool)

	go func() {
		select {
		case <-interrupt:
			intV = 1
		case <-done:
		}
	}()

	C.microsleep(C.int(ms), (*C.int)(unsafe.Pointer(&intV)))
	close(done)
}
