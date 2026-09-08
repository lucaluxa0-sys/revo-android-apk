package alignment

import (
	"fmt"
	"github.com/nosyliam/revolution/bitmaps"
	"github.com/nosyliam/revolution/opencv"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"image"
	"math"
)

func CropImage(img *image.RGBA, crop *Crop) *image.RGBA {
	if crop == nil {
		return img
	}
	bounds := img.Bounds()
	x1, y1, x2, y2 := crop.X1, crop.Y1, crop.X2, crop.Y2
	if x2 == 0 {
		x2 = 1
	}
	if y2 == 0 {
		y2 = 1
	}
	x1 *= float64(bounds.Dx())
	y1 *= float64(bounds.Dy())
	x2 *= float64(bounds.Dx())
	y2 *= float64(bounds.Dy())
	return revimg.CropRGBA(img, image.Rect(int(x1), int(y1), int(x2), int(y2)))
}

func DetectImage(image *image.RGBA, detector *Detector) bool {
	points, err := revimg.ImageSearch(bitmaps.Registry.Get(detector.Bitmap.Name), image, &revimg.SearchOptions{
		Variation: detector.Bitmap.Variance,
	})
	return err == nil && len(points) != 0
}

func DetectObject(mat opencv.Mat, detector *Detector) bool {
	sift := detector.Parameters.SIFT()
	defer sift.Close()

	_, sceneDescriptors := sift.DetectAndCompute(mat, opencv.NewMat())
	defer sceneDescriptors.Close()

	matcher := opencv.NewBFMatcher()
	defer matcher.Close()

	matches := matcher.KnnMatch(detector.Mat, sceneDescriptors, 2)

	var goodMatches []opencv.DMatch
	for _, m := range matches {
		if len(m) >= 2 {
			if m[0].Distance < 0.7*m[1].Distance {
				goodMatches = append(goodMatches, m[0])
			}
		}
	}

	fmt.Printf("Total matches: %d, Good matches: %d\n", len(matches), len(goodMatches))
	// opencv.IMWrite("detector.png", mat)
	return len(goodMatches) >= detector.MinMatches
}

func DetectColor(mat opencv.Mat, detector *Detector) bool {
	totalPixels := float64(mat.Rows() * mat.Cols())
	inRangePixels := 0
	outOfRangeDistances := make([]float64, 0)
	opencv.IMWrite("detector.png", mat)

	for y := 0; y < mat.Rows(); y++ {
		for x := 0; x < mat.Cols(); x++ {
			pixel := mat.GetVecbAt(y, x)

			if pixel[0] >= detector.Color.LowerBound.B && pixel[0] <= detector.Color.UpperBound.B &&
				pixel[1] >= detector.Color.LowerBound.G && pixel[1] <= detector.Color.UpperBound.G &&
				pixel[2] >= detector.Color.LowerBound.R && pixel[2] <= detector.Color.UpperBound.R {
				inRangePixels++
			} else {
				blue := clamp(float64(pixel[0]), float64(detector.Color.LowerBound.B), float64(detector.Color.UpperBound.B))
				green := clamp(float64(pixel[1]), float64(detector.Color.LowerBound.G), float64(detector.Color.UpperBound.G))
				red := clamp(float64(pixel[2]), float64(detector.Color.LowerBound.R), float64(detector.Color.UpperBound.R))
				dist := math.Sqrt(
					math.Pow(float64(pixel[0])-blue, 2) +
						math.Pow(float64(pixel[1])-green, 2) +
						math.Pow(float64(pixel[2])-red, 2),
				)
				outOfRangeDistances = append(outOfRangeDistances, dist)
			}
		}
	}

	inRangePercentage := (float64(inRangePixels) / totalPixels) * 100

	var meanDistance, variance float64
	if len(outOfRangeDistances) > 0 {
		sum := 0.0
		for _, val := range outOfRangeDistances {
			sum += val
		}
		meanDistance = sum / float64(len(outOfRangeDistances))

		sumOfSquares := 0.0
		for _, val := range outOfRangeDistances {
			sumOfSquares += math.Pow(val-meanDistance, 2)
		}
		variance = sumOfSquares / float64(len(outOfRangeDistances))
	}

	fmt.Printf("Percentage of Pixels in Range: %.2f%%\n", inRangePercentage)
	fmt.Printf("Mean Distance of Out-of-Range Pixels: %.2f\n", meanDistance)
	fmt.Printf("Variance of Out-of-Range Distances: %.2f\n", variance)

	if int(inRangePercentage) > detector.Color.Percentage || (meanDistance < detector.Color.Variance && variance < detector.Color.Variance) {
		fmt.Println("Image is uniform within the specified color range.")
		return true
	} else {
		fmt.Println("Image is NOT uniform within the specified color range.")
		return false
	}
}

// Clamp a value between min and max
func clamp(value, min, max float64) float64 {
	if value < min {
		return min
	}
	if value > max {
		return max
	}
	return value
}
