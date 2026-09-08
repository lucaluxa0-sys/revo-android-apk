package actions

import (
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/image"
)

type ImageSteps []Step
type Modifier func(params ...interface{}) Value
type Value func(ctx *imageSearchContext) interface{}

type Step func(ctx *imageSearchContext)

type imageSearchContext struct {
	search *imageSearch
	macro  *common.Macro

	result     map[string][]image.Point
	lastResult []image.Point

	subX, subY     int
	x1, y1, x2, y2 int
	exit           bool

	defVariance                    int
	varianceSet                    bool
	variance, instances, direction int
}

func (i *imageSearchContext) execute() {
	for _, step := range i.search.steps {
		step(i)
		if i.exit {
			break
		}
	}
	if i.lastResult == nil {
		panic("invalid search: no search executed")
	}
}

func NewImageSearchContext(search *imageSearch, macro *common.Macro) *imageSearchContext {
	return &imageSearchContext{
		search: search,
		macro:  macro,
		result: make(map[string][]image.Point),
	}
}

type imageSearch struct {
	steps []Step
}

func (i *imageSearch) Found() func(macro *common.Macro) bool {
	return func(macro *common.Macro) bool {
		ctx := NewImageSearchContext(i, macro)
		ctx.execute()
		return len(ctx.lastResult) > 0
	}
}

func (i *imageSearch) NotFound() func(macro *common.Macro) bool {
	return func(macro *common.Macro) bool {
		ctx := NewImageSearchContext(i, macro)
		ctx.execute()
		return len(ctx.lastResult) == 0
	}
}

func (i *imageSearch) Instances() func(macro *common.Macro) int {
	return func(macro *common.Macro) int {
		ctx := NewImageSearchContext(i, macro)
		ctx.execute()
		return len(ctx.lastResult)
	}
}

func (i *imageSearch) X() func(macro *common.Macro) int {
	return func(macro *common.Macro) int {
		ctx := NewImageSearchContext(i, macro)
		ctx.execute()
		if len(ctx.lastResult) == 0 {
			return -1
		}
		return ctx.lastResult[0].X
	}
}

func (i *imageSearch) Y() func(macro *common.Macro) int {
	return func(macro *common.Macro) int {
		ctx := NewImageSearchContext(i, macro)
		ctx.execute()
		if len(ctx.lastResult) == 0 {
			return -1
		}
		return ctx.lastResult[0].Y
	}
}

func Image(steps ...Step) *imageSearch {
	return &imageSearch{steps: steps}
}
