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
import re
import sys
import yaml
import json
import asyncio

from dotenv import load_dotenv

from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from typing import List, Dict
from jinja2 import Template

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
        self.system = self.setup_system()

    async def connect_to_server(self, cmd: str, args: List[str], env: Dict[str, str]) -> None:
        """
        Connect to MCP Server for Slack communication running on Standard I/O Transport.
        Args:
            cmd (str): Command to initiate the local MCP server instance
            args (List[str]): The list of arguments needed to kick off cmd
            env (Dict[str, str]): environment variables to configure the server behaviors
        """

        server_params = StdioServerParameters(command=cmd, args=args, env=env)

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        self.stdio, self.write = stdio_transport

        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()
        response = await self.session.list_tools()
        tools = response.tools
        print(f"Oldson tools: {[tool.name for tool in tools]}")

        self.available_tools = [{
            "name": tool.name, 
            "description": tool.description, 
            "parameters": tool.inputSchema
        } for tool in tools]

        self.system = Template(self.system).render({"tools": self.available_tools})

    async def handle_request(self, query: str) -> str:
        """Handles the user request as a whole. If the query requests a simple response 
        it returns the model output in plain text. In event of multi-step reasoning and tool use,
        it acts as a ReAct agent that reasons over the current observations from the tools and decide
        to return the final answer or proceed differently.
        Args:
            query (str): User query currently in absence of context

        Returns:
            str: model response or the final answer formulated through ReAct reasoning.
        """

        messages = [
            { "role": "system", "content": self.system },
            { "role": "user", "content": query }
        ]

        response = await generate_message(self.model_client, "egune", messages)


        if (match := re.search(r"```json\s*(.*?)\s*```", response)) is not None:
            tool_call = match.group(1)
            try:
                invocation_request = json.loads(tool_call)

                if ("name" in invocation_request) and ("args" in invocation_request):
                    
                    tool_response = await self.session.call_tool(
                        invocation_request["name"], 
                        invocation_request["args"]
                    )

                    print(f"Tool response: {tool_response}")

                else:
                    print(f"tool invocation request generated/parsed incorrectly: {tool_call}")

            except (ValueError, Exception) as e:
                print(f"Error happened in parsing the invocation request..: {str(e)}")

            sys.exit(0)

        return response
    
    async def initiate_cycle(self) -> None:
        """
        Sets off the ReAct agent cycle by receiving user queries indefinitely.
        If user requests something that requires a series of actions and contemplating
        actions, the request handling method encapsulates those steps according to queries.
        In other words, the session to solve a single query is isolated in itself.
        """

        while True:
            try:
                query = input("(ctrl+c/quit)>>>").strip()

                if query.lower().strip() == "quit":
                    print(f"Quitting the interaction cycle...")
                    sys.exit(0)

                response = await self.handle_request(query)
                print(f"Response: {response}\n")
            
            except Exception as e:
                print(f"Exception in the midst of interaction.\n{str(e)}")
        

    async def cleanup(self) -> None:
        await self.exit_stack.aclose()

    def setup_system(self) -> str:
        with open("config/system.yaml", 'r', encoding="utf-8") as f:
            system = yaml.safe_load(f)

        return system["models"]["egune"]["prompt"]
    
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
        await client.initiate_cycle()

    except Exception as e:
        print(f"ERROR: {str(e)}")
    
    finally:
        await client.cleanup()


if __name__ == '__main__':
    asyncio.run(main())