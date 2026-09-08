package platform

import (
	"fmt"
	"github.com/nosyliam/revolution/pkg/image"
	"github.com/nosyliam/revolution/pkg/window"
	"github.com/stretchr/testify/assert"
	"testing"
	"time"
)

func Test_DisplayFrames(t *testing.T) {
	frames, err := WindowBackend.DisplayFrames()
	assert.NoError(t, err)
	assert.GreaterOrEqual(t, len(frames), 1)
	assert.Greater(t, frames[0].Height, 500)
}

func Test_Capture(t *testing.T) {
	id, err := WindowBackend.OpenWindow(window.JoinOptions{})
	assert.NoError(t, err)
	_, err = WindowBackend.StartCapture(id)
	assert.NoError(t, err)
	time.Sleep(78 * time.Second)
}

func Test_Window(t *testing.T) {
	frames, err := WindowBackend.DisplayFrames()
	assert.NoError(t, err)
	fmt.Println(frames)

	id, err := WindowBackend.OpenWindow(window.JoinOptions{})
	assert.NoError(t, err)

	err = WindowBackend.ActivateWindow(id)
	assert.NoError(t, err)

	err = WindowBackend.SetFrame(id, image.Frame{100, 100, 0, 0})
	assert.NoError(t, err)

	fmt.Println(WindowBackend.GetFrame(id))

	err = WindowBackend.ActivateWindow(id)
	assert.NoError(t, err)

	/*img, err := WindowBackend.Screenshot(id)
	assert.NoError(t, err)

	f, _ := os.Create("test.png")
	png.Encode(f, img)
	f.Close()*/
}
