import json
import logging

from attr import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    name: str
    description: str
    malicious: bool
    category: str


@dataclass
class Server:
    name: str
    instruction: str
    tools: list[Tool]


def load_mcptox() -> list[Server]:
    with open("data/mcptox/response_all.json", "r", encoding="utf-8") as file:
        json_data = json.load(file)

    servers = []

    for server_name, server_data in json_data["servers"].items():
        logger.debug("[%s] Add benign tools", {server_name})

        tools = []

        for tool_name in server_data["tool_names"]:
            tools.append(
                Tool(name=tool_name, description="", malicious=False, category="benign")
            )

        logger.debug("[%s] Add poisoned tools", {server_name})
        attacks = server_data["malicious_instance"]

        for attack in attacks:
            [tool_name, tool_description] = attack["poisoned_tool"].split(
                "Description: ", 1
            )

            tool_name = (
                tool_name.replace("Tool: ", "", 1).replace("\n", "").replace("\\n", "")
            )

            tools.append(
                Tool(
                    name=tool_name,
                    description=tool_description,
                    malicious=True,
                    category=attack["metadata"]["security risk"],
                )
            )

        servers.append(
            Server(
                name=server_name,
                instruction=server_data[
                    "clean_system_promot"
                ],  # spelling mistake in the dataset
                tools=tools,
            )
        )

    return servers


mcp_tox = load_mcptox()
print(mcp_tox)
