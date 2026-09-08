package window

import (
	"fmt"
	. "github.com/nosyliam/revolution/pkg/config"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"github.com/pkg/errors"
	"github.com/sqweek/dialog"
	"image"
	"runtime"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

type Window struct {
	id         int
	config     *WindowConfig
	backend    Backend
	screenshot atomic.Pointer[image.RGBA]
	capturing  atomic.Bool
	output     chan *image.RGBA
	loaded     bool
	mgr        *Manager
	err        error
}

func (w *Window) Activate() error {
	if err := w.backend.ActivateWindow(w.id); err != nil {
		w.err = err
	}
	return w.err
}

func (w *Window) PID() int {
	return w.id
}

func (w *Window) Dissociate() {
	w.backend.DissociateWindow(w.id)
}

func (w *Window) Fix() error {
	if err := w.mgr.adjustDisplays(); err != nil {
		return errors.Wrap(err, "failed to adjust displays")
	}
	if w.err != nil {
		return w.err
	}

	frame, err := w.backend.GetFrame(w.id)
	if errors.Is(err, WindowNotFoundErr) {
		w.mgr.freeWindow(w.config.ID)
		return err
	} else if err != nil {
		return errors.Wrap(err, "failed to get window frame")
	}

	if correct := w.mgr.windowFrames[w.config.ID]; !frame.Equals(correct) {
		if err = w.backend.SetFrame(w.id, correct); err != nil {
			return errors.Wrap(err, "failed to set window frame")
		}
	}

	return nil
}

func (w *Window) Output() <-chan *image.RGBA {
	output := make(chan *image.RGBA, 60)
	w.output = output
	return output
}

func (w *Window) CloseOutput() {
	if w.output != nil {
		ch := w.output
		w.output = nil
		close(ch)
	}
}

func (w *Window) Screenshot() *image.RGBA {
	return w.screenshot.Load()
}

func (w *Window) HopServer(instance string) error {
	return w.backend.HopServer(JoinOptions{GameInstance: instance})
}

func (w *Window) StartCapture() error {
	input, err := w.backend.StartCapture(w.id)
	if err != nil {
		return err
	}
	// Wait for the first image
	select {
	case img := <-input:
		w.screenshot.Store(img)
	case <-time.After(10 * time.Second):
		return errors.New("timeout exceeded waiting for first frame")
	}
	w.capturing.Store(true)
	go func() {
		for {
			select {
			case img, ok := <-input:
				if !ok {
					w.capturing.Store(false)
					w.output <- nil
					return
				}
				w.screenshot.Store(img)
				if w.output != nil {
					if len(w.output) > 30 {
						fmt.Printf("WARNING: Scheduler frame output buffer is %d frames behind!\n", len(w.output))
					}
					if len(w.output) == 60 {
						fmt.Println("WARNING: Scheduler frame buffer full, skipping frames")
						for len(w.output) > 0 {
							<-w.output
						}
					} else {
						w.output <- img
					}
				}
				if img == nil {
					w.capturing.Store(false)
					return
				}
			case <-time.After(5 * time.Second):
				if w.output != nil {
					for len(w.output) > 0 {
						<-w.output
					}
				}
				w.capturing.Store(false)
				w.output <- nil
				dialog.Message("The screen capture mechanism has timed out.").Error()
				return
			}
		}
	}()
	return nil
}

func (w *Window) Capturing() bool {
	return w.capturing.Load()
}

func (w *Window) Close() error {
	if w.Capturing() {
		w.backend.StartCapture(w.id)
		w.capturing.Store(false)
	}
	if err := w.backend.CloseWindow(w.id); err != nil {
		return errors.Wrap(err, "failed to close window")
	}
	w.mgr.freeWindow(w.config.ID)
	return nil
}

type windowArray [4]*string

func (a windowArray) Available(spots ...int) bool {
	for _, spot := range spots {
		if a[spot] != nil {
			return false
		}
	}
	return true
}

type Manager struct {
	sync.Mutex
	backend         Backend
	reservedWindows []windowArray
	reservedIds     map[string]*Window
	windowFrames    map[string]revimg.Frame
	displayCount    int
	frames          []revimg.ScreenFrame
}

func (m *Manager) minimumSize() revimg.Frame {
	if runtime.GOOS == "darwin" {
		return revimg.Frame{Width: 800, Height: 628}
	} else {
		return revimg.Frame{Width: 0, Height: 0}
	}
}

func (m *Manager) freeWindow(id string) {
	m.Lock()
	defer m.Unlock()
	if _, ok := m.reservedIds[id]; !ok {
		return
	}
	for _, screen := range m.reservedWindows {
		for i, win := range screen {
			if win != nil {
				if *win == id {
					screen[i] = nil
				}
			}
		}
	}
	delete(m.reservedIds, id)
	delete(m.windowFrames, id)
}

func (m *Manager) adjustDisplays() error {
	m.Lock()
	defer m.Unlock()
	if count, err := m.backend.DisplayCount(); err != nil {
		return errors.Wrap(err, "failed to read display count")
	} else {
		m.displayCount = count
	}
	if len(m.reservedWindows) > m.displayCount {
		for i := len(m.reservedWindows); i > m.displayCount; i-- {
			for _, id := range m.reservedWindows[i-1] {
				if id != nil {
					if window, ok := m.reservedIds[*id]; ok {
						if err := window.Close(); err != nil {
							return errors.Wrap(err, "failed to close window")
						}
						window.err = errors.New("The display for this window has been disconnected")
					}
				}
			}
		}
		m.reservedWindows = m.reservedWindows[:m.displayCount]
	} else if len(m.reservedWindows) < m.displayCount {
		for len(m.reservedWindows) != m.displayCount {
			m.reservedWindows = append(m.reservedWindows, [4]*string{})
		}
	}
	return nil
}

func (m *Manager) windowFrame(id string) revimg.Frame {
	return m.windowFrames[id]
}

func (m *Manager) getScreens() ([]revimg.ScreenFrame, error) {
	var adjustedScreens []revimg.ScreenFrame
	screens, err := m.backend.DisplayFrames()
	if err != nil {
		return nil, errors.Wrap(err, "failed to get screen data")
	}
	if runtime.GOOS == "darwin" {
		for _, screen := range screens {
			adjustedScreens = append(adjustedScreens, revimg.ScreenFrame{
				Frame: revimg.Frame{Width: screen.Width, Height: screen.Height - 38},
				Scale: screen.Scale,
			})
		}
	} else {
		adjustedScreens = screens
	}

	return adjustedScreens, nil
}

func (m *Manager) reserveWindow(settings *WindowConfig, sz WindowSize) (*WindowConfig, error) {
	m.Lock()
	defer m.Unlock()

	screens, err := m.getScreens()
	if err != nil {
		return nil, err
	}

	// If there's no window configuration associated with the macro instance, attempt to find an available spot
	if settings == nil {
		retinaFound := false
		if sz == "" {
			sz = FullWindowSize
		}
		for i, screen := range m.reservedWindows {
			if screens[i].Scale > 1 {
				retinaFound = true
				continue
			}

			switch {
			case screen.Available(0, 1, 2, 3) && sz == FullWindowSize:
				settings = &WindowConfig{Screen: i, Alignment: FullScreenWindowAlignment}
			case screen.Available(0, 1) && sz == HalfWindowSize:
				settings = &WindowConfig{Screen: i, Alignment: TopLeftWindowAlignment, FullWidth: true}
			case screen.Available(2, 3) && sz == HalfWindowSize:
				settings = &WindowConfig{Screen: i, Alignment: BottomLeftWindowAlignment, FullWidth: true}
			case screen.Available(0):
				settings = &WindowConfig{Screen: i, Alignment: TopLeftWindowAlignment}
			case screen.Available(1):
				settings = &WindowConfig{Screen: i, Alignment: TopRightWindowAlignment}
			case screen.Available(2):
				settings = &WindowConfig{Screen: i, Alignment: BottomLeftWindowAlignment}
			case screen.Available(3):
				settings = &WindowConfig{Screen: i, Alignment: BottomRightWindowAlignment}
			}
			if settings != nil {
				break
			}
		}
		if settings == nil {
			if retinaFound {
				return nil, errors.New("A non-retina display could not be found. Attach a monitor or install DeskPad to add a virtual monitor.")
			} else {
				return nil, errors.New("No displays available for the macro window")
			}
		}
	}

	if len(screens) < settings.Screen {
		return nil, errors.New(fmt.Sprintf("The configuration for this window exists on screen %d. Only %d screen(s) are available.",
			settings.Screen, len(screens)))
	}
	m.frames = screens

	screen := screens[settings.Screen]
	if screen.Scale > 1 {
		return nil, errors.New(fmt.Sprintf("Retina displays are not supported. Attach a monitor or install DeskPad to add a virtual monitor."))
	}

	if len(screens) > len(m.reservedWindows) {
		for i := len(m.reservedWindows); i < len(screens); i++ {
			m.reservedWindows = append(m.reservedWindows, [4]*string{})
		}
	}
	reservations := m.reservedWindows[settings.Screen]
	id := settings.ID

	// Validate and reserve the position/size
	switch settings.Alignment {
	case FullScreenWindowAlignment:
		if reservations[0] != nil {
			return nil, errors.New(fmt.Sprintf("The top left corner of screen %d is reserved.", settings.Screen))
		}
		if reservations[1] != nil {
			return nil, errors.New(fmt.Sprintf("The top right corner of screen %d is reserved.", settings.Screen))
		}
		if reservations[2] != nil {
			return nil, errors.New(fmt.Sprintf("The bottom left corner of screen %d is reserved.", settings.Screen))
		}
		if reservations[3] != nil {
			return nil, errors.New(fmt.Sprintf("The bottom right corner of screen %d is reserved.", settings.Screen))
		}
	case TopLeftWindowAlignment:
		if reservations[0] != nil {
			return nil, errors.New(fmt.Sprintf("The top left corner of screen %d is reserved.", settings.Screen))
		}
		if settings.FullWidth && reservations[1] != nil {
			return nil, errors.New(fmt.Sprintf("The top right corner of screen %d is reserved.", settings.Screen))
		} else {
			reservations[1] = &id
		}
		reservations[0] = &id
	case TopRightWindowAlignment:
		if reservations[1] != nil {
			return nil, errors.New(fmt.Sprintf("The top right corner of screen %d is reserved.", settings.Screen))
		}
		if settings.FullWidth && reservations[0] != nil {
			return nil, errors.New(fmt.Sprintf("The top left corner of screen %d is reserved.", settings.Screen))
		} else {
			reservations[0] = &id
		}
		reservations[1] = &id
	case BottomLeftWindowAlignment:
		if reservations[2] != nil {
			return nil, errors.New(fmt.Sprintf("The bottom left corner of screen %d is reserved.", settings.Screen))
		}
		if settings.FullWidth && reservations[3] != nil {
			return nil, errors.New(fmt.Sprintf("The bottom right corner of screen %d is reserved.", settings.Screen))
		} else {
			reservations[3] = &id
		}
		reservations[2] = &id
	case BottomRightWindowAlignment:
		if reservations[3] != nil {
			return nil, errors.New(fmt.Sprintf("The bottom right corner of screen %d is reserved.", settings.Screen))
		}
		if settings.FullWidth && reservations[2] != nil {
			return nil, errors.New(fmt.Sprintf("The bottom left corner of screen %d is reserved.", settings.Screen))
		} else {
			reservations[2] = &id
		}
		reservations[3] = &id
	}

	// Compute the frame of the window
	x := 0
	for i := 0; i < settings.Screen; i++ {
		x += screens[i].Width
	}
	y := 0
	w := screen.Width
	h := screen.Height
	if settings.Alignment != FullScreenWindowAlignment {
		h = screen.Height / 2
		if !settings.FullWidth {
			w = screen.Width / 2
		}
	}
	if settings.Alignment == BottomLeftWindowAlignment || settings.Alignment == BottomRightWindowAlignment {
		y = screen.Height / 2
	}
	if (settings.Alignment == TopRightWindowAlignment || settings.Alignment == BottomRightWindowAlignment) && settings.FullWidth == false {
		x += screen.Width / 2
	}

	minSize := m.minimumSize()
	if w < minSize.Width || h < minSize.Height {
		return nil, errors.New("There is not enough space for the window configuration. Please increase your resolution or add another display.")
	}
	m.windowFrames[settings.ID] = revimg.Frame{X: x, Y: y, Width: w, Height: h}
	return settings, nil
}

func (m *Manager) OpenWindow(accountName string, db Reactive, settings *Object[Settings], ignoreLink bool) (*Window, error) {
	var joinOptions = JoinOptions{}
	var windowConfig *WindowConfig
	if accountName != "Default" {
		account := Concrete[Account](db, "accounts[%s]", accountName)
		if account == nil {
			return nil, errors.New(fmt.Sprintf("Account %s not found", accountName))
		}
		if url, err := account.GenerateJoinUrl(ignoreLink); err != nil {
			return nil, errors.Wrap(err, "Failed to generate join url")
		} else {
			joinOptions = JoinOptions{Url: url}
		}
		if account.WindowConfigID != "" {
			windowConfig = Concrete[WindowConfig](settings, "windows[%s]", account.WindowConfigID)
			if windowConfig == nil {
				return nil, errors.New(fmt.Sprintf("Window configuration %s does not exist", account.WindowConfigID))
			}
		}
	} else {
		if privateLink := Concrete[string](settings, "window.privateServerLink"); *privateLink != "" && !ignoreLink {
			parts := strings.Split(*privateLink, "=")
			if len(parts) != 2 {
				return nil, errors.New("Invalid private server link format")
			}
			joinOptions = JoinOptions{LinkCode: parts[1]}
		}
	}
	if windowConfig == nil {
		if id := Concrete[string](settings, "window.windowConfigId"); *id != "" && *id != "default" {
			if windowConfigValue, err := settings.GetPathf("windows[%s]", *id); err != nil {
				return nil, errors.New(fmt.Sprintf("Window configuration %s does not exist", *id))
			} else {
				windowConfig = windowConfigValue.(*WindowConfig)
			}
		}
	}
	if windowConfig != nil {
		if _, ok := m.reservedIds[windowConfig.ID]; ok {
			return nil, errors.New(fmt.Sprintf("Window config ID \"%s\" is already in use", windowConfig.ID))
		}
	}
	var err error
	if err = m.adjustDisplays(); err != nil {
		return nil, errors.Wrap(err, "failed to adjust displays")
	}
	windowConfig, err = m.reserveWindow(windowConfig, *Concrete[WindowSize](settings, "window.windowSize"))
	if err != nil {
		dialog.Message(err.Error()).Error()
		return nil, errors.Wrap(err, "Failed to reserve window")
	}
	id, err := m.backend.OpenWindow(joinOptions)
	fmt.Println(err)
	if err != nil {
		return nil, errors.Wrap(err, "Failed to open window")
	}

	win := &Window{
		id:      id,
		config:  windowConfig,
		backend: m.backend,
		mgr:     m,
	}
	m.reservedIds[windowConfig.ID] = win
	return win, nil
}

func NewWindowManager(backend Backend) *Manager {
	return &Manager{
		backend:      backend,
		windowFrames: make(map[string]revimg.Frame),
		reservedIds:  make(map[string]*Window),
	}
}
