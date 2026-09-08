import {
    BackgroundImage, Box,
    Button, CheckIcon,
    Container,
    Grid,
    Group,
    Modal,
    NumberInput,
    Overlay,
    Paper,
    Select,
    Stack,
    Switch,
    UnstyledButton
} from "@mantine/core";
import React, {useContext, useState} from "react";
import {Bees} from '../../assets/images/bees/bees'
import {RuntimeContext} from "../../hooks/useRuntime";
import ControlBox from "../../components/ControlBox";
import beeClasses from "../../assets/css/Bee.module.css"
import {IconCheck, IconTrash} from "@tabler/icons-react";

interface Mutation {
    value: string,
    label: string,
    minPercent?: number,
    maxPercent?: number,
    minNumeric?: number,
    maxNumeric?: number,
    percent: boolean
    numeric: boolean
}

const Mutations: { [key: string]: Mutation } = {
    "attack": {
        value: "attack",
        label: "Attack",
        minPercent: 2,
        maxPercent: 6,
        minNumeric: 1,
        maxNumeric: 2,
        percent: true,
        numeric: true
    },
    "convert": {
        value: "convert-amount",
        label: "Convert",
        minPercent: 10,
        maxPercent: 30,
        minNumeric: 20,
        maxNumeric: 70,
        percent: true,
        numeric: true
    },
    "gather": {
        value: "gather-amount",
        label: "Gather",
        minPercent: 10,
        maxPercent: 30,
        minNumeric: 2,
        maxNumeric: 78,
        percent: true,
        numeric: true
    },
    "movespeed": {
        value: "movespeed",
        label: "Movespeed",
        minNumeric: 2,
        maxNumeric: 6,
        percent: false,
        numeric: true
    },
    "energy": {
        value: "energy",
        label: "Energy",
        minPercent: 10,
        maxPercent: 40,
        percent: true,
        numeric: false
    },
    "ability-rate": {
        value: "ability-rate",
        label: "Ability Rate",
        minPercent: 1,
        maxPercent: 4,
        percent: true,
        numeric: false
    },
    "critical-chance": {
        value: "critical-chance",
        label: "Critical Chance",
        minPercent: 1,
        maxPercent: 3,
        percent: true,
        numeric: false
    },
    "instant-conversion": {
        value: "instant-conversion",
        label: "Instant Conv.",
        minPercent: 8,
        maxPercent: 20,
        percent: true,
        numeric: false
    },
}

interface BeeProps {
    code: string
    name: string
    image: string
    size: number
    checked?: boolean
}

export default function JellyTool() {
    const runtime = useContext(RuntimeContext)
    const [beeOpen, setBeeOpen] = useState(false)
    const settings = runtime.Object("settings.tools.jellyTool")
    const enabled = settings.Value<boolean>("enabled", false)
    const allowedTypes = settings.List<string>("beeTypes")
    const allowedTypesValues = allowedTypes.Values()
    const requireMutation = settings.Value<boolean>("requireMutation", false)
    const mutationType = settings.Value<string>("mutationType", "movespeed")
    const mutationValue = settings.Value<number>("mutationValue", 0)
    const usePercent = settings.Value<boolean>("usePercent", false)
    const stopGifted = settings.Value<boolean>("stopGifted", false)
    const stopMythic = settings.Value<boolean>("stopMythic", false)

    const clearAllowedTypes = () => {
        for (let i = 0; i < allowedTypesValues.length; i++) {
            allowedTypes.Delete(0);
        }
    }

    const Bee = (props: BeeProps) => {
        const [hover, setHover] = useState(false)
        const index = allowedTypesValues.findIndex((v) => v == props.code)

        const click = () => {
            if (props.checked && index == -1) {
                allowedTypes.Append(undefined, props.code)
            } else if (index != -1) {
                allowedTypes.Delete(index)
            }
        }

        return (
            <Box style={{position: 'relative'}}>
                <BackgroundImage
                    src={props.image}
                    style={{height: props.size, width: props.size}}
                    classNames={beeClasses}
                >
                    <Container fluid classNames={beeClasses} p={4} style={{pointerEvents: 'none'}}>
                        { (index != -1 && props.checked) && <IconCheck size={props.size} style={{color: 'white'}}/>}
                        { !props.checked && hover && <IconTrash size={props.size * 2} stroke="red" fill="red"/>}
                    </Container>
                    <UnstyledButton
                        size={props.size}
                        style={{
                            width: '100%',
                            height: '100%',
                        }}
                        onMouseEnter={() => setHover(true)}
                        onMouseLeave={() => setHover(false)}
                        onClick={click}
                    />

                </BackgroundImage>
            </Box>
        )
    }


    return (
        <Grid gutter="xs" style={{flexGrow: 1, height: '100%'}} styles={{inner: {height: '100%'}}}>
            <Modal opened={beeOpen} onClose={() => setBeeOpen(false)} centered withCloseButton={false} size={'90%'}>
                <Grid columns={12} mb={14} mr={10}>
                    {Object.entries(Bees).map((bee, i) => {
                        return (
                            <Grid.Col span={1} key={bee[0]} style={{height: '35px', width: '35px'}} mb={3}>
                                <Bee code={bee[0]} name={bee[1][0]} image={bee[1][1]} size={35}
                                     checked={true}/>
                            </Grid.Col>
                        )
                    })}
                </Grid>
            </Modal>
            <Grid.Col span={7}>
                <Stack style={{height: '100%', flexGrow: 1, gap: 4}}>
                    <ControlBox title="Enabled">
                        <Switch
                            checked={enabled}
                            onChange={(event) => settings.Set<boolean>("enabled", event.currentTarget.checked)}
                        />
                    </ControlBox>
                    <ControlBox title="Allow All Types">
                        <Switch
                            checked={allowedTypesValues.length == Object.keys(Bees).length}
                            onChange={(event) => {
                                event.currentTarget.checked && Object.keys(Bees)
                                    .filter((b) => !Boolean(allowedTypesValues.find((v) => v == b)))
                                    .map((b) => allowedTypes.Append(undefined, b))
                            }}
                            disabled={!enabled}
                        />
                    </ControlBox>
                    <ControlBox title="Stop On Mythic">
                        <Switch
                            checked={stopMythic}
                            onChange={(event) => settings.Set<boolean>("stopMythic", event.currentTarget.checked)}
                        />
                    </ControlBox>
                    <ControlBox title="Stop On Gifted">
                        <Switch
                            checked={stopGifted}
                            onChange={(event) => settings.Set<boolean>("stopGifted", event.currentTarget.checked)}
                        />
                    </ControlBox>
                    <ControlBox title="Require Mutation">
                        <Switch
                            checked={requireMutation}
                            onChange={(event) => settings.Set<boolean>("requireMutation", event.currentTarget.checked)}
                            disabled={!enabled}
                        />
                    </ControlBox>
                    <ControlBox
                        leftAction={
                            <Group style={{gap: 4, flexWrap: 'nowrap'}}>
                                <NumberInput w={60} size="xs" value={mutationValue} max={100}
                                             disabled={!enabled || !requireMutation}
                                             onChange={(value) => settings.Set<number>("mutationValue", value as number)}/>
                                <Select
                                    size="xs"
                                    w={60}
                                    withCheckIcon={false}
                                    value={usePercent ? '%' : '+'}
                                    onChange={(value) => settings.Set<boolean>("usePercent", value == '%')}
                                    data={['+', '%']}
                                    disabled={!enabled || !requireMutation}
                                />
                            </Group>
                        }
                    >
                        <Select
                            size="xs"
                            pl={4}
                            w={110}
                            withCheckIcon={false}
                            value={mutationType}
                            onChange={(value) => settings.Set<string>("mutationType", value as string)}
                            data={Object.values(Mutations)}
                            maxDropdownHeight={100}
                            disabled={!enabled || !requireMutation}
                        />
                    </ControlBox>
                </Stack>
            </Grid.Col>
            <Grid.Col span={5}>
                <Paper shadow="xs" style={{height: '100%'}} p={4}>
                    <Stack style={{height: '100%', gap: 4}}>
                        <Container p={0} style={(theme) => ({
                            border: `1px solid ${theme.colors.gray[2]}`,
                            width: '163px',
                            flexGrow: 1,
                            borderRadius: 2
                        })}>
                            <Grid styles={{inner: {margin: 0, width: 'unset'}}} columns={5} m={2} pl={2}>
                                {
                                    allowedTypesValues
                                        .slice()
                                        .sort((a, b) => Object.entries(Bees).findIndex((v) => v[0] == a) - Object.entries(Bees).findIndex((v) => v[0] == b))
                                        .map((v) => {
                                        const bee = Object.entries(Bees).find((b) => b[0] == v)
                                        if (!bee)
                                            return <></>
                                        return (
                                            <Grid.Col span={1} p={0} key={bee[0]} style={{height: '30px', width: '30px'}}>
                                                <Bee code={bee[0]} name={bee[1][0]} image={bee[1][1]} size={29}/>
                                            </Grid.Col>
                                        )
                                    })
                                }
                            </Grid>
                        </Container>
                        <Grid columns={2} gutter="xs">
                            <Grid.Col span={1} pr={2}>
                                <Button size="compact-sm" style={{flexGrow: 1, width: '100%'}}
                                        disabled={!enabled} onClick={() => setBeeOpen(true)}>Edit</Button>
                            </Grid.Col>
                            <Grid.Col span={1} pl={2}>
                                <Button size="compact-sm" style={{flexGrow: 1, width: '100%'}}
                                        disabled={!enabled} onClick={clearAllowedTypes}>Clear</Button>
                            </Grid.Col>
                        </Grid>
                    </Stack>
                </Paper>
            </Grid.Col>
        </Grid>
    )
}