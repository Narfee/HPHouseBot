import discord
from discord.ext import commands
from discord.ext.commands import MemberConverter
import os
from webserver import keep_alive
from aiohttp import ClientSession
import json
from datetime import datetime

client = commands.Bot(command_prefix="!!")
client.remove_command('help')

HOUSES = {"gryffindor", "hufflepuff", "slytherin", "ravenclaw"}
HOUSE_MAP = {740132911197585408 : "gryffindor", 740132911843377203: "slytherin", 740132912720117801 : "hufflepuff", 740132912338305035 : "ravenclaw"}
HOUSE_COLORS = {"gryffindor" : 0xae0001, "hufflepuff" : 0xffed86,"slytherin" : 0x2a623d,"ravenclaw" : 0x222f5b }
MESSAGES_UNTIL_EMBED = 50
POINTS_FOR_MESSAGES = 5

def house_point_keepers(): 
  with open("house_point_keepers.json" , "r") as f: 
    return json.load(f)

def find_house(member : discord.Member): 
  user_roles = [role.id for role in member.roles]
  for house in HOUSE_MAP.keys(): 
    if house in user_roles: 
      return HOUSE_MAP[house]
  return False

def get_house_points(house : str): 
  with open("house_points.json" , "r") as file: 
    member_dict = json.load(file)
    total = 0
    for member in member_dict[house].keys():
      total += member_dict[house][member]["points"]
    return total

def get_members():
  with open("house_points.json" , "r") as file: 
    member_dict = json.load(file)
    members = []
    for house in member_dict.keys(): 
      members += list(member_dict[house].keys())

    return members

async def point_logger():
  with open("house_points.json" , "r") as f: 
    dict = json.load(f)
    async with ClientSession() as s:
      url_key = await s.post("https://mystb.in/documents", data = json.dumps(dict, indent=6))
      url_key = await url_key.json()
    

  point_channel = client.get_channel(741447867088109718)
  total_channel = client.get_channel(741444986620477480)

  log_embed = discord.Embed(
    title = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    url = f"https://mystb.in/{url_key['key']}.json", 
    colour =  0x2ee863)
  
  total_embed = discord.Embed(title = "__**Points for each house**__",   colour =  0x2ee863)

  
  with open("house_points.json" , "r") as f:
    member_dict = json.load(f) 
    for house in HOUSES: 
      total = 0
      for member in member_dict[house].keys():
        total += member_dict[house][member]["points"]
      total_embed.add_field(name=f"**{house.title()}**", value = f"{total} points")

  hogwarts_img = discord.File("house_crests/hogwarts.png", filename="hogwarts.png")
  total_embed.set_thumbnail(url=f"attachment://hogwarts.png")

  await total_channel.purge(limit=100)
  await total_channel.send(embed=total_embed, file=hogwarts_img)
  
  await point_channel.send(embed=log_embed)



async def point_embed_maker(channel, house, point_amount, action, user, reason): 
  embed = discord.Embed(
  title = f"__{house.title()} House Points__", 
  colour = HOUSE_COLORS[house]
  )

  embed.add_field(name=f"{action.title()} Points", value=f"{point_amount} points have been {action}")
  embed.add_field(name = "Reason", value = f"{reason}")
  embed.add_field(name= f"Total Points for {house.title()}", value= f"{get_house_points(house)}")
  img_file = discord.File(f"house_crests/{house}.png", filename=f"{house}.png")
  embed.set_thumbnail(url=f"attachment://{house}.png")
  await channel.send(file=img_file, embed=embed)
  await point_logger()
  
@client.event
async def on_ready():
  print("House Bot is ready")
  await client.change_presence(activity=discord.Game(name='Quidditch'))


@client.group(case_insensitive=True, invoke_without_command=True)
async def perms(): 
  """"Command group for dealing with permissions"""

@perms.command()
@commands.is_owner()
async def give(ctx, user: discord.Member): 
  with open("house_point_keepers.json" , "r+") as f: 
    perms_list = json.load(f)
    if user.id in perms_list:
      await ctx.send(embed= discord.Embed(title=f"{user.name} already has permissions to add points."))
    else: 
      perms_list.append(user.id)
      f.seek(0) # moves cursor to beginning of file
      f.truncate(0) # deletes file contents 
      json.dump(perms_list, f) # loads the new dict into the file
      await ctx.send(embed= discord.Embed(title=f"Gave {user.name} permissions to manage points."))

@perms.command()
@commands.is_owner()
async def remove(ctx, user: discord.Member): 
  with open("house_point_keepers.json" , "r+") as f: 
    perms_list = json.load(f)
    if user.id not in perms_list:
      await ctx.send(embed= discord.Embed(title=f"{user.name} doesn't already have permissions to add points."))
    else: 
      perms_list.remove(user.id)
      f.seek(0) # moves cursor to beginning of file
      f.truncate(0) # deletes file contents 
      json.dump(perms_list, f) # loads the new dict into the file
      await ctx.send(embed= discord.Embed(title=f"Removed {user.name}'s permissions to manage points."))


@client.command()
async def help(ctx): 
  embed = discord.Embed(
    title = "Command Help!", 
    description = 
    """
    __**House Point Tracking:**__
      -**!points show [house]**
        -shows the points of a certain house or user
        -can be done by anyone
        -ex: !points show ravenclaw

      -**!points add [user] [points] [reason]**
        -adds house points for a certain user
        -points are automatically added every 50 messages sent by a user
        -command can only be run by authorized individuals
        -ex: !points add @Albus 10 for helping out a member

      -**!points remove [user] [points] [reason]**
        -removes house points for a certain user
        -command can only be run by authorized individuals
        -ex: !points remove @Albus 10 for being mean to a member
      
    __**Permission Management**__
        -**!perms give [user]**
          -gives house point management perms to a user
          -can only be done by Albus
          -ex: !perms give @HarryPotter

        -**!perms remove [user]**
          -removes house point management perms from a user
          -can only be done by Albus
          -ex: !perms remove @HarryPotter
    """, 
    colour = 0x2ee863
  )
  await ctx.send(embed=embed)

@client.group(case_insensitive=True, invoke_without_command=True)
async def points():
  """Main command group that deals with house points"""

@points.command(aliases = ["s"])
async def show(ctx, house): 
  if house.lower() in HOUSES: 
    house = house.lower()
    embed = discord.Embed(title=f"{house.title()}'s Points!", description = f"{house.title()} has {get_house_points(house)} points!", colour = HOUSE_COLORS[house])
    img_file = discord.File(f"house_crests/{house}.png", filename=f"{house}.png")
    embed.set_thumbnail(url=f"attachment://{house}.png")
    await ctx.send(file=img_file, embed = embed)
  else: 
    member = await MemberConverter().convert(ctx, house)
    if isinstance(member, discord.Member):
      with open("house_points.json" , "r") as f: 
        member_dict = json.load(f)
      house = find_house(member)
      embed = discord.Embed(
        title= f"__{member.name}'s Points__", 
        description = f"Narfee has contributed {member_dict[house][str(member.id)]['points']} points for {house.title()}!", 
        colour = 0x2ee863) 
      embed.set_thumbnail(url=str(member.avatar_url).replace("webp", "png"))
      await ctx.send(embed=embed)
    else:
      await ctx.send(embed= discord.Embed(title="Uh oh! Make sure the house or user is valid!"))

@points.command(aliases = ["a", "add"])
async def _add(ctx, user : discord.Member, points: int, *, reason): 
  if ctx.author.id in house_point_keepers(): 
    if points > 0 and points < 1000: 
      with open("house_points.json" , "r+") as file: 
        member_dict = json.load(file)
        house = find_house(user)
        if house: 
          member_dict[house][str(user.id)]["points"] += int(points)

        file.seek(0) # moves cursor to beginning of file
        file.truncate(0) # deletes file contents 
        json.dump(member_dict, file, indent=6) # loads the new dict into the file 

      await point_embed_maker(ctx.channel, house, points, "Awarded", user, reason)
    else: 
      await ctx.send(embed= discord.Embed(title="Uh oh! Points can't be less than 1 or greater than 1000"))
  else: 
    await ctx.send(embed= discord.Embed(title="You don't have permission to manage points! Contact Albus if you think this is an error."))


@points.command(aliases = ["rem", "r", "remove", "sub", "subtract"])
async def _sub(ctx, user : discord.Member, points: int, *, reason):
  if ctx.author.id in house_point_keepers(): 
    
    if points > 0 and points < 1000: 
      with open("house_points.json" , "r+") as file: 
        member_dict = json.load(file)
        house = find_house(user)
        if house: 
          member_dict[house][str(user.id)]["points"] -= int(points)
          if member_dict[house][str(user.id)]["points"] < 0:
            member_dict[house][str(user.id)]["points"] = 0
            await ctx.send(embed= discord.Embed(title="User points can't go below 0"))
          
        file.seek(0) # moves cursor to beginning of file
        file.truncate(0) # deletes file contents 
        json.dump(member_dict, file, indent=6) # loads the new dict into the file 
      await point_embed_maker(ctx.channel, house, points, "Removed", user, reason)
    else: 
      await ctx.send(embed= discord.Embed(title="Uh oh! You can't remove less than 1 point or greater than 999 points"))
  else: 
    await ctx.send(embed= discord.Embed(title="You don't have permission to manage points! Contact Albus if you think this is an error."))

@client.event
async def on_message(message):  

  if not message.author.bot:

    if str(message.author.id) in get_members(): # if the member has been cached
      house = find_house(message.author) # checks to see if they have a house 
      if house: # if they have a house
        with open("house_points.json" , "r+") as file: 
          member_dict = json.load(file) # loads dict
          try:
            member_dict[house][str(message.author.id)]["msgs"] += 1 # increases message count by 1
          except KeyError: 
            # if the member switches houses
            for every_house in HOUSE_MAP.values(): 
              try:
                del member_dict[every_house][str(message.author.id)]
              except: 
                pass
            member_dict[house][str(message.author.id)] = {"points": 0, "msgs" : 1}

          # if the member has sent enough messages 
          if member_dict[house][str(message.author.id)]["msgs"] >= MESSAGES_UNTIL_EMBED: 

            channel = client.get_channel(741445244838477874)
            
            await point_embed_maker(channel, house, 5, "awarded", message.author.name, "for being active and sending 50 messages!")
            await channel.send(f"<@{message.author.id}> ^") 

            member_dict[house][str(message.author.id)]["points"] += POINTS_FOR_MESSAGES # gives points 
            member_dict[house][str(message.author.id)]["msgs"] = 0 # resets count

          file.seek(0) # moves cursor to beginning of file
          file.truncate(0) # deletes file contents 
          json.dump(member_dict, file, indent=6) # loads the new dict into the file 

    else: # member has never been cached
      house = find_house(message.author) # checks to see if they have a house 
      if house: # if they have a house
        with open("house_points.json" , "r+") as file: 
          member_dict = json.load(file)
          member_dict[house][str(message.author.id)] = {"points": 0, "msgs" : 1} # creates new member cache
          file.seek(0) # moves cursor to beginning of file
          file.truncate(0) # deletes file contents 
          json.dump(member_dict, file, indent=6) # loads the new dict into the file 

  await client.process_commands(message)


keep_alive()
TOKEN = os.environ.get("TOKEN")
client.run(TOKEN)
