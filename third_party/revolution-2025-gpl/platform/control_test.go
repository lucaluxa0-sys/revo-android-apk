package platform

import (
	"fmt"
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/stretchr/testify/assert"
	"testing"
	"time"
)

func Test_Sleep(t *testing.T) {
	start := time.Now()
	ControlBackend.Sleep(500, make(chan struct{}))
	end := time.Now()
	assert.GreaterOrEqual(t, end.Sub(start), 500*time.Millisecond)

	// Test interrupt
	interrupt := make(chan struct{})
	start = time.Now()
	go func() {
		time.Sleep(100 * time.Millisecond)
		interrupt <- struct{}{}
	}()
	ControlBackend.Sleep(500, interrupt)
	end = time.Now()
	fmt.Println(end.Sub(start))
	assert.LessOrEqual(t, end.Sub(start), 150*time.Millisecond)

}

func TestControlBackend_MoveMouse(t *testing.T) {
	ControlBackend.MoveMouse(0, 0)
}

func TestControlBackend_ScrollMouse(t *testing.T) {
	ControlBackend.ScrollMouse(0, 100)
}

func TestControlBackend_Key(t *testing.T) {
	ControlBackend.KeyDown(0, common.Forward)
	time.Sleep(1 * time.Second)
	ControlBackend.KeyUp(0, common.Forward)
}
