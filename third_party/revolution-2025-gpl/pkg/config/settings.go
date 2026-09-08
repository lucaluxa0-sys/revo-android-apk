package config

import (
	"github.com/pkg/errors"
)

type WindowAlignment string

const (
	FullScreenWindowAlignment  WindowAlignment = "fullscreen"
	TopLeftWindowAlignment                     = "top-left"
	TopRightWindowAlignment                    = "top-right"
	BottomLeftWindowAlignment                  = "bottom-left"
	BottomRightWindowAlignment                 = "bottom-right"
)

type WindowSize string

const (
	QuarterWindowSize WindowSize = "quarter"
	HalfWindowSize    WindowSize = "half"
	FullWindowSize    WindowSize = "full"
)

type DiscordSettings struct {
	Enabled    bool   `yaml:"enabled"`
	WebhookUrl string `yaml:"webhookUrl,omitempty"`
	PingID     int    `yaml:"pingID,omitempty"`
}

type WindowConfig struct {
	ID        string          `yaml:"id" key:"true" lock:"default"`
	Alignment WindowAlignment `yaml:"alignment" default:"top-left"`
	FullWidth bool            `yaml:"fullWidth" default:"true"`
	Screen    int             `yaml:"screen"`
}

type WindowSettings struct {
	WindowConfigID         string     `yaml:"windowConfigId"`
	WindowSize             WindowSize `yaml:"windowSize" default:"full"`
	PrivateServerLink      string     `yaml:"privateServerLink,omitempty"`
	FallbackToPublicServer bool       `yaml:"fallbackToPublicServer" default:"true"`
}

type PlayerSettings struct {
	MoveSpeed float64 `yaml:"moveSpeed" default:"24"`
}

type PatternSettings struct {
	Overrides      *List[PatternOverride] `yaml:"overrides"`
	Active         *List[Pattern]         `yaml:"active"`
	RetryCount     int                    `yaml:"retryCount" default:"3"`
	AlignmentLevel string                 `yaml:"alignmentLevel" default:"Low"`
}

type MacroSettings struct {
	KeyDelay int `yaml:"keyDelay" default:"50"`
}

// Settings defines the configuration for an individual preset
type Settings struct {
	Name         string                   `yaml:"name" key:"true"`
	LogVerbosity int                      `yaml:"logVerbosity"`
	Discord      *Object[DiscordSettings] `yaml:"discord"`
	Window       *Object[WindowSettings]  `yaml:"window"`
	Player       *Object[PlayerSettings]  `yaml:"player"`
	Patterns     *Object[PatternSettings] `yaml:"patterns"`
	VicHop       *Object[VicHop]          `yaml:"vicHop"`
	Macro        *Object[MacroSettings]   `yaml:"macro"`
}

type Tools struct {
	JellyTool *Object[JellyTool] `yaml:"jellyTool"`
}

type Networking struct {
	AutoConnect bool `yaml:"autoConnect"`
}

type Config struct {
	Presets    *List[Settings]     `yaml:"presets"`
	Windows    *List[WindowConfig] `yaml:"windows"`
	Tools      *Object[Tools]      `yaml:"tools"`
	Networking *Object[Networking] `yaml:"networking"`
	DevMode    bool                `yaml:"devMode"`
}

func NewConfig(runtime *Runtime) (*Object[Config], error) {
	settings := File[Config]{name: "settings", path: "settings.yaml", format: YAML, runtime: runtime}
	if err := settings.load(); err != nil {
		return nil, errors.Wrap(err, "Failed to load macro settings")
	}
	obj := settings.Object()
	if obj.LengthPath("presets") == 0 {
		_ = obj.AppendPath("presets[Default]")
	}
	if obj.LengthPath("windows") == 0 {
		_ = obj.AppendPath("windows[Default]")
	}
	return obj, nil
}
