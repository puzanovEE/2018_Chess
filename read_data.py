"""
author: Andrey Puzanov
Created on Tue Jan  1 10:45:25 2019

    This script reads the date out of .pgn file that was provided by chess.com
and creates a dataframe with summary statistics for the 2018.
    Country location for each player is being taken from his/her chess.com
account page. 
    The script runs about 10 minutes depending on the quality of yuor internet 
connection.
    The result is saved into chesscom_games.csv file.
"""

import re
import numpy as np
import pandas as pd


filename = 'chesscom_games.pgn'
list_of_data = []

count = 0
# Reading data from file into a list and clearing out moves sequence for 
# each game except for the first move
with open(filename, 'r') as fin:
    for line in fin:
        if (line == '[Event "Live Chess"]\n'):
            count = count + 1
            for i in range (0, 14):
                if line[0][0] == '[':
                    line = re.sub('["["]', '', line)
                    line = re.sub(']', '', line)
                    list_of_data.append(' '.join((line.split()[1:])))
                elif line[0][0] == '1':
                    m = re.search("1. (.+?) {", line)
                    if m:
                        list_of_data.append(m.group(1))
                line = fin.readline()                
fin.close()

# Creating a NumPy array
num_of_columns = 13
num_of_lines = int(len(list_of_data)/num_of_columns)
array_of_data = np.array(list_of_data)
array_of_data = array_of_data.reshape(num_of_lines, num_of_columns)
# Creating DataFrame
df = pd.DataFrame(array_of_data, columns = ["Event", "Site", "Date", 
        "Round", "White", "Black", "Score", "WhiteElo",
        "BlackElo", "Time Control", "Time", "Comment", "Opening move"])

# Adding Color column
df['Color'] = df['White'].apply(
        lambda name: 'White' if name == 'apuzanov' else 'Black')
# Adding Opponent name column
df['Opponent'] = ''
for i in range (0, num_of_lines):
    if df['White'][i] != 'apuzanov':
        df['Opponent'][i] = df['White'][i]
    else:
        df['Opponent'][i] = df['Black'][i]
df['Opponent location'] = '' # This column will be filled out later
# Adding Rank columns
df['Current Rank'] = ""
df['Opponent Rank'] = ""
for i in range (0, num_of_lines):
    if df['Color'][i] == 'White':
        df['Current Rank'][i] = df['WhiteElo'][i]
        df['Opponent Rank'][i] = df['BlackElo'][i]
    else:
        df['Current Rank'][i] = df['BlackElo'][i]
        df['Opponent Rank'][i] = df['WhiteElo'][i]
# Adding Result column
df['Result'] = ""
for i in range (0, num_of_lines):
    if df['Score'][i] == '1/2-1/2':
        df['Result'][i] = 'Draw'
    elif (df['Score'][i] == '1-0') and (df['Color'][i] == 'White'):
        df['Result'][i] = 'Won'
    elif (df['Score'][i] == '0-1') and (df['Color'][i] == 'Black'):
        df['Result'][i] = 'Won'
    else:
        df['Result'][i] = 'Lost'
# Adding Reason column
df['Reason'] = ""
for i in range (0, num_of_lines):
    if df['Result'][i] == 'Draw':
        if df['Comment'][i].split()[-1] == 'material':
            df['Reason'][i] = 'Insufficient material'
        elif df['Comment'][i].split()[-1] == 'stalemate':
            df['Reason'][i] = 'Stalemate'
        else:
            df['Reason'][i] = 'Agreement'
    elif df['Comment'][i].split()[-1] == 'checkmate':
        df['Reason'][i] = 'Checkmate'
    elif df['Comment'][i].split()[-1] == 'resignation':
        df['Reason'][i] = 'Resignation'
    elif df['Comment'][i].split()[-1] == 'time':
        df['Reason'][i] = 'Time'
    else:
        df['Reason'][i] = 'Game abandoned'

# Adjusting the time From US/Pacific to Europe/Moscow timezone, also
# accounting for daylight savings time correctly
from datetime import datetime
from pytz import timezone
df['Hour'] = ''
for i in range (0, num_of_lines):
    date_str = df['Date'][i] + ' ' + df['Time'][i][:8].replace(' ', '')    
    time_original = datetime.strptime(date_str, '%Y.%m.%d %H:%M:%S')
    time_pacific = timezone('US/Pacific').localize(time_original)    
    fmt_time = '%H:%M:%S'
#    fmt_date = '%Y.%m.%d'
    time_moscow = time_pacific.astimezone(timezone('Europe/Moscow'))
    df['Time'][i] = time_moscow.strftime(fmt_time)
#    df['Date'][i] = time_moscow.strftime(fmt_date)
    df['Hour'][i] = time_moscow.strftime('%H')
# I have commented out date conversion, because the dates provided by chess.com
# in the .pgn file don't match the dates on the webpage for several games. As
# a result several matches (for instance #29) are placed in chronological order,
# but the time/date don't confirm that.
# For the purpose of having games in chronological order I am leaving dates 
# unchanged and only adjust time. Otherwise this brakes later calculations that
# are based on date. To take care of this issue, I would have to parse the 
# webpages for data instead of reading it from the .pgn file. However, this 
# should be OK for the purpose of this project.

# Counting the number of games played at a certain date and the ordial number
# for each game that day. Bedtime can be set
bedtime = 3 # Bedtime set to 3 A.M.
df['Previously played that day'] = '0'
game_number = 0
current_date = df['Date'][0]
for i in range (0, num_of_lines):
    if df['Date'][i] == df['Date'][0]:
        df['Previously played that day'][i] = 0
    else:
        if (df['Date'][i] != current_date) and (int(df['Hour'][i]) > bedtime):
            df['Previously played that day'][i] = 0
            current_date = df['Date'][i]
            game_number = 0
        else:
            game_number = game_number + 1
            df['Previously played that day'][i] = game_number

# Filling out "Opponent location" colomn
import re
import urllib.request
from bs4 import BeautifulSoup

headers= {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 \
          (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,\
           application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}

list_of_countries = []

for i in range (0, len(df['Opponent'])):

    url = 'https://www.chess.com/member/'+ df['Opponent'][i]
        
    request=urllib.request.Request(url,None,headers)
    response = urllib.request.urlopen(request)
    html = response.read()
            
    soup = BeautifulSoup(html)
            
    tip_string = str(
            soup.find('div', {'class': 'overview'}).find('h1').contents)
    m = re.search('tip="(.+?)"', tip_string)
    if m:
        country_name = m.group(1)
    list_of_countries.append(country_name)
    response.close()
    
df['Opponent location'] = list_of_countries

# Deleting old and unnecessary columns & reordering columns
df = df.drop(
        columns=['White', 'Black', 'Score', 'WhiteElo', 'BlackElo', 'Comment'])
df = df[['Event', 'Site', 'Date', 'Round', 'Time Control', 'Time', 'Color',
         'Opening move', 'Opponent', 'Opponent location', 'Current Rank',
         'Opponent Rank', 'Result', 'Reason', 'Hour',
         'Previously played that day',]]
# Saving the DataFrame
df.to_csv('chesscom_games.csv')
