import os
import sqlite3
from datetime import datetime, date
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

DB_PATH = "inventory.db"
TOKEN = os.getenv("DISCORD_TOKEN")
print("TOKEN:", TOKEN)
ITEM_ALIASES = {
    "kit": "Kitsune",
    "kitsune": "Kitsune",
    "galaxy kit": "Galaxy Kitsune",
    "galaxy kitsune": "Galaxy Kitsune",
    "fiend yeti": "Fiend Yeti",
    "feind yeti": "Fiend Yeti",
    "yeti": "Fiend Yeti",
    "werewolf": "Werewolf",
    "were wolf": "Werewolf",
    "werewofl": "Werewolf",
    "divine portal": "Divine Portal",
    "devine portal": "Divine Portal",
    "devine": "Divine Portal",
    "purple lightning": "Purple Lightning",
    "yellow lightning": "Yellow Lightning",
    "red lightning": "Red Lightning",
    "dragon east": "Dragon East",
    "east dragon": "Dragon East",
    "dragon west": "Dragon West",
    "west dragon": "Dragon West",
}

STARTING_ACCOUNTS = {
    "Godofgrandson": {"max_cap": 26, "stock": {
        "Galaxy Kitsune": 1, "Fiend Yeti": 6, "Werewolf": 6, "Purple Lightning": 1,
        "Yellow Lightning": 1, "Red Lightning": 1, "Divine Portal": 6,
        "Dragon East": 12, "Dragon West": 8, "Kitsune": 26}},
    "Sauske2418": {"max_cap": 23, "stock": {
        "Galaxy Kitsune": 1, "Fiend Yeti": 1, "Werewolf": 3, "Yellow Lightning": 2,
        "Divine Portal": 1, "Dragon East": 3, "Dragon West": 3, "Kitsune": 23}},
    "Rocketzap84": {"max_cap": 19, "stock": {
        "Werewolf": 7, "Fiend Yeti": 2, "Yellow Lightning": 2, "Divine Portal": 4,
        "Dragon East": 6, "Dragon West": 1, "Kitsune": 19}},
    "Moneytalk778": {"max_cap": 21, "stock": {
        "Fiend Yeti": 2, "Yellow Lightning": 1, "Red Lightning": 2,
        "Dragon East": 3, "Dragon West": 2, "Kitsune": 21}},
    "Stormylightdancer31": {"max_cap": 17, "stock": {
        "Fiend Yeti": 4, "Divine Portal": 2, "Red Lightning": 2, "Kitsune": 17}},
    "Sh4dow_0022": {"max_cap": 16, "stock": {
        "Divine Portal": 1, "Kitsune": 16, "Dragon East": 3, "Dragon West": 2}},
    "orbitblockstream2020": {"max_cap": 9, "stock": {
        "Werewolf": 2, "Dragon East": 1, "Kitsune": 4, "Dragon West": 1}},
    "Skat3rZ3roSab3r": {"max_cap": 5, "stock": {
        "Divine Portal": 1, "Kitsune": 3}},
    "jamiulhasanS": {"max_cap": 5, "stock": {
        "Fiend Yeti": 1, "Werewolf": 1, "Kitsune": 2}},
}

STARTING_PRICES = {
    "Galaxy Kitsune": 35.00,
    "Fiend Yeti": 3.00,
    "Werewolf": 3.70,
    "Purple Lightning": 18.70,
    "Yellow Lightning": 6.30,
    "Red Lightning": 7.20,
    "Divine Portal": 5.27,
    "Dragon East": 15.00,
    "Dragon West": 15.00,
    "Kitsune": 2.30,
}

def today_str() -> str:
    return date.today().isoformat()

def normalize_item(item: str) -> str:
    key = item.strip().lower()
    return ITEM_ALIASES.get(key, item.strip().title())

def connect():
    return sqlite3.connect(DB_PATH)

def init_db():
    con = connect()
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS accounts (
        username TEXT PRIMARY KEY,
        max_cap INTEGER NOT NULL,
        trades_left INTEGER NOT NULL DEFAULT 5,
        last_reset TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS stock (
        username TEXT NOT NULL,
        item TEXT NOT NULL,
        qty INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(username, item)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS prices (
        item TEXT PRIMARY KEY,
        price REAL NOT NULL
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        username TEXT NOT NULL,
        item TEXT NOT NULL,
        qty INTEGER NOT NULL,
        value REAL NOT NULL,
        created_at TEXT NOT NULL
    )""")
    con.commit()

    # Seed only if empty
    count = cur.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    if count == 0:
        for username, data in STARTING_ACCOUNTS.items():
            cur.execute("INSERT INTO accounts(username, max_cap, trades_left, last_reset) VALUES (?, ?, 5, ?)",
                        (username, data["max_cap"], today_str()))
            for item, qty in data["stock"].items():
                cur.execute("INSERT INTO stock(username, item, qty) VALUES (?, ?, ?)", (username, item, qty))
        for item, price in STARTING_PRICES.items():
            cur.execute("INSERT INTO prices(item, price) VALUES (?, ?)", (item, price))
        con.commit()
    con.close()

def reset_if_needed():
    con = connect()
    cur = con.cursor()
    today = today_str()
    rows = cur.execute("SELECT username, last_reset FROM accounts").fetchall()
    for username, last_reset in rows:
        if last_reset != today:
            cur.execute("UPDATE accounts SET trades_left = 5, last_reset = ? WHERE username = ?", (today, username))
    con.commit()
    con.close()

def money(n: float) -> str:
    return f"${n:,.2f}"

class InventoryBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = InventoryBot()

@bot.event
async def on_ready():
    init_db()
    reset_if_needed()
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="find", description="Find which accounts have an item")
@app_commands.describe(item="Example: Kitsune, Dragon East, Galaxy Kitsune")
async def find(interaction: discord.Interaction, item: str):
    reset_if_needed()
    item = normalize_item(item)
    con = connect()
    cur = con.cursor()
    rows = cur.execute("""
        SELECT s.username, s.qty, a.max_cap, a.trades_left
        FROM stock s JOIN accounts a ON s.username=a.username
        WHERE s.item=? AND s.qty > 0
        ORDER BY s.qty DESC
    """, (item,)).fetchall()
    con.close()
    if not rows:
        return await interaction.response.send_message(f"No account has **{item}**.")
    msg = "\n".join([f"**{u}** → {q}/{cap} | trades left: {t}" for u, q, cap, t in rows])
    await interaction.response.send_message(f"Accounts with **{item}**:\n{msg}")

@bot.tree.command(name="full", description="Show accounts full of one item")
async def full(interaction: discord.Interaction, item: str):
    reset_if_needed()
    item = normalize_item(item)
    con = connect()
    cur = con.cursor()
    rows = cur.execute("""
        SELECT a.username, COALESCE(s.qty,0), a.max_cap, a.trades_left
        FROM accounts a
        LEFT JOIN stock s ON s.username=a.username AND s.item=?
        WHERE COALESCE(s.qty,0) >= a.max_cap
        ORDER BY a.max_cap DESC
    """, (item,)).fetchall()
    con.close()
    if not rows:
        return await interaction.response.send_message(f"No account is full of **{item}**.")
    msg = "\n".join([f"**{u}** → {q}/{cap} FULL | trades left: {t}" for u, q, cap, t in rows])
    await interaction.response.send_message(f"Full accounts for **{item}**:\n{msg}")

@bot.tree.command(name="space", description="Show accounts that still have space for one item")
async def space(interaction: discord.Interaction, item: str):
    reset_if_needed()
    item = normalize_item(item)
    con = connect()
    cur = con.cursor()
    rows = cur.execute("""
        SELECT a.username, COALESCE(s.qty,0), a.max_cap, a.trades_left
        FROM accounts a
        LEFT JOIN stock s ON s.username=a.username AND s.item=?
        WHERE COALESCE(s.qty,0) < a.max_cap
        ORDER BY (a.max_cap - COALESCE(s.qty,0)) DESC
    """, (item,)).fetchall()
    con.close()
    if not rows:
        return await interaction.response.send_message(f"All accounts are full of **{item}**.")
    msg = "\n".join([f"**{u}** → {q}/{cap} | space: {cap-q} | trades left: {t}" for u, q, cap, t in rows])
    await interaction.response.send_message(f"Space for **{item}**:\n{msg}")

@bot.tree.command(name="bestrestock", description="Suggest best account to restock an item")
async def bestrestock(interaction: discord.Interaction, item: str):
    reset_if_needed()
    item = normalize_item(item)
    con = connect()
    cur = con.cursor()
    row = cur.execute("""
        SELECT a.username, COALESCE(s.qty,0), a.max_cap, a.trades_left
        FROM accounts a
        LEFT JOIN stock s ON s.username=a.username AND s.item=?
        WHERE COALESCE(s.qty,0) < a.max_cap AND a.trades_left > 0
        ORDER BY (a.max_cap - COALESCE(s.qty,0)) DESC, a.trades_left DESC
        LIMIT 1
    """, (item,)).fetchone()
    con.close()
    if not row:
        return await interaction.response.send_message(f"No good account found for **{item}**. Either full or no trades left.")
    u, q, cap, t = row
    await interaction.response.send_message(f"Best restock account for **{item}**: **{u}** → {q}/{cap}, space {cap-q}, trades left {t}")

def change_stock(username: str, item: str, qty: int, action: str):
    if qty <= 0:
        raise ValueError("Amount must be positive.")
    item = normalize_item(item)
    con = connect()
    cur = con.cursor()
    acc = cur.execute("SELECT username, max_cap, trades_left FROM accounts WHERE lower(username)=lower(?)", (username,)).fetchone()
    if not acc:
        con.close()
        raise ValueError("Account not found.")
    username, max_cap, trades_left = acc
    if trades_left <= 0:
        con.close()
        raise ValueError(f"{username} has no trades left.")
    current = cur.execute("SELECT qty FROM stock WHERE username=? AND item=?", (username, item)).fetchone()
    current_qty = current[0] if current else 0

    if action == "restock":
        new_qty = current_qty + qty
        if new_qty > max_cap:
            con.close()
            raise ValueError(f"Cannot restock. {username} would become {new_qty}/{max_cap}.")
    elif action == "sell":
        new_qty = current_qty - qty
        if new_qty < 0:
            con.close()
            raise ValueError(f"Cannot sell. {username} only has {current_qty} {item}.")
    else:
        con.close()
        raise ValueError("Invalid action.")

    if current:
        cur.execute("UPDATE stock SET qty=? WHERE username=? AND item=?", (new_qty, username, item))
    else:
        cur.execute("INSERT INTO stock(username, item, qty) VALUES (?, ?, ?)", (username, item, new_qty))

    price_row = cur.execute("SELECT price FROM prices WHERE item=?", (item,)).fetchone()
    price = price_row[0] if price_row else 0
    value = price * qty

    cur.execute("UPDATE accounts SET trades_left = trades_left - 1 WHERE username=?", (username,))
    cur.execute("INSERT INTO logs(action, username, item, qty, value, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (action, username, item, qty, value, datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()
    return username, item, new_qty, max_cap, trades_left - 1, value

@bot.tree.command(name="restock", description="Add item to account and deduct 1 trade")
async def restock(interaction: discord.Interaction, username: str, item: str, amount: int = 1):
    reset_if_needed()
    try:
        u, it, new_qty, cap, trades, value = change_stock(username, item, amount, "restock")
        await interaction.response.send_message(
            f"Restocked **{amount}x {it}** to **{u}**.\nNow: {new_qty}/{cap}. Trades left: {trades}. Added value: {money(value)}"
        )
    except Exception as e:
        await interaction.response.send_message(f"Error: {e}")

@bot.tree.command(name="sell", description="Sell item from account and deduct 1 trade")
async def sell(interaction: discord.Interaction, username: str, item: str, amount: int = 1):
    reset_if_needed()
    try:
        u, it, new_qty, cap, trades, value = change_stock(username, item, amount, "sell")
        await interaction.response.send_message(
            f"Sold **{amount}x {it}** from **{u}**.\nNow: {new_qty}/{cap}. Trades left: {trades}. Sold value: {money(value)}"
        )
    except Exception as e:
        await interaction.response.send_message(f"Error: {e}")

@bot.tree.command(name="value", description="Show total inventory value")
async def value(interaction: discord.Interaction):
    reset_if_needed()
    con = connect()
    cur = con.cursor()
    rows = cur.execute("""
        SELECT s.item, SUM(s.qty), COALESCE(p.price,0), SUM(s.qty)*COALESCE(p.price,0)
        FROM stock s LEFT JOIN prices p ON s.item=p.item
        GROUP BY s.item
        ORDER BY SUM(s.qty)*COALESCE(p.price,0) DESC
    """).fetchall()
    con.close()
    total = sum(r[3] for r in rows)
    lines = [f"**{item}**: {qty} × {money(price)} = {money(val)}" for item, qty, price, val in rows if qty > 0]
    await interaction.response.send_message(f"Total stock value: **{money(total)}**\n" + "\n".join(lines[:20]))

@bot.tree.command(name="daily", description="Show today's restock/sell analysis")
async def daily(interaction: discord.Interaction):
    reset_if_needed()
    start = today_str()
    con = connect()
    cur = con.cursor()
    rows = cur.execute("""
        SELECT action, item, SUM(qty), SUM(value), COUNT(*)
        FROM logs
        WHERE date(created_at)=?
        GROUP BY action, item
        ORDER BY action, item
    """, (start,)).fetchall()
    trades = cur.execute("SELECT SUM(5 - trades_left) FROM accounts").fetchone()[0] or 0
    con.close()
    if not rows:
        return await interaction.response.send_message(f"No activity logged today. Trades used today: **{trades}**")
    lines = [f"**{action}** {item}: qty {qty}, value {money(val)}, commands {count}" for action, item, qty, val, count in rows]
    await interaction.response.send_message(f"Today's analysis:\nTrades used: **{trades}**\n" + "\n".join(lines))

@bot.tree.command(name="account", description="Show one account stock and trades")
async def account(interaction: discord.Interaction, username: str):
    reset_if_needed()
    con = connect()
    cur = con.cursor()
    acc = cur.execute("SELECT username, max_cap, trades_left FROM accounts WHERE lower(username)=lower(?)", (username,)).fetchone()
    if not acc:
        con.close()
        return await interaction.response.send_message("Account not found.")
    username, cap, trades = acc
    rows = cur.execute("SELECT item, qty FROM stock WHERE username=? AND qty > 0 ORDER BY item", (username,)).fetchall()
    con.close()
    lines = [f"{item}: {qty}/{cap}" for item, qty in rows]
    await interaction.response.send_message(f"**{username}** | trades left: **{trades}** | max cap: **{cap}**\n" + "\n".join(lines))

@bot.tree.command(name="setprice", description="Set or update item USD price")
async def setprice(interaction: discord.Interaction, item: str, price: float):
    item = normalize_item(item)
    con = connect()
    cur = con.cursor()
    cur.execute("INSERT INTO prices(item, price) VALUES (?, ?) ON CONFLICT(item) DO UPDATE SET price=excluded.price", (item, price))
    con.commit()
    con.close()
    await interaction.response.send_message(f"Price updated: **{item}** = **{money(price)}**")

@bot.tree.command(name="addaccount", description="Add a new account")
async def addaccount(interaction: discord.Interaction, username: str, max_cap: int):
    con = connect()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO accounts(username, max_cap, trades_left, last_reset) VALUES (?, ?, 5, ?)", (username, max_cap, today_str()))
        con.commit()
        await interaction.response.send_message(f"Added account **{username}** with max cap **{max_cap}**.")
    except sqlite3.IntegrityError:
        await interaction.response.send_message("That account already exists.")
    finally:
        con.close()

@bot.tree.command(name="resettrades", description="Manually reset all account trades to 5")
async def resettrades(interaction: discord.Interaction):
    con = connect()
    cur = con.cursor()
    cur.execute("UPDATE accounts SET trades_left=5, last_reset=?", (today_str(),))
    con.commit()
    con.close()
    await interaction.response.send_message("All account trades reset to **5**.")

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable.")

bot.run(TOKEN)
