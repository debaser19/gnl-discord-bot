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
    # remove trailing whitespace from dates
    for matchup in matchups_list:
        matchup["date"] = matchup["date"].strip()

    # convert to datetime objects
    from datetime import datetime, timedelta

    new_matchups_list = []
    for matchup in matchups_list:
        try:
            matchup["time"] = datetime.strptime(matchup["time"], "%I:%M %p").time()
        except ValueError:
            matchup["time"] = datetime.strptime(matchup["time"], "%I:%M:%S %p").time()

        try:
            matchup["date"] = datetime.strptime(matchup["date"], "%a %d %b").date()
            matchup["date"] = matchup["date"].replace(year=datetime.now().year)
        except ValueError:
            # matchup["date"] = datetime.strptime(matchup["date"], "%a %-d %b")
            # matchup["date"] = matchup["date"].replace(year=datetime.now().year)
            print("no date")
            print(matchup["p1_name"])

        # combine date and time
        try:
            matchup_datetime = datetime.combine(matchup["date"], matchup["time"])
            matchup["datetime"] = matchup_datetime
        except Exception as e:
            # TODO: sometimes returning None value
            # combine() argument 2 must be datetime.time, not datetime.datetime
            print(e)
            matchup_datetime = None

        # remove matchups that have no date, are in the past, or more than one hour away
        if (
            matchup_datetime is not None
            and matchup_datetime > datetime.now()
            and matchup_datetime < datetime.now() + timedelta(hours=1)
        ):
            # print(f"Removing matchup: {matchup}")
            print(f"Adding matchup: {matchup}")
            new_matchups_list.append(matchup)

    # return matchups_list
    print(f"Matchups List: {matchups_list}")
    print(f"New: {new_matchups_list}")
    return new_matchups_list
