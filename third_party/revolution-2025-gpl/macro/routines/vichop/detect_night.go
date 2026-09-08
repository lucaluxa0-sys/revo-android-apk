package vichop

import (
	"fmt"
	"github.com/nosyliam/revolution/opencv"
	. "github.com/nosyliam/revolution/pkg/common"
	. "github.com/nosyliam/revolution/pkg/control/actions"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"image"
)

const DetectNightRoutineKind RoutineKind = "detect-night"

func calcAverage(hist opencv.Mat, totalPixels float32) float32 {
	sum := float32(0)
	for i := 0; i < hist.Rows(); i++ {
		sum += float32(i) * hist.GetFloatAt(i, 0)
	}
	return sum / totalPixels
}

func detectNight(macro *Macro) bool {
	screenshot := macro.GetWindow().Screenshot()
	offsetX, offsetY := macro.MacroState.Object().HoneyOriginX, macro.MacroState.Object().BaseOriginY
	cropped := revimg.CropRGBA(screenshot, image.Rect(offsetX, offsetY+1, offsetX+50, offsetY+19))

	// Perform a histogram calculation to determine the average color intensity
	mat, err := opencv.NewMatFromBytes(cropped.Bounds().Dy(), cropped.Bounds().Dx(), opencv.MatTypeCV8UC4, cropped.Pix)
	if err != nil {
		macro.Action(Error("Failed to map night detection image!")(Discord))
		return false
	}
	defer mat.Close()

	channels := opencv.Split(mat)

	histSize := []int{256}
	ranges := []float64{0, 256}

	blueHist := opencv.NewMat()
	greenHist := opencv.NewMat()
	redHist := opencv.NewMat()
	defer blueHist.Close()
	defer greenHist.Close()
	defer redHist.Close()

	opencv.CalcHist([]opencv.Mat{channels[0]}, []int{0}, opencv.NewMat(), &blueHist, histSize, ranges, false)
	opencv.CalcHist([]opencv.Mat{channels[1]}, []int{0}, opencv.NewMat(), &greenHist, histSize, ranges, false)
	opencv.CalcHist([]opencv.Mat{channels[2]}, []int{0}, opencv.NewMat(), &redHist, histSize, ranges, false)

	totalPixels := float32(mat.Rows() * mat.Cols())

	blueAvg := calcAverage(blueHist, totalPixels)
	greenAvg := calcAverage(greenHist, totalPixels)
	redAvg := calcAverage(redHist, totalPixels)

	fmt.Println("Color averages", blueAvg, greenAvg, redAvg)
	if blueAvg < 50 && greenAvg < 50 && redAvg < 50 {
		return true
	}
	return false
}

var DetectNightRoutine = Actions{
	Info("Detecting Night")(Status),
	Set(NightDetected, false),
	Loop(
		For(4),
		KeyDown(ZoomIn),
		KeyUp(ZoomIn),
	),
	Loop(
		For(2),
		KeyDown(ZoomOut),
		KeyUp(ZoomOut),
	),
	Loop(
		For(2),
		KeyDown(RotDown),
		KeyUp(RotDown),
	),
	// Allow new frame to be processed
	Sleep(200),
	Condition(
		If(True(detectNight)),
		Info("Night Detected")(Status, Discord),
		Set(NightDetected, true),
		Loop(
			For(2),
			KeyPress(RotUp),
		),
	),
}

func init() {
	DetectNightRoutine.Register(DetectNightRoutineKind)
}
