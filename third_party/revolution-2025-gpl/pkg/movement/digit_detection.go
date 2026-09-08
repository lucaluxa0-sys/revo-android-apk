package movement

import (
	"github.com/nosyliam/revolution/bitmaps"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"github.com/pkg/errors"
	"image"
	"math"
	"slices"
)

var digits = make(map[*image.RGBA]int)

func generateNumber(digits []int) int {
	finalNumber := 0
	for i, digit := range digits {
		finalNumber += digit * int(math.Pow(10, float64(i)))
	}
	return finalNumber
}

// DetectDigits detects the digits inside an image. Returns -1 if no digits were found
func DetectDigits(image *image.RGBA) (int, error) {
	if len(digits) == 0 {
		digits[bitmaps.Registry.Get("digit_zero")] = 0
		digits[bitmaps.Registry.Get("digit_one")] = 1
		digits[bitmaps.Registry.Get("digit_two")] = 2
		digits[bitmaps.Registry.Get("digit_three")] = 3
		digits[bitmaps.Registry.Get("digit_four")] = 4
		digits[bitmaps.Registry.Get("digit_five")] = 5
		digits[bitmaps.Registry.Get("digit_six")] = 6
		digits[bitmaps.Registry.Get("digit_seven")] = 7
		digits[bitmaps.Registry.Get("digit_eight")] = 8
		digits[bitmaps.Registry.Get("digit_nine")] = 9
	}
	var detectedDigits []struct{ x, v int }
	for needle, digit := range digits {
		points, err := revimg.ImageSearch(needle, image,
			&revimg.SearchOptions{
				BoundStart:      &revimg.Point{Y: 22},
				BoundEnd:        &revimg.Point{Y: 38},
				SearchDirection: 8,
				Variation:       0,
			},
		)
		if err != nil {
			return -1, errors.Wrap(err, "failed to perform image search")
		}
		for _, point := range points {
			detectedDigits = append(detectedDigits, struct{ x, v int }{point.X, digit})
		}
	}
	if len(detectedDigits) == 0 {
		return -1, nil
	}
	if len(detectedDigits) == 1 {
		return detectedDigits[0].v, nil
	}
	var sortedDigits []int
	slices.SortFunc(detectedDigits, func(x, y struct{ x, v int }) int { return y.x - x.x })
	for _, d := range detectedDigits {
		sortedDigits = append(sortedDigits, d.v)
	}
	return generateNumber(sortedDigits), nil
}
