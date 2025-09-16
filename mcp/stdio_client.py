# MIT License

# Copyright (c) 2025 Erdenebileg Byambadorj

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import os
import sys
import asyncio

from dotenv import load_dotenv

from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from typing import List, Dict

_ = load_dotenv()

base_url = os.getenv("BASE_URL")
api_key = os.getenv("API_KEY")

from src.models import setup_client, generate_message

class StdioClient:

    def __init__(self) -> None:
        """
        The client and the server is in exact 1-1 relationship.
        It's the convention to use the client session to communicate with the tool,
        though I'd have preferred otherwise.
        """
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.model_client = setup_client(base_url, api_key)

    async def connect_to_server(self, cmd: str, args: List[str], env: Dict[str, str]) -> None:
        """
        Connect to MCP Server for Slack communication running on Standard I/O Transport.
        """

        print(env)
        server_params = StdioServerParameters(command=cmd, args=args, env=env)

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()
        response = await self.session.list_tools()
        tools = response.tools

        print(f"Oldson tools: {[tool.name for tool in tools]}")

    async def process_query(self, query: str) -> str:
        raise NotImplementedError()
    
    async def interaction_loop(self) -> None:
        raise NotImplementedError()
    
    async def cleanup(self) -> None:
        await self.exit_stack.aclose()
    
async def main():

    client = StdioClient()
    try:

        cmd = "npx"
        args = ["-y" , "@modelcontextprotocol/server-slack"]
        env = {
            "SLACK_BOT_TOKEN": os.getenv("SLACK_BOT_TOKEN"),
            "SLACK_TEAM_ID": os.getenv("SLACK_TEAM_ID"),
            "SLACK_CHANNEL_IDS": os.getenv("SLACK_CHANNEL_IDS")
        }

        await client.connect_to_server(cmd, args, env)

    except Exception as e:
        print(f"ERROR: {str(e)}")
    
    finally:
        await client.cleanup()


if __name__ == '__main__':
    asyncio.run(main())