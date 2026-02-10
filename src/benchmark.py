import logging

import pandas as pd

from dataset import ServerData, ToolData
from mock_server import MCP_SERVER_PORT, MockServer
from scan import ProxyAdapter, ScanAdapter, ScanResult

logger = logging.getLogger(__name__)


def generate_tool_call(name: str, args: dict) -> dict:
    return {
        "mcp_request": {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": args,
            },
        },
    }


def make_callback(tool: ToolData):
    """
    Helper function since the mcp sdk does not accept
    partials as callbacks
    """

    def callback():
        return tool.return_value

    return callback


def init_server_content(server: MockServer, server_data: ServerData):
    logger.debug("Register %d tools", len(server_data.tools))
    for tool in server_data.tools:
        server.add_tool(
            name=tool.name,
            title=tool.name,
            description=tool.description,
            callback=make_callback(tool),
        )
        # server.add_prompt(tool.name, tool.description)
        # server.add_resource(tool.name, tool.description)


async def benchmark_proxy(
    server_data: ServerData, proxy: ProxyAdapter
) -> list[ScanResult]:
    server = MockServer()
    await server.start(instructions=server_data.instruction)
    init_server_content(server, server_data)

    await proxy.initialize()

    tool_call_results = []
    for tool in server_data.tools:
        result = await proxy.evaluate_request(generate_tool_call(tool.name, {}))
        tool_call_results.append(result)

    await proxy.close()
    await server.stop()

    return tool_call_results


async def benchmark_scanner(
    server_data: ServerData, scanner: ScanAdapter
) -> pd.DataFrame:
    server = MockServer()
    await server.start(instructions=server_data.instruction)
    init_server_content(server, server_data)

    await scanner.initialize(f"http://127.0.0.1:{MCP_SERVER_PORT}/mcp")

    scan_results = await scanner.evaluate_tools()

    await scanner.close()
    await server.stop()

    benchmark_result = []
    for tool in server_data.tools:
        scan_result = scan_results[tool.name]
        benchmark_result.append(
            {
                "scanner": scanner.__module__,
                "server": server_data.name,
                "server_instructions": server_data.instruction,
                **tool.__dict__,
                **scan_result.__dict__,
            }
        )

    return pd.DataFrame(benchmark_result)
