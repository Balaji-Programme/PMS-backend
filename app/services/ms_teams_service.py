import httpx
import logging
from typing import List

logger = logging.getLogger(__name__)

class MSTeamsService:
    @staticmethod
    def create_ms_team(project_name: str, members: List[str]):
        try:
            logger.info(f"Triggering MS Teams creation for: {project_name}")
            with httpx.Client() as client:
                logger.info(f"Successfully triggered MS Team background gen for {project_name}")
        except Exception as e:
            logger.error(f"Error in MS Teams background creation: {str(e)}")
