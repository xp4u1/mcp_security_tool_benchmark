import asyncio
import logging
from functools import reduce

from dataset import load_mcptox
from tools.mcp_context_protector import MCPContextProtector
from tools.mock_server import MockServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")


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


async def run_mock_server():
    server = None

    try:
        server_data = load_mcptox()[0]

        server = MockServer()
        await server.start(instructions=server_data.instruction)

        server.add_tool("print", "print", "Print text", lambda text: print(text))

        benign_callback = lambda x: "benign tool response"  # pylint: disable=C3001
        malicious_callback = lambda: "malicious tool response"  # pylint: disable=C3001
        # malicious_callback = lambda: "Nothing to see here"  # pylint: disable=C3001

        for tool in server_data.tools:
            server.add_tool(
                name=tool.name,
                title=tool.name,
                description=tool.description,
                callback=malicious_callback if tool.malicious else benign_callback,
            )
            server.add_prompt(tool.name, tool.description)
            server.add_resource(tool.name, tool.description)

        while True:
            await asyncio.sleep(10)

    except asyncio.CancelledError:
        if server:
            await server.stop()


async def test_mcpcp():
    mcp_context_protector = MCPContextProtector()
    await mcp_context_protector.initialize()

    tool_call_results = []
    for _ in range(10):
        result = await mcp_context_protector.evaluate_request(
            generate_tool_call("sky", {})
        )
        tool_call_results.append(result)

    avg_latency = reduce(lambda sum, r: sum + r.latency_ms, tool_call_results, 0) / 10
    logger.debug("avg mcp-context-protector latency: %d ms", avg_latency)

    await mcp_context_protector.close()


async def main():
    server_task = asyncio.create_task(run_mock_server())

    mcpcp_task = asyncio.create_task(test_mcpcp())
    await mcpcp_task
    server_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
