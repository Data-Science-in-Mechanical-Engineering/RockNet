from pathlib import Path

import matplotlib.pyplot as plt

import pickle as p

import numpy as np

from jax_training import get_logger_name
# from trainer import get_logger_name

import pandas as pd


def plot_data(file, color, label):
    try:
        with open(f"results/{file}", 'rb') as handle:
            acc = p.load(handle)

        if label:
            plt.plot(acc, label=file, color=color)
        else:
            plt.plot(acc, color=color)
    except Exception as e:
        print(f"File {file} not found {e}")


def load_data(dataset_name, seed, use_rocket, eval_dataset, quantize_adam, use_dynamic_tree_quantization, sample_dataset_iid, learning_rate):
    file = get_logger_name(dataset_name=dataset_name, 
                            seed=seed, 
                            use_rocket=use_rocket,
                            eval_dataset=eval_dataset,
                            quantize_adam=quantize_adam,
                            use_dynamic_tree_quantization=use_dynamic_tree_quantization,
                            learning_rate=learning_rate,
                            sample_dataset_iid=sample_dataset_iid)
    print(f"Loading file {file}")
    # if use_rocket and quantize_adam:
    #     file = f"../../jax_results/{file}"
    # else:
    #     file = f"results/{file}" 
    file = f"../../jax_results_iid/{file}"
    try:
        with open(file, 'rb') as handle:
            acc = p.load(handle)
        return acc
    except:
        print(f"Loading file {file} failed")
        return None


def get_final_accuracy(dataset_name, seed, use_rocket, quantize_adam, use_dynamic_tree_quantization, sample_dataset_iid, learning_rate):

    acc_evaluation = load_data(dataset_name=dataset_name,
                                seed=seed,
                                use_rocket=use_rocket,
                                eval_dataset=True,
                                quantize_adam=quantize_adam, 
                                use_dynamic_tree_quantization=use_dynamic_tree_quantization, 
                                learning_rate=learning_rate,
                                sample_dataset_iid=sample_dataset_iid)
    acc_test = load_data(dataset_name=dataset_name,
                            seed=seed,
                            use_rocket=use_rocket,
                            eval_dataset=False,
                            quantize_adam=quantize_adam, 
                            use_dynamic_tree_quantization=use_dynamic_tree_quantization, 
                            learning_rate=learning_rate,
                            sample_dataset_iid=sample_dataset_iid)

    if acc_evaluation is None or acc_test is None:
        return False, None

    return True, acc_test[np.argmax(acc_evaluation)]


def plot_comparison_entire_dataset():
    data = pd.read_csv(f"{Path.home()}/datasets/DataSummary.csv")
    names = data["Name"]
    length = data["Train "]
    results = []
    distance_to_boundary = []
    boundary = np.array([1.0, 1.0])
    boundary /= np.linalg.norm(boundary)
    boundary_ort = np.array([-1.0, 1.0])
    boundary_ort /= np.linalg.norm(boundary_ort)


    for data_idx, n in enumerate(names):
        if length[data_idx] < 100:
            continue
        for i in range(10):
            name_dataset_seed = f"{n}"
            succ_rocket, acc_rocket = get_final_accuracy(name_dataset_seed, i, True, quantize_adam=False, use_dynamic_tree_quantization=True, learning_rate=0.001, sample_dataset_iid=False)
            succ_nn, acc_nn = get_final_accuracy(name_dataset_seed, i, True, quantize_adam=False, use_dynamic_tree_quantization=False, learning_rate=0.001, sample_dataset_iid=True)
            if succ_nn and succ_rocket:
                results.append([acc_rocket, acc_nn])

                a = np.array([acc_rocket, acc_nn]) - boundary * np.dot(np.array([acc_rocket, acc_nn]), boundary)
                #distance_to_boundary.append(np.dot(boundary_ort, a.flatten()))
                distance_to_boundary.append(acc_nn/acc_rocket)

    results = np.array(results)
    plt.scatter(results[:, 0], results[:, 1])
    plt.plot([0, 1], [0, 1], 'k')

    print(f"acc_improvement {np.mean(results[:, 0] - results[:, 1])}")

    print(np.sum(results[:, 0] > results[:, 1]) / len(results[:, 1]))

    data = {"accNonIID": results[:, 0]*100, "accIID": results[:, 1]*100, "distanceBoundary": distance_to_boundary}
    df = pd.DataFrame(data)
    df.to_csv("results/plots/ComparisonIID.csv")

    plt.show()

    acc_dev = (results[:, 0] - results[:, 1]) * 100
    hist, bin_edges = np.histogram(acc_dev, bins=[-100.5 + i for i in range(201)], density=True)

    data = {"x": bin_edges[1:] - 0.5, "y": hist}
    df = pd.DataFrame(data)
    df.to_csv("results/plots/ComparisonIIDHist.csv")

    plt.bar(bin_edges[1:] - 0.5, hist)
    plt.show()


def plot_comparison_quantized_adam():

    data = pd.read_csv(f"{Path.home()}/datasets/DataSummary.csv")
    names = data["Name"]
    results = []
    distance_to_boundary = []
    boundary = np.array([1.0, 1.0])
    boundary /= np.linalg.norm(boundary)
    boundary_ort = np.array([-1.0, 1.0])
    boundary_ort /= np.linalg.norm(boundary_ort)


    for n in names:
        num_data_points = 0
        temp_data = []
        for i in range(10):
            succ_qa, acc_qa = get_final_accuracy(dataset_name=n,
                                                    seed=i,
                                                    use_rocket=True,
                                                    quantize_adam=True, 
                                                    use_dynamic_tree_quantization=False, 
                                                    learning_rate=0.001)
            
            succ_qa_dyntree, acc_qa_dyntree = get_final_accuracy(dataset_name=n,
                                                    seed=i,
                                                    use_rocket=True,
                                                    quantize_adam=True, 
                                                    use_dynamic_tree_quantization=True, 
                                                    learning_rate=0.001)

            succ, acc = get_final_accuracy(dataset_name=n,
                                            seed=i,
                                            use_rocket=True,
                                            quantize_adam=False, 
                                            use_dynamic_tree_quantization=True, 
                                            learning_rate=0.001)
            if succ_qa and succ_qa_dyntree and succ:
                temp_data.append([acc_qa, acc_qa_dyntree, acc])

                # a = np.array([acc_rocket, acc_nn]) - boundary * np.dot(np.array([acc_rocket, acc_nn]), boundary)
                #distance_to_boundary.append(np.dot(boundary_ort, a.flatten()))
                distance_to_boundary.append([acc_qa_dyntree/acc_qa, acc_qa_dyntree/acc])

        temp_data = np.array(temp_data)
        if temp_data.shape[0] > 0:
            results.append(list(temp_data.mean(axis=0)))

    results = np.array(results)
    plt.figure()
    plt.scatter(results[:, 0], results[:, 1])
    plt.plot([0, 1], [0, 1], 'k')
    plt.xlabel("Quantized Adam")
    plt.ylabel("Quantized Adam + Dynamic Tree")

    print(f"acc_improvement {np.mean(results[:, 0] - results[:, 1])}")

    print(np.sum(results[:, 0] > results[:, 1]) / len(results[:, 1]))

    # data = {"accRocket": results[:, 0]*100, "accNN": results[:, 1]*100, "distanceBoundary": distance_to_boundary}
    # df = pd.DataFrame(data)
    # df.to_csv("results/plots/ComparisonNNROCKET.csv")

    plt.show()

    plt.figure()
    plt.scatter(results[:, 2], results[:, 1])
    plt.xlabel("Adam")
    plt.ylabel("Quantized Adam + Dynamic Tree")
    plt.plot([0, 1], [0, 1], 'k')

    print(f"acc_improvement {np.mean(results[:, 1] - results[:, 2])}")

    print(np.sum(results[:, 1] > results[:, 2]) / len(results[:, 1]))

    # data = {"accRocket": results[:, 0]*100, "accNN": results[:, 1]*100, "distanceBoundary": distance_to_boundary}
    # df = pd.DataFrame(data)
    # df.to_csv("results/plots/ComparisonNNROCKET.csv")

    plt.show()

    # acc_dev = (results[:, 0] - results[:, 1]) * 100
    # hist, bin_edges = np.histogram(acc_dev, bins=[-100.5 + i for i in range(201)], density=True)

    # data = {"x": bin_edges[1:] - 0.5, "y": hist}
    # df = pd.DataFrame(data)
    # df.to_csv("results/plots/ComparisonNNROCKETHist.csv")

    # plt.bar(bin_edges[1:] - 0.5, hist)
    # plt.show()


if __name__ == "__main__":


    # plot_comparison_quantized_adam()
    plot_comparison_entire_dataset()
    exit(0)

    data = pd.read_csv(f"{Path.home()}/datasets/DataSummary.csv")

    names = data["Name"]
    #names = ["ElectricDevices", "NonInvasiveFetalECGThorax2", "Crop", "ChlorineConcentration"]
    names = ["FaceAll"]

    lr = 0.001

    max_num_seeds = 100
    seed_offset = 0
    colors=['b', 'r', 'g', 'm', 'y', 'k']
    seed = 0
    for name_dataset in names:
        plt.figure(figsize=(4,4))
        learning_rates = [0.001]
        color_idx = 0
        for i in range(0,10):
            name_dataset_seed = f"{name_dataset}_{i}_test"
            label = get_logger_name(name_dataset_seed, use_cocob=False, learning_rate=lr, use_rocket=True)
            plot_data(label, colors[color_idx], label=label)
        color_idx += 1
        for i in range(0,10):
            name_dataset_seed = f"{name_dataset}_{i}_test"
            label = get_logger_name(name_dataset_seed, use_cocob=False, learning_rate=lr, use_rocket=False)
            plot_data(label, colors[color_idx], label=label)
        color_idx += 1

        plt.title(name_dataset)
        # plt.legend()
        plt.show()
