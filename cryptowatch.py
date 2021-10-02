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
		
		cryptoChannel = client.get_channel(defaultChannel)
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

			if coinsCount <= 1:
				result = "[" + time + "] "
			result = result + emoji + " " + name + ": " + fetchPrice + " " + fetchPercent + " "
		
		print(result)
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
		await channel.send('Error: Coin name and URL is required. Format: $add <COIN> <URL>')
	else:
		db = sqlite3.connect('coins.db')
		cursor = db.cursor()
		cursor.execute("SELECT * FROM coins WHERE Name = '" + coin + "'")
		cursor.fetchall()
		rowCount = cursor.rowcount
		if rowCount > 0:
			await channel.send('Error: ' + coin + ' is already being fetched.')
		else:
			dateAdded = datetime.today().strftime("%Y-%m-%d %I:%M %p")
			cursor.execute("INSERT INTO coins (Name, Emoji, URL, DateAdded) VALUES (%s, %s, %s, %s)", (coin, emoji, url, dateAdded))
			db.commit()
			await channel.send('Success: ' + coin + ' has been added to the fetch list.')

@client.command(pass_context=True)
async def update(ctx, coin = None, newUrl = None, newEmoji = None):
	channel = ctx.channel # current channel

	if coin is None:
		await channel.send('Error: Coin name is required. Format: $update <COIN> <URL>')
	else:
		db = sqlite3.connect('coins.db')
		cursor = db.cursor()
		cursor.execute("SELECT * FROM coins WHERE Name = '" + coin + "'")
		cursor.fetchall()
		rowCount = cursor.rowcount
		if rowCount > 0:
			url = ""
			emoji = ""
			for row in cursor:
				url = row[3]
				emoji = row[2]
			if newUrl is not None:
				url = newUrl
			if newEmoji is not None:
				emoji = newEmoji

			if (url == newUrl and emoji == newEmoji):
				await channel.send('Nothing was changed. Format: $update <COIN> <URL>')
			else:
				dateUpdated = datetime.today().strftime("%Y-%m-%d %I:%M %p")
				cursor.execute("UPDATE coins SET Emoji = %s, URL = %s, DateUpdated = %s WHERE Name = %s", (emoji, url, dateUpdated, coin))
				db.commit()
				await channel.send('Success: ' + coin + ' has been updated.')
		else:
			await channel.send('Error: ' + coin + ' is not being fetched.')

# ------------------------------------------------
# EXECUTE
# ------------------------------------------------

client.loop.create_task(check_price())
# client.loop.create_task(check_gas())	
client.run(TOKEN)