import asyncio
import logging
import os
from typing import Any, Callable

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

load_dotenv()
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT") or 4200)


class MockServer:
    """
    Creates a FastMCP server over streamable http.
    """

    def __init__(self):
        self.mcp = None
        self.server_task = None

    async def start(self):
        logger.debug("Starting MCP mock server on port %d", MCP_SERVER_PORT)
        self.mcp = FastMCP(
            name="Benchmark Mock Server", port=MCP_SERVER_PORT, log_level="WARNING"
        )
        self.server_task = asyncio.create_task(self._start_server())

    async def _start_server(self):
        try:
            if self.mcp:
                await self.mcp.run_streamable_http_async()
            else:
                logger.critical("FastMCP missing. Cannot start missing server")
                raise RuntimeError("Unable to start MCP server")
        except asyncio.CancelledError:
            logger.debug("MCP mock server task cancelled")

    async def stop(self):
        if self.server_task:
            self.server_task.cancel()
        else:
            logger.debug("Stop called on missing FastMCP server")

    def add_tool(
        self, name: str, title: str, description: str, callback: Callable[..., Any]
    ):
        self.mcp.add_tool(
            fn=callback,
            name=name,
            title=title,
            description=description,
        )
