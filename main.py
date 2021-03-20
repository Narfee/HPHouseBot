import discord
from discord.ext import commands, tasks
from discord.ext.commands import MemberConverter
import os
from webserver import keep_alive
from aiohttp import ClientSession
import json
from datetime import datetime

# EDITABLE VALUES:
ACTIVE_POINTS_CHANNEL = 822645070737047612
TOTAL_POINTS_CHANNEL = 822645768463712277
LOG_CHANNEL = 822645656883560459


# Colors of each house, sends in the embed
HOUSE_COLORS = {"gryffindor": 0xae0001, "hufflepuff": 0xffed86,
                "slytherin": 0x2a623d, "ravenclaw": 0x222f5b}
# Determines the amount of messages to be sent before you get points
MESSAGES_UNTIL_EMBED = 50
# Determines the amount of points you get after reaching the message limit
POINTS_FOR_MESSAGES = 5
# Bot prefix
PREFIX = "!!"

# only edit these if id of roles has changed
HOUSES = {"gryffindor", "hufflepuff", "slytherin", "ravenclaw"}
HOUSE_MAP = {821780382444945428: "gryffindor", 821780383053643815: "slytherin",
             821780381673717800: "hufflepuff", 821780380809822208: "ravenclaw"}


# initates bot and sets prefix
client = commands.Bot(command_prefix=PREFIX, case_insensitive=True)
# removes the default help command so I can add my own
client.remove_command('help')


def house_point_keepers():
    """returns the discord id's of people with permissions to give points """
    with open("house_point_keepers.json", "r") as f:
        return json.load(f)


def find_house(member: discord.Member):
    """Finds the house of a discord member. Returns a house in the form of a string"""
    user_roles = [role.id for role in member.roles]
    for house in HOUSE_MAP.keys():
        if house in user_roles:
            return HOUSE_MAP[house]

    return False  # returns false if user not in a house


def get_house_points(house: str) -> int:
    """Gets the total points of a house"""
    with open("house_points.json", "r") as file:
        member_dict = json.load(file)
        total = 0
        for member in member_dict[house].keys():
            total += member_dict[house][member]["points"]
        return total


def get_members():
    """Returns a list of all the members that have been cached"""
    with open("house_points.json", "r") as file:
        member_dict = json.load(file)
        members = []
        for house in member_dict.keys():  # for every house
            # generates a list of members of the house and adds it
            members += list(member_dict[house].keys())
        return members


async def point_logger():
    """Logs house_points.json to mystbin"""
    with open("house_points.json", "r") as f:
        dict = json.load(f)
        async with ClientSession() as s:
            url_key = await s.post("https://mystb.in/documents", data=json.dumps(dict, indent=6))
            url_key = await url_key.json()  # posts the dict to mystbin

    # generated embed with datetime and url
    log_embed = discord.Embed(
        title=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        url=f"https://mystb.in/{url_key['key']}.json",
        colour=0x2ee863)

    # sends embed
    log_channel = client.get_channel(LOG_CHANNEL)
    await log_channel.send(embed=log_embed)


async def total_tracker():
    """Tracks the total number of points per house and displays it in a channel"""
    total_channel = client.get_channel(TOTAL_POINTS_CHANNEL)
    total_embed = discord.Embed(
        title="__**Points for each house**__",   colour=0x2ee863)

    with open("house_points.json", "r") as f:
        member_dict = json.load(f)
        for house in HOUSES:
            total = 0
            for member in member_dict[house].keys():
                total += member_dict[house][member]["points"]
            total_embed.add_field(
                name=f"**{house.title()}**", value=f"{total} points")

    hogwarts_img = discord.File(
        "house_crests/hogwarts.png", filename="hogwarts.png")
    total_embed.set_thumbnail(url=f"attachment://hogwarts.png")

    await total_channel.purge(limit=100)
    await total_channel.send(embed=total_embed, file=hogwarts_img)


async def point_embed_maker(channel, house, point_amount, action, user, reason):
    embed = discord.Embed(
        title=f"__**{house.title()} House Points**__",
        colour=HOUSE_COLORS[house]
    )

    embed.add_field(name=f"**{action.title()} Points**",
                    value=f"{point_amount} points have been {action}")
    embed.add_field(name="**Reason**", value=f"{reason}")
    embed.add_field(
        name=f"**Total Points for {house.title()}**", value=f"{get_house_points(house)}")
    img_file = discord.File(
        f"house_crests/{house}.png", filename=f"{house}.png")
    embed.set_thumbnail(url=f"attachment://{house}.png")
    await channel.send(file=img_file, embed=embed)
    await total_tracker()


@tasks.loop(hours=3.0)
async def log_file():
    await point_logger()


@client.event
async def on_ready():
    print("House Bot is ready")
    await client.change_presence(activity=discord.Game(name='Quidditch'))
    log_file.start()


@client.group(case_insensitive=True, invoke_without_command=True, aliases=["perm"])
async def perms():
    """"Command group for dealing with permissions"""


@perms.command()
@commands.is_owner()
async def give(ctx, user: discord.Member):
    with open("house_point_keepers.json", "r+") as f:
        perms_list = json.load(f)
        if user.id in perms_list:
            await ctx.send(embed=discord.Embed(title=f"{user.name} already has permissions to add points."))
        else:
            perms_list.append(user.id)
            f.seek(0)  # moves cursor to beginning of file
            f.truncate(0)  # deletes file contents
            json.dump(perms_list, f)  # loads the new dict into the file
            await ctx.send(embed=discord.Embed(title=f"Gave {user.name} permissions to manage points."))


@perms.command()
@commands.is_owner()
async def remove(ctx, user: discord.Member):
    with open("house_point_keepers.json", "r+") as f:
        perms_list = json.load(f)
        if user.id not in perms_list:
            await ctx.send(embed=discord.Embed(title=f"{user.name} doesn't already have permissions to add points."))
        else:
            perms_list.remove(user.id)
            f.seek(0)  # moves cursor to beginning of file
            f.truncate(0)  # deletes file contents
            json.dump(perms_list, f)  # loads the new dict into the file
            await ctx.send(embed=discord.Embed(title=f"Removed {user.name}'s permissions to manage points."))


@client.command()
async def help(ctx):
    embed = discord.Embed(
        title="Command Help!",
        description="""
    __**House Point Tracking:**__
      -**!!points show [house]**
        -shows the points of a certain house or user
        -can be done by anyone
        -ex: !!points show ravenclaw

      -**!!points add [user] [points] [reason]**
        -adds house points for a certain user
        -points are automatically added every 
         50 messages sent by a user
        -command can only be run by authorized 
         individuals
        -ex: !!points add @Albus 10 for 
         helping out a member

      -**!!points remove [user] [points] [reason]**
        -removes house points for a certain user
        -command can only be run by authorized 
         individuals
        -ex: !!points remove @Albus 10 for being
         mean to a member
      
    __**Permission Management**__
        -**!!perms give [user]**
          -gives house point management perms 
           to a user
          -can only be done by Albus
          -ex: !!perms give @HarryPotter

        -**!!perms remove [user]**
          -removes house point management perms 
           from a user
          -can only be done by Albus
          -ex: !!perms remove @HarryPotter
    """,
        colour=0x2ee863
    )
    await ctx.send(embed=embed)


@client.group(case_insensitive=True, invoke_without_command=True, aliases=["c", "purge"])
async def clear():
    """"General command group for clearing messages and channels"""


@clear.command()
@commands.is_owner()
async def messages(ctx, amount: int):
    await ctx.channel.purge(limit=amount+1)  # clears the channel


@clear.command()
@commands.is_owner()
async def channel(ctx, channel, amount: int = 1):
    if channel == "total":
        await total_tracker()  # clears channel and refreshes it
    elif channel == "points":  # simply clears channel
        c = client.get_channel(ACTIVE_POINTS_CHANNEL)
        await c.purge(limit=amount+1)


@client.group(case_insensitive=True, invoke_without_command=True, aliases=["point"])
async def points():
    """Main command group that deals with house points"""


@points.command(aliases=["s"])
async def show(ctx, *, house):
    """Shows the points of a user"""

    if house.lower() in HOUSES:  # if the house isn't a discord user
        house = house.lower()

        embed = discord.Embed(
            title=f"__{house.title()}'s Points:__",
            description=f"{house.title()} has {get_house_points(house)} points!",
            colour=HOUSE_COLORS[house])  # generates embed

        # adds the images to the embed with local files not links, so this is necessary
        img_file = discord.File(
            f"house_crests/{house}.png", filename=f"{house}.png")
        embed.set_thumbnail(url=f"attachment://{house}.png")
        await ctx.send(file=img_file, embed=embed)

    else:  # if the house is instead a discord user

        try:  # attempts to create a discord.Member object

            member = await MemberConverter().convert(ctx, house)
            with open("house_points.json", "r") as f:
                member_dict = json.load(f)

            house = find_house(member)  # get's the user's hosue

            embed = discord.Embed(
                title=f"__{member.name}'s Points__",
                description=f"{member.name} has contributed {member_dict[house][str(member.id)]['points']} points for {house.title()}!\n\n{member.name} is {MESSAGES_UNTIL_EMBED-member_dict[house][str(member.id)]['msgs']} messages away from getting {house.title()} {POINTS_FOR_MESSAGES} more points!",
                colour=0x2ee863)  # generates embed

            # adds image of user and sends embed
            embed.set_thumbnail(
                url=str(member.avatar_url).replace("webp", "png"))
            await ctx.send(embed=embed)

        except discord.ext.commands.errors.BadArgument:  # if the user ended up putting an invalid member
            await ctx.send(embed=discord.Embed(title="Uh oh! Make sure the house or user is valid!"))


@points.command(aliases=["a", "add", "give"])
async def _add(ctx, user: discord.Member, points: int, *, reason):
    """Adds points to a certain user"""

    if ctx.author.id in house_point_keepers():  # if the user is authorized to manage points

        if points in range(1, 1000):
            with open("house_points.json", "r+") as file:
                member_dict = json.load(file)
                house = find_house(user)  # finds the user's house
                if house:  # if they have a house
                    # adds the points to the dict
                    member_dict[house][str(user.id)]["points"] += int(points)
                else:
                    await ctx.send(embed=discord.Embed(title="Uh oh! User doesn't have a house!"))

                file.seek(0)  # moves cursor to beginning of file
                file.truncate(0)  # deletes file contents
                # loads the new dict into the file
                json.dump(member_dict, file, indent=6)

            # sends embed with info
            await point_embed_maker(ctx.channel, house, points, "Awarded", user, reason)

        else:  # if the points added weren't within a valid range
            await ctx.send(embed=discord.Embed(title="Uh oh! Points can't be less than 1 or greater than 1000"))

    else:  # if the user isn't authorized to manage permissions
        await ctx.send(embed=discord.Embed(title="You don't have permission to manage points! Contact Albus if you think this is an error."))


@points.command(aliases=["rem", "r", "remove", "sub", "subtract"])
async def _sub(ctx, user: discord.Member, points: int, *, reason):
    """Removes points from a user"""

    if ctx.author.id in house_point_keepers():  # if the user is authorized to manage points

        if points in range(1, 1000):
            with open("house_points.json", "r+") as file:
                member_dict = json.load(file)
                house = find_house(user)  # checks for the user's house
                if house:  # if the user has a house
                    # removes points
                    member_dict[house][str(user.id)]["points"] -= int(points)

                    # sends an embed if the points
                    if member_dict[house][str(user.id)]["points"] < 0:
                        member_dict[house][str(user.id)]["points"] = 0
                        await ctx.send(embed=discord.Embed(title="Oops, it seems like this user's points would have gone below 0. A user's points can't go below 0, but the current points have still been removed."))
                else:
                    await ctx.send(embed=discord.Embed(title="Uh oh! User doesn't have a house!"))

                file.seek(0)  # moves cursor to beginning of file
                file.truncate(0)  # deletes file contents
                # loads the new dict into the file
                json.dump(member_dict, file, indent=6)

            # sends embed with info
            await point_embed_maker(ctx.channel, house, points, "Removed", user, reason)

        else:  # if the points added weren't within a valid range
            await ctx.send(embed=discord.Embed(title="Uh oh! You can't remove less than 1 point or greater than 999 points"))

    else:  # if user doesn't have perms to manage points
        await ctx.send(embed=discord.Embed(title="You don't have permission to manage points! Contact Albus if you think this is an error."))


@client.event
async def on_message(message):

    if not message.author.bot:  # if the user isn't a bot

        if str(message.author.id) in get_members():  # if the member has been cached
            # checks to see if they have a house
            house = find_house(message.author)

            if house:  # if they have a house
                with open("house_points.json", "r+") as file:
                    member_dict = json.load(file)  # loads dict

                    try:  # attempts to increase message count by 1
                        # increases message count by 1
                        member_dict[house][str(message.author.id)]["msgs"] += 1
                    except KeyError:  # this happens if the member switches houses

                        for every_house in HOUSES:
                            try:  # tries deleting info from every house they are in
                                del member_dict[every_house][str(
                                    message.author.id)]
                            except:
                                pass
                        # gives them an empty cache in the new house
                        member_dict[house][str(message.author.id)] = {
                            "points": 0, "msgs": 1}

                    # if the member has sent enough messages
                    if member_dict[house][str(message.author.id)]["msgs"] >= MESSAGES_UNTIL_EMBED:
                        # gives points
                        member_dict[house][str(
                            message.author.id)]["points"] += POINTS_FOR_MESSAGES
                        # resets the messages sent count
                        member_dict[house][str(message.author.id)]["msgs"] = 0

                        file.seek(0)  # moves cursor to beginning of file
                        file.truncate(0)  # deletes file contents
                        # loads the new dict into the file
                        json.dump(member_dict, file, indent=6)
                        file.close()  # closes the file so it doesn't interfere with total_tracker

                        await total_tracker()  # tracks the house total points

                        # gets the right channel and sends embed with info
                        channel = client.get_channel(ACTIVE_POINTS_CHANNEL)
                        await point_embed_maker(channel, house, 5, "awarded", message.author.name, "for being active and sending 50 messages!")
                        # sends ping
                        await channel.send(f"<@{message.author.id}> ^")

                    else:  # if the member has not sent enough mesages, closes the file
                        file.seek(0)  # moves cursor to beginning of file
                        file.truncate(0)  # deletes file contents
                        # loads the new dict into
                        json.dump(member_dict, file, indent=6)
                        file.close()

        else:  # member has never been cached
            # checks to see if they have a house
            house = find_house(message.author)
            if house:  # if they have a house
                with open("house_points.json", "r+") as file:
                    member_dict = json.load(file)
                    member_dict[house][str(message.author.id)] = {
                        "points": 0, "msgs": 1}  # creates new member cache
                    file.seek(0)  # moves cursor to beginning of file
                    file.truncate(0)  # deletes file contents
                    # loads the new dict into the file
                    json.dump(member_dict, file, indent=6)

    # necessary so that the commands module doesn't stop working
    await client.process_commands(message)


keep_alive() # keeps the bot alive using flask and uptime-robot
TOKEN = os.environ.get("TOKEN") # get's bot token from hidden .env file
client.run(TOKEN) # runs bot
