package actions

import (
	"github.com/nosyliam/revolution/pkg/common"
	"reflect"
)

type (
	intCompareOpType int
	eqCompareOpType  int
)

const (
	gtIntCompareOp intCompareOpType = iota
	ltIntCompareOp
	gteIntCompareOp
	lteIntCompareOp
)

const (
	eqEqCompareOp eqCompareOpType = iota
	notEqEqCompareOp
)

func intCompareType(op intCompareOpType, args []interface{}) PredicateFunc {
	if len(args) != 2 {
		panic("invalid arguments")
	}
	switch args[0].(type) {
	case int:
		return intCompare[int](op, args)
	case func(*common.Macro) int:
		return intCompare[int](op, args)
	case uint:
		return intCompare[uint](op, args)
	case func(*common.Macro) uint:
		return intCompare[uint](op, args)
	case float32:
		return intCompare[float32](op, args)
	case func(*common.Macro) float32:
		return intCompare[float32](op, args)
	case float64:
		return intCompare[float64](op, args)
	case func(*common.Macro) float64:
		return intCompare[float64](op, args)
	}
	panic("incomparable type")
}

func intCompare[T int | uint | float32 | float64](op intCompareOpType, args []interface{}) PredicateFunc {
	if len(args) != 2 {
		panic("invalid arguments")
	}

	var l, r func(*common.Macro) T
	var lV, rV T
	var ok bool
	if l, ok = args[0].(func(*common.Macro) T); !ok {
		lV = args[0].(T)
	}
	if r, ok = args[1].(func(*common.Macro) T); !ok {
		rV = args[1].(T)
	}
	return func(macro *common.Macro) bool {
		var lR, rR T
		if l != nil {
			lR = l(macro)
		} else {
			lR = lV
		}
		if r != nil {
			rR = r(macro)
		} else {
			rR = rV
		}
		switch op {
		case gtIntCompareOp:
			return lR > rR
		case ltIntCompareOp:
			return lR < rR
		case gteIntCompareOp:
			return lR >= rR
		case lteIntCompareOp:
			return lR <= rR
		default:
			panic("unknown op")
		}
	}
}

func equalityCompareType(op eqCompareOpType, args []interface{}) PredicateFunc {
	if len(args) != 2 {
		panic("invalid arguments")
	}
	switch args[0].(type) {
	case bool:
		return equalityCompare[bool](op, args)
	case func(*common.Macro) bool:
		return equalityCompare[bool](op, args)
	case string:
		return equalityCompare[string](op, args)
	case func(*common.Macro) string:
		return equalityCompare[string](op, args)
	case int:
		return equalityCompare[int](op, args)
	case func(*common.Macro) int:
		return equalityCompare[int](op, args)
	case uint:
		return equalityCompare[uint](op, args)
	case func(*common.Macro) uint:
		return equalityCompare[uint](op, args)
	case float32:
		return equalityCompare[float32](op, args)
	case func(*common.Macro) float32:
		return equalityCompare[float32](op, args)
	case float64:
		return equalityCompare[float64](op, args)
	case func(*common.Macro) float64:
		return equalityCompare[float64](op, args)
	case *any:
		return equalityCompare[*any](op, args)
	case func(*common.Macro) *any:
		return equalityCompare[*any](op, args)
	}
	panic("incomparable type")
}

func equalityCompare[T comparable](op eqCompareOpType, args []interface{}) PredicateFunc {
	var l, r func(*common.Macro) T
	var lV, rV T
	var ok bool
	if l, ok = args[0].(func(*common.Macro) T); !ok {
		lV = args[0].(T)
	}
	if r, ok = args[1].(func(*common.Macro) T); !ok {
		rV = args[1].(T)
	}
	return func(macro *common.Macro) bool {
		var lR, rR T
		if l != nil {
			lR = l(macro)
		} else {
			lR = lV
		}
		if r != nil {
			rR = r(macro)
		} else {
			rR = rV
		}
		switch op {
		case eqEqCompareOp:
			return lR == rR
		case notEqEqCompareOp:
			return lR != rR
		default:
			panic("unknown op")
		}
	}
}

func Equal(args ...interface{}) PredicateFunc {
	return equalityCompareType(eqEqCompareOp, args)
}

func NotEqual(args ...interface{}) PredicateFunc {
	return equalityCompareType(notEqEqCompareOp, args)
}

func GreaterThan(args ...interface{}) PredicateFunc {
	return intCompareType(gtIntCompareOp, args)
}

func LessThan(args ...interface{}) PredicateFunc {
	return intCompareType(ltIntCompareOp, args)
}

func GreaterThanEq(args ...interface{}) PredicateFunc {
	return intCompareType(gteIntCompareOp, args)
}

func LessThanEq(args ...interface{}) PredicateFunc {
	return intCompareType(lteIntCompareOp, args)
}

func NotNil(obj interface{}) PredicateFunc {
	fn := obj.(func(*common.Macro) interface{})
	return func(macro *common.Macro) bool {
		return !reflect.ValueOf(fn(macro)).IsNil()
	}
}

func Nil(obj interface{}) PredicateFunc {
	fn := obj.(func(*common.Macro) interface{})
	return func(macro *common.Macro) bool {
		return reflect.ValueOf(fn(macro)).IsNil()
	}
}

func True(args ...interface{}) PredicateFunc {
	return equalityCompareType(eqEqCompareOp, []interface{}{true, args[0]})
}

func False(args ...interface{}) PredicateFunc {
	return equalityCompareType(eqEqCompareOp, []interface{}{false, args[0]})
}

func execError(exec interface{}, err bool) PredicateFunc {
	var exc func(macro *common.Macro) error
	switch fn := exec.(type) {
	case func(macro *common.Macro) error:
		exc = fn
	case func() error:
		exc = func(*common.Macro) error { return fn() }
	case common.Action:
		exc = fn.Execute
	default:
		panic("invalid")
	}
	return func(macro *common.Macro) bool {
		if err {
			res := exc(macro)
			return res != nil
		} else {
			res := exc(macro)
			return res == nil
		}
	}
}

func ExecError(exec interface{}) PredicateFunc {
	return execError(exec, true)
}

func ExecNoError(exec interface{}) PredicateFunc {
	return execError(exec, false)
}
