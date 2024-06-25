from flask import Flask, request, jsonify,render_template_string
import requests
from datetime import datetime
import pytz
import pandas as pd
import numpy as np

app = Flask(__name__)




def api_request(sport):

    # An api key is emailed to you when you sign up to a plan
    # Get a free API key at https://api.the-odds-api.com/
    API_KEY = '13584f961a551b823507d02641673702'

    SPORT = sport  # use the sport_key from the /sports endpoint below, or use 'upcoming' to see the next 8 games across all sports

    REGIONS = 'us'  # uk | us | eu | au. Multiple can be specified if comma delimited

    MARKETS = 'h2h'  # h2h | spreads | totals. Multiple can be specified if comma delimited

    ODDS_FORMAT = 'american'  # decimal | american

    DATE_FORMAT = 'iso'  # iso | unix

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    #
    # First get a list of in-season sports
    #   The sport 'key' from the response can be used to get odds in the next request
    #
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    # sports_response = requests.get(
    #     'https://api.the-odds-api.com/v4/sports',
    #     params={
    #         'api_key': API_KEY
    #     }
    # )

    # if sports_response.status_code != 200:
    #     print(f'Failed to get sports: status_code {sports_response.status_code}, response body {sports_response.text}')

    # else:
    #     print('List of in season sports:', sports_response.json())

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    #
    # Now get a list of live & upcoming games for the sport you want, along with odds for different bookmakers
    # This will deduct from the usage quota
    # The usage quota cost = [number of markets specified] x [number of regions specified]
    # For examples of usage quota costs, see https://the-odds-api.com/liveapi/guides/v4/#usage-quota-costs
    #
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    odds_response = requests.get(
        f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds',
        params={
            'api_key': API_KEY,
            'regions': REGIONS,
            'markets': MARKETS,
            'oddsFormat': ODDS_FORMAT,
            'dateFormat': DATE_FORMAT,
        }
    )

    if odds_response.status_code != 200:
        print(f'Failed to get odds: status_code {odds_response.status_code}, response body {odds_response.text}')

    else:
        odds_json = odds_response.json()
        print('Number of events:', len(odds_json))
        print(odds_json)

        # Check the usage quota
        print('Remaining requests', odds_response.headers['x-requests-remaining'])
        print('Used requests', odds_response.headers['x-requests-used'])
    return odds_json

def tuple_to_list(x):
    if isinstance(x, tuple):
        return list(x)
    else:
        return x
def list_to_tuple(x):
    if isinstance(x, list):
        return tuple(x)
    else:
        return x


def create_df(odds_json):
    bookmaker_data = {}
    game_list = []
    time_list = []
    # Iterate through odds_json
    for game in odds_json:
        home_team = game['home_team']
        away_team = game['away_team']
        game_list.append(home_team + " vs. " + away_team)
        time_list.append(game['commence_time'])

        for bookmaker in game['bookmakers']:
            bookmaker_name = bookmaker['title']
            if bookmaker_name not in bookmaker_data:
                bookmaker_data[bookmaker_name] = []  # home/away/draw

            # Initialize lists if bookmaker is not yet in the dictionary
            for market in bookmaker['markets']:
                game_odds = [None, None, None]
                for outcome in market['outcomes']:
                    if outcome['name'] == home_team:
                        game_odds[0] = int(outcome['price'])
                    if outcome['name'] == away_team:
                        game_odds[1] = int(outcome['price'])
                    elif outcome['name'] == 'Draw':
                        game_odds[2] = int(outcome['price'])
                    bookmaker_data[bookmaker_name].append(game_odds)
    utc_tz = pytz.utc
    # Define Eastern Standard Timezone (EST)
    est_tz = pytz.timezone('America/New_York')

    # Initialize an empty list to store converted times
    times_est = []

    # Loop through each UTC time string, convert to datetime object, and convert to EST
    for time_utc in time_list:
        dt_utc = datetime.strptime(time_utc, '%Y-%m-%dT%H:%M:%SZ')
        dt_utc = utc_tz.localize(dt_utc)
        dt_est = dt_utc.astimezone(est_tz)
        times_est.append(dt_est.strftime('%Y-%m-%d %H:%M:%S'))
    max_length = max(len(v) for v in bookmaker_data.values())

    # Fill missing spots with NaN
    for key in bookmaker_data:
        while len(bookmaker_data[key]) < max_length:
            bookmaker_data[key].append(np.nan)

    # Create DataFrame
    df = pd.DataFrame(bookmaker_data)
    # Return the element unchanged if it's not a list

    # Apply the function to convert lists to tuples
    df = df.applymap(list_to_tuple)

    # Drop duplicates based on tuples
    df = df.drop_duplicates()

    df = df.applymap(tuple_to_list)
    # Reset index
    df = df.reset_index(drop=True)

    # Make games index
    df.index = game_list

    # Add in times
    df.insert(loc=0, column='Date', value=times_est)

    return df


def get_rows(row, user_date):
    # Convert user_date to datetime
    date_format = "%Y-%m-%d"
    user_date = datetime.strptime(user_date, date_format).date()

    # Convert the 'date' column to datetime and extract the date part
    row_date = pd.to_datetime(row['Date']).date()

    # Check if the date matches the user_date
    return row_date == user_date


def process_odds_dataframe(odds_df):
    # Convert odds values from string to list of integers
    results = []
    bookmakers_names=odds_df.columns
    for index, game in odds_df.iterrows():
        final_dict={}
        match_name = index
        final_dict['Game']=match_name
        results_list=[]
#         print(match_name,row)
        home_odds_list=[]
        away_odds_list=[]
        draw_odds_list=[]
        for bookmaker in bookmakers_names:
            home_odds_list.append(game[bookmaker][0])
            away_odds_list.append(game[bookmaker][1])
            draw_odds_list.append(game[bookmaker][2])
        list_of_odds=[home_odds_list,away_odds_list,draw_odds_list]
        list_of_results=['home_win','away_win','draw']
        for lister,result_type in zip(list_of_odds,list_of_results):
            odds_dict={}
            lister_odds_list = pd.Series(lister)
            lister_max=lister_odds_list.max()
            indices = lister_odds_list[lister_odds_list == lister_max].index.tolist()
            lister_bookmaker=[bookmakers_names[i] for i in indices]
            odds_dict[result_type]=float(lister_max)
            odds_dict['bookmaker']=lister_bookmaker
            results_list.append(odds_dict)
        final_dict['Results']=results_list
        results.append(final_dict)
    return results

def get_best_odds(df,user_date,betting_sites=None):#Ex: Takes in date ex:2024-06-15, also takes in a list of betting sites that you use
    try:
        date_format = "%Y-%m-%d"
        user_date_dt = datetime.strptime(user_date, date_format).date()
    except ValueError as e:
        return "Invalid date format or value"
    matching_rows = df[df.apply(lambda row: get_rows(row, user_date), axis=1)]
    matching_rows=matching_rows.drop(columns='Date')
    if betting_sites is None:
        betting_sites = matching_rows.columns  # If no columns provided, keep all columns
    else:
        betting_sites = betting_sites
    matching_rows=matching_rows[betting_sites]
    if not matching_rows.empty:
        return process_odds_dataframe(matching_rows)
    else:
        return "Sorry no games found on this date"


def format_game_results(game_results):
    result_str = ""
    for game in game_results:
        teams = game['Game'].split(' vs. ')
        home_team = teams[0]
        away_team = teams[1]

        result_str += f"Game: {game['Game']}<br>Results:<br>"
        for result in game['Results']:
            if 'home_win' in result:
                outcome = home_team
                odds = result['home_win']
            elif 'away_win' in result:
                outcome = away_team
                odds = result['away_win']
            else:
                outcome = "Draw"
                odds = result['draw']

            result_str += f"  {outcome}: {odds:.1f} (Bookmakers: {', '.join(result['bookmaker'])})<br>"
        result_str += "<br>"  # Add a blank line for better readability

    return result_str


# def main():
#     json=api_request()
#     df = create_df(json)
#     date = input("Please enter the date of the game you want to look at (ex: '2024-06-15'):")
#     bookmakers_input = input(
#         "Please enter your bookmaker(seperated by comma) or enter nothing if you want to see all bookmakers:")
#
#     if bookmakers_input.lower() == 'none' or not bookmakers_input.strip():
#         bookmaker = None
#     else:
#         bookmaker = [bookmaker.strip() for bookmaker in bookmakers_input.split(',')]
#
#     try:
#         result = get_best_odds(df, date, bookmaker)
#         final_result=format_game_results(result)
#         return render_template_string(final_result)
#
#         # Display the result or handle it as needed
#     except Exception as e:
#         print("Sorry all bookmakers haven't released game odds yet")
#         return None


@app.route('/', methods=['GET', 'POST'])
def get_odds():
    if request.method == 'POST':
        # Get user inputs from form POST request
        sport = request.form.get('sport')
        date = request.form.get('date')
        bookmakers_input = request.form.get('bookmakers')
        json = api_request(sport)
        df = create_df(json)
        if bookmakers_input.lower() == 'none' or not bookmakers_input.strip():
            bookmaker = None
        else:
            bookmaker = [bookmaker.strip() for bookmaker in bookmakers_input.split(',')]

        try:
            result = get_best_odds(df, date, bookmaker)
            formatted_result = format_game_results(result)
            return formatted_result
        except Exception as e:
            return jsonify({'error': str(e)})


    return '''
        <form method="post">
            Sport: <input type="text" name="sport"><br>
            Date: <input type="text" name="date"><br>
            Bookmakers (comma separated): <input type="text" name="bookmakers"><br>
            <input type="submit" value="Submit"><br>
        </form>
    '''

if __name__ == '__main__':
    app.run()
