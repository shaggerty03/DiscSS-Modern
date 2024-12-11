import os
import sys
from interactions import Embed, Extension, Client, OptionType, slash_command, slash_option
sys.path.append(os.path.abspath(os.path.join('..', 'utils')))
from utils.database import RedisDB

class WhitelistExtension(Extension):
    OVERRIDE_WHITELIST = [686107711829704725]
    
    def __init__(self, bot) -> None:
        self.bot: Client = bot
        self.db = RedisDB(db=16)
    
    @slash_command(
        name="add-to-whitelist",
        description="Add a user to the whitelist",
    )
    @slash_option(
        name="user",
        description="The user to add to the whitelist",
        required=True,
        opt_type=OptionType.USER
    )
    async def add_to_whitelist(self, ctx, user):
        if not ctx.author.id in self.OVERRIDE_WHITELIST:
            return await ctx.send("You do not have permission to use this command")
        self.db.add_to_whitelist(user.id)
        await ctx.send(f"Added {user.mention} to the whitelist", ephemeral=True)
    
    @slash_command(
        name="remove-from-whitelist",
        description=f"Remove a user from the whitelist",
    )
    @slash_option(
        name="user",
        description="The user to remove from the whitelist",
        required=True,
        opt_type=OptionType.USER
    )
    async def remove_from_whitelist(self, ctx, user):
        if not ctx.author.id in self.OVERRIDE_WHITELIST:
            return await ctx.send("You do not have permission to use this command")
        self.db.remove_from_whitelistt(user.id)
        await ctx.send(f"Removed {user.mention} from the whitelist", ephemeral=True)
    
    @slash_command(
        name="list-whitelist",
        description="List all users in the whitelist",
    )
    async def list_whitelist(self, ctx):
        if not ctx.author.id in self.OVERRIDE_WHITELIST:
            return await ctx.send("You do not have permission to use this command")
        whitelist = self.db.list_whitelist()
        embed = Embed(
            title="Whitelisted Users",
            color=0x000000,
        )
        message = "Here are all the whitelisted users:\n"
        for user_id in whitelist:
            message += f"<@{user_id}>\n"
        embed.add_field(name="Users", value=message, inline=False)
        await ctx.send(embeds=[embed], ephemeral=True)
