package routines

import (
	"fmt"
	"github.com/nosyliam/revolution/macro/routines/vichop"
	. "github.com/nosyliam/revolution/pkg/common"
	. "github.com/nosyliam/revolution/pkg/control/actions"
	"image/png"
	"os"
)

const (
	OpenRobloxRoutineKind RoutineKind = "OpenRoblox"
	ResetRoutineKind      RoutineKind = "Reset"
)

func hopServer(macro *Macro) error {
	instance := V[string](GameInstance)(macro)
	if err := macro.Root.Window.HopServer(instance); err != nil {
		return err
	}

	return nil
}

func closeWindow(macro *Macro) error {
	if err := macro.Root.Window.Close(); err != nil {
		return err
	}

	macro.Root.Window = nil
	return nil
}

func openWindow(macro *Macro) error {
	if V[bool](HopServer)(macro) && macro.Root.Window != nil && fixWindow(macro) == nil {
		return hopServer(macro)
	}

	if macro.Root.Window != nil {
		if err := closeWindow(macro); err != nil {
			return err
		}
	}
	ignoreLink := V[bool](UsePublicServer)(macro)
	if win, err := macro.WinManager.OpenWindow(macro.Account, macro.Database, macro.Settings, ignoreLink); err != nil {
		return err
	} else {
		macro.Root.Window = win
		return nil
	}
}

func fixWindow(macro *Macro) error {
	if err := macro.Root.Window.Fix(); err != nil {
		return err
	}
	return nil
}

var LoadingImage = ImageSteps{
	SelectCoordinate(Change, 0, 30, 0, 150),
	Variance(4),
	Search("loading").Find(),
}

var ScienceImage = ImageSteps{
	SelectCoordinate(Change, 0, 30, 0, 150),
	Variance(4),
	Search("science").Find(),
}

var DisconnectImage = ImageSteps{
	SelectCoordinate(Change, 0, 0, 0, 100),
	Variance(2),
	Search("disconnected").Find(),
}

var HoneyOffsetImage = ImageSteps{
	SelectCoordinate(Change, 0, 0, 0, 150),
	Variance(5),
	Direction(0),
	Search("tophoney").Find(),
}

var RobloxOffsetImage = ImageSteps{
	SelectCoordinate(Change, 0, 0, 300, 300),
	Variance(2),
	Direction(0),
	Search("roblox").Find(),
}

var HotbarOffsetImage = ImageSteps{
	SelectCoordinate(Change, 0, Sub(Height, 200), Width, Height),
	Variance(5),
	Direction(0),
	Search("hotbar").Find(),
}

var ExperienceBlockedImage = ImageSteps{
	SelectCoordinate(Change, 0, Sub(Height, 50), Width, Height),
	Variance(20),
	Search("fullserver", "restricted").Find(),
}

var OpenRobloxRoutine = Actions{
	Set(HopServer, false),
	Set(GameInstance, ""),
	Routine(vichop.VicSearchRoutineKind),
	Condition(
		If(And(True(V[bool](RestartSleep)), False(V[bool](HopServer)))),
		Sleep(5).Seconds(),
	),
	Set(RetryCount, 0),
	Set(UsePublicServer, false),
	Set(NewJoin, false),
	Condition(
		If(And(NotNil(Window), False(V[bool](HopServer)))),
		Info("Attempting to close Roblox")(Status, Discord),
		Logic(closeWindow),
		Sleep(3).Seconds(),
	),
	Info("Opening Roblox")(Status, Discord),
	Loop(
		For(1, 11),
		Condition(
			If(ExecError(openWindow)),
			Error("Failed to open Roblox! Attempt: %d", Index(0))(Status, Discord),
			Sleep(5).Seconds(),
			Condition(
				If(And(GreaterThanEq(Index(), 5), True(P[bool]("window.fallbackToPublicServer")))),
				Set(UsePublicServer, true),
				If(Equal(Index(), 5)),
				Break(),
			),
			Else(),
			Condition(
				If(And(True(V[bool](FullServerSleep)))),
				Sleep(5).Seconds(),
				Set(FullServerSleep, false),
			),
			Condition(
				If(ExecError(fixWindow)),
				Error("Failed to fix window!")(Status, Discord),
				Continue(),
			),
			Condition(
				If(Or(False(V[bool](HopServer)), False(Capturing))),
				Condition(
					If(ExecError(func(macro *Macro) error {
						return macro.Root.Window.StartCapture()
					})),
					Error("Failed to start screen capture!")(Status, Discord),
					Continue(),
				),
				Else(),
				Condition(
					If(Image(ScienceImage...).Found()),
					Loop(Until(Image(ScienceImage...).NotFound()), Sleep(10)),
				),
				Loop(
					For(100),
					Condition(
						If(Equal(Index(), 179)),
						Error("Server hop failed!")(Status, Discord),
						Sleep(5).Seconds(),
					),
					Condition(
						If(Image(LoadingImage...).Found()),
						Break(),
						If(Image(ExperienceBlockedImage...).Found()),
						Set(FullServerSleep, true),
						Restart(),
					),
					Sleep(100),
				),
			),
			Loop(
				For(180),
				Condition(
					If(Equal(Index(), 179)),
					Error("No BSS was found!")(Status, Discord),
					Sleep(5).Seconds(),
					Continue(1),
				),
				Condition(
					If(Or(False(Capturing), ExecError(fixWindow))),
					Error("Failed to capture Roblox!")(Status, Discord),
					Sleep(5).Seconds(),
					Continue(1),
					Else(),
					Condition(
						If(Image(ExperienceBlockedImage...).Found()),
						Set(FullServerSleep, true),
						Restart(),
						If(Image(LoadingImage...).Found()),
						Info("Game Open")(Status, Discord),
						Set(NewJoin, true),
						Break(),
						If(Image(ScienceImage...).Found()),
						Info("Game Loaded")(Status, Discord),
						Break(),
						If(Image(DisconnectImage...).Found()),
						Info("Disconnected during reconnect")(Status, Discord),
						Sleep(5).Seconds(),
						Continue(1),
					),
				),
				Sleep(100),
			),
			Loop(
				For(180),
				Condition(
					If(Equal(Index(), 179)),
					Error("BSS load timeout exceeded!")(Status, Discord),
					Sleep(5).Seconds(),
					Continue(1),
				),
				Condition(
					If(Or(False(Capturing), ExecError(fixWindow))),
					Error("Failed to screenshot BSS!")(Status, Discord),
					Sleep(5).Seconds(),
					Continue(1),
					Else(),
					Set(OffsetX, Image(HoneyOffsetImage...).X()),
					Set(OffsetY, Image(HoneyOffsetImage...).Y()),
					Condition(
						If(And(Or(
							Image(LoadingImage...).NotFound(),
							Image(ScienceImage...).Found(),
						), GreaterThan(V[int](OffsetX), 0))),
						Info("Game Loaded")(Status, Discord),
						Break(),
						If(Image(DisconnectImage...).Found()),
						Info("Disconnected during reconnect!")(Status, Discord),
						Sleep(5).Seconds(),
						Continue(1),
					),
				),
				Sleep(100),
			),
			Break(),
		),
	),
	SetState("honeyOriginX", V[int](OffsetX)),
	SetState("honeyOriginY", V[int](OffsetY)),
	Set(OffsetX, Image(RobloxOffsetImage...).X()),
	Condition(
		If(GreaterThan(V[int](OffsetX), 0)),
		Set(OffsetY, Image(RobloxOffsetImage...).Y()),
		Subtract(OffsetX, 28),
		Subtract(OffsetY, 24),
		SetState("baseOriginX", V[int](OffsetX)),
		SetState("baseOriginY", V[int](OffsetY)),
		Else(),
		Error("Offsets could not be detected!")(Status, Discord),
		Sleep(10).Seconds(),
		Restart(),
	),
	Logic(func() { fmt.Println("offset") }),
	Set(OffsetX, Image(HotbarOffsetImage...).X()),
	Condition(
		If(GreaterThan(V[int](OffsetX), 0)),
		Set(OffsetY, Image(HotbarOffsetImage...).Y()),
		Logic(func(macro *Macro) {
			f, _ := os.Create("test.png")
			png.Encode(f, macro.GetWindow().Screenshot())
			f.Close()
			fmt.Println("Offset", macro.Scratch.Get("offset-x"), macro.Scratch.Get("offset-y"))
		}),
		Subtract(OffsetX, 28),
		Subtract(OffsetY, 24),
		SetState("hotbarOriginX", V[int](OffsetX)),
		SetState("hotbarOriginY", V[int](OffsetY)),
		Else(),
		Error("Offsets could not be detected!")(Status, Discord),
		Sleep(10).Seconds(),
		Restart(),
	),

	Condition(
		If(Nil(Window)),
		Error("Waiting 30 seconds before retrying")(Status, Discord),
		Sleep(30).Seconds(),
		Restart(),
	),
	Condition(
		If(False(V[bool](RestartSleep))),
		Logic(func(macro *Macro) {
			macro.Input.Reset()
			go macro.Scheduler.Start()
		}),
	),
	Set(RestartSleep, true),
}

func init() {
	OpenRobloxRoutine.Register(OpenRobloxRoutineKind)
}
