import discord
from discord.ext import commands
import asyncio
from datetime import datetime
from urllib.request import urlopen as uReq, Request
from bs4 import BeautifulSoup as soup
import sqlite3
import os
from dotenv import load_dotenv
import requests, json
import math

# ------------------------------------------------
# CONFIGS
# ------------------------------------------------

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
defaultChannel = int(os.getenv("DEFAULT_CHANNEL")) # current-interest
ACTIVITY_STATUS = os.getenv("ACTIVITY_STATUS")
ACTIVITY_TYPE = os.getenv("ACTIVITY_TYPE")
ACTIVITY_TEXT = os.getenv("ACTIVITY_TEXT")
# DATABASE_HOST = os.getenv("DATABASE_HOST")
# DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
# DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
# DATABASE_DBNAME = os.getenv("DATABASE_DBNAME")

print("[" + datetime.now().strftime(r"%I:%M:%S %p") + "] " + "[1/3] Assigning SCV for launch...")
print("[" + datetime.now().strftime(r"%I:%M:%S %p") + "] " + "Loaded configs:")
print("[" + datetime.now().strftime(r"%I:%M:%S %p") + "] " + "Activity status: " + ACTIVITY_STATUS)
print("[" + datetime.now().strftime(r"%I:%M:%S %p") + "] " + "Activity type: " + ACTIVITY_TYPE)
print("[" + datetime.now().strftime(r"%I:%M:%S %p") + "] " + "Activity text: " + ACTIVITY_TEXT)
print("[" + datetime.now().strftime(r"%I:%M:%S %p") + "] " + "Channel: " + str(defaultChannel))

# ------------------------------------------------
# INITIALIZATION
# ------------------------------------------------

clientStatus = ""
if ACTIVITY_STATUS == "online":
	clientStatus = discord.Status.online
elif ACTIVITY_STATUS == "offline":
	clientStatus = discord.Status.offline
elif ACTIVITY_STATUS == "idle":
	clientStatus = discord.Status.idle
elif ACTIVITY_STATUS == "busy":
	clientStatus = discord.Status.dnd
else:
	clientStatus = discord.Status.online

clientActivityType = ""
if ACTIVITY_TYPE == "playing":
	clientActivityType = discord.ActivityType.playing
elif ACTIVITY_TYPE == "streaming":
	clientActivityType = discord.ActivityType.streaming
elif ACTIVITY_TYPE == "listening":
	clientActivityType = discord.ActivityType.listening
elif ACTIVITY_TYPE == "watching":
	clientActivityType = discord.ActivityType.watching
elif ACTIVITY_TYPE == "custom":
	clientActivityType = discord.ActivityType.custom
elif ACTIVITY_TYPE == "competing":
	clientActivityType = discord.ActivityType.competing
else:
	clientActivityType = discord.ActivityType.playing

if ACTIVITY_TEXT is not None:
	clientActivityText = ACTIVITY_TEXT
else:
	clientActivityText = ""

intents = discord.Intents().all()
client = commands.Bot(command_prefix = "$", activity=discord.Activity(type=clientActivityType, name=clientActivityText), status=clientStatus, intents=intents)

print("[" + datetime.now().strftime(r"%I:%M:%S %p") + "] " + "[2/3] Initializing connection to Korhal network.")

waitTime = 305 # 5 minutes 5 seconds (rate limit is 2 requests per 10 minutes)
counter = 0
gasCounter = 0
gasWaitTime = 15

# ------------------------------------------------
# EVENTS SECTION
# ------------------------------------------------

@client.event
async def on_ready():
	print("[" + datetime.now().strftime(r"%I:%M:%S %p") + "] " + "[3/3] Battlecruiser operational.")

async def check_price():
	global counter
	global defaultChannel
	while not client.is_closed():
		await client.wait_until_ready()
		counter += 1

		db = sqlite3.connect('coins.db')
		cursor = db.cursor()

		print("[" + datetime.now().strftime(r"%I:%M:%S %p") + "] " + "[" + str(counter) + "] Updating data")
		timestamp = datetime.now()
		time = timestamp.strftime(r"%I:%M %p")
		
		hdr = {'User-Agent': 'Mozilla/5.0'} # browser header

		cursor.execute("SELECT * FROM coins")
		result = ""
		coinsCount = 0
		for row in cursor:
			coinsCount += 1
			name = row[1]
			url = row[3]
			emoji = row[2]
			if emoji is None:
				emoji = "<>"

			print("[" + datetime.now().strftime(r"%I:%M:%S %p") + "] " + "Fetching " + name + " @ " + url)
			
			req = Request(url,headers=hdr)
			uClient = uReq(req)
			page_html = uClient.read()
			uClient.close()

			page_soup = soup(page_html, "html.parser")
			if "coinpaprika" in url:
				priceTag = page_soup.find_all("strong", {"class":"cp-usd-price"})
				fetchPrice = "";
				fetchPercent = "";
				for price in priceTag:
					coinPriceList = price.find_all("span", {"id":"coinPrice"})
					for coinPrice in coinPriceList:
						fetchPrice = coinPrice.text
						fetchPrice = fetchPrice.replace('\n', '').replace('\r', '')
					percentRankList = price.find_all("span", {"class":"cp-rank-up"})
					for percentRank in percentRankList:
						fetchPercent = percentRank.text
					percentRankList = price.find_all("span", {"class":"cp-rank-down"})
					for percentRank in percentRankList:
						fetchPercent = percentRank.text
					fetchPercent = fetchPercent.replace('\n', '').replace('\r', '')
			elif "coingecko" in url:
				page_soup = soup(page_html, "html.parser")
				fetchPrice = page_soup.find("span", {"class":"no-wrap"})
				fetchPrice = fetchPrice.text
				fetchPrice = fetchPrice.replace('\n', '').replace('\r', '')
				fetchPercent = page_soup.find("span", {"class":"live-percent-change"})
				fetchPercent = fetchPercent.text
				fetchPercent = fetchPercent.replace('\n', '').replace('\r', '')
				fetchPercent = "(" + fetchPercent + ")"
			fetchPriceAlt = round(float(fetchPrice[1:]) * 50, 2) # Average PHP price
			if coinsCount <= 1:
				result = "[" + time + "] "
			result = result + emoji + " " + name + ": " + fetchPrice + " / ₱" + str(fetchPriceAlt) + " " + fetchPercent + " "
		
		print(result)
		db = sqlite3.connect('channels.db')
		cursor = db.cursor()
		cursor.execute("SELECT * FROM channels")
		for row in cursor:
			getChannel = int(row[1])
			cryptoChannel = client.get_channel(getChannel)
			await cryptoChannel.edit(topic=result)

		await asyncio.sleep(waitTime) # task loop wait time

async def check_gas():
	global gasCounter
	global defaultChannel
	while not client.is_closed():
		gasCounter += 1

		
		timestamp = datetime.now()
		time = timestamp.strftime(r"%I:%M %p")

		content = requests.get("https://www.gasnow.org/api/v3/gas/price?utm_source=OptiBot")
		gas = json.loads(content.content)
		rapid = int(gas["data"]["rapid"] / math.pow(10, 9))
		fast = int(gas["data"]["fast"] / math.pow(10, 9))
		standard = int(gas["data"]["standard"] / math.pow(10, 9))
		slow = int(gas["data"]["slow"] / math.pow(10, 9))

		print("[" + datetime.now().strftime(r"%I:%M:%S %p") + "] " + "[" + str(gasCounter) + "] Reading gas prices: RAPID = " + str(rapid) + " | FAST = " + str(fast) + " | STANDARD = " + str(standard) + " | SLOW = " + str(slow))

		if slow <= 35:
			await client.wait_until_ready()
			channel = client.get_channel(868876393252020244)
			await channel.send("Gas price for SLOW reached " + str(slow) + " gwei | RAPID = " + str(rapid) + " | FAST = " + str(fast) + " | STANDARD = " + str(standard) + " | SLOW = " + str(slow))

		# await cryptoChannel.edit(topic=result)

		await asyncio.sleep(gasWaitTime) # task loop wait time

# ------------------------------------------------
# COMMANDS
# ------------------------------------------------

@client.command(pass_context=True)
async def add(ctx, coin = None, url = None, emoji = None):
	channel = ctx.channel # current channel

	if coin is None or url is None:
		embedTitle = 'Error: Coin name and URL is required.'
		embed=discord.Embed(
			title=embedTitle,
			description="Format: $add <COIN> <URL>",
			color=discord.Color.red())
		embed.set_thumbnail(url="https://image.pngaaa.com/946/28946-middle.png")
		await channel.send(embed=embed)
	else:
		db = sqlite3.connect('coins.db')
		cursor = db.cursor()
		cursor.execute("SELECT * FROM coins WHERE Name = '" + coin + "'")
		rows = cursor.fetchall()
		rowCount = len(rows)
		if rowCount > 0:
			embedTitle = 'Error: ' + coin + ' is already being fetched.'
			embed=discord.Embed(
				title=embedTitle,
				description="Format: $add <COIN> <URL>",
				color=discord.Color.red())
			embed.set_thumbnail(url="https://image.pngaaa.com/946/28946-middle.png")
			await channel.send(embed=embed)
		else:
			dateAdded = datetime.today().strftime("%Y-%m-%d %I:%M %p")
			cursor.execute("INSERT INTO coins (Name, Emoji, URL, DateAdded) VALUES (?, ?, ?, ?)", (coin, emoji, url, dateAdded))
			db.commit()
			embedTitle = 'Success: ' + coin + ' has been added to the fetch list.'
			embed=discord.Embed(
				title=embedTitle,
				description="Format: $add <COIN> <URL>",
				color=discord.Color.green())
			embed.set_thumbnail(url="https://toppng.com/uploads/preview/check-mark-png-11553192910q4npemdiib.png")
			await channel.send(embed=embed)

@client.command(pass_context=True)
async def update(ctx, coin = None, newUrl = None, newEmoji = None):
	channel = ctx.channel # current channel

	if coin is None:
		embedTitle = 'Error: Coin name is required.'
		embed=discord.Embed(
			title=embedTitle,
			description="Format: $update <COIN> <URL>",
			color=discord.Color.red())
		embed.set_thumbnail(url="https://image.pngaaa.com/946/28946-middle.png")
		await channel.send(embed=embed)
	else:
		db = sqlite3.connect('coins.db')
		cursor = db.cursor()
		cursor.execute("SELECT * FROM coins WHERE Name = '" + coin + "'")
		rows = cursor.fetchall()
		rowCount = len(rows)
		if rowCount > 0:
			url = ""
			emoji = ""
			for row in rows:
				url = row[3]
				emoji = row[2]
			if newUrl is not None:
				url = newUrl
			if newEmoji is not None:
				emoji = newEmoji

			if (url == newUrl and emoji == newEmoji):
				embedTitle = 'Nothing was changed.'
				embed=discord.Embed(
					title=embedTitle,
					description="Format: $update <COIN> <URL>",
					color=discord.Color.yellow())
				embed.set_thumbnail(url="https://mpng.subpng.com/20190808/bp/kisspng-warning-sign-5d4c128bd24591.0527908715652665718613.jpg")
				await channel.send(embed=embed)
			else:
				dateUpdated = datetime.today().strftime("%Y-%m-%d %I:%M %p")
				cursor.execute("UPDATE coins SET Emoji = ?, URL = ?, DateUpdated = ? WHERE Name = ?", (emoji, url, dateUpdated, coin))
				db.commit()
				embedTitle = 'Success: ' + coin + ' has been updated.'
				embed=discord.Embed(
					title=embedTitle,
					description="Format: $update <COIN> <URL>",
					color=discord.Color.green())
				embed.set_thumbnail(url="https://toppng.com/uploads/preview/check-mark-png-11553192910q4npemdiib.png")
				await channel.send(embed=embed)
		else:
			embedTitle = 'Error: ' + coin + ' is not in the list. $list to view all coins.'
			embed=discord.Embed(
				title=embedTitle,
				color=discord.Color.red())
			embed.set_thumbnail(url="https://image.pngaaa.com/946/28946-middle.png")
			await channel.send(embed=embed)

@client.command(pass_context=True)
async def remove(ctx, coin = None):
	channel = ctx.channel # current channel

	if coin is None:
		embedTitle = 'Error: Coin name is required.'
		embed=discord.Embed(
			title=embedTitle,
			description="Format: $remove <COIN>",
			color=discord.Color.red())
		embed.set_thumbnail(url="https://image.pngaaa.com/946/28946-middle.png")
		await channel.send(embed=embed)
	else:
		db = sqlite3.connect('coins.db')
		cursor = db.cursor()
		cursor.execute("SELECT * FROM coins WHERE Name = '" + coin + "'")
		rows = cursor.fetchall()
		rowCount = len(rows)
		if rowCount > 0:
			cursor.execute("DELETE FROM coins WHERE Name = '" + coin + "'")
			db.commit()
			embedTitle = 'Success: ' + coin + ' has been removed from the list.'
			embed=discord.Embed(
				title=embedTitle,
				description="Format: $remove <COIN>",
				color=discord.Color.green())
			embed.set_thumbnail(url="https://toppng.com/uploads/preview/check-mark-png-11553192910q4npemdiib.png")
			await channel.send(embed=embed)
		else:
			embedTitle = 'Error: ' + coin + ' is not in the list. $list to view all coins.'
			embed=discord.Embed(
				title=embedTitle,
				description="Format: $remove <COIN>",
				color=discord.Color.red())
			embed.set_thumbnail(url="https://image.pngaaa.com/946/28946-middle.png")
			await channel.send(embed=embed)

@client.command(pass_context=True)
async def list(ctx):
	channel = ctx.channel # current channel

	db = sqlite3.connect('coins.db')
	cursor = db.cursor()
	cursor.execute("SELECT * FROM coins")
	rows = cursor.fetchall()
	rowCount = len(rows)
	if rowCount > 0:
		embedTitle = "Coin List (" + str(rowCount) + ")" 
		embed=discord.Embed(
			title=embedTitle,
			color=discord.Color.orange())
		embed.set_thumbnail(url="https://i.kym-cdn.com/photos/images/newsfeed/001/475/112/f36.jpg")
		for row in rows:
			coinName = "#" + row[0] + " " + row[1]
			coinURL = row[3]
			embed.add_field(name=coinName, value=coinURL, inline=False)
		await channel.send(embed=embed)
	else:
		await channel.send('No coins to fetch. List new coins with $add <COIN> <URL>')

@client.command(pass_context=True)
async def listchannels(ctx):
	channel = ctx.channel # current channel

	db = sqlite3.connect('channels.db')
	cursor = db.cursor()
	cursor.execute("SELECT * FROM channels")
	rows = cursor.fetchall()
	rowCount = len(rows)
	if rowCount > 0:
		embedTitle = "Channels List (" + str(rowCount) + ")" 
		embed=discord.Embed(
			title=embedTitle,
			color=discord.Color.orange())
		embed.set_thumbnail(url="https://i.kym-cdn.com/photos/images/newsfeed/001/475/112/f36.jpg")
		for row in rows:
			coinChannel = "#" + str(row[0]) + " " + row[1]
			date = "Added in: " + row[2]
			embed.add_field(name=coinChannel, value=date, inline=False)
		await channel.send(embed=embed)
	else:
		await channel.send('No channels found.')

@client.command(pass_context=True)
async def addchannel(ctx, coinChannel = None):
	channel = ctx.channel # current channel

	if channel is None:
		embedTitle = 'Error: Channel ID is required (Right-click the channel with Dev mode enabled -> Copy ID).'
		embed=discord.Embed(
			title=embedTitle,
			description="Format: $addchannel <CHANNEL ID>",
			color=discord.Color.red())
		embed.set_thumbnail(url="https://image.pngaaa.com/946/28946-middle.png")
		await channel.send(embed=embed)
	else:
		db = sqlite3.connect('channels.db')
		cursor = db.cursor()
		cursor.execute("SELECT * FROM channels WHERE Channel = '" + coinChannel + "'")
		rows = cursor.fetchall()
		rowCount = len(rows)
		if rowCount > 0:
			embedTitle = 'Error: ' + coinChannel + ' is already listed.'
			embed=discord.Embed(
				title=embedTitle,
				description="Format: $addchannel <CHANNEL ID>",
				color=discord.Color.red())
			embed.set_thumbnail(url="https://image.pngaaa.com/946/28946-middle.png")
			await channel.send(embed=embed)
		else:
			dateAdded = datetime.today().strftime("%Y-%m-%d %I:%M %p")
			cursor.execute("INSERT INTO channels (Channel, DateAdded) VALUES (?, ?)", (coinChannel, dateAdded))
			db.commit()
			embedTitle = 'Success: ' + coinChannel + ' has been added.'
			embed=discord.Embed(
				title=embedTitle,
				description="Format: $addchannel <CHANNEL ID>",
				color=discord.Color.green())
			embed.set_thumbnail(url="https://toppng.com/uploads/preview/check-mark-png-11553192910q4npemdiib.png")
			await channel.send(embed=embed)

@client.command(pass_context=True)
async def removechannel(ctx, coinChannel = None):
	channel = ctx.channel # current channel

	if coin is None:
		embedTitle = 'Error: Channel ID is required (Right-click the channel with Dev mode enabled -> Copy ID).'
		embed=discord.Embed(
			title=embedTitle,
			description="Format: $removechannel <CHANNEL ID>",
			color=discord.Color.red())
		embed.set_thumbnail(url="https://image.pngaaa.com/946/28946-middle.png")
		await channel.send(embed=embed)
	else:
		db = sqlite3.connect('channels.db')
		cursor = db.cursor()
		cursor.execute("SELECT * FROM channels WHERE Channel = '" + coinChannel + "'")
		rows = cursor.fetchall()
		rowCount = len(rows)
		if rowCount > 0:
			cursor.execute("DELETE FROM channels WHERE Channel = '" + coinChannel + "'")
			db.commit()
			embedTitle = 'Success: ' + coin + ' has been removed from the list.'
			embed=discord.Embed(
				title=embedTitle,
				description="Format: $removechannel <CHANNEL ID>",
				color=discord.Color.green())
			embed.set_thumbnail(url="https://toppng.com/uploads/preview/check-mark-png-11553192910q4npemdiib.png")
			await channel.send(embed=embed)
		else:
			embedTitle = 'Error: ' + coinChannel + ' is not in the list. $listchannel to view all channels.'
			embed=discord.Embed(
				title=embedTitle,
				description="Format: $removechannel <CHANNEL ID>",
				color=discord.Color.red())
			embed.set_thumbnail(url="https://image.pngaaa.com/946/28946-middle.png")
			await channel.send(embed=embed)

# @client.command(pass_context=True)
# async def help(ctx):
# 	channel = ctx.channel # current channel

# 	embedTitle = "Commands List" 
# 	embed=discord.Embed(
# 		title=embedTitle,
# 		description="Format: $<COMMAND>",
# 		color=discord.Color.orange())
# 	embed.set_thumbnail(url="https://i.kym-cdn.com/photos/images/newsfeed/001/475/112/f36.jpg")
# 	embed.add_field(name="$list", value="List of all coins that are being fetched.", inline=False)
# 	embed.add_field(name="$add <COIN> <URL>", value="Adds a new coin to the list.", inline=False)
# 	embed.add_field(name="$update <COIN> <URL>", value="Updates the coin with new details.", inline=False)
# 	embed.add_field(name="$remove <COIN>", value="Removes the specified coin.", inline=False)
# 	await channel.send(embed=embed)

# ------------------------------------------------
# EXECUTE
# ------------------------------------------------

client.loop.create_task(check_price())
# client.loop.create_task(check_gas())	
client.run(TOKEN)