import gspread

import config


PLAYERS_SHEET = "Players"


def get_players():
    """
    Returns a list of all players in the Players sheet.
    """
    gc = gspread.service_account(filename=config.SERVICE_ACCOUNT_FILE)
    sh = gc.open_by_url(config.GNL_SHEET)
    players = sh.worksheet(PLAYERS_SHEET).get_all_records()

    return players


def get_matchups(week):
    """
    Returns a list of all matchups in the specified week.
    """
    gc = gspread.service_account(filename=config.SERVICE_ACCOUNT_FILE)
    sh = gc.open_by_url(config.GNL_SHEET)
    matchups = sh.worksheet(f"Week {week}").batch_get(["D6:I18"])[0]
    matchups += sh.worksheet(f"Week {week}").batch_get(["D22:I34"])[0]
    matchups += sh.worksheet(f"Week {week}").batch_get(["D38:I50"])[0]
    matchups_list = []
    for matchup in matchups:
        matchups_list.append(
            {
                "time": matchup[0],
                "date": matchup[1],
                "p1_name": matchup[2],
                "p1_score": matchup[3],
                "p2_score": matchup[4],
                "p2_name": matchup[5],
            }
        )
    return matchups_list


def update_score(week, p1_name, p2_name, p1_score, p2_score):
    gc = gspread.service_account(filename=config.SERVICE_ACCOUNT_FILE)
    sh = gc.open_by_url(config.GNL_SHEET)
    worksheet = sh.worksheet(f"Week {week}")
    players = get_players()
    for player in players:
        # check if p1_name is in the lowercase values of the player dict
        if (
            p1_name.lower() in player["Bnet"].lower()
            or p1_name.lower() in player["Bnet + Host"].lower()
            or p1_name.lower() in player["Discord"].lower()
        ):
            current_player = player
            break

    try:
        cell = worksheet.find(current_player["Bnet"])
        assert cell is not None
    except Exception:
        cell = worksheet.find(current_player["Bnet + Host"])

    cell_row = cell.row
    cell_col = cell.col

    if cell_col == 6:
        cell_values = [[p1_score, p2_score]]
    else:
        cell_values = [[p2_score, p1_score]]
    if (
        p2_name.lower() in worksheet.acell(f"F{cell_row}").value.lower()
        or p2_name.lower() in worksheet.acell(f"I{cell_row}").value.lower()
    ):
        worksheet.batch_update(
            [
                {
                    "range": f"G{cell_row}:H{cell_row}",
                    "values": cell_values,
                }
            ],
            raw=False,
        )
    else:
        raise Exception(
            f"Could not find matchup for week {week}: `{p1_name} vs {p2_name}`"
        )


def schedule(week, p1_name, p2_name, match_date, match_time):
    gc = gspread.service_account(filename=config.SERVICE_ACCOUNT_FILE)
    sh = gc.open_by_url(config.GNL_SHEET)
    worksheet = sh.worksheet(f"Week {week}")
    players = get_players()

    for player in players:
        # check if p1_name is in the lowercase values of the player dict
        if (
            p1_name.lower() in player["Bnet"].lower()
            or p1_name.lower() in player["Bnet + Host"].lower()
            or p1_name.lower() in player["Discord"].lower()
        ):
            current_player = player
            break

    try:
        cell = worksheet.find(current_player["Bnet"])
        assert cell is not None
    except Exception:
        cell = worksheet.find(current_player["Bnet + Host"])
    cell_row = cell.row
    if (
        p2_name.lower() in worksheet.acell(f"F{cell_row}").value.lower()
        or p2_name.lower() in worksheet.acell(f"I{cell_row}").value.lower()
    ):
        worksheet.batch_update(
            [
                {
                    "range": f"D{cell_row}:E{cell_row}",
                    "values": [[match_time, match_date]],
                },
            ],
            raw=False,
        )
    else:
        raise Exception(
            f"Could not find matchup for week {week}: `{p1_name} vs {p2_name}`"
        )


def find_uncasted_matches():
    gc = gspread.service_account(filename=config.SERVICE_ACCOUNT_FILE)
    sh = gc.open_by_url(config.GNL_SHEET)
    matchups_list = []

    for week in range(1, 6):
        print(f"Checking week {week}")
        matchups = sh.worksheet(f"Week {week}").batch_get(["B6:I18"])[0]
        matchups += sh.worksheet(f"Week {week}").batch_get(["B22:I34"])[0]
        matchups += sh.worksheet(f"Week {week}").batch_get(["B38:I50"])[0]
        for matchup in matchups:
            if (
                matchup[0] == ""  # caster is empty
                and matchup[2] != ""  # time is not empty
                and matchup[3] != ""  # date is not empty
                and matchup[5] == ""  # p1_score is empty
                and matchup[6] == ""  # p2_score is empty
            ):
                matchups_list.append(
                    {
                        "caster": matchup[0],
                        "time": matchup[2],
                        "date": matchup[3],
                        "p1_name": matchup[4],
                        "p2_name": matchup[7],
                    }
                )

    # convert to datetime objects
    from datetime import datetime, timedelta

    for matchup in matchups_list:
        try:
            matchup["time"] = datetime.strptime(matchup["time"], "%I:%M %p")
            matchup["time"] = matchup["time"].replace(year=datetime.now().year)
        except ValueError:
            matchup["time"] = datetime.strptime(matchup["time"], "%I:%M:%S %p")
            matchup["time"] = matchup["time"].replace(year=datetime.now().year)

        try:
            matchup["date"] = datetime.strptime(matchup["date"], "%a %d %b")
            matchup["date"] = matchup["date"].replace(year=datetime.now().year)
        except ValueError:
            matchup["date"] = datetime.strptime(matchup["date"], "%a %-d %b")
            matchup["date"] = matchup["date"].replace(year=datetime.now().year)

        # combine date and time
        try:
            matchup_datetime = datetime.combine(matchup["date"], matchup["time"])
        except Exception as e:
            # TODO: sometimes returning None value
            # combine() argument 2 must be datetime.time, not datetime.datetime
            print(e)
            matchup_datetime = None

        # check if the matchup is in the past or datetime is None
        if matchup_datetime == None:
            print(
                f"Removing match {matchup['p1_name']} vs {matchup['p2_name']} for None value"
            )
            matchups_list.remove(matchup)
        elif matchup_datetime < datetime.now():
            print(
                f"Removing matchup {matchup['p1_name']} vs {matchup['p2_name']} for being in the past"
            )
            matchups_list.remove(matchup)
        # check if matchup in more than 1 hour away
        elif matchup_datetime - datetime.now() > timedelta(hours=1):
            print(
                f"Removing matchup {matchup['p1_name']} vs {matchup['p2_name']} for being more than 1 hour away"
            )
            matchups_list.remove(matchup)

        # return matchups_list
    return matchups_list


for match in find_uncasted_matches():
    print(match)
