
from src.evaluation.metrics import precision, recall, f1_score

def test_precision():
    assert precision(8, 2) == 0.8

def test_recall():
    assert recall(8, 2) == 0.8

def test_f1():
    assert round(f1_score(0.8, 0.8), 2) == 0.8
