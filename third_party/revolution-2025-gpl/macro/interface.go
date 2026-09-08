package macro

import (
	"fmt"
	"github.com/nosyliam/revolution/macro/routines"
	"github.com/nosyliam/revolution/macro/routines/develop"
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/config"
	"github.com/nosyliam/revolution/pkg/control"
	"github.com/nosyliam/revolution/pkg/logging"
	"github.com/nosyliam/revolution/pkg/movement"
	"github.com/nosyliam/revolution/pkg/movement/alignment"
	"github.com/nosyliam/revolution/pkg/networking"
	"github.com/nosyliam/revolution/pkg/vichop"
	"github.com/nosyliam/revolution/pkg/window"
	"github.com/pkg/errors"
	"github.com/sqweek/dialog"
)

type Interface struct {
	EventBus common.EventBus
	Backend  common.Backend
	State    *config.Object[config.MacroState]
	Settings *config.Object[config.Settings]
	Database *config.Object[config.AccountDatabase]
	Pattern  common.PatternLoader
	WinMgr   *window.Manager
	Logger   *logging.Logger
	Macro    *common.Macro
	VicHop   *vichop.Manager
	Account  string

	NetworkClient *networking.Client
	NetworkRelay  *networking.Relay

	pause    chan struct{}
	unpause  chan struct{}
	stop     chan struct{}
	quit     chan struct{}
	redirect chan *common.RedirectExecution

	command chan []string
}

func (i *Interface) Command() chan<- []string {
	return i.command
}

func (i *Interface) ReceiveCommands() {
	for len(i.command) > 0 {
		<-i.command
	}
	for {
		cmd := <-i.command
		if i.Macro == nil || cmd == nil {
			for len(i.command) > 0 {
				<-i.command
			}
			return
		}
		handlers := map[string]func(args ...string){
			"execpattern": func(args ...string) {
				if len(args) != 1 {
					common.Console(logging.Error, "Expected a pattern name!")
					return
				}
				if i.Macro.Window == nil {
					common.Console(logging.Error, "Macro not started!")
					return
				}
				if !i.Macro.Pattern.Exists(args[0]) {
					common.Console(logging.Error, fmt.Sprintf("Pattern \"%s\" does not exist!", args[0]))
					return
				}
				i.Macro.Scratch.Set("PatternToExecute", args[0])
				if err := i.Macro.SetRedirect(develop.ExecuteDevelopmentPatternRoutineKind); err != nil {
					common.Console(logging.Error, err.Error())
					return
				}
				common.Console(logging.Success, "Pattern successfully queued for execution")
				i.Unpause()
			},
			"execroutine": func(args ...string) {
				if len(args) != 1 {
					common.Console(logging.Error, "Expected a routine name!")
					return
				}
				if i.Macro.Window == nil {
					common.Console(logging.Error, "Macro not started!")
					return
				}
				if _, ok := common.Routines[common.RoutineKind(args[0])]; !ok {
					common.Console(logging.Error, fmt.Sprintf("Routine \"%s\" does not exist!", args[0]))
					return
				}
				if err := i.Macro.SetRedirect(common.RoutineKind(args[0])); err != nil {
					common.Console(logging.Error, err.Error())
					return
				}
			},
			"detectvic": func(args ...string) {
				if len(args) != 1 {
					common.Console(logging.Error, "Expected a field name!")
					return
				}
				result, _ := i.Macro.VicHop.Detect(i.Macro, args[0])
				if result {
					common.Console(logging.Error, "Vicious bee detected!")
				} else {
					common.Console(logging.Error, "Vicious bee not detected!")
				}
			},
			"detect": func(args ...string) {
				if len(args) != 1 {
					common.Console(logging.Error, "Expected a detector name!")
					return
				}
				result, err := alignment.Manager.PerformDetection(i.Macro, args[0])
				if err != nil {
					common.Console(logging.Error, fmt.Sprintf("Detection failed: %v", err))
				} else if result {
					common.Console(logging.Success, "Checkpoint detected!")
				} else {
					common.Console(logging.Error, "Checkpoint not detected!")
				}
			},
		}
		go handlers[cmd[0]](cmd[1:]...)
	}
}

func (i *Interface) Start() {
	for len(i.stop) > 0 {
		<-i.stop
	}
	i.redirect = make(chan *common.RedirectExecution, 1)
	pause := make(chan (<-chan struct{}), 1)
	stop := make(chan struct{}, 1)
	err := make(chan string, 1)
	i.Macro = &common.Macro{
		Account:    i.Account,
		EventBus:   i.EventBus,
		Backend:    i.Backend,
		Settings:   i.Settings,
		MacroState: i.State,
		Database:   i.Database,
		Logger:     i.Logger,
		WinManager: i.WinMgr,
		VicHop:     i.VicHop,
		BuffDetect: movement.NewBuffDetector(i.Settings),
		Pattern:    i.Pattern,
		Scratch:    config.NewScratch(),
		Results:    &common.ActionResults{},
		Pause:      pause,
		Error:      err,
		Stop:       i.stop,
		Redirect:   i.redirect,
	}
	i.Macro.Network = &common.Network{
		Client: i.NetworkClient,
		Relay:  i.NetworkRelay,
	}
	i.Macro.Input = movement.NewInputManager(i.Macro)
	i.Macro.Scheduler = NewScheduler(i.redirect, i.stop)

	i.State.SetPath("running", true)
	i.State.SetPath("counters.claimedHive", -1)
	if err := i.VicHop.RegisterMacro(i.Macro); err != nil {
		i.Macro = nil
		i.State.SetPath("running", false)
		i.State.SetPath("status", "Ready")
		dialog.Message(errors.Wrap(err, "Failed to register with Vic Hop").Error()).Error()
		return
	}

	status := make(chan string)

	go func() {
		for {
			select {
			case stat := <-status:
				_ = i.State.SetPath("status", stat)
			case errStr := <-err:
				i.SendError(errStr)
				i.Pause()
			case <-i.pause:
				i.Macro.Lock()
				if i.unpause != nil {
					_ = i.State.SetPath("paused", false)
					if i.Macro.Window != nil {
						go i.Macro.Scheduler.Start()
					}
					if len(i.unpause) > 0 {
						<-i.unpause
					}
					i.unpause <- struct{}{}
					i.unpause = nil
					for _, watcher := range i.Macro.UnpauseWatchers {
						watcher <- struct{}{}
					}
					i.Macro.UnpauseWatchers = nil
					i.Macro.Unlock()
					continue
				}
				_ = i.State.SetPath("paused", true)
				i.Macro.Scheduler.Close()
				i.unpause = make(chan struct{}, 1)
				if len(pause) == 0 {
					pause <- i.unpause
				}
				for _, watcher := range i.Macro.Watchers {
					ch := make(chan struct{}, 1)
					i.Macro.UnpauseWatchers = append(i.Macro.UnpauseWatchers, ch)
					if len(watcher) == 0 {
						watcher <- ch
					}
				}
				i.Macro.Unlock()
			case <-i.stop:
				i.Macro.Lock()
				if i.Macro.Window != nil {
					i.Macro.Window.Dissociate()
				}
				for _, watcher := range i.Macro.UnpauseWatchers {
					if len(watcher) == 0 {
						watcher <- struct{}{}
					}
				}
				for _, watcher := range i.Macro.Watchers {
					if len(watcher) == 0 {
						watcher <- nil
					}
				}
				if len(stop) == 0 {
					stop <- struct{}{}
				}
				i.NetworkClient.UnsubscribeAll()
				i.NetworkClient.SetRole(common.InactiveClientRole)
				i.VicHop.UnregisterMacro(i.Macro)
				i.Macro.Scheduler.Close()
				i.command <- nil
				i.Macro.Unlock()
				i.Macro = nil
				_ = i.State.SetPath("running", false)
				_ = i.State.SetPath("status", "Ready")
				return
			}
		}
	}()

	go i.ReceiveCommands()

	main := common.Routines[routines.MainRoutineKind]
	go control.ExecuteRoutine(i.Macro, main, status, err)
}

func (i *Interface) SendError(err string) {
	dialog.Message(err).Error()
}

func (i *Interface) Stop() {
	if i.unpause != nil {
		i.unpause <- struct{}{}
		i.unpause = nil
		_ = i.State.SetPath("paused", false)
	}
	if len(i.stop) != 0 {
		return
	}
	i.stop <- struct{}{}
}

func (i *Interface) Pause() {
	if len(i.pause) != 0 {
		return
	}
	i.pause <- struct{}{}
}

func (i *Interface) Unpause() {
	if i.unpause == nil || len(i.unpause) != 0 {
		return
	}
	i.pause <- struct{}{}
}

func NewInterface(
	account string,
	settings *config.Object[config.Settings],
	state *config.Object[config.MacroState],
	database *config.Object[config.AccountDatabase],
	pattern common.PatternLoader,
	winMgr *window.Manager,
	vicHop *vichop.Manager,
	eventBus common.EventBus,
	backend common.Backend,
) *Interface {
	ifc := &Interface{
		EventBus: eventBus,
		Backend:  backend,
		Settings: settings,
		Database: database,
		Pattern:  pattern,
		Logger:   logging.NewLogger(account, settings),
		State:    state,
		WinMgr:   winMgr,
		VicHop:   vicHop,
		Account:  account,

		pause:   make(chan struct{}, 1),
		stop:    make(chan struct{}, 1),
		command: make(chan []string, 100),
	}
	ifc.NetworkClient = networking.NewClient(state, ifc.Logger)
	ifc.NetworkRelay = networking.NewRelay(ifc.NetworkClient, state, ifc.Logger)
	go ifc.NetworkClient.Start()
	return ifc
}
