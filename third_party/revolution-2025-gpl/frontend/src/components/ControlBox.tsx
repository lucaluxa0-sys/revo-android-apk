import {Divider, MantineStyleProp, Paper, Text} from "@mantine/core";
import React from "react";

interface ControlBoxProps {
    title?: string
    description?: string
    height?: number
    grow?: boolean
    style?: MantineStyleProp
    leftAction?: React.ReactNode
}

export default function(props: React.PropsWithChildren<ControlBoxProps>) {
    return (
        <Paper shadow="xs" style={{
            width: '100%',
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'center',
            padding: '4px',
            flexGrow: props.grow ? 1 : undefined,
            height: props.height ? `${props.height}px` : undefined,
            ...props.style
        }}>
            {props.leftAction ?? <Text fz={14} ml={4}>{ props.title }</Text>}
            <div style={{flexGrow: 1}}/>
            { props.children }
        </Paper>
    )
}