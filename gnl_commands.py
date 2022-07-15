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
    # TODO: scores will always update on the sheet in the order they are entered
    # regardless of which player is entered first.
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
    print(current_player["Bnet"])
    cell_row = cell.row
    if (
        p2_name.lower() in worksheet.acell(f"F{cell_row}").value.lower()
        or p2_name.lower() in worksheet.acell(f"I{cell_row}").value.lower()
    ):
        worksheet.batch_update(
            [
                {
                    "range": f"G{cell_row}:H{cell_row}",
                    "values": [[p1_score, p2_score]],
                }
            ]
        )
    else:
        print("Player not found.")


def main():
    # players = get_players()
    # for player in players:
    #     print(player)

    # matchups = get_matchups(1)
    # for matchup in matchups:
    #     print(matchup)
    update_score(1, "debaser", "serai", 1, 2)


main()
