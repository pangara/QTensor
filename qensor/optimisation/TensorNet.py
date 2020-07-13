import qtree
from qensor.ProcessingFrameworks import NumpyBackend

class TensorNet:
    @property
    def tensors(self):
        return self._tensors

    def slice(self, slice_dict):
        raise NotImplementedError

    def __len__(self):
        return len(self.tensors)

    def get_line_graph(self):
        raise NotImplementedError


class QtreeTensorNet:
    def __init__(self, buckets, data_dict
                 , bra_vars, ket_vars, fixed_vars
                 , bucket_backend=NumpyBackend):
        self.buckets = buckets
        self.data_dict = data_dict
        self.bra_vars = bra_vars
        self.ket_vars = ket_vars
        self.fixed_vars = fixed_vars
        self.bucket_backend = bucket_backend

    @property
    def _tensors(self):
        return sum(self.buckets, [])

    def slice(self, slice_dict):
        sliced_buckets = self.bucket_backend.get_sliced_buckets(
            self.buckets, self.data_dict, slice_dict)
        self.buckets = sliced_buckets

    def get_line_graph(self):
        ignored_vars = self.bra_vars + self.ket_vars
        return qtree.graph_model.buckets2graph(self.buckets,
                                               ignore_variables=ignored_vars)

