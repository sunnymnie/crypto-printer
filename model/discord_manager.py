import discord
from discord.ext import tasks, commands
from datetime import datetime
import json

bot = commands.Bot(command_prefix="-")

messages = {"message":"", "o_l":"", "o_s":""}
def get_message(message:str):
    global messages
    """gets the message"""
    with open('message.txt') as json_file:
        new_message = json.load(json_file)[message]
        try: #Basically, sometimes if you don't need to limit rate
            if messages[message] == new_message: #Same message
                return ""
            elif messages[message] == "": #Haven't updated
                messages[message] = new_message
                return ""
            messages[message] = new_message
        except:
            pass
        return new_message
    
@bot.event
async def on_ready():
    print("Logged in")
    updater.start()


@tasks.loop(seconds=60)
async def updater():
    noti = bot.get_channel(853110820611555328)
    announcements = bot.get_channel(864949029623169044)
#     await channel.send(str(datetime.today()))
    try:
        await announcements.send(get_message("message"))
    except:
        pass
    try:
        await noti.send(get_message("o_l"))
    except:
        pass
    try:
        await noti.send(get_message("o_s"))
    except:
        pass
    
@bot.command()
async def asset(message, asset=""):
    '''Returns isolated margin account for that asset'''
    try:
        reply = "-------------------------\n"
        a = get_isolated_margin_account(asset.upper())
        for item in a["baseAsset"]:
            if item in ["asset", "borrowed", "free", "interest", "netAsset"]:
                reply = reply + f"{item}: {a['baseAsset'][item]}\n"
        reply = reply + "-------------------------\n"
        for item in a["quoteAsset"]:
            if item in ["asset", "free"]:
                reply = reply + f"{item}: {a['quoteAsset'][item]}\n"
        await message.channel.send(reply)
    except:
        await message.channel.send("There are no positions with that asset")
        
        
@bot.command()
async def mode(message):
    '''Returns current printer mode, which corresponds to printer refersh rate'''
    await message.channel.send(f"Current mode is : {get_message('mode')}")
    
@bot.command()
async def z(message):
    '''Returns current z-score'''
    await message.channel.send(f"Latest z-score: {str(round(float(get_message('z')), 2))}")
    
@bot.command()
async def analyze(message, a="CELR", b="FET", past=2000):
    """Plots analysis"""
    create_plot(a, b, "USDT", past)
    await message.channel.send(file=discord.File('plot.png'))

@bot.command()
async def level(message, asset=""):
    """Get current margin level of asset, where 2 or greater is safe"""
    get_isolated_margin_account("FET")
    if asset == "":
        await message.channel.send(f"Current margin level is {client.get_margin_account()['marginLevel']}")
    else:
        try:
            await message.channel.send(f"Current margin level for {asset.upper()} is {get_isolated_margin_account(asset.upper())['marginLevel']}")
        except:
            await message.channel.send(f"Margin level does not exist for asset {asset.upper()}")
    
@bot.command()
async def position(message, asset="", quote="USDT"):
    """Get position for asset with quote="USDT". ASSUMES there is an ongoing trade"""
    trade = 0 #Price that I traded the asset for
    price = 0
    percent = 0
    pair = asset.upper() + quote.upper()
    side = ""
    try:
        price = round(get_price(pair), 5) #Current price
        position = client.get_margin_trades(symbol=pair, isIsolated='TRUE')[-1]
        trade = round(float(position["price"]), 5)
        if position["isBuyer"]:
            side = "Long"
            percent = round((price-trade)*100/trade, 2)
        else:
            side = "Short"
            percent = round((trade-price)*100/trade, 2)    
        await message.channel.send(f"{side} {asset.upper()}: Trade price: {str(trade)}, now: {str(price)}, current change: {str(percent)}%")
    except:
        await message.channel.send(f"Unfortuately cannot find position for {pair}")

@updater.before_loop
async def before():
    await bot.wait_until_ready()
    
def get_price(symbol:str):
    """returns the price. symbol MUST include USDT, ie ZECUSDT"""
    return float(client.get_recent_trades(symbol=symbol, limit=1)[0]["price"])

def get_isolated_margin_account(base_asset: str):
    """Returns dict for isolated margin account for base_asset. Enter base_asset as 'FET'. Do NOT include USDT"""
    c = client.get_isolated_margin_account()
    return list(filter(lambda x: x["baseAsset"]["asset"] == base_asset, c["assets"]))[0]

bot.run(dtoken)

