from collections import Counter
from sklearn.metrics import (
    silhouette_score,
    adjusted_rand_score,
    completeness_score,
    homogeneity_score,
)
import pandas as pd
import numpy as np

from relevanceai.vector_tools.dim_reduction import DimReduction
from relevanceai.base import _Base
from relevanceai.api.client import BatchAPIClient
from relevanceai.vector_tools.constants import CENTROID_DISTANCES
from doc_utils import DocUtils
from typing import Optional, Dict

SILHOUETTE_INFO = """
Good clusters have clusters which are highly seperated and elements within which are highly cohesive. <br/>
<b>Silohuette Score</b> is a metric from <b>-1 to 1</b> that calculates the average cohesion and seperation of each element, with <b>1</b> being clustered perfectly, <b>0</b> being indifferent and <b>-1</b> being clustered the wrong way"""

RAND_INFO = """Good clusters have elements, which, when paired, belong to the same cluster label and same ground truth label. <br/>
<b>Rand Index</b> is a metric from <b>0 to 1</b> that represents the percentage of element pairs that have a matching cluster and ground truth labels with <b>1</b> matching perfect and <b>0</b> matching randomly. <br/> <i>Note: This measure is adjusted for randomness so does not equal the exact numerical percentage.</i>"""

HOMOGENEITY_INFO = """Good clusters only have elements from the same ground truth within the same cluster<br/>
<b>Homogeneity</b> is a metric from <b>0 to 1</b> that represents whether clusters contain only elements in the same ground truth with <b>1</b> being perfect and <b>0</b> being absolutely incorrect."""

COMPLETENESS_INFO = """Good clusters have all elements from the same ground truth within the same cluster <br/>
<b>Completeness</b> is a metric from <b>0 to 1</b> that represents whether clusters contain all elements in the same ground truth with <b>1</b> being perfect and <b>0</b> being absolutely incorrect."""

METRIC_DESCRIPTION = {
    "Silhouette Score": SILHOUETTE_INFO,
    "Rand Score": RAND_INFO,
    "Homogeneity": HOMOGENEITY_INFO,
    "Completeness": COMPLETENESS_INFO,
}


def sort_dict(dict, reverse: bool = True, cut_off=0):
    return {
        k: v
        for k, v in sorted(dict.items(), reverse=reverse, key=lambda item: item[1])
        if v > cut_off
    }


class ClusterEvaluate(BatchAPIClient, _Base, DocUtils):
    def __init__(self, project, api_key):
        self.project = project
        self.api_key = api_key
        super().__init__(project, api_key)

    def plot(
        self,
        dataset_id: str,
        vector_field: str,
        alias: str,
        ground_truth_field: str = None,
        description_fields: list = [],
        marker_size: int = 5,
    ):

        """
        Plot the vectors in a collection to compare performance of cluster labels, optionally, against ground truth labels

        Parameters
        ----------
        dataset_id : string
            Unique name of dataset
        vector_field: string
            The vector field that was clustered upon
        alias: string
            The alias of the clustered labels
        ground_truth_field: string
            The field to use as ground truth
        description_fields : list
            List of fields to use as additional labels on plot
        marker_size: int
            Size of scatterplot marker
        """

        (
            vectors,
            cluster_labels,
            ground_truth,
            vector_description,
        ) = self._get_cluster_documents(
            dataset_id=dataset_id,
            vector_field=vector_field,
            alias=alias,
            ground_truth_field=ground_truth_field,
            description_fields=description_fields,
        )
        self.plot_from_documents(
            vectors=vectors,
            cluster_labels=cluster_labels,
            ground_truth=ground_truth,
            vector_description=vector_description,
            marker_size=marker_size,
        )
        return

    def metrics(
        self,
        dataset_id: str,
        vector_field: str,
        alias: str,
        ground_truth_field: str = None,
    ):

        """
        Determine the performance of clusters through the Silhouette Score, and optionally against ground truth labels through Rand Index, Homogeneity and Completeness

        Parameters
        ----------
        dataset_id : string
            Unique name of dataset
        vector_field: string
            The vector field that was clustered upon
        alias: string
            The alias of the clustered labels
        ground_truth_field: string
            The field to use as ground truth
        """

        (
            vectors,
            cluster_labels,
            ground_truth,
            vector_description,
        ) = self._get_cluster_documents(
            dataset_id=dataset_id,
            vector_field=vector_field,
            alias=alias,
            ground_truth_field=ground_truth_field,
        )

        return self.metrics_from_documents(
            vectors=vectors, cluster_labels=cluster_labels, ground_truth=ground_truth
        )

    def distribution(
        self,
        dataset_id: str,
        vector_field: str,
        alias: str,
        ground_truth_field: str = None,
        transpose=False,
    ):

        """
        Determine the distribution of clusters, optionally against the ground truth

        Parameters
        ----------
        dataset_id : string
            Unique name of dataset
        vector_field: string
            The vector field that was clustered upon
        alias: string
            The alias of the clustered labels
        ground_truth_field: string
            The field to use as ground truth
        transpose: bool
            Whether to transpose cluster and ground truth perspectives

        """

        (
            vectors,
            cluster_labels,
            ground_truth,
            vector_description,
        ) = self._get_cluster_documents(
            dataset_id=dataset_id,
            vector_field=vector_field,
            alias=alias,
            ground_truth_field=ground_truth_field,
            get_vectors=False,
        )

        if ground_truth_field:
            if transpose:
                return self.label_joint_distribution_from_documents(
                    cluster_labels, ground_truth
                )
            else:
                return self.label_joint_distribution_from_documents(
                    ground_truth, cluster_labels
                )

        else:
            return self.label_distribution_from_documents(cluster_labels)

    def centroid_distances(
        self,
        dataset_id: str,
        vector_field: str,
        alias: str,
        distance_measure_mode: CENTROID_DISTANCES = "cosine",
        callable_distance=None,
    ):

        """
        Determine the distances of centroid from each other

        Parameters
        ----------
        dataset_id : string
            Unique name of dataset
        vector_field: string
            The vector field that was clustered upon
        alias: string
            The alias of the clustered labels
        distance_measure_mode : string
            Distance measure to compare cluster centroids
        callable_distance: func
            Optional function to use for distance measure

        """

        centroid_response = self.services.cluster.centroids.list(
            dataset_id, [vector_field], alias, include_vector=True
        )

        centroids = {i["_id"]: i[vector_field] for i in centroid_response["documents"]}

        return self.centroid_distances_from_documents(
            centroids,
            distance_measure_mode=distance_measure_mode,
            callable_distance=callable_distance,
        )

    def _get_cluster_documents(
        self,
        dataset_id: str,
        vector_field: str,
        alias: str,
        ground_truth_field: str = None,
        description_fields: list = [],
        get_vectors=True,
    ):

        """
        Return vectors, cluster labels, ground truth labels and other fields
        """

        cluster_field = f"_cluster_.{vector_field}.{alias}"

        if ground_truth_field:
            ground_truth_select_field = [ground_truth_field]
        else:
            ground_truth_select_field = []

        if get_vectors:
            vector_select_field = [vector_field]
        else:
            vector_select_field = []

        documents = self.get_all_documents(
            dataset_id,
            chunk_size=1000,
            select_fields=["_id", cluster_field]
            + vector_select_field
            + ground_truth_select_field
            + description_fields,
            filters=[
                {
                    "field": cluster_field,
                    "filter_type": "exists",
                    "condition": "==",
                    "condition_value": "",
                }
            ],
        )

        # Get cluster labels
        cluster_labels = self.get_field_across_documents(cluster_field, documents)

        # Get vectors
        if get_vectors:
            vectors = self.get_field_across_documents(vector_field, documents)
        else:
            vectors = None

        # Get ground truth
        if ground_truth_field:
            ground_truth = self.get_field_across_documents(
                ground_truth_field, documents
            )
        else:
            ground_truth = None

        # Get vector description
        if len(description_fields) > 0:
            vector_description: Optional[Dict] = {
                field: self.get_field_across_documents(field, documents)
                for field in description_fields
            }
        else:
            vector_description = None

        return vectors, cluster_labels, ground_truth, vector_description

    @staticmethod
    def plot_from_documents(
        vectors: list,
        cluster_labels: list,
        ground_truth: list = None,
        vector_description: dict = None,
        marker_size: int = 5,
    ):

        """
        Plot the vectors in a collection to compare performance of cluster labels, optionally, against ground truth labels

        Parameters
        ----------
        vectors : list
            List of vectors which were clustered upon
        cluster_labels: list
            List of cluster labels corresponding to the vectors
        ground_truth: list
            List of ground truth labels for the vectors
        vector_description : dict
            Dictionary of fields and their values to describe the vectors
        marker_size: int
            Size of scatterplot marker
        """
        import plotly.graph_objs as go

        vector_dr = DimReduction.dim_reduce(
            vectors=np.array(vectors), dr="pca", dr_args=None, dims=3
        )
        embedding_df = pd.DataFrame(
            {"x": vector_dr[:, 0], "y": vector_dr[:, 1], "z": vector_dr[:, 2]}
        )

        embedding_df = pd.concat(
            [
                embedding_df,
                pd.DataFrame([{"Predicted Cluster": i} for i in cluster_labels]),
            ],
            axis=1,
        )
        hover_label = ["Predicted Cluster"]

        if ground_truth:
            embedding_df = pd.concat(
                [
                    embedding_df,
                    pd.DataFrame([{"Ground Truth": i} for i in ground_truth]),
                ],
                axis=1,
            )
            hover_label += ["Ground Truth"]

        if vector_description:
            for k, v in vector_description.items():
                embedding_df = pd.concat(
                    [embedding_df, pd.DataFrame([{k: i} for i in v])], axis=1
                )
                hover_label += [k]

        # Plot Cluster
        cluster_data = []
        cluster_groups = embedding_df.groupby("Predicted Cluster")
        for idx, val in cluster_groups:
            cluster_data.append(
                ClusterEvaluate._generate_plot(val, hover_label, marker_size)
            )

        cluster_fig = go.Figure(
            data=cluster_data, layout=ClusterEvaluate._generate_layout()
        )
        cluster_fig.update_layout(title={"text": "Cluster", "font": {"size": 30}})
        cluster_fig.show()

        # Plot Ground Truth
        if ground_truth:
            ground_truth_data = []
            ground_truth_groups = embedding_df.groupby("Ground Truth")
            for idx, val in ground_truth_groups:
                ground_truth_data.append(
                    ClusterEvaluate._generate_plot(val, hover_label, marker_size)
                )

            ground_truth_fig = go.Figure(
                data=ground_truth_data, layout=ClusterEvaluate._generate_layout()
            )
            ground_truth_fig.update_layout(
                title={"text": "Ground Truth", "font": {"size": 30}}
            )
            ground_truth_fig.show()

        return

    @staticmethod
    def metrics_from_documents(vectors, cluster_labels, ground_truth=None):
        """
        Determine the performance of clusters through the Silhouette Score, and optionally against ground truth labels through Rand Index, Homogeneity and Completeness

        Parameters
        ----------
        vectors : list
            List of vectors which were clustered upon
        cluster_labels: list
            List of cluster labels corresponding to the vectors
        ground_truth: list
            List of ground truth labels for the vectors
        """
        metrics_list = []
        metrics_list.append(
            {
                "Metric": "Silhouette Score",
                "Value": ClusterEvaluate.silhouette_score(vectors, cluster_labels),
                "Description": METRIC_DESCRIPTION["Silhouette Score"],
            }
        )
        if ground_truth:
            metrics_list.append(
                {
                    "Metric": "Rand Score",
                    "Value": ClusterEvaluate.adjusted_rand_score(
                        ground_truth, cluster_labels
                    ),
                    "Description": METRIC_DESCRIPTION["Rand Score"],
                }
            )
            metrics_list.append(
                {
                    "Metric": "Homogeneity",
                    "Value": ClusterEvaluate.homogeneity_score(
                        ground_truth, cluster_labels
                    ),
                    "Description": METRIC_DESCRIPTION["Homogeneity"],
                }
            )
            metrics_list.append(
                {
                    "Metric": "Completeness",
                    "Value": ClusterEvaluate.completeness_score(
                        ground_truth, cluster_labels
                    ),
                    "Description": METRIC_DESCRIPTION["Completeness"],
                }
            )
        return metrics_list

    @staticmethod
    def label_distribution_from_documents(label):
        """
        Determine the distribution of a label

        Parameters
        ----------
        label : list
            List of labels
        """

        label_sparsity = Counter(label)
        return dict(label_sparsity)

    @staticmethod
    def label_joint_distribution_from_documents(label_1, label_2):
        """
        Determine the distribution of a label against another label

        Parameters
        ----------
        label_1 : list
            List of labels
        label_2 : list
            List of labels
        """
        cluster_matches = {}
        for i in list(set(label_1)):
            matches = [j == i for j in label_1]
            result = [label for label, match in zip(label_2, matches) if match == True]
            cluster_matches[i] = result

        label_distribution = {
            k: {i: len([j for j in v if j == i]) / len(v) for i in list(set(label_2))}
            for k, v in cluster_matches.items()
        }

        label_distribution = {k: sort_dict(v) for k, v in label_distribution.items()}

        return label_distribution

    @staticmethod
    def centroid_distances_from_documents(
        centroids,
        distance_measure_mode: CENTROID_DISTANCES = "cosine",
        callable_distance=None,
    ):
        """
        Determine the distances of centroid from each other

        Parameters
        ----------
        centroids : dict
            Dictionary containing cluster name and centroid
        distance_measure_mode : string
            Distance measure to compare cluster centroids
        callable_distance: func
            Optional function to use for distance measure

        """
        import scipy.spatial.distance as spatial_distance

        df = pd.DataFrame(columns=centroids.keys(), index=centroids.keys())
        for cluster1 in centroids.keys():
            for cluster2 in centroids.keys():
                if callable_distance:
                    df.loc[cluster1, cluster2] = callable_distance(
                        centroids[cluster1], centroids[cluster2]
                    )
                elif distance_measure_mode == "cosine":
                    df.loc[cluster1, cluster2] = 1 - spatial_distance.cosine(
                        centroids[cluster1], centroids[cluster2]
                    )
                elif distance_measure_mode == "l2":
                    df.loc[cluster1, cluster2] = spatial_distance.euclidean(
                        centroids[cluster1], centroids[cluster2]
                    )
                else:
                    raise ValueError(
                        "Need valid distance measure mode or callable distance"
                    )
        return df.astype("float").to_dict()

    @staticmethod
    def silhouette_score(vectors, cluster_labels):
        return silhouette_score(vectors, cluster_labels)

    @staticmethod
    def adjusted_rand_score(ground_truth, cluster_labels):
        return adjusted_rand_score(ground_truth, cluster_labels)

    @staticmethod
    def completeness_score(ground_truth, cluster_labels):
        return completeness_score(ground_truth, cluster_labels)

    @staticmethod
    def homogeneity_score(ground_truth, cluster_labels):
        return homogeneity_score(ground_truth, cluster_labels)

    @staticmethod
    def _generate_layout():
        import plotly.graph_objects as go

        axes_3d = {
            "title": "",
            "backgroundcolor": "#ffffff",
            "showgrid": False,
            "showticklabels": False,
        }

        layout = go.Layout(
            scene={"xaxis": axes_3d, "yaxis": axes_3d, "zaxis": axes_3d},
            plot_bgcolor="#FFF",
        )
        return layout

    @staticmethod
    def _generate_plot(df, hover_label, marker_size):
        import plotly.graph_objects as go

        custom_data = df[hover_label]
        custom_data_hover = [
            f"{c}: %{{customdata[{i}]}}" for i, c in enumerate(hover_label)
        ]
        coord_info = "X: %{x}   Y: %{y}   Z: %{z}"
        hovertemplate = (
            "<br>".join(
                [
                    coord_info,
                ]
                + custom_data_hover
            )
            + "<extra></extra>"
        )
        scatter_args = {
            "x": df["x"],
            "y": df["y"],
            "z": df["z"],
            "showlegend": False,
            "mode": "markers",
            "marker": {"size": marker_size, "symbol": "circle", "opacity": 0.75},
            "customdata": custom_data,
            "hovertemplate": hovertemplate,
        }

        scatter = go.Scatter3d(**scatter_args)
        return scatter
