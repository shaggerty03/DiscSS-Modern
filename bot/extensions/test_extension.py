import os
import sys
from interactions import Extension, Client, slash_command
sys.path.append(os.path.abspath(os.path.join('..', 'utils')))
from utils.http_client import HttpClient
from utils.endpoints import Endpoints


class TestExtension(Extension):
    def __init__(self, bot) -> None:
        self.bot: Client = bot
        self.client: HttpClient = HttpClient()
    
    @slash_command(name="test", description="A test command")
    async def test(self, ctx):
        response = await self.client.get(Endpoints.STATUS.value)
        if response["status"] == 200:
            await ctx.send(f"Code: **{response['status']}**\nData: **{response['data']['message']}**.\n*(Full response: {response})*")
        else:
            await ctx.send(f"Code: **{response['status']}**\nData: **{response['data']['message']}**.\n*(Full response: {response})*")
