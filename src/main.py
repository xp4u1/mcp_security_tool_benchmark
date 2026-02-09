import asyncio
import csv
import json
import logging
import sys
from uuid import uuid4

import pandas as pd

from benchmark import benchmark_proxy, benchmark_scanner
from data.mcpsafety import MCPSafety
from data.mcptox import MCPTox
from dataset import Dataset
from mock_server import MockServer
from tools.mcp_context_protector import MCPContextProtector
from tools.mcp_guard import MCPGuard
from tools.mcp_shield import MCPShield

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")


async def server():
    mcptox = MCPTox().load()
    mock_server = MockServer()
    await mock_server.start()

    for tool in mcptox[0].tools:
        mock_server.add_tool(tool.name, tool.name, tool.description, lambda: "Test")

    while True:
        await asyncio.sleep(10)


async def test_proxy():
    mcptox = MCPTox().load()
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
    datasets: list[Dataset] = [MCPTox(), MCPSafety()]
    results = pd.DataFrame()

    for dataset in datasets:
        for server_data in dataset.load():
            scenario_id = uuid4()
            logger.info("Benchmark '%s' server (%s)", server_data.name, scenario_id)

            scanners = [
                MCPShield([tool.name for tool in server_data.tools]),
                MCPGuard(server_data),
            ]

            for scanner in scanners:
                logger.info(
                    "Scanning scenario %s using %s", scenario_id, scanner.__module__
                )
                benchmark_result = await benchmark_scanner(server_data, scanner)
                benchmark_result["dataset"] = dataset.__module__
                benchmark_result["scenario_id"] = scenario_id

                results = pd.concat([results, benchmark_result])

    logger.info("Exporting results as csv")
    results.replace({r"\r\n|\r|\n": r"\\n"}, regex=True).to_csv(
        "results.csv", index=False, quoting=csv.QUOTE_ALL
    )


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
