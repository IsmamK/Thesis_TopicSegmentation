"""LECSEG: Lecture Topic Segmentation package."""

__version__ = "0.1.0"

from lecseg.metrics import evaluate, SegmentationScores
from lecseg.models.hierarchical import HierarchicalSegmenter
from lecseg.models.boundary_predictor import TwoStageBoundaryPredictor
from lecseg.models.fusion import ReliabilityWeightedFusion
from lecseg.features.text_embeddings import embed_sentences

__all__ = [
    "evaluate",
    "SegmentationScores",
    "HierarchicalSegmenter",
    "TwoStageBoundaryPredictor",
    "ReliabilityWeightedFusion",
    "embed_sentences",
]
