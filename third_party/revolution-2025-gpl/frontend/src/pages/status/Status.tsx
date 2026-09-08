import {Box, Group, Paper, rem, px, Stack, Tabs} from "@mantine/core";
import React, {useState} from "react";
import FloatingSelector from "../../components/FloatingSelector";
import {IconChartBarPopular, IconLogs, IconWebhook} from "@tabler/icons-react";
import Console from "./Console";

export default function Status() {
    const iconStyle = { width: rem(16), height: rem(16), marginRight: px(-3) };

    return (
        <Group style={{height: '100%', flexWrap: 'nowrap'}} gap={8}>
            <Console />
            <Paper shadow="xs" style={{height: '100%', flexGrow: 0, flexShrink: 1}} p={4}>
                <Stack gap={4} style={{height: '100%'}}>
                    <Box style={{flexGrow: 1, height: '100%'}}>
                    </Box>
                    <Tabs variant="pills" defaultValue="logs">
                        <Tabs.List style={{flexWrap: 'nowrap'}}>
                            <Tabs.Tab value="statistics" leftSection={<IconChartBarPopular style={iconStyle} />}>
                                Statistics
                            </Tabs.Tab>
                            <Tabs.Tab value="logs" leftSection={<IconLogs style={iconStyle} />}>
                                Logs
                            </Tabs.Tab>
                            <Tabs.Tab value="webhook" leftSection={<IconWebhook style={iconStyle} />}>
                                Webhook
                            </Tabs.Tab>
                        </Tabs.List>

                        <Tabs.Panel value="statistics">
                        </Tabs.Panel>

                        <Tabs.Panel value="logs">
                        </Tabs.Panel>

                        <Tabs.Panel value="webhook">
                        </Tabs.Panel>
                    </Tabs>
                </Stack>
            </Paper>
        </Group>
    )
}