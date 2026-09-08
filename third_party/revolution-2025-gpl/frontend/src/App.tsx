import "@mantine/core/styles.css";
import {ModalsProvider} from '@mantine/modals';
import {Flex, MantineProvider, Overlay} from "@mantine/core";
import {theme} from "./theme";
import {RuntimeContext} from "./hooks/useRuntime";
import {useContext, useEffect, useState} from "react";
import State from "./control/command/State";
import Macro from "./control/Macro";
import {useViewportSize} from "@mantine/hooks";

function App() {
    const viewport = useViewportSize()
    const runtime = useContext(RuntimeContext)
    const disconnected = runtime.Disconnected()
    const [disconnectTimer, setDisconnectTimer] = useState(0)

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(runtime.Ready)
    useEffect(() => {
        if (!disconnected) {
            setDisconnectTimer(0)
            return
        }

        const timer = setInterval(() => {
            setDisconnectTimer((v) => v + 0.1)
        }, 100)

        return () => {
            clearInterval(timer)
        }
    }, [disconnected])

    return (
        <MantineProvider theme={theme}>
            <ModalsProvider>
                <Flex
                    direction="column"
                    style={{height: viewport.height, position: 'relative'}}
                >
                    {disconnected &&
                        <Overlay color="#000" fz="30" fw={600} c="gray.3" backgroundOpacity={0.6} pb={30} style={{
                            position: 'absolute',
                            inset: 0,
                            display: 'flex',
                            justifyContent: 'center',
                            alignItems: 'center',
                        }}>
                            Connecting to Backend... ({disconnectTimer.toFixed(1)})
                        </Overlay>}
                    <Macro/>
                    <State/>
                </Flex>
            </ModalsProvider>
        </MantineProvider>
    )
}

export default App
