#
# Copyright (C) 2023-present ScyllaDB
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
import random
import time
import pytest
import logging

from test.pylib.internal_types import IPAddress, HostID
from test.pylib.scylla_cluster import ReplaceConfig
from test.pylib.manager_client import ManagerClient
from test.topology.util import wait_for_token_ring_and_group0_consistency


logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_python_driver_stress(manager: ManagerClient) -> None:
    """Replace a node in presence of multiple dead nodes.
       Regression test for #14487. Does not apply to Raft-topology mode.

       This is a slow test with a 7 node cluster any 3 replace operations,
       we don't want to run it in debug mode.
       Preferably run it only in one mode e.g. dev.
    """
    logger.info(f"Booting initial cluster")
    servers = [await manager.server_add() for _ in range(7)]

    all_in_cluster = {0, 1, 2, 3, 4, 5, 6}
    up = {0, 1, 2, 3, 4, 5, 6}
    down = set()

    for i in range(30):
        rand = random.randint(0, 4)
        logger.info(f"OPP: {i}, {rand}")
        logger.info(f"UP: {up}")
        logger.info(f"DOWN: {down}")
        logger.info("Servers: %s", [e.ip_addr for e in servers])
        if rand == 0:
            if len(up) <= len(all_in_cluster) / 2 + 1:
                continue
            e = up.pop()
            logger.info(f"Stopping node {servers[e]}, {servers[e].ip_addr}")
            down.add(e)
            await manager.server_stop(servers[e].server_id)
        elif rand == 1:
            if len(up) <= len(all_in_cluster) / 2 + 1:
                continue
            e = up.pop()
            logger.info(f"Stopping node gracefully {servers[e]}, {servers[e].ip_addr}")
            down.add(e)
            await manager.server_stop_gracefully(servers[e].server_id)
        elif rand == 2:
            logger.info(f"Adding node")
            for s in down:
                logger.info(f"Restart {servers[s]}")
                await manager.server_start(servers[s].server_id)
                up.add(s)
            logger.info(f"WRRR Check if servers see each other {[servers[a] for a in all_in_cluster]}")
            await manager.servers_see_each_other([servers[a] for a in all_in_cluster])
            await wait_for_token_ring_and_group0_consistency(manager, time.time() + 30)

            logger.info("Servers see each other")
            down = set()
            server = await manager.server_add()
            servers.append(server)
            up.add(len(servers) - 1)
            all_in_cluster.add(len(servers) - 1)
        elif rand == 3:
            if len(up) <= len(all_in_cluster) / 2 + 1:
                continue
            e = up.pop()
            logger.info(f"Replacing {servers[e]}, ignore_dead_nodes = {down}")
            
            ignore_dead = down.copy()
            for s in down:
                ignore_dead.remove(s)
                logger.info(f"Remove stopped node {servers[s].server_id}, {servers[s].ip_addr}")
                logger.info(f"Ignore dead {ignore_dead}")
                await manager.remove_node(servers[e].server_id, servers[s].server_id, [await manager.get_host_id(servers[e].server_id) for e in ignore_dead])
                all_in_cluster.remove(s)
            down = set()
            logger.info(f"WRRR Check if servers see each other {[servers[a] for a in all_in_cluster]}")
            await manager.servers_see_each_other([servers[a] for a in all_in_cluster])
            await wait_for_token_ring_and_group0_consistency(manager, time.time() + 30)


            await manager.server_stop(servers[e].server_id)
            replace_cfg = ReplaceConfig(replaced_id = servers[e].server_id, reuse_ip_addr = False, use_host_id = False)
            server = await manager.server_add(replace_cfg=replace_cfg)
            servers[e] = server
            up.add(e)
        elif rand == 4:
            if len(up) <= len(all_in_cluster) / 2 + 1:
                continue
            e = up.pop()
            logger.info(f"Replacing gracefully {servers[e]}, ignore_dead_nodes = {down}")
            
            ignore_dead = down.copy()
            for s in down:
                ignore_dead.remove(s)
                logger.info(f"Remove stopped node {servers[s].server_id}, {servers[s].ip_addr}")
                logger.info(f"Ignore dead {ignore_dead}")
                await manager.remove_node(servers[e].server_id, servers[s].server_id, [await manager.get_host_id(servers[e].server_id) for e in ignore_dead])
                all_in_cluster.remove(s)
            down = set()
            logger.info(f"WRRR Check if servers see each other {[servers[a] for a in all_in_cluster]}")
            await manager.servers_see_each_other([servers[a] for a in all_in_cluster])
            await wait_for_token_ring_and_group0_consistency(manager, time.time() + 30)


            await manager.server_stop_gracefully(servers[e].server_id)
            replace_cfg = ReplaceConfig(replaced_id = servers[e].server_id, reuse_ip_addr = False, use_host_id = False,
                                        ignore_dead_nodes = [servers[e].ip_addr for e in down])
            server = await manager.server_add(replace_cfg=replace_cfg)
            servers[e] = server
            up.add(e)

        await wait_for_token_ring_and_group0_consistency(manager, time.time() + 30)
