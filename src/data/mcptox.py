import json
import logging

from dataset import DatasetLoader, ServerData, ToolData

logger = logging.getLogger(__name__)


class MCPTox(DatasetLoader):
    def load(self) -> list[ServerData]:
        """
        Load the MCPTox dataset
        """

        logger.info("Loading MCPTox dataset")

        with open("data/mcptox/response_all.json", "r", encoding="utf-8") as file:
            json_data = json.load(file)

        servers = []

        for server_name, server_data in json_data["servers"].items():
            logger.debug("[%s] Add benign tools", {server_name})

            tools = []

            for tool_name in server_data["tool_names"]:
                tools.append(
                    ToolData(
                        name=tool_name,
                        description="",
                        malicious=False,
                        category="benign",
                    )
                )

            logger.debug("[%s] Add poisoned tools", {server_name})
            attacks = server_data["malicious_instance"]

            for index, attack in enumerate(attacks):
                [tool_name, tool_description] = attack["poisoned_tool"].split(
                    "Description: ", 1
                )

                tool_name = (
                    tool_name.replace("Tool: ", "", 1)
                    .replace("\n", "")
                    .replace("\\n", "")
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
                        # spelling mistake in the dataset
                        "clean_system_promot"
                    ],
                    tools=tools,
                )
            )

        return servers
