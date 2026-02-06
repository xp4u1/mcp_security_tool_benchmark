import asyncio
import json
import logging

from benchmark import benchmark_proxy
from dataset import load_mcptox
from tools.mcp_context_protector import MCPContextProtector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")


async def main():
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


if __name__ == "__main__":
    asyncio.run(main())
