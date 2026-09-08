SetName("vic_path")
if not State.SearchedFields then
    State.SearchedFields = {}
end

function WalkCannon()
    SetZoom(2)
    Walk(Direction.Forward, 83.2)
    Walk(Direction.Backward, 6)
    Walk(Direction.Right, 4)
    Sleep(100)
    Walk(Direction.Right, 94)
    Walk(Direction.Forward, 4)

    Checkpoint({
        Detector = "press_e",
        Walk = function()
            KeyDown(Key.Right)
            KeyPress(Key.Space)
            Sleep(1500)
            KeyUp(Key.Right)
        end,
        Nudge = function()
            WalkAsync(Direction.Forward, 2)
            KeyPress(Key.Space)
            Sleep(200)
            KeyDown(Key.Right)
            Sleep(500)
            KeyUp(Key.Right)
            Sleep(500)
        end,
        MaxAttempts = 5
    })
end

function WalkMountain()
    Status("Searching: Mountain Top")
    Sleep(500)
    KeyPress(Key.E)
    for i = 1, 4 do
        KeyPress(Key.RotLeft)
        Sleep(100)
    end

    Sleep(1100)

    KeyPress(Key.Space)
    KeyPress(Key.Space)
    KeyDown(Key.Right)

    Sleep(2600)

    KeyUp(Key.Right)
    KeyDown(Key.Forward)

    Sleep(1800)

    KeyPress(Key.Space)
    KeyUp(Key.Forward)

    Walk(Direction.Forward, 130)
    Walk(Direction.Left, 196)
    Walk(Direction.Backward, 13)

    KeyPress(Key.Shift)

    for i = 1, 2 do
        KeyPress(Key.RotRight)
    end

    for i = 1, 9 do
        KeyPress(Key.RotDown)
    end
    for i = 1, 2 do
        KeyPress(Key.RotUp)
    end
    Sleep(50)

    if PerformDetection("mountain") then
        Exit()
        return
    end

    KeyPress(Key.Shift)
end

function WalkSpider()
    Status("Searching: Spider")
    for i = 1, 4 do
        KeyPress(Key.RotLeft)
    end
    Sleep(50)

    KeyPress(Key.RotUp)
    Sleep(50)
    KeyPress(Key.RotUp)

    Walk(Direction.Backward, 197)
    Walk(Direction.Left, 93.6)

    KeyPress(Key.Space)
    Sleep(350)
    KeyPress(Key.Space)
    Sleep(3200)

    Walk(Direction.Forward, 78)
    Walk(Direction.Right, 26)
    Walk(Direction.Forward, 56)

    KeyPress(Key.Shift)

    for i = 1, 9 do
        KeyPress(Key.RotDown)
    end

    for i = 1, 5 do
        KeyPress(Key.RotUp)
    end

    for i = 1, 10 do
        KeyPress(Key.ZoomOut)
    end

    if PerformDetection("spider") then
        Exit()
        return
    end

    KeyPress(Key.Shift)
end

function WalkCactus()
    Status("Searching: Cactus")
    for i = 1, 2 do
        KeyPress(Key.RotUp)
    end

    Walk(Direction.Left, 2.6)
    Walk(Direction.Backward, 14)
    Walk(Direction.Left, 30)

    KeyPress(Key.Space)
    Sleep(200)

    Walk(Direction.Forward, 26)
    Walk(Direction.Right, 39)

    WalkAsync(Direction.Forward, 130)
    Walk(Direction.Right, 130)

    Walk(Direction.Forward, 20)
    KeyPress(Key.Space)
    Walk(Direction.Forward, 46)

    Walk(Direction.Forward, 90)
    Walk(Direction.Right, 30)

    KeyPress(Key.Shift)

    for i = 1, 9 do
        KeyPress(Key.RotDown)
    end

    Walk(Direction.Backward, 15.6)
    Walk(Direction.Right, 10)

    Sleep(1000)

    if PerformDetection("cactus") then
        Exit()
        return
    end

    Walk(Direction.Backward, 50.7)
    Walk(Direction.Right, 10)

    if PerformDetection("cactus") then
        Exit()
        return
    end


    KeyPress(Key.Shift)

    Walk(Direction.Forward, 78)
end

function WalkRose()
    Status("Searching: Rose")
    for i = 1, 6 do
        KeyPress(Key.RotUp)
    end

    Walk(Direction.Left, 104)

    KeyPress(Key.Space)

    Walk(Direction.Left, 70.2)
    Walk(Direction.Forward, 39)

    KeyPress(Key.Shift)

    for i = 1, 2 do
        KeyPress(Key.RotLeft)
    end

    Walk(Direction.Backward, 46.8)

    for i = 1, 9 do
        KeyPress(Key.RotDown)
    end

    for i = 1, 5 do
        KeyPress(Key.RotUp)
    end

    Walk(Direction.Right, 1.3)
    Walk(Direction.Backward, 1.3)

    for i = 1, 10 do
        KeyPress(Key.ZoomOut)
    end

    if PerformDetection("rose") then
        Exit()
        return
    end

    for i = 1, 2 do
        KeyPress(Key.ZoomIn)
    end

    if PerformDetection("rose") then
        Exit()
        return
    end
end

function WalkPepper()
    Status("Searching: Pepper")

    Checkpoint({
        Detector = "vic_pepper/jump0",
        Walk = function()
            Walk(Direction.Right, 70)
        end,
        Nudge = function()
            Walk(Direction.Right, 8)
        end,
        MaxAttempts = 5
    })

    Checkpoint({
        Detector = "vic_pepper/jump1",
        Walk = function()
            KeyPress(Key.Space)
            KeyPress(Key.Space)
            Sleep(50)

            Walk(Direction.Right, 16)
            Walk(Direction.Forward, 12)
        end,
    })

    Checkpoint({
        Detector = "vic_pepper/jump2",
        Walk = function()
            KeyPress(Key.Space)
            KeyPress(Key.Space)

            Sleep(100)

            Walk(Direction.Forward, 58)
            Walk(Direction.Right, 20)
        end,
    })


    Checkpoint({
        Detector = "vic_pepper/jump3",
        Walk = function()
            SetZoom(0)
            KeyDown(Key.Forward)
            KeyPress(Key.Space)
            Sleep(800)
            KeyPress(Key.Space)
            Sleep(1800)
            KeyUp(Key.Forward)
        end,
    })

    KeyDown(Key.Forward)
    KeyPress(Key.Space)
    Sleep(2600)

    KeyDown(Key.Right)
    Sleep(1000)
    KeyUp(Key.Forward)

    KeyPress(Key.Space)
    KeyPress(Key.Space)
    Sleep(3000)
    KeyUp(Key.Right)

    Walk(Direction.Backward, 7.8)

    SetZoom(5)
    SetPitch(-2)
    KeyPress(Key.Shift)
    Sleep(100)

    if PerformDetection("pepper") then
        Exit()
        return
    end

    KeyPress(Key.Shift)
end

function WalkCannonFromPepper()
    ExecuteWithAlignment({
        Medium = function()
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
            Walk(Direction.Left, 40)
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
        end,
        Low = function()
            KeyPress(Key.Space)
            KeyDown(Key.Right)
            Sleep(200)
            KeyUp(Key.Right)
            Walk(Direction.Backward, 40)
            KeyPress(Key.Space)
            KeyDown(Key.Left)
            KeyDown(Key.Backward)
            Sleep(200)
            KeyPress(Key.Space)
            Sleep(2650)
            KeyUp(Key.Backward)
            Sleep(750)
            KeyUp(Key.Left)
            Checkpoint({
                Detector = "press_e",
                Walk = function()
                    KeyPress(Key.Space)
                    Sleep(500)
                end,
                Nudge = function()
                    WalkAsync(Direction.Forward, 4)
                    Walk(Direction.Left, 8)
                end,
                MaxAttempts = 5
            })
        end,
    })
end

WalkCannon()
if not State.SearchedFields["pepper"] then
    WalkPepper()
    WalkCannonFromPepper()
    State.SearchedFields["pepper"] = true
end
if not State.SearchedFields["mountain"] then
    WalkMountain()
    State.SearchedFields["mountain"] = true
end
WalkSpider()
WalkCactus()
WalkRose()
