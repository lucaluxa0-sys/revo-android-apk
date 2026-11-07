-- Restored offline from the previously evidenced Revolution e_lol gather geometry.
-- Not claimed to be official contemporary Revo source. Width=2, Length=8 -> 18 steps.
SetName("e_lol")
Walk(Left, 5 * Pattern.Width)
for i=1,math.floor(Pattern.Width) do
    Walk(Backward, 2.5 * Pattern.Length)
    Walk(Right, 2.5 * Pattern.Width)
    Walk(Forward, 2.5 * Pattern.Length)
    Walk(Right, 2.5 * Pattern.Width)
end
for i=1,math.floor(Pattern.Width) do
    Walk(Backward, 2.5 * Pattern.Length)
    Walk(Left, 2.5 * Pattern.Width)
    Walk(Forward, 2.5 * Pattern.Length)
    Walk(Left, 2.5 * Pattern.Width)
end
Walk(Right, 5 * Pattern.Width)
