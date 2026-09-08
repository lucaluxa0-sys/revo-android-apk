import React, {createContext, useEffect, useState} from "react";
import {EventsEmit, EventsOn} from "../../wailsjs/runtime";
import {flushSync} from "react-dom";

interface BaseEvent {
    id?: number
}

interface SetEvent {
    op: "set"
    value: Value
}

interface AppendEvent {
    op: "append"
    primitive: boolean
    key?: string
    value?: Value
}

interface DeleteEvent {
    op: "delete"
}

interface HistoricalEvent {
    op: "set" | "append" | "delete"
    path: Path
    id: number
    timeout: number
    reverted?: boolean
    index?: string | number
    previousValue?: ListValue
    processed?: boolean
}

interface RollbackEvent {
    op: "rollback"
    record: HistoricalEvent
}

type EmittedEvent = SetEvent | AppendEvent | DeleteEvent
type Event = (RollbackEvent | EmittedEvent) & BaseEvent

type Value = number | string | boolean

export interface KeyedObject {
    key: string
    object: Object
}

type ListValue = KeyedObject | Object | Value

type Dispatch<T> = React.Dispatch<React.SetStateAction<T>>

interface Field {
    value: Value
    dispatch?: Dispatch<Value>
}

interface Reactive {
    // Pass the event data to the object associated with the given path
    Receive(path: Path, event: Event): void

    // Return the reactive object at the given path
    Object(path: Path | string): Object

    // Flush all values to the frontend by calling every dispatcher down the object tree
    Flush(): void
}

interface PathComponent {
    val: string
    brackets: boolean
}

export class Path extends String {
    private index: number = 0;
    components: PathComponent[] = [];

    constructor(path: string, components?: PathComponent[]) {
        super(path);
        if (components) {
            this.components = components
            return
        }
        const regex = /(\w+)|\[((?:\[[^\]]*\]|[^\]])*)\]/g;

        let match;
        while ((match = regex.exec(path)) !== null) {
            if (match[1]) {
                this.components = [...this.components, {val: match[1], brackets: false}]
            }
            if (match[2]) {
                this.components = [...this.components, {val: match[2], brackets: true}]
            }
        }
    }

    public reset(): Path {
        this.index = 0
        return this
    }

    public finalize(): Path {
        this.index = this.components.length - 1
        return this
    }

    public increment(): Path {
        this.index += 1
        return this
    }

    public decrement(): Path {
        this.index -= 1
        return this
    }

    public get value(): string {
        return this.components[this.index].val
    }

    public get brackets(): boolean {
        return this.components[this.index].brackets
    }

    public get final(): boolean {
        return this.components.length == this.index
    }

    public get peekFinal(): boolean {
        return this.components.length - 1 == this.index
    }

    public extend(path: string, brackets?: boolean): Path {
        return new Path(brackets ? `${this}[${path}]` : `${this}.${path}`, [...this.components, {
            val: path,
            brackets: Boolean(brackets)
        }])
    }
}

export class Object implements Reactive {
    private readonly path: Path;
    private readonly runtime: Runtime;

    private objects: { [field: string]: Reactive } = {};
    private values: { [field: string]: Field } = {};

    constructor(path: Path, runtime: Runtime) {
        this.runtime = runtime
        this.path = path
    }

    public Concrete<T extends Value>(field: string): T | undefined {
        return this.values[field]?.value as T
    }

    public Value<T extends Value>(field: string, defaultValue: T): T {
        let def: Field = this.values[field] ? {value: this.values[field].value} : {value: defaultValue}
        const [value, dispatch] = useState<Value>(def.value)
        this.values[field] = {...def, dispatch: dispatch}
        return value as T
    }

    public Set<T extends Value>(field: string, value: T, noEmit?: boolean) {
        const previousValue = this.values[field]?.value
        let data: Field = this.values[field] || {value: value}
        data.dispatch && data.dispatch(value)
        this.values[field] = {...data, value: value}
        if (!noEmit)
            this.runtime.Emit(this.Field(field), {op: "set", value: value}, previousValue)
    }

    public SetAfterInitialization<T extends Value>(field: string, value: T) {
        const previousValue = this.values[field]?.value
        let data: Field = this.values[field] || {value: value}
        data.dispatch && data.dispatch(value)
        this.values[field] = {...data, value: value}
        this.runtime.EmitAfterInit(this.Field(field), {op: "set", value: value}, previousValue)
    }

    public List<T extends ListValue>(field: string): List<T> {
        if (!this.objects[field]) {
            this.objects[field] = new List(this.path.extend(field), this.runtime)
        }
        return this.objects[field] as List<T>
    }

    public Receive(path: Path, event: Event): void {
        switch (event.op) {
            case "rollback":
                if (!path.peekFinal) {
                    this.objects[path.value].Receive(path.increment(), event)
                    return
                }
                const value = this.values[path.value]
                value.value = event.record.previousValue! as Value
                value.dispatch && value.dispatch(value.value)
                break
            case "set":
                if (!path.peekFinal) {
                    if (!this.objects[path.value]) {
                        this.objects[path.value] = new Object(this.path.extend(path.value), this.runtime)
                    }
                    this.objects[path.value].Receive(path.increment(), event)
                } else {
                    let field: Field | undefined
                    if ((field = this.values[path.value]) != undefined) {
                        field.value = event.value
                        field.dispatch && field.dispatch(event.value)
                    } else {
                        this.values[path.value] = {value: event.value}
                    }
                }
                break
            case "append":
                if (path.increment().peekFinal) {
                    path.decrement()
                    if (!this.objects[path.value])
                        this.objects[path.value] = new List(this.path.extend(path.value), this.runtime)
                    let list = this.objects[path.value] as List<any>
                    list.primitive = event.primitive
                    list.keyField = event.key
                } else {
                    path.decrement()
                    if (!this.objects[path.value])
                        this.objects[path.value] = new Object(this.path.extend(path.value), this.runtime)
                }
            case "delete":
                this.objects[path.value].Receive(path.increment(), event)
        }
    }

    Object(path: Path | string): Object {
        if (typeof path == 'string') {
            path = new Path(path)
        }
        if (path.final) {
            return this
        }
        if (!this.objects[path.value]) {
            if (!path.peekFinal) {
                if (path.increment().brackets) {
                    path.decrement()
                    this.objects[path.value] = new List(this.path.extend(path.value, true), this.runtime)
                    return this.objects[path.value].Object(path.increment())
                }
                path.decrement()
            }
            this.objects[path.value] = new Object(this.path.extend(path.value), this.runtime)
        }
        return this.objects[path.value].Object(path.increment())
    }

    Flush() {
        for (const value of globalThis.Object.values(this.values)) {
            if (value.dispatch) {
                value.dispatch(value.value)
            }
        }
        for (const object of globalThis.Object.values(this.objects)) {
            object.Flush()
        }
    }

    public Field(field: string): Path {
        return new Path(`${this.path}.${field}`)
    }
}

export class List<T extends ListValue> implements Reactive {
    private readonly path: Path;
    private readonly runtime: Runtime;

    private dispatch?: Dispatch<T[]>
    private values: Array<T> = []
    private reactive?: boolean = false

    public primitive: boolean | undefined = undefined;
    public keyField?: string = '';

    constructor(path: Path, runtime: Runtime) {
        this.path = path;
        this.runtime = runtime;
    }

    private index(path: Path | string): number {
        if (typeof path == 'string') {
            path = new Path(path)
        }
        let index: number;
        if (this.keyField) {
            index = (this.values as KeyedObject[]).findIndex((v) => v.key == (path as Path).value)
        } else {
            index = Number((path as Path).value)
        }
        return index
    }

    public Values(reactive?: boolean): T[] {
        if (reactive)
            this.reactive = true
        const [values, dispatch] = useState<T[]>(this.values)
        useEffect(() => {
            this.dispatch = dispatch
            return () => {
                this.dispatch = undefined
            }
        })
        return values as T[]
    }

    public Append(key?: string, value?: Value): ListValue | undefined {
        let object: ListValue | undefined = value
        if (this.primitive) {
            this.values = [...this.values, value! as T]
        } else if (this.keyField) {
            const reactive = new Object(this.Key(key!), this.runtime)
            reactive.Set(this.keyField, key!, true);
            object = {key: key!, object: reactive}
            this.values = [...this.values, object as T]
        } else {
            object = new Object(this.Key(key!), this.runtime)
            this.values = [...this.values, object as T]
        }
        this.dispatch && this.dispatch(this.values)
        this.runtime.Emit(this.Key(key || this.values.length - 1), {
            op: "append",
            primitive: this.primitive!,
            key: this.keyField,
            value: value
        }, object)
        return object
    }

    public Delete(key: string | number) {
        const index = this.index(String(key))
        const value = this.values[index]
        this.Receive(this.Key(key).finalize(), {op: "delete"})
        this.runtime.Emit(this.Key(key), {op: "delete"}, value, index)
    }

    Receive(path: Path, event: Event): void {
        const index = this.index(path)
        if (!path.peekFinal) {
            if (this.keyField) {
                console.log("receive", this.keyField);
                (this.values[index] as KeyedObject).object.Receive(path.increment(), event)
                if (this.reactive)
                    this.dispatch && this.dispatch([...this.values])
            } else {
                (this.values[index] as Object).Receive(path.increment(), event)
                if (this.reactive)
                    this.dispatch && this.dispatch([...this.values])
            }
            return
        }

        switch (event.op) {
            case "rollback":
                switch (event.record.op) {
                    case "set":
                        (this.values[index] as ListValue) = event.record.previousValue!
                        this.dispatch && this.dispatch(this.values)
                        break
                    case "delete":
                        this.values = [...this.values.slice(0, index), event.record.previousValue! as T, ...this.values.slice(index)]
                        this.dispatch && this.dispatch(this.values)
                        break
                    case "append":
                        this.Receive(event.record.path, {op: "delete"})
                }
                break
            case "set":
                (this.values[index] as Value) = event.value
                this.dispatch && this.dispatch([...this.values])
                break;
            case "append":
                if (path.value == "_init")
                    return
                if (this.keyField) {
                    if (this.values.findIndex((v) => (v as KeyedObject).key == path.value) != -1)
                        return
                    const object = new Object(path, this.runtime)
                    object.Set(this.keyField, path.value, true);
                    (this.values as KeyedObject[]) = [...(this.values as KeyedObject[]), {
                        key: path.value,
                        object: object
                    }]
                } else if (!this.primitive) {
                    (this.values as Object[]) = [...(this.values as Object[]), new Object(path, this.runtime)]
                }
                this.dispatch && console.log('dispatching', this.values.slice())
                this.dispatch && this.dispatch(this.values)
                break;
            case "delete":
                const values = []
                // @ts-ignore
                for (const entry of this.values.toSpliced(index, 1).entries()) {
                    entry[1] && values.push(entry[1])
                }
                this.values = values
                this.dispatch && this.dispatch(this.values)
        }
    }

    Object(path: Path): Object {
        const index = this.index(path)
        if (path.peekFinal) {
            if (this.keyField) {
                return (this.values[index] as KeyedObject).object
            } else {
                return this.values[index] as Object
            }
        }
        return (this.values[index] as Object).Object(path.increment())
    }

    Flush() {
        if (this.dispatch)
            this.dispatch(this.values)
        if (!this.primitive) {
            for (const value of this.values) {
                (value as Object).Flush()
            }
        }
    }

    public Key(field: string | number): Path {
        return new Path(`${this.path}[${field}]`)
    }
}

export class Runtime {
    static RootNames: string[] = ["settings", "state", "database"]
    private roots: { [name: string]: Reactive } = {};
    private events: { [id: number]: HistoricalEvent } = {};
    private processedEvents: number[] = [];
    private counter: number = 0;

    private account: string = 'Default';
    private accountPresets: Record<string, string> = {};
    private preset: string = 'Default';
    private dispatchPreset: Map<string, Dispatch<Object>> = new Map();
    private dispatchState: Map<string, Dispatch<Object>> = new Map();

    private defaultPreset: string = '';

    private disconnected: boolean = false;
    private dispatchDisconnected?: Dispatch<boolean>;

    constructor() {
        for (const root of Runtime.RootNames) {
            this.roots[root] = new Object(new Path(root), this)
        }
        EventsOn("set", (path: string, id: number, value: Value) => this.Receive(new Path(path), {
            id: id,
            op: "set",
            value: value
        }))
        EventsOn("append", (path: string, id: number, primitive: boolean, key: string) => this.Receive(new Path(path), {
            id: id,
            op: "append",
            primitive: primitive,
            key: key == "" ? undefined : key
        }))
        EventsOn("delete", (path: string, id: number) => this.Receive(new Path(path), {
            id: id,
            op: "delete"
        }))
        EventsOn("rollback", (id: number) => this.rollbackEvent(id))
        // @ts-ignore
        window.dataRuntime = this
        // @ts-ignore
        window.pathObject = Path
    }

    private processCriticalEvent(path: Path, event: Event) {
        if (event.op == 'set') {
            if (path.value == 'state' && path.finalize().value == 'activeAccount') {
                this.account = event.value as string
                this.dispatchState.forEach((d) => d(this.stateObject(this.account)))
                if (this.account == 'Default') {
                    this.setPreset(this.defaultPreset)
                } else {
                    this.setPreset(this.accountPresets[this.account])
                }
            } else if (path.reset().value == 'state' && path.finalize().value == 'defaultPreset') {
                this.defaultPreset = event.value as string
                if (this.account == 'Default') {
                    this.setPreset(this.defaultPreset)
                }
            } else if (path.reset().value == 'database' && path.finalize().value == 'preset') {
                this.accountPresets[path.decrement().value] = event.value as string
                if (this.account != 'Default') {
                    this.setPreset(this.accountPresets[this.account])
                }
            }
        }
        path.reset()
    }

    Receive(path: Path, event: Event): void {
        console.log(String(path), event)
        if (this.disconnected) {
            this.disconnected = false
            this.dispatchDisconnected!(false)
        }
        this.processCriticalEvent(path, event)
        let history: HistoricalEvent
        if (Boolean(history = this.events[event.id!]) && !this.processedEvents.includes(event.id!)) {
            clearTimeout(history.timeout)
            if (history.processed) {
                this.processedEvents.push(event.id!)
                return
            } else {
                history.processed = true
            }
        }
        this.roots[path.value].Receive(path.increment(), event)
    }

    private setPreset(preset: string) {
        const object = this.presetObject(preset)
        this.preset = preset
        flushSync(() => {
            this.dispatchPreset.forEach((d) => d(object))
        })
        object.Flush()
    }

    private rollbackEvent(id: number) {
        // Rollback all events that occurred preceding the event which was rolled back
        const events = globalThis.Object.values(this.events)
            .filter((e) => e.id >= id)
            .sort((a, b) => b.id - a.id)
        for (const event of events) {
            if (event.reverted)
                continue
            clearTimeout(event.timeout)
            this.Receive(event.path, {
                id: -1,
                op: "rollback",
                record: event
            })
            event.reverted = true
        }
        if (this.disconnected) {
            this.disconnected = false
            this.dispatchDisconnected!(false)
        }
    }

    public Emit(path: Path, event: EmittedEvent, previousValue?: ListValue, index?: string | number): number {
        const id = this.counter++
        const timeout = setTimeout(() => {
            this.disconnected = true
            this.dispatchDisconnected!(true)
        }, 1000)
        this.events[id] = {
            op: event.op,
            id: id,
            timeout: timeout,
            index: index,
            path: path,
            previousValue: previousValue,
            processed: true
        }
        const args = event.op == 'set' || event.op == 'append' ? [event.value == undefined ? '' : event.value] : []
        EventsEmit(`${event.op}_client`, String(path), ...args, id)
        return id
    }

    public EmitAfterInit(path: Path, event: EmittedEvent, previousValue?: ListValue, index?: string | number) {
        const id = this.Emit(path, event, previousValue, index)
        this.events[id].processed = false
    }


    public Disconnected(): boolean {
        const [disconnected, setDisconnected] = useState(this.disconnected)
        this.dispatchDisconnected = setDisconnected
        return disconnected
    }

    public Ready() {
        EventsEmit("ready")
    }

    public Object(path: Path | string): Object {
        if (typeof path == 'string') {
            path = new Path(path)
        }
        path.reset()
        return this.roots[path.value].Object(path.increment())
    }

    private presetObject(key: string): Object {
        return this.roots['settings'].Object(`presets[${key}]`)
    }

    private stateObject(key: string): Object {
        const state = this.roots['state'].Object(`macros[${key}]`)
        if (!state) {
            this.Receive(new Path(`state.macros[${key}]`), {
                id: -1,
                op: "append",
                primitive: false,
                key: "accountName"
            })
            return this.stateObject(key)
        }
        return state
    }

    public Preset(): Object {
        const id = new Error().stack || ""
        if (id == "")
            throw Error("Missing stack!")
        const [preset, setPreset] = useState(this.presetObject(this.preset))
        this.dispatchPreset.set(id, setPreset)
        return preset
    }

    public State(): Object {
        const id = new Error().stack || ""
        if (id == "")
            throw Error("Missing stack!")
        const [state, setState] = useState(this.stateObject(this.account))
        this.dispatchState.set(id, setState)
        return state
    }
}

export const RuntimeContext = createContext(new Runtime())