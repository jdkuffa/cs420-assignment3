
import pandas as pd

df = pd.read_csv('data.csv')
df.head()

output_db_cols = [
    "Problem", "Prompt Strategy", "Prompt","Output Model 1: OpenAI GPT-4", "Output Model 2: Mistral Large"
    ]

output_db = pd.DataFrame(columns=pd.Index(output_db_cols))

for i in range(len(df)):
  row = df.iloc[i]
  problem = row['Problem']
  code = row["Code Input"]
  prompt1 = row['Prompt 1'] + code
  prompt1strat = row['Prompt 1 Strategy'].lower()
  prompt2strat = row['Prompt 2 Strategy'].lower()
  prompt2 = row['Prompt 2'] + code
  output_db.loc[len(output_db)] = [problem, prompt1strat,  prompt1, " ", " "]
  output_db.loc[len(output_db)] = [problem, prompt2strat, prompt2, " ", " "]

output_db.to_csv('output.csv', index=False)