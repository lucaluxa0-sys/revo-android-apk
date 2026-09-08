package logging

import (
	"context"
	"github.com/fatih/color"
	"github.com/wailsapp/wails/v2/pkg/runtime"
)

func Console(ctx context.Context, level LogLevel, text string) {
	switch level {
	case Info:
		runtime.EventsEmit(ctx, "console", text)
	case Warning:
		runtime.EventsEmit(ctx, "console", color.YellowString(text))
	case Error:
		runtime.EventsEmit(ctx, "console", color.RedString(text))
	case Success:
		runtime.EventsEmit(ctx, "console", color.GreenString(text))
	}
}
