package main

import (
	"embed"
	"flag"
	"github.com/getsentry/sentry-go"
	"github.com/nosyliam/revolution/platform"
	"github.com/pkg/errors"
	"github.com/sqweek/dialog"
	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
	"github.com/wailsapp/wails/v2/pkg/options/mac"
	"github.com/wailsapp/wails/v2/pkg/options/windows"
	"log"
	"os"
	"runtime"
	"runtime/pprof"
)

//go:embed all:frontend/dist
var assets embed.FS

var cpuprofile = flag.String("cpuprofile", "", "write cpu profile to file")

func main() {
	err := sentry.Init(sentry.ClientOptions{
		Dsn:              "https://645d28ea8dd7113dad0aace50f276f16@o4508651129536512.ingest.us.sentry.io/4508651131764736",
		TracesSampleRate: 0.5,
	})
	if err != nil {
		log.Fatalf("sentry.Init: %s", err)
	}

	flag.Parse()
	if *cpuprofile != "" {
		f, err := os.Create(*cpuprofile)
		if err != nil {
			log.Fatal(err)
		}
		pprof.StartCPUProfile(f)
		defer pprof.StopCPUProfile()
	}

	app := NewMacro(platform.WindowBackend, platform.ControlBackend)

	var height = 400
	var width = 600
	if runtime.GOOS == "windows" {
		height += 11
		width += 12
	}
	backdrop := windows.Acrylic
	if determineOs() == "windows11" {
		backdrop = windows.Mica
	}

	if err := wails.Run(&options.App{
		Title:         "Revolution Macro",
		Width:         width,
		Height:        height,
		DisableResize: true,
		AssetServer: &assetserver.Options{
			Assets: assets,
		},
		BackgroundColour: &options.RGBA{R: 210, G: 211, B: 214, A: 0},
		OnStartup:        app.startup,
		Bind: []interface{}{
			app,
		},
		AlwaysOnTop: true,
		Mac: &mac.Options{
			TitleBar: &mac.TitleBar{
				TitlebarAppearsTransparent: false,
				HideTitle:                  false,
				HideTitleBar:               false,
				FullSizeContent:            true,
				UseToolbar:                 false,
				HideToolbarSeparator:       true,
			},
			WebviewIsTransparent: true,
			WindowIsTranslucent:  true,
		},
		Windows: &windows.Options{
			WebviewIsTransparent: true,
			WindowIsTranslucent:  backdrop == windows.Mica,
			BackdropType:         backdrop,
			Theme:                windows.SystemDefault,
		},
	}); err != nil {
		dialog.Message(errors.Wrap(err, "Failed to run application").Error()).Error()
		return
	}
}

/*func init() {
	syscall.NewLazyDLL("kernel32.dll").NewProc("AllocConsole").Call()
	stdoutHandle, _ := syscall.GetStdHandle(syscall.STD_OUTPUT_HANDLE)
	stderrHandle, _ := syscall.GetStdHandle(syscall.STD_ERROR_HANDLE)

	os.Stdout = os.NewFile(uintptr(stdoutHandle), "/dev/stdout")
	os.Stderr = os.NewFile(uintptr(stderrHandle), "/dev/stderr")
}*/
