package movement

import (
	"bytes"
	_ "embed"
	"github.com/nosyliam/revolution/patterns"
	"github.com/yuin/gopher-lua/parse"
	"io/fs"
)

var embeddedPatterns = make(map[string]embeddedPattern)

type embeddedPattern struct {
	Version int
	Path    string
	Data    []byte
}

func init() {
	_ = fs.WalkDir(patterns.PatternFs, ".", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		if !d.IsDir() {
			content, _ := patterns.PatternFs.ReadFile(path)
			chunk, _ := parse.Parse(bytes.NewReader(content), path)
			metadata, name, _ := NewMetadataFromStatementList(chunk)
			embeddedPatterns[name] = embeddedPattern{Version: metadata.Version, Path: path, Data: content}
		}

		return nil
	})
}
