import os
from tempfile import mkdtemp

from dotenv import load_dotenv

load_dotenv()

# (access token?)
SECRET_KEY = os.getenv("SECRET_KEY") or "development-secret"

DEBUG = False

# 10 = DEBUG, 20 = INFO, 30 = WARNING
LOG_LEVEL = os.getenv("LOG_LEVEL") or 20

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE") or 10000)
ANNO_CHUNK_SIZE = int(os.getenv("ANNO_CHUNK_SIZE") or 500)
PROP_CHUNK_SIZE = int(os.getenv("PROP_CHUNK_SIZE") or 10000)

FILTER_DELETE_SIZE = int(os.getenv("FILTER_DELETE_SIZE") or 2000)

TMP_CACHE = os.path.abspath(mkdtemp(prefix=".sonarCache_"))

ANNO_TOOL_PATH = os.getenv("ANNO_TOOL_PATH", "snpEff")
# SNPSIFT_TOOL_PATH = os.getenv("SNPSIFT_TOOL_PATH","")
# VCF_ONEPERLINE_PATH = os.getenv("VCF_ONEPERLINE_PATH","")

MAX_SUPPORTED_DB_VERSION = 2
SUPPORTED_DB_VERSION = 1.2

# API/Backend
BASE_URL = os.getenv("API_URL") or "http://127.0.0.1:8000/api"

# For sourmash
KSIZE = int(os.getenv("KSIZE") or 11)
SCALED = int(os.getenv("SCALED") or 1)
