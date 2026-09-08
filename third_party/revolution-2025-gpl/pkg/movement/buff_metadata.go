package movement

import (
	"bytes"
	"encoding/binary"
	"fmt"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"hash/crc32"
	"image/color"
)

type BuffMetadata struct {
	PixelColor     color.RGBA
	PixelCount     int
	Stackable      bool
	ImagePresent   string
	ImageMissing   string
	ImageY1        int
	ImageY2        int
	ImageX1        int
	ImageX2        int
	ImageVariation int
	ImageDirection int
	Speed          bool
}

var BuffMetadataMap = map[BuffType]BuffMetadata{
	Focus: {
		PixelColor: revimg.HexToRGBA(0x22FF06),
		Stackable:  true,
	},
	Haste: {
		PixelColor:     revimg.HexToRGBA(0xF0F0F0),
		ImageMissing:   "melody",
		ImageX1:        13,
		ImageY1:        5,
		ImageX2:        30,
		ImageY2:        13,
		ImageVariation: 20,
		Stackable:      true,
		Speed:          true,
	},
	HasteCoconut: {
		Speed: true,
	},
	HastePlus: {
		PixelColor: revimg.HexToRGBA(0xEDDB4C),
		Speed:      true,
	},
	BlackBear: {
		ImagePresent: "black_bear",
		ImageX1:      15,
		ImageY1:      37,
		ImageX2:      23,
		ImageY2:      38,
		Speed:        true,
	},
	BrownBear: {
		ImagePresent: "brown_bear",
		ImageX1:      15,
		ImageY1:      37,
		ImageX2:      23,
		ImageY2:      38,
		Speed:        true,
	},
	GummyBear: {
		ImagePresent: "gummy_bear",
		ImageX1:      15,
		ImageY1:      37,
		ImageX2:      23,
		ImageY2:      38,
		Speed:        true,
	},
	MotherBear: {
		ImagePresent: "mother_bear",
		ImageX1:      15,
		ImageY1:      37,
		ImageX2:      23,
		ImageY2:      38,
		Speed:        true,
	},
	PandaBear: {
		ImagePresent: "panda_bear",
		ImageX1:      15,
		ImageY1:      37,
		ImageX2:      23,
		ImageY2:      38,
		Speed:        true,
	},
	PolarBear: {
		ImagePresent: "polar_bear",
		ImageX1:      15,
		ImageY1:      37,
		ImageX2:      23,
		ImageY2:      38,
		Speed:        true,
	},
	ScienceBear: {
		ImagePresent: "science_bear",
		ImageX1:      15,
		ImageY1:      37,
		ImageX2:      23,
		ImageY2:      38,
		Speed:        true,
	},
	Melody: {
		PixelColor:     revimg.HexToRGBA(0xF0F0F0),
		ImagePresent:   "melody",
		ImageX1:        13,
		ImageY1:        5,
		ImageX2:        30,
		ImageY2:        13,
		ImageVariation: 20,
	},
	Oil: {
		ImagePresent:   "oil",
		ImageX1:        15,
		ImageY1:        37,
		ImageX2:        25,
		ImageY2:        38,
		ImageVariation: 2,
		Speed:          true,
	},
	SuperSmoothie: {
		ImagePresent:   "smoothie",
		ImageX1:        8,
		ImageY1:        37,
		ImageX2:        24,
		ImageY2:        38,
		ImageVariation: 2,
		Speed:          true,
	},
}

type BuffType int

const (
	Haste BuffType = iota
	HastePlus
	HasteCoconut
	BlackBear
	MotherBear
	PandaBear
	PolarBear
	BrownBear
	ScienceBear
	GummyBear
	Oil
	SuperSmoothie
	Melody
	Focus
)

type BuffMap map[BuffType]int

func (b *BuffMap) Hash() string {
	if b == nil {
		return "INVALID"
	}
	h := crc32.New(crc32.MakeTable(crc32.IEEE))

	for t, value := range *b {
		// Only speed buffs are relevant for hashing
		if !BuffMetadataMap[t].Speed {
			continue
		}
		var buf bytes.Buffer
		_ = binary.Write(&buf, binary.LittleEndian, t)
		_ = binary.Write(&buf, binary.LittleEndian, int32(value))
		h.Write(buf.Bytes())
	}

	return fmt.Sprintf("%08x", h.Sum32())
}
