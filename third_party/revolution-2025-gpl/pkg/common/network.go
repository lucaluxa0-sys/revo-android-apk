package common

type MessageKind int

const (
	RegistrationMessageKind MessageKind = iota
	AckRegistrationMessageKind
	ConnectedIdentitiesMessageKind
	SetRoleMessageKind
	AckSetRoleMessageKind
	VicDetectMessageKind
	NightDetectMessageKind
	SearchedServerMessageKind
	ShutdownMessageKind
	UnknownMessageKind
)

type ClientRole string

const (
	MainClientRole     = "main"
	SearcherClientRole = "searcher"
	PassiveClientRole  = "passive"
	InactiveClientRole = "inactive"
)

type Message struct {
	Kind     MessageKind
	Sender   string
	Receiver string
	Content  string

	Data []byte `json:"-"`
}

type Network struct {
	Client   NetworkClient
	Relay    NetworkRelay
	Watchers []chan *Message
}

type NetworkClient interface {
	Start()
	Close()
	Subscribe(kind MessageKind) chan *Message
	SubscribeOnce(kind MessageKind) <-chan *Message
	SetRole(ClientRole) error
	Send(receiver string, content interface{})
	Broadcast(content interface{})
	Connect(address string) error
	Disconnect()
	UnsubscribeAll()
}

type NetworkRelay interface {
}
