"""access the client via this class
"""
import getpass
import os
from typing import Optional

from doc_utils.doc_utils import DocUtils

from relevanceai.batch.client import BatchAPIClient
from relevanceai.config import CONFIG
from relevanceai.errors import APIError

vis_requirements = False
try:
    from relevanceai.visualise.projector import Projector
    vis_requirements = True
except ModuleNotFoundError as e:
    pass

def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

class Client(BatchAPIClient, DocUtils):
    """Python Client for Relevance AI's relevanceai"""

    WELCOME_MESSAGE = """Welcome to the RelevanceAI Python SDK"""
    FAIL_MESSAGE = """Your API key is invalid. Please login again"""

    def __init__(
        self,
        project: Optional[str]=os.getenv("VDB_PROJECT", None),
        api_key: Optional[str]=os.getenv("VDB_API_KEY", None),
        base_url: Optional[str]="https://gateway-api-aueast.relevance.ai/v1/",
        verbose: bool=True
    ):

        if project is None or api_key is None:
            project, api_key = Client.token_to_auth(verbose=verbose)
            # raise ValueError(
            #     "It seems you are missing an API key, "
            #     + "you can sign up for an API key following the instructions here: "
            #     + "https://discovery.relevance.ai/reference/usage"
            # )

        # if (
        #     self.datasets.list(
        #         verbose=False, output_format=None, retries=1
        #     ).status_code
        #     == 200
        # ):
        #     if verbose: self.logger.success(self.WELCOME_MESSAGE)
        # else:
        # raise APIError(self.FAIL_MESSAGE)
        if verbose: self.logger.success(self.WELCOME_MESSAGE)

        super().__init__(project, api_key, base_url) # type: ignore
        if vis_requirements:
            self.projector = Projector(project, api_key, base_url)

    @staticmethod
    def token_to_auth(verbose=True):
        if verbose:
            print("To find your API credentials, sign up at our login page and head to https://cloud.relevance.ai/settings.")
        token = getpass.getpass(
            "Paste your project and API key in the format: of `project:api_key` here:"
        )
        project = token.split(":")[0]
        api_key = token.split(":")[1]
        return project, api_key

    @staticmethod
    def login(
        self,
        base_url: str = "https://gateway-api-aueast.relevance.ai/v1/",
        verbose: bool = True,
    ):
        """Preferred login method for demos and interactive usage."""
        project, api_key = Client.token_to_auth()
        return Client(
            project=project, api_key=api_key, base_url=base_url, verbose=verbose
        )

    @property
    def auth_header(self):
        return {"Authorization": self.project + ":" + self.api_key}
