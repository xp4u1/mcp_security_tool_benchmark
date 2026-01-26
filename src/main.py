import asyncio
import logging

from tools.mcp_context_protector import MCPContextProtector

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("benchmark")


async def main():
    mcp_context_protector = MCPContextProtector()
    await mcp_context_protector.initialize()
    await mcp_context_protector.close()


if __name__ == "__main__":
    asyncio.run(main())
