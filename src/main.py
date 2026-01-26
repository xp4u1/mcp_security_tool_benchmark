import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from mcp_session import create_http_session, create_stdio_session

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("benchmark")

load_dotenv()
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT") or 4200)


async def main():
    async def start_context_protector():
        command = [
            "/home/paul/documents/dhbw/t2000/tools/mcp-context-protector/mcp-context-protector.sh",
            "--guardrail-provider",
            "LlamaFirewall",
            "--url",
            f"http://127.0.0.1:{MCP_SERVER_PORT}/mcp",
        ]

        async with create_stdio_session(command) as session:
            print(f"{await session.list_tools() = }")

    logger.debug("Starting mcp mock server")
    mcp = FastMCP(
        name="Benchmark Mock Server", port=MCP_SERVER_PORT, log_level="WARNING"
    )

    server_task = asyncio.create_task(mcp.run_streamable_http_async())

    logger.debug("Add test tool")
    mcp.add_tool(
        fn=lambda params: print(params, file=sys.stderr),
        name="test2",
        title="Test Title",
        description="Lorem ipsum dolor sit amet",
    )

    # logger.debug("Connect to mock server")
    # async with create_http_session(
    #     f"http://127.0.0.1:{MCP_SERVER_PORT}/mcp"
    # ) as session:
    #     print(f"{await session.list_tools() = }")

    logger.debug("Start mcp-context-protector")
    await start_context_protector()

    logger.debug("Shutting down mock server")
    server_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
