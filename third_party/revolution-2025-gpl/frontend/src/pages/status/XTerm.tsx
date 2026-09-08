import React, { useEffect, useRef } from 'react';
import { Terminal, ITerminalOptions } from 'xterm';
import { FitAddon } from '@xterm/addon-fit';

import 'xterm/css/xterm.css';

const isWebGl2Supported = !!document.createElement('canvas').getContext('webgl2');

type EventHandler = (event?: any) => void;

interface XTermProps {
    id?: string;
    className?: string;
    options?: ITerminalOptions;
    onBell?: EventHandler;
    onBinary?: EventHandler;
    onCursorMove?: EventHandler;
    onData?: EventHandler;
    onKey?: EventHandler;
    onLineFeed?: EventHandler;
    onRender?: EventHandler;
    onResize?: EventHandler;
    onScroll?: EventHandler;
    onSelectionChange?: EventHandler;
    onTitleChange?: EventHandler;
    onWriteParsed?: EventHandler;
    onInit?: (terminal: Terminal) => void;
    onDispose?: (terminal: Terminal) => void;
}

function useBind(
    termRef: React.MutableRefObject<Terminal | null>,
    handler: EventHandler | undefined,
    eventName: keyof Terminal
) {
    useEffect(() => {
        if (!termRef.current || typeof handler !== 'function') return;

        const term = termRef.current;
        // @ts-ignore
        const eventBinding = term[eventName]?.(handler);

        return () => {
            eventBinding?.dispose();
        };
    }, [handler, termRef, eventName]);
}

export const XTerm: React.FC<XTermProps> = ({
                                                id,
                                                className,
                                                options,
                                                onBell,
                                                onBinary,
                                                onCursorMove,
                                                onData,
                                                onKey,
                                                onLineFeed,
                                                onRender,
                                                onResize,
                                                onScroll,
                                                onSelectionChange,
                                                onTitleChange,
                                                onWriteParsed,
                                                onInit,
                                                onDispose,
                                            }) => {
    const termRef = useRef<Terminal | null>(null);
    const divRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        const term = new Terminal({ ...options, rows: 16, cols: 35, allowProposedApi: true });
        termRef.current = term;
        term.open(divRef.current!)

        return () => {
            if (typeof onDispose === 'function') onDispose(term);
            term.dispose();
            termRef.current = null;
        };
    }, [options, onDispose]);

    useBind(termRef, onBell, 'onBell');
    useBind(termRef, onBinary, 'onBinary');
    useBind(termRef, onCursorMove, 'onCursorMove');
    useBind(termRef, onData, 'onData');
    useBind(termRef, onKey, 'onKey');
    useBind(termRef, onLineFeed, 'onLineFeed');
    useBind(termRef, onRender, 'onRender');
    useBind(termRef, onResize, 'onResize');
    useBind(termRef, onScroll, 'onScroll');
    useBind(termRef, onSelectionChange, 'onSelectionChange');
    useBind(termRef, onTitleChange, 'onTitleChange');
    useBind(termRef, onWriteParsed, 'onWriteParsed');

    useEffect(() => {
        if (termRef.current && typeof onInit === 'function') {
            onInit(termRef.current);
        }
    }, [onInit]);

    return <div id={id} className={className} ref={divRef}></div>;
};
