SetName("test")

WalkAsync(Direction.Left, 4)
Walk(Direction.Backward, 20)
KeyPress(Key.Space)
Sleep(500)
KeyPress(Key.Space)
KeyDown(Key.Backward)
Sleep(1600)
KeyPress(Key.Space)
KeyUp(Key.Backward)
WalkAlign(Direction.Backward, 16)
WalkAlign(Direction.Left, 40)
Walk(Direction.Right, 16)
Walk(Direction.Forward, 16)
SetYaw(6)
Walk(Direction.Forward, 96)
Walk(Direction.Left, 44)
Checkpoint({
    Detector = "press_e",
    Walk = function()
        Walk(Direction.Forward, 80)
    end,
    Nudge = function()
        Walk(Direction.Forward, 6)
    end,
    MaxAttempts = 10
})

