package config

import (
	"context"
	"fmt"
	"github.com/sqweek/dialog"
	"github.com/wailsapp/wails/v2/pkg/runtime"
	"sync"
	"time"
)

type event struct {
	path, op  string
	primitive bool
	key       string
	value     interface{}
}

type waitingEvent struct {
	id   int
	wait chan<- bool
}

type Runtime struct {
	sync.Mutex
	ready       bool
	roots       map[string]Reactive
	events      []event
	waiting     sync.Map
	errorActive bool
	evtCounter  int
	activeEvent int
}

func (r *Runtime) handleError(op string, err error) bool {
	if err == nil {
		return true
	}
	if r.errorActive {
		return false
	}
	r.errorActive = true
	dialog.Message(fmt.Sprintf("%s operation failed: %v", op, err)).Error()
	r.errorActive = false
	return false
}

func (r *Runtime) handleEventError(op string, err error) bool {
	if err == nil {
		return true
	}
	runtime.EventsEmit(AppContext, "rollback", r.activeEvent)
	r.waiting.Range(func(k, v interface{}) bool {
		v.(waitingEvent).wait <- true
		r.evtCounter++
		r.waiting.Delete(k)
		return true
	})
	if r.errorActive {
		return false
	}
	r.errorActive = true
	dialog.Message(fmt.Sprintf("%s operation failed: %v", op, err)).Error()
	r.errorActive = false
	return false
}

func (r *Runtime) AddRoot(name string, object Reactive) {
	r.roots[name] = object
}

func (r *Runtime) Set(path string, value interface{}) {
	if !r.ready {
		r.events = append(r.events, event{path: path, op: "set", value: value})
		return
	}

	runtime.EventsEmit(AppContext, "set", path, r.activeEvent, value)
}

func (r *Runtime) Append(path string, primitive bool, key string) {
	if !r.ready {
		r.events = append(r.events, event{path: path, op: "append", primitive: primitive, key: key})
		return
	}
	runtime.EventsEmit(AppContext, "append", path, r.activeEvent, primitive, key)
}

func (r *Runtime) Delete(path string) {
	if !r.ready {
		r.events = append(r.events, event{path: path, op: "delete"})
		return
	}
	runtime.EventsEmit(AppContext, "delete", path, r.activeEvent)
}

func (r *Runtime) eventEpilogue() {
	r.evtCounter++
	r.waiting.Range(func(k, v interface{}) bool {
		if v.(waitingEvent).id == r.evtCounter {
			v.(waitingEvent).wait <- false
			return false
		}
		return true
	})
}

func (r *Runtime) Listen() {
	_ = runtime.EventsOn(AppContext, "set_client", func(data ...interface{}) {
		path := data[0].(string)
		ct := int(data[2].(float64))
		if r.evtCounter != ct {
			waitChan := make(chan bool)
			r.waiting.Store(ct, waitingEvent{id: ct, wait: waitChan})
			if <-waitChan {
				return
			}
			r.waiting.Delete(ct)
		}
		r.activeEvent = ct
		defer r.eventEpilogue()
		r.handleEventError("Set", r.roots[getRoot(path)].Set(mustCompilePath(getPath(path)), 0, data[1]))
	})
	_ = runtime.EventsOn(AppContext, "append_client", func(data ...interface{}) {
		path := data[0].(string)
		ct := int(data[2].(float64))
		if r.evtCounter != ct {
			waitChan := make(chan bool)
			r.waiting.Store(ct, waitingEvent{id: ct, wait: waitChan})
			if <-waitChan {
				return
			}
			r.waiting.Delete(ct)
		}
		r.activeEvent = ct
		defer r.eventEpilogue()
		r.handleEventError("Append", r.roots[getRoot(path)].Append(mustCompilePath(getPath(path)), 0, data[1]))
	})
	_ = runtime.EventsOn(AppContext, "delete_client", func(data ...interface{}) {
		path := data[0].(string)
		ct := int(data[1].(float64))
		if r.evtCounter != ct {
			waitChan := make(chan bool)
			r.waiting.Store(ct, waitingEvent{id: ct, wait: waitChan})
			if <-waitChan {
				return
			}
			r.waiting.Delete(ct)
		}
		r.activeEvent = ct
		defer r.eventEpilogue()
		r.handleEventError("Delete", r.roots[getRoot(path)].Delete(mustCompilePath(getPath(path)), 0))
	})
}

func (r *Runtime) Start() {
	r.Listen()
	for _, evt := range r.events {
		switch evt.op {
		case "set":
			runtime.EventsEmit(AppContext, "set", evt.path, -1, evt.value)
		case "append":
			runtime.EventsEmit(AppContext, "append", evt.path, -1, evt.primitive, evt.key)
		}
	}
	r.events = nil
}

func NewRuntime(ctx context.Context) *Runtime {
	app := &Runtime{roots: make(map[string]Reactive)}
	ready := make(chan bool)
	runtime.EventsOnce(ctx, "ready", func(...interface{}) {
		fmt.Println("ready")
		app.ready = true
		for len(app.roots) != 3 {
			<-time.After(100 * time.Millisecond)
		}
		ready <- true
	})
	go func() {
		select {
		case <-ready:
			app.Start()
			return
		case <-time.After(time.Second * 10):
			//dialog.Message("UI failed to start! Please contact the developer for assistance").Error()
			//os.Exit(1)
		}
	}()
	return app
}
