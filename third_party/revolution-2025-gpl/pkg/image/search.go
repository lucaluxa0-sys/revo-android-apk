package image

/*
 * Copyright (c) 2024
 * Author: Liam Sagi
 */

// #include "search.h"
import "C"

import (
	"github.com/pkg/errors"
	"image"
	"image/color"
	"unsafe"
)

func HexToRGBA(hex uint32) color.RGBA {
	return color.RGBA{
		R: uint8((hex >> 16) & 0xFF),
		G: uint8((hex >> 8) & 0xFF),
		B: uint8(hex & 0xFF),
		A: 0xFF,
	}
}

func CropRGBA(src *image.RGBA, rect image.Rectangle) *image.RGBA {
	dstRect := image.Rect(0, 0, rect.Dx(), rect.Dy())

	cropped := image.NewRGBA(dstRect)

	for y := rect.Min.Y; y < rect.Max.Y; y++ {
		for x := rect.Min.X; x < rect.Max.X; x++ {
			offsetSrc := src.PixOffset(x, y)
			// Now (x - rect.Min.X, y - rect.Min.Y) is correct since cropped’s Min is (0,0).
			offsetDst := cropped.PixOffset(x-rect.Min.X, y-rect.Min.Y)

			copy(
				cropped.Pix[offsetDst:offsetDst+4],
				src.Pix[offsetSrc:offsetSrc+4],
			)
		}
	}

	return cropped
}

func ClearRGBA(img *image.RGBA, rect image.Rectangle) {
	rect = rect.Intersect(img.Bounds())

	for y := rect.Min.Y; y < rect.Max.Y; y++ {
		for x := rect.Min.X; x < rect.Max.X; x++ {
			img.SetRGBA(x, y, color.RGBA{R: 255, G: 255, B: 255})
		}
	}
}

type Point struct {
	X int
	Y int
}

type Frame struct {
	X      int
	Y      int
	Width  int
	Height int
}

func (f *Frame) Equals(other Frame) bool {
	return f.X == other.X && f.Y == other.Y && f.Width == other.Width && f.Height == other.Height
}

type ScreenFrame struct {
	Frame
	Scale float32
}

type SearchOptions struct {
	BoundStart      *Point
	BoundEnd        *Point
	SearchDirection int
	Variation       int
	Instances       int
}

func ImageSearch(needle *image.RGBA, haystack *image.RGBA, options *SearchOptions) ([]Point, error) {
	if needle == nil || haystack == nil {
		return nil, errors.New("image needle or haystack nil")
	}
	if options == nil {
		options = &SearchOptions{}
	}

	if options.Variation > 255 || options.Variation < 0 {
		return nil, errors.New("invalid variation")
	}

	hScan := &haystack.Pix[0]
	nScan := &needle.Pix[0]

	direction := options.SearchDirection
	if direction == 0 {
		direction = 1
	}
	instances := options.Instances
	if instances == 0 {
		instances = 1
	}

	var outerX1, outerY1, outerX2, outerY2 int
	if options.BoundStart != nil {
		outerX1, outerY1 = options.BoundStart.X, options.BoundStart.Y
	}

	if options.BoundEnd != nil {
		outerX2, outerY2 = options.BoundEnd.X, options.BoundEnd.Y
	}

	hBounds, nBounds := haystack.Bounds(), needle.Bounds()
	if outerX2 == 0 {
		outerX2 = hBounds.Dx() - nBounds.Dx() + 1
	} else {
		outerX2 = outerX2 - nBounds.Dx() + 1
	}

	if outerY2 == 0 {
		outerY2 = hBounds.Dy() - nBounds.Dy() + 1
	} else {
		outerY2 = outerY2 - nBounds.Dy() + 1
	}

	innerX1, innerY1 := outerX1, outerY1
	innerX2, innerY2 := outerX2, outerY2

	update := func(x, y string, z int, value int) {
		if x == "inner" {
			if y == "X" {
				if z == 1 {
					innerX1 = value
				} else {
					innerX2 = value
				}
			} else {
				if z == 1 {
					innerY1 = value
				} else {
					innerY2 = value
				}
			}
		} else {
			if y == "X" {
				if z == 1 {
					outerX1 = value
				} else {
					outerX2 = value
				}
			} else {
				if z == 1 {
					innerY1 = value
				} else {
					innerY2 = value
				}
			}
		}
	}

	var outputs = make([]Point, 0)
	iX, stepX, iY, stepY, outputCount := 1, 1, 1, 1, 0
	mod := direction % 4
	if mod > 1 {
		iY, stepY = 2, 0
	}
	if mod%3 == 0 {
		iX, stepX = 2, 0
	}
	P, N, iP, iN := "Y", "X", 0, 0
	if direction > 4 {
		P, N = "X", "Y"
	}
	if P == "X" {
		iP = iX
	} else {
		iP = iY
	}
	if N == "X" {
		iN = iX
	} else {
		iN = iY
	}

	found := func(point *Point, v string) int {
		if v == "X" {
			return point.X
		} else {
			return point.Y
		}
	}

	step := func(v string) int {
		if v == "X" {
			return stepX
		} else {
			return stepY
		}
	}

	for outputCount != instances {
		point, err := cgoSearch(haystack.Stride, hBounds.Dx(), hBounds.Dy(), needle.Stride, nBounds.Dx(), nBounds.Dy(),
			outerX1, outerY1, outerX2, outerY2, options.Variation, direction, hScan, nScan)
		if err != nil {
			return nil, err
		}
		if point == nil {
			break
		}
		outputs = append(outputs, *point)
		outputCount++
		update("outer", P, iP, found(point, P)+step(P))
		update("inner", N, iN, found(point, N)+step(N))
		update("inner", P, 1, found(point, P))
		update("inner", P, 2, found(point, P)+1)
		for outputCount != instances {
			point, err := cgoSearch(haystack.Stride, hBounds.Dx(), hBounds.Dy(), needle.Stride, nBounds.Dx(), nBounds.Dy(),
				innerX1, innerY1, innerX2, innerY2, options.Variation, direction, hScan, nScan)
			if err != nil {
				return nil, err
			}
			if point == nil {
				break
			}
			outputs = append(outputs, *point)
			outputCount++
			update("inner", N, iN, found(point, N)+step(N))
		}
	}

	return outputs, nil
}

func cgoSearch(hStride, hWidth, hHeight, nStride, nWidth, nHeight, sx1, sy1, sx2, sy2, variation, sd int, hScan, nScan *uint8) (*Point, error) {
	if sx2 < sx1 {
		return nil, errors.New("invalid search area")
	}
	if sy2 < sy1 {
		return nil, errors.New("invalid search area")
	}
	if sx2 > (hWidth - nWidth + 1) {
		return nil, errors.New("invalid search area")
	}
	if sy2 > (hHeight - nHeight + 1) {
		return nil, errors.New("invalid search area")
	}
	if sx2-sx1 == 0 {
		return nil, errors.New("invalid search area")
	}
	if sy2-sy1 == 0 {
		return nil, errors.New("invalid search area")
	}

	x, y := 0, 0
	ret := (C.int)(C.search((*C.int)(unsafe.Pointer(&x)), (*C.int)(unsafe.Pointer(&y)), (*C.uchar)(unsafe.Pointer(hScan)),
		(*C.uchar)(unsafe.Pointer(nScan)), C.int(nWidth), C.int(nHeight), C.int(hStride), C.int(nStride),
		C.int(sx1), C.int(sy1), C.int(sx2), C.int(sy2), C.int(variation), C.int(sd)))

	if ret == 0 {
		return &Point{x, y}, nil
	}
	return nil, nil
}
