package config

import (
	"github.com/pkg/errors"
)

type UnwindLoop struct {
	Depth    int
	Continue bool
}

type LoopState struct {
	Unwind *UnwindLoop
	Index  []int
}

type NetworkIdentity struct {
	Address  string `yaml:"address" key:"true"`
	Identity string `yaml:"identity"`
	Role     string `yaml:"role,omitempty"`
}

type MacroNetworkingConfig struct {
	SavedRelays *List[NetworkIdentity] `yaml:"savedRelays"`

	AvailableRelays     *List[NetworkIdentity] `state:"availableRelays" yaml:"-"`
	ConnectedIdentities *List[NetworkIdentity] `state:"connectedIdentities" yaml:"-"`
	ConnectingAddress   string                 `state:"connectingAddress" yaml:"-"`
	ConnectedAddress    string                 `state:"connectedAddress" yaml:"-"`
	RelayStarting       bool                   `state:"relayStarting" yaml:"-"`
	RelayActive         bool                   `state:"relayActive" yaml:"-"`
	RoleRegisterError   string                 `state:"roleRegisterError" yaml:"-"`

	Identity string `state:"identity" yaml:"-"`
}

type VicHopMacroStatistics struct {
}

type MacroCounters struct {
	ClaimedHive int `state:"claimedHive" default:"-1" yaml:"-"`
}

type MacroState struct {
	AccountName string `yaml:"accountName" key:"true"`

	Running bool `state:"running" yaml:"-"`
	Paused  bool `state:"paused" yaml:"-"`

	Status string `state:"status" default:"Ready" yaml:"-"`

	Counters *Object[MacroCounters] `state:"counters" default:"true" yaml:"-"`

	HoneyOriginX int `state:"honeyOriginX" yaml:"-"`
	HoneyOriginY int `state:"honeyOriginY" yaml:"-"`

	BaseOriginX int `state:"baseOriginX" yaml:"-"`
	BaseOriginY int `state:"baseOriginY" yaml:"-"`

	HotbarOriginX int `state:"hotbarOriginX" yaml:"-"`
	HotbarOriginY int `state:"hotbarOriginY" yaml:"-"`

	Networking *Object[MacroNetworkingConfig] `yaml:"networking"`
}

type StateConfig struct {
	CodeStatus    string `state:"codeStatus" default:"pending" yaml:"-"`
	DefaultPreset string `yaml:"defaultPreset" default:"Default"`
	ActiveAccount string `yaml:"activeAccount,omitempty" default:"Default"`
}

type VicHopStatistics struct {
}

type VicHopVersion struct {
	DatasetVersion     string `state:"datasetVersion"`
	DownloadingDataset bool   `state:"downloadingDataset"`
	UpToDate           bool   `state:"upToDate"`
}

type State struct {
	Config *Object[StateConfig] `yaml:"config"`
	Macros *List[MacroState]    `yaml:"macros"`

	VicHop *Object[VicHopVersion] `state:"vicHop" yaml:"-"`
}

func NewState(runtime *Runtime) (*Object[State], error) {
	state := File[State]{name: "state", path: "state.yaml", format: YAML, runtime: runtime}
	if err := state.load(); err != nil {
		return nil, errors.Wrap(err, "Failed to load macro state")
	}
	return state.Object(), nil
}
