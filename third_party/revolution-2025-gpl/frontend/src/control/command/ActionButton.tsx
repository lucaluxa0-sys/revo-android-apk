import classes from "./ActionButton.module.css"
import {Button} from "@mantine/core";
import {IconDotsVertical} from "@tabler/icons-react";
import React from "react";

interface ActionButtonProps {
    action: string
    icon: React.ReactNode
    execute: () => void
    disabled?: boolean
}

export default function ActionButton(props: ActionButtonProps) {
    return (
        <Button.Group>
            <Button
                size="compact-sm"
                classNames={classes}
                fz={16}
                leftSection={props.icon}
                disabled={props.disabled}
                onClick={props.execute}
            >
                { props.action }
            </Button>
            <Button size="compact-sm" p={0} style={{maxWidth: "auto"}}>
                <IconDotsVertical style={{width: '20px', height: '80%'}} stroke={1.5}/>
            </Button>
        </Button.Group>
    )
}