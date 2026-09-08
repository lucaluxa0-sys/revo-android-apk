import React, {useContext} from "react";
import {RuntimeContext} from "../../hooks/useRuntime";
import {Grid, NumberInput, Stack, Switch} from "@mantine/core";
import ControlBox from "../../components/ControlBox";

export default function Game() {
    const runtime = useContext(RuntimeContext)
    const preset = runtime.Preset()
    const player = preset.Object("player")
    const moveSpeed = player.Value("moveSpeed", 16)

    return (
        <Stack style={{height: '100%', flexGrow: 1, gap: 4}}>
            <ControlBox title="Player Movespeed">
                <NumberInput w={150} size="xs" value={moveSpeed}
                             onChange={(value) => player.Set<number>("moveSpeed", Number(value))}/>
            </ControlBox>
        </Stack>
    )
}