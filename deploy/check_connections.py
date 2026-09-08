"""Read-only live database/MCP probe; invoke through local_cloud.py."""
import asyncio
import json
import os
import clickhouse_connect
from app.integrations import ClickHouse

async def main():
    writer = ClickHouse().writer()
    try:
        print('ClickHouse version:',writer.command('SELECT version()'))
        print('Selected database:',writer.command('SELECT currentDatabase()'))
    finally:
        writer.close()
    reader = clickhouse_connect.get_client(host=os.environ['CLICKHOUSE_HOST'],port=int(os.environ['CLICKHOUSE_PORT']),secure=False,username=os.environ['CLICKHOUSE_READ_USER'],password=os.environ['CLICKHOUSE_READ_PASSWORD'],database=os.environ['CLICKHOUSE_DATABASE'])
    try:
        readonly = str(reader.command("SELECT value FROM system.settings WHERE name = 'readonly'"))
        assert readonly == '1', 'Reader does not have readonly enforcement'
        print('Server-enforced reader readonly:',readonly)
    finally:
        reader.close()
    result = await ClickHouse().query('SELECT 1 AS value WHERE 1 = 0')
    assert result['rows'] == [], 'Impossible predicate returned rows'
    print('Official MCP impossible-predicate probe:',json.dumps(result))

asyncio.run(main())
