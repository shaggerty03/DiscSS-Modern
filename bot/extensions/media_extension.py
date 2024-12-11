import random
import uuid
import os
import re
import sys
from interactions import Button, ButtonStyle, Color, ComponentContext, Embed, Extension, Client, OptionType, SlashCommandChoice, component_callback, slash_command, slash_option
from interactions.ext.paginators import Paginator
sys.path.append(os.path.abspath(os.path.join('..', 'utils')))
from utils.database import RedisDB
from utils.media_utils import TV_PATH, get_media_type, get_movie_files, get_movie_folders, get_tv_show_files, get_tv_show_files_extra, get_tv_show_files_extra_batch, get_tvshow_folders, get_video_length, sort_tv_show_episodes, truncate_sorted_episodes
from utils.http_client import HttpClient
from utils.db_apis.mdblist import MDBList

class MediaExtension(Extension):
    def __init__(self, bot) -> None:
        self.bot: Client = bot
        self.client = Client()
        self.mdblist = MDBList()
        self.client: HttpClient = HttpClient()
        self.uuids = {}
        self.title_uuids = {}
        
        # DB
        self.whitelist_db = RedisDB(db=16)
        
        # Lock
        self.playing = False
    
    @slash_command(name="search", description="Search for media")
    @slash_option(
        name="query",
        description="The search query",
        required=True,
        opt_type=OptionType.STRING
    )
    async def search(self, ctx, query: str):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        if "@everyone" in query or "@here" in query:
            await ctx.send("Please don't use @everyone or @here in your search query.", ephemeral=True)
            return
        await ctx.defer()
        await ctx.send("Processing your request...", ephemeral=True)
        guild_id_caller, author_id = str(ctx.guild.id), str(ctx.author.id)
        movie_folders = get_movie_folders()
        tvshow_folders = get_tvshow_folders()
        all_folders = movie_folders + tvshow_folders
        matched_folders = [folder for folder in all_folders if query.lower().replace('.', '') in folder.lower().replace('.', '')]
        print(f"Matched folders: {matched_folders}")
        if matched_folders:
            embeds = []
            tv_show_files = get_tv_show_files(show_folders=matched_folders)
            for folder in matched_folders:
                files = get_movie_files(movie_folder=folder) if folder in movie_folders else sort_tv_show_episodes(tv_show_files.get(folder, {}))
                if folder in files and files[folder]:
                    path = files[folder][0] if folder in movie_folders else next((files[folder][s][0] for s in files[folder] if files[folder][s]), None)
                    if not path:
                        await ctx.send(f"Invalid path: {path} (Folder: {folder}. **Please screenshot and send to unicorns!**)")
                        continue
                    imdb_id = re.search(r'imdbid-(tt\d+)', path)
                    if imdb_id:
                        imdb_id = imdb_id.group(1)
                        details_data = await self.mdblist.get_details("i", imdb_id)
                        details = await self.mdblist.extract_details(details=details_data, skip_dominant_colors=False, id=imdb_id)
                        if details and details.get("poster", ""):
                            extracted = {
                                "poster": details.get("poster", ""),
                                "score_average": details.get("score_average", 0),
                                "type": details.get("type", ""),
                                "description": details.get("description", ""),
                                "runtime": details.get("runtime", 0),
                                "title": details.get("title", ""),
                                "year": details.get("year", 0),
                                "released": details.get("released", ""),
                                "most_dominant_colors": details.get("most_dominant_colors", [])
                            }
                            most_dominant_color = random.choice(extracted["most_dominant_colors"]) if extracted["most_dominant_colors"] else None
                            if most_dominant_color is not None:
                                most_dominant_color = tuple(int(x) for x in most_dominant_color)
                            else:
                                most_dominant_color = []
                        else:
                            await ctx.send(f"Failed to extract details? (Search) (Details: {details}). Please send this to unicorns if you encounter this issue.", ephemeral=True)
                        print(f"Most Dominant Color: {most_dominant_color}")
                        embed = Embed(
                            title=extracted["title"] if extracted["title"] else "Unknown",
                            color=Color.from_rgb(*most_dominant_color) if most_dominant_color else Color.random(),
                            footer="Streamer App | By femboy maid unicorns uwu",
                            thumbnail=extracted["poster"],
                        )
                        embed.add_field(name="Type", value=extracted["type"], inline=True)
                        embed.add_field(name="Year", value=extracted["year"], inline=True)
                        embed.add_field(name="Released", value=extracted["released"], inline=True)
                        embed.add_field(name="Runtime", value=extracted["runtime"], inline=True)
                        embed.add_field(name="Score", value=f"{extracted['score_average'] / 10:.1f}/10", inline=True)
                        embed.add_field(name="Description", value=extracted["description"], inline=False)
                        file_identifier = str(uuid.uuid4())
                        self.uuids[file_identifier] = path
                        embeds.append((embed, file_identifier))
            if embeds:
                if len(embeds) == 1:
                    embed, file_identifier = embeds[0]
                    play_button = Button(
                        style=ButtonStyle.PRIMARY,
                        label="Play",
                        custom_id=f"play_media_{file_identifier}"
                    )
                    info_button = Button(
                        style=ButtonStyle.SECONDARY,
                        label="Info",
                        custom_id=f"info_media_{file_identifier}"
                    )
                    imdb_button = Button(
                        style=ButtonStyle.LINK,
                        label="IMDb",
                        url=f"https://www.imdb.com/title/{imdb_id}"
                    )
                    await ctx.send(embed=embed, components=[play_button, info_button, imdb_button])
                else:
                    paginator = Paginator.create_from_embeds(self.bot, *[embed for embed, _ in embeds])
                    paginator.show_callback_button = True
                    
                    async def dynamic_callback(ctx):
                        await ctx.defer(ephemeral=False)
                        await ctx.send("Processing your request...", ephemeral=True)
                        index = paginator.page_index
                        _, file_identifier = embeds[index]
                        folder_path = self.uuids.get(file_identifier)
                        if folder_path:
                            title = ctx.message.embeds[0].title
                            print(f"Title: {title}")
                            media_type = "Movies" if title in get_movie_folders() else "TV Shows"
                            print(f"Media Type: {media_type}")
                            if media_type == "Movies":
                                movie_files = get_movie_files(movie_folder=title)
                                if movie_files:
                                    media_file = self.get_largest_media_file(title)
                                    if media_file:
                                        response = await self.client.post('play', {
                                            "title": media_file['title'],
                                            "path": media_file['path'],
                                            "type": media_type,
                                            "sorted_episodes": [] if media_type == "Movies" else sorted_episodes,
                                            "guild_id": guild_id_caller,
                                            "author": author_id
                                        })
                                        if response["status"] == 200:
                                            await ctx.send(content="Media file details sent successfully.", ephemeral=True)
                                        else:
                                            await ctx.send(content="Failed to send media file details.", ephemeral=True)
                                    else:
                                        await ctx.send(content="No valid media files found in the closest matching movie folder.", ephemeral=True)
                                else:
                                    await ctx.send(content="No movie files found.", ephemeral=True)
                            elif media_type == "TV Shows":
                                sorted_episodes = sort_tv_show_episodes(get_tv_show_files_extra(show_folder=title))
                                media_type = get_media_type(file_path=folder_path)
                                response = await self.client.post('play', {
                                    "title": title,
                                    "path": folder_path,
                                    "type": media_type if media_type == "Movies" else "TV Shows",
                                    "sorted_episodes": [] if media_type == "Movies" else sorted_episodes,
                                    "guild_id": guild_id_caller,
                                    "author": author_id
                                })
                                if response["status"] == 200:
                                    await ctx.send(content="Media file details sent successfully.", ephemeral=True)
                                else:
                                    await ctx.send(content="Failed to send media file details.", ephemeral=True)
                            else:
                                await ctx.send(content="No matching media folder found.", ephemeral=True)
                        else:
                            await ctx.send(content="Invalid file identifier.", ephemeral=True)
                    
                    paginator.callback = dynamic_callback
                    for i, (embed, _) in enumerate(embeds):
                        embed.set_footer(text=f"{i+1} of {len(embeds)} | Streamer App | By femboy maid unicorns uwu")
                    await paginator.send(ctx)
            else:
                await ctx.send(f"No media found matching the query: {query}")
        else:
            await ctx.send(f"No media found matching the query: {query}")
    
    @component_callback(re.compile(r"play_media_(.*)"))
    async def play_media_callback(self, ctx: ComponentContext):
        await ctx.defer()
        await ctx.send("Processing your request...", ephemeral=True)
        file_identifier = ctx.custom_id.split("_")[-1]
        guild_id_caller, author_id = str(ctx.guild.id), str(ctx.author.id)
        if ctx.author.voice:
            path = self.uuids.get(file_identifier)
            title = ctx.message.embeds[0].title
            if path:
                media_type = get_media_type(file_path=path)
                if media_type == "TV Shows":
                    tvshowfiles = get_tv_show_files_extra(show_folder=title)
                    sorted_episodes = sort_tv_show_episodes(tvshowfiles)
                    # TODO: Change this in the future to chunk the seasons and send them in batches
                    sorted_episodes = truncate_sorted_episodes(sorted_episodes, "Season 10")
                    response = await self.client.post('play', {
                        "title": title,
                        "path": path,
                        "type": media_type,
                        "sorted_episodes": [] if media_type == "Movies" else sorted_episodes,
                        "guild_id": guild_id_caller,
                        "author": author_id,
                    })
                    if response["status"] == 200:
                        await ctx.send(content=f"Media file details sent successfully. ({response})")
                    else:
                        await ctx.send(content=f"Failed to send media file details. ({response})")
                else:
                    await ctx.send(content="No matching movie folder found.")
            else:
                await ctx.send(content="No matching media folder found.")
        else:
            await ctx.send("Please join a voice channel first.", ephemeral=True)
    
    @slash_command(name="pause", description="Pause the currently playing media")
    async def pause(self, ctx):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        await ctx.send("Processing your request...", ephemeral=True)
        try:
            response = await self.client.get('pause')
            print(response)
            
            if response["status"] == 200:
                await ctx.edit(content="Media paused successfully.")
            else:
                await ctx.edit(content="Failed to pause media.")
        except Exception as e:
            print(f"Error pausing movie: {str(e)}")
            await ctx.edit(content=f"Failed to pause media.")
    
    @slash_command(name="resume", description="Resume the currently paused media")
    async def resume(self, ctx):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        await ctx.send("Processing your request...", ephemeral=True)
        try:
            response = await self.client.get('resume')
            if response["status"] == 200:
                await ctx.edit(content="Media resumed successfully.")
            else:
                await ctx.edit(content="Failed to resume media.")
        except Exception as e:
            print(f"Error resuming movie: {str(e)}")
            await ctx.edit(content=f"Failed to resume media.")
    
    @slash_command(name="stop", description="Stop the currently playing media")
    async def stop(self, ctx):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        await ctx.defer()
        await ctx.send("Processing your request...", ephemeral=True)
        try:
            response = await self.client.get('stop')
            if response["status"] == 200:
                await ctx.send("Media stopped successfully.")
                self.playing = False
            else:
                await ctx.send("Failed to stop media.")
        except Exception as e:
            print(f"Error stopping movie: {str(e)}")
            await ctx.send(f"Failed to stop media. (Exception: {e})")
    
    @slash_command(name="play", description="Play a movie or TV show")
    @slash_option(
        name="title",
        description="The title of the media to play",
        required=True,
        opt_type=OptionType.STRING
    )
    @slash_option(
        name="season",
        description="The season of the TV show to play",
        required=False,
        opt_type=OptionType.INTEGER
    )
    @slash_option(
        name="episode",
        description="The episode of the TV show to play",
        required=False,
        opt_type=OptionType.INTEGER
    )
    async def play(self, ctx, title: str, season: int = None, episode: int = None):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        # if self.playing:
        #     await ctx.send("Please wait for the current media to finish playing... Or use the stop command.", ephemeral=True)
        #     return
        if not ctx.author.voice:
            await ctx.send("Please join a voice channel first.", ephemeral=True)
            return
        if "@everyone" in title or "@here" in title:
            await ctx.send("Please don't use @everyone or @here in your title.", ephemeral=True)
            return
        # self.playing = True
        await ctx.send("Processing your request...")
        movie_folders, tvshow_folders = get_movie_folders(), get_tvshow_folders()
        all_folders = movie_folders + tvshow_folders
        matched_folders = [folder for folder in all_folders if title.lower().replace('.', '') in folder.lower().replace('.', '')]
        print(f"Matched folders: {matched_folders}")
        if matched_folders:
            embeds = []
            tv_show_files = get_tv_show_files(show_folders=matched_folders)
            for folder in matched_folders:
                files = get_movie_files(movie_folder=folder) if folder in movie_folders else sort_tv_show_episodes(tv_show_files.get(folder, {}))
                if folder in files and files[folder]:
                    path = files[folder][0] if folder in movie_folders else next((files[folder][s][0] for s in files[folder] if files[folder][s]), None)
                    if not path:
                        await ctx.send(f"Invalid path: {path} (Folder: {folder}. **Please screenshot and send to unicorns!**)")
                        continue
                    imdb_id = re.search(r'imdbid-(tt\d+)', path)
                    if imdb_id:
                        imdb_id = imdb_id.group(1)
                        details_data = await self.mdblist.get_details("i", imdb_id)
                        details = await self.mdblist.extract_details(details=details_data, skip_dominant_colors=False, id=imdb_id)
                        if details and details.get("poster", ""):
                            extracted = {
                                "poster": details.get("poster", ""),
                                "score_average": details.get("score_average", 0),
                                "type": details.get("type", ""),
                                "description": details.get("description", ""),
                                "runtime": details.get("runtime", 0),
                                "title": details.get("title", ""),
                                "year": details.get("year", 0),
                                "released": details.get("released", ""),
                                "most_dominant_colors": details.get("most_dominant_colors", [])
                            }
                            most_dominant_color = random.choice(extracted["most_dominant_colors"]) if extracted["most_dominant_colors"] else None
                            if most_dominant_color is not None:
                                most_dominant_color = tuple(int(x) for x in most_dominant_color)
                            else:
                                most_dominant_color = []
                        else:
                            await ctx.send(f"Failed to extract details? (Search) (Details: {details}). Please send this to unicorns if you encounter this issue.", ephemeral=True)
                        print(f"Most Dominant Color: {most_dominant_color}")
                        embed = Embed(
                            title=extracted["title"] if extracted["title"] else "Unknown",
                            color=Color.from_rgb(*most_dominant_color) if most_dominant_color else Color.random(),
                            footer="Streamer App | By femboy maid unicorns uwu",
                            thumbnail=extracted["poster"],
                        )
                        embed.add_field(name="Type", value=extracted["type"], inline=True)
                        embed.add_field(name="Year", value=extracted["year"], inline=True)
                        embed.add_field(name="Released", value=extracted["released"], inline=True)
                        embed.add_field(name="Runtime", value=extracted["runtime"], inline=True)
                        embed.add_field(name="Score", value=f"{extracted['score_average'] / 10:.1f}/10", inline=True)
                        embed.add_field(name="Description", value=extracted["description"], inline=False)
                        file_identifier = str(uuid.uuid4())
                        self.uuids[file_identifier] = path
                        embeds.append((embed, file_identifier))
            if embeds:
                if len(embeds) == 1:
                    embed, file_identifier = embeds[0]
                    play_button = Button(
                        style=ButtonStyle.PRIMARY,
                        label="Play",
                        custom_id=f"play_media_{file_identifier}"
                    )
                    info_button = Button(
                        style=ButtonStyle.SECONDARY,
                        label="Info",
                        custom_id=f"info_media_{file_identifier}"
                    )
                    imdb_button = Button(
                        style=ButtonStyle.LINK,
                        label="IMDb",
                        url=f"https://www.imdb.com/title/{imdb_id}"
                    )
                    await ctx.send(embed=embed, components=[play_button, info_button, imdb_button])
                else:
                    paginator = Paginator.create_from_embeds(self.bot, *[embed for embed, _ in embeds])
                    paginator.show_callback_button = True
                    
                    async def dynamic_callback(ctx):
                        await ctx.defer(ephemeral=False)
                        await ctx.send("Processing your request...", ephemeral=True)
                        guild_id_caller, author_id = str(ctx.guild.id), str(ctx.author.id)
                        idx = paginator.page_index
                        _, file_identifier = embeds[idx]
                        folder_path = self.uuids.get(file_identifier)
                        if folder_path:
                            title = ctx.message.embeds[0].title
                            print(f"Title: {title}")
                            media_type = "Movies" if title in get_movie_folders() else "TV Shows"
                            print(f"Media Type: {media_type}")
                            if media_type == "Movies":
                                movie_files = get_movie_files(movie_folder=title)
                                if movie_files:
                                    media_file = self.get_largest_media_file(title)
                                    if media_file:
                                        response = await self.client.post('play', {
                                            "title": media_file['title'],
                                            "path": media_file['path'],
                                            "type": media_type,
                                            "sorted_episodes": [] if media_type == "Movies" else sorted_episodes,
                                            "guild_id": guild_id_caller,
                                            "author": author_id
                                        })
                                        if response["status"] == 200:
                                            await ctx.send(content="Media file details sent successfully.", ephemeral=True)
                                        else:
                                            if response["message"] == "Already playing media":
                                                await ctx.send(content="Media is already playing. Please stop the current media before playing another one.", ephemeral=True)
                                            else:
                                                await ctx.send(content=f"Failed to send media file details. Error: {response['message']}", ephemeral=True)
                                    else:
                                        await ctx.send(content="No valid media files found in the closest matching movie folder.", ephemeral=True)
                                else:
                                    await ctx.send(content="No movie files found.", ephemeral=True)
                            elif media_type == "TV Shows":
                                sorted_episodes = sort_tv_show_episodes(get_tv_show_files_extra(show_folder=title))
                                sorted_episodes = truncate_sorted_episodes(sorted_episodes, "Season 10")
                                media_type = get_media_type(file_path=folder_path)
                                payload = {
                                    "title": title,
                                    "path": folder_path,
                                    "type": media_type if media_type == "Movies" else "TV Shows",
                                    "sorted_episodes": [] if media_type == "Movies" else sorted_episodes,
                                    "guild_id": guild_id_caller,
                                    "author": author_id
                                }
                                if season is not None and episode is not None:
                                    payload["season"] = season
                                    payload["episode"] = episode
                                response = await self.client.post('play', payload)
                                if response["status"] == 200:
                                    await ctx.send(content="Media file details sent successfully.", ephemeral=True)
                                else:
                                    await ctx.send(content="Failed to send media file details.", ephemeral=True)
                            else:
                                await ctx.send(content="No matching media folder found.", ephemeral=True)
                        else:
                            await ctx.send(content="Invalid file identifier.", ephemeral=True)
                            
                    paginator.callback = dynamic_callback
                    for i, (embed, _) in enumerate(embeds):
                        embed.set_footer(text=f"{i+1} of {len(embeds)} | Streamer App | By femboy maid unicorns uwu")
                    await paginator.send(ctx)
            else:
                await ctx.send(f"No media found matching the query: {title}")
        else:
            await ctx.send(f"No media found matching the query: {title}")
    
    @slash_command(
        name="list",
        description="List all available media files",
    )
    @slash_option(
        name="type",
        description="The type of media to list",
        required=True,
        choices=[
            SlashCommandChoice(name="Movies", value="Movies"),
            SlashCommandChoice(name="TV Shows", value="TV Shows")
        ],
        opt_type=OptionType.STRING
    )
    async def list(self, ctx, type: str):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        await ctx.defer()
        if type == "Movies":
            movie_folders = get_movie_folders()
            if movie_folders:
                embeds = []
                for folder in movie_folders:
                    movie_files = get_movie_files(movie_folder=folder)
                    if movie_files:
                        path = movie_files[folder][0]
                        imdb_id = re.search(r'imdbid-(tt\d+)', path)
                        if imdb_id:
                            imdb_id = imdb_id.group(1)
                            details_data = await self.mdblist.get_details("i", imdb_id)
                            details = await self.mdblist.extract_details(details=details_data, skip_dominant_colors=False, id=imdb_id)
                            if details and details.get("poster", ""):
                                extracted = {
                                    "poster": details.get("poster", ""),
                                    "score_average": details.get("score_average", 0),
                                    "type": details.get("type", ""),
                                    "description": details.get("description", ""),
                                    "runtime": details.get("runtime", 0),
                                    "title": details.get("title", ""),
                                    "year": details.get("year", 0),
                                    "released": details.get("released", ""),
                                    "most_dominant_colors": details.get("most_dominant_colors", [])
                                }
                                most_dominant_color = random.choice(extracted["most_dominant_colors"]) if extracted["most_dominant_colors"] else None
                                if most_dominant_color is not None:
                                    most_dominant_color = tuple(int(x) for x in most_dominant_color)
                                else:
                                    most_dominant_color = []
                            else:
                                await ctx.send(f"Failed to extract details? (Movies) (Details: {details}). Please send this to unicorns if you encounter this issue.", ephemeral=True)
                            print(f"Most Dominant Color: {most_dominant_color}")
                            embed = Embed(
                                title=extracted["title"] if extracted["title"] else "Unknown",
                                color=Color.from_rgb(*most_dominant_color) if most_dominant_color else Color.random(),
                                footer="Streamer App | By femboy maid unicorns uwu",
                                thumbnail=extracted["poster"],
                            )
                            embed.add_field(name="Type", value=extracted["type"], inline=True)
                            embed.add_field(name="Year", value=extracted["year"], inline=True)
                            embed.add_field(name="Released", value=extracted["released"], inline=True)
                            embed.add_field(name="Runtime", value=extracted["runtime"], inline=True)
                            embed.add_field(name="Score", value=f"{extracted['score_average'] / 10:.1f}/10", inline=True)
                            embed.add_field(name="Description", value=extracted["description"], inline=False)
                            embeds.append(embed)
                if embeds:
                    paginator = Paginator.create_from_embeds(self.bot, *embeds)
                    embeds = [embed.set_footer(text=f"{i+1} of {len(embeds)} | Streamer App | By femboy maid unicorns uwu") or embed for i, embed in enumerate(embeds)]
                    # TODO: Maybe add a callback button which sends the media file details to the user, with play buttons and etc
                    await paginator.send(ctx)
                else:
                    await ctx.send("No movies found.")
            else:
                await ctx.send("No movie folders found.")
        elif type == "TV Shows":
            tvshow_folders = get_tvshow_folders()
            if tvshow_folders:
                embeds = []
                tv_show_files = get_tv_show_files_extra_batch(show_folders=tvshow_folders)
                for folder in tv_show_files:
                    files = next((season_files for season in tv_show_files.get(folder, {}) for season_files in [tv_show_files[folder][season].values()]), None)
                    if files:
                        path = os.path.join(TV_PATH, folder, next(iter(tv_show_files[folder])), next(iter(files)))
                        imdb_id = re.search(r'imdbid-(tt\d+)', path)
                        if imdb_id:
                            imdb_id = imdb_id.group(1)
                            details_data = await self.mdblist.get_details("i", imdb_id)
                            details = await self.mdblist.extract_details(details=details_data, skip_dominant_colors=False, id=imdb_id)
                            if details and details.get("poster", ""):
                                extracted = {
                                    "poster": details.get("poster", ""),
                                    "score_average": details.get("score_average", 0),
                                    "type": details.get("type", ""),
                                    "description": details.get("description", ""),
                                    "runtime": details.get("runtime", 0),
                                    "title": details.get("title", ""),
                                    "year": details.get("year", 0),
                                    "released": details.get("released", ""),
                                    "most_dominant_colors": details.get("most_dominant_colors", [])
                                }
                                most_dominant_color = random.choice(extracted["most_dominant_colors"]) if extracted["most_dominant_colors"] else None
                                if most_dominant_color is not None:
                                    most_dominant_color = tuple(int(x) for x in most_dominant_color)
                                else:
                                    most_dominant_color = []
                            else:
                                await ctx.send(f"Failed to extract details? (TV Shows) (Details: {details}). Please send this to unicorns if you encounter this issue.", ephemeral=True)
                            print(f"Most Dominant Color: {most_dominant_color}")
                            embed = Embed(
                                title=extracted["title"] if extracted["title"] else "Unknown",
                                color=Color.from_rgb(*most_dominant_color) if most_dominant_color else Color.random(),
                                footer="Streamer App | By femboy maid unicorns uwu",
                                thumbnail=extracted["poster"],
                            )
                            embed.add_field(name="Type", value=extracted["type"], inline=True)
                            embed.add_field(name="Year", value=extracted["year"], inline=True)
                            embed.add_field(name="Released", value=extracted["released"], inline=True)
                            embed.add_field(name="Runtime", value=extracted["runtime"], inline=True)
                            embed.add_field(name="Score", value=f"{extracted['score_average'] / 10:.1f}/10", inline=True)
                            embed.add_field(name="Description", value=extracted["description"], inline=False)
                            embeds.append(embed)
                if embeds:
                    paginator = Paginator.create_from_embeds(self.bot, *embeds)
                    embeds = [embed.set_footer(text=f"{i+1} of {len(embeds)} | Streamer App | By femboy maid unicorns uwu") or embed for i, embed in enumerate(embeds)]
                    await paginator.send(ctx)
                else:
                    await ctx.send("No TV shows found.")
            else:
                await ctx.send("No TV show folders found.")
        else:
            await ctx.send("Invalid media type. Please choose between Movies and TV Shows.")

    @slash_command(name="play-scheduled", description="Play a movie or TV show for a specified duration")
    @slash_option(
        name="title",
        description="The title of the media to play",
        required=True,
        opt_type=OptionType.STRING
    )
    @slash_option(
        name="duration",
        description="The duration to play the media (e.g. 30s, 5m, 6h, 1d, 1w)",
        required=True,
        opt_type=OptionType.STRING
    )
    async def play_scheduled(self, ctx, title: str, duration: str):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        duration_seconds = self.parse_duration(duration)
        if duration_seconds is None:
            await ctx.send("Invalid duration format. Please use a format like 30s, 5m, 6h, 1d, or 1w.")
            return
        await ctx.defer(ephemeral=True)
        movie_folders = get_movie_folders()
        matched_folders = [folder for folder in movie_folders if title.lower().replace('.', '') in folder.lower().replace('.', '')]
        print(f"Matched folders: {matched_folders}")
        if matched_folders:
            embeds = []
            for folder in matched_folders:
                files = get_movie_files(movie_folder=folder)
                if folder in files and files[folder]:
                    path = files[folder][0]
                    if not path:
                        await ctx.send(f"Invalid path: {path} (Folder: {folder}. **Please screenshot and send to unicorns!**)", ephemeral=True)
                        continue
                    imdb_id = re.search(r'imdbid-(tt\d+)', path)
                    if not imdb_id:
                        await ctx.send(f"Failed to extract IMDb ID from path: {path}. Please send this to unicorns if you encounter this issue.", ephemeral=True)
                        continue
                    imdb_id = imdb_id.group(1)
                    details_data = await self.mdblist.get_details("i", imdb_id)
                    details = await self.mdblist.extract_details(details=details_data, skip_dominant_colors=False, id=imdb_id)
                    if details and details.get("poster", ""):
                        extracted = {
                            "poster": details.get("poster", ""),
                            "score_average": details.get("score_average", 0),
                            "type": details.get("type", ""),
                            "description": details.get("description", ""),
                            "runtime": details.get("runtime", 0),
                            "title": details.get("title", ""),
                            "year": details.get("year", 0),
                            "released": details.get("released", ""),
                            "most_dominant_colors": details.get("most_dominant_colors", [])
                        }
                        most_dominant_color = random.choice(extracted["most_dominant_colors"]) if extracted["most_dominant_colors"] else None
                        if most_dominant_color is not None:
                            most_dominant_color = tuple(int(x) for x in most_dominant_color)
                        else:
                            most_dominant_color = []
                    else:
                        await ctx.send(f"Failed to extract details? (Search) (Details: {details}). Please send this to unicorns if you encounter this issue.", ephemeral=True)
                    # TODO: Add an alternate way to get title from path
                    embed = Embed(
                        title=extracted["title"] if extracted["title"] else "Unknown",
                        color=Color.from_rgb(*most_dominant_color) if most_dominant_color else Color.random(),
                        footer="Streamer app | By femboy maid unicorns uwu",
                        thumbnail=extracted["poster"],
                    )
                    embed.add_field(name="Type", value=extracted["type"], inline=True)
                    embed.add_field(name="Year", value=extracted["year"], inline=True)
                    embed.add_field(name="Released", value=extracted["released"], inline=True)
                    embed.add_field(name="Runtime", value=extracted["runtime"], inline=True)
                    embed.add_field(name="Score", value=f"{extracted['score_average'] / 10:.1f}/10", inline=True)
                    embed.add_field(name="Description", value=extracted["description"], inline=False)
                    file_identifier = str(uuid.uuid4())
                    self.uuids[file_identifier] = path
                    embeds.append((embed, file_identifier))
            if embeds:
                if len(embeds) == 1:
                    embed, file_identifier = embeds[0]
                    play_button = Button(
                        style=ButtonStyle.PRIMARY,
                        label="Play",
                        custom_id=f"play_media_{file_identifier}"
                    )
                    info_button = Button(
                        style=ButtonStyle.SECONDARY,
                        label="Info",
                        custom_id=f"info_media_{file_identifier}"
                    )
                    imdb_button = Button(
                        style=ButtonStyle.LINK,
                        label="IMDb",
                        url=f"https://www.imdb.com/title/{imdb_id}"
                    )
                    await ctx.send(embed=embed, components=[play_button, info_button, imdb_button])
                else:
                    paginator = Paginator.create_from_embeds(self.bot, *[embed for embed, _ in embeds])
                    paginator.show_callback_button = True
                    
                    async def dynamic_callback(ctx):
                        await ctx.defer(ephemeral=True)
                        guild_id_caller, author_id = str(ctx.guild.id), str(ctx.author.id)
                        idx = paginator.page_index
                        print(f"Index: {idx}")
                        _, file_identifier = embeds[idx]
                        folder_path = self.uuids.get(file_identifier)
                        if folder_path:
                            title, year = ctx.message.embeds[0].title, ctx.message.embeds[0].fields[1].value
                            media_type = "Movies"
                            media_file = self.get_largest_media_file(f"{title} ({year})")
                            if not media_file:
                                await ctx.send(content="No valid media files found in the closest matching movie folder.", ephemeral=True)
                                return
                            movie_duration = get_video_length(media_file['path'])
                            print(f"Title: {title}, Year: {year}, Combined: {title} ({year}), Duration: {movie_duration}")
                            payload = {
                                "title": media_file['title'],
                                "path": media_file['path'],
                                "type": media_type,
                                "sorted_episodes": [],
                                "guild_id": guild_id_caller,
                                "author": author_id,
                                "duration": duration_seconds,
                                "movie_duration": movie_duration
                            }
                            response = await self.client.post('play-scheduled', payload)
                            if response["status"] == 200:
                                await ctx.send(content=f"Media file details sent successfully. ||{response}||", ephemeral=True)
                            else:
                                if "message" in response:
                                    if response["message"] == "Already playing media":
                                        await ctx.send(content="Media is already playing. Please stop the current media before playing another one.", ephemeral=True)
                                    else:
                                        await ctx.send(content=f"Failed to send media file details. Error: {response['message']}", ephemeral=True)
                                else:
                                    await ctx.send(content=f"Failed to send media file details. Status code: {response['message']}", ephemeral=True)
                        else:
                            await ctx.send(content="No valid media files found in the closest matching movie folder.", ephemeral=True)
                    paginator.callback = dynamic_callback
                    for i, (embed, _) in enumerate(embeds):
                        embed.set_footer(text=f"{i+1} of {len(embeds)} | Streamer App | By femboy maid unicorns uwu")
                    await paginator.send(ctx)
            else:
                await ctx.send(f"No media found matching the query: {title}")
        else:
            await ctx.send(f"No media found matching the query: {title}")
    
    @slash_command(name="timeleft-schedule", description="Check the remaining time left for the scheduled media")
    async def timeleft_schedule(self, ctx):
        if not self.whitelist_db.is_whitelisted(ctx.author.id):   
            await ctx.send("You are not whitelisted to use this command.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        response = await self.client.get('timeleft')
        if response["status"] == 500:
            await ctx.send("No media is currently scheduled to play.", ephemeral=True)
        elif response["status"] == 400:
            embed = Embed(
                title="Time Left",
                description="No current stream active.",
                color=Color.random(),
                footer="Streamer App | By femboy maid unicorns uwu"
            )
            await ctx.send(embed=embed, ephemeral=True)
        else:
            time_left = response['data']['message']
            try:
                time_left = time_left.split(' ')[-1]
                time_left = float(time_left)
            except ValueError:
                await ctx.send(f"Failed to parse time left. ||{response}||", ephemeral=True)
                return
            time_left = self.convert_time(time_left)
            embed = Embed(
                title="Time Left",
                description=f"{time_left}",
                color=Color.random(),
                footer="Streamer App | By femboy maid unicorns uwu"
            )
            await ctx.send(embed=embed, ephemeral=True)
    
    def convert_time(self, time_left):
        time_left = int(time_left)
        days = time_left // 86400
        hours = (time_left % 86400) // 3600
        minutes = (time_left % 3600) // 60
        seconds = time_left % 60
        if days > 0: return f"{days} days, {hours} hours, {minutes} minutes, and {seconds} seconds"
        elif hours > 0: return f"{hours} hours, {minutes} minutes, and {seconds} seconds"
        elif minutes > 0: return f"{minutes} minutes and {seconds} seconds"
        else: return f"{seconds} seconds"
    
    def parse_duration(self, duration: str) -> int:
        match = re.match(fr"(\d+)([smhdw])", duration)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            if unit == "s":
                return value
            elif unit == "m":
                return value * 60
            elif unit == "h":
                return value * 3600
            elif unit == "d":
                return value * 86400
            elif unit == "w":
                return value * 604800
            else:
                return value # Default to seconds
        else:
            return None # Invalid duration format

    def get_largest_media_file(self, folder: str) -> dict:
        movie_files = get_movie_files(movie_folder=folder)
        print(f"Movie Files: {movie_files}, Folder: {folder}")
        if not movie_files:
            return None
        for key in movie_files:
            if folder in key:
                largest_file = None
                max_size = 0
                for file_path in movie_files[key]:
                    file_size = os.path.getsize(file_path)
                    if file_size > max_size:
                        max_size = file_size
                        largest_file = file_path
                if largest_file:
                    return {"title": os.path.basename(largest_file), "path": largest_file}
        return None