from discord.ext import commands, tasks
import discord
import requests
import gspread
import pandas as pd
from datetime import datetime
import json

import config

bot = commands.Bot(command_prefix="!")


def get_race(race):
    races = ["random", "human", "orc", "nightelf", "undead"]
    if race in races:
        match race:
            case "random":
                return 0
            case "human":
                return 1
            case "orc":
                return 2
            case "nightelf":
                return 4
            case "undead":
                return 8
    else:
        return 0


def get_race_string(race):
    races = [0, 1, 2, 4, 8]
    if race in races:
        match race:
            case 0:
                return "Random"
            case 1:
                return "Human"
            case 2:
                return "Orc"
            case 4:
                return "Night Elf"
            case 8:
                return "Undead"
    else:
        return 0


def parse_player(player, matches):
    match player.lower():
        case "a":
            return matches[0][0]
        case "b":
            return matches[0][1]
        case "c":
            return matches[1][0]
        case "d":
            return matches[1][1]
        case "e":
            return matches[2][0]
        case "f":
            return matches[2][1]


def get_gnl_sheet():
    gc = gspread.service_account(filename="portfolio-update-3ef72f62cf31.json")
    sh = gc.open_by_url(
        "https://docs.google.com/spreadsheets/d/1SbEa3lu_G87AILFyywa4Ib44bR8fs-gLlqQlrfa3sPM"
    )
    worksheet = sh.get_worksheet(2)

    df = pd.DataFrame(worksheet.get("A:P"))
    df.columns = df.iloc[0]
    df = df[1:]
    df.head()
    return df


def get_betting_sheet():
    gc = gspread.service_account(filename="portfolio-update-3ef72f62cf31.json")
    sh = gc.open_by_url(
        "https://docs.google.com/spreadsheets/d/1JGumsXhaX3ptv-cdSWtcAG7MWLz6O0HO6VQC-z7RSIE/"
    )
    return sh.get_worksheet(0)


def get_matchup_sheet():
    gc = gspread.service_account(filename="portfolio-update-3ef72f62cf31.json")
    sh = gc.open_by_url(
        "https://docs.google.com/spreadsheets/d/1JGumsXhaX3ptv-cdSWtcAG7MWLz6O0HO6VQC-z7RSIE/"
    )
    return sh.get_worksheet(1)


@bot.command(name="mmr")
async def mmr(ctx: commands.Context, w3c_username, w3c_race):
    race = get_race(w3c_race)
    username = w3c_username.replace("#", "%23")
    res = requests.get(
        config.W3C_URL + username + "/game-mode-stats?gateWay=20&season=10"
    )
    for item in res.json():
        if item["gameMode"] == 1 and item["race"] == race:
            mmr = item["mmr"]

    print(f"Responding to {ctx.author}")
    embed = discord.Embed(
        title=f"{w3c_username} - {w3c_race}", colour=0xE45B9D, description=f"{mmr}"
    )

    await ctx.send(embed=embed)


@bot.command(name="stats")
async def stats(ctx: commands.Context, w3c_username, season=None):
    username = w3c_username.replace("#", "%23")
    if season is None:
        season = 12
    res = requests.get(
        config.W3C_URL + username + f"/game-mode-stats?gateWay=20&season={season}"
    )
    race_list = []

    for item in res.json():
        if item["gameMode"] == 1:
            race_stats = {
                "race": item["race"],
                "mmr": item["mmr"],
                "wins": item["wins"],
                "losses": item["losses"],
                "winrate": item["winrate"],
            }
            race_list.append(race_stats)

    content_string = ""
    for race in race_list:
        content_string += f"""
            **Race**: {get_race_string(race['race'])}
            **MMR**: {race['mmr']}
            **Wins**: {race['wins']}
            **Losses**: {race['losses']}
            **Winrate**: {round(race['winrate'], 2)}
        """

    embed = discord.Embed(
        title=f'{username.replace("%23", "#")} Stats',
        colour=0xE45B9D,
        description=content_string,
    )

    # file = discord.File('images/fom.png', filename='fom.png')
    w3c_logo = "https://w3champions.com/favicon.ico"
    embed.set_author(name=f"W3Champions Season {season}", icon_url=w3c_logo)

    await ctx.send(embed=embed)


@bot.command(name="bet")
async def bet(ctx: commands.Context, user, points):
    # convert points to int and validate input
    try:
        points = int(points)
    except:
        await ctx.reply(
            """Invalid bet: Please choose corresponding letter (A-F) to specify player.
            **Usage: `!bet <player_letter> <points>`**
            `!listmatches` to see matchups"""
        )
        return 1
    message = await ctx.reply("Processing...")
    # get current time and date for when bet was placed
    current_time = datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")
    # get the current sheet and store values in matches
    matchup_sheet = get_matchup_sheet()
    matches = matchup_sheet.get_all_values()
    print(matches)
    sh = get_betting_sheet()
    values = sh.get_all_values()
    print(values)

    # check if user has already places 3 bets
    bet_count = 0
    for row in values:
        if row[0] == str(ctx.author):
            bet_count += 1

    # set list of valid choices
    valid_choices = ["a", "b", "c", "d", "e", "f"]
    if user.lower() in valid_choices:
        try:
            player = parse_player(user, matches)
        except:
            await ctx.reply("Featured matches not set yet. Try again later")
            return 2
        if points <= 0 or points > 3:
            await ctx.reply("Invalid bet: Points must be between 1 and 3")
            await message.delete()
        # if bet_count >= 3, reject bet and inform user
        elif bet_count >= 3:
            # get list of users current bets
            current_bets = []
            for row in values:
                if row[0] == str(ctx.author):
                    current_bets.append(row)

            # create a string of current bets
            current_bets_string = ""
            current_bet_id = 1
            for bet in current_bets:
                current_bets_string += (
                    f"{current_bet_id}) **Winner**: {bet[1]} **Wager**: {bet[2]}\n"
                )
                current_bet_id += 1

            await ctx.reply(
                "You have already placed 3 bets. Remove a bet with `!removebet <bet_id>`\nCurrent bets:\n"
                + current_bets_string
            )
            await message.delete()
        # elif any(str(ctx.author) in value for value in values):
        #     res = sh.find(str(ctx.author))
        #     cell = (res.row, res.col)
        #     print(f'Found {str(ctx.author)} at {cell}')
        #     sh.update_cell(res.row, 2, player)
        #     sh.update_cell(res.row, 3, points)
        #     sh.update_cell(res.row, 4, current_time)
        #     await ctx.reply(f'''
        #     You have already voted on a matchup this week. Updating your previous entry.
        #     {ctx.author} bet {points} points on {parse_player(user, matches)}
        #     ''')
        #     await message.delete()
        else:
            # reject bet if author has already bet on given matchup
            for row in values:
                if row[0] == str(ctx.author) and row[1] == player:
                    await message.delete()
                    await ctx.reply(
                        f"You have already bet on {player}. Choose another outcome."
                    )
                    return 1

            author = str(ctx.author)
            print(f"Responding to {author}")
            bet_content = [author, player, points, current_time]
            sh.append_row(bet_content)
            await message.delete()
            emoji = "<:RiggedGNL:833837273081577472>"
            await ctx.message.add_reaction(emoji)
            await ctx.reply(f"{ctx.author} bet {points} points on {player}")
    else:
        await ctx.reply(
            """Invalid bet: Please choose corresponding letter (A-F) to specify player.
            **Usage: `!bet <player_letter> <points>**
            `!listmatches` to see matchups"""
        )


# create a command to list the total amount of points wagered on each outcome
@bot.command(name="spread")
async def spread(ctx: commands.Context):
    # get unique list of players
    sh = get_betting_sheet()
    values = sh.get_all_records()
    players = []
    for row in values:
        if row["Outcome"] not in players:
            players.append(row["Outcome"])

    # tally up points wagered on each player
    player_points = {}
    for player in players:
        player_points[player] = 0
        for row in values:
            if row["Outcome"] == player:
                player_points[player] += int(row["Points Wagered"])

    # sort the players by points wagered
    sorted_players = sorted(player_points.items(), key=lambda x: x[1], reverse=True)

    # create a string of players and their points
    player_points_string = ""
    for player in sorted_players:
        player_points_string += f"{player[0]}: {player[1]}\n"

    # create discord embed and reply with player points
    embed = discord.Embed(
        title="Total Points Wagered", colour=0xE45B9D, description=player_points_string
    )
    await ctx.send(embed=embed)


@bot.command(name="createbet")
async def createbet(ctx: commands.Context, p1_name, p1_race, p2_name, p2_race):
    sh = get_matchup_sheet()
    sh.append_row([p1_name, p2_name])

    embed = discord.Embed(
        title=f"{p1_name} ({p1_race}) vs {p2_name} ({p2_race})",
        colour=0xE45B9D,
        description=f"Place your bets with `!bet <player> <points>`",
    )

    await ctx.send(embed=embed)


# command to remove a user's bet, only allowing user to delete their own bets
@bot.command(name="removebet")
async def removebet(ctx: commands.Context, bet_id):
    bet_id = int(bet_id)
    # loop through user's bets and remove the one with the given bet_id
    sh = get_betting_sheet()
    values = sh.get_all_values()
    current_row = 1
    users_current_bet_id = 0
    for row in values:
        if row[0] == str(ctx.author):
            ctx.reply(f"{ctx.author} row {current_row} bet_id {users_current_bet_id}")
            users_current_bet_id += 1
            if bet_id == users_current_bet_id:
                sh.delete_row(current_row)
                await ctx.reply(f"Removed bet {bet_id}")
                return
        current_row += 1

    await ctx.reply(f"You do not have a bet with ID {bet_id}")


@bot.command(name="listmatches")
async def listmatches(ctx: commands.Context):
    matchup_sheet = get_matchup_sheet()
    matches = matchup_sheet.get_all_values()

    embed_content = f"""
        1) **(A)** {matches[0][0]} vs **(B)** {matches[0][1]}

        2) **(C)** {matches[1][0]} vs **(D)** {matches[1][1]}
        
        3) **(E)** {matches[2][0]} vs **(F)** {matches[2][1]}
        """

    embed = discord.Embed(
        title="Featured betting Matches",
        author="Gym Newbie League",
        description=embed_content,
    )

    await ctx.send(embed=embed)


@bot.command(name="clearbets")
async def clearbets(ctx: commands.Context):
    print(f"{ctx.author} used command `!clearbets`")
    sh = get_betting_sheet()
    try:
        sh.resize(rows=1)
        sh.resize(rows=500)
        print(f"Bets cleared by {ctx.author}")
        await ctx.reply(f"Bets cleared by {ctx.author}")
    except Exception as e:
        await ctx.reply(f"Error clearing bets: {e}")


@bot.command(name="clearmatches")
async def clearmatches(ctx: commands.Context):
    print(f"{ctx.author} used command `!clearmatches`")
    sh = get_matchup_sheet()
    try:
        sh.resize(rows=1)
        sh.resize(rows=501)
        sh.delete_rows(1)
        print(f"Matches cleared by {ctx.author}")
        await ctx.reply(f"Matches cleared by {ctx.author}")
    except Exception as e:
        await ctx.reply(f"Error clearing matches: {e}")


# GNL Score commands
@bot.command(name="gnlscore")
# @commands.has_role("GNL Captains & Coaches")
async def gnlscore(
    ctx: commands.Context, week_num, p1_name, p2_name, p1_score, p2_score
):
    print(f"{ctx.author} used command `!gnlscore`")
    # check if message has an attachment
    if not ctx.message.attachments:
        await ctx.reply("Please attach the replays for the match")
        return

    import gnl_commands

    try:
        gnl_commands.update_score(week_num, p1_name, p2_name, p1_score, p2_score)
        await ctx.reply(f"Score updated: {p1_name} {p1_score} - {p2_score} {p2_name}")
    except Exception as e:
        await ctx.reply(f"Error updating score - could not find player: {e}")


@bot.command(name="gnlschedule")
# @commands.has_role("GNL Captains & Coaches")
async def gnlschedule(
    ctx: commands.Context, week_num, p1_name, p2_name, match_date, match_time
):
    print(f"{ctx.author} used command `!gnlschedule`")
    import gnl_commands

    # convert match_date and match_time to datetime object
    from datetime import datetime

    # match_time = match_time[:2] + ":" + match_time[2:]

    match_date = datetime.strptime(match_date, "%m/%d/%Y")
    match_time = datetime.strptime(match_time, "%H%M")

    # convert match_date and match_time to google sheet format
    match_date = match_date.strftime("%a %d %b")
    match_time = match_time.strftime("%I:%M %p")

    try:
        gnl_commands.schedule(week_num, p1_name, p2_name, match_date, match_time)
        await ctx.reply(
            f"Week {week_num} match scheduled: {p1_name} vs {p2_name} - {match_date} @ {match_time}"
        )
    except Exception as e:
        await ctx.reply(f"Error updating match schedule - could not find player: {e}")


@bot.command()
async def toUnicode(ctx, emoji):
    await ctx.send(f"{emoji} **{json.dumps(emoji)[1:-1]}**")


@bot.command(name="lookup")
async def lookup(ctx: commands.Context, user):
    df = get_gnl_sheet()
    find = df.loc[df["Player"].str.lower() == user.lower()]
    points = find["Total Points"].values[0]

    await ctx.reply(f"{user} has {points} points")


@bot.command(name="upcoming")
async def upcoming(ctx: commands.Context):
    message = await ctx.reply("Looking for upcoming matches...")
    import gnl_commands

    upcoming_matches = gnl_commands.get_upcoming_matches()
    if len(upcoming_matches) > 0:
        print("Listing matches upcoming in the next 24 hours")
        result = ""
        for match in upcoming_matches:
            # convert match["datetime"] to string containing date and time
            # match_date = match["datetime"].strftime("%a %d %b @ %I:%M %p EST")
            # convert match["datetime"] to unix timestamp
            match_date = int(match["datetime"].timestamp())
            match_date = f"<t:{match_date}:f>"
            result += f"**{match['p1_name']}** vs **{match['p2_name']}** - {match_date}"

            if match["caster"] != "":
                result += f" - <https://twitch.tv/{match['caster']}>\n"
            else:
                result += f" - No caster scheduled yet\n"

        await message.delete()
        await ctx.reply(
            f"**Matches scheduled in the next 24 hours**:\nMatch times should be automatically converted to your timezone\n\n{result}"
        )
    else:
        await message.delete()
        await ctx.reply("No matches scheduled in the next 24 hours")
        print("No upcoming matches without caster")


@tasks.loop(hours=12)
async def check_scheduled_matches():
    channel = bot.get_channel(689941824424771712)  # gym-youtube channel
    # channel = bot.get_channel(950602007700447252)  # personal gnl-bot channel
    caster_role = "<@&569926408932032513>"
    import gnl_commands

    upcoming_matches = gnl_commands.get_upcoming_matches()
    if len(upcoming_matches) > 0:
        print("Listing matches upcoming in the next 24 hours")
        result = ""
        for match in upcoming_matches:
            # convert match["datetime"] to string containing date and time
            # match_date = match["datetime"].strftime("%a %d %b @ %I:%M %p EST")
            # convert match["datetime"] to unix timestamp
            match_date = int(match["datetime"].timestamp())
            match_date = f"<t:{match_date}:f>"
            result += f"**{match['p1_name']}** vs **{match['p2_name']}** - {match_date}"

            if match["caster"] != "":
                result += f" - <https://twitch.tv/{match['caster']}>\n"
            else:
                result += f" - No {caster_role} scheduled yet\n"

        await channel.send(
            f"**Matches scheduled in the next 24 hours**:\nMatch times should be automatically converted to your timezone\n\n{result}"
        )
    else:
        print("No upcoming matches without caster")


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    check_scheduled_matches.start()


DISCORD_TOKEN = config.DISCORD_TOKEN
W3C_URL = config.W3C_URL
bot.run(DISCORD_TOKEN)
