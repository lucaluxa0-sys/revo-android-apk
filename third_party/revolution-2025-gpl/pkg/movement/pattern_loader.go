package movement

import (
	"bytes"
	"context"
	"fmt"
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/config"
	"github.com/pkg/errors"
	"github.com/sqweek/dialog"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"sync"

	"github.com/fsnotify/fsnotify"
	"github.com/yuin/gopher-lua"
	"github.com/yuin/gopher-lua/ast"
	"github.com/yuin/gopher-lua/parse"
)

func NewMetadataFromStatementList(stmts []ast.Stmt) (*config.PatternMetadata, string, error) {
	name := "INVALID"
	meta := config.PatternMetadata{
		AutoUpdate:   true,
		ReturnMethod: "reset",
	}
	value := reflect.ValueOf(meta)
	for _, stmt := range stmts {
		if n, ok := stmt.(*ast.FuncCallStmt); ok {
			if fc, ok := n.Expr.(*ast.FuncCallExpr); ok {
				if fn, ok := fc.Func.(*ast.IdentExpr); ok {
					if fn.Value == "DisableAutoUpdate" {
						meta.AutoUpdate = false
						continue
					}
					if fn.Value == "SetName" {
						if expr, ok := fc.Args[0].(*ast.StringExpr); ok {
							name = expr.Value
						} else {
							return nil, "", errors.New("invalid argument for metadata call \"SetName\"")
						}
						continue
					}
					field := value.FieldByName(strings.TrimPrefix(fn.Value, "Set"))
					if !field.IsValid() {
						continue
					}
					switch field.Type().Kind() {
					case reflect.String:
						if expr, ok := fc.Args[0].(*ast.StringExpr); ok {
							field.SetString(expr.Value)
						} else {
							return nil, "", errors.New(fmt.Sprintf("invalid argument for metadata call \"%s\"", fn.Value))
						}
					case reflect.Bool:
						switch fc.Args[0].(type) {
						case *ast.TrueExpr:
							field.SetBool(true)
						case *ast.FalseExpr:
							field.SetBool(false)
						default:
							return nil, "", errors.New(fmt.Sprintf("invalid argument for metadata call \"%s\"", fn.Value))
						}
					case reflect.Int:
						if expr, ok := fc.Args[0].(*ast.NumberExpr); ok {
							val, _ := strconv.Atoi(expr.Value)
							field.SetInt(int64(val))
						} else {
							return nil, "", errors.New(fmt.Sprintf("invalid argument for metadata call \"%s\"", fn.Value))
						}
					}
				}
			}
		}
	}
	return &meta, name, nil
}

type Pattern struct {
	Name  string
	Meta  *config.PatternMetadata
	Proto *lua.FunctionProto
	Path  string
}

type Loader struct {
	watcher  *fsnotify.Watcher
	ctx      context.Context
	cancel   context.CancelFunc
	mu       sync.RWMutex
	patterns map[string]*Pattern
}

func NewLoader() *Loader {
	w, _ := fsnotify.NewWatcher()
	ctx, cancel := context.WithCancel(context.Background())
	return &Loader{watcher: w, ctx: ctx, cancel: cancel, patterns: make(map[string]*Pattern)}
}

func (l *Loader) Patterns() []string {
	l.mu.Lock()
	defer l.mu.Unlock()
	var names []string
	for name := range l.patterns {
		names = append(names, name)
	}
	return names
}

func (l *Loader) Exists(patternName string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	_, ok := l.patterns[patternName]
	return ok
}

func (l *Loader) Execute(macro *common.Macro, meta *config.PatternMetadata, patternName string) error {
	l.mu.Lock()
	pattern, ok := l.patterns[patternName]
	l.mu.Unlock()
	if !ok {
		return errors.Errorf("no such pattern: %s", patternName)
	}
	if meta == nil {
		meta = pattern.Meta
	}
	ExecutePattern(pattern, meta, macro)
	return nil
}

func (l *Loader) Start() error {
	os.MkdirAll("patterns", 0755)
	os.MkdirAll("patterns/misc", 0755)
	os.MkdirAll("patterns/edges", 0755)
	err := l.watcher.Add("patterns")
	if err != nil {
		return err
	}
	err = l.watcher.Add("patterns/misc")
	if err != nil {
		return err
	}
	err = l.watcher.Add("patterns/edges")
	if err != nil {
		return err
	}
	err = filepath.Walk("patterns", func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() {
			l.handleFileChange(path)
		}
		return nil
	})
	if err != nil {
		return err
	}
	for name, data := range embeddedPatterns {
		if pattern, ok := l.patterns[name]; ok {
			if pattern.Meta.AutoUpdate && pattern.Meta.Version < data.Version {
				file, err := os.OpenFile(filepath.Join("patterns", data.Path), os.O_WRONLY|os.O_TRUNC, 0644)
				if err != nil {
					return errors.New(fmt.Sprintf("failed to open pattern for auto-update: %s", data.Path))
				}
				_, err = file.Write(data.Data)
				if err != nil {
					return errors.New(fmt.Sprintf("failed to write embedded pattern for auto-update: %s", data.Path))
				}
				l.handleFileChange(data.Path)
			}
		} else {
			file, err := os.Create(filepath.Join("patterns", data.Path))
			if err != nil {
				return errors.New(fmt.Sprintf("failed to create embedded pattern: %s", data.Path))
			}
			_, err = file.Write(data.Data)
			if err != nil {
				return errors.New(fmt.Sprintf("failed to write embedded pattern: %s", data.Path))
			}
			_ = file.Close()
			l.handleFileChange(data.Path)
		}
	}
	go l.run()
	return nil
}

func (l *Loader) run() {
	for {
		select {
		case event, ok := <-l.watcher.Events:
			if !ok {
				return
			}
			if event.Op&fsnotify.Write == fsnotify.Write || event.Op&fsnotify.Create == fsnotify.Create {
				l.handleFileChange(event.Name)
			}
		case <-l.ctx.Done():
			return
		}
	}
}

func (l *Loader) handleFileChange(path string) {
	if filepath.Ext(path) != ".lua" {
		return
	}
	fmt.Println("Loading new pattern at", path)
	fi, err := os.Stat(path)
	if err != nil || fi.IsDir() {
		return
	}
	if strings.HasSuffix(strings.ToLower(filepath.Ext(path)), ".lua") {
		data, err := os.ReadFile(path)
		if err != nil {
			return
		}
		chunk, err := parse.Parse(bytes.NewReader(data), path)
		if err != nil {
			dialog.Message(fmt.Sprintf("Failed to parse Lua pattern at %s: %v", path, err)).Error()
			return
		}
		metadata, name, err := NewMetadataFromStatementList(chunk)
		if err != nil {
			dialog.Message(fmt.Sprintf("Failed to extract metadata from Lua pattern at %s: %v", path, err)).Error()
			return
		}
		proto, err := lua.Compile(chunk, path)
		if err != nil {
			dialog.Message(fmt.Sprintf("Failed to compile Lua pattern at %s: %v", path, err)).Error()
			return
		}
		l.mu.Lock()
		l.patterns[name] = &Pattern{
			Meta:  metadata,
			Proto: proto,
			Path:  path,
		}
		l.mu.Unlock()
	}
}

func (l *Loader) Retrieve(pattern string) (*Pattern, error) {
	p, ok := l.patterns[pattern]
	if !ok {
		return nil, fmt.Errorf("pattern not found: %s", pattern)
	}
	return p, nil
}

func (l *Loader) Close() error {
	l.cancel()
	return l.watcher.Close()
}
