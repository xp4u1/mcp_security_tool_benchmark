import asyncio
import logging
import os
from typing import Any, Callable

from dotenv import load_dotenv
from mcp.server.fastmcp.prompts.base import Prompt
from mcp.server.fastmcp.resources.types import TextResource
from pydantic import AnyUrl

from lib.fastmcp import FastMCP

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
        self.uvicorn_server = None

    async def start(self, instructions: str = ""):
        logger.debug("Starting MCP mock server on port %d", MCP_SERVER_PORT)
        self.mcp = FastMCP(
            name="Benchmark Mock Server",
            port=MCP_SERVER_PORT,
            log_level="WARNING",
            instructions=instructions,
        )
        self.uvicorn_server = await self.mcp.prepare_streamable_http_async()
        self.server_task = asyncio.create_task(self._start_server())

    async def _start_server(self):
        try:
            if self.uvicorn_server:
                await self.uvicorn_server.serve()
            else:
                logger.error(
                    "FastMCP Uvicorn server missing. Cannot start missing server"
                )
                raise RuntimeError("Unable to start MCP server")
        except asyncio.CancelledError:
            logger.debug("MCP mock server task cancelled")
            if self.uvicorn_server:
                await self.uvicorn_server.shutdown()

    async def stop(self):
        if self.server_task:
            self.server_task.cancel()
        else:
            logger.warning("Stop called on missing FastMCP server")

    def add_tool(
        self, name: str, title: str, description: str, callback: Callable[..., Any]
    ):
        if not self.mcp:
            logger.error("No mock server instance found. Did you call 'start'?")
            raise RuntimeError("Missing FastMCP server instance")

        self.mcp.add_tool(
            fn=callback,
            name=name,
            title=title,
            description=description,
        )

    def add_resource(self, name: str, content: str):
        if not self.mcp:
            logger.error("No mock server instance found. Did you call 'start'?")
            raise RuntimeError("Missing FastMCP server instance")

        self.mcp.add_resource(
            TextResource(
                uri=AnyUrl("resource://" + name),
                name=name,
                text=content,
            )
        )

    def add_prompt(self, name: str, content: str):
        if not self.mcp:
            logger.error("No mock server instance found. Did you call 'start'?")
            raise RuntimeError("Missing FastMCP server instance")

        self.mcp.add_prompt(
            Prompt(
                name=name,
                title=name,
                description="Useful prompt",
                arguments=[],
                fn=lambda: content,
                context_kwarg=None,
            )
        )

    async def clear_tools(self):
        if not self.mcp:
            logger.error("No mock server instance found. Did you call 'start'?")
            raise RuntimeError("Missing FastMCP server instance")

        for tool in await self.mcp.list_tools():
            self.mcp.remove_tool(tool.name)
