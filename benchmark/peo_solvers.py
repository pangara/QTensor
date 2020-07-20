"""
Create different benchmarks for running peo solvers with
multiple options and types of solvers
"""

import sys
sys.path.insert(0, "../")
sys.path.insert(1, "../../PACE2017-TrackA")
sys.path.insert(2, "../../quickbb")
sys.path.insert(3, "../qtree")
sys.path.insert(4, "../../flow-cutter-pace17")

import numpy as np
import networkx as nx
from qensor import QtreeQAOAComposer
import qtree
from qtree.graph_model import get_upper_bound_peo, get_peo
from time import time
from qensor import utils

def peo_benchmark(
        method,
        problem_graph_start,
        problem_graph_end,
        problem_graph_jumps=2,
        graph_connectivity=5,
        heuristic_runtime=-1,
        operators="diagonal",
        seed=25,
        beta=None,
        gamma=None):
    if beta is None:
        beta = [.5, 1]
    if gamma is None:
        gamma = [.5, 1]

    # print all output data to a file

    print("method: " + str(method)
          + " | heuristic_runtime: " + str(heuristic_runtime)
          + " | maxNodes" + str(problem_graph_end)
          + " | graph_connectivity: " + str(graph_connectivity)
          + " | p: " + str(len(beta))
          + " | operators: " + operators
          + " | seed: " + str(seed) + "\n")

    for num_nodes in range(problem_graph_start, problem_graph_end, problem_graph_jumps):
        print("problem_graph_size:", num_nodes)
        graph = nx.random_regular_graph(d=graph_connectivity, n=num_nodes, seed=seed)
        composer = QtreeQAOAComposer(graph, beta=beta, gamma=gamma)
        # for using the non-optimal full operators
        if operators == "full_matrix":
            composer.set_operators(operators)
        composer.ansatz_state()  # creates the QAOA circuit

        # create the tensor network graph based on the problem circuit
        qc = composer.circuit
        all_gates = qc
        n_qubits = len(set(sum([g.qubits for g in all_gates], tuple())))
        circuit = [[g] for g in qc]
        buckets, data_dict, bra_vars, ket_vars = qtree.optimizer.circ2buckets(
            n_qubits, circuit)
        graph = qtree.graph_model.buckets2graph(buckets,
                                                ignore_variables=ket_vars + bra_vars)

        # find the perfect elimination order (peo) for the tensor network
        peo = []
        treewidth = -1
        # time the peo functions
        start = time()

        if method == "tamaki_heuristic":
            peo, treewidth = get_upper_bound_peo(graph, method="tamaki", wait_time=heuristic_runtime)

        elif method == "quickbb":
            peo, treewidth = get_upper_bound_peo(graph, method="quickbb", wait_time=heuristic_runtime)

        elif method == "flow_cutter":
            peo, treewidth = get_upper_bound_peo(graph, method="flow_cutter", wait_time=heuristic_runtime)

        elif method == "greedy":
            peo_ints, tw = utils.get_locale_peo(graph, utils.n_neighbors)
            treewidth = max(tw)
            peo = [qtree.optimizer.Var(var, size=graph.nodes[var]['size'],
                                       name=graph.nodes[var]['name'])
                   for var in peo_ints]

        elapsed = time() - start

        # print all relevant information
        print("peo_processing:", elapsed)
        print("graph_nodes:", graph.number_of_nodes())
        print("max_treewidth:", treewidth)
        print()



def peo_benchmark_wrapper(
        folder,
        method,
        problem_graph_start,
        problem_graph_end,
        problem_graph_jumps=2,
        graph_connectivity=5,
        heuristic_runtime=-1,
        operators="diagonal",
        seed=25,
        beta=None,
        gamma=None):
    if beta is None:
        beta = [.5, 1]
    if gamma is None:
        gamma = [.5, 1]

    sys.stdout = open(folder + "peo_" + str(method)
                      + "_heuristicRun" + str(heuristic_runtime)
                      + "_maxNodes" + str(problem_graph_end)
                      + "_d" + str(graph_connectivity)
                      + "_p" + str(len(beta))
                      + "_operators-" + operators
                      + "_seed" + str(seed)
                      + ".txt", 'w')

    peo_benchmark(method,
                  problem_graph_start,
                  problem_graph_end,
                  problem_graph_jumps,
                  graph_connectivity,
                  heuristic_runtime,
                  operators,
                  seed,
                  beta,
                  gamma)


def run_treewidth_dependency_benchmarks():
    p_values = np.ones(100) * 0.5
    seeds = [23, 24, 25]

    for seed in seeds:
        # run increasing d for several p
        d = np.arange(1, 11)
        for d_i in d:
            peo_benchmark_wrapper("treewidth_dependency_data/", "greedy", 20, 21, 1, d_i, 120, "diagonal", seed,
                                  p_values[:1], p_values[:1])
            peo_benchmark_wrapper("treewidth_dependency_data/", "greedy", 20, 21, 1, d_i, 120, "diagonal", seed,
                                  p_values[:2], p_values[:2])
            peo_benchmark_wrapper("treewidth_dependency_data/", "greedy", 20, 21, 1, d_i, 120, "diagonal", seed,
                                  p_values[:3], p_values[:3])

        # run increasing p for several d
        p_options = np.arange(1, 11)
        for i in p_options:
            peo_benchmark_wrapper("treewidth_dependency_data/", "tamaki_heuristic", 20, 21, 1, 3, 120, "diagonal", seed,
                                  p_values[:i], p_values[:i])
            peo_benchmark_wrapper("treewidth_dependency_data/", "tamaki_heuristic", 20, 21, 1, 4, 120, "diagonal", seed,
                                  p_values[:i], p_values[:i])
            peo_benchmark_wrapper("treewidth_dependency_data/", "tamaki_heuristic", 20, 21, 1, 5, 120, "diagonal", seed,
                                  p_values[:i], p_values[:i])


def run_peo_benchmarks():
    # peo_benchmark_wrapper("peo_bench_data/", "greedy", 10, 151, 10, 3, 1)
    peo_running_times = [1, 5, 15, 60]
    seeds = [23, 24, 25]
    methods = ["tamaki_heuristic", "flow_cutter"]

    for method in methods:
        for seed in seeds:
            for peo_run_time in peo_running_times:
                peo_benchmark_wrapper("peo_bench_data/", method, 10, 11, 10, 3, peo_run_time, "diagonal", seed)


    # peo_benchmark_wrapper("peo_bench_data/", "tamaki_heuristic", 10, 151, 10, 3, 1, "full_matrix")
    # peo_benchmark_wrapper("peo_bench_data/", "tamaki_heuristic", 10, 151, 10, 3, 2, "full_matrix")
    # peo_benchmark_wrapper("peo_bench_data/", "tamaki_heuristic", 10, 151, 10, 3, 5, "full_matrix")
    # peo_benchmark_wrapper("peo_bench_data/", "tamaki_heuristic", 10, 151, 10, 3, 15, "full_matrix")
    # peo_benchmark_wrapper("peo_bench_data/", "tamaki_heuristic", 10, 151, 10, 3, 60, "full_matrix")

    # peo_benchmark_wrapper("peo_bench_data/", "quickbb", 10, 31, 10, 3, 1)
    # peo_benchmark_wrapper("peo_bench_data/", "quickbb", 10, 31, 10, 3, 2)
    # peo_benchmark_wrapper("peo_bench_data/", "quickbb", 10, 31, 10, 3, 5)
    # peo_benchmark_wrapper("peo_bench_data/", "quickbb", 10, 31, 10, 3, 15)


# peo_benchmark_wrapper("peo_bench_data/", "greedy", 10, 501, 10, 3, 1)
# run_peo_benchmarks()
run_treewidth_dependency_benchmarks()
