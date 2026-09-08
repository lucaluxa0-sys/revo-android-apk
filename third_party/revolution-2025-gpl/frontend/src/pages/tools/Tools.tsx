import {Group, Paper} from "@mantine/core";
import React, {useState} from "react";
import FloatingSelector from "../../components/FloatingSelector";
import JellyTool from "./JellyTool";
import VicHop from "./VicHop";

export default function Tools() {
    const tools: {[key: string]: React.ReactNode} = {
        "Auto-Jelly": <JellyTool/>,
        "Auto-Clicker": <></>,
        "Boost Macro": <></>,
        "Vic Hop": <VicHop/>
    }
    const [active, setActive] = useState(0)

    return (
        <Group style={{height: '100%', flexWrap: 'nowrap'}} gap={8}>
            <Paper shadow="xs" w={150} style={{height: '100%'}}>
                <FloatingSelector selections={Object.keys(tools)} active={active} setActive={setActive}/>
            </Paper>

            { tools[Object.keys(tools)[active]] }
        </Group>
    )
}