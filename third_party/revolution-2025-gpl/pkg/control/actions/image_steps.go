package actions

import (
	"fmt"
	. "github.com/nosyliam/revolution/bitmaps"
	"github.com/nosyliam/revolution/pkg/common"
	"github.com/nosyliam/revolution/pkg/image"
	"reflect"
)

func X1(ctx *imageSearchContext) interface{} {
	return ctx.x1
}

func Y1(ctx *imageSearchContext) interface{} {
	return ctx.y1
}

func X2(ctx *imageSearchContext) interface{} {
	return ctx.x2
}

func Y2(ctx *imageSearchContext) interface{} {
	return ctx.y2
}

func XY1(ctx *imageSearchContext) interface{} {
	return image.Point{X: ctx.x1, Y: ctx.y1}
}

func XY2(ctx *imageSearchContext) interface{} {
	return image.Point{X: ctx.x2, Y: ctx.y2}
}

func Height(ctx *imageSearchContext) interface{} {
	return ctx.macro.Root.Window.Screenshot().Bounds().Dy()
}

func Width(ctx *imageSearchContext) interface{} {
	return ctx.macro.Root.Window.Screenshot().Bounds().Dx()
}

// Add adds together two or more values
func Add(params ...interface{}) Value {
	if len(params) != 2 {
		panic("two parameters required for modifier: add")
	}
	return func(ctx *imageSearchContext) interface{} {
		var value int
		for _, param := range params {
			switch v := param.(type) {
			case int:
				value += param.(int)
			case Value:
				value += v(ctx).(int)
			case func(macro *common.Macro) int:
				value += v(ctx.macro)
			default:
				panic("invalid parameter type: add")
			}
		}
		return value
	}
}

// Change returns the value of the last parameter
func Change(params ...interface{}) Value {
	if len(params) == 0 {
		panic("one or more parameters required for modifier: set")
	}
	return func(ctx *imageSearchContext) interface{} {
		switch v := params[len(params)-1].(type) {
		case int:
			return v
		case Value:
			return v(ctx)
		case func(macro *common.Macro) int:
			return v(ctx.macro)
		default:
			panic("invalid parameter type: add")
		}
	}
}

// Sub subtracts the first parameter from one or more parameters
func Sub(params ...interface{}) Value {
	if len(params) != 2 {
		panic("two or more parameters required for modifier: sub")
	}
	return func(ctx *imageSearchContext) interface{} {
		var value int
		for i, param := range params {
			switch v := param.(type) {
			case int:
				if i == 0 {
					value = v
					continue
				}
				value -= v
			case Value:
				if i == 0 {
					value = v(ctx).(int)
					continue
				}
				value -= v(ctx).(int)
			case func(macro *common.Macro) int:
				if i == 0 {
					value = v(ctx.macro)
					continue
				}
				value -= v(ctx.macro)
			default:
				panic("invalid parameter type: sub")
			}
		}
		return value
	}
}

// Div divides the first parameter by the second parameter and floors the result
func Div(params ...interface{}) Value {
	if len(params) != 2 {
		panic("two parameters required for modifier: div")
	}
	return func(ctx *imageSearchContext) interface{} {
		var value int
		for i, param := range params {
			switch v := param.(type) {
			case int:
				if i == 0 {
					value = v
					continue
				}
				value /= v
			case Value:
				if i == 0 {
					value = v(ctx).(int)
					continue
				}
				value /= v(ctx).(int)
			case func(macro *common.Macro) int:
				if i == 0 {
					value = v(ctx.macro)
					continue
				}
				value /= v(ctx.macro)
			default:
				panic("invalid parameter type: sub")
			}
		}
		return value
	}
}

// Mul multiplies two or more parameters

func Result(params ...interface{}) Value {
	return func(ctx *imageSearchContext) interface{} {
		var point image.Point
		if len(params) == 0 {
			point = ctx.lastResult[0]
		} else if len(params) == 1 {
			point = ctx.result[params[0].(string)][0]
		} else {
			switch v := params[1].(type) {
			case int:
				return ctx.result[params[0].(string)][v]
			case Value:
				return ctx.result[params[0].(string)][v(ctx).(int)]
			case func(macro *common.Macro) int:
				return ctx.result[params[0].(string)][v(ctx.macro)]
			}
		}
		return point
	}
}

func ResultX(params ...interface{}) Value {
	return func(ctx *imageSearchContext) interface{} {
		if len(params) == 0 {
			return ctx.lastResult[0].X
		} else if len(params) == 1 {
			return ctx.result[params[0].(string)][0].X
		} else {
			switch v := params[1].(type) {
			case int:
				return ctx.result[params[0].(string)][v].X
			case Value:
				return ctx.result[params[0].(string)][v(ctx).(int)].X
			case func(macro *common.Macro) int:
				return ctx.result[params[0].(string)][v(ctx.macro)].X
			default:
				panic("invalid parameter type")
			}
		}
	}
}

func ResultY(params ...interface{}) Value {
	return func(ctx *imageSearchContext) interface{} {
		if len(params) == 0 {
			return ctx.lastResult[0].Y
		} else if len(params) == 1 {
			return ctx.result[params[0].(string)][0].Y
		} else {
			switch v := params[1].(type) {
			case int:
				return ctx.result[params[0].(string)][v].Y
			case Value:
				return ctx.result[params[0].(string)][v(ctx).(int)].Y
			case func(macro *common.Macro) int:
				return ctx.result[params[0].(string)][v(ctx.macro)].Y
			default:
				panic("invalid parameter type")
			}
		}
	}
}

func SelectCoordinate(params ...interface{}) Step {
	return func(ctx *imageSearchContext) {
		switch fn := params[0].(type) {
		case Modifier:
			params = params[1:]
			if len(params) != 4 {
				panic("expected 4 parameters for coordinate")
			}
			var getters = []Value{X1, Y1, X2, Y2}
			var values []int
			for i, paramValue := range params {
				switch param := paramValue.(type) {
				case int:
					values = append(values, fn(getters[i], param)(ctx).(int))
				case func(macro *common.Macro) int:
					values = append(values, fn(getters[i], param(ctx.macro))(ctx).(int))
				case Value:
					values = append(values, fn(getters[i], param(ctx).(int))(ctx).(int))
				default:
					panic("invalid value type")
				}
			}
			ctx.x1, ctx.y1, ctx.x2, ctx.y2 = values[0], values[1], values[2], values[3]
		case Value:
			point := fn(ctx).(image.Point)
			ctx.x1, ctx.y1, ctx.x2, ctx.y2 = point.X, point.Y, point.X, point.Y
		}
	}
}

func singleCoordinateSelect(value Value, mod func(ctx *imageSearchContext, val int), params ...interface{}) Step {
	return func(ctx *imageSearchContext) {
		switch fn := params[0].(type) {
		case Modifier:
			params = params[1:]
			if len(params) != 4 {
				panic("expected one parameter for single coordinate selection")
			}
			switch param := params[0].(type) {
			case int:
				mod(ctx, fn(value, param)(ctx).(int))
			case Value:
				mod(ctx, fn(value, param(ctx).(int))(ctx).(int))
			case func(macro *common.Macro) int:
				mod(ctx, fn(value, param(ctx.macro))(ctx).(int))
			default:
				panic("invalid value type")
			}
		case Value:
			switch v := fn(ctx).(type) {
			case image.Point:
				switch reflect.ValueOf(value).Pointer() {
				case reflect.ValueOf(X1).Pointer():
					fallthrough
				case reflect.ValueOf(X2).Pointer():
					mod(ctx, v.X)
				case reflect.ValueOf(Y1).Pointer():
					fallthrough
				case reflect.ValueOf(Y2).Pointer():
					mod(ctx, v.Y)
				}
			case int:
				mod(ctx, fn(ctx).(int))
			default:
				panic("invalid value type for single coordinate select")
			}
		case func(macro *common.Macro) int:
			mod(ctx, fn(ctx.macro))
		case int:
			mod(ctx, fn)
		}
	}
}

func SelectX1(params ...interface{}) Step {
	return singleCoordinateSelect(X1, func(ctx *imageSearchContext, val int) { ctx.x1 = val }, params...)
}

func SelectY1(params ...interface{}) Step {
	return singleCoordinateSelect(Y1, func(ctx *imageSearchContext, val int) { ctx.y1 = val }, params...)
}

func SelectX2(params ...interface{}) Step {
	return singleCoordinateSelect(X2, func(ctx *imageSearchContext, val int) { ctx.x2 = val }, params...)
}

func SelectY2(params ...interface{}) Step {
	return singleCoordinateSelect(Y2, func(ctx *imageSearchContext, val int) { ctx.y2 = val }, params...)
}

func SelectXY1(params ...interface{}) Step {
	return func(ctx *imageSearchContext) {
		switch fn := params[0].(type) {
		case Modifier:
			params = params[1:]
			if len(params) != 4 {
				panic("expected 4 parameters for coordinate")
			}
			var getters = []Value{X1, Y1}
			var values []int
			for i, paramValue := range params {
				switch param := paramValue.(type) {
				case int:
					values = append(values, fn(getters[i], param)(ctx).(int))
				case func(macro *common.Macro) int:
					values = append(values, fn(getters[i], param(ctx.macro))(ctx).(int))
				case Value:
					values = append(values, fn(getters[i], param(ctx).(int))(ctx).(int))
				default:
					panic("invalid value type")
				}
			}
			ctx.x1, ctx.y1, ctx.x2, ctx.y2 = values[0], values[1], values[2], values[3]
		case Value:
			point := fn(ctx).(image.Point)
			ctx.x1, ctx.y1 = point.X, point.Y
		}
	}
}

func SelectXY2(params ...interface{}) Step {
	return func(ctx *imageSearchContext) {
		switch fn := params[0].(type) {
		case Modifier:
			params = params[1:]
			if len(params) != 4 {
				panic("expected 4 parameters for coordinate")
			}
			var getters = []Value{X2, Y2}
			var values []int
			for i, paramValue := range params {
				switch param := paramValue.(type) {
				case int:
					values = append(values, fn(getters[i], param)(ctx).(int))
				case func(macro *common.Macro) int:
					values = append(values, fn(getters[i], param(ctx.macro))(ctx).(int))
				case Value:
					values = append(values, fn(getters[i], param(ctx).(int))(ctx).(int))
				default:
					panic("invalid value type")
				}
			}
			ctx.x1, ctx.y1, ctx.x2, ctx.y2 = values[0], values[1], values[2], values[3]
		case Value:
			point := fn(ctx).(image.Point)
			ctx.x1, ctx.y1 = point.X, point.Y
		}
	}
}

// Bounds increases the value of X2 and Y2 by the given values
func Bounds(params ...interface{}) Step {
	return func(ctx *imageSearchContext) {
		switch fn := params[0].(type) {
		case Modifier:
			params = params[1:]
			if len(params) != 4 {
				panic("expected 4 parameters for coordinate")
			}
			var getters = []Value{X2, Y2}
			var values []int
			for i, paramValue := range params {
				switch param := paramValue.(type) {
				case int:
					values = append(values, fn(getters[i], param)(ctx).(int))
				case func(macro *common.Macro) int:
					values = append(values, fn(getters[i], param(ctx.macro))(ctx).(int))
				case Value:
					values = append(values, fn(getters[i], param(ctx).(int))(ctx).(int))
				default:
					panic("invalid value type")
				}
			}
			ctx.x1, ctx.y1, ctx.x2, ctx.y2 = values[0], values[1], values[2], values[3]
		case Value:
			point := fn(ctx).(image.Point)
			ctx.x2 += point.X
			ctx.y2 += point.Y
		}
	}
}

func SubdivideX(params ...interface{}) Step {
	if len(params) != 1 {
		panic("expected one parameter for variation")
	}
	return func(ctx *imageSearchContext) {
		ctx.subX = params[0].(int)
	}
}

func SubdivideY(params ...interface{}) Step {
	if len(params) != 1 {
		panic("expected one parameter for variation")
	}
	return func(ctx *imageSearchContext) {
		ctx.subY = params[0].(int)
	}
}

func Subdivide(params ...interface{}) Step {
	if len(params) != 1 {
		panic("expected one or more parameters for multi-axis subdivision")
	}
	return func(ctx *imageSearchContext) {
		ctx.subX = params[0].(int)
		ctx.subY = params[0].(int)

	}
}

func Variance(params ...interface{}) Step {
	if len(params) != 1 {
		panic("expected one parameter for variance")
	}
	return func(ctx *imageSearchContext) {
		ctx.variance = params[0].(int)
		ctx.varianceSet = true
	}
}

func DefaultVariance(params ...interface{}) Step {
	if len(params) != 1 {
		panic("expected one parameter for default variance")
	}
	return func(ctx *imageSearchContext) {
		ctx.defVariance = params[0].(int)
	}
}

func Instances(params ...interface{}) Step {
	if len(params) != 1 {
		panic("expected one parameter for variation")
	}
	return func(ctx *imageSearchContext) {
		ctx.instances = params[0].(int)
	}
}

func Direction(params ...interface{}) Step {
	if len(params) != 1 {
		panic("expected one parameter for variation")
	}
	return func(ctx *imageSearchContext) {
		ctx.instances = params[0].(int)
	}
}

func IVD(params ...interface{}) Step {
	if len(params) != 3 {
		panic("expected three parameter for variance, instances, direction")
	}
	return func(ctx *imageSearchContext) {
		ctx.instances = params[0].(int)
		ctx.variance = params[1].(int)
		ctx.direction = params[2].(int)
		ctx.varianceSet = true
	}
}

func VD(params ...interface{}) Step {
	if len(params) != 2 {
		panic("expected two parameter for variance, direction")
	}
	return func(ctx *imageSearchContext) {
		ctx.variance = params[0].(int)
		ctx.direction = params[1].(int)
		ctx.varianceSet = true
	}
}

type search struct {
	bitmaps []string
	none    bool
}

func (s *search) Find() Step {
	return func(ctx *imageSearchContext) {
		fmt.Println(s.bitmaps)
		for _, bitmap := range s.bitmaps {
			var variance = ctx.variance
			if ctx.defVariance != 0 && variance == 0 && !ctx.varianceSet {
				variance = ctx.defVariance
			}
			screenshot := ctx.macro.Root.Window.Screenshot()
			if screenshot == nil {
				ctx.exit = true
				ctx.lastResult = make([]image.Point, 0)
				return
			}
			points, err := image.ImageSearch(
				Registry.Get(bitmap),
				ctx.macro.Root.Window.Screenshot(),
				&image.SearchOptions{
					BoundStart:      &image.Point{X: ctx.x1, Y: ctx.x2},
					BoundEnd:        &image.Point{X: ctx.x2, Y: ctx.y2},
					SearchDirection: ctx.direction,
					Variation:       ctx.variance,
					Instances:       ctx.instances,
				},
			)

			if err != nil {
				ctx.macro.Action(Error("Image search failed!", bitmap, err)(Status))
				ctx.macro.Action(Error("Image search for bitmap %s failed: %v", bitmap, err)(Discord))
				ctx.lastResult = make([]image.Point, 0)
				fmt.Println("search failed", err)
				return
			}

			ctx.result[bitmap] = points
			ctx.lastResult = points
			if len(points) != 0 || s.none {
				break
			}
		}

		if len(ctx.lastResult) == 0 && !s.none {
			ctx.exit = true
		}

		ctx.instances, ctx.variance, ctx.direction = 0, 0, 0
		ctx.varianceSet = false
	}
}

func (s *search) NotFound() *search {
	s.none = true
	return s
}

func Search(bitmaps ...string) *search {
	return &search{bitmaps: bitmaps}
}
