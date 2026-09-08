package config

import (
	"fmt"
	"github.com/stretchr/testify/assert"
	"gopkg.in/yaml.v3"
	"testing"
)

type mockFile struct {
	runtime *Runtime
}

var _mockFile = &mockFile{runtime: &Runtime{}}

func (m *mockFile) Runtime() *Runtime { return m.runtime }
func (m *mockFile) Save() error       { return nil }

func TestConfigObject_SetPrimitive(t *testing.T) {
	type object struct {
		Val string `yaml:"val"`
	}

	var obj = Object[object]{}
	obj.Initialize("Root", _mockFile)
	assert.NoError(t, obj.SetPath("val", "test"))
	val, err := obj.GetPath("val")
	assert.NoError(t, err)
	assert.Equal(t, val, "test")
}

func TestConfigObject_SetNestedObjectPrimitive(t *testing.T) {
	type nested2 struct {
		Val2 int  `yaml:"val2"`
		Val3 bool `state:"val3"`
	}

	type nested struct {
		Val string           `yaml:"val"`
		Obj *Object[nested2] `state:"val2"`
	}

	type object struct {
		Val string          `yaml:"val"`
		Obj *Object[nested] `yaml:"obj"`
	}

	var obj = Object[object]{}
	obj.Initialize("", _mockFile)
	assert.NoError(t, obj.SetPath("obj.val", "test"))
	val, err := obj.GetPath("obj.val")
	assert.NoError(t, err)
	assert.Equal(t, val, "test")
	assert.NoError(t, obj.SetPath("obj.val2.val3", true))
	val, err = obj.GetPath("obj.val2.val3")
	assert.NoError(t, err)
	assert.Equal(t, val, true)

	var activated = false
	callback := func(v interface{}) {
		fmt.Println(v)
		activated = true
	}

	assert.NoError(t, obj.ListenPath("obj.val2.val3", callback))
	assert.NoError(t, obj.SetPath("obj.val2.val3", false))
	assert.Equal(t, activated, true)
}

func TestConfigObject_List(t *testing.T) {
	type nested struct {
		Val string `yaml:"val" default:"test"`
		Int int    `yaml:"int" default:"12"`
	}

	type keyed struct {
		ID  string `yaml:"id" key:"true"`
		Val string `yaml:"val" default:"test2"`
	}

	type object struct {
		Val  string        `yaml:"val"`
		Objs *List[nested] `yaml:"objs"`
		Prim *List[int]    `yaml:"prim"`
		Key  *List[keyed]  `yaml:"key"`
	}

	var obj = Object[object]{}
	obj.Initialize("Root", _mockFile)

	// Test keyed append
	assert.NoError(t, obj.AppendPath("key[test]"))
	assert.Equal(t, obj.LengthPath("key"), 1)
	val, err := obj.GetPath("key[test].id")
	assert.NoError(t, err)
	assert.Equal(t, val, "test")
	val, err = obj.GetPath("key[test].val")
	assert.NoError(t, err)
	assert.Equal(t, val, "test2")
	assert.Error(t, obj.SetPath("key[test].id", "val"))
	assert.NoError(t, obj.SetPath("key[test].val", "test3"))
	val, err = obj.GetPath("key[test].val")
	assert.NoError(t, err)
	assert.Equal(t, val, "test3")

	var activated = false
	callback := func(v interface{}) {
		fmt.Println(v)
		activated = true
	}

	assert.NoError(t, obj.ListenPath("key", callback))
	assert.NoError(t, obj.AppendPath("key[test2]"))
	assert.Equal(t, activated, true)
	activated = false
	assert.NoError(t, obj.DeletePath("key[test2]"))
	assert.Equal(t, activated, true)
}

func TestConfigObject_Concrete(t *testing.T) {
	type X string
	type keyed struct {
		ID  string `yaml:"id" key:"true"`
		Val string `yaml:"val" default:"test"`
	}

	type nested struct {
		Val   string       `yaml:"val"`
		Alias X            `yaml:"alias" default:"test"`
		Items *List[int]   `yaml:"items"`
		Keys  *List[keyed] `yaml:"keys"`
	}

	type object struct {
		Val string          `yaml:"val"`
		Obj *Object[nested] `yaml:"obj"`
	}

	var obj = Object[object]{}
	obj.Initialize("Root", _mockFile)
	assert.NotNil(t, Concrete[string](&obj, "val"))
	assert.NotNil(t, Concrete[nested](&obj, "obj"))
	assert.NotNil(t, Concrete[X](&obj, "obj.alias"))
	assert.Equal(t, *Concrete[X](&obj, "obj.alias"), X("test"))
	assert.NoError(t, obj.AppendPath("obj.items"))
	assert.NotNil(t, Concrete[int](&obj, "obj.items[0]"))
	assert.Equal(t, *Concrete[int](&obj, "obj.items[0]"), 0)
	assert.NoError(t, obj.DeletePath("obj.items[0]"))
	assert.NoError(t, obj.AppendPath("obj.keys[test]"))
	assert.NotNil(t, Concrete[string](&obj, "obj.keys[test].id"))
	assert.Equal(t, *Concrete[string](&obj, "obj.keys[test].id"), "test")
	assert.Equal(t, *Concrete[string](&obj, "obj.keys[test].val"), "test")
	assert.NoError(t, obj.DeletePath("obj.keys[test]"))
}

func TestConfigObject_Serialization(t *testing.T) {
	type nested struct {
		Val string `yaml:"val" default:"test"`
		Int int    `yaml:"int" default:"12"`
	}

	type keyed struct {
		ID  string          `yaml:"id" key:"true"`
		Val string          `yaml:"val" default:"test2"`
		Obj *Object[nested] `yaml:"obj"`
	}

	type test struct {
		Val  string        `yaml:"val,omitempty"`
		Objs *List[nested] `yaml:"objs"`
		Prim *List[int]    `yaml:"prim"`
		Key  *List[keyed]  `yaml:"key"`
	}

	var obj = Object[test]{}
	obj.Initialize("Root", _mockFile)
	assert.NoError(t, obj.AppendPath("objs"))
	assert.NoError(t, obj.AppendPath("prim"))
	assert.NoError(t, obj.AppendPath("key[test]"))

	data, err := yaml.Marshal(&obj)
	assert.NoError(t, err)
	var res = `objs:
    - val: test
      int: 12
prim:
    - 0
key:
    - id: test
      val: test2
      obj:
        val: test
        int: 12
`
	assert.Equal(t, res, string(data))

	var newObj test
	var mutated = `objs:
    - val: test
      int: 12
    - val: x
      int: 5
prim:
    - 0
    - 3
key:
    - id: test2
      val: test3
      obj:
        val: test2
        int: 5
`
	assert.NoError(t, yaml.Unmarshal([]byte(mutated), &newObj))
	obj = Object[test]{obj: &newObj}
	obj.Initialize("Root", _mockFile)
	data, err = yaml.Marshal(&newObj)
	assert.NoError(t, err)
	assert.Equal(t, string(data), mutated)

}

func TestConfigObject_Runtime(t *testing.T) {
	type nested struct {
		Val string `yaml:"val" default:"test"`
		Int int    `yaml:"int" default:"12"`
	}

	type keyed struct {
		ID  string          `yaml:"id" key:"true"`
		Val string          `yaml:"val" default:"test2"`
		Obj *Object[nested] `yaml:"obj"`
	}

	type test struct {
		Val  string          `yaml:"val,omitempty" default:"test"`
		Nest *Object[nested] `yaml:"nest"`
		Objs *List[nested]   `yaml:"objs"`
		Prim *List[int]      `yaml:"prim"`
		Key  *List[keyed]    `yaml:"key"`
	}
	var obj = Object[test]{}
	obj.Initialize("Root", _mockFile)
	assert.Len(t, _mockFile.runtime.events, 3)
	assert.Equal(t, _mockFile.runtime.events[0].value, "test")
	_mockFile.runtime.events = nil
	assert.NoError(t, obj.AppendPath("objs"))
	assert.Equal(t, _mockFile.runtime.events[0].op, "append")
	_mockFile.runtime.events = nil
	assert.NoError(t, obj.AppendPath("key[test]"))
	fmt.Println(_mockFile.runtime.events)
	assert.Len(t, _mockFile.runtime.events, 5)
	assert.Equal(t, _mockFile.runtime.events[0].op, "append")
	_mockFile.runtime.events = nil
	assert.NoError(t, obj.AppendPath("prim"))
	assert.Len(t, _mockFile.runtime.events, 1)
	fmt.Println(_mockFile.runtime.events)
}
