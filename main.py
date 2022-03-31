from discord.ext import commands
import discord
import requests
import gspread
import pandas as pd
from datetime import datetime
import json

import config

bot = commands.Bot(command_prefix="!")


def get_race(race):
    races = ['random', 'human', 'orc', 'nightelf', 'undead']
    if race in races:
        match race:
            case 'random':
                return 0
            case 'human':
                return 1
            case 'orc':
                return 2
            case 'nightelf':
                return 4
            case 'undead':
                return 8
    else:
        return 0

    
def get_race_string(race):
    races = [0, 1, 2, 4, 8]
    if race in races:
        match race:
            case 0:
                return 'Random'
            case 1:
                return 'Human'
            case 2:
                return 'Orc'
            case 4:
                return 'Night Elf'
            case 8:
                return 'Undead'
    else:
        return 0


def parse_player(player, matches):
    match player.lower():
        case 'a':
            return matches[0][0]
        case 'b':
            return matches[0][1]
        case 'c':
            return matches[1][0]
        case 'd':
            return matches[1][1]
        case 'e':
            return matches[2][0]
        case 'f':
            return matches[2][1]


def get_gnl_sheet():
    gc = gspread.service_account(filename='portfolio-update-3ef72f62cf31.json')
    sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1SbEa3lu_G87AILFyywa4Ib44bR8fs-gLlqQlrfa3sPM")
    worksheet = sh.get_worksheet(2)

    df = pd.DataFrame(worksheet.get('A:P'))
    df.columns = df.iloc[0]
    df = df[1:]
    df.head()
    return df


def get_betting_sheet():
    gc = gspread.service_account(filename='portfolio-update-3ef72f62cf31.json')
    sh = gc.open_by_url('https://docs.google.com/spreadsheets/d/1JGumsXhaX3ptv-cdSWtcAG7MWLz6O0HO6VQC-z7RSIE/')
    return sh.get_worksheet(0)


def get_matchup_sheet():
    gc = gspread.service_account(filename='portfolio-update-3ef72f62cf31.json')
    sh = gc.open_by_url('https://docs.google.com/spreadsheets/d/1JGumsXhaX3ptv-cdSWtcAG7MWLz6O0HO6VQC-z7RSIE/')
    return sh.get_worksheet(1)


# @bot.event
# async def on_message(message):
#     rigged_emote = '<:RiggedGNL:833837273081577472>'
#     if 'rigged' in message.content.lower() or 'rigging' in message.content.lower():
#         print(f'Reacting with Rigged emote to {message.author}')
#         await message.add_reaction(rigged_emote)


@bot.command(name="mmr")
async def mmr(ctx: commands.Context, w3c_username, w3c_race):
    race = get_race(w3c_race)
    username = w3c_username.replace('#', '%23')
    res = requests.get(config.W3C_URL + username + '/game-mode-stats?gateWay=20&season=10')
    for item in res.json():
        if item['gameMode'] == 1 and item['race'] == race:
            mmr = item['mmr']

    print(f'Responding to {ctx.author}')
    embed = discord.Embed(
        title=f'{w3c_username} - {w3c_race}',
        colour=0xE45B9D,
        description=f'{mmr}')
    
    await ctx.send(embed=embed)


@bot.command(name='stats')
async def stats(ctx: commands.Context, w3c_username):
    username = w3c_username.replace('#', '%23')
    res = requests.get(config.W3C_URL + username + '/game-mode-stats?gateWay=20&season=10')
    race_list = []

    for item in res.json():
        if item['gameMode'] == 1:
            race_stats = {
                'race': item['race'],
                'mmr': item['mmr'],
                'wins': item['wins'],
                'losses': item['losses'],
                'winrate': item['winrate']
            }
            race_list.append(race_stats)

    content_string = ''
    for race in race_list:
        content_string += f'''
            **Race**: {get_race_string(race['race'])}
            **MMR**: {race['mmr']}
            **Wins**: {race['wins']}
            **Losses**: {race['losses']}
            **Winrate**: {round(race['winrate'], 2)}
        '''
    
    embed = discord.Embed(
        title=f'{username.replace("%23", "#")} Stats',
        colour=0xE45B9D,
        description=content_string
    )

    # file = discord.File('images/fom.png', filename='fom.png')
    fom_logo = 'https://s3.amazonaws.com/challonge_app/organizations/images/000/143/459/large/discord_icon.png?1641342459'
    embed.set_author(name='Fountain of Manner', icon_url=fom_logo)
    embed.set_thumbnail(url=fom_logo)
    embed.set_image(url=fom_logo)

    await ctx.send(embed=embed)


@bot.command(name="bet")
async def bet(ctx: commands.Context, user, points):
    try:
        points = int(points)
    except:
        await ctx.reply(
            '''Invalid bet: Please choose corresponding letter (A-F) to specify player.
            **Usage: `!bet <player_letter> <points>`**
            `!listmatches` to see matchups'''
            )
        return 1
    message = await ctx.reply('Processing...')
    current_time = datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')
    matchup_sheet = get_matchup_sheet()
    matches = matchup_sheet.get_all_values()
    print(matches)
    sh = get_betting_sheet()
    values = sh.get_all_values()
    print(values)
    valid_choices = ['a', 'b', 'c', 'd', 'e', 'f']
    if user.lower() in valid_choices:
        try:
            player = parse_player(user, matches)
        except:
            await ctx.reply('Featured matches not set yet. Try again later')
            return 2
        if points <= 0 or points > 5:
            await ctx.reply('Invalid bet: Points must be between 1 and 5')
            await message.delete()
        elif any(str(ctx.author) in value for value in values):
            res = sh.find(str(ctx.author))
            cell = (res.row, res.col)
            print(f'Found {str(ctx.author)} at {cell}')
            sh.update_cell(res.row, 2, player)
            sh.update_cell(res.row, 3, points)
            sh.update_cell(res.row, 4, current_time)
            await ctx.reply(f'''
            You have already voted on a matchup this week. Updating your previous entry.
            {ctx.author} bet {points} points on {parse_player(user, matches)}
            ''')
            await message.delete()
        else:
            author = str(ctx.author)
            print(f'Responding to {author}')
            bet_content = [author, player, points, current_time]
            sh.append_row(bet_content)
            await message.delete()
            emoji = '<:RiggedGNL:833837273081577472>'
            await ctx.message.add_reaction(emoji)
            await ctx.reply(f'{ctx.author} bet {points} points on {player}')
    else:
        await ctx.reply(
            '''Invalid bet: Please choose corresponding letter (A-F) to specify player.
            **Usage: `!bet <player_letter> <points>**
            `!listmatches` to see matchups'''
            )


@bot.command(name='createbet')
async def createbet(ctx: commands.Context, p1_name, p1_race, p2_name, p2_race):
    sh = get_matchup_sheet()
    sh.append_row([p1_name, p2_name])

    embed = discord.Embed(
        title=f'{p1_name} ({p1_race}) vs {p2_name} ({p2_race})',
        colour=0xE45B9D,
        description=f'Place your bets with `!bet <player> <points>`')
    
    await ctx.send(embed=embed)


@bot.command(name='listmatches')
async def listmatches(ctx: commands.Context):
    matchup_sheet = get_matchup_sheet()
    matches = matchup_sheet.get_all_values()

    embed_content = f'''
        1) **(A)** {matches[0][0]} vs **(B)** {matches[0][1]}

        2) **(C)** {matches[1][0]} vs **(D)** {matches[1][1]}
        
        3) **(E)** {matches[2][0]} vs **(F)** {matches[2][1]}
        '''

    embed = discord.Embed(
        title='Featured betting Matches',
        author='Gym Newbie League',
        description=embed_content
    )

    await ctx.send(embed=embed)


@bot.command(name='clearbets')
async def clearbets(ctx: commands.Context):
    sh = get_betting_sheet()
    try:
        sh.resize(rows=1)
        sh.resize(rows=500)
        print(f'Bets cleared by {ctx.author}')
        await ctx.reply(f'Bets cleared by {ctx.author}')
    except Exception as e:
        await ctx.reply(f'Error clearing bets: {e}')


@bot.command(name='clearmatches')
async def clearmatches(ctx: commands.Context):
    sh = get_matchup_sheet()
    try:
        sh.resize(rows=1)
        sh.resize(rows=501)
        sh.delete_rows(1)
        print(f'Matches cleared by {ctx.author}')
        await ctx.reply(f'Matches cleared by {ctx.author}')
    except Exception as e:
        await ctx.reply(f'Error clearing matches: {e}')


@bot.command()
async def toUnicode(ctx, emoji):
    await ctx.send(f'{emoji} **{json.dumps(emoji)[1:-1]}**')


@bot.command(name='lookup')
async def lookup(ctx: commands.Context, user):
    df = get_gnl_sheet()
    find = df.loc[df['Player'].str.lower()==user.lower()]
    points = find['Total Points'].values[0]
    
    await ctx.reply(f'{user} has {points} points')


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

DISCORD_TOKEN = config.DISCORD_TOKEN
W3C_URL = config.W3C_URL
bot.run(DISCORD_TOKEN)