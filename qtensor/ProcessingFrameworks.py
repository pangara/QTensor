import numpy as np
import lazy_import
from qtree import np_framework
from qtree import optimizer as opt
from pyrofiler import timing
from tqdm import tqdm

class MockModule:
    def __getattribute__(self, attr):
        # Fail spectacularly
        raise ImportError(f'Module tcontract is not imported! Please install it and try again.')

tcontract = MockModule()
try:
    import tcontract
except ImportError:
    pass


from qtensor.utils import ReportTable
from . import exatn_framework

class BucketBackend:
    def process_bucket(self, bucket, no_sum=False):
        raise NotImplementedError

    def get_sliced_buckets(self, buckets, data_dict, slice_dict):
        raise NotImplementedError

    def get_result_data(self, result):
        raise NotImplementedError

class NumpyBackend(BucketBackend):
    def __init__(self):
        super().__init__()
        #self.pbar = tqdm(desc='Buckets', position=2)
        #self.status_bar = tqdm(desc='Current status', position=3, bar_format='{desc}')

    def process_bucket(self, bucket, no_sum=False):
        return np_framework.process_bucket_np(bucket, no_sum=no_sum)

    def get_sliced_buckets(self, buckets, data_dict, slice_dict):
        return np_framework.get_sliced_np_buckets(buckets, data_dict, slice_dict)

    def get_result_data(self, result):
        return result.data

class ExaTnBackend(BucketBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        exatn_framework.import_exatn()

    def process_bucket(self, bucket, no_sum=False):
        res = exatn_framework.process_bucket_exatn(bucket, no_sum=no_sum)
        total_indices = set.union(*[set(t.indices) for t in bucket])
        #self.status_bar.set_description_str(f'Current bucker result size: {len(total_indices)}')
        res =  np_framework.process_bucket_np(bucket, no_sum=no_sum)
        #self.pbar.update(1)
        return res

    def get_sliced_buckets(self, buckets, data_dict, slice_dict):
        return exatn_framework.get_sliced_exatn_buckets(buckets, data_dict, slice_dict)

class CMKLExtendedBackend(BucketBackend):
    def get_sliced_buckets(self, buckets, data_dict, slice_dict):
        return np_framework.get_sliced_np_buckets(buckets, data_dict, slice_dict)

    def process_bucket(self, bucket, no_sum=False):
        result_indices = bucket[0].indices
        result_data = bucket[0].data

        for tensor in bucket[1:]:
            ixa, ixb = result_indices, tensor.indices
            common_ids = sorted(list(set.intersection(set(ixa), set(ixb))), key=int)
            distinct_a = [x for x in ixa if x not in common_ids]
            distinct_b = [x for x in ixb if x not in common_ids]
            transp_a = [ixa.index(x) for x in common_ids+distinct_a]
            transp_b = [ixb.index(x) for x in common_ids+distinct_b]
            a = result_data.transpose(transp_a)
            b = tensor.data.transpose(transp_b)
            n, m, k = 2**len(common_ids), 2**len(distinct_a), 2**len(distinct_b)
            a = a.reshape(n, m)
            b = b.reshape(n, k)

            c = np.empty((n, m, k), dtype=np.complex128)
            tcontract.mkl_contract_complex(a, b, c)

            # Merge and sort indices and shapes
            result_indices = tuple(sorted(
                set(result_indices + tensor.indices),
                key=int)
            )
            ixc = common_ids + distinct_a + distinct_b
            assert len(result_indices) == len(ixc), 'Wrong transposition, please submit an issue'
            transp_c = [ixc.index(x) for x in result_indices]
            result_data = c.reshape(*[2 for _ in result_indices])
            result_data = result_data.transpose(transp_c)

        if len(result_indices) > 0:
            if not no_sum:  # trim first index
                first_index, *result_indices = result_indices
            else:
                first_index, *_ = result_indices
            tag = first_index.identity
        else:
            tag = 'f'
            result_indices = []

        # reduce
        if no_sum:
            result = opt.Tensor(f'E{tag}', result_indices,
                                data=result_data)
        else:
            result = opt.Tensor(f'E{tag}', result_indices,
                                data=np.sum(result_data, axis=0))
        return result

    def get_result_data(self, result):
        return result.data

class PerfBackend(BucketBackend):
    Backend = BucketBackend

    def __init__(self, *args, print=False, num_lines=20, **kwargs):
        self.backend = self.Backend(*args, **kwargs)
        self._print = print
        self.max_lines = num_lines
        self._profile_results = {}
        self.report_table = ReportTable(measure=['max','mean','sum'], max_records=num_lines)

    def _profile_callback(self, time, label, indices):
        if self._print:
            print(f"PROF:: perf data {label}: {time}")
        self._profile_results[str(indices)] = indices, time

    @classmethod
    def from_backend(cls, backend, *args, **kwargs):
        """ Dynamically create and instantiate a class with a given backend. """
        class CustomGeneratedBackend(cls):
            Backend = backend
        return CustomGeneratedBackend(*args, **kwargs)

    def process_bucket(self, bucket, no_sum=False):
        indices = [tensor.indices for tensor in bucket]
        with timing('process bucket time', indices
                         , callback=self._profile_callback):
            return self.backend.process_bucket(bucket, no_sum=no_sum)

    def get_sliced_buckets(self, buckets, data_dict, slice_dict):
        return self.backend.get_sliced_buckets(buckets, data_dict, slice_dict)

    def get_result_data(self, result):
        return self.backend.get_result_data(result)

    def _perfect_bucket_flop(self, bucket_indices):
        resulting_indices = list(set.union(*[set(ixs) for ixs in bucket_indices]))
        # The first index is contracted
        resulting_indices = resulting_indices[1:]
        # don't take index size into account
        n_multiplications = len(bucket_indices)
        size_of_result = 2**len(resulting_indices)
        summation_index_size = 2
        n_summations = summation_index_size - 1
        op = size_of_result*( n_summations + n_multiplications )
        return op


    def gen_report(self):
        data = self._profile_results.values()
        # -- sotrt data with respect to time
        data = sorted(data, key= lambda pair: pair[1], reverse=True)
        # -- report on largest contractions
        max_lines = self.max_lines

        report_lines =  [str([i, ixs, time ]) for i, (ixs, time) in enumerate(data[:max_lines])]
        rep = '\n'.join(report_lines[:max_lines])
        if len(report_lines) > max_lines:
            rep += f'\n ... and {len(data)-max_lines} lines more...'

        # -- report on totals
        for indices, time in  data[:max_lines]:
            kwargs= dict(
                bucket_len = len(indices)
                , time = time
                , flop = self._perfect_bucket_flop(indices)
                , FLOPS = self._perfect_bucket_flop(indices)/time
                , max_size = max([len(ixs) for ixs in indices])
                , min_size = min([len(ixs) for ixs in indices])
                , result_size = len(set.union(*[set(i) for i in indices])) - 1
            )
            self.report_table.record( **kwargs)

        print(self.report_table.markdown())


        # -- report on totals
        total_data = len(data)
        total_time = sum(d[1] for d in data)
        rep += '\n======\n'
        rep += 'Total time: ' + str(total_time)
        rep += '\nTotal bucket contractions: ' + str(total_data)
        rep += '\nMean time for contraction: ' + str(total_time/total_data)
        rep += '\n'
        return rep




class PerfNumpyBackend(PerfBackend):
    Backend = NumpyBackend
