# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import json
import warnings

import plotly.graph_objs as go

from dataclasses import dataclass

from relevanceai.base import Base
from relevanceai.visualise.constants import *
from relevanceai.visualise.dataset import Dataset
from relevanceai.visualise.cluster import Cluster
from relevanceai.visualise.dim_reduction import DimReduction 



@dataclass
class Projector(Base):
    """
        Projector class.

        Example: 
            >>> from relevanceai import Client
            >>> project = input()
            >>> api_key = input()
            >>> client = Client(project, api_key)
            >>> client.projector.plot(
                    dataset_id, vector_field, number_of_points_to_render
                    dr, dr_args, dims,
                    cluster, cluster_args,
                    vector_label, vector_label_char_length,
                    color_label, hover_label
                    )
    """

    def __init__(self, project, api_key, base_url):
        self.project = project
        self.api_key = api_key
        self.base_url = base_url

        # self.docs = dataset
        # self.dataset_id = dataset.dataset_id
        # self.vector_fields = dataset.vector_fields
        # self.data = dataset.data

        self.base_args = {
            "project": self.project, 
            "api_key": self.api_key, 
            "base_url": self.base_url,
        }
        super().__init__(**self.base_args)


    def _prepare_labels(
        self,
        data: List[JSONDict],
        vector_label: str,
        vector_field: str,
    ):
        """
        Prepare labels
        """
        self.logger.info(f'Preparing {vector_label} ...')
        labels = np.array(
            [
                data[i][vector_label].replace(",", "")
                for i, _ in enumerate(data)
                if data[i].get(vector_field)
            ]
        )
        _labels = set(labels)
        return labels, _labels


    def _generate_fig(
        self,
        embedding_df: pd.DataFrame,
        legend: Union[None, str],
    ) -> go.Figure:
        '''
        Generates the 3D scatter plot 
        '''
        if self.colour_label:
            data = []
            groups = embedding_df.groupby(legend)
            for idx, val in groups:
                scatter = go.Scatter3d(
                    name=idx,
                    x=val['x'],
                    y=val['y'],
                    z=val['z'],
                    text=[ idx for _ in range(val['x'].shape[0]) ],
                    textposition='top center',
                    mode='markers',
                    marker=dict(size=3, symbol='circle'),
                )
                data.append(scatter)
        else:
            if self.vector_label:
                plot_mode ='text+markers'
                text_labels = embedding_df['labels'].apply(lambda x: x[:self.vector_label_char_length]+'...')
            else:
                plot_mode = 'markers'
                text_labels = None

            ## TODO: We can change this later to show top 100 neighbours of a selected word
            #  # Regular displays the full scatter plot with only circles
            # if wordemb_display_mode == 'regular':
            #     plot_mode = 'markers'
            # # Nearest Neighbors displays only the 200 nearest neighbors of the selected_word, in text rather than circles
            # elif wordemb_display_mode == 'neighbors':
            #     if not selected_word:
            #         return go.Figure()
            #     plot_mode = 'text'
            #     # Get the nearest neighbors indices
            #     dataset = data_dict[dataset_name].set_index('0')
            #     selected_vec = dataset.loc[selected_word]

            #     nearest_neighbours = get_nearest_neighbours(
            #                             dataset=dataset, 
            #                             selected_vec=selected_vec,
            #                             distance_measure_mode=distance_measure_mode,  
            #                             )

            #     neighbors_idx = nearest_neighbours[:100].index
            #     embedding_df =  embedding_df.loc[neighbors_idx]

            scatter = go.Scatter3d(
                name=str(embedding_df.index),
                x=embedding_df['x'],
                y=embedding_df['y'],
                z=embedding_df['z'],
                text=text_labels,
                textposition='middle center',
                showlegend=False,
                mode=plot_mode,
                marker=dict(size=3, color=RELEVANCEAI_BLUE, symbol='circle'),
            )
            data=[scatter]

        '''
        Generating figure
        '''
        plot_title = f"{self.dataset_id}: {len(embedding_df)} points<br>Vector Label: {self.vector_label}<br>Vector Field: {self.vector_field}"

        axes = dict(title='', showgrid=True, zeroline=False, showticklabels=False)
        layout = go.Layout(
            margin=dict(l=0, r=0, b=0, t=0),
            scene=dict(xaxis=axes, yaxis=axes, zaxis=axes),
        )
        
        fig = go.Figure(data=data, layout=layout)
        fig.update_layout(title={
            'text': plot_title,
            'y':0.1,
            'x':0,
            'xanchor': 'left',
            'yanchor': 'bottom'}
        )

        '''
        Updating hover label
        '''
        if not self.hover_label and self.vector_label: self.hover_label = [self.vector_label]
        if self.hover_label:
            fig.update_traces(customdata=self.dataset.detail[self.hover_label])
            fig.update_traces(hovertemplate='%{customdata}')
            custom_data_hover = [f"{c}: %{{customdata[{i}]}}" for i, c in enumerate(self.hover_label) 
                                if self.dataset.valid_label_name(c)]
            fig.update_traces(
                hovertemplate="<br>".join([
                    "X: %{x}",
                    "Y: %{y}",
                ] + custom_data_hover
                )
            )
        return fig


    def plot(
        self,
        dataset_id: str,
        vector_field: str,
        number_of_points_to_render: int = 1000,
        random_state: int = 42,

        ### Dimensionality reduction args
        dr: DIM_REDUCTION = "pca",
        dr_args: Union[None, JSONDict] = DIM_REDUCTION_DEFAULT_ARGS['pca'],
        dims: Literal[2, 3] = 3,

        ### Cluster args
        cluster: CLUSTER = None,
        cluster_args: Union[None, JSONDict] = {"n_init" : 20},

        ### Plot rendering args
        vector_label: Union[None, str] = None,
        vector_label_char_length: Union[None, int] = 12,
        colour_label: Union[None, str] = None,  
        hover_label: Union[None, List[str]] = None,
    ):
        """
        Plot function for Embedding Projector class

        Example: 
            >>> from relevanceai import Client
            >>> project = input()
            >>> api_key = input()
            >>> client = Client(project, api_key)
            >>> client.projector.plot(
                    dataset_id, vector_field, random_seed, number_of_points_to_render
                    dr, dr_args, dims,
                    cluster, cluster_args,
                    vector_label, vector_label_char_length,
                    color_label, hover_label
                    )
        """                 
        self.dataset_id = dataset_id
        self.vector_label = vector_label
        self.vector_field = vector_field
        self.random_state = random_state
        self.vector_label_char_length = vector_label_char_length
        self.colour_label = colour_label
        self.hover_label = hover_label

        if vector_label is None:
            warnings.warn(f'A vector label has not been specified.')
        
        if number_of_points_to_render > 1000:
            warnings.warn(f'You are rendering over 1000 points, this may take some time ...')
        
        number_of_documents = None if number_of_points_to_render == -1 else number_of_points_to_render
        self.dataset = Dataset(**self.base_args, 
                                dataset_id=dataset_id, number_of_documents=number_of_documents, 
                                ## TODO: Fix bug where `cursor` is not returned if `random_state`` is set
                                # random_state=random_state 
                                )

        self.vector_fields = self.dataset.vector_fields
        self.docs = self.dataset.docs

        if self.dataset.valid_vector_name(vector_field):
            dr = DimReduction(**self.base_args, data=self.docs, 
                                vector_label=self.vector_label, vector_field=self.vector_field, 
                                dr=dr, dr_args=dr_args, dims=dims
                                )
            self.vectors = dr.vectors
            self.vectors_dr = dr.vectors_dr
            points = { 'x': self.vectors_dr[:,0], 
                        'y': self.vectors_dr[:,1], 
                        'z': self.vectors_dr[:,2]}
            self.embedding_df = pd.DataFrame(points)

            if self.vector_label and self.dataset.valid_label_name(self.vector_label):
                self.labels, self._labels = self._prepare_labels(data=self.docs, 
                                vector_field=self.vector_field, vector_label=self.vector_label)
                self.embedding_df.index = self.labels
                self.embedding_df['labels'] = self.labels
            
            self.legend = None
            if self.colour_label and self.dataset.valid_label_name(self.colour_label):
                self.labels, self._labels = self._prepare_labels(data=self.docs, 
                                vector_field=self.vector_field, vector_label=self.colour_label)
                self.embedding_df.index = self.labels
                self.embedding_df['labels'] = self.labels
                self.legend = 'labels'
        
            if cluster:
                cluster = Cluster(**self.base_args,
                    vectors=self.vectors, cluster=cluster, cluster_args=cluster_args)
                self.cluster_labels = cluster.cluster_labels
                self.embedding_df['cluster_labels'] = self.cluster_labels
                self.legend = 'cluster_labels'

            return self._generate_fig(embedding_df=self.embedding_df, legend=self.legend)

    