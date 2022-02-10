"""All fixtures go here.
"""
import os
import pytest

import pandas as pd

from relevanceai import Client
from relevanceai.dataset_api import Dataset

import tempfile

from tests.globals.constants import *
from tests.globals.document import *
from tests.globals.documents import *
from tests.globals.objects import *
from tests.globals.datasets import *
from tests.globals.clusterers import *

REGION = os.getenv("TEST_REGION")


@pytest.fixture(scope="session")
def test_project():
    if REGION == "us-east-1":
        return os.getenv("TEST_US_PROJECT")
    return os.getenv("TEST_PROJECT")


@pytest.fixture(scope="session")
def test_api_key():
    if REGION == "us-east-1":
        return os.getenv("TEST_US_API_KEY")
    return os.getenv("TEST_API_KEY")


@pytest.fixture(scope="session")
def test_firebase_uid():
    return "test-user"


@pytest.fixture(scope="session")
def test_client(test_project, test_api_key, test_firebase_uid):
    if REGION is None:
        client = Client(
            project=test_project, api_key=test_api_key, firebase_uid=test_firebase_uid
        )
    else:
        client = Client(
            project=test_project,
            api_key=test_api_key,
            firebase_uid=test_firebase_uid,
            region=REGION,
        )
    # For some reason not resetting to default
    client.config.reset()
    if client.region != "us-east-1":
        raise ValueError("default value aint RIGHT")
    return client


@pytest.fixture(scope="module")
def test_csv_dataset(test_client: Client, vector_documents: List[Dict]):
    test_client.config.reset()
    test_dataset_id = generate_dataset_id()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as csvfile:
        df = pd.DataFrame(vector_documents)
        df.to_csv(csvfile)

        response = test_client._insert_csv(test_dataset_id, csvfile.name)
        yield response, len(vector_documents)
        test_client.datasets.delete(test_dataset_id)


@pytest.fixture(scope="module")
def test_read_df(test_client: Client, vector_documents: List[Dict]):
    test_client.config.reset()
    DATASET_ID = "_sample_df_"
    df = test_client.Dataset(DATASET_ID)
    results = df.upsert_documents(vector_documents)
    yield results
    df.delete()


@pytest.fixture(scope="module")
def test_csv_df(test_df: Dataset, vector_documents: List[Dict]):
    """Sample csv dataset"""
    test_df.config.reset()
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as csvfile:
        df = pd.DataFrame(vector_documents)
        df.to_csv(csvfile)

        response = test_df.insert_csv(csvfile.name)
        yield response, len(vector_documents)
        test_df.delete()
