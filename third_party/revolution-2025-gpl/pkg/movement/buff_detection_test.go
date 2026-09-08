package movement

import (
	"github.com/nosyliam/revolution/bitmaps"
	"github.com/stretchr/testify/assert"
	"testing"
)

func Test_HasteBuff(t *testing.T) {
	data, err := loadFixture("./fixture/buffs/haste_fixture.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	count := DetectBuff(0, Haste, test)
	assert.Equal(t, 10, count)
	count = DetectBuff(0, Melody, test)
	assert.Equal(t, 0, count)
}

func Test_BlackBear(t *testing.T) {
	data, err := loadFixture("./fixture/buffs/black_fixture.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	count := DetectBuff(0, BlackBear, test)
	assert.Equal(t, 1, count)
}

func Test_BrownBear(t *testing.T) {
	data, err := loadFixture("./fixture/buffs/brown_fixture.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	count := DetectBuff(0, BrownBear, test)
	assert.Equal(t, 1, count)
}

func Test_GummyBear(t *testing.T) {
	data, err := loadFixture("./fixture/buffs/gummy_fixture.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	count := DetectBuff(0, GummyBear, test)
	assert.Equal(t, 1, count)
}
func Test_MotherBear(t *testing.T) {
	data, err := loadFixture("./fixture/buffs/mother_fixture.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	count := DetectBuff(0, MotherBear, test)
	assert.Equal(t, 1, count)
}

func Test_PandaBear(t *testing.T) {
	data, err := loadFixture("./fixture/buffs/panda_fixture.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	count := DetectBuff(0, PandaBear, test)
	assert.Equal(t, 1, count)
}

func Test_PolarBear(t *testing.T) {
	data, err := loadFixture("./fixture/buffs/polar_fixture.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	count := DetectBuff(0, PolarBear, test)
	assert.Equal(t, 1, count)
}

func Test_ScienceBear(t *testing.T) {
	data, err := loadFixture("./fixture/buffs/science_fixture.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	count := DetectBuff(0, ScienceBear, test)
	assert.Equal(t, 1, count)
}

func Test_Oil(t *testing.T) {
	data, err := loadFixture("./fixture/buffs/oil_fixture.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	count := DetectBuff(0, Oil, test)
	assert.Equal(t, 1, count)
}

func Test_Smoothie(t *testing.T) {
	data, err := loadFixture("./fixture/buffs/smoothie_fixture.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	count := DetectBuff(0, SuperSmoothie, test)
	assert.Equal(t, 1, count)
}

func Test_Haste2(t *testing.T) {
	data, err := loadFixture("./fixture/buffs/speed_fixture.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	count := DetectBuff(0, Haste, test)
	assert.Equal(t, 10, count)
}

func Test_Melody(t *testing.T) {
	data, err := loadFixture("./fixture/buffs/melody_fixture.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	count := DetectBuff(0, Haste, test)
	assert.Equal(t, 0, count)
	count = DetectBuff(0, Melody, test)
	assert.Equal(t, 1, count)
}
