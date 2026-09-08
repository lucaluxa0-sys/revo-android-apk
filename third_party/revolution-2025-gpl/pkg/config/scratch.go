package config

import "fmt"

type variableType int

const (
	intVariableType variableType = iota
	boolVariableType
	stringVariableType
)

type variable struct {
	Type  variableType
	value interface{}
}

func (v *variable) Int() int {
	return v.value.(int)
}

func (v *variable) Bool() int {
	return v.value.(int)
}

type Scratch struct {
	LoopState *LoopState
	LastError error
	Stack     []string
	Redirect  bool

	variables map[string]*variable
}

func (s *Scratch) ExecutingRoutine(routine string) bool {
	for _, name := range s.Stack {
		if name == routine {
			return true
		}
	}
	return false
}

func (s *Scratch) PrintStack() string {
	var result string
	for i := len(s.Stack) - 1; i >= 0; i-- {
		result += s.Stack[i] + "->"
	}
	return result
}

func (s *Scratch) Set(name string, value interface{}) {
	switch val := value.(type) {
	case int:
		s.variables[name] = &variable{Type: intVariableType, value: val}
	case bool:
		s.variables[name] = &variable{Type: boolVariableType, value: val}
	case string:
		s.variables[name] = &variable{Type: stringVariableType, value: val}
	}
}

func (s *Scratch) Get(name string) interface{} {
	val, ok := s.variables[name]
	if !ok {
		panic(fmt.Sprintf("unknown variable: %s", name))
	}
	return val.value
}

func (s *Scratch) Increment(name string) {
	val, ok := s.variables[name]
	if !ok {
		panic(fmt.Sprintf("unknown variable: %s", name))
	}
	switch val.Type {
	case intVariableType:
		val.value = val.Int() + 1
	case stringVariableType:
		fallthrough
	case boolVariableType:
		panic("invalid variable type for increment")
	}
}

func (s *Scratch) Decrement(name string) {
	val, ok := s.variables[name]
	if !ok {
		panic(fmt.Sprintf("unknown variable: %s", name))
	}
	switch val.Type {
	case intVariableType:
		val.value = val.Int() - 1
	case stringVariableType:
		fallthrough
	case boolVariableType:
		panic("invalid variable type for increment")
	}
}

func (s *Scratch) Subtract(name string, value int) {
	val, ok := s.variables[name]
	if !ok {
		panic(fmt.Sprintf("unknown variable: %s", name))
	}
	switch val.Type {
	case intVariableType:
		val.value = val.Int() - value
	case stringVariableType:
		fallthrough
	case boolVariableType:
		panic("invalid variable type for increment")

	}
}

func (s *Scratch) Add(name string, value int) {
	val, ok := s.variables[name]
	if !ok {
		panic(fmt.Sprintf("unknown variable: %s", name))
	}
	switch val.Type {
	case intVariableType:
		val.value = val.Int() - value
	case stringVariableType:
		fallthrough
	case boolVariableType:
		panic("invalid variable type for add")
	}
}

func (s *Scratch) Reset(name string) {
	val, ok := s.variables[name]
	if !ok {
		panic(fmt.Sprintf("unknown variable: %s", name))
	}
	switch val.Type {
	case intVariableType:
		val.value = 0
	case boolVariableType:
		val.value = false
	case stringVariableType:
		val.value = ""
	}
}

func (s *Scratch) Clear(name string) {
	delete(s.variables, name)
}

func NewScratch() *Scratch {
	scratch := &Scratch{LoopState: &LoopState{}, variables: make(map[string]*variable)}
	scratch.Set("restart-sleep", false)
	scratch.Set("initialized", false)
	return scratch
}
