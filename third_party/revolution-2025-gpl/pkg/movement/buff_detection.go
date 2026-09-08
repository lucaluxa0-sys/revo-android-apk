package movement

import (
	"fmt"
	"github.com/nosyliam/revolution/bitmaps"
	"github.com/nosyliam/revolution/pkg/config"
	revimg "github.com/nosyliam/revolution/pkg/image"
	"golang.org/x/exp/maps"
	"golang.org/x/exp/slices"
	"image"
	"sync"
)

// ConfirmationCount defines the number of the same hashes that must be successively calculated to confirm a new buff set.
// This mechanic is necessary in order to address the transition states between buffs and handle unexpected graphical changes.
const ConfirmationCount = 6

type BuffDetector struct {
	mu              sync.Mutex
	hourlyHistogram map[BuffType][]int
	interrupts      map[chan bool]bool
	outputs         map[chan struct{}]chan bool
	buffs           BuffMap
	tick            int
	settings        *config.Object[config.Settings]

	newHash       string
	confirmations int
}

func NewBuffDetector(settings *config.Object[config.Settings]) *BuffDetector {
	return &BuffDetector{
		interrupts:      make(map[chan bool]bool),
		outputs:         make(map[chan struct{}]chan bool),
		hourlyHistogram: make(map[BuffType][]int),
		settings:        settings,
	}
}

// MoveSpeed returns the corrected player speed, factoring in all speed buffs
func (b *BuffDetector) MoveSpeed() float64 {
	speed := b.settings.Object().Player.Object().MoveSpeed
	if b.buffs == nil {
		return speed
	}
	keys := maps.Keys(b.buffs)
	for _, bear := range []BuffType{BlackBear, BrownBear, GummyBear, MotherBear, PandaBear, PolarBear, ScienceBear} {
		if slices.Contains(keys, bear) {
			speed += 4
			break
		}
	}
	if _, ok := b.buffs[HasteCoconut]; ok {
		speed += 10
	}
	for buff, count := range b.buffs {
		switch buff {
		case Haste:
			speed *= 1 + (float64(count) * 0.1)
		case HastePlus:
			speed *= 2
		case Oil:
			speed *= 1.2
		case SuperSmoothie:
			speed *= 1.25
		}
	}
	return speed

}

// Watch creates a channel which will respond to changes in movespeed
func (b *BuffDetector) Watch() chan struct{} {
	b.mu.Lock()
	defer b.mu.Unlock()
	waiter := make(chan bool)
	b.interrupts[waiter] = true
	output := make(chan struct{})
	b.outputs[output] = waiter
	go func() {
		closed := <-waiter
		b.mu.Lock()
		delete(b.interrupts, waiter)
		b.mu.Unlock()
		if closed {
			return
		}
		select {
		case <-output:
			return
		default:
			output <- struct{}{}
		}
	}()
	return output
}

func (b *BuffDetector) Unwatch(output chan struct{}) {
	close(output)
	b.outputs[output] <- true
}

func DetectBuff(index int, kind BuffType, tile *image.RGBA) int {
	meta := BuffMetadataMap[kind]
	if image := meta.ImagePresent; image != "" || meta.ImageMissing != "" {
		var missing = false
		if image == "" {
			image = meta.ImageMissing
			missing = true
		}
		result, err := revimg.ImageSearch(bitmaps.Registry.Get(image), tile, &revimg.SearchOptions{
			BoundStart:      &revimg.Point{X: meta.ImageX1, Y: meta.ImageY1},
			BoundEnd:        &revimg.Point{X: meta.ImageX2, Y: meta.ImageY2},
			SearchDirection: meta.ImageDirection,
			Variation:       meta.ImageVariation,
		})
		if err != nil {
			fmt.Printf("Failed to perform buff image search: %v", err)
			return 0
		}
		if (missing && len(result) > 0) || (!missing && len(result) == 0) {
			return 0
		}
	}
	if r, g, b, a := meta.PixelColor.RGBA(); !(r == 0 && g == 0 && b == 0 && a == 0) {
		var count = meta.PixelCount
		if count == 0 {
			count = 38
		}
		if index == 0 {
			count -= 1 // Left-most edge of the window may have pixel discoloration
		}
		// Detect the line of pixels at the bottom of the buff. These will always be consistent since
		// they will always be present right up until the very last moment that the buff expires.
		var detected = 0
		for i := 0; i < 38; i++ {
			if tile.RGBAAt(i, 37) == meta.PixelColor {
				detected++
			}
		}
		if detected < count {
			return 0
		}
	}
	if meta.Stackable {
		value, err := DetectDigits(tile)
		if err != nil {
			fmt.Printf("Failed to detect digits: %v", err)
			return 0
		}
		if value == -1 {
			value = 1
		}
		return value
	} else {
		return 1
	}
}

func (b *BuffDetector) Tick(origin *revimg.Point, screenshot *image.RGBA) {
	var buffs = make(BuffMap)
	for index := 0; ; index++ {
		// We'll have to check for buffs until the end of the window until we have every buff indexed.
		// I may be able to implement a heuristic method to detect the last buff in the future.
		if (index+1)*38 >= screenshot.Bounds().Dx() {
			break
		}
		tile := revimg.CropRGBA(screenshot, image.Rect((index*38)+origin.X, origin.Y+58, ((index+1)*38)+origin.X, origin.Y+96))
		for kind := range BuffMetadataMap {
			if kind == HasteCoconut {
				continue
			}
			if _, ok := buffs[kind]; ok && kind != Haste {
				continue
			}
			value := DetectBuff(index, kind, tile)
			if value == 0 {
				continue
			}
			if _, ok := buffs[Haste]; ok && kind == Haste {
				buffs[HasteCoconut] = 1
				continue
			}
			buffs[kind] = value
		}
	}
	oldHash, newHash := b.buffs.Hash(), buffs.Hash()
	if oldHash != newHash {
		if newHash != b.newHash {
			b.newHash = newHash
			b.confirmations = 0
		} else {
			b.confirmations++
		}
		if b.confirmations >= ConfirmationCount {
			b.mu.Lock()
			b.buffs = buffs
			for ch, _ := range b.interrupts {
				ch <- false
			}
			b.mu.Unlock()
			b.confirmations = 0
		}
	}
	b.tick++
}
