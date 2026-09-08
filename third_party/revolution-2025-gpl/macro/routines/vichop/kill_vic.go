package vichop

import (
	"github.com/nosyliam/revolution/macro/routines/hive"
	. "github.com/nosyliam/revolution/pkg/common"
	. "github.com/nosyliam/revolution/pkg/control/actions"
	"github.com/nosyliam/revolution/pkg/vichop"
)

const KillVicRoutineKind RoutineKind = "KillVic"

var Prologue = Actions{
	CancelPattern(),
	Logic(vichop.StopDetectingBattle),
	Set(VicField, ""),
	Redirect("OpenRoblox"),
}

var KillVic = Actions{
	Info("Killing Vicious Bee: %s", V[string](VicField))(Status, Discord),
	Condition(
		If(True(V[bool](PerformReset))),
		ResetCharacter(),
		Set(PerformReset, false),
	),
	Routine(hive.ClaimHiveRoutineKind),
	Routine(hive.GotoCannonRoutineKind),
	Logic(vichop.StartDetectingBattle),
	Condition(
		If(Equal(V[string](VicField), "pepper")),
		ExecutePattern("vic_pepper").Async(),
		If(Equal(V[string](VicField), "mountain")),
		ExecutePattern("vic_mountain").Async(),
		If(Equal(V[string](VicField), "spider")),
		ExecutePattern("vic_spider").Async(),
		If(Equal(V[string](VicField), "cactus")),
		ExecutePattern("vic_cactus").Async(),
		If(Equal(V[string](VicField), "rose")),
		ExecutePattern("vic_rose").Async(),
	),
	Loop(
		For(6000),
		Condition(
			If(True(vichop.BattleActive)),
			CancelPattern(),
			Info("Battling Vicious Bee: %s", V[string](VicField))(Status, Discord),
			ExecutePattern("vic_kill").Async(),
			Loop(
				For(3000), // TODO: Custom battle timeout
				Condition(
					If(Equal(Index(), 2999)),
					Error("Vicious Bee battle timed out!")(Status, Discord),
					Subroutine(Prologue),
					If(False(vichop.BattleActive)),
					Info("Vicious Bee defeated")(Status, Discord),
					Subroutine(Prologue),
				),
				Sleep(10),
			),
		),
		Sleep(10),
	),
	Subroutine(Prologue),
}

func init() {
	KillVic.Register(KillVicRoutineKind)
}
