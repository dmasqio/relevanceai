"""
Batch Cluster Operations
"""
from relevanceai.operations_new.cluster.batch.transform import BatchClusterTransform
from relevanceai.operations_new.ops_base import OperationAPIBase
from relevanceai.operations_new.cluster.ops import ClusterOps
from relevanceai.operations_new.cluster.batch.models.base import BatchClusterModelBase
from relevanceai.dataset import Dataset
from typing import Any

from relevanceai.operations_new.ops_run import PullTransformPush


class BatchClusterOps(BatchClusterTransform, ClusterOps):
    """Batch Clustering related Operations"""

    def __init__(
        self,
        vector_fields,
        alias: str = None,
        model: BatchClusterModelBase = None,
        model_kwargs=None,
        dataset_id: str = None,
        cluster_field="_cluster_",
        verbose: bool = False,
        **kwargs
    ):
        if len(vector_fields) > 1:
            raise NotImplementedError(
                "Currently we do not support more than 1 vector field."
            )

        if dataset_id is not None:
            self.dataset_id = dataset_id
        self.vector_fields = vector_fields
        self.cluster_field = cluster_field
        self.verbose = verbose
        if isinstance(model, str):
            self.model_name = model
        else:
            self.model_name = str(model)

        if model_kwargs is None:
            model_kwargs = {}

        self.model_kwargs = model_kwargs

        for k, v in kwargs.items():
            setattr(self, k, v)

        super().__init__(
            vector_fields=vector_fields,
            model="MiniBatchKmeans" if model is None else model,
            model_kwargs=model_kwargs,
            **kwargs
        )

        self.alias = self._get_alias(alias)

    def fit(self, chunk):
        vectors = self.get_field_across_documents(
            self.vector_fields[0], chunk, missing_treatment="skip"
        )
        self.model.partial_fit(vectors)
        return chunk

    def run(self, dataset: Dataset, filters: list = None, chunksize: int = 500):
        """
        Run batch clustering
        """
        pup = PullTransformPush(
            dataset=dataset,
            func=self.fit,
            pull_batch_size=chunksize,
            push_batch_size=chunksize,
            filters=filters,
            select_fields=self.vector_fields,
            show_progress_bar=True,
        )
        pup.run()

        pup = PullTransformPush(
            dataset=dataset,
            func=self.transform,
            pull_batch_size=chunksize,
            push_batch_size=chunksize,
            filters=filters,
            select_fields=self.vector_fields,
            show_progress_bar=True,
        )
        pup.run()

        return
