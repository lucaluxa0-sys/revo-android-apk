package logging

import (
	"fmt"
	"github.com/nosyliam/revolution/pkg/config"
	"image"
	"os"
	"time"
)

type LogLevel string

const (
	Info    LogLevel = "INFO"
	Warning LogLevel = "WARNING"
	Success LogLevel = "SUCCESS"
	Error   LogLevel = "ERROR"
)

var writer = &logWriter{}

type logWriter struct {
	file *os.File
}

func (l *logWriter) Initialize() error {
	return nil
}

func (l *logWriter) Write(level LogLevel, line string) error {
	line = fmt.Sprintf("[%s] %s", level, line)
	return nil
}

type Logger struct {
	stack     []string
	verbosity int
	settings  *config.Object[config.Settings]
}

func (s *Logger) Child(name string) *Logger {
	return &Logger{stack: append(s.stack, name), settings: s.settings}
}

func (s *Logger) Log(verbosity int, level LogLevel, message string) error {
	fmt.Printf("[%s] %s: %s\n", time.Now().Format("15:04:05"), level, message)
	return nil
}

func (s *Logger) LogDiscord(level LogLevel, message string, id *int, screenshot *image.RGBA) (int, error) {
	fmt.Printf("[%s] %s: %s\n", time.Now().Format("15:04:05"), level, message)
	return 0, nil
}

func NewLogger(name string, settings *config.Object[config.Settings]) *Logger {
	return &Logger{stack: []string{name}, settings: settings}
}
