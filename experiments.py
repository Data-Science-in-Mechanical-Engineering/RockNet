"""
This file includes the experiments to validate rocket works properly.
"""
"""
Used datasets so far:
ElectricDevices : dataset is too big, takes way too long to compute
ECG200 is used for now

Results so far:
on ECG200:

Scores are:     [0.77 0.72 0.71 0.84 0.82]
Timings are:   [[3.00212583e+02     3.23654123e+02      2.86469381e+02      1.02817715e+02      3.17165780e+02]
                [2.92515608e+02     3.22072393e+02      2.87634340e+02      1.02637792e+02      3.19481253e+02]
                [1.50352920e-02     2.61733402e-03      2.06695800e-03      2.05383298e-03      2.27549998e-03]
                [1.16041698e-03     1.83125027e-04      1.84291042e-04      1.81916985e-04      1.81665993e-04]]
"""

import jax.random
import numpy as np
import jax.numpy as jnp
from kernel import RocketKernel
import time
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# Load the dataset

training_path = ("/Users/alperencebecik/Desktop/DSME/Datasets/ECG200/ECG200_TRAIN.txt")
training = np.loadtxt(training_path)
y_train, X_train = training[:,0].astype(float).astype(int), training[:,1:]
X_train = jnp.array(X_train)
y_train = jnp.array(y_train)


test_path = ("/Users/alperencebecik/Desktop/DSME/Datasets/ECG200/ECG200_TEST.txt")
test = np.loadtxt(test_path)
y_test, X_test = test[:,0].astype(float).astype(int), test[:, 1:]
X_test = jnp.array(X_test)
y_test = jnp.array(y_test)


# Running the experiment

num_runs = 5
num_measurements = 4
results = np.zeros(num_runs)
timings = np.zeros([num_measurements, num_runs])

for i in range(num_runs):

    # Apply transform to train data
    time_start = time.perf_counter()
    inp_length = X_train.shape[-1]
    training_kernel = RocketKernel(input_length=inp_length, num_kernels=20, rkey=jax.random.PRNGKey(i))
    training_kernel(X=X_train)
    time_end = time.perf_counter()
    timings[0,i] = time_end - time_start

    print('Transformed training data with kernels')
    print(f'Elapsed time during transform: {timings[0,i]}')

    # Apply transform to test data
    time_start = time.perf_counter()
    test_inp_length = X_test.shape[-1]
    testing_kernel = RocketKernel(input_length=test_inp_length, num_kernels=20, rkey=jax.random.PRNGKey(i))
    testing_kernel(X=X_test)
    time_end = time.perf_counter()
    timings[1, i] = time_end-time_start

    print('Transformed test data with kernels')
    print(f'Elapsed time during transform: {timings[1,i]}')

    # Training
    time_start = time.perf_counter()
    classifier = make_pipeline(StandardScaler(with_mean=False), RidgeCV())
    classifier.fit(training_kernel.feature_map, y_train)
    time_end = time.perf_counter()
    timings[2,i] = time_end-time_start

    print('Completed training phase')
    print(f'Elapsed time during training: {timings[2,i]}')

    # Test
    time_start = time.perf_counter()
    results[i] = classifier.score(testing_kernel.feature_map, y_test)
    time_end = time.perf_counter()
    timings[3,i] = time_end-time_start
    print('Completed test phase')
    print(f'Elapsed time during testing: {timings[3,i]}')

    print(f'End of run no: {i}')
    print(f'Score of the run: {results[i]}')


print('All done!')
print(f'Scores are: {results}')
print(f'Timings are: {timings}')

'''
Transform stage may need some optimizations to quicken runs.
'''
