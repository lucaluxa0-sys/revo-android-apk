package hive

import (
	. "github.com/nosyliam/revolution/pkg/common"
	. "github.com/nosyliam/revolution/pkg/control/actions"
)

const GotoCannonRoutineKind RoutineKind = "GotoCannon"

var GotoCannonRoutine = Actions{
	Walk(Forward, 12),
	Loop(
		For(MS[int]("counters.claimedHive")),
		Walk(Right, 37),
	),
	KeyDown(Right),
	KeyPress(Space),
	Sleep(1300),
	KeyPress(Space),
	Loop(
		For(500),
		Condition(
			If(Image(PressEImage...).Found()),
			KeyUp(Right),
			Terminate(),
		),
		Sleep(10),
	),
	Error("Failed to goto cannon!")(Status, Discord),
	Sleep(5).Seconds(),
	ResetCharacter(),
	Restart(),
}

func init() {
	GotoCannonRoutine.Register(GotoCannonRoutineKind)
}
