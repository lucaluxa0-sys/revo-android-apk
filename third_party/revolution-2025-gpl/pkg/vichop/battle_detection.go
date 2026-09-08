package vichop

import (
	"fmt"
	"github.com/nosyliam/revolution/bitmaps"
	"github.com/nosyliam/revolution/pkg/common"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"image/color"
	"math"
)

type StatusDetector struct {
	manager *Manager
	macro   *common.Macro
	active  bool
}

func NewStatusDetector(manager *Manager, macro *common.Macro) *StatusDetector {
	return &StatusDetector{
		manager: manager,
		macro:   macro,
	}
}

func (s *StatusDetector) Tick() {
	screenshot := s.macro.GetWindow().Screenshot()
	if screenshot == nil {
		return
	}
	width, height := screenshot.Bounds().Dx(), screenshot.Bounds().Dy()

	// To detect Vicious bee attacking events, we'll use a heuristic method which involves
	// detecting the message's black background color up to an exact height, as well as the color of the
	// red text for at least 100 pixels. For defeated events, we can use template matching
	if s.active {
		for _, variant := range []string{"vicdefeated", "giftedvicdefeated"} {
			result, err := revimg.ImageSearch(bitmaps.Registry.Get(variant), screenshot, &revimg.SearchOptions{
				BoundStart: &revimg.Point{X: width - 355, Y: height - 200},
				BoundEnd:   &revimg.Point{X: width - 16},
				Variation:  1,
			})
			if err != nil {
				panic(err)
			}
			if len(result) > 0 {
				fmt.Println("Vicious bee defeated!")
				s.active = false
			}
		}
		return
	}

	scanLine := func(x int, req *color.RGBA) (int, *color.RGBA) {
		var boxScan = 0
		var boxDetected = false
		var boxColor *color.RGBA
		var boxY = 0
		for y := height; y > height-100; y-- {
			if !boxDetected {
				rgba := screenshot.RGBAAt(x, y)
				if boxColor != nil && (rgba.R == boxColor.R || rgba.G == boxColor.G || rgba.B == boxColor.B) {
					boxScan++
				} else if req == nil && rgba.R <= 14 && rgba.G <= 14 && rgba.B <= 14 && rgba.A == 255 {
					boxScan = 1
					boxY = y
					boxColor = &rgba
				} else if req != nil && rgba.R == req.R && rgba.G == req.G && rgba.B == req.B {
					boxScan = 1
					boxY = y
					boxColor = req
				} else {
					boxScan = 0
					boxColor = nil
				}
				if boxScan == 20 {
					boxDetected = true
					break
				}
			}
		}
		if !boxDetected {
			boxY = -1
		}
		return boxY, boxColor
	}

	// Start from the middle and expand search outwards (we'll only search for 150 pixels)
	var boxDetected = false
	var boxY = 0
	for i := 1; i < 150; i++ {
		var dir = -1
		if i%2 == 0 {
			dir = 1
		}
		x := width - 186 - (int(math.Floor(float64(i/2))) * dir)

		if y, clr := scanLine(x, nil); y != -1 {
			lScan, _ := scanLine(x-1, clr)
			rScan, _ := scanLine(x+1, clr)
			if lScan != -1 && rScan != -1 {
				boxY = y
				boxDetected = true
			}
		}

		if boxDetected {
			var redPixels = 0
			for bI := 1; i < 250; i++ {
				var bDir = -1
				if i%2 == 0 {
					bDir = 1
				}
				bX := width - 186 - (int(math.Floor(float64(bI/2))) * bDir)
				for y := boxY; y > boxY-20; y-- {
					rgba := screenshot.RGBAAt(bX, y)
					if rgba.R > 200 && rgba.G < 30 && rgba.B < 30 {
						redPixels++
					}
				}
			}
			if redPixels > 200 {
				//img := revimg.CropRGBA(screenshot, image.Rect(width-400, boxY-21, width, boxY))
				fmt.Println("Vicious bee attack detected", redPixels)
				/*f, _ := os.Create("night.png")
				png.Encode(f, img)
				f.Close()*/
				s.active = true
				return
			}
		}
	}
}

func StartDetectingBattle(macro *common.Macro) {
	macro.Root.VicHop.BattleDetect(macro)
}

func StopDetectingBattle(macro *common.Macro) {
	macro.Root.VicHop.StopBattleDetect(macro)
}

func BattleActive(macro *common.Macro) bool {
	return macro.Root.VicHop.BattleActive(macro)
}

func ReadQueue(macro *common.Macro) {
	macro.Root.VicHop.ReadQueue(macro)
}
