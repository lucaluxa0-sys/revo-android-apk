package actions

import (
	"fmt"
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/logging"
	"github.com/pkg/errors"
	"image"
)

type LogModifier int

const (
	Status LogModifier = iota
	Discord
	Screenshot
)

func execArgs(macro *common.Macro, args []interface{}) []interface{} {
	var res []interface{}
	for _, arg := range args {
		switch fn := arg.(type) {
		case func(macro *common.Macro) error:
			res = append(res, fn(macro).Error())
		case func(macro *common.Macro) int:
			res = append(res, fn(macro))
		case func(macro *common.Macro) bool:
			res = append(res, fn(macro))
		case func(macro *common.Macro) string:
			res = append(res, fn(macro))
		case func(macro *common.Macro) interface{}:
			res = append(res, fn(macro))
		case func() interface{}:
			res = append(res, fn())
		case func() error:
			res = append(res, fn().Error())
		case common.Action:
			res = append(res, fn.Execute(macro).Error())
		default:
			res = append(res, fn)
		}
	}
	return res
}

type LogAction struct {
	log       string
	level     logging.LogLevel
	discord   bool
	status    bool
	verbosity int
	args      []interface{}
	id        *int
}

func (a *LogAction) Execute(macro *common.Macro) error {
	msg := fmt.Sprintf(a.log, execArgs(macro, a.args)...)
	if a.status {
		macro.Status(msg)
	}
	if err := macro.Logger.Log(a.verbosity, a.level, msg); err != nil {
		return errors.Wrap(err, "failed to log")
	}
	if a.discord {
		var screenshot *image.RGBA
		if macro.Results.EditedScreenshot != nil {
			screenshot = macro.Results.EditedScreenshot
		} else if macro.Window != nil && macro.Window.Screenshot() != nil {
			screenshot = macro.Window.Screenshot()
		}
		if id, err := macro.Logger.LogDiscord(a.level, msg, a.id, screenshot); err != nil {
			return err
		} else {
			a.id = &id
		}
	}
	return nil
}

func (a *LogAction) Status() *LogAction {
	a.status = true
	return a
}

func (a *LogAction) Discord() *LogAction {
	a.discord = true
	return a
}

func (a *LogAction) V(verbosity int) *LogAction {
	a.verbosity = verbosity
	return &LogAction{verbosity: verbosity, level: a.level, log: a.log}
}

func (a *LogAction) applyLogModifiers(modifiers []LogModifier) *LogAction {
	for _, modifier := range modifiers {
		switch modifier {
		case Status:
			a.status = true
		case Discord:
			a.discord = true
		}
	}
	return a
}

func Error(log string, args ...interface{}) func(...LogModifier) *LogAction {
	return func(mods ...LogModifier) *LogAction {
		return (&LogAction{level: logging.Error, log: log, args: args}).applyLogModifiers(mods)
	}
}

func Info(log string, args ...interface{}) func(...LogModifier) *LogAction {
	return func(mods ...LogModifier) *LogAction {
		return (&LogAction{level: logging.Info, log: log, args: args}).applyLogModifiers(mods)
	}
}

func Warning(log string, args ...interface{}) func(...LogModifier) *LogAction {
	return func(mods ...LogModifier) *LogAction {
		return (&LogAction{level: logging.Warning, log: log, args: args}).applyLogModifiers(mods)
	}
}
