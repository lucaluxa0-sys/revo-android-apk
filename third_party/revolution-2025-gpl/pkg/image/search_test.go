package image

import (
	"fmt"
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

func Test_PollenSearch(t *testing.T) {
	data, err := loadFixture("./fixture/pollen.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test1", data)
	needle := bitmaps.Registry.Get("toppollen")
	haystack := bitmaps.Registry.Get("test1")
	assert.NotNil(t, needle)
	assert.NotNil(t, haystack)
	results, err := ImageSearch(needle, haystack, &SearchOptions{Variation: 20})
	assert.Len(t, results, 1)
	fmt.Println(results)

	data, err = loadFixture("./fixture/collect.png")
	assert.NoError(t, err)
	bitmaps.Registry.RegisterPng("test2", data)
	needle = bitmaps.Registry.Get("collectpollen")
	haystack = bitmaps.Registry.Get("test2")
	assert.NotNil(t, needle)
	assert.NotNil(t, haystack)
	fmt.Println(ImageSearch(needle, haystack, &SearchOptions{Variation: 0}))
}
