import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    ILMU_API_KEY = os.getenv('ILMU_API_KEY', 'sk-ce3d5c2e0663d672d31a996832e91daf63d255cf8f69d588')
    ILMU_BASE_URL = os.getenv('ILMU_BASE_URL', 'https://api.ilmu.ai/v1')
    ILMU_MODEL = os.getenv('ILMU_MODEL', 'ilmu-glm-5.1')
