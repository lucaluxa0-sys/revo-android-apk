package routines

import (
	"github.com/nosyliam/revolution/macro/routines/vichop"
	. "github.com/nosyliam/revolution/pkg/common"
	. "github.com/nosyliam/revolution/pkg/control/actions"
)

const MainRoutineKind RoutineKind = "Main"

var InitializeRoutine = Actions{
	Set(VicField, ""),
	Set(FullServerSleep, false),
	Set(Initialized, true),
}

var MainRoutine = Actions{
	Condition(
		If(False(V[bool](Initialized))),
		Subroutine(InitializeRoutine),
	),
	Condition(
		If(False(V[bool](RestartSleep))),
		Redirect(OpenRobloxRoutineKind),
	),
	Condition(
		If(NotEqual(V[string](VicField), "")),
		Routine(vichop.KillVicRoutineKind),
		If(True(P[bool]("vicHop.enabled"))),
		Routine(vichop.VicSearchRoutineKind),
	),
	/*Condition(
		If(Equal(MS[int]("counters.claimedHive"), -1)),
		Routine(hive.ClaimHiveRoutineKind),
		Routine(hive.GotoCannonRoutineKind),
	),*/
	Info("Idling")(Status),
	Sleep(1).Seconds(),
}

func init() {
	MainRoutine.Register(MainRoutineKind)
}
