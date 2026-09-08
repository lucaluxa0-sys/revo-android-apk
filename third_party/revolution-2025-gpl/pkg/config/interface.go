package config

import (
	"context"
	"fmt"
	"github.com/pkg/errors"
	"reflect"
	"regexp"
	"runtime/debug"
	"strconv"
	"strings"
)

var AppContext context.Context

type ListenOp int

const (
	Set ListenOp = iota
	Append
	Delete
)

type Reactive interface {
	Initialize(path string, file Savable) error
	Set(chain chain, index int, value interface{}) error
	Get(chain chain, index int) (interface{}, error)
	GetConcrete(chain chain, index int) (interface{}, error)
	Append(chain chain, index int, value interface{}) error
	Delete(chain chain, index int) error
	Length(chain chain, index int) int
	Listen(chain chain, index int, callback func(ListenOp, interface{})) error
	File() Savable
}

type reactiveObject interface {
	Reactive
	object() interface{}
}

type reactiveList interface {
	initialize(meta reflect.StructField)
}

type config struct {
	path      string
	file      Savable
	listeners map[string]func(ListenOp, interface{})
}

func (c *config) File() Savable {
	return c.file
}

type link struct {
	val      string
	brackets bool
}

type chain []link

func (c chain) String() string {
	var output = ""
	for i, clink := range c {
		if i == 0 {
			output += clink.val
		}
		if clink.brackets {
			output += fmt.Sprintf("[%s]", clink.val)
		} else {
			output += fmt.Sprintf(".%s", clink.val)
		}
	}
	return output
}

func (c chain) TrimRight() chain {
	return c[:len(c)-1]
}

func (c *config) errPath(err string) error {
	return errors.New(fmt.Sprintf("%s: %s", c.path, err))
}

func (c *config) errPanic(err string) {
	panic(fmt.Sprintf("%s: %s", c.path, err))
}

func (c *config) setField(meta reflect.StructField, field reflect.Value, chain chain, index int, value interface{}) error {
	if obj, ok := field.Interface().(Reactive); ok {
		if index+1 == len(chain) {
			return errors.New("cannot set an object value")
		}
		return obj.Set(chain, index+1, value)
	}
	if len(chain)-1 != index {
		return c.errPath("cannot index a primitive value")
	}
	var path string
	if chain[index].brackets {
		path = fmt.Sprintf("%s[%s]", c.path, chain[index].val)
	} else {
		path = fmt.Sprintf("%s.%s", c.path, chain[index].val)
	}
	switch field.Kind() {
	case reflect.Int:
		var val int
		switch v := value.(type) {
		case int:
			val = v
		case float64:
			val = int(v)
		}
		field.SetInt(int64(val))
		c.file.Runtime().Set(path, val)
	case reflect.Bool:
		field.SetBool(value.(bool))
		c.file.Runtime().Set(path, value.(bool))
	case reflect.String:
		field.SetString(value.(string))
		c.file.Runtime().Set(path, value.(string))
	case reflect.Float64:
		field.SetFloat(value.(float64))
		c.file.Runtime().Set(path, value.(float64))
	default:
		return errors.New("unsupported value")
	}
	if listener, ok := c.listeners[chain.String()]; ok {
		listener(Set, value)
	}
	// TODO: save before runtime update
	if meta.Tag.Get("yaml") != "" {
		if err := c.file.Save(); err != nil {
			return errors.Wrap(err, "failed to save to file")
		}
	}

	return nil
}

func (c *config) getField(field reflect.Value, chain chain, index int) (interface{}, error) {
	if obj, ok := field.Interface().(Reactive); ok {
		if _, ok := obj.(reactiveObject); ok {
			if index+1 == len(chain) {
				return nil, c.errPath("cannot get an object value")
			}
		}
		return obj.Get(chain, index+1)
	}
	if len(chain)-1 != index {
		debug.PrintStack()
		return nil, c.errPath("cannot index a primitive value")
	}
	switch field.Kind() {
	case reflect.Int:
		return int(field.Int()), nil
	case reflect.Bool:
		return field.Bool(), nil
	case reflect.String:
		return field.String(), nil
	case reflect.Float64:
		return field.Float(), nil
	default:
		return errors.New("unsupported value"), nil
	}
}

func (c *config) getConcreteField(field reflect.Value, chain chain, index int) (interface{}, error) {
	if obj, ok := field.Interface().(Reactive); ok {
		if rObj, ok := obj.(reactiveObject); ok {
			if index+1 == len(chain) {
				return rObj.object(), nil
			}
		}
		return obj.GetConcrete(chain, index+1)
	}
	if len(chain)-1 != index {
		return nil, c.errPath("cannot index a primitive value")
	}
	return field.Interface(), nil
}

type List[T any] struct {
	config
	meta       reflect.StructField
	prim       []T
	obj        []*Object[T]
	index      map[string]*Object[T]
	key, keySz string
}

func (c *List[T]) MarshalYAML() (interface{}, error) {
	if c.prim != nil {
		return c.prim, nil
	} else {
		return c.obj, nil
	}
}

func (c *List[T]) UnmarshalYAML(unmarshal func(interface{}) error) error {
	var zero [0]T
	tt := reflect.TypeOf(zero).Elem()
	if tt.Kind() != reflect.Struct {
		var temp []T
		if err := unmarshal(&temp); err != nil {
			return err
		}
		c.prim = temp
		return nil
	}

	var temp []*T
	if err := unmarshal(&temp); err != nil {
		return err
	}
	var objs []*Object[T]
	for _, v := range temp {
		objs = append(objs, &Object[T]{obj: v})
	}
	c.obj = objs

	for i := 0; i < tt.NumField(); i++ {
		field := tt.Field(i)
		if key := field.Tag.Get("key"); key == "true" {
			c.key = field.Name
			c.keySz = field.Tag.Get("yaml")
			c.index = make(map[string]*Object[T])
			for _, obj := range c.obj {
				objKey := reflect.ValueOf(obj.object()).Elem().FieldByName(c.key).String()
				if _, ok := c.index[objKey]; ok {
					return c.errPath(fmt.Sprintf("duplicate key: %s", objKey))
				}
				c.index[objKey] = obj
			}
		}
	}

	return nil
}

func (c *List[T]) ForEach(callback func(*T)) {
	if c.prim != nil {
		for _, v := range c.prim {
			callback(&v)
		}
	} else if c.index != nil {
		for _, obj := range c.index {
			callback(obj.obj)
		}
	} else {
		for _, obj := range c.obj {
			callback(obj.obj)
		}
	}
}

func (c *List[T]) ForEachObject(callback func(*Object[T])) {
	if c.prim != nil {
		panic("cannot call for each object on a primitive list")
	} else if c.index != nil {
		for _, obj := range c.index {
			callback(obj)
		}
	} else {
		for _, obj := range c.obj {
			callback(obj)
		}
	}
}

func (c *List[T]) Initialize(path string, file Savable) error {
	c.listeners = make(map[string]func(ListenOp, interface{}))
	c.file = file
	if c.prim == nil && c.obj == nil {
		var zero [0]T
		tt := reflect.TypeOf(zero).Elem()
		if tt.Kind() != reflect.Struct {
			c.prim = make([]T, 0)
		} else {
			c.obj = make([]*Object[T], 0)
			for i := 0; i < tt.NumField(); i++ {
				field := tt.Field(i)
				if key := field.Tag.Get("key"); key == "true" {
					c.key = field.Name
					c.keySz = field.Tag.Get("yaml")
					c.index = make(map[string]*Object[T])
				}
			}
		}
	}

	c.path = path
	if c.obj != nil {
		if c.key != "" {
			c.file.Runtime().Append(fmt.Sprintf("%s[_init]", path), false, c.keySz)
		} else {
			c.file.Runtime().Append(fmt.Sprintf("%s[_init]", path), false, "")
		}
		for n, obj := range c.obj {
			if c.key != "" {
				key := reflect.ValueOf(*obj.obj).FieldByName(c.key).String()
				listPath := fmt.Sprintf("%s[%s]", path, key)
				c.file.Runtime().Append(listPath, false, c.keySz)
				_ = obj.Initialize(listPath, file)
			} else {
				listPath := fmt.Sprintf("%s[%d]", path, n)
				c.file.Runtime().Append(listPath, false, c.keySz)
				_ = obj.Initialize(fmt.Sprintf("%s[%d]", path, n), file)
			}
		}
	} else if c.prim != nil {
		c.file.Runtime().Append(fmt.Sprintf("%s[_init]", path), true, c.keySz)
		for i, value := range c.prim {
			c.file.Runtime().Set(fmt.Sprintf("%s[%d]", path, i), value)

		}
	}
	return nil
}

func (c *List[T]) Set(chain chain, index int, value interface{}) error {
	if len(chain) == index {
		return c.errPath("a key must be provided")
	}
	if !chain[index].brackets {
		return c.errPath("list values must be indexed with brackets")
	}
	if c.index != nil {
		if len(chain) == index+1 {
			return c.errPath("cannot set an object value")
		}
		if chain[index+1].val == c.keySz {
			return c.errPath(fmt.Sprintf("cannot modify object key \"%s\"", chain[index].val))
		}
		if val, ok := c.index[chain[index].val]; ok {
			return c.setField(c.meta, reflect.ValueOf(val), chain, index, value)
		} else {
			return c.errPath(fmt.Sprintf("invalid key \"%s\"", chain[index].val))
		}
	}
	idx, err := strconv.Atoi(chain[index].val)
	var count int
	var slice interface{}
	if c.prim != nil {
		count = len(c.prim)
		slice = c.prim
	} else {
		count = len(c.obj)
		slice = c.obj
	}
	if err != nil || (idx < 0 || idx >= count) {
		return c.errPath("invalid index")
	}

	field := reflect.ValueOf(slice).Index(idx)
	return c.setField(c.meta, field, chain, index, value)
}

func (c *List[T]) Get(chain chain, index int) (interface{}, error) {
	if len(chain) == index {
		return nil, c.errPath("a key must be provided")
	}
	if !chain[index].brackets {
		return nil, c.errPath("list values must be indexed with brackets")
	}
	if c.index != nil {
		if val, ok := c.index[chain[index].val]; ok {
			return c.getField(reflect.ValueOf(val), chain, index)
		} else {
			return nil, c.errPath(fmt.Sprintf("invalid key \"%s\"", chain[index].val))
		}
	}
	var count int
	var slice interface{}
	if c.prim != nil {
		count = len(c.prim)
		slice = c.prim
	} else {
		count = len(c.obj)
		slice = c.obj
	}
	idx, err := strconv.Atoi(chain[index].val)
	if err != nil || (idx < 0 || idx >= count) {
		return nil, c.errPath("invalid integer index")
	}

	field := reflect.ValueOf(slice).Index(idx)
	return c.getField(field, chain, index)
}

func (c *List[T]) GetConcrete(chain chain, index int) (interface{}, error) {
	if c.prim != nil {
		idx, err := strconv.Atoi(chain[index].val)
		if err != nil || (idx < 0 || idx >= len(c.prim)) {
			return nil, c.errPath("invalid integer index")
		}
		field := reflect.ValueOf(c.prim).Index(idx)
		return field.Interface(), nil
	}
	if len(chain) == index {
		return c.list(), nil
	}
	if !chain[index].brackets {
		return nil, c.errPath("list values must be indexed with brackets")
	}
	if c.index != nil {
		if val, ok := c.index[chain[index].val]; ok {
			if len(chain) == index+1 {
				return val, nil
			}
			return c.getConcreteField(reflect.ValueOf(val), chain, index)
		} else {
			return nil, nil
		}
	}
	idx, err := strconv.Atoi(chain[index].val)
	if err != nil || (idx < 0 || idx >= len(c.obj)) {
		return nil, c.errPath("invalid integer index")
	}

	field := reflect.ValueOf(c.obj).Index(idx)
	if len(chain) == index+1 {
		return field.Interface(), nil
	}
	return field.Interface().(Reactive).GetConcrete(chain, index+1)
}

func (c *List[T]) Append(chain chain, index int, value interface{}) error {
	if c.index != nil && len(chain) == index {
		return c.errPath("a primary key is required")
	}
	if c.index != nil && !chain[index].brackets {
		return c.errPath("list values must be indexed with brackets")
	}
	if len(chain)-1 != index && c.index != nil {
		if val, ok := c.index[chain[index].val]; ok {
			return val.Append(chain, index+1, nil)
		} else {
			return c.errPath(fmt.Sprintf("invalid key \"%s\"", chain[index].val))
		}
	} else if len(chain)-1 != index && c.obj != nil {
		idx, err := strconv.Atoi(chain[index].val)
		if err != nil || (idx < 0 || idx >= len(c.obj)) {
			return c.errPath("invalid integer index")
		}
		return c.obj[idx].Append(chain, index+1, nil)
	}

	if c.prim != nil {
		c.prim = append(c.prim, value.(T))
		path := fmt.Sprintf("%s[%d]", c.path, len(c.prim)-1)
		c.file.Runtime().Set(path, value)
		if c.meta.Tag.Get("yaml") != "" {
			if err := c.file.Save(); err != nil {
				return errors.Wrap(err, "failed to save to file")
			}
		}
		if listener, ok := c.listeners[chain.TrimRight().String()]; ok {
			listener(Append, value.(T))
		}
		return nil
	}

	cfo := &Object[T]{}
	if c.key != "" {
		key := chain[index].val
		if _, ok := c.index[key]; ok {
			return c.errPath(fmt.Sprintf("key \"%s\" already exists", key))
		}
		path := fmt.Sprintf("%s[%s]", c.path, chain[index].val)
		c.file.Runtime().Append(path, false, c.keySz)
		_ = cfo.Initialize(path, c.file)
		ref := reflect.ValueOf(cfo.obj)
		ref.Elem().FieldByName(c.key).SetString(key)
		c.file.Runtime().Set(fmt.Sprintf("%s[%s].%s", c.path, key, c.keySz), key)
		c.index[key] = cfo
	} else {
		path := fmt.Sprintf("%s[%d]", c.path, len(c.obj))
		c.file.Runtime().Append(path, false, c.keySz)
		_ = cfo.Initialize(path, c.file)
	}
	c.obj = append(c.obj, cfo)
	if c.meta.Tag.Get("yaml") != "" {
		if err := c.file.Save(); err != nil {
			return errors.Wrap(err, "failed to save to file")
		}
	}
	if listener, ok := c.listeners[chain.TrimRight().String()]; ok {
		listener(Append, cfo)
	}
	return nil
}

func (c *List[T]) Delete(chain chain, index int) error {
	if c.index != nil && len(chain) == index {
		return c.errPath("a primary key is required")
	}
	if !chain[index].brackets {
		return errors.New("list values must be indexed with brackets")
	}
	var count, idx = 0, -1
	if len(chain)-1 != index && c.index != nil {
		if val, ok := c.index[chain[index].val]; ok {
			return val.Delete(chain, index+1)
		} else {
			return c.errPath(fmt.Sprintf("invalid key \"%s\"", chain[index].val))
		}
	} else if len(chain)-1 != index && c.obj != nil {
		idx, err := strconv.Atoi(chain[index].val)
		if err != nil || (idx < 0 || idx >= len(c.obj)) {
			return c.errPath("invalid integer index")
		}
		return c.obj[idx].Delete(chain, index+1)
	} else if c.index != nil {
		for i, obj := range c.obj {
			if reflect.ValueOf(obj.obj).Elem().FieldByName(c.key).String() == chain[index].val {
				idx = i
			}
		}
		if idx == -1 {
			return c.errPath(fmt.Sprintf("invalid key \"%s\"", chain[index].val))
		}
	}
	if idx == -1 {
		if c.prim != nil {
			count = len(c.prim)
		} else {
			count = len(c.obj)
		}
		var err error
		idx, err = strconv.Atoi(chain[index].val)
		if err != nil || (idx < 0 || idx >= count) {
			return c.errPath("invalid integer index")
		}
	}
	delete(c.index, chain[index].val)
	if c.prim != nil {
		for i, _ := range c.prim {
			if listener, ok := c.listeners[chain.TrimRight().String()]; ok {
				listener(Delete, c.prim[i])
			}
			if i == idx {
				c.prim = append(c.prim[:i], c.prim[i+1:]...)
			}
		}
	} else {
		for i, _ := range c.obj {
			if listener, ok := c.listeners[chain.TrimRight().String()]; ok {
				listener(Delete, c.obj[i])
			}
			if i == idx {
				c.obj = append(c.obj[:i], c.obj[i+1:]...)
			}
		}
	}
	c.file.Runtime().Delete(fmt.Sprintf("%s[%s]", c.path, chain[index].val))
	if c.meta.Tag.Get("yaml") != "" {
		if err := c.file.Save(); err != nil {
			return errors.Wrap(err, "failed to save to file")
		}
	}
	return nil
}

func (c *List[T]) Length(chain chain, index int) int {
	if len(chain) == index {
		if c.prim != nil {
			return len(c.prim)
		} else {
			return len(c.obj)
		}
	}
	if c.prim != nil {
		c.errPanic("cannot get the length of a primitive value")
	}
	idx, err := strconv.Atoi(chain[index].val)
	if err != nil || (idx < 0 || idx >= len(c.obj)) {
		c.errPanic("invalid integer index")
	}

	field := reflect.ValueOf(c.obj).Index(idx)
	return field.Interface().(Reactive).Length(chain, index+1)
}

func (c *List[T]) Listen(chain chain, index int, callback func(ListenOp, interface{})) error {
	if len(chain) == index {
		c.listeners[chain.String()] = callback
		return nil
	}
	if c.prim != nil {
		c.errPanic("cannot listen on a primitive value")
	}
	if !chain[index].brackets {
		return c.errPath("list values must be indexed with brackets")
	}
	if c.index != nil {
		if val, ok := c.index[chain[index].val]; ok {
			return val.Listen(chain, index+1, callback)
		} else {
			return c.errPath(fmt.Sprintf("invalid key \"%s\"", chain[index].val))
		}
	}
	var count int
	idx, err := strconv.Atoi(chain[index].val)
	if err != nil || (idx < 0 || idx >= count) {
		return c.errPath("invalid integer index")
	}

	return c.obj[idx].Listen(chain, index+1, callback)
}

func (c *List[T]) list() interface{} {
	if c.prim != nil {
		return c.prim
	} else {
		return c.obj
	}
}

func (c *List[T]) initialize(meta reflect.StructField) {
	c.meta = meta
}

type Object[T any] struct {
	config
	obj *T
}

func (c *Object[T]) object() interface{} {
	return c.obj
}

func (c *Object[T]) Object() T {
	return *c.obj
}

func (c *Object[T]) MarshalYAML() (interface{}, error) {
	return c.obj, nil
}

func (c *Object[T]) UnmarshalYAML(unmarshal func(interface{}) error) error {
	var obj = new(T)
	if err := unmarshal(obj); err != nil {
		return err
	}
	c.obj = obj
	return nil
}

func (c *Object[T]) Initialize(path string, file Savable) error {
	c.path = path
	c.file = file
	c.listeners = make(map[string]func(ListenOp, interface{}))
	if c.obj == nil {
		c.obj = new(T)
		t := reflect.TypeOf(c.obj).Elem()
		val := reflect.ValueOf(c.obj).Elem()
		for i := 0; i < val.NumField(); i++ {
			field := val.Field(i)
			meta := t.Field(i)
			def := meta.Tag.Get("default")
			if def == "" {
				continue
			}
			switch field.Kind() {
			case reflect.Int:
				fallthrough
			case reflect.Int32:
				fallthrough
			case reflect.Int64:
				if num, err := strconv.Atoi(def); err == nil {
					field.SetInt(int64(num))
				} else {
					panic("invalid number default")
				}
			case reflect.Bool:
				switch def {
				case "true":
					field.SetBool(true)
				case "false":
					field.SetBool(false)
				default:
					panic("invalid boolean default")
				}
			case reflect.String:
				field.SetString(def)
			case reflect.Float64:
				if num, err := strconv.ParseFloat(def, 64); err == nil {
					field.SetFloat(num)
				} else {
					panic("invalid number default")
				}
			}
		}
	}
	t := reflect.TypeOf(c.obj).Elem()
	val := reflect.ValueOf(c.obj).Elem()

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)
		meta := t.Field(i)
		fieldPath := fmt.Sprintf("%s.%s", path, getFieldTag(meta.Tag))
		if field.Kind() == reflect.Ptr && meta.Type.Elem().Kind() == reflect.Struct && field.IsNil() {
			obj := reflect.New(meta.Type.Elem())
			field.Set(obj)
			if cfg, ok := field.Interface().(Reactive); ok {
				_ = cfg.Initialize(fieldPath, file)
			}
			if cfg, ok := field.Interface().(reactiveList); ok {
				cfg.initialize(meta)
			}
		} else if field.Kind() == reflect.Ptr && meta.Type.Elem().Kind() == reflect.Struct {
			if cfg, ok := field.Interface().(Reactive); ok {
				_ = cfg.Initialize(fieldPath, file)
			}
			if cfg, ok := field.Interface().(reactiveList); ok {
				cfg.initialize(meta)
			}
		} else {
			if meta.Tag.Get("key") == "true" {
				continue
			}
			file.Runtime().Set(fieldPath, field.Interface())
		}
	}
	if strings.Count(c.path, ".") == 0 {
		if err := c.file.Save(); err != nil {
			return errors.Wrap(err, fmt.Sprintf("failed to save %s to disk: %v", c.path, err))
		}
	}
	return nil
}

func (c *Object[T]) Set(chain chain, index int, value interface{}) error {
	t := reflect.TypeOf(c.obj).Elem()
	val := reflect.ValueOf(c.obj).Elem()

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)
		meta := t.Field(i)
		if getFieldTag(meta.Tag) == chain[index].val && field.CanSet() {
			return c.setField(meta, field, chain, index, value)
		}
	}

	return c.errPath("field path not found")
}

func (c *Object[T]) Get(chain chain, index int) (interface{}, error) {
	t := reflect.TypeOf(c.obj).Elem()
	val := reflect.ValueOf(c.obj).Elem()

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)
		meta := t.Field(i)
		if getFieldTag(meta.Tag) == chain[index].val {
			return c.getField(field, chain, index)
		}
	}

	return nil, c.errPath(fmt.Sprintf("field %s not found", chain[index].val))
}

func (c *Object[T]) GetConcrete(chain chain, index int) (interface{}, error) {
	t := reflect.TypeOf(c.obj).Elem()
	val := reflect.ValueOf(c.obj).Elem()

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)
		meta := t.Field(i)
		if getFieldTag(meta.Tag) == chain[index].val {
			return c.getConcreteField(field, chain, index)
		}
	}

	return nil, c.errPath(fmt.Sprintf("field %s not found", chain[index].val))
}

func (c *Object[T]) Append(chain chain, index int, value interface{}) error {
	if len(chain) == index {
		return c.errPath("cannot append to an object")
	}
	t := reflect.TypeOf(c.obj).Elem()
	val := reflect.ValueOf(c.obj).Elem()

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)
		meta := t.Field(i)
		if getFieldTag(meta.Tag) == chain[index].val {
			switch obj := field.Interface().(type) {
			case Reactive:
				return obj.Append(chain, index+1, value)
			default:
				return c.errPath("cannot append to a primitive value")
			}
		}
	}

	return c.errPath(fmt.Sprintf("field %s not found", chain[index].val))
}

func (c *Object[T]) Delete(chain chain, index int) error {
	if len(chain) == index {
		return c.errPath("cannot delete from an object")
	}
	t := reflect.TypeOf(c.obj).Elem()
	val := reflect.ValueOf(c.obj).Elem()

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)
		meta := t.Field(i)
		if getFieldTag(meta.Tag) == chain[index].val {
			switch obj := field.Interface().(type) {
			case Reactive:
				return obj.Delete(chain, index+1)
			default:
				return c.errPath("cannot delete from a primitive value")
			}
		}
	}

	return c.errPath(fmt.Sprintf("field %s not found", chain[index].val))
}

func (c *Object[T]) Length(chain chain, index int) int {
	if len(chain) == index {
		c.errPanic("cannot get the length of an object")
	}
	t := reflect.TypeOf(c.obj).Elem()
	val := reflect.ValueOf(c.obj).Elem()

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)
		meta := t.Field(i)
		if getFieldTag(meta.Tag) == chain[index].val {
			switch obj := field.Interface().(type) {
			case Reactive:
				return obj.Length(chain, index+1)
			default:
				c.errPanic("cannot get the length of a primitive value")
			}
		}
	}

	c.errPanic(fmt.Sprintf("field %s not found", chain[index].val))
	return 0
}

func (c *Object[T]) Listen(chain chain, index int, callback func(ListenOp, interface{})) error {
	if len(chain) == index {
		c.errPanic("cannot listen on an object")
	}
	t := reflect.TypeOf(c.obj).Elem()
	val := reflect.ValueOf(c.obj).Elem()

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)
		meta := t.Field(i)
		if getFieldTag(meta.Tag) == chain[index].val {
			switch obj := field.Interface().(type) {
			case Reactive:
				return obj.Listen(chain, index+1, callback)
			default:
				c.listeners[chain.String()] = callback
				return nil
			}
		}
	}

	return c.errPath(fmt.Sprintf("field %s not found", chain[index].val))
}

func (c *Object[T]) SetPath(path string, value interface{}) error {
	chain, err := compilePath(path)
	if err != nil {
		return err
	}
	return c.Set(chain, 0, value)
}

func (c *Object[T]) SetPathf(value interface{}, path string, args ...interface{}) error {
	chain, err := compilePath(fmt.Sprintf(path, args...))
	if err != nil {
		return err
	}
	return c.Set(chain, 0, value)
}

func (c *Object[T]) GetPath(path string) (interface{}, error) {
	chain, err := compilePath(path)
	if err != nil {
		return nil, err
	}
	return c.Get(chain, 0)
}

func (c *Object[T]) GetPathf(path string, args ...interface{}) (interface{}, error) {
	chain, err := compilePath(fmt.Sprintf(path, args...))
	if err != nil {
		return nil, err
	}
	return c.Get(chain, 0)
}

func (c *Object[T]) GetObjectPath(path string) (interface{}, error) {
	chain, err := compilePath(path)
	if err != nil {
		return nil, err
	}
	return c.GetConcrete(chain, 0)
}

func (c *Object[T]) AppendPath(path string) error {
	chain, err := compilePath(path)
	if err != nil {
		return nil
	}
	return c.Append(chain, 0, nil)
}

func (c *Object[T]) AppendPathf(path string, args ...interface{}) error {
	chain, err := compilePath(fmt.Sprintf(path, args...))
	if err != nil {
		return nil
	}
	return c.Append(chain, 0, nil)
}

func (c *Object[T]) DeletePath(path string) error {
	chain, err := compilePath(path)
	if err != nil {
		return nil
	}
	return c.Delete(chain, 0)
}

func (c *Object[T]) DeletePathf(path string, args ...interface{}) error {
	chain, err := compilePath(fmt.Sprintf(path, args...))
	if err != nil {
		return nil
	}
	return c.Delete(chain, 0)
}

func (c *Object[T]) LengthPath(path string) int {
	chain, err := compilePath(path)
	if err != nil {
		return 0
	}
	return c.Length(chain, 0)
}

func (c *Object[T]) ListenPath(path string, callback func(ListenOp, interface{})) error {
	chain, err := compilePath(path)
	if err != nil {
		return nil
	}
	return c.Listen(chain, 0, callback)
}

func compilePath(path string) (chain, error) {
	var chains chain
	regex := regexp.MustCompile(`(\w+)|\[((?:\[[^\]]*\]|[^\]])*)\]`)
	matches := regex.FindAllStringSubmatch(path, -1)
	if len(matches) == 0 {
		return nil, errors.New("invalid path")
	}

	for _, match := range matches {
		if match[1] != "" {
			chains = append(chains, link{match[1], false})
		}
		if match[2] != "" {
			chains = append(chains, link{match[2], true})
		}
	}

	return chains, nil
}

func getFieldTag(tag reflect.StructTag) string {
	var field string
	if field = tag.Get("yaml"); field != "" && field != "-" {
		if strings.Count(field, ",") > 0 {
			field = strings.Split(field, ",")[0]
		}
	} else {
		field = tag.Get("state")
	}
	return field
}

func getRoot(path string) string {
	return strings.Split(path, ".")[0]
}

func getPath(path string) string {
	return strings.Join(strings.Split(path, ".")[1:], ".")
}

func mustCompilePath(path string) chain {
	chain, err := compilePath(path)
	if err != nil {
		panic(fmt.Sprintf("failed to compile path: %v", path))
	}
	return chain
}

func Concrete[T any](object Reactive, path string, args ...interface{}) *T {
	path = fmt.Sprintf(path, args...)
	chain, err := compilePath(path)
	if err != nil {
		panic("invalid concrete path")
	}
	if obj, err := object.GetConcrete(chain, 0); err != nil {
		panic(fmt.Sprintf("invalid concrete access: %s: %v", path, err))
	} else {
		if obj == nil {
			return nil
		}
		switch val := obj.(type) {
		case T:
			return &val
		case *T:
			return val
		case *Object[T]:
			return val.object().(*T)
		default:
			panic(fmt.Sprintf("invalid concrete object type: %s", path))
		}
	}
}
