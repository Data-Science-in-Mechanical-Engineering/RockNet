'''
Created to explore and understand the dataset. Not really relevant.
'''

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

training_path = ("/Users/alperencebecik/Desktop/DSME/Datasets/ElectricDevices/ElectricDevices_TRAIN.txt")
training = np.loadtxt(training_path, "str")
y_train, X_train = training[:,0].astype(float).astype(int), training[:, 1:]

df_train_labels = pd.DataFrame(y_train, columns=["Class"])
df_train_data = pd.DataFrame(X_train, columns =["Timestep {}".format(i) for i in range(96)])
print(df_train_data.shape)
print(df_train_data.describe())

for index,row in df_train_data.head(1).iterrows():
    plt.plot(row, label=index)
plt.legend()
plt.show()

#print(df_train_data.columns)

test_path = ("/Users/alperencebecik/Desktop/DSME/Datasets/ElectricDevices/ElectricDevices_TEST.txt")
test = np.loadtxt(test_path, "str")
y_test, X_test = test[:,0].astype(float).astype(int), test[:,1:]
