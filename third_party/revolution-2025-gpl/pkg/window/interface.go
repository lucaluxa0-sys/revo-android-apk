package window

import (
	"fmt"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"github.com/pkg/errors"
	"image"
)

var (
	PermissionDeniedErr = errors.New("accessibility permissions required")
	WindowNotFoundErr   = errors.New("window not found")
)

type JoinOptions struct {
	LinkCode     string
	GameInstance string
	Url          string
}

func (j JoinOptions) String() string {
	var url string
	if j.Url == "" {
		url = fmt.Sprintf("roblox://placeID=1537690962%s", (func() string {
			if j.LinkCode == "" && j.GameInstance == "" {
				return ""
			} else if j.GameInstance != "" {
				return fmt.Sprintf("&gameInstanceId=%s", j.GameInstance)
			} else if j.LinkCode != "" {
				return fmt.Sprintf("&linkCode=%s", j.LinkCode)
			}
			return ""
		})())
	} else {
		url = j.Url
	}
	return url
}

type Backend interface {
	DissociateWindow(int)
	HopServer(options JoinOptions) error
	OpenWindow(options JoinOptions) (int, error)
	CloseWindow(id int) error
	ActivateWindow(id int) error
	SetRobloxLocation(loc string)

	StartCapture(id int) (<-chan *image.RGBA, error)
	StopCapture(id int)
	GetFrame(id int) (*revimg.Frame, error)
	SetFrame(id int, frame revimg.Frame) error
	DisplayFrames() ([]revimg.ScreenFrame, error)
	DisplayCount() (int, error)
}
