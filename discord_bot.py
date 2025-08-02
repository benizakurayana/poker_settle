#!/usr/bin/env python3

import discord
from discord.ext import commands
import aiohttp
import asyncio
import json
import os
from datetime import datetime

# Discord bot configuration
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!poker ', intents=intents)

# API configuration - your Flask app
API_BASE_URL = "http://localhost:5000/api"  # Change this if deployed elsewhere

class PokerAPI:
    """Helper class to interact with the Flask API"""
    
    @staticmethod
    async def make_request(method, endpoint, data=None):
        """Make async HTTP request to Flask API"""
        url = f"{API_BASE_URL}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            try:
                if method.upper() == 'GET':
                    async with session.get(url) as response:
                        return await response.json(), response.status
                elif method.upper() == 'POST':
                    async with session.post(url, json=data) as response:
                        return await response.json(), response.status
                elif method.upper() == 'DELETE':
                    async with session.delete(url, json=data) as response:
                        return await response.json(), response.status
            except Exception as e:
                return {"error": str(e)}, 500

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready to manage poker games!')

@bot.command(name='start')
async def start_game(ctx, date: str = None):
    """Start a new poker game
    Usage: !poker start 08/01
    """
    if not date:
        date = datetime.now().strftime("%m/%d")
    
    data, status = await PokerAPI.make_request('POST', '/game/start', {'date': date})
    
    if status == 200:
        embed = discord.Embed(
            title="🎮 Poker Game Started!",
            description=f"Game started for **{date}**",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Error starting game: {data.get('error', 'Unknown error')}")

@bot.command(name='buyin')
async def buy_in(ctx, name: str, amount: int):
    """Player buy-in
    Usage: !poker buyin Alice 100
    """
    data, status = await PokerAPI.make_request('POST', '/players/buy-in', {
        'name': name,
        'amount': amount
    })
    
    if status == 200:
        embed = discord.Embed(
            title="💰 Buy-in Recorded",
            description=f"**{name}** bought in for **${amount}**",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Error recording buy-in: {data.get('error', 'Unknown error')}")

@bot.command(name='payment')
async def payment(ctx, name: str, amount: int, method: str = "cash"):
    """Record player payment
    Usage: !poker payment Alice 50 cash
    Usage: !poker payment Bob 75 zelle
    """
    if method.lower() not in ['cash', 'zelle']:
        await ctx.send("❌ Payment method must be 'cash' or 'zelle'")
        return
    
    data, status = await PokerAPI.make_request('POST', '/players/payment', {
        'name': name,
        'amount': amount,
        'method': method.lower()
    })
    
    if status == 200:
        embed = discord.Embed(
            title="💳 Payment Recorded",
            description=f"**{name}** paid **${amount}** via **{method}**",
            color=0x0099ff
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Error recording payment: {data.get('error', 'Unknown error')}")

@bot.command(name='cashout')
async def cash_out(ctx, name: str, amount: int):
    """Record player cash out
    Usage: !poker cashout Alice 75
    """
    data, status = await PokerAPI.make_request('POST', '/players/cash-out', {
        'name': name,
        'amount': amount
    })
    
    if status == 200:
        embed = discord.Embed(
            title="💵 Cash Out Recorded",
            description=f"**{name}** cashed out **${amount}**",
            color=0xffaa00
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Error recording cash out: {data.get('error', 'Unknown error')}")

@bot.command(name='payout')
async def payout(ctx, name: str, amount: int, method: str = "cash"):
    """Record player payout
    Usage: !poker payout Alice 25 cash
    Usage: !poker payout Bob 50 zelle
    """
    if method.lower() not in ['cash', 'zelle']:
        await ctx.send("❌ Payout method must be 'cash' or 'zelle'")
        return
    
    data, status = await PokerAPI.make_request('POST', '/players/payout', {
        'name': name,
        'amount': amount,
        'method': method.lower()
    })
    
    if status == 200:
        embed = discord.Embed(
            title="💸 Payout Recorded",
            description=f"**{name}** received payout of **${amount}** via **{method}**",
            color=0x9900ff
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Error recording payout: {data.get('error', 'Unknown error')}")

@bot.command(name='remove')
async def remove_player(ctx, name: str):
    """Remove a player from the table
    Usage: !poker remove Alice
    """
    data, status = await PokerAPI.make_request('DELETE', '/players/remove', {'name': name})
    
    if status == 200:
        embed = discord.Embed(
            title="🗑️ Player Removed",
            description=f"**{name}** has been removed from the table",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Error removing player: {data.get('error', 'Unknown error')}")

@bot.command(name='table')
async def show_table(ctx):
    """Show current table status
    Usage: !poker table
    """
    data, status = await PokerAPI.make_request('GET', '/table')
    
    if status != 200:
        await ctx.send(f"❌ Error getting table data: {data.get('error', 'Unknown error')}")
        return
    
    table = data.get('table', {})
    current_date = data.get('current_date', 'None')
    
    if not table:
        embed = discord.Embed(
            title="🃏 Poker Table",
            description="No players at the table yet",
            color=0x666666
        )
        embed.add_field(name="Current Game", value=current_date, inline=False)
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="🃏 Current Poker Table",
        description=f"Game Date: **{current_date}**",
        color=0x0099ff
    )
    
    for name, player_data in table.items():
        payment_total = player_data['cash'] + player_data['zelle']
        payout_total = player_data['payout_cash'] + player_data['payout_zelle']
        
        field_value = (
            f"💰 Buy-in: ${player_data['buy_in']}\n"
            f"💳 Payment: ${payment_total} ({player_data['cash']}+{player_data['zelle']})\n"
            f"💵 Cash Out: ${player_data['cash_out']}\n"
            f"💸 Payout: ${payout_total} ({player_data['payout_cash']}+{player_data['payout_zelle']})"
        )
        
        embed.add_field(name=f"👤 {name}", value=field_value, inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='summary')
async def summary(ctx):
    """Show game summary
    Usage: !poker summary
    """
    data, status = await PokerAPI.make_request('GET', '/summary')
    
    if status != 200:
        await ctx.send(f"❌ Error getting summary: {data.get('error', 'Unknown error')}")
        return
    
    embed = discord.Embed(
        title="📊 Game Summary",
        color=0xffaa00
    )
    
    embed.add_field(name="💰 Total Buy In", value=f"${data['total_buy_in']}", inline=True)
    embed.add_field(name="💵 Total Cash Out", value=f"${data['total_cash_out']}", inline=True)
    embed.add_field(name="💳 Total Payment", value=f"${data['total_payment']}", inline=True)
    embed.add_field(name="💸 Total Payout", value=f"${data['total_payout']}", inline=True)
    embed.add_field(name="🏦 Bank Balance", value=f"${data['bank_balance']}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='solve')
async def solve(ctx):
    """Calculate settlement transfers
    Usage: !poker solve
    """
    data, status = await PokerAPI.make_request('GET', '/solve')
    
    if status != 200:
        await ctx.send(f"❌ Error calculating settlement: {data.get('error', 'Unknown error')}")
        return
    
    # Player Balances
    embed1 = discord.Embed(
        title="⚖️ Player Balances",
        color=0x9900ff
    )
    
    for name, balance in data['balances'].items():
        if balance > 0:
            embed1.add_field(name=f"✅ {name}", value=f"+${balance}", inline=True)
        elif balance < 0:
            embed1.add_field(name=f"❌ {name}", value=f"-${abs(balance)}", inline=True)
        else:
            embed1.add_field(name=f"⚪ {name}", value="$0", inline=True)
    
    await ctx.send(embed=embed1)
    
    # Settlement Transfers
    if data['transactions']:
        embed2 = discord.Embed(
            title="💸 Settlement Transfers",
            description="Minimum transfers needed to settle all balances:",
            color=0x00ff00
        )
        
        transfer_text = ""
        for i, tx in enumerate(data['transactions'], 1):
            transfer_text += f"{i}. **{tx['payer']}** pays **{tx['receiver']}** → **${tx['amount']}**\n"
        
        embed2.add_field(name="Transfers", value=transfer_text, inline=False)
        embed2.add_field(name="🏦 Final Bank Balance", value=f"${data['final_bank_balance']}", inline=False)
        
        await ctx.send(embed=embed2)
    else:
        embed2 = discord.Embed(
            title="✅ No Transfers Needed",
            description="All balances are already settled!",
            color=0x00ff00
        )
        await ctx.send(embed=embed2)

@bot.command(name='help')
async def help_command(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🎮 Poker Bot Commands",
        description="Manage your poker games with these commands:",
        color=0x0099ff
    )
    
    commands_text = """
    `!poker start [date]` - Start a new game (default: today)
    `!poker buyin <name> <amount>` - Record player buy-in
    `!poker payment <name> <amount> [method]` - Record payment (cash/zelle)
    `!poker cashout <name> <amount>` - Record cash out
    `!poker payout <name> <amount> [method]` - Record payout (cash/zelle)
    `!poker remove <name>` - Remove player from table
    `!poker table` - Show current table status
    `!poker summary` - Show game summary
    `!poker solve` - Calculate settlement transfers
    `!poker help` - Show this help message
    """
    
    embed.add_field(name="Available Commands", value=commands_text, inline=False)
    embed.add_field(name="Examples", value="""
    `!poker start 08/01`
    `!poker buyin Alice 100`
    `!poker payment Bob 50 zelle`
    `!poker solve`
    """, inline=False)
    
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!poker help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument type. Use `!poker help` for command usage.")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")

if __name__ == "__main__":
    # Get Discord bot token from environment variable
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN environment variable not set!")
        print("Please set your Discord bot token:")
        print("export DISCORD_BOT_TOKEN='your_bot_token_here'")
        exit(1)
    
    print("🤖 Starting Discord Poker Bot...")
    print("🌐 Make sure your Flask API is running on http://localhost:5000")
    bot.run(TOKEN)
