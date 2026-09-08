package networking

import (
	"encoding/json"
	"fmt"
	. "github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/config"
	"time"
)

type MessageKindEnumerator []MessageKind

var MessageKinds = MessageKindEnumerator{
	RegistrationMessageKind,
	AckRegistrationMessageKind,
	ConnectedIdentitiesMessageKind,
	AckSetRoleMessageKind,
	SetRoleMessageKind,
	VicDetectMessageKind,
	NightDetectMessageKind,
	SearchedServerMessageKind,
	ShutdownMessageKind,
}

func (m *MessageKindEnumerator) Determine(data interface{}) MessageKind {
	switch data.(type) {
	case RegistrationMessage:
		return RegistrationMessageKind
	case AckRegistrationMessage:
		return AckRegistrationMessageKind
	case ConnectedIdentitiesMessage:
		return ConnectedIdentitiesMessageKind
	case SetRoleMessage:
		return SetRoleMessageKind
	case AckSetRoleMessage:
		return AckSetRoleMessageKind
	case VicDetectMessage:
		return VicDetectMessageKind
	case SearchedServerMessage:
		return SearchedServerMessageKind
	case NightDetectMessage:
		return NightDetectMessageKind
	}
	return UnknownMessageKind
}

type RegistrationMessage struct {
	Identity string
}

type AckRegistrationMessage struct {
	Error string
}

type ConnectedIdentitiesMessage struct {
	Identities []config.NetworkIdentity
}

type SetRoleMessage struct {
	Role ClientRole
}

type AckSetRoleMessage struct {
	Error string
}

type VicDetectMessage struct {
	GameInstance string
	Field        string
	Time         time.Time
}

type NightDetectMessage struct {
	AccessCode string
}

type SearchedServer struct {
	Time time.Time
	ID   string
}

type SearchedServerMessage struct {
	Server SearchedServer
}

type EmptyMessage struct{}

type ShutdownMessage EmptyMessage

func SubscribeMessage[T any](macro *Macro, callback func(message *T)) {
	var t T
	kind := MessageKinds.Determine(t)
	watcher := macro.Network.Client.Subscribe(kind)
	macro.Network.Watchers = append(macro.Network.Watchers, watcher)
	go func() {
		for {
			message, ok := <-watcher
			if message == nil || !ok {
				return
			}
			var msg T
			if err := json.Unmarshal([]byte(message.Content), &msg); err != nil {
				macro.Error <- fmt.Sprintf("Unable to decode message from %s: %v", message.Sender, err)
				continue
			}
			callback(&msg)
		}
	}()
}
