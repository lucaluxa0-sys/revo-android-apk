import {Group, Paper} from "@mantine/core";
import React, {useState} from "react";
import FloatingSelector from "../../components/FloatingSelector";
import Networking from "./Networking";
import Game from "./Game";
import Macro from "./Macro";

export default function Settings() {
    const pages: {[key: string]: React.ReactNode} = {
        "Macro": <Macro/>,
        "Game": <Game/>,
        "Networking": <Networking/>,
        "Presets": <></>,
        "Accounts": <></>
    }
    const [active, setActive] = useState(0)

    return (
        <Group style={{height: '100%', flexWrap: 'nowrap'}} gap={8}>
            <Paper shadow="xs" maw={150} miw={150} style={{height: '100%'}}>
                <FloatingSelector selections={Object.keys(pages)} active={active} setActive={setActive}/>
            </Paper>

            { pages[Object.keys(pages)[active]] }
        </Group>
    )
}