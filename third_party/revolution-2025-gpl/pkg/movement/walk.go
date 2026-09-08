package movement

import (
	"fmt"
	"github.com/nosyliam/revolution/pkg/common"
	"time"
)

type Direction int

const (
	Forward  Direction = Direction(common.Forward)
	Backward Direction = Direction(common.Backward)
	Left     Direction = Direction(common.Left)
	Right    Direction = Direction(common.Right)
)

func Sleep(ms int, macro *common.Macro) {
	watch := macro.Watch()
	defer macro.Unwatch(watch)
	remaining := time.Duration(ms) * time.Millisecond
	for remaining > 0 {
		start := time.Now()
		select {
		case <-time.After(remaining):
			return
		case resume := <-watch: // TODO: Clean up unused timer
			remaining -= time.Now().Sub(start)
			if resume == nil {
				return
			}
			<-resume
		}
	}
}

func walk(direction Direction, distance float64, macro *common.Macro, async bool) {
	if len(macro.Stop) > 0 {
		return
	}
	finish := make(chan struct{})
	go func() {
		watch := macro.Watch()
		defer macro.Unwatch(watch)
		remaining := distance
		<-macro.EventBus.KeyDown(macro, common.Key(direction))
		for remaining > 0 {
			change := macro.BuffDetect.Watch()
			speed := macro.BuffDetect.MoveSpeed()
			duration := time.Duration((remaining / speed) * float64(time.Second))
			fmt.Println("Speed", speed, remaining, "Duration", duration)
			start := time.Now()
			select {
			case <-time.After(duration):
				<-macro.EventBus.KeyUp(macro, common.Key(direction))
				if !async {
					finish <- struct{}{}
				}
				macro.BuffDetect.Unwatch(change)
				return
			case resume := <-watch: // TODO: Clean up unused timer
				end := time.Now()
				<-macro.EventBus.KeyUp(macro, common.Key(direction))
				if resume == nil {
					if !async {
						finish <- struct{}{}
					}
					return
				}
				fmt.Println("waiting for resume")
				<-resume
				<-macro.EventBus.KeyDown(macro, common.Key(direction))
				remaining -= (end.Sub(start)).Seconds() * speed
				macro.BuffDetect.Unwatch(change)
			case <-change:
				remaining -= (time.Now().Sub(start)).Seconds() * speed
			}
		}
	}()
	if !async {
		<-finish
	}
}

func Walk(direction Direction, distance float64, macro *common.Macro) {
	walk(direction, distance, macro, false)
}

func WalkAsync(direction Direction, distance float64, macro *common.Macro) {
	walk(direction, distance, macro, true)
}
