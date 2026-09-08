import React, {useContext, useState} from "react";
import {KeyedObject, RuntimeContext} from "../../hooks/useRuntime";
import {
    Badge,
    Box,
    Button,
    Flex,
    Grid,
    Loader,
    Paper,
    ScrollArea,
    Stack,
    Switch,
    Table,
    Text,
    TextInput,
    Tooltip,
    UnstyledButton
} from "@mantine/core";
import ControlBox from "../../components/ControlBox";
import {modals} from '@mantine/modals';
import {
    IconForbid,
    IconForbidFilled,
    IconLogin2,
    IconLogout,
    IconNetwork,
    IconPlus,
    IconRocket,
    IconSquare,
    IconStar
} from "@tabler/icons-react";
import {useHover} from "@mantine/hooks";
import {BanIdentity, ConnectRelay, DisconnectRelay, StartRelay, StopRelay} from "../../../wailsjs/go/main/Macro";

interface RoleMetadata {
    color: string
    text: string
}

const Roles: Record<string, RoleMetadata> = {
    "main": {color: "green", text: "Main"},
    "searcher": {color: "orange", text: "Search"},
    "passive": {color: "gray", text: "Passive"}
}

function AddRelayModalContent() {
    const runtime = useContext(RuntimeContext)
    const [address, setAddress] = useState("");
    const [identity, setIdentity] = useState("");
    const macroState = runtime.State()
    const networking = macroState.Object("networking")

    const handleAdd = () => {
        console.log("Saving", address, identity)
        const item = networking.List<KeyedObject>("savedRelays").Append(address) as KeyedObject
        item.object.SetAfterInitialization("identity", identity)
        modals.closeAll();
    }

    return (
        <>
            <TextInput
                label="Identity"
                value={identity}
                onChange={(e) => setIdentity(e.currentTarget.value)}
            />
            <TextInput
                label="Address"
                value={address}
                onChange={(e) => setAddress(e.currentTarget.value)}
            />
            <Button fullWidth mt="md" onClick={handleAdd}>
                Add
            </Button>
        </>
    )
}

export default function Networking() {
    const [hoveredIndex, setHoveredIndex] = useState("")
    const [actionHovered, setActionHovered] = useState(false)
    const {hovered: exitHovered, ref: exitRef} = useHover()
    const runtime = useContext(RuntimeContext)
    const macroState = runtime.State()
    const activeAccount = macroState.Value("accountName", "Default")
    const settings = runtime.Object("settings.networking")
    const networking = macroState.Object("networking")

    const autoConnect = settings.Value("autoConnect", false)

    let relayStarting = networking.Value("relayStarting", false)
    let relayActive = networking.Value("relayActive", false)
    let connectedIdentities = networking.List<KeyedObject>("connectedIdentities").Values(true)

    let connectingAddress = networking.Value("connectingAddress", "")
    let connectedAddress = networking.Value("connectedAddress", "")

    let identity = networking.Value("identity", "Unknown/Unknown")
    let availableRelays = networking.List<KeyedObject>("availableRelays").Values(true)
    let savedRelays = networking.List<KeyedObject>("savedRelays").Values(true)

    const identityShorthand = identity.split('/').slice(-2).join('/')

    let mappedSavedRelays = savedRelays.map((v) => ({
        address: v.object.Concrete<string>("address"),
        identity: v.object.Concrete<string>("identity"),
        role: 'none',
    }))
    console.log("saved", mappedSavedRelays)

    let mappedConnectedIdentities = connectedIdentities.map((v) => ({
        address: v.object.Concrete<string>("address"),
        identity: v.object.Concrete<string>("identity"),
        role: v.object.Concrete<string>("role")
    }))

    let mappedRelays = availableRelays.map((v) => ({
        address: v.object.Concrete<string>("address"),
        identity: v.object.Concrete<string>("identity"),
        role: 'none'
    }))

    let uniqueRelays = Array.from(
        new Map(
            [...mappedSavedRelays, ...mappedRelays].map((relay) => [relay.address, relay])
        ).values()
    );

    const showNetwork = relayActive || Boolean(connectedAddress)

    const mappedRelayRows = (showNetwork ? mappedConnectedIdentities : uniqueRelays).map((relay) => {
        const saved = !relayActive && mappedSavedRelays.findIndex((r) => r.address == relay.address) != -1
        const actionStyle: React.CSSProperties = {
            display: hoveredIndex == relay.address || saved ? 'inherit' : 'none',
            position: 'absolute',
            bottom: 9,
            right: 8
        }
        const connectStyle: React.CSSProperties = {
            display: hoveredIndex == relay.address || saved ? 'inherit' : 'none',
            position: 'absolute',
            bottom: 9,
            right: 32
        }
        const loadingStyle: React.CSSProperties = {
            position: 'absolute',
            bottom: 0,
            right: 8
        }

        const action = () => {
            if (showNetwork) {
                BanIdentity(activeAccount, relay.identity!)
            } else {
                if (saved) {
                    networking.List<KeyedObject>("savedRelays").Delete(relay.address!)
                } else {
                    const item = networking.List<KeyedObject>("savedRelays").Append(relay.address!) as KeyedObject
                    item.object.SetAfterInitialization("identity", relay.identity!)
                }
            }
        }

        const connect = () => {
            ConnectRelay(activeAccount, relay.address!)
        }

        return (
            <Table.Tr key={relay.address} style={{width: '100%'}}
                      onMouseEnter={() => setHoveredIndex(relay.address!)}
                      onMouseLeave={() => setHoveredIndex((i) => i == relay.address ? "" : i)}>
                <Table.Td pb={2} pr={0}><IconNetwork size={16}/></Table.Td>
                <Table.Td style={{display: 'flex', alignItems: 'center', paddingLeft: 0, position: 'relative'}}>
                    <Tooltip label={`${relay.identity} @ ${relay.address}`} withArrow>
                        <Text
                            fz={14}
                            mr={4}
                            c="gray.8"
                            style={{
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                width: '100px',
                                direction: 'rtl',
                                textAlign: 'left',
                            }}
                        >
                            {relay.identity!.split('/').slice(-2).join('/')}
                        </Text>
                    </Tooltip>
                    {connectingAddress != relay.address ? <div>
                        {(showNetwork && (!relayActive || (relayActive && hoveredIndex != relay.address)) && Roles[relay.role!]) &&
                            <Badge color={Roles[relay.role!].color} radius="sm" style={{
                                position: 'absolute',
                                bottom: 8,
                                right: 8,
                                paddingLeft: 4,
                                paddingRight: 4,
                            }}>
                                { Roles[relay.role!].text }
                            </Badge>}
                        {(relayActive || connectedAddress == "") &&
                            <UnstyledButton onPointerEnter={() => setActionHovered(true)}
                                            onPointerLeave={() => setActionHovered(false)} onClick={action}>
                                {(relayActive && relay.identity != identity) && (actionHovered ? <IconForbidFilled size={18} style={actionStyle}/> :
                                    <IconForbid size={18} style={actionStyle}/>)}
                                {!relayActive && <IconStar size={18} style={{...actionStyle, stroke: 'goldenrod'}}
                                                           fill={actionHovered || saved ? 'goldenrod' : 'none'}/>}
                            </UnstyledButton>}
                        {!showNetwork && <UnstyledButton onClick={connect}>
                            <IconLogin2 size={18} style={connectStyle}/>
                        </UnstyledButton>}
                    </div> : <Loader type="dots" color="blue" style={loadingStyle}/>}
                </Table.Td>
            </Table.Tr>
        )
    })

    const openDisconnectModal = () => modals.openConfirmModal({
        title: 'Please confirm your action',
        centered: true,
        children: (
            <Text size="sm">
                Are you sure you want to disconnect from your current relay?
            </Text>
        ),
        labels: {confirm: 'Confirm', cancel: 'Cancel'},
        onConfirm: () => DisconnectRelay(activeAccount),
    });

    const openShutdownModal = () => modals.openConfirmModal({
        title: 'Please confirm your action',
        centered: true,
        children: (
            <Text size="sm">
                Are you sure you want to shut down your relay? This will disconnect all connected clients.
            </Text>
        ),
        labels: {confirm: 'Confirm', cancel: 'Cancel'},
        onCancel: () => console.log('Cancel'),
        onConfirm: () => console.log('Confirmed'),
    });

    return (
        <Grid gutter="xxs" style={{flexGrow: 1, height: '100%'}} styles={{inner: {height: '100%'}}}>
            <Grid.Col span={6}>
                <Stack style={{height: '100%', flexGrow: 1, gap: 4}}>
                    <ControlBox height={38} title="Identity">
                        <Tooltip label={identity} withArrow>
                            <Text
                                fz={14}
                                mr={4}
                                c="gray.8"
                                style={{
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    width: '150px',
                                    direction: 'rtl',
                                    textAlign: 'right',
                                }}
                            >
                                {identityShorthand}
                            </Text>
                        </Tooltip>
                    </ControlBox>
                    <ControlBox height={38} title="Relay">
                        <Button
                            onClick={() => relayActive ? StopRelay(activeAccount) : StartRelay(activeAccount)}
                            disabled={!relayActive && connectedAddress != ""}
                            rightSection={relayActive ? <IconSquare size={18} fill="white"/> : <IconRocket size={18}/>}
                            color={relayActive ? 'green' : 'blue'}
                            w={100}
                            size="xs"
                        >
                            {relayActive ? 'Active' : 'Start'}
                        </Button>
                    </ControlBox>
                    <ControlBox height={38} title="Auto-Connect">
                        <Switch
                            size="md"
                            checked={autoConnect}
                            onChange={(event) => settings.Set("autoConnect", event.currentTarget.checked)}
                            height={38}
                        />
                    </ControlBox>
                </Stack>
            </Grid.Col>
            <Grid.Col span={6}>
                <Paper style={(theme) => ({
                    border: `1px solid ${theme.colors.gray[4]}`,
                    height: '100%',
                })}>
                    <Flex justify="left" align="center" direction="row" style={(theme) => ({
                        borderBottom: `1px solid ${theme.colors.gray[4]}`,
                        height: '37px',
                    })}>
                        <Text fw={500} fz={14} ml={6}>{showNetwork ? 'Connected Identities' : 'Available Relays'}</Text>
                        <Box style={{flexGrow: 1}}/>
                        {!showNetwork && <Button
                            mr={4}
                            onClick={() => {
                                modals.open({
                                    title: 'Add an External Relay',
                                    children: <AddRelayModalContent/>,
                                })
                            }}
                            disabled={showNetwork}
                            radius="xl"
                            styles={{
                                root: {
                                    width: '22px',
                                    height: '22px',
                                    padding: 0,
                                },
                            }}
                        >
                            <IconPlus size={18} style={{marginBottom: '1px'}} color="white" fill="white"/>
                        </Button>}
                        {(showNetwork && !relayActive) && <UnstyledButton
                            ref={exitRef}
                            mr={4}
                            mt={6}
                            onClick={openDisconnectModal}
                        >
                            <IconLogout size={22} strokeWidth={exitHovered ? 2 : 1}/>
                        </UnstyledButton>}
                    </Flex>

                    <ScrollArea style={{flexGrow: 1, height: '212px'}} type="scroll" offsetScrollbars>
                        <Table striped style={{width: '212px'}}>
                            <Table.Tbody style={{width: '100%'}}>{mappedRelayRows}</Table.Tbody>
                        </Table>
                    </ScrollArea>
                </Paper>
            </Grid.Col>
        </Grid>
    )
}