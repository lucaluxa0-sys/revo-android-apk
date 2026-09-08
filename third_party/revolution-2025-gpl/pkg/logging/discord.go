package logging

import (
	"github.com/nosyliam/revolution/pkg/config"
	"image"
)

var LogColors = map[LogLevel]int{}

func LogDiscord(settings *config.Settings, level LogLevel, message string) error {
	if settings.Discord == nil {
		return nil
	}
	return nil
}

func LogDiscordUpdate(settings *config.Settings, level LogLevel, message string, id *int, screenshot *image.RGBA) (*int, error) {
	if settings.Discord == nil {
		return nil, nil
	}
	return nil, nil
}
