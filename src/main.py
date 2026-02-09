import asyncio
import json
import logging
import sys

from benchmark import benchmark_proxy, benchmark_scanner
from dataset import load_mcpsafety, load_mcptox
from mock_server import MockServer
from tools.mcp_context_protector import MCPContextProtector
from tools.mcp_guard import MCPGuard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")


async def server():
    mcptox = load_mcptox()
    mock_server = MockServer()
    await mock_server.start()

    for tool in mcptox[0].tools:
        mock_server.add_tool(tool.name, tool.name, tool.description, lambda: "Test")

    while True:
        await asyncio.sleep(10)


async def test_proxy():
    mcptox = load_mcptox()
    mcp_context_protector = MCPContextProtector()

    results = []
    for server_data in mcptox:
        logger.info("Benchmark '%s' server", server_data.name)
        scan_result = await benchmark_proxy(server_data, mcp_context_protector)
        for result in scan_result:
            results.append(result.__dict__)

    with open("results.json", "w", encoding="utf8") as file:
        json.dump(results, file)


async def test_scanner():
    dataset = load_mcpsafety()

    results = []
    for server_data in dataset:
        logger.info("Benchmark '%s' server", server_data.name)
        mcp_guard = MCPGuard(server_data)
        # mcp_shield = MCPShield([tool.name for tool in server_data.tools])
        scan_result = await benchmark_scanner(server_data, mcp_guard)
        for tool_name, result in scan_result.items():
            results.append({"name": tool_name, **result.__dict__})

    with open("results.json", "w", encoding="utf8") as file:
        json.dump(results, file)


async def main():
    if len(sys.argv) == 1:
        await test_scanner()  # debug
        sys.exit(0)

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} [proxy / scanner / server]")
        sys.exit(1)

    match sys.argv[1]:
        case "proxy":
            await test_proxy()
        case "scanner":
            await test_scanner()
        case "server":
            await server()


if __name__ == "__main__":
    asyncio.run(main())
