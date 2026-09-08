package config

type PatternMetadata struct {
	Position        int
	Length          int
	Width           int
	Distance        int
	RotateDirection int
	RotateCount     int
	InvertFB        bool
	InvertLR        bool

	BackpackPercentage int
	Minutes            int
	ShiftLock          bool
	ReturnMethod       string
	DriftComp          bool
	GatherPattern      bool

	AutoUpdate bool
	Version    int
}

type Pattern struct {
	PatternMetadata
	ID    string `yaml:"id" key:"true"`
	Order int    `yaml:"order"`
}

type PatternOverride struct {
	PatternMetadata
	Name string `yaml:"id" key:"true"`
}
