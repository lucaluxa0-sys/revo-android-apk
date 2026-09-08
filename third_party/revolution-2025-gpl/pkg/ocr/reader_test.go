package ocr

import (
	"fmt"
	"github.com/nosyliam/revolution/bitmaps"
	"github.com/stretchr/testify/assert"
	"testing"
)

func Test_ImageReader(t *testing.T) {
	ch := make(chan string, 100)
	imageReader, err := NewReader(ch)
	if err != nil {
		panic(err)
	}

	go imageReader.Start()

	//now := time.Now()
	img := bitmaps.Registry.Get("testdigit")
	fmt.Println(img)
	res := <-imageReader.ReadImage(img)
	fmt.Println(res)

	assert.NotNil(t, res)
	assert.NoError(t, err)
}
