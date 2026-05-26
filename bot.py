import os
import sqlite3
from datetime import datetime, date
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

DB_PATH = "inventory.db"
TOKEN = os.getenv("DISCORD_TOKEN")
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

# ---------- Premium UI helpers ----------

COLOR_MAIN = 0x7C3AED
COLOR_SUCCESS = 0x22C55E
COLOR_ERROR = 0xEF4444
COLOR_WARNING = 0xF59E0B
COLOR_INFO = 0x38BDF8

ITEM_EMOJIS = {
    "Kitsune": "🦊",
    "Galaxy Kitsune": "🌌",
    "Fiend Yeti": "👹",
    "Werewolf": "🐺",
    "Divine Portal": "🌀",
    "Purple Lightning": "🟣",
    "Yellow Lightning": "🟡",
    "Red Lightning": "🔴",
    "Dragon East": "🐉",
    "Dragon West": "🐲",
}

def item_icon(item: str) -> str:
    return ITEM_EMOJIS.get(item, "🍈")

def make_embed(title: str, description: str = "", color: int = COLOR_MAIN):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text="Twix Vault Business • Inventory System")
    return embed

def success_embed(title: str, description: str):
    return make_embed(f"✅ {title}", description, COLOR_SUCCESS)

def error_embed(description: str):
    return make_embed("❌ Error", description, COLOR_ERROR)

def warning_embed(title: str, description: str):
    return make_embed(f"⚠️ {title}", description, COLOR_WARNING)

def chunk_lines(lines, limit=1000):
    chunks = []
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current += ("\n" if current else "") + line
    if current:
        chunks.append(current)
    return chunks

def find_account(search: str):
    """
    Smart account finder.
    Examples: god -> Godofgrandson, sau -> Sauske2418, storm -> Stormylightdancer31
    """
    con = connect()
    cur = con.cursor()
    rows = cur.execute("SELECT username FROM accounts").fetchall()
    con.close()

    usernames = [r[0] for r in rows]
    search = search.strip().lower()

    exact = [u for u in usernames if u.lower() == search]
    if exact:
        return exact[0]

    starts = [u for u in usernames if u.lower().startswith(search)]
    if len(starts) == 1:
        return starts[0]
    if len(starts) > 1:
        raise ValueError(f"Multiple accounts matched: {', '.join(starts)}")

    partial = [u for u in usernames if search in u.lower()]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        raise ValueError(f"Multiple accounts matched: {', '.join(partial)}")

    raise ValueError("Account not found.")

class InventoryBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
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
        return await interaction.response.send_message(embed=warning_embed("Not Found", f"No account has **{item}**."))

    total = sum(q for _, q, _, _ in rows)
    embed = make_embed(f"{item_icon(item)} {item} Stock Finder", f"Total found: **{total}x** across **{len(rows)}** accounts", COLOR_INFO)

    lines = []
    for u, q, cap, t in rows:
        status = "FULL" if q >= cap else f"{cap-q} space"
        lines.append(f"**{u}** → `{q}/{cap}` • trades: `{t}` • {status}")

    for i, chunk in enumerate(chunk_lines(lines), start=1):
        embed.add_field(name="Accounts" if i == 1 else f"Accounts {i}", value=chunk, inline=False)

    await interaction.response.send_message(embed=embed)

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
        return await interaction.response.send_message(embed=warning_embed("No Full Accounts", f"No account is full of **{item}**."))

    embed = make_embed(f"🔒 Full Accounts • {item_icon(item)} {item}", f"**{len(rows)}** accounts are full.", COLOR_WARNING)
    lines = [f"**{u}** → `{q}/{cap}` • trades: `{t}`" for u, q, cap, t in rows]
    for i, chunk in enumerate(chunk_lines(lines), start=1):
        embed.add_field(name="Full List" if i == 1 else f"Full List {i}", value=chunk, inline=False)

    await interaction.response.send_message(embed=embed)

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
        return await interaction.response.send_message(embed=warning_embed("No Space", f"All accounts are full of **{item}**."))

    embed = make_embed(f"📦 Space Available • {item_icon(item)} {item}", "Best restock accounts are shown first.", COLOR_SUCCESS)
    lines = [f"**{u}** → `{q}/{cap}` • space: `{cap-q}` • trades: `{t}`" for u, q, cap, t in rows]
    for i, chunk in enumerate(chunk_lines(lines), start=1):
        embed.add_field(name="Available Accounts" if i == 1 else f"Available Accounts {i}", value=chunk, inline=False)

    await interaction.response.send_message(embed=embed)

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
        return await interaction.response.send_message(embed=warning_embed("No Restock Option", f"No good account found for **{item}**. Either full or no trades left."))

    u, q, cap, t = row
    embed = success_embed("Best Restock Account", f"Best account for **{item_icon(item)} {item}** is **{u}**.")
    embed.add_field(name="Current Stock", value=f"`{q}/{cap}`", inline=True)
    embed.add_field(name="Free Space", value=f"`{cap-q}`", inline=True)
    embed.add_field(name="Trades Left", value=f"`{t}`", inline=True)
    await interaction.response.send_message(embed=embed)

def change_stock(username: str, item: str, qty: int, action: str):
    if qty <= 0:
        raise ValueError("Amount must be positive.")
    item = normalize_item(item)
    con = connect()
    cur = con.cursor()
    real_username = find_account(username)
    acc = cur.execute("SELECT username, max_cap, trades_left FROM accounts WHERE username=?", (real_username,)).fetchone()
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
        embed = success_embed("Restock Complete", f"Added **{amount}x {item_icon(it)} {it}** to **{u}**.")
        embed.add_field(name="New Stock", value=f"`{new_qty}/{cap}`", inline=True)
        embed.add_field(name="Trades Left", value=f"`{trades}`", inline=True)
        embed.add_field(name="Added Value", value=money(value), inline=True)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(embed=error_embed(str(e)))

@bot.tree.command(name="sell", description="Sell item from account and deduct 1 trade")
async def sell(interaction: discord.Interaction, username: str, item: str, amount: int = 1):
    reset_if_needed()
    try:
        u, it, new_qty, cap, trades, value = change_stock(username, item, amount, "sell")
        embed = success_embed("Sale Logged", f"Sold **{amount}x {item_icon(it)} {it}** from **{u}**.")
        embed.add_field(name="New Stock", value=f"`{new_qty}/{cap}`", inline=True)
        embed.add_field(name="Trades Left", value=f"`{trades}`", inline=True)
        embed.add_field(name="Sold Value", value=money(value), inline=True)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(embed=error_embed(str(e)))

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
    embed = make_embed("💰 Total Inventory Value", f"Current combined value: **{money(total)}**", COLOR_SUCCESS)
    lines = [f"{item_icon(item)} **{item}**: `{qty}` × `{money(price)}` = **{money(val)}**" for item, qty, price, val in rows if qty > 0]
    for i, chunk in enumerate(chunk_lines(lines), start=1):
        embed.add_field(name="Inventory Values" if i == 1 else f"Inventory Values {i}", value=chunk, inline=False)
    await interaction.response.send_message(embed=embed)

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

    embed = make_embed("📊 Today's Business Report", f"Trades used today: **{trades}**", COLOR_INFO)

    if not rows:
        embed.description += "No sales/restocks logged today."
        return await interaction.response.send_message(embed=embed)

    lines = []
    for action, item, qty, val, count in rows:
        icon = "📥" if action == "restock" else "📤"
        lines.append(f"{icon} **{action.title()}** {item_icon(item)} {item}: qty `{qty}` • value **{money(val)}** • commands `{count}`")

    for i, chunk in enumerate(chunk_lines(lines), start=1):
        embed.add_field(name="Activity" if i == 1 else f"Activity {i}", value=chunk, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="account", description="Show one account stock and trades")
async def account(interaction: discord.Interaction, username: str):
    reset_if_needed()
    con = connect()
    cur = con.cursor()

    try:
        real_username = find_account(username)
    except Exception as e:
        con.close()
        return await interaction.response.send_message(embed=error_embed(str(e)))

    acc = cur.execute("SELECT username, max_cap, trades_left FROM accounts WHERE username=?", (real_username,)).fetchone()
    if not acc:
        con.close()
        return await interaction.response.send_message(embed=error_embed("Account not found."))

    username, cap, trades = acc
    rows = cur.execute("SELECT item, qty FROM stock WHERE username=? AND qty > 0 ORDER BY item", (username,)).fetchall()
    con.close()

    embed = make_embed(f"👤 Account Panel • {username}", "", COLOR_MAIN)
    embed.add_field(name="Max Cap", value=f"`{cap}`", inline=True)
    embed.add_field(name="Trades Left", value=f"`{trades}/5`", inline=True)

    if rows:
        lines = [f"{item_icon(item)} **{item}**: `{qty}/{cap}`" for item, qty in rows]
        for i, chunk in enumerate(chunk_lines(lines), start=1):
            embed.add_field(name="Stock" if i == 1 else f"Stock {i}", value=chunk, inline=False)
    else:
        embed.add_field(name="Stock", value="No stock found.", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setprice", description="Set or update item USD price")
async def setprice(interaction: discord.Interaction, item: str, price: float):
    item = normalize_item(item)
    con = connect()
    cur = con.cursor()
    cur.execute("INSERT INTO prices(item, price) VALUES (?, ?) ON CONFLICT(item) DO UPDATE SET price=excluded.price", (item, price))
    con.commit()
    con.close()

    embed = success_embed("Price Updated", f"**{item_icon(item)} {item}** is now **{money(price)}**.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addaccount", description="Add a new account")
async def addaccount(interaction: discord.Interaction, username: str, max_cap: int):
    con = connect()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO accounts(username, max_cap, trades_left, last_reset) VALUES (?, ?, 5, ?)", (username, max_cap, today_str()))
        con.commit()
        embed = success_embed("Account Added", f"Added **{username}** with max cap **{max_cap}** and **5 trades**.")
        await interaction.response.send_message(embed=embed)
    except sqlite3.IntegrityError:
        await interaction.response.send_message(embed=error_embed("That account already exists."))
    finally:
        con.close()

@bot.tree.command(name="resettrades", description="Manually reset all account trades to 5")
async def resettrades(interaction: discord.Interaction):
    con = connect()
    cur = con.cursor()
    cur.execute("UPDATE accounts SET trades_left=5, last_reset=?", (today_str(),))
    con.commit()
    con.close()
    await interaction.response.send_message(embed=success_embed("Trades Reset", "All account trades reset to **5**."))


@bot.tree.command(name="settrades", description="Set trades for one account")
@app_commands.describe(username="Example: god, sau, storm", amount="Trades amount, example: 5")
async def settrades(interaction: discord.Interaction, username: str, amount: int):
    reset_if_needed()
    if amount < 0:
        return await interaction.response.send_message(embed=error_embed("Trades cannot be negative."))

    try:
        real_username = find_account(username)
        con = connect()
        cur = con.cursor()
        cur.execute("UPDATE accounts SET trades_left=?, last_reset=? WHERE username=?", (amount, today_str(), real_username))
        con.commit()
        con.close()

        embed = success_embed("Trades Updated", f"Trades for **{real_username}** set to **{amount}**.")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(embed=error_embed(str(e)))

@bot.tree.command(name="setcap", description="Change max cap for one account")
@app_commands.describe(username="Example: god, sau, storm", cap="New max cap")
async def setcap(interaction: discord.Interaction, username: str, cap: int):
    reset_if_needed()
    if cap <= 0:
        return await interaction.response.send_message(embed=error_embed("Cap must be greater than 0."))

    try:
        real_username = find_account(username)
        con = connect()
        cur = con.cursor()
        cur.execute("UPDATE accounts SET max_cap=? WHERE username=?", (cap, real_username))
        con.commit()
        con.close()

        embed = success_embed("Max Cap Updated", f"Max cap for **{real_username}** updated to **{cap}**.")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(embed=error_embed(str(e)))

@bot.tree.command(name="panel", description="Premium overview dashboard")
async def panel(interaction: discord.Interaction):
    reset_if_needed()
    con = connect()
    cur = con.cursor()

    accounts = cur.execute("SELECT username, max_cap, trades_left FROM accounts ORDER BY username").fetchall()
    total_accounts = len(accounts)
    total_trades = sum(t for _, _, t in accounts)

    value_row = cur.execute("""
        SELECT SUM(s.qty * COALESCE(p.price,0))
        FROM stock s LEFT JOIN prices p ON s.item=p.item
    """).fetchone()
    total_value = value_row[0] or 0

    stock_rows = cur.execute("""
        SELECT item, SUM(qty)
        FROM stock
        WHERE qty > 0
        GROUP BY item
        ORDER BY SUM(qty) DESC
    """).fetchall()
    con.close()

    embed = make_embed("👑 Twix Vault Business Dashboard", "Premium inventory control panel", COLOR_MAIN)
    embed.add_field(name="Accounts", value=f"`{total_accounts}`", inline=True)
    embed.add_field(name="Trades Left", value=f"`{total_trades}`", inline=True)
    embed.add_field(name="Total Value", value=f"**{money(total_value)}**", inline=True)

    stock_lines = [f"{item_icon(item)} **{item}**: `{qty}`" for item, qty in stock_rows]
    if stock_lines:
        embed.add_field(name="Combined Stock", value=chunk_lines(stock_lines, 1000)[0], inline=False)

    trade_lines = [f"**{u}** → trades `{t}` • cap `{cap}`" for u, cap, t in accounts]
    if trade_lines:
        embed.add_field(name="Account Trades", value=chunk_lines(trade_lines, 1000)[0], inline=False)

    await interaction.response.send_message(embed=embed)

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable.")

bot.run(TOKEN)
