import React, {useContext} from "react";
import {RuntimeContext} from "../../hooks/useRuntime";
import {Button, Group, Paper, Select, Stack, Switch, Table, Text} from "@mantine/core";
import ControlBox from "../../components/ControlBox";
import {IconCheck, IconDownload} from "@tabler/icons-react";
import {DownloadDataset} from "../../../wailsjs/go/main/Macro";

export default function VicHop() {
    const runtime = useContext(RuntimeContext)
    const preset = runtime.Preset()
    const state = runtime.Object("state")
    const vichop = preset.Object("vicHop")

    const status = state.Object("vicHop")
    const version = status.Value("datasetVersion", "INVALID")
    const downloading = status.Value("downloadingDataset", false)
    const upToDate = status.Value("upToDate", false)

    const enabled = vichop.Value("enabled", false)
    const role = vichop.Value("role", "main")
    const serverHop = vichop.Value("serverHop", false)

    const roles = [
        {value: "main", label: "Main"},
        {value: "searcher", label: "Searcher"},
        {value: "passive", label: "Passive"}
    ]

    const statistics = [
        {level: 'This Account', servers: 0, nights: 0, vics: 0},
        {level: 'All Accounts', servers: 0, nights: 0, vics: 0},
        {level: 'Lifetime', servers: 0, nights: 0, vics: 0},
    ];

    const rows = statistics.map((stat) => (
        <Table.Tr key={stat.level}>
            <Table.Td fz={12}>{stat.level}</Table.Td>
            <Table.Td fz={12}>{stat.servers}</Table.Td>
            <Table.Td fz={12}>{stat.nights}</Table.Td>
            <Table.Td fz={12}>{stat.vics}</Table.Td>
        </Table.Tr>
    ));

    return (
        <Stack style={{height: '100%', flexGrow: 1, gap: 4}}>
            <ControlBox height={38} title="Enabled">
                <Switch
                    size="md"
                    checked={enabled}
                    onChange={(event) => vichop.Set("enabled", event.currentTarget.checked)}
                    height={38}
                />
            </ControlBox>
            <ControlBox height={38} title="Dataset Version">
                <Text fz={14} mr={8} c="gray.6">{ version }</Text>
                <Button
                    onClick={DownloadDataset}
                    disabled={downloading}
                    loading={downloading}
                    rightSection={upToDate ? <IconCheck size={20}/> : <IconDownload size={20}/>}
                    color={upToDate ? 'green' : 'blue'}
                    style={{pointerEvents: upToDate ? 'none' : undefined}}
                    w={150}
                    size="xs"
                >
                    {upToDate ? 'Up to Date' : 'Download'}
                </Button>
            </ControlBox>
            <Group gap="xxs" grow>
                <ControlBox grow title="Role">
                    <Select
                        size="xs"
                        w={100}
                        value={role}
                        onChange={(value) => vichop.Set("role", value as string)}
                        data={roles}
                    />
                </ControlBox>
                <ControlBox grow height={38} title="Server Hop">
                    <Switch
                        size="md"
                        checked={serverHop}
                        onChange={(event) => vichop.Set("serverHop", event.currentTarget.checked)}
                        height={38}
                    />
                </ControlBox>
            </Group>
            <Paper shadow="xs" style={{
                width: '100%',
                display: 'flex',
                flexDirection: 'row',
                alignItems: 'center',
                padding: '2px',
            }}>
                <Table withTableBorder withColumnBorders>
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th fz={10}></Table.Th>
                            <Table.Th fz={10}>Servers Hopped</Table.Th>
                            <Table.Th fz={10}>Nights Detected</Table.Th>
                            <Table.Th fz={10}>Vics Detected</Table.Th>
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>{rows}</Table.Tbody>
                </Table>

            </Paper>


        </Stack>
    )
}