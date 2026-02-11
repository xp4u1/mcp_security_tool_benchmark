import json
import logging
import os

from dataset import DatasetLoader, ServerData, ToolData

logger = logging.getLogger(__name__)


class MCPSafety(DatasetLoader):
    def load_serialized(self, path: str) -> list[ServerData]:
        with open(path, "r", encoding="utf8") as file:
            json_data = json.load(file)

        result = []

        for data in json_data:
            result.append(ServerData.from_dict(data))

        return result

    def apply_change(self, base: ServerData, change_file: str) -> ServerData:
        logger.debug("Generating change '%s'", change_file)

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

        if not (additions or modifications):
            logger.debug("Skip '%s' (unsupported change/attack)", change_file)

        return ServerData(
            name=base.name, instruction=base.instruction, tools=list(tools.values())
        )

    def load(self) -> list[ServerData]:
        """
        Load the MCPSafety dataset. Returns a new ServerData object for each
        scenario (change file) from the dataset.
        """

        logger.info("Loading MCPSafety dataset")

        path = "data/mcpsafety/changes"
        base_servers = {
            server.name: server
            for server in self.load_serialized("data/mcpsafety/servers.json")
        }

        servers = [
            self.apply_change(
                base_servers[server_name], f"{path}/{server_name}/{change_file}"
            )
            for server_name in os.listdir(path)
            for change_file in os.listdir(f"{path}/{server_name}")
        ]

        # filter skipped entries
        return [
            server for server in servers if any(tool.malicious for tool in server.tools)
        ]
