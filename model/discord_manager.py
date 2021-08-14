import discord
from discord.ext import tasks, commands
from datetime import datetime
import json
import messenger
from keys import key

bot = commands.Bot(command_prefix="-")

    
@bot.event
async def on_ready():
    print("Logged in")
    updater.start()


@tasks.loop(seconds=60)
async def updater():
    noti = bot.get_channel(853110820611555328)
    announcements = bot.get_channel(864949029623169044)
#     await channel.send(str(datetime.today()))
    message = messenger.get_message()
    if len(message["trades"])>0:
        try:
            for trade in message["trades"]:
                action = "Liquidate" if trade["liquidate"] else "Trade"
                await announcements.send(f"{action} long position: {trade['long']}, and short position {trade['short']}")
        except:
            await announcements.send("Action performed but is corrupted")
        message["trades"] = []
        messenger.save_message(message)

@bot.command()
async def portfolio(message):
    '''Returns current printer mode, which corresponds to printer refersh rate'''
    portfolio = messenger.get_message()["portfolio"]
    await message.channel.send(f"Current USDT: {str(round(portfolio['usdt'], 2))}, total: {str(round(portfolio['total'], 2))}")
    
@bot.command()
async def summary(message, strat=None):
    """Plots analysis"""
    m = messenger.get_message()
    if strat is None:
        for strat in m["strategy"]:
            summary = m["strategy"][strat]
            await message.channel.send(f"{strat} occupies {str(round(summary['pct']*100, 2))}% of portfolio, with asset worths {str(round(summary['a'], 2))} and {str(round(summary['b'], 2))}")
    else:
        try:
            summary = m["strategy"][strat.upper()]
            await message.channel.send(f"{strat} occupies {str(round(summary['pct']*100, 2))}% of portfolio, with asset worths {str(round(summary['a'], 2))} and {str(round(summary['b'], 2))}")
        except:
            await message.channel.send(f"No summary available for strat {strat}")
            

@updater.before_loop
async def before():
    await bot.wait_until_ready()
    
bot.run(key("discord", "api"))

