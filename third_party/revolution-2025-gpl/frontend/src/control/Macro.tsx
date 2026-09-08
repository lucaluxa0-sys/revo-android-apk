import {Box, Flex, Tabs} from "@mantine/core";
import {
    IconShovel,
    IconTicket,
    IconBucket,
    IconTerminal2,
    IconTool,
    IconSettings,
} from "@tabler/icons-react";
import tabClasses from "./Tab.module.css"
import React from "react";
import Tools from "../pages/tools/Tools";
import Status from "../pages/status/Status";
import Settings from "../pages/settings/Settings";

export default function MacroTabs() {
    return (
        <Flex style={{flexGrow: 1, minHeight: 0}}>
            <Tabs defaultValue="gallery" style={{width: '100%'}} classNames={tabClasses}>
                <Tabs.List bg="gray.0">
                    <Tabs.Tab value="gather" leftSection={<IconShovel size={16}/>}>
                        Gather
                    </Tabs.Tab>
                    <Tabs.Tab value="collect" leftSection={<IconTicket size={16}/>}>
                        Collect
                    </Tabs.Tab>
                    <Tabs.Tab value="planters" leftSection={<IconBucket size={16}/>}>
                        Planters
                    </Tabs.Tab>
                    <Tabs.Tab value="status" leftSection={<IconTerminal2 size={16}/>}>
                        Status
                    </Tabs.Tab>
                    <Tabs.Tab value="tools" leftSection={<IconTool size={16}/>}>
                        Tools
                    </Tabs.Tab>
                    <Tabs.Tab value="settings" leftSection={<IconSettings size={16}/>}>
                        Settings
                    </Tabs.Tab>
                </Tabs.List>

                <Box p={6} style={{height: 'calc(100% - 34px)'}}>
                    <Tabs.Panel value="tools" style={{height: '100%'}}>
                        <Tools/>
                    </Tabs.Panel>
                    <Tabs.Panel value="status" style={{height: '100%'}}>
                        <Status />
                    </Tabs.Panel>
                    <Tabs.Panel value="settings" style={{height: '100%'}}>
                        <Settings />
                    </Tabs.Panel>
                </Box>
            </Tabs>
        </Flex>
    )
}