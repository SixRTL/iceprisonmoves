import discord
from discord.ext import commands
from pymongo import MongoClient
import pokebase as pb
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize bot with Message Content Intent enabled
intents = discord.Intents.default()
intents.message_content = True  # Enable Message Content Intent

bot = commands.Bot(command_prefix="&", intents=intents, help_command=None)

# Database setup
mongo_client = MongoClient(os.getenv("MONGO_URI"))
db = mongo_client["move_bot"]
moves_collection = db["moves"]

# Function to categorize moves
def categorize_move(damage_class, base_power, move_name):
    # List of 1-hit KO moves and special unique moves
    unique_moves = [
        "dragon rage", "sonic boom", "guillotine", "fissure", "horn drill", "sheer cold"
    ]
    
    # List of status moves (moves that alter stats or have no base power and are status-related)
    stat_altering_moves = [
        "growl", "swords dance", "agility", "leer", "tail whip", "sand attack", "iron defense", 
        "amnesia", "calm mind", "harden", "ancient power", "work up"
    ]
    
    # Explicitly classify unique moves first
    if move_name.lower() in unique_moves:
        return "Unique"
    
    # Check if the move is a stat-altering move and categorize it as Status
    if move_name.lower() in stat_altering_moves or damage_class == "status":
        return "Status"
    
    # If no base power, categorize as Unique (unless it's a stat-altering move, which is already handled)
    if base_power is None:
        return "Unique"

    # Categorize damage moves by base power
    if 1 <= base_power <= 60:
        return "Light"
    elif 61 <= base_power <= 99:
        return "Medium"
    elif 100 <= base_power <= 500:
        return "Heavy"
    else:
        return "Medium"  # For base power over 500, categorize as Medium

@bot.event
async def on_ready():
    print(f"Bot is ready as {bot.user}")

@bot.command()
async def learn(ctx, character: str, move: str):
    """Register a move for a user's character."""
    try:
        # Fetch move details from Pokebase
        move_data = pb.move(move.lower())  # Using lowercase for consistency

        # Extract damage class and base power
        damage_class = getattr(move_data.damage_class, 'name', None)  # "physical", "special", or "status"
        base_power = getattr(move_data, 'power', None)  # Fetch base power

        # Categorize move based on its damage class and name
        move_type = categorize_move(damage_class, base_power, move_data.name)

        # Save to the database
        move_entry = {
            "user_id": ctx.author.id,
            "character_name": character,
            "move_name": move_data.name,
            "move_type": move_type
        }
        moves_collection.insert_one(move_entry)

        # Create an embed message
        embed = discord.Embed(
            title="Move Registered Successfully!",
            description=f"Move '{move_data.name}' has been registered for character '{character}'.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Move Type",
            value=move_type,
            inline=False
        )

        await ctx.send(embed=embed)
    
    except Exception as e:
        # General error handling for issues
        embed = discord.Embed(
            title="Error",
            description=f"An error occurred: {str(e)}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command()
async def custom_move(ctx, character: str, move: str, move_type: str):
    """Create a custom move for a user's character."""
    if move_type.lower() not in ["light", "medium", "heavy", "status", "unique"]:
        embed = discord.Embed(
            title="Invalid Move Type",
            description="Invalid move type. Choose from: Light, Medium, Heavy, Status, Unique.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Save custom move to the database
    move_entry = {
        "user_id": ctx.author.id,
        "character_name": character,
        "move_name": move.lower(),
        "move_type": move_type.capitalize()  # Capitalizing the move type
    }
    moves_collection.insert_one(move_entry)

    # Create an embed message
    embed = discord.Embed(
        title="Custom Move Registered!",
        description=f"Custom move '{move}' has been registered for character '{character}'.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Move Type",
        value=move_type.capitalize(),
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command()
async def moves(ctx, character: str):
    """List all moves registered for a character."""
    moves = list(moves_collection.find({"user_id": ctx.author.id, "character_name": character}))

    if moves:
        move_list = "\n".join([f"{move['move_name'].title()} ({move['move_type']})" for move in moves])
        embed = discord.Embed(
            title=f"Moves for '{character}'",
            description=move_list,
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="No Moves Found",
            description=f"No moves found for character '{character}'.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command()
async def forget(ctx, character: str, move: str):
    """Delete a move from a character."""
    result = moves_collection.delete_one({
        "user_id": ctx.author.id,
        "character_name": character,
        "move_name": move.lower()
    })

    if result.deleted_count > 0:
        embed = discord.Embed(
            title="Move Removed",
            description=f"Move '{move}' removed from character '{character}'.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="Error",
            description=f"Move '{move}' not found for character '{character}'.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    """Show all available commands in a pretty table-like format using Embed."""
    embed = discord.Embed(
        title="Command Menu",  # Title updated to "Command Menu"
        description="Here are all the available commands. When registering moves, use dashes (-) for spaces in move names.",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="&learn <character> <move>",
        value="Register a move for a character. The move's type will be categorized automatically. Example: `&learn Pikachu thunderbolt`.",
        inline=False
    )
    embed.add_field(
        name="&custom_move <character> <move> <move_type>",
        value="Register a custom move for a character with a specified type (Light, Medium, Heavy, Status, Unique). Example: `&custom_move Pikachu thunder-wave status`.",
        inline=False
    )
    embed.add_field(
        name="&moves <character>",
        value="List all moves registered for a particular character. Example: `&moves Pikachu`.",
        inline=False
    )
    embed.add_field(
        name="&forget <character> <move>",
        value="Delete a specific move from a character's list. Example: `&forget Pikachu thunderbolt`.",
        inline=False
    )

    await ctx.send(embed=embed)

# Run the bot
bot_token = os.getenv("DISCORD_BOT_TOKEN")
bot.run(bot_token)
