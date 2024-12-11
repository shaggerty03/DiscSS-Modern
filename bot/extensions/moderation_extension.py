import os
import sys
from interactions import Extension, Client, OptionType, slash_command, slash_option
sys.path.append(os.path.abspath(os.path.join('..', 'utils')))
from utils.database import RedisDB

class ModerationExtension(Extension):
    def __init__(self, bot) -> None:
        self.bot: Client = bot
        self.whitelist_db = RedisDB(db=16)

    @slash_command(name="purge", description="Purge messages from a channel")
    @slash_option(name="amount", description="The amount of messages to purge", required=True, opt_type=OptionType.INTEGER)
    async def purge(self, ctx, amount: int):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        channel = ctx.channel
        messages = []
        # Discord API limits the amount of messages that can be deleted at once to 100.
        async for message in channel.history(limit=100):
            messages.append(message)
        await channel.delete_messages(messages)
        await ctx.send(f"Purged {amount} messages.", ephemeral=True)
