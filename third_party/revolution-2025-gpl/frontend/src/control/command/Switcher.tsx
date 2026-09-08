import classes from "./Switcher.module.css"
import {Button, Container, Flex, Group, Text} from "@mantine/core";
import React, {useContext} from "react";
import {IconChevronLeft, IconChevronRight} from "@tabler/icons-react";
import TextContainer from "./TextContainer";
import {KeyedObject, RuntimeContext} from "../../hooks/useRuntime";
import {SetAccountPreset} from "../../../wailsjs/go/main/Macro";

export function PresetSwitcher() {
    const runtime = useContext(RuntimeContext)
    const settings = runtime.Object('settings')
    const state = runtime.Object('state.config')
    const account = state.Value<string>('activeAccount', 'Default')
    const presets = settings.List<KeyedObject>('presets').Values(true)
    const activePreset = runtime.Preset()

    let activeIdx = presets.findIndex((p) => p.object == activePreset)
    if (activeIdx == -1) {
        activeIdx = 0
    }

    console.log(activePreset)

    const changePreset = (delta: number) => SetAccountPreset(account, presets[activeIdx + delta].key)

    return (
        <Group mah={26} style={{flexGrow: 1, gap: 4}}>
            <TextContainer label="Preset">{ presets[activeIdx]?.key || 'Default' }</TextContainer>
            <Button
                radius="50%"
                size="xs"
                disabled={activeIdx == 0}
                classNames={classes}
                onClick={() => changePreset(-1)}
            >
                <IconChevronLeft size={16} style={{marginRight: 2}}/>
            </Button>
            <Button
                radius="50%"
                size="xs"
                disabled={activeIdx == presets.length - 1}
                classNames={classes}
                onClick={() => changePreset(1)}
            >
                <IconChevronRight size={16} style={{marginLeft: 2}}/>
            </Button>
        </Group>
    )
}

export function AccountSwitcher() {
    return (
        <Group mah={26} style={{flexGrow: 1, gap: 4}}>
            <TextContainer label="Account">Default</TextContainer>
            <Button
                radius="50%"
                size="xs"
                classNames={classes}
            >
                <IconChevronLeft size={16} style={{marginRight: 2}}/>
            </Button>
            <Button
                radius="50%"
                size="xs"
                classNames={classes}
            >
                <IconChevronRight size={16} style={{marginLeft: 2}}/>
            </Button>
        </Group>
    )
}