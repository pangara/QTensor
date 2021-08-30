#!/usr/bin/env python3
import qtensor
from qtensor.optimisation.Optimizer import GreedyOptimizer, TamakiOptimizer, KahyparOptimizer
import numpy as np
import json
import platform
from qtensor.Simulate import QtreeSimulator
from qtensor.optimisation.kahypar_ordering.test_kahypar_ordering import get_tw_costs_kahypar, \
get_tw_costs_greedy, get_tw_costs_rgreedy, get_tw_costs_tamaki, generate_problem, \
    timing

### json format
def print_results_json(mode, N, p, method, result, func):
    res = dict(
                mode=mode
                ,device_props=dict(name=platform.node())
                ,N=N
                ,p=p
                ,method=method
                ,time=result[0]
                ,tw=int(result[1])
                ,mem=max(result[2])
                ,flop=sum(result[3])
                ,func=func)
    #print(json.dumps(res), flush=True)
    return res
    
def test_cost_estimation(): 

    ### Different mode, p, N
    mode_list = ['ansatz','energy']
    p_list = [1,3,5] #[2,4,6,8,10]
    N_list = [20,40,60,80,100,120]
    func_name = test_cost_estimation.__name__
    with open('test_cost_estimation.jsonl', 'w') as f:
        for mode in mode_list:
            for p in p_list:
                for N in N_list:
                    composer, tn = generate_problem(N,p,mode = mode)
                    ###
                    rgreedy_str = get_tw_costs_rgreedy(tn)
                    #print_results_json(mode, N, p, 'RGreedy', greedy_str)
                    json.dump(print_results_json(mode, N, p, 'RGreedy', rgreedy_str,func_name),f)
                    f.write('\n')
                    
                    ###
                    greedy_str = get_tw_costs_greedy(tn)
                    #print_results_json(mode, N, p, 'Greedy', greedy_str)
                    json.dump(print_results_json(mode, N, p, 'Greedy', greedy_str,func_name),f)
                    f.write('\n')
                    
                    ###
                    kahypar_str = get_tw_costs_kahypar(tn)
                    #print_results_json(mode, N, p, 'Kahypar', kahypar_str)
                    json.dump(print_results_json(mode, N, p, 'Kahypar', kahypar_str,func_name),f)
                    f.write('\n')
                    
                    ###
                    tamaki_str=[];  wait_time_list = [30,60,150]
                    for (count,wait_time) in enumerate(wait_time_list):
                        tamaki_str.append(get_tw_costs_tamaki(tn, wait_time))
                        name = 'Tamaki ({:d})'.format(wait_time)
                        #print_results_json(mode, N, p, name, tamaki_str[count])
                        json.dump(print_results_json(mode, N, p, name, tamaki_str[count],func_name),f)
                        f.write('\n')
            
 
                 
def test_get_tw():
    mode_list = ['ansatz','energy']
    N_list = list(range(10, 100+10, 10))
    N_list.extend(list(range(200, 1000+100, 100)))
    p_list = [1,2,3,4,5]
    func_name = test_get_tw.__name__
    with open('test_get_tw.jsonl', 'w') as f: 
        for mode in mode_list:
            for p in p_list:
                for N in N_list:
                    composer, tn = generate_problem(N,p,mode = mode)
                    ###
                    kahypar_str = get_tw_costs_kahypar(tn)   
                    #print_results_json(mode, N, p, 'Kahypar', kahypar_str)
                    json.dump(print_results_json(mode, N, p, 'Kahypar', kahypar_str,func_name),f)
                    f.write('\n')
                    
                    ###
                    rgreedy_str = get_tw_costs_rgreedy(tn)
                    json.dump(print_results_json(mode, N, p, 'RGreedy', rgreedy_str,func_name),f)
                    f.write('\n')
    
    
    
def test_qtree():
    mode_list = ['energy']
    N_list = list(range(10, 100+10, 10))
    N_list.extend(list(range(200, 1000+100, 100)))
    #N_list = [50,100,200,300] 
    p_list = [1,2,3,4]
    func_name = test_qtree.__name__
    def qtree_results_json(mode, N, p, method, result, func):
        res = dict(
                    mode=mode
                    ,device_props=dict(name=platform.node())
                    ,N=N
                    ,p=p
                    ,method=method
                    ,time=result
                    ,func=func)
        #print(json.dumps(res), flush=True)
        return res

    with open('test_qtree.jsonl', 'w') as f: 
        for mode in mode_list:
            for p in p_list:
                for N in N_list:
                    composer, tn = generate_problem(N,p,mode=mode)
                    ###
                    wait_time = 1
                    optimizer=TamakiOptimizer(wait_time = wait_time)
                    sim = QtreeSimulator(optimizer = optimizer)
                    with timing() as t_tamaki:
                        result_tamaki = sim.simulate(composer.circuit)
                    name = 'Tamaki ({:d})'.format(wait_time)
                    json.dump(qtree_results_json(mode, N, p, name, t_tamaki.result,func_name),f)
                    f.write('\n')
                    
                    optimizer=GreedyOptimizer()
                    sim = QtreeSimulator(optimizer = optimizer)
                    with timing() as t_greedy:
                        result_greedy = sim.simulate(composer.circuit)
                    json.dump(qtree_results_json(mode, N, p, 'Greedy', t_greedy.result,func_name),f)
                    f.write('\n')
                    
                    assert np.allclose(result_tamaki, result_greedy)
                    
                    max_time = 1
                    optimizer=qtensor.toolbox.get_ordering_algo('rgreedy_0.02_10', max_time=max_time)
                    sim = QtreeSimulator(optimizer = optimizer)
                    with timing() as t_rgreedy:
                        result_rgreedy = sim.simulate(composer.circuit)
                    json.dump(qtree_results_json(mode, N, p, 'RGreedy', t_rgreedy.result, func_name),f)
                    f.write('\n')
                    
                    assert np.allclose(result_rgreedy, result_greedy)
                    
                    optimizer=KahyparOptimizer()
                    sim = QtreeSimulator(optimizer = optimizer)
                    with timing() as t_kahypar:
                        result_kahypar = sim.simulate(composer.circuit)
                    json.dump(qtree_results_json(mode, N, p, 'Kahypar', t_kahypar.result,func_name),f)
                    f.write('\n')
                    
                    assert np.allclose(result_greedy, result_kahypar)
        

if __name__ == '__main__':
    test_cost_estimation()
    #test_get_tw()
    #test_qtree()
