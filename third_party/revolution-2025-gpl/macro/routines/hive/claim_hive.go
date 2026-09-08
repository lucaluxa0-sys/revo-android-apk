package hive

import (
	. "github.com/nosyliam/revolution/pkg/common"
	. "github.com/nosyliam/revolution/pkg/control/actions"
)

const ClaimHiveRoutineKind RoutineKind = "ClaimHive"

var MoveToNextHive = Actions{
	Condition(
		If(And(Equal(V[int]("CheckingHive"), 1), Equal(V[int]("CheckDirection"), -1))),
		Set("CheckDirection", 1),
		Set("CheckSkip", V[int]("CheckedHives")),
	),
	Condition(
		If(Equal(V[int]("CheckDirection"), 1)),
		KeyDown(Left),
		Increment("CheckingHive"),
		Else(),
		KeyDown(Right),
		Decrement("CheckingHive"),
	),
	Loop(
		Until(Image(AllHiveImages...).NotFound()),
		Sleep(10),
	),
	Loop(
		Forever(),
		Condition(
			If(Image(ClaimHiveImage...).Found()),
			KeyUp(Left),
			KeyUp(Right),
			SetState("counters.claimedHive", V[int]("CheckingHive")),
			KeyPress(E),
			Terminate(),
		),
		Condition(
			If(Or(
				Image(SendTradeImage...).Found(),
				Image(TradeDisabledImage...).Found(),
				Image(TradeLockedImage...).Found(),
			)),
			Break(),
		),
		Sleep(10),
	),
	Condition(
		If(Equal(V[int]("CheckSkip"), 0)),
		KeyUp(Left),
		KeyUp(Right),
		Increment("CheckedHives"),
		Else(),
		Decrement("CheckSkip"),
	),
	Sleep(100),
}

var ClaimHiveRoutine = Actions{
	KeyDown(Forward),
	Loop(
		Forever(),
		Condition(
			If(Image(AllHiveImages...).Found()),
			KeyUp(Forward),
			Walk(Backward, 2),
			Break(),
		),
		Sleep(10),
	),
	Sleep(100),
	Condition(
		If(Image(ClaimHiveImage...).Found()),
		SetState("counters.claimedHive", 3),
		KeyPress(E),
		Walk(Backward, 4),
		Info("Claimed Hive: 3")(Status, Discord),
		Terminate(),
	),
	Set("CheckDirection", -1),
	Set("CheckedHives", 1),
	Set("CheckingHive", 3),
	Set("CheckSkip", 0),
	Loop(
		Until(Or(
			Equal(V[int]("CheckedHives"), 6),
			NotEqual(MS[int]("counters.claimedHive"), -1),
		)),
		Subroutine(MoveToNextHive),
	),
	Condition(
		If(Equal(MS[int]("counters.claimedHive"), -1)),
		Error("Failed to claim hive!")(Status, Discord),
		Sleep(5).Seconds(),
		Redirect("OpenRoblox"),
	),
	Info("Claimed Hive: %d", MS[int]("counters.claimedHive"))(Status, Discord),
}

func init() {
	ClaimHiveRoutine.Register(ClaimHiveRoutineKind)
}
