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

from typing import Optional

from typing import List, Optional, Dict
from jinja2 import Template

from langchain_mcp_adapters.client import MultiServerMCPClient
from src.models import setup_client, generate_message

class StdioMultiClient:

    def __init__(self, base_url: str, api_key: str) -> None:
        self.client: Optional[MultiServerMCPClient] = None
        self.model_client = setup_client(base_url, api_key)
        self.system = self.setup_system()

    async def connect_to_servers(self, server_configs: Dict[str, Dict]) -> None:
        """
        Connect to multiple MCP servers using MultiServerMCPClient
        Args:
            server_configs: Dictionary mapping server names to their configurations
        """
        self.client = MultiServerMCPClient(server_configs)
        
        # Get all tools from all servers
        self.available_tools = await self.client.get_tools()
        print(f"Available tools from all servers: {[tool.name for tool in self.available_tools]}")
        
        # Update system prompt with all available tools
        self.system = Template(self.system).render({"tools": self.available_tools})

    async def handle_request(self, context: List[Dict[str, str]]) -> None:
        """
        Multi-step (possibly) circulation to solve a single user request.
        In comparison to the single server MCP used in stdio_client.py it abstracts away
        the use of exit stack and sessions.

        Args:
            context (List[Dict[str, str]): User query currently in absence of context
        """

        is_process = True
        while is_process:
            
            raw_response_output = await generate_message(
                self.model_client,
                model="chatgpt-4o-latest",
                context=context
            )

            try:
                model_response = json.loads(raw_response_output)

                if model_response["decision"] == "tool":
                    if "tool" in model_response:
                        tool_name = model_response["tool"]["name"]
                        tool_args = model_response["tool"]["args"]

                        # Find and invoke the tool (works across all servers)
                        tool = next((t for t in self.available_tools if t.name == tool_name), None)
                        if tool:
                            tool_response = await tool.ainvoke(tool_args)
                            context.append({"role": "assistant", 
                                          "content": f"TOOL RESPONSE SAYS:\n{tool_response}"})
                        else:
                            context.append({"role": "assistant", 
                                          "content": f"Tool {tool_name} not found"})
                else:
                    print(f"FINAL:\n{model_response}")
                    is_process = False
                    return

            except ValueError as e:
                print(f"Parsing error: {str(e)}")
                is_process=False

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


                context = [
                    { "role" : "system" , "content" : self.system },
                    { "role" : "user", "content": query }
                ]

                response = await self.handle_request(context)
                print(f"Response: {response}\n")
            
            except Exception as e:
                print(f"Exception in the midst of interaction.\n{str(e)}")
        
    def setup_system(self) -> str:
        with open("config/system.txt", 'r', encoding="utf-8") as f:
            system = f.read()

        return system
    