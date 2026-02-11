import asyncio
import csv
import json
import logging
import sys

import pandas as pd

from benchmark import benchmark_proxy, benchmark_scanner
from data.mcpsafety import MCPSafety
from data.mcptox import MCPTox
from dataset import load_dataset, save_dataset
from mock_server import MockServer
from tools.mcp_context_protector import MCPContextProtector
from tools.mcp_guard import MCPGuard
from tools.mcp_scan import MCPScan
from tools.mcp_shield import MCPShield

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(format=LOG_FORMAT, datefmt=DATE_FORMAT, level=logging.INFO)
logger = logging.getLogger("main")


async def server():
    dataset = load_dataset()
    mock_server = MockServer()
    await mock_server.start()
    init_server_content(mock_server, dataset[0].server)

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


def export_csv(dataframe: pd.DataFrame, path: str):
    dataframe.replace({r"\r\n|\r|\n": r"\\n"}, regex=True).to_csv(
        path, index=False, quoting=csv.QUOTE_ALL
    )


async def _tmp(scenario, scanner):
    try:
        benchmark_result = await benchmark_scanner(scenario.server, scanner)
        benchmark_result["dataset"] = scenario.dataset
        benchmark_result["scenario_id"] = scenario.id

        return benchmark_result
    except RuntimeError:
        logger.warning("Benchmark failed. Sleeping 10 minutes...")
        await asyncio.sleep(600)
        logger.warning("Trying again")
        return await _tmp(scenario, scanner)


async def test_scanner():
    dataset = load_dataset()
    results = pd.DataFrame()

    for scenario in dataset:
        logger.info("Benchmark '%s' server (%s)", scenario.server.name, scenario.id)

        # scanners = [
        #     MCPShield([tool.name for tool in scenario.server.tools]),
        #     MCPGuard(scenario.server),
        # ]
        scanners = [MCPScan()]

        for scanner in scanners:
            logger.info(
                "Scanning scenario %s using %s", scenario.id, scanner.__module__
            )

            benchmark_result = await _tmp(scenario, scanner)
            results = pd.concat([results, benchmark_result])
            export_csv(results, "/tmp/benchmark_results.csv")  # checkpoint
            await asyncio.sleep(120)

    logger.info("Exporting results as csv")
    export_csv(results, "results.csv")


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
        case "save_dataset":
            save_dataset([MCPTox(), MCPSafety()])


if __name__ == "__main__":
    asyncio.run(main())
