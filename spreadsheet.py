import gspread
import pandas as pd

gc = gspread.service_account(filename='portfolio-update-3ef72f62cf31.json')

sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1SbEa3lu_G87AILFyywa4Ib44bR8fs-gLlqQlrfa3sPM")
worksheet = sh.get_worksheet(2)

df = pd.DataFrame(worksheet.get('A:P'))
df.columns = df.iloc[0]
df = df[1:]
df.head()
# print(df)

user = 'YungHofer'
find = df.loc[df['Player'].str.lower()==user.lower()]
points = find['Total Points'].values[0]
print(points)