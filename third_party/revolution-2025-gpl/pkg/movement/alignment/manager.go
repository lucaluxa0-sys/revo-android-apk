package alignment

import (
	"fmt"
	"github.com/nosyliam/revolution/opencv"
	"github.com/nosyliam/revolution/pkg/common"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
	"image"
	"image/color"
	"io"
	"net/http"
	"os"
	"slices"
)

var Manager = &manager{}

type Descriptor struct {
	Rows int    `bson:"rows"`
	Cols int    `bson:"cols"`
	Type int    `bson:"type"`
	Data []byte `bson:"data"`
}

type Bitmap struct {
	Name     string `bson:"name"`
	Variance int    `bson:"variance"`
}

type Color struct {
	UpperBound color.RGBA `bson:"upper_bound"`
	LowerBound color.RGBA `bson:"lower_bound"`
	Percentage int        `bson:"percentage"`
	Distance   float64    `bson:"threshold"`
	Variance   float64    `bson:"variance"`
}

type Crop struct {
	X1 float64 `bson:"x1"`
	X2 float64 `bson:"x2"`
	Y1 float64 `bson:"y1"`
	Y2 float64 `bson:"y2"`
}

type Parameters struct {
	OctaveLayers      int     `bson:"octave_layers"`
	ContrastThreshold float64 `bson:"contrast_threshold"`
	EdgeThreshold     float64 `bson:"edge_threshold"`
	Sigma             float64 `bson:"sigma"`
}

func (p *Parameters) SIFT() opencv.SIFT {
	features := 0
	octaveLayers := 1
	if p != nil && p.OctaveLayers != 0 {
		octaveLayers = p.OctaveLayers
	}
	contrastThreshold := 0.01
	if p != nil && p.ContrastThreshold != 0 {
		contrastThreshold = p.ContrastThreshold
	}
	edgeThreshold := float64(20)
	if p != nil && p.EdgeThreshold != 0 {
		edgeThreshold = p.EdgeThreshold
	}
	sigma := 0.5
	if p != nil && p.Sigma != 0 {
		sigma = p.Sigma
	}
	return opencv.NewSIFTWithParams(&features, &octaveLayers, &contrastThreshold, &edgeThreshold, &sigma)
}

type Detector struct {
	Quadrants []int `bson:"quadrants"`

	Descriptor *Descriptor `bson:"descriptor,omitempty"`
	Color      *Color      `bson:"color,omitempty"`
	Bitmap     *Bitmap     `bson:"bitmap,omitempty"`
	Parameters *Parameters `bson:"parameters,omitempty"`

	ZoomLevel int   `bson:"zoom_level"`
	RotPitch  int   `bson:"rot_pitch"` // Up, Down
	RotYaw    int   `bson:"rot_yaw"`   // Left, Right
	Crop      *Crop `bson:"crop,omitempty"`

	HalfWidth  bool `bson:"half_width"`
	MinMatches int  `bson:"min_matches"`

	Mat opencv.Mat
}

type DetectorFile struct {
	Version   string               `bson:"version"`
	Detectors map[string]*Detector `bson:"detectors"`
}

type manager struct {
	version  string
	Detector *DetectorFile
}

func (d *manager) CheckVersion() error {
	resp, err := http.Get("https://raw.githubusercontent.com/nosyliam/revolution/refs/heads/main/pkg/movement/alignment/dataset/version")
	if err != nil {
		return errors.Wrap(err, "failed to download dataset version")
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return errors.Wrap(err, "failed to read dataset version")
	}

	d.version = string(data)
	return nil
}

func (d *manager) Update(load bool) error {
	resp, err := http.Get("https://raw.githubusercontent.com/nosyliam/revolution/refs/heads/main/pkg/movement/alignment/dataset/detectors.bin")
	if err != nil {
		return errors.Wrap(err, "failed to download dataset")
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return errors.Errorf("Failed to download dataset: HTTP status %s", resp.Status)
	}

	fmt.Println("downloaded new dataset")

	file, err := os.Create("detectors.bin")
	if err != nil {
		return errors.Wrap(err, "failed to create dataset file")
	}
	defer file.Close()

	_, err = io.Copy(file, resp.Body)
	if err != nil {
		return errors.Wrap(err, "failed to write to dataset file")
	}

	if load {
		return d.Load(load)
	}
	return nil
}

func (d *manager) Load(load bool) error {
	if _, err := os.Stat("detectors.bin"); os.IsNotExist(err) {
		return d.Update(load)
	}

	if err := d.CheckVersion(); err != nil {
		return errors.New("failed to check for new version")
	}

	fileData, err := os.ReadFile("detectors.bin")
	if err != nil {
		return errors.Wrap(err, "failed to read dataset file")
	}

	d.Detector = &DetectorFile{}
	err = bson.Unmarshal(fileData, d.Detector)
	if err != nil {
		d.Detector = nil
		return errors.Wrap(err, "failed to unmarshal dataset file")
	}

	if d.Detector.Version != d.version {
		if load {
			if err := d.Update(false); err != nil {
				return errors.Wrap(err, "failed to update detection dataset")
			}
		}
	}

	for name, detector := range d.Detector.Detectors {
		if detector.Color == nil && detector.Bitmap == nil {
			mat, err := opencv.NewMatFromBytes(detector.Descriptor.Rows, detector.Descriptor.Cols, opencv.MatType(detector.Descriptor.Type), detector.Descriptor.Data)
			if err != nil {
				return errors.Wrap(err, fmt.Sprintf("failed to map descriptor for detector %s", name))
			}
			detector.Mat = mat
			fmt.Println("loaded", name)
		}
	}

	return nil
}

func (d *manager) PerformDetection(macro *common.Macro, name string) (bool, error) {
	detector, ok := d.Detector.Detectors[name]
	if !ok {
		return false, errors.Errorf("detector \"%s\" not found", name)
	}
	if detector.Bitmap == nil {
		zoom, pitch, yaw := macro.Input.Zoom(), macro.Input.Pitch(), macro.Input.Yaw()
		macro.Input.SetZoom(detector.ZoomLevel)
		macro.Input.SetPitch(detector.RotPitch)
		macro.Input.SetYaw(detector.RotYaw)
		defer func() {
			macro.Input.SetZoom(zoom)
			macro.Input.SetPitch(pitch)
			macro.Input.SetYaw(yaw)
		}()
		macro.Input.Sleep(100)
	}
	frame := <-macro.Scheduler.RequestFrame()
	if frame == nil {
		return false, nil
	}
	x1, y1, x2, y2 := 0, 0, frame.Bounds().Dx(), frame.Bounds().Dy()
	switch {
	case slices.Compare(detector.Quadrants, []int{0, 1, 2, 3}) == 0:
		break
	case slices.Compare(detector.Quadrants, []int{0, 1}) == 0:
		y2 /= 2
	case slices.Compare(detector.Quadrants, []int{2, 3}) == 0:
		y1 = y2 / 2
	case slices.Compare(detector.Quadrants, []int{0, 2}) == 0:
		x2 /= 2
	case slices.Compare(detector.Quadrants, []int{1, 3}) == 0:
		x1 = x2 / 2
	case slices.Equal(detector.Quadrants, []int{0}):
		x2, y2 = x2/2, y2/2
	case slices.Equal(detector.Quadrants, []int{1}):
		x1 = x2 / 2
		y2 /= 2
	case slices.Equal(detector.Quadrants, []int{2}):
		y1 = y2 / 2
		x2 /= 2
	case slices.Equal(detector.Quadrants, []int{3}):
		x1, y1 = x2/2, y2/2
	default:
		return false, errors.New("unsupported quadrants")
	}
	hotbarX, hotbarY := macro.MacroState.Object().HotbarOriginX, macro.MacroState.Object().HotbarOriginY
	honeyX, honeyY := macro.MacroState.Object().HoneyOriginX, macro.MacroState.Object().HoneyOriginY
	revimg.ClearRGBA(frame, image.Rect(hotbarX-13, hotbarY-106, hotbarX+680, hotbarY+40))
	revimg.ClearRGBA(frame, image.Rect(honeyX-15, honeyY-20, honeyX+600, honeyY+30))
	cropped := revimg.CropRGBA(frame, image.Rect(x1, y1, x2, y2))
	cropped = CropImage(cropped, detector.Crop)
	if detector.Bitmap != nil {
		return DetectImage(cropped, detector), nil
	}
	mat, err := opencv.NewMatFromBytes(cropped.Bounds().Dy(), cropped.Bounds().Dx(), opencv.MatTypeCV8UC4, cropped.Pix)
	if err != nil || mat.Empty() {
		return false, errors.Wrap(err, "failed to map image")
	}
	defer mat.Close()

	if detector.Color != nil {
		return DetectColor(mat, detector), nil
	} else {
		grayImg := opencv.NewMat()
		defer grayImg.Close()
		opencv.CvtColor(mat, &grayImg, opencv.ColorRGBAToGray)
		return DetectObject(grayImg, detector), nil
	}
}
