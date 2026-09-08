package common

import (
	"context"
	"fmt"
	"github.com/nosyliam/revolution/pkg/config"
	"github.com/nosyliam/revolution/pkg/logging"
	"github.com/nosyliam/revolution/pkg/window"
	"github.com/pkg/errors"
	"sync"
)

var (
	RestartSignal   = errors.New("restart")   // Restarts the routine
	TerminateSignal = errors.New("terminate") // Terminates the routine
	RetrySignal     = errors.New("retry")     // Retry the current action
	StepBackSignal  = errors.New("step back") // Step back to the last action

)

func Console(level logging.LogLevel, text string) {
	logging.Console(config.AppContext, level, text)
}

type RedirectExecution struct {
	Routine RoutineKind
}

func (e RedirectExecution) Error() string {
	return fmt.Sprintf("redirect to %s", e.Routine)
}

type (
	RoutineKind        string
	RoutineExecutor    func(kind RoutineKind)
	SubroutineExecutor func(actions []Action)
)

type Macro struct {
	sync.Mutex

	Root *Macro

	CancelPattern context.CancelFunc

	Account    string
	EventBus   EventBus
	Input      InputManager
	Backend    Backend
	Scheduler  Scheduler
	Results    *ActionResults
	State      *config.Object[config.State]
	MacroState *config.Object[config.MacroState]
	Settings   *config.Object[config.Settings]
	Database   *config.Object[config.AccountDatabase]
	Network    *Network
	VicHop     VicHop
	BuffDetect BuffDetector
	Pattern    PatternLoader
	Logger     *logging.Logger
	Window     *window.Window
	WinManager *window.Manager
	Scratch    *config.Scratch

	Routine    RoutineExecutor
	Subroutine SubroutineExecutor
	Action     func(Action) error
	Status     func(string)
	Pause      <-chan (<-chan struct{})
	Stop       chan struct{}
	Error      chan string
	Redirect   chan *RedirectExecution

	Watchers        []chan (<-chan struct{})
	UnpauseWatchers []chan<- struct{}
}

// Watch returns channel which outputs a channel or a nil value whenever the macro is paused or stopped.
// If a new channel is received, it indicates that the macro is paused and that the channel should be used to wait for unpause.
// This function must be used in asynchronous operations that are executed outside the routine loop.
func (m *Macro) Watch() <-chan (<-chan struct{}) {
	if m.Root != nil {
		return m.Root.Watch()
	}
	m.Lock()
	defer m.Unlock()
	ch := make(chan (<-chan struct{}), 1)
	m.Watchers = append(m.Watchers, ch)
	return ch
}

func (m *Macro) Unwatch(ch <-chan (<-chan struct{})) {
	if m.Root != nil {
		m.Root.Unwatch(ch)
		return
	}
	m.Lock()
	defer m.Unlock()
	for i, c := range m.Watchers {
		if c == ch {
			m.Watchers = append(m.Watchers[:i], m.Watchers[i+1:]...)
			return
		}
	}
}

func (m *Macro) SetRedirect(routine RoutineKind) error {
	if m.Root != nil {
		return m.Root.SetRedirect(routine)
	}
	m.Lock()
	defer m.Unlock()
	for _, watcher := range m.UnpauseWatchers {
		watcher <- struct{}{}
	}
	m.UnpauseWatchers = nil
	for _, watcher := range m.Watchers {
		if len(watcher) == 0 {
			watcher <- nil
		}
	}
	if len(m.Redirect) == 0 {
		m.Redirect <- &RedirectExecution{routine}
		return nil
	} else {
		return errors.New("A redirect operation is already taking place!")
	}
}

func (m *Macro) SetError(err error, context string) {
	m.Status(context)
	m.Error <- errors.Wrap(err, context).Error()
}

func (m *Macro) GetWindow() *window.Window {
	if m.Root != nil {
		return m.Root.GetWindow()
	}
	return m.Window
}

func (m *Macro) GetRoot() *Macro {
	if m.Root == nil {
		return m
	}
	return m.Root.GetRoot()
}

func (m *Macro) Copy() *Macro {
	var root = m
	if m.Root != nil {
		root = m.Root
	}
	return &Macro{
		Root:       root,
		Account:    m.Account,
		EventBus:   m.EventBus,
		Input:      m.Input,
		Backend:    m.Backend,
		Scheduler:  m.Scheduler,
		Settings:   m.Settings,
		State:      m.State,
		MacroState: m.MacroState,
		Database:   m.Database,
		VicHop:     m.VicHop,
		Network:    m.Network,
		BuffDetect: m.BuffDetect,
		Pattern:    m.Pattern,
		Window:     m.Window,
		WinManager: m.WinManager,
		Scratch:    m.Scratch,
		Subroutine: m.Subroutine,
		Logger:     m.Logger,
		Pause:      m.Pause,
		Stop:       m.Stop,
		Redirect:   m.Redirect,
	}
}
