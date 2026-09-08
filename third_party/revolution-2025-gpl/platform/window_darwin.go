//go:build darwin

package platform

// #include "window.h"
// #include "capture_darwin/CaptureBridge.h"
//
//extern void GoFrameCallback(int id, unsigned char* data, size_t length, int width, int height, int stride);
//
//static inline FrameCallback getCallbackPtr() {
//    return (FrameCallback)GoFrameCallback;
//}
import "C"

import (
	"encoding/json"
	"fmt"
	ps "github.com/mitchellh/go-ps"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"github.com/nosyliam/revolution/pkg/window"
	"github.com/pkg/errors"
	"image"
	"io"
	"net/http"
	"os"
	"os/exec"
	"regexp"
	"sync"
	"time"
	"unsafe"
)

var singleton = &windowBackend{
	windows: make(map[int]*windowData),
}

var WindowBackend window.Backend = singleton

type windowData struct {
	win        *C.Window
	mu         sync.Mutex
	controller C.CaptureControllerRef
	output     chan<- *image.RGBA
}

type windowBackend struct {
	mu        sync.Mutex
	windows   map[int]*windowData
	robloxLoc string
}

func (w *windowBackend) DissociateWindow(id int) {
	if _, ok := w.windows[id]; ok {
		w.freeWindow(id)
	}
	w.mu.Lock()
	delete(w.windows, id)
	w.mu.Unlock()
}

func (w *windowBackend) CloseWindow(id int) error {
	proc, err := os.FindProcess(id)
	if err == nil {
		_ = proc.Kill()
	}

	if _, ok := w.windows[id]; ok {
		w.freeWindow(id)
	}
	w.mu.Lock()
	delete(w.windows, id)
	w.mu.Unlock()
	return nil
}

func (w *windowBackend) freeWindow(id int) {
	win, ok := w.windows[id]
	if !ok {
		return
	}
	w.StopCapture(id)
	w.mu.Lock()
	C.CFRelease((C.CFTypeRef)(win.win.window))
	C.free(unsafe.Pointer(win.win))
	w.mu.Unlock()
}

func (w *windowBackend) getWindow(id int) (*windowData, error) {
	resp := (bool)(C.check_ax_enabled(C.bool(true)))
	if resp == false {
		return nil, window.PermissionDeniedErr
	}

	win, ok := w.windows[id]
	if !ok {
		return nil, window.WindowNotFoundErr
	}

	_, err := ps.FindProcess(id)
	if err != nil {
		return nil, window.WindowNotFoundErr
	}

	return win, nil
}

func (w *windowBackend) initializeWindow(pid int) bool {
	ret := (*C.Window)(C.get_window_with_pid(C.int(pid)))
	if ret == nil {
		return false
	}

	w.windows[pid] = &windowData{win: ret}
	return true
}

func (w *windowBackend) getRobloxVersion(loc string) (string, error) {
	pList, err := os.Open(fmt.Sprintf("%s/Contents/Info.plist", loc))
	if os.IsNotExist(err) {
		return "", nil
	} else if err != nil {
		return "", errors.Wrap(err, "failed to open Roblox application info for update check")
	}

	data, err := io.ReadAll(pList)
	if err != nil {
		return "", errors.Wrap(err, "failed to read Roblox application info for update check")
	}

	_ = pList.Close()

	versionReg := regexp.MustCompile("<key>CFBundleShortVersionString</key>\n\t<string>(.*)</string>")
	matches := versionReg.FindStringSubmatch(string(data))
	if len(matches) <= 1 {
		return "", errors.Wrap(err, "failed to read Roblox version")
	}

	return matches[1], nil
}

func (w *windowBackend) SetRobloxLocation(loc string) {
	w.robloxLoc = loc
}

func (w *windowBackend) HopServer(options window.JoinOptions) error {
	cmd := exec.Command("open", "-n", options.String())
	err := cmd.Start()
	if err != nil {
		return errors.Wrap(err, "failed to open roblox")
	}
	return nil
}

func (w *windowBackend) OpenWindow(options window.JoinOptions) (int, error) {
	w.mu.Lock()
	defer w.mu.Unlock()
	resp := (bool)(C.check_ax_enabled(C.bool(true)))
	if resp == false {
		return 0, window.PermissionDeniedErr
	}

	// Attempt to bind non-macro roblox instances first
	findRunningInstance := func(initialize bool) (int, error) {
		processes, err := ps.Processes()
		if err != nil {
			return 0, errors.Wrap(err, "failed to list processes")
		}
		for _, process := range processes {
			if pid := process.Pid(); process.Executable() == "RobloxPlayer" {
				if !initialize {
					return pid, nil
				}
				if _, ok := w.windows[pid]; !ok {
					if w.initializeWindow(pid) {
						return pid, nil
					}
				}
			}
		}
		return -1, nil
	}

	fmt.Println(options, options.GameInstance == "")
	if options.GameInstance == "" {
		if pid, err := findRunningInstance(true); err != nil {
			return 0, err
		} else if pid != -1 {
			return pid, nil
		}
	}

	loc := "/Applications/Roblox.app"
	if w.robloxLoc != "" {
		loc = w.robloxLoc
	}

	version, err := w.getRobloxVersion(loc)
	if err != nil {
		return 0, errors.Wrap(err, "failed to get current Roblox version")
	}

	vResp, err := http.Get("https://clientsettingscdn.roblox.com/v2/client-version/MacPlayer")
	if err != nil {
		return 0, errors.Wrap(err, "failed to fetch latest Roblox version")
	}

	data, _ := io.ReadAll(vResp.Body)

	dataMap := make(map[string]interface{})
	err = json.Unmarshal(data, &dataMap)
	if err != nil {
		return 0, errors.Wrap(err, "failed to unmarshal latest Roblox version")
	}

	if dataMap["version"].(string) != version {
		var pid = -1
		cmd := exec.Command("open", fmt.Sprintf("%s/Contents/MacOS/RobloxPlayerInstaller.app", loc))
		err = cmd.Start()
		if err != nil {
			return 0, errors.New("failed to start installer")
		}

		for i := 0; i < 1000; i++ {
			if pid, err = findRunningInstance(false); err != nil {
				return 0, err
			} else if pid != -1 {
				break
			}
			<-time.After(10 * time.Millisecond)
		}

		if pid == -1 {
			return 0, errors.New("failed to find installer process")
		}

		for i := 0; i < 1000; i++ {
			if int((C.int)(C.get_window_count(C.int(pid)))) == 1 {
				break
			}
			<-time.After(10 * time.Millisecond)
		}

		proc, err := os.FindProcess(pid)
		if err == nil {
			_ = proc.Kill()
		}
	}

	for i := 0; i < 10; i++ {
		fmt.Println("Attempting open", options.String())
		cmd := exec.Command("open", "-n", options.String())
		err = cmd.Start()
		if err != nil {
			return 0, errors.New("failed to start installer")
		}

		var pid = 0

		for j := 0; j < 500; j++ {
			if pid, err = findRunningInstance(true); err != nil {
				return 0, err
			} else if pid != -1 {
				break
			}
			<-time.After(10 * time.Millisecond)
		}

		for i := 0; i < 1000; i++ {
			if int((C.int)(C.get_window_count(C.int(pid)))) == 1 {
				return pid, nil
			}
			<-time.After(10 * time.Millisecond)
		}

		<-time.After(1 * time.Second)
	}

	return 0, errors.New("failed to initialize roblox process")
}

func (w *windowBackend) ActivateWindow(id int) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	win, err := w.getWindow(id)
	if err != nil {
		return err
	}

	C.activate_window(win.win)
	return nil
}

//export GoFrameCallback
func GoFrameCallback(id C.int, data *C.uchar, length C.size_t, width, height, stride C.int) {
	buf := C.GoBytes(unsafe.Pointer(data), C.int(length))
	C.free(unsafe.Pointer(data))

	img := &image.RGBA{}
	img.Rect = image.Rect(0, 0, int(width), int(height))
	img.Pix = buf
	img.Stride = int(stride)

	if win, ok := singleton.windows[int(id)]; ok {
		win.mu.Lock()
		if win.output != nil && len(win.output) == 0 {
			win.output <- img
		}
		win.mu.Unlock()
	}
}

func (w *windowBackend) StartCapture(id int) (<-chan *image.RGBA, error) {
	w.mu.Lock()
	defer w.mu.Unlock()
	win, err := w.getWindow(id)
	if err != nil {
		return nil, err
	}

	controller := C.CreateCaptureController()
	if controller == nil {
		return nil, errors.New("failed to create capture controller")
	}

	cbPtr := C.getCallbackPtr()
	C.SetFrameCallback(controller, cbPtr)
	C.SetID(controller, C.int(id))

	output := make(chan *image.RGBA, 1)
	win.output = output

	if !C.StartCapture(controller, win.win.id) {
		return nil, errors.New("failed to start capture")
	}

	fmt.Printf("Capture started for window ID: %d\n", id)
	win.controller = controller
	return output, nil
}

func (w *windowBackend) StopCapture(id int) {
	w.mu.Lock()
	defer w.mu.Unlock()
	win, err := w.getWindow(id)
	if err != nil {
		return
	}
	win.mu.Lock()
	defer win.mu.Unlock()
	if win.output != nil {
		close(win.output)
		win.output = nil
	}
	if win.controller != nil {
		C.StopCapture(win.controller)
	}
}

func (w *windowBackend) GetFrame(id int) (*revimg.Frame, error) {
	w.mu.Lock()
	defer w.mu.Unlock()
	win, err := w.getWindow(id)
	if err != nil {
		return nil, err
	}

	cFrame := (*C.Frame)(C.get_window_frame(win.win))
	if cFrame == nil || (cFrame.width == 0 && cFrame.height == 0) {
		return nil, errors.New("failed to get window frame")
	}

	frame := &revimg.Frame{
		Width:  int(C.int(cFrame.width)),
		Height: int(C.int(cFrame.height)),
		X:      int(C.int(cFrame.x)),
		Y:      int(C.int(cFrame.y)),
	}
	C.free(unsafe.Pointer(cFrame))
	return frame, nil
}

func (w *windowBackend) SetFrame(id int, frame revimg.Frame) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	win, err := w.getWindow(id)
	if err != nil {
		return err
	}

	C.set_window_frame(win.win, C.int(frame.Width), C.int(frame.Height), C.int(frame.X), C.int(frame.Y))
	return nil
}

func (w *windowBackend) DisplayFrames() ([]revimg.ScreenFrame, error) {
	var goFrames []revimg.ScreenFrame
	frames := (*C.Frames)(C.get_display_frames())
	if int(C.int(frames.len)) == 0 {
		return nil, errors.New("no displays were detected")
	}
	for i := 0; i < int(C.int(frames.len)); i++ {
		cFrame := (*C.Frame)(unsafe.Pointer(uintptr(unsafe.Pointer(frames.frames)) + (unsafe.Sizeof(C.Frame{}) * uintptr(i))))
		goFrames = append(goFrames, revimg.ScreenFrame{
			Frame: revimg.Frame{
				Width:  int(C.int(cFrame.width)),
				Height: int(C.int(cFrame.height)),
				X:      int(C.int(cFrame.x)),
				Y:      int(C.int(cFrame.y)),
			},
			Scale: float32(C.float(cFrame.scale)),
		})
	}
	C.free(unsafe.Pointer(frames))
	return goFrames, nil
}

func (w *windowBackend) DisplayCount() (int, error) {
	res := (C.int)(C.get_display_count())
	if count := int(res); count == -1 {
		return 0, errors.New("failed to read display information")
	} else {
		return count, nil
	}
}
