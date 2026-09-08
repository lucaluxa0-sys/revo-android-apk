//go:build windows
// +build windows

package platform

// #include "window.h"
// #include "capture_windows/CaptureBridge.h"
//
//extern void GoFrameCallback(int id, unsigned char* data, size_t length, int width, int height, int stride);
//extern void GoErrorCallback(int id, char* error);
//
//static inline FrameCallback getFrameCallbackPtr() {
//    return (FrameCallback)GoFrameCallback;
//}
//static inline ErrorCallback getErrorCallbackPtr() {
//    return (ErrorCallback)GoErrorCallback;
//}
import "C"

import (
	"encoding/json"
	"fmt"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"github.com/nosyliam/revolution/pkg/window"
	"github.com/pkg/browser"
	"github.com/pkg/errors"
	ps "github.com/shirou/gopsutil/v4/process"
	"github.com/sqweek/dialog"
	"image"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
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
	mu      sync.Mutex
	windows map[int]*windowData
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
	C.free(unsafe.Pointer(win.win))
	w.mu.Unlock()
}

func (w *windowBackend) getWindow(id int) (*windowData, error) {
	win, ok := w.windows[id]
	if !ok {
		return nil, window.WindowNotFoundErr
	}

	exists, err := ps.PidExists(int32(id))
	if !exists || err != nil {
		w.freeWindow(id)
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

func (w *windowBackend) getRobloxRoot() string {
	return filepath.Join(os.Getenv("LOCALAPPDATA"), "Roblox", "Versions")
}

func (w *windowBackend) getRobloxVersion() (string, error) {
	entries, err := os.ReadDir(w.getRobloxRoot())
	if err != nil {
		panic(err)
	}

	var instances = make(map[string]time.Time)
	for _, entry := range entries {
		if entry.IsDir() {
			exePath := filepath.Join(w.getRobloxRoot(), entry.Name(), "RobloxPlayerBeta.exe")
			if info, err := os.Stat(exePath); err == nil {
				instances[entry.Name()] = info.ModTime()
			} else if !os.IsNotExist(err) {
				return "", err
			}
		}
	}

	if len(instances) == 0 {
		return "", errors.New("no Roblox versions found")
	}

	var mostRecent time.Time
	var mostRecentKey string

	for key, t := range instances {
		if mostRecent.IsZero() || t.After(mostRecent) {
			mostRecent = t
			mostRecentKey = key
		}
	}

	return mostRecentKey, nil
}

func (w *windowBackend) HopServer(options window.JoinOptions) error {
	processes, err := ps.Processes()
	if err != nil {
		fmt.Println("proc err", err)
		return errors.Wrap(err, "failed to list processes")
	}
	for _, p := range processes {
		n, err := p.Name()
		if err != nil {
			continue
		}
		if pid := int(p.Pid); n == "RobloxPlayerBeta.exe" {
			if int((C.int)(C.get_window_visible_count(C.int(pid)))) == 0 {
				fmt.Println("found ghost process", pid)
				p.Kill()
			}
		}
	}
	fmt.Println("opening", options.String())
	err = browser.OpenURL(options.String())
	if err != nil {
		return errors.Wrap(err, "failed to open roblox")
	}
	return nil
}

func (w *windowBackend) OpenWindow(options window.JoinOptions) (int, error) {
	w.mu.Lock()
	defer w.mu.Unlock()
	// Attempt to bind non-macro roblox instances first
	findRunningInstance := func(initialize bool) (int, error) {
		processes, err := ps.Processes()
		if err != nil {
			return 0, errors.Wrap(err, "failed to list processes")
		}
		for _, p := range processes {
			n, err := p.Name()
			if err != nil {
				continue
			}
			if pid := int(p.Pid); n == "RobloxPlayerBeta.exe" {
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

	if pid, err := findRunningInstance(true); err != nil {
		return 0, err
	} else if pid != -1 {
		return pid, nil
	}

	version, err := w.getRobloxVersion()
	if err != nil {
		return 0, errors.Wrap(err, "failed to get current Roblox version")
	}

	vResp, err := http.Get("https://clientsettingscdn.roblox.com/v2/client-version/WindowsPlayer")
	if err != nil {
		return 0, errors.Wrap(err, "failed to fetch latest Roblox version")
	}

	data, _ := io.ReadAll(vResp.Body)
	fmt.Println(string(data))

	dataMap := make(map[string]interface{})
	err = json.Unmarshal(data, &dataMap)
	if err != nil {
		return 0, errors.Wrap(err, "failed to unmarshal latest Roblox version")
	}

	if dataMap["clientVersionUpload"].(string) != version {
		var pid = -1
		cmd := exec.Command(filepath.Join(w.getRobloxRoot(), version, "RobloxPlayerInstaller.exe"))
		err = cmd.Start()
		if err != nil {
			fmt.Println(err)
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
			if int((C.int)(C.get_window_visible_count(C.int(pid)))) == 1 {
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
		err = browser.OpenURL(options.String())
		fmt.Println("starting roblox")
		if err != nil {
			return 0, errors.New("failed to open roblox")
		}

		var pid = 0
		for j := 0; j < 500; j++ {
			if pid, err = findRunningInstance(true); err != nil {
				return 0, err
			} else if pid != -1 {
				return pid, nil
			}
			<-time.After(10 * time.Millisecond)
		}

		if pid == -1 {
			return 0, errors.New("failed to find roblox process")
		}

		<-time.After(1 * time.Second)
	}

	return 0, errors.New("failed to initialize roblox process")
}

//export GoFrameCallback
func GoFrameCallback(id C.int, data *C.uchar, length C.size_t, width, height, stride C.int) {
	buf := C.GoBytes(unsafe.Pointer(data), C.int(length))

	img := &image.RGBA{}
	img.Rect = image.Rect(0, 0, int(width), int(height))
	img.Pix = buf
	img.Stride = int(stride)

	/*f, _ := os.Create("test.png")
	png.Encode(f, img)
	f.Close()*/

	if win, ok := singleton.windows[int(id)]; ok {
		win.mu.Lock()
		if win.output != nil && len(win.output) == 0 {
			win.output <- img
		}
		win.mu.Unlock()
	}
}

//export GoErrorCallback
func GoErrorCallback(id C.int, data *C.char) {
	err := C.GoString(data)
	dialog.Message(fmt.Sprintf("Received capture error for window ID %d: %v\n", int(id), err)).Error()
}

func (w *windowBackend) StartCapture(id int) (<-chan *image.RGBA, error) {
	w.mu.Lock()
	defer w.mu.Unlock()
	win, err := w.getWindow(id)
	if err != nil {
		return nil, err
	}

	frameCbPtr := C.getFrameCallbackPtr()
	errorCbPtr := C.getErrorCallbackPtr()
	controller := C.CreateCaptureController(C.int(id), win.win.hwnd, frameCbPtr, errorCbPtr)
	if controller == nil {
		return nil, errors.New("failed to create capture controller")
	}

	output := make(chan *image.RGBA, 60)
	win.output = output

	C.StartCaptureController(controller)

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
	if win.output != nil {
		close(win.output)
		win.output = nil
	}
	win.mu.Unlock()
	if win.controller != nil {
		C.StopCaptureController(win.controller)
		C.DestroyCaptureController(win.controller)
		win.controller = nil
	}
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

func (w *windowBackend) SetRobloxLocation(loc string) {}
