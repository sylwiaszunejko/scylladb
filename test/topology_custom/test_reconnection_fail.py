import time
import pytest
from test.pylib.manager_client import ManagerClient
from test.pylib.util import wait_for_cql_and_get_hosts


@pytest.mark.asyncio
async def test_reconnection(manager: ManagerClient) -> None:
    servers = await manager.servers_add(5)

    manager.driver_close()
    await manager.driver_connect()
    cql = manager.get_cql()

    for _ in range(200):
        srv = servers[0]
        await manager.server_stop_gracefully(srv.server_id)
        await manager.server_start(srv.server_id)

        h = (await wait_for_cql_and_get_hosts(cql, [srv], time.time() + 60))[0]
        print(h)

        output = cql.execute("select * from system.local", host=h)
        print(output)
