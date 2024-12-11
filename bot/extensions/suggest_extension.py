import os
import random
import sys
from interactions import Color, Embed, Extension, Client, Modal, ModalContext, OptionType, ShortText, modal_callback, slash_command, slash_option
from interactions.ext.paginators import Paginator
sys.path.append(os.path.abspath(os.path.join('..', 'utils')))
from utils.database import RedisDB
from utils.db_apis.mdblist import MDBList

class SuggestionsExtension(Extension):
    def __init__(self, bot) -> None:
        self.bot: Client = bot
        self.channel_id = None
        self.db = RedisDB(db=15)
        self.whitelist_db = RedisDB(db=16)
        self.mdblist = MDBList()
    
    @slash_command(name="set-suggestions-channel", description="Set the channel where the suggestions will be sent")
    @slash_option(
        name="channel",
        description="The channel where the suggestions will be sent",
        required=True,
        opt_type=OptionType.CHANNEL
    )
    async def set_channel(self, ctx, channel):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        self.db.set_channel(ctx.guild.id, channel.id)
        await ctx.send(f"Set the suggestions channel to {channel.mention} for server: {ctx.guild.name}")
    
    @slash_command(name="list-suggestions-channels", description="List all channels")
    async def list_channels(self, ctx):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        channels = self.db.list_all_channels()
        if not channels:
            await ctx.send("No channels have been set.")
            return
        message = "Here are all the channels:\n```\n"
        for guild_id, channel_id in channels.items():
            message += f"Guild ID: {guild_id}, Channel ID: {channel_id}\n"
        message += "```"
        await ctx.send(message)
    
    @slash_command(name="delete-channel", description="Delete a channel")
    @slash_option(
        name="guild_id",
        description="The ID of the guild where the channel is",
        required=True,
        opt_type=OptionType.STRING
    )
    async def delete_channel(self, ctx, guild_id: str):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        self.db.delete_channel(guild_id)
        await ctx.send(f"Channel for guild {guild_id} has been deleted.")
    
    """
    @slash_command(name="suggest", description="Suggest a movie to watch in our movie nights")
    @slash_option(
        name="movie",
        description="The movie you want to suggest",
        required=True,
        opt_type=OptionType.STRING
    )
    async def suggest(self, ctx, movie: str):
        await ctx.defer()
        channel = self.db.get_channel(ctx.guild.id)
        if not channel:
            return await ctx.send("You need to set the suggestions channel first. Try using the command `/set-suggestions-channel` with the channel you want to use.")
        channel = self.bot.get_channel(int(channel))
        print(f"Sending suggestion to {channel}")
        await channel.send(f"query: {movie}")
        await ctx.send("Suggestion sent!")
    """
    
    @slash_command(name="clear-all-suggestions", description="Clear all suggestions made by a user")
    async def clear_all_suggestions(self, ctx):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        self.db.clear_all_suggestions()
        await ctx.send("Cleared all suggestions for this month.", ephemeral=True)
    
    @slash_command(name="suggest", description="Suggest a movie to watch in our movie nights")
    async def suggest(self, ctx):
        modal = Modal(
            ShortText(
                label="Movie Title",
                custom_id="movie_title",
                placeholder="Enter the movie title",
                max_length=100,
            ),
            title="Suggest a Movie",
            custom_id="suggest_movie",
        )
        await ctx.send_modal(modal)
    
    @modal_callback("suggest_movie")
    async def suggest_movie(self, ctx: ModalContext, movie_title: str):
        await ctx.send("Please give me one moment...", ephemeral=True)
        print(f"Movie title: {movie_title}")
        results = await self.mdblist.search_movie(query=movie_title)
        if not results or not results.get('search'):
            await ctx.send("No results found for that movie title.", ephemeral=True)
            return
        embeds = []
        for result in results['search']:
            movie_details = await self.mdblist.get_details("i", result["id"])
            extracted_details = await self.mdblist.extract_details(movie_details, result["id"], skip_dominant_colors=True)
            if extracted_details and extracted_details.get("poster", ""):
                extracted = {
                    "poster": movie_details.get("poster", ""),
                    "score_average": movie_details.get("score_average", 0),
                    "type": movie_details.get("type", ""),
                    "description": movie_details.get("description", ""),
                    "runtime": movie_details.get("runtime", 0),
                    "title": movie_details.get("title", ""),
                    "year": movie_details.get("year", 0),
                    "released": movie_details.get("released", ""),
                    "most_dominant_colors": result.get("most_dominant_colors", [])
                }
                most_dominant_color = random.choice(extracted["most_dominant_colors"]) if extracted["most_dominant_colors"] else None
                if most_dominant_color is not None: most_dominant_color = tuple(int(x) for x in most_dominant_color)
                else: most_dominant_color = []
            else:
                embed = Embed(
                    title=movie_title,
                    description=f"Suggested by {ctx.author.username}",
                    color=0x00FF00,
                )
                embed.set_author(name=ctx.author.username, icon_url=ctx.author.avatar_url)
                embed.set_footer(text=f"Suggested by {ctx.author.username}")
                embeds.append(embed)
                continue
            embed = Embed(
                title=extracted["title"] if extracted["title"] else "Unknown",
                color=Color.from_rgb(*most_dominant_color) if most_dominant_color else Color.random(),
                footer="Streamer App | To select a movie, click the checkmark below",
                thumbnail=extracted["poster"],
            )
            embed.add_field(name="Type", value=extracted["type"], inline=True)
            embed.add_field(name="Year", value=extracted["year"], inline=True)
            embed.add_field(name="Released", value=extracted["released"], inline=True)
            embed.add_field(name="Runtime", value=extracted["runtime"], inline=True)
            embed.add_field(name="Score", value=f"{extracted['score_average'] / 10:.1f}/10", inline=True)
            embed.add_field(name="Description", value=f"||{extracted['description']}||", inline=False)
            embeds.append(embed)
        paginator = Paginator.create_from_embeds(self.bot, *embeds)
        paginator.show_callback_button = True
        async def dynamic_callback(ctx):
            await ctx.defer(ephemeral=True)
            await ctx.send("Suggestion sent!", ephemeral=True)
            idx = paginator.page_index
            channel = self.db.get_channel(ctx.guild.id)
            if not channel:
                return await ctx.send("You need to set the suggestions channel first. Try using the command `/set-suggestions-channel` with the channel you want to use.")
            if not self.db.is_whitelisted(str(ctx.author.id)):
                suggestions = self.db.get_suggestions(str(ctx.author.id))
                print(f"Suggestions for {str(ctx.author.id)}: {suggestions}")
                if suggestions is None: suggestions = int(0)
                else:
                    try: suggestions = int(suggestions)
                    except ValueError: suggestions = int(0)
                if suggestions >= 3:
                    await ctx.send("You have reached the maximum number of suggestions for this month.", ephemeral=True)
                    return
                self.db.increment_suggestions(str(ctx.author.id))
            channel = self.bot.get_channel(int(channel))
            print(f"Sending suggestion to {channel}")
            message = await channel.send(embeds=[embeds[idx]], ephemeral=True)
            await message.add_reaction(":white_check_mark:")
            await message.add_reaction(":x:")
        paginator.callback = dynamic_callback
        await paginator.send(ctx, ephemeral=True)
        # if not self.db.is_whitelisted(ctx.author.id):
        #     suggestions = self.db.get_suggestions(ctx.author.id)
        #     if suggestions >= 2:
        #         await ctx.send("You have reached the maximum number of suggestions for this month.", ephemeral=True)
        #         return
        #     self.db.increment_suggestions(ctx.author.id)
        # suggestions = self.db.get_suggestions(ctx.author.id)
        # if suggestions >= 2 and not is_whitelisted(ctx.author.id):
        #     await ctx.send("You have reached the maximum number of suggestions for this month.")
        #     return
        # self.db.increment_suggestions(ctx.author.id)
    
    @slash_command(name="list-suggestions", description="List all suggestions made by a user")
    @slash_option(
        name="user",
        description="The user whose suggestions you want to list",
        required=True,
        opt_type=OptionType.USER
    )
    async def list_suggestions(self, ctx, user):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        suggestions = self.db.list_current_month_suggestions(user.id)
        if not suggestions:
            await ctx.send("No suggestions found for this user.")
            return
        embed = Embed(
            title=f"Suggestions made by {user.username}",
            description="Here are the suggestions made by this user:",
            color=0x00FF00,
        )
        for key, count in suggestions.items():
            parts = key.split(":")
            embed.add_field(name=f"Suggestions for {parts[2]}", value=str(count), inline=False)
        await ctx.send(embeds=[embed], ephemeral=True)
    
    @slash_command(
        name="clear-suggestions",
        description="Clear all suggestions made by a user (for the current month)."
    )
    @slash_option(
        name="user",
        description="The user whose suggestions you want to clear",
        required=True,
        opt_type=OptionType.USER
    )
    @slash_option(
        name="count",
        description="The number of suggestions you want to clear",
        required=False,
        opt_type=OptionType.INTEGER
    )
    async def clear_suggestions(self, ctx, user, count: int = None):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        self.db.clear_suggestions(user.id, count)
        if count is None:
            await ctx.send(f"Cleared all suggestions made by {user.username} for this month.", ephemeral=True)
        else:
            await ctx.send(f"Cleared {count} suggestions made by {user.username} for this month.", ephemeral=True)
