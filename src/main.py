import asyncio
import csv
import logging
import sys

import pandas as pd

from benchmark import benchmark_proxy, benchmark_scanner, init_server_content
from data.mcpsafety import MCPSafety
from data.mcptox import MCPTox
from dataset import load_dataset, save_dataset
from mock_server import MockServer
from tools.mcp_context_protector import MCPContextProtector
from tools.mcp_guard import MCPGuard
from tools.mcp_scan import MCPScan
from tools.mcp_scanner import MCPScanner
from tools.mcp_shield import MCPShield

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(format=LOG_FORMAT, datefmt=DATE_FORMAT, level=logging.INFO)
logger = logging.getLogger("main")

RETRY_TIMEOUT_SECONDS = 600


async def server():
    dataset = load_dataset()
    mock_server = MockServer()
    await mock_server.start()
    init_server_content(mock_server, dataset[0].server)

    while True:
        await asyncio.sleep(10)


async def test_proxy():
    dataset = load_dataset()
    results = pd.DataFrame()
    proxies = [MCPContextProtector()]

    for scenario in dataset[:2]:
        logger.info("Benchmark '%s' server (%s)", scenario.server.name, scenario.id)

        for proxy in proxies:
            logger.info("Scanning scenario %s using %s", scenario.id, proxy.__module__)

            benchmark_result = await benchmark_proxy(scenario.server, proxy)
            results = pd.concat([results, benchmark_result])
            export_csv(results, "/tmp/benchmark_results.csv")  # checkpoint

    logger.info("Exporting results as csv")
    export_csv(results, "results.csv")


def export_csv(dataframe: pd.DataFrame, path: str):
    dataframe.replace(r"\r\n|\r|\n", r"\\n", regex=True).to_csv(
        path, index=False, quoting=csv.QUOTE_ALL
    )


async def test_scanner():
    dataset = load_dataset()
    results = pd.DataFrame()

    for scenario in dataset:
        logger.info("Benchmark '%s' server (%s)", scenario.server.name, scenario.id)

        scanners = [
            MCPShield([tool.name for tool in scenario.server.tools]),
            MCPGuard(scenario.server),
            MCPScan(),
            MCPScanner(analyzers=["llm", "yara"]),
        ]

        for scanner in scanners:
            logger.info(
                "Scanning scenario %s using %s", scenario.id, scanner.__module__
            )

            benchmark_result = None
            while benchmark_result == None:
                try:
                    benchmark_result = await benchmark_scanner(scenario.server, scanner)
                    benchmark_result["dataset"] = scenario.dataset
                    benchmark_result["scenario_id"] = scenario.id

                    return benchmark_result
                except RuntimeError:
                    logger.warning(
                        "Benchmark failed. Sleeping %d seconds...",
                        RETRY_TIMEOUT_SECONDS,
                    )
                    await asyncio.sleep(RETRY_TIMEOUT_SECONDS)
                    logger.warning("Trying again")

            results = pd.concat([results, benchmark_result])
            export_csv(results, "/tmp/benchmark_results.csv")  # checkpoint

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
