package vichop

import (
	. "github.com/nosyliam/revolution/pkg/common"
	. "github.com/nosyliam/revolution/pkg/control/actions"
	"github.com/nosyliam/revolution/pkg/vichop"
)

const VicSearchRoutineKind RoutineKind = "VicSearch"

var VicSearch = Actions{
	Condition(
		If(False(P[bool]("vicHop.enabled"))),
		Terminate(),
	),
	Condition(
		If(And(Equal(V[string](GameInstance), ""), Equal(P[string]("vicHop.role"), "main"))),
		Logic(vichop.ReadQueue),
		Condition(
			If(NotEqual(V[string](GameInstance), "")),
			Info("Searching")(Status, Discord),
			Terminate(),
		),
	),
	// Check if we're being called from OpenRoblox so that we can find a new server
	Condition(
		If(And(Equal(V[string](GameInstance), ""), True(P[bool]("vicHop.serverHop")))),
		Info("Finding new server")(Status, Discord),
		Set(GameInstance, func(macro *Macro) string {
			server, err := macro.VicHop.FindServer(macro)
			if server == "" || err != nil {
				macro.SetError(err, "Failed to find server")
			}
			return server
		}),
		Set(HopServer, true),
		Terminate(),
		If(Equal(V[string](GameInstance), "")),
		Set(HopServer, true),
		Info("Waiting for server")(Status, Discord),
		Loop(Forever(), Sleep(100)),
	),
	Set(VicField, ""),
	// Check for night
	Routine(DetectNightRoutineKind),
	Condition(
		If(False(V[bool](NightDetected))),
		Redirect("OpenRoblox"),
	),
	// Perform the vic search. Vic manager will handle redirecting on detection
	// We'll continue to scan for vicious bee attacking/defeated GUIs in case another player finds it
	ExecutePattern("vic_path").Async(),
	WaitForPatternStart(),
	Logic(vichop.StartDetectingBattle),
	Loop(Until(Or(False(PatternExecuting), True(vichop.BattleActive))), Sleep(100)),
	Info("Search Ended")(Status),
	CancelPattern(),
	Logic(vichop.StopDetectingBattle),
	Redirect("OpenRoblox"),
}

func init() {
	VicSearch.Register(VicSearchRoutineKind)
}
