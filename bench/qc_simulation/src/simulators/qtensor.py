import qtensor
import qtree
import numpy as np

# -- QAOA generic parser

class QAOAComposer(qtensor.DefaultQAOAComposer):
    def __init__(self, N, terms, **kwargs):
        self.n_qubits = N
        # from ccomp (Can't call DefaultQAOA Composer since need graph)
        self.builder = self._get_builder()
        # gamma and beta
        self.params = kwargs
        # 
        self.terms = terms
        self.qubit_map = {n: i for i, n in enumerate(range(N))}

    def cost_operator_circuit(self, gamma):
        for factor, term in self.terms:
            t_mapped = [self.qubit_map[i] for i in term]
            self.append_Z_term(term, gamma)

    def append_Z_term(self, term, gamma):
        if len(term) == 2:
            self.apply_gate(self.operators.ZZ, term[0], term[1], alpha=2*gamma)
            #self.apply_gate(qtensor.OpFactory.ZZFull, term[0], term[1], alpha=2*gamma)
        elif len(term) == 4:
            self.apply_gate(self.operators.Z4, *term, alpha=2*gamma)
        else:
            raise ValueError(f"Invalid QAOA term length: {len(term)}")

    def mixer_operator(self, beta):
        qubits = self.qubit_map.values()
        for qubit in qubits:
            self.x_term(qubit, beta)

def parse_qaoa(data):
    import json
    data = json.loads(data)
    terms = data["terms"]
    gamma = np.array(data["gamma"])/np.pi/2
    beta = np.array(data["beta"])/np.pi
    N = len(set(sum([t[1] for t in terms], [])))
    composer = QAOAComposer(N, terms, gamma=gamma, beta=beta)
    composer.ansatz_state()
    return composer.circuit
# --

def read_circ(circ_f, type=None):

    if type is None:
        type = circ_f.path.name.split(".")[-1]

    print("Reading circuit of type", type)
    if type == "jsonterms":
        b = circ_f.f.read()
        return parse_qaoa(b)

    elif type == "qasm":
        from qiskit import QuantumCircuit
        b = circ_f.f.read()
        str = b.decode('utf-8')

        qiskit_circuit = QuantumCircuit.from_qasm_str(str)
        return qtree.operators.from_qiskit_circuit(qiskit_circuit)
    else:
        b = circ_f.f.read()
        str = b.decode('utf-8')
        import io
        f = io.StringIO(str)
        N, circ = qtree.operators.read_circuit_stream(f)
        return sum(circ, [])

def read_preps(prep_f):
    import pickle
    return pickle.load(prep_f.f)

def write_preps(peo, prep_f):
    import pickle
    pickle.dump(peo, open(prep_f, 'wb'))

def write_json(data, out_file):
    import json
    with open(out_file, 'w') as f:
        json.dump(data, f)
        # This newline plays nice when cat-ing multiple files
        f.write('\n')

def preprocess(in_file, out_file, O='greedy', S=None, M=30, after_slice='run-again'):
    """
    Arguments:
        in_file: input file
        out_file: output file
        O: ordering algorithm 
        S: slicing algorithm 
        M: Memory limit for slicing 
    """
    circ = read_circ(in_file)
    tn = qtensor.optimisation.QtreeTensorNet.from_qtree_gates(circ)
    opt = qtensor.toolbox.get_ordering_algo(O)
    if S:
        # ignore argument type mismatch for pyright -- opt can be `Optimizer`
        # pyright: reportGeneralTypeIssues=false
        opt = qtensor.optimisation.TreeTrimSplitter(
            tw_bias=0, max_tw=M, base_ordering=opt,
            peo_after_slice_strategy=after_slice
        )
        
        peo, par_vars, _ = opt.optimize(tn)
        # --dbg
        import networkx as nx
        graph = tn.get_line_graph()
        ignore_vars = tn.bra_vars + tn.ket_vars
        for pv in par_vars:
            graph.remove_node(int(pv))
        components = list(nx.connected_components(graph))
        print(f"Sliced graph # nodes: {graph.number_of_nodes()} and #components: {len(components)} with sizes {[len(c) for c in components]}")
        print(f"peo size without par_vars and ignore_vars: {len(peo) - len(par_vars) - len(ignore_vars)}")
        def inspect_node(g, n):
            neighbors = sorted(list(g.neighbors(n)))
            return f"{n} -> {len(neighbors)}({neighbors[0]}::{neighbors[-1]})"
        # inspect first 10 nodes
        graph, label_dict = qtree.graph_model.relabel_graph_nodes(
            graph, dict(zip(opt.peo_ints, range(graph.number_of_nodes())))
        ) 
        for n in sorted(list(graph.nodes()))[127*2:127*4]:
            print(inspect_node(graph, n), end='; ', flush=True)
        print()
        # --
    else:
        peo, _ = opt.optimize(tn)
        par_vars = []
    print("W", opt.treewidth)
    # -- qtensor_estim
    prep_data = (peo, par_vars, tn)
    write_preps(prep_data, out_file)


def estimate(in_file, out_file, C=100, M=30, F=1e12, T=1e9, **kwargs):
    """
    Arguments:
        in_file: file with preprocessed data
        out_file: file to write the results to
        C: Compression ratio
        M: Memory limit in log2(b/16)
        F: assumed FLOPS 
        T: Throughput of compression
    """
    from qtensor.compression.cost_estimation import compressed_contraction_cost, Cost
    from dataclasses import asdict
    import json
    prep_data = read_preps(in_file)
    peo, par_vars, tn = prep_data

    tn.slice({i: slice(0, 1) for i in par_vars})
    peo = peo[:len(peo) - len(par_vars)]
    costs: list[Cost] = compressed_contraction_cost(tn, peo, mem_limit=M, compression_ratio=C)
    totals: Cost = sum(costs[1:], costs[0])
    time = totals.time(F, T, T, M)
    C = asdict(totals)
    C['time'] = time*2**len(par_vars)
    print("C", C)
    out_file += ".json"
    write_json(C, out_file)
    return out_file

def simulate(in_file, out_file, backend='einsum', compress=None, M=29, **kwargs):
    """
    Args:
        in_file: file with preprocessed data
        out_file: file to write the results to
        backend: backend to use
        compress: compression algorithm
        M: memory threshold for compression
    """
    import time
    from qtensor.contraction_algos import bucket_elimination
    import cupy
    cupy.cuda.profiler.start()
    prep_data = read_preps(in_file)
    peo, par_vars, tn = prep_data
    
    backend = qtensor.contraction_backends.get_backend(backend)
    if compress is not None:
        if compress == 'szx':
            compressor = qtensor.compression.CUSZCompressor(r2r_error=1e-2, r2r_threshold=1e-2)
        else:
            raise ValueError(f"Unknown compression algorithm: {compress}")
        backend = qtensor.contraction_backends.CompressionBackend(backend, compressor, M)

    relabelid = {}
    for tensor in tn.tensors:
        for i in tensor.indices:
            relabelid[int(i)] = i

    slice_ext = {relabelid[int(i)]: 0 for i in par_vars}

    if len(par_vars) > 0:
        print("Parvars", par_vars)
        print(f"Detected {len(par_vars)} slice variables")
    sim = qtensor.QtreeSimulator(backend=backend)
    sim.tn = tn
    sim.tn.backend = backend
    sim.peo = peo
    sim._slice_relabel_buckets(slice_ext)
    buckets = sim.tn.buckets
    # --dbg
    ignore_vars  = sim.tn.bra_vars + sim.tn.ket_vars 
    graph = qtree.graph_model.importers.buckets2graph(buckets, ignore_vars)
    graph, label_dict = qtree.graph_model.relabel_graph_nodes(
        graph, dict(zip(graph.nodes, np.array(list(graph.nodes)) - 127*2))
    ) 
    import networkx as nx
    components = list(nx.connected_components(graph))
    print(f"Sliced graph # nodes: {graph.number_of_nodes()} and #components: {len(components)} with sizes {[len(c) for c in components]}")
    print(f"peo size without par_vars and ignore_vars: {len(peo) - len(ignore_vars)}")
    # --

    start = time.time()
    for i in range(2**0):
        print(f"P {i}", end='', flush=True)
        bcopy = [b[:] for b in buckets]
        res = bucket_elimination(
            bcopy, backend,
            n_var_nosum=len(tn.free_vars)
        )
        del bcopy
        print("Result", res.data.flatten()[0])
        time.sleep(0.5)
    print("Simulation result:", backend.get_result_data(res).flatten()[0])
    end = time.time()
    print("D", end - start)
    out_file += ".json"
    C = {'time': end - start}
    write_json(C, out_file)
    cupy.cuda.profiler.stop()
    return out_file