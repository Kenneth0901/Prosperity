import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("1.txt", sep=";", header=0)
df.set_index('timestamp', inplace=True)
products = df['product'].unique()

for product in products:
    data = df[df['product'] == product]
    data.to_pickle(f'{product}.pkl')
    print(data)