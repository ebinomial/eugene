import asyncio

import os
import sys

sys.path.append('/home/verdine/Projects/eugene/')

from dotenv import load_dotenv
from mcp_client.multiple_clients import StdioMultiClient

load_dotenv()

base_url = os.getenv("BASE_URL")
api_key = os.getenv("OPENAI_API_KEY")

async def main():

    client = StdioMultiClient(base_url, api_key)

    try:
        configs = {
            "slack": {
                "command": "npx",
                "args": ["-y" , "@modelcontextprotocol/server-slack"],
                "transport": "stdio",
                "env": {
                    "SLACK_BOT_TOKEN": os.getenv("SLACK_BOT_TOKEN"),
                    "SLACK_TEAM_ID": os.getenv("SLACK_TEAM_ID"),
                    "SLACK_CHANNEL_IDS": os.getenv("SLACK_CHANNEL_IDS")
                }
            },
            "google_search": {
                "command": "node",
                "transport": "stdio",
                "args": [
                    "/home/verdine/Projects/Google-Search-MCP-Server/dist/google-search.js"
                ],
                "env": {
                    "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
                    "GOOGLE_SEARCH_ENGINE_ID": os.getenv("GOOGLE_SEARCH_ENGINE_ID")
                }
            }
        }


        await client.connect_to_servers(configs)
        await client.initiate_cycle()

    except Exception as e:
        print(f"ERROR: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())