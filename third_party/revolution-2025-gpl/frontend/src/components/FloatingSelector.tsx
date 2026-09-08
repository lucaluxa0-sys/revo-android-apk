import React, {SetStateAction, useState} from "react";
import {FloatingIndicator, UnstyledButton} from "@mantine/core";
import classes from "./FloatingSelector.module.css"

interface FloatingSelector {
    selections: string[]
    active: number
    setActive: React.Dispatch<SetStateAction<number>>
}

export default function FloatingSelector(props: FloatingSelector) {
    const [rootRef, setRootRef] = useState<HTMLDivElement | null>(null);
    const [controlsRefs, setControlsRefs] = useState<Record<string, HTMLButtonElement | null>>({});

    const setControlRef = (index: number) => (node: HTMLButtonElement) => {
        controlsRefs[index] = node;
        setControlsRefs(controlsRefs);
    };

    const controls = props.selections.map((item, index) => (
        <UnstyledButton
            key={item}
            className={classes.control}
            ref={setControlRef(index)}
            onClick={() => props.setActive(index)}
            mod={{active: props.active === index}}
            style={{width: '100%', textAlign: 'center'}}
        >
            <span className={classes.controlLabel}>{item}</span>
        </UnstyledButton>
    ));

    return (
        <div className={classes.root} ref={setRootRef}>
            {controls}

            <FloatingIndicator
                target={controlsRefs[props.active]}
                parent={rootRef}
                className={classes.indicator}
            />
        </div>
    );
}