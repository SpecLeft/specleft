"""Discovery models and infrastructure package."""

from specleft.discovery.models import *  # noqa: F401,F403

from specleft.discovery.config import DiscoveryConfig
from specleft.discovery.context import MinerContext
from specleft.discovery.file_index import DEFAULT_EXCLUDE_DIRS, FileIndex
from specleft.discovery.framework_detector import FrameworkDetector
from specleft.discovery.language_detect import detect_project_languages
from specleft.discovery.language_registry import SUPPORTED_EXTENSIONS, LanguageRegistry
from specleft.discovery.grouping import group_items
from specleft.discovery.spec_writer import generate_draft_specs
from specleft.discovery.pipeline import (
    BaseMiner,
    DiscoveryPipeline,
    build_default_pipeline,
)
