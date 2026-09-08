package movement

import (
	"github.com/nosyliam/revolution/bitmaps"
	"github.com/stretchr/testify/assert"
	"io"
	"os"
	"testing"
)

func loadFixture(name string) ([]byte, error) {
	file, err := os.Open(name)
	if err != nil {
		return nil, err
	}

	data, err := io.ReadAll(file)
	if err != nil {
		return nil, err
	}

	err = file.Close()
	if err != nil {
		return nil, err
	}

	return data, nil
}

func Test_DigitDetection(t *testing.T) {
	data, err := loadFixture("./fixture/digits/blessing.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	result, err := DetectDigits(test)
	assert.NoError(t, err)
	assert.Equal(t, 23, result)
}

func Test_DigitDetection_Four(t *testing.T) {
	data, err := loadFixture("./fixture/digits/four.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(t, test)
	result, err := DetectDigits(test)
	assert.NoError(t, err)
	assert.Equal(t, 4, result)
}

func BenchmarkDigitDetection(b *testing.B) {
	data, err := loadFixture("./fixture/digits/blessing.png")
	assert.NoError(b, err)
	bitmaps.Registry.RegisterPng("test", data)
	test := bitmaps.Registry.Get("test")
	assert.NotNil(b, test)
	for i := 0; i < b.N; i++ {
		result, err := DetectDigits(test)
		assert.NoError(b, err)
		assert.Equal(b, 23, result)
	}
}
