import logging
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client

logger = logging.getLogger(__name__)


async def message_handler(
    message,
):
    if isinstance(message, Exception):
        logger.error("Error: %s", message)
        return

    logger.debug("Received message: %s", message)


@asynccontextmanager
async def create_http_session(url: str):
    """
    Create a mcp client session over streamable http
    """

    logger.debug("Create mcp client session (url=%s)", url)
    async with streamable_http_client(url) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
            message_handler=message_handler,
            client_info=None,
        ) as session:
            await session.initialize()
            yield session


@asynccontextmanager
async def create_stdio_session(command: list[str]):
    """
    Attach as a mcp client to a local mcp server over stdio

    Usage:

        command = [
            "uv",
            "run",
            "weather.py",
        ]

        async with create_mcp_session(command) as session:
            print(f"{await session.list_tools() = }")
    """

    logger.debug("Create mcp client session (command='%s')", " ".join(command))
    server_parameters = StdioServerParameters(
        command=command[0],
        args=command[1:],
    )
    async with stdio_client(server_parameters) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
            message_handler=message_handler,
            client_info=None,
        ) as session:
            await session.initialize()
            yield session
