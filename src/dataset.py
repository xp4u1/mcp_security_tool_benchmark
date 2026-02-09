import copy
import json
import logging
import os
from dataclasses import dataclass

from dataclasses_json import dataclass_json

logger = logging.getLogger(__name__)


@dataclass_json
@dataclass
class ToolData:
    name: str
    description: str
    malicious: bool
    category: str
    return_value: str = ""


@dataclass_json
@dataclass
class ServerData:
    name: str
    instruction: str
    tools: list[ToolData]


def load_serialized(path: str) -> list[ServerData]:
    with open(path, "r", encoding="utf8") as file:
        json_data = json.load(file)

    result = []

    for data in json_data:
        result.append(ServerData.from_dict(data))

    return result


def load_mcptox() -> list[ServerData]:
    with open("data/mcptox/response_all.json", "r", encoding="utf-8") as file:
        json_data = json.load(file)

    servers = []

    for server_name, server_data in json_data["servers"].items():
        logger.debug("[%s] Add benign tools", {server_name})

        tools = []

        for tool_name in server_data["tool_names"]:
            tools.append(
                ToolData(
                    name=tool_name, description="", malicious=False, category="benign"
                )
            )

        logger.debug("[%s] Add poisoned tools", {server_name})
        attacks = server_data["malicious_instance"]

        for index, attack in enumerate(attacks):
            [tool_name, tool_description] = attack["poisoned_tool"].split(
                "Description: ", 1
            )

            tool_name = (
                tool_name.replace("Tool: ", "", 1).replace("\n", "").replace("\\n", "")
            )

            tools.append(
                ToolData(
                    # avoid name conflicts
                    name=f"{index}_{tool_name}",
                    description=tool_description,
                    malicious=True,
                    category=attack["metadata"]["security risk"],
                )
            )

        servers.append(
            ServerData(
                name=server_name,
                instruction=server_data[
                    "clean_system_promot"
                ],  # spelling mistake in the dataset
                tools=tools,
            )
        )

    return servers


def mcpsafety_apply_change(base: ServerData, change_file: str) -> ServerData:
    with open(change_file, "r", encoding="utf8") as file:
        json_data = json.load(file)

    tools = {tool.name: tool for tool in base.tools}

    if modifications := json_data.get("mcp_server_modifications"):
        assert len(modifications) == 1

        original_tool = tools[modifications[0]["tool_name"]]
        tools[modifications[0]["tool_name"]] = ToolData(
            name=original_tool.name,
            description=modifications[0].get(
                "modification_description", original_tool.description
            ),
            malicious=True,
            category=json_data["attack_category"],
            return_value=modifications[0].get(
                "modification_return", original_tool.return_value
            ),
        )

    if additions := json_data.get("mcp_server_additions"):
        tools[additions["tool_name"]] = ToolData(
            name=additions["tool_name"],
            description=additions["description"],
            malicious=True,
            category=json_data["attack_category"],
        )

    return ServerData(
        name=base.name, instruction=base.instruction, tools=list(tools.values())
    )


def load_mcpsafety() -> list[ServerData]:
    path = "data/mcpsafety/changes"
    base_servers = {
        server.name: server for server in load_serialized("data/mcpsafety/servers.json")
    }

    servers = []

    for server_name in os.listdir(path):
        for change_file in os.listdir(f"{path}/{server_name}"):
            servers.append(
                mcpsafety_apply_change(
                    base_servers[server_name], f"{path}/{server_name}/{change_file}"
                )
            )

    return servers
