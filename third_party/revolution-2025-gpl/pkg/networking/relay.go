package networking

import (
	"bufio"
	"encoding/json"
	"fmt"
	"github.com/grandcat/zeroconf"
	. "github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/config"
	"github.com/nosyliam/revolution/pkg/logging"
	"github.com/pkg/errors"
	"net"
	"net/url"
	"strings"
	"sync"
	"time"
)

const BroadcastReceiver = "!BROADCAST"
const RelayReceiver = "!RELAY"
const MainReceiver = "!main"

type Relay struct {
	mu         sync.Mutex
	client     *Client
	server     *zeroconf.Server
	listener   net.Listener
	port       int
	identities map[string]net.Conn
	roles      map[string]ClientRole
	banned     map[string]bool
	state      *config.Object[config.MacroState]
	logger     *logging.Logger
	stop       chan struct{}
	actionTime time.Time
}

func getRandomOpenPort() (int, error) {
	listener, err := net.Listen("tcp", ":0")
	if err != nil {
		return 0, fmt.Errorf("failed to get a random open port: %v", err)
	}
	defer listener.Close()

	addr := listener.Addr().(*net.TCPAddr)
	return addr.Port, nil
}

func NewRelay(client *Client, state *config.Object[config.MacroState], logger *logging.Logger) *Relay {
	port, err := getRandomOpenPort()
	if err != nil {
		port = 45645
	}
	return &Relay{
		client:     client,
		port:       port,
		identities: make(map[string]net.Conn),
		banned:     make(map[string]bool),
		roles:      make(map[string]ClientRole),
		state:      state,
		logger:     logger,
	}
}

func (r *Relay) Identity() string {
	return getIdentity() + "/" + r.state.Object().AccountName
}

func (r *Relay) Start() error {
	if time.Now().Sub(r.actionTime) < time.Second {
		return nil
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.actionTime = time.Now()
	var err error
	defer r.state.SetPath("networking.relayStarting", false)
	r.state.SetPath("networking.relayStarting", true)
	r.listener, err = net.Listen("tcp", fmt.Sprintf(":%d", r.port))
	if err != nil {
		return err
	}

	if err := r.client.Connect(r.listener.Addr().String()); err != nil {
		return errors.Wrap(err, "failed to connect to local relay")
	}

	txtRecords := []string{fmt.Sprintf("identity=%s", url.QueryEscape(r.Identity()))}
	r.server, err = zeroconf.Register("RevolutionMacro", "_revolution._tcp", "local.", r.port, txtRecords, nil)
	if err != nil {
		return errors.Wrap(err, "failed to start zeroconf")
	}

	r.state.SetPath("networking.relayActive", true)

	go func() {
		for {
			select {
			case <-r.stop:
				return
			default:
				conn, err := r.listener.Accept()
				if err != nil {
					if errors.Is(err, net.ErrClosed) || err.Error() == "use of closed network connection" {
						return
					}
					r.logger.Log(0, logging.Error, fmt.Sprintf("[Relay]: failed to accept new connection: %v", err))
					continue
				}
				go r.handleConnection(conn)
			}

		}
	}()

	return nil
}

func (r *Relay) Ban(identity string) {
	conn, ok := r.identities[identity]
	if !ok {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	conn.Close()
	r.banned[identity] = true
	delete(r.identities, identity)
	delete(r.roles, identity)
	r.broadcastIdentities()
}

func (r *Relay) Stop() {
	if time.Now().Sub(r.actionTime) < time.Second {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.actionTime = time.Now()
	var message = Message{
		Kind:     ShutdownMessageKind,
		Receiver: BroadcastReceiver,
		Sender:   RelayReceiver,
		Content:  "{}",
	}
	r.handleMessage(&message)
	r.state.SetPath("networking.relayActive", false)
	r.listener.Close()
	r.server.Shutdown()
	for _, conn := range r.identities {
		conn.Close()
	}
	clear(r.identities)
	clear(r.roles)
}

func (r *Relay) handleConnection(conn net.Conn) {
	reader := bufio.NewReader(conn)
	data, err := reader.ReadString('\n')
	if err != nil {
		r.logger.Log(0, logging.Warning, fmt.Sprintf("[Relay]: Failed to receive registration message from client %s", conn.RemoteAddr().String()))
		conn.Close()
		return
	}

	var message Message
	if err := json.Unmarshal([]byte(data), &message); err != nil || message.Kind != RegistrationMessageKind || message.Receiver != RelayReceiver {
		r.logger.Log(0, logging.Warning, fmt.Sprintf("[Relay]: Failed to decode message from client %s: %v", conn.RemoteAddr().String(), err))
		conn.Close()
		return
	}

	var registrationMessage RegistrationMessage
	if err = json.Unmarshal([]byte(message.Content), &registrationMessage); err != nil {
		r.logger.Log(0, logging.Warning, fmt.Sprintf("[Relay]: Failed to decode registration message from client %s", conn.RemoteAddr().String()))
		conn.Close()
		return
	}

	identity := registrationMessage.Identity
	ack := Message{
		Kind:     AckRegistrationMessageKind,
		Receiver: identity,
		Sender:   RelayReceiver,
		Content:  "{}",
	}

	if _, ok := r.identities[identity]; ok {
		byteData, _ := json.Marshal(AckRegistrationMessage{Error: fmt.Sprintf("The identity \"%s\" is already connected to this relay!", identity)})
		ack.Content = string(byteData)
		msg, _ := json.Marshal(ack)
		conn.Write(append(msg, "\r\n"...))
		conn.Close()
		return
	}

	r.mu.Lock()
	r.identities[identity] = conn
	r.handleMessage(&ack)
	r.mu.Unlock()
	r.broadcastIdentities()

	defer func() {
		r.mu.Lock()
		delete(r.identities, identity)
		delete(r.roles, identity)
		r.mu.Unlock()
		conn.Close()
	}()

	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			return
		}
		var message Message
		if err = json.Unmarshal([]byte(line), &message); err != nil {
			r.logger.Log(0, logging.Warning, fmt.Sprintf("[Relay]: Failed to decode message from client %s: %v", identity, err))
			continue
		}
		message.Data = []byte(line)
		r.mu.Lock()
		r.handleMessage(&message)
		r.mu.Unlock()
	}
}

func (r *Relay) broadcastIdentitiesLocked() {
	var identities ConnectedIdentitiesMessage
	for identity, conn := range r.identities {
		role, _ := r.roles[identity]
		identities.Identities = append(identities.Identities, config.NetworkIdentity{
			Address:  conn.RemoteAddr().String(),
			Identity: identity,
			Role:     string(role),
		})
	}
	data, _ := json.Marshal(identities)
	var message = Message{
		Kind:     ConnectedIdentitiesMessageKind,
		Receiver: BroadcastReceiver,
		Sender:   RelayReceiver,
		Content:  string(data),
	}
	r.handleMessage(&message)
}

func (r *Relay) broadcastIdentities() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.broadcastIdentitiesLocked()
}

func (r *Relay) handleRoleRegistration(message *Message) {
	var content SetRoleMessage
	if err := json.Unmarshal([]byte(message.Content), &content); err != nil {
		r.logger.Log(0, logging.Warning, fmt.Sprintf("[Relay]: Failed to unmarshal role registration message from identity %s", message.Sender))
		return
	}
	role, ok := r.roles[message.Sender]
	if !ok {
		role = "none"
	}
	r.logger.Log(0, logging.Info,
		fmt.Sprintf("[Relay]: Received role registration message from identity %s: %s->%s", message.Sender, role, content.Role))
	var ack AckSetRoleMessage
	var ackMessage = Message{
		Kind:     AckSetRoleMessageKind,
		Receiver: message.Sender,
		Sender:   RelayReceiver,
	}
	if role != content.Role {
		if content.Role == MainClientRole {
			for id, activeRole := range r.roles {
				if activeRole == MainClientRole {
					ack.Error = fmt.Sprintf("The main role is already taken by identity %s", id)
				}
			}
		}
		if ack.Error == "" {
			r.roles[message.Sender] = content.Role
		}
	}
	data, _ := json.Marshal(ack)
	ackMessage.Content = string(data)
	r.handleMessage(&ackMessage)
	r.broadcastIdentitiesLocked()
}

func (r *Relay) handleMessage(message *Message) {
	if string(message.Data) == "" {
		message.Data, _ = json.Marshal(message)
	}
	switch message.Receiver {
	case RelayReceiver:
		if message.Kind == SetRoleMessageKind {
			r.handleRoleRegistration(message)
		}
	case BroadcastReceiver:
		for _, conn := range r.identities {
			conn.Write(append(message.Data, "\r\n"...))
		}
		return
	default:
		if strings.HasPrefix(message.Receiver, "!") {
			role := strings.TrimPrefix(message.Receiver, "!")
			for identity, idRole := range r.roles {
				if string(idRole) == role {
					r.identities[identity].Write(append(message.Data, "\r\n"...))
				}
			}
		} else {
			if conn, ok := r.identities[message.Receiver]; !ok {
				r.logger.Log(0, logging.Warning,
					fmt.Sprintf("[Relay]: Failed to forward message from %s->%s: invalid receiver", message.Sender, message.Receiver))
				return
			} else {
				fmt.Println(conn.Write(append(message.Data, "\r\n"...)))
			}
		}
	}
}
