import React from "react";
import {Divider, Flex, Text} from "@mantine/core";
import textClasses from "../../assets/css/NonSelectableText.module.css";

export default function TextContainer(props: React.PropsWithChildren<{width?: number, label: string}>) {
    return (
        <Flex align="center" justify="left" h={26} style={(theme) => ({
            backgroundColor: theme.colors.gray[1],
            borderColor: theme.colors.gray[5],
            borderWidth: 1,
            borderStyle: 'solid',
            flexGrow: 1,
            display: 'flex',
            borderRadius: '2px',
            width: props.width ? `${props.width}px` : undefined,
            maxWidth: props.width ? `${props.width}px` : undefined
        })}>
            <Text fw={700} size="sm" p={4} classNames={textClasses}>{ props.label }</Text>
            <div style={{flexGrow: 1}}/>
            <Text size="sm" p={4} classNames={textClasses}>{ props.children }</Text>
        </Flex>
    )
}