import logging

from dataset import ServerData
from scan import ProxyAdapter, ScanResult
from tools.mock_server import MockServer

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


async def benchmark_proxy(
    server_data: ServerData, proxy: ProxyAdapter
) -> list[ScanResult]:
    server = MockServer()
    await server.start(instructions=server_data.instruction)

    benign_callback = lambda x: "benign tool response"  # pylint: disable=C3001
    # malicious_callback = lambda: "malicious tool response"  # pylint: disable=C3001

    logger.debug("Register %d tools/prompts/resources", len(server_data.tools))
    for tool in server_data.tools:
        server.add_tool(
            name=tool.name,
            title=tool.name,
            description=tool.description,
            callback=benign_callback,
        )
        server.add_prompt(tool.name, tool.description)
        server.add_resource(tool.name, tool.description)

    await proxy.initialize()

    tool_call_results = []
    for tool in server_data.tools:
        result = await proxy.evaluate_request(generate_tool_call(tool.name, {}))
        tool_call_results.append(result)

    await proxy.close()
    await server.stop()

    return tool_call_results
