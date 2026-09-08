package routines

import (
	. "github.com/nosyliam/revolution/pkg/common"
	. "github.com/nosyliam/revolution/pkg/control/actions"
)

var ResetRoutine = Actions{
	// Check for (and disable) performance stats
	Condition(
		If(Image(
			DefaultVariance(2),
			Direction(5),
			Search("perfmem").Find(),
			SelectCoordinate(Result()),
			Bounds(17, 7),
			Search("perfwhitefill").NotFound().Find(),
			SelectXY1(Result("perfmem")),
			SelectXY2(Change, 0, Add(ResultY("perfmem"), 7)),
			Search("perfcpu").Find(),
			SelectCoordinate(Result()),
			Bounds(17, 7),
			Search("perfwhitefill").NotFound().Find(),
			SelectXY1(Result("perfcpu")),
			SelectXY2(Change, 0, Add(ResultY("perfcpu"), 7)),
			Search("perfcpu").Find(),
			SelectCoordinate(Result()),
			Bounds(17, 7),
			Search("perfwhitefill").NotFound().Find(),
		).Found()),
	),
}

func init() {
	ResetRoutine.Register(ResetRoutineKind)
}
