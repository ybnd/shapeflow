import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

file = 'D:/temp/SIMPLE/jitter/shuttle jitterD 2019-05-21 19-38-16.xlsx'

df_avg = pd.read_excel(file, sheet_name='data-avg')
df_std = pd.read_excel(file, sheet_name='data-std')


series = df_avg.columns.to_list()
series.remove('t')

plt.figure(figsize=(10, 6))
for volume in series:
    # plt.plot(df_avg['t'], df_avg[volume])
    plt.errorbar(df_avg['t'], df_avg[volume], xerr=None, yerr=1.96*df_std[volume], linestyle='')

plt.show()