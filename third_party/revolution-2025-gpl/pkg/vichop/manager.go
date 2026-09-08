package vichop

import (
	"encoding/json"
	"fmt"
	"github.com/nosyliam/revolution/pkg/common"
	. "github.com/nosyliam/revolution/pkg/config"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"github.com/nosyliam/revolution/pkg/logging"
	"github.com/nosyliam/revolution/pkg/movement"
	. "github.com/nosyliam/revolution/pkg/networking"
	"github.com/pkg/errors"
	"io"
	"net/http"
	"sync"
	"sync/atomic"
	"time"
)

type ServerData struct {
	NextPageCursor string `json:"nextPageCursor"`
	Data           []struct {
		ID string `json:"id"`
	} `json:"data"`
}
type Manager struct {
	mu sync.Mutex

	Dataset   *Dataset
	presets   map[string]string
	states    map[string]*Object[MacroState]
	macros    map[string]*common.Macro
	servers   map[string]SearchedServer
	detectors map[*common.Macro]*StatusDetector

	queue chan *VicDetectMessage

	settings *Object[Config]
	state    *Object[State]
	logger   *logging.Logger

	waiters    map[chan *ServerData]bool
	loading    atomic.Bool
	serverData atomic.Pointer[ServerData]
	cursor     string
}

func NewManager(logger *logging.Logger, settings *Object[Config], state *Object[State]) *Manager {
	return &Manager{
		Dataset: NewDataset(state),

		state:    state,
		settings: settings,
		logger:   logger,

		queue:     make(chan *VicDetectMessage, 10),
		waiters:   make(map[chan *ServerData]bool),
		presets:   make(map[string]string),
		states:    make(map[string]*Object[MacroState]),
		macros:    make(map[string]*common.Macro),
		servers:   make(map[string]SearchedServer),
		detectors: make(map[*common.Macro]*StatusDetector),
	}
}

func (m *Manager) HandleRoleChange(account string, role string) {
	if macro, ok := m.macros[account]; ok {
		macro.Network.Client.SetRole(common.ClientRole(role))
	}
}

func (m *Manager) RegisterPreset(preset *Object[Settings]) {
	if err := preset.ListenPath("vicHop.role", func(_ ListenOp, value interface{}) {
		if !preset.Object().VicHop.Object().Enabled {
			return
		}
		for account, activePreset := range m.presets {
			if preset.Object().Name == activePreset {
				m.HandleRoleChange(account, value.(string))
			}
		}
	}); err != nil {
		panic(err)
	}
	if err := preset.ListenPath("vicHop.enabled", func(_ ListenOp, value interface{}) {
		if value.(bool) {
			return
		}
		for account, activePreset := range m.presets {
			if preset.Object().Name == activePreset {
				m.HandleRoleChange(account, common.InactiveClientRole)
			}
		}
	}); err != nil {
		panic(err)
	}
}

func (m *Manager) RegisterState(state *Object[MacroState]) {
	m.mu.Lock()
	m.states[state.Object().AccountName] = state
	m.mu.Unlock()
}

func (m *Manager) UnregisterState(state *Object[MacroState]) {
	m.mu.Lock()
	delete(m.states, state.Object().AccountName)
	m.mu.Unlock()
}

func (m *Manager) Start() {
	m.settings.Object().Presets.ForEachObject(func(value *Object[Settings]) {
		m.RegisterPreset(value)
	})
	m.state.Object().Macros.ForEachObject(func(value *Object[MacroState]) {
		m.RegisterState(value)
	})
	if err := m.settings.ListenPath("presets", func(op ListenOp, value interface{}) {
		if op == Append {
			m.RegisterPreset(value.(*Object[Settings]))
		}
	}); err != nil {
		panic(err)
	}
	if err := m.state.ListenPath("macros", func(op ListenOp, value interface{}) {
		if op == Append {
			m.RegisterState(value.(*Object[MacroState]))
		} else {
			m.UnregisterState(value.(*Object[MacroState]))
		}
	}); err != nil {
		panic(err)
	}
	if err := m.state.ListenPath("config.defaultPreset", func(_ ListenOp, value interface{}) {
		m.presets["Default"] = value.(string)
		role, _ := m.settings.GetPathf("presets[%s].vicHop.role", value.(string))
		m.HandleRoleChange("Default", role.(string))
	}); err != nil {
		panic(err)
	}
}

func (m *Manager) RegisterMacro(macro *common.Macro) error {
	m.macros[macro.MacroState.Object().AccountName] = macro
	if settings := macro.Settings.Object().VicHop.Object(); settings.Enabled {
		if err := macro.Network.Client.SetRole(common.ClientRole(settings.Role)); errors.Is(err, InactiveNetworkError) {
			return errors.New("please connect to a network relay to use Vic Hop")
		} else if err != nil {
			return err
		}
	}

	SubscribeMessage(macro, func(message *SearchedServerMessage) {
		m.mu.Lock()
		defer m.mu.Unlock()
		m.servers[message.Server.ID] = message.Server
		for id, server := range m.servers {
			if time.Now().Sub(server.Time) > time.Minute*20 {
				delete(m.servers, id)
			}
		}
	})

	SubscribeMessage(macro, func(message *VicDetectMessage) {
		// If we're not already killing a vic, redirect now. If we're in the same server that the
		// vic was detected, redirect to the KillVic routine; otherwise, open Roblox and join the instance.
		if !macro.Scratch.ExecutingRoutine("KillVic") {
			if macro.Scratch.Get("game-instance") == message.GameInstance {
				macro.Scratch.Set("vic-field", message.Field)
				macro.Scratch.Set("perform-reset", true)
				if macro.CancelPattern != nil {
					macro.CancelPattern()
				}
				macro.SetRedirect("KillVic")
			} else {
				m.queue <- message
				macro.SetRedirect("OpenRoblox")
			}
		}
	})

	return nil
}

func (m *Manager) ReadQueue(macro *common.Macro) {
	if len(m.queue) == 0 {
		return
	}
	fmt.Println("popping queue")
	server := <-m.queue
	macro.Scratch.Set("vic-field", server.Field)
	macro.Scratch.Set("game-instance", server.GameInstance)
	macro.Scratch.Set("hop-server", true)
}

func (m *Manager) UnregisterMacro(macro *common.Macro) {
	delete(m.detectors, macro)
}

func (m *Manager) HandleDetection(macro *common.Macro, field string) {
	macro.Network.Client.Send(MainReceiver, VicDetectMessage{
		GameInstance: macro.Scratch.Get("game-instance").(string),
		Field:        field,
	})
	if macro.Settings.Object().VicHop.Object().Role == common.SearcherClientRole {
		if err := macro.SetRedirect("OpenRoblox"); err != nil {
			m.logger.Log(0, logging.Error, fmt.Sprintf("Failed to set redirect for searcher: %v", err))
		}
	}
}

func (m *Manager) Detect(macro *common.Macro, field string) (bool, error) {
	root := macro
	if macro.Root != nil {
		root = macro.Root
	}
	image, err := DetectViciousBee(field, m.Dataset, macro.GetWindow().Screenshot(),
		revimg.Point{X: root.MacroState.Object().BaseOriginX, Y: root.MacroState.Object().BaseOriginY})
	if err != nil {
		macro.Logger.LogDiscord(logging.Error, fmt.Sprintf("Failed to detect vicious bee: %v", err), nil, image)
		return false, err
	}
	if image != nil {
		/*f, _ := os.Create("detected.png")
		png.Encode(f, image)
		f.Close()*/
		<-macro.EventBus.KeyDown(macro, common.LShift)
		movement.Sleep(50, macro)
		<-macro.EventBus.KeyUp(macro, common.LShift)
		m.HandleDetection(macro, field)
		return true, nil
	}
	return false, nil
}

func (m *Manager) LoadNewServers() <-chan *ServerData {
	waiter := make(chan *ServerData)
	m.waiters[waiter] = true
	if m.loading.Load() {
		return waiter
	}
	m.loading.Store(true)
	go func() {
		m.mu.Lock()
		defer m.mu.Unlock()
		url := "https://games.roblox.com/v1/games/1537690962/servers/Public?cursor=&sortOrder=Desc&excludeFullGames=true"
		if m.cursor != "" {
			url = fmt.Sprintf("https://games.roblox.com/v1/games/1537690962/servers/Public?cursor=%s&sortOrder=Desc&excludeFullGames=true", m.cursor)
		}
		resp, err := http.Get(url)
		if resp.StatusCode != http.StatusOK {
			m.logger.Log(0, logging.Error, "Failed to load new servers: rate limited")
			<-time.After(5 * time.Second)
			m.LoadNewServers()
			return
		}
		if err != nil {
			m.logger.Log(0, logging.Error, fmt.Sprintf("Failed to load new servers: %v", err))
			<-time.After(5 * time.Second)
			m.LoadNewServers()
		}
		defer resp.Body.Close()

		body, err := io.ReadAll(resp.Body)
		if err != nil {
			m.logger.Log(0, logging.Error, fmt.Sprintf("Failed to load new servers: %v", err))
			<-time.After(5 * time.Second)
			m.LoadNewServers()
		}

		var servers ServerData
		err = json.Unmarshal(body, &servers)
		if err != nil || len(servers.Data) == 0 {
			m.cursor = ""
			m.logger.Log(0, logging.Error, fmt.Sprintf("Failed to load new servers: %v", err))
			<-time.After(5 * time.Second)
			m.LoadNewServers()
		}
		m.cursor = servers.NextPageCursor
		m.loading.Store(false)
		m.serverData.Store(&servers)
		for ch := range m.waiters {
			delete(m.waiters, ch)
			ch <- &servers
		}
	}()
	return waiter
}

func (m *Manager) FindServer(macro *common.Macro) (string, error) {
	data := m.serverData.Load()
	if data == nil {
		data = <-m.LoadNewServers()
	}
	for _, server := range data.Data {
		if _, ok := m.servers[server.ID]; !ok {
			message := SearchedServer{
				Time: time.Now(),
				ID:   server.ID,
			}
			macro.Network.Client.Send(BroadcastReceiver, SearchedServerMessage{Server: message})
			return server.ID, nil
		}
	}

	<-m.LoadNewServers()
	return m.FindServer(macro)
}

func (m *Manager) BattleActive(macro *common.Macro) bool {
	if detector, ok := m.detectors[macro.GetRoot()]; ok {
		return detector.active
	} else {
		return false
	}
}

func (m *Manager) StopBattleDetect(macro *common.Macro) {
	m.mu.Lock()
	delete(m.detectors, macro.GetRoot())
	m.mu.Unlock()
}

func (m *Manager) BattleDetect(macro *common.Macro) {
	m.mu.Lock()
	if _, ok := m.detectors[macro.GetRoot()]; !ok {
		m.detectors[macro.Root] = NewStatusDetector(m, macro.GetRoot())
	}
	m.mu.Unlock()
}

func (m *Manager) Tick(macro *common.Macro) {
	if detector, ok := m.detectors[macro.GetRoot()]; ok {
		detector.Tick()
	}
}
