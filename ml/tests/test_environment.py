"""
Environment Verification and Sanity Tests
Validates that all foundational ML libraries and runtimes are correctly installed and operational.
"""

import sys
import pytest


def test_python_version():
    """Verify Python runtime meets minimum version constraint (>= 3.10)."""
    assert sys.version_info >= (3, 10), f"Python version {sys.version_info} must be >= 3.10"


def test_core_numeric_libraries():
    """Verify NumPy and Pandas can be imported and execute basic operations."""
    import numpy as np
    import pandas as pd

    arr = np.array([1.0, 2.0, 3.0, 4.0])
    assert arr.mean() == 2.5

    df = pd.DataFrame({"sensor_temp": [300.1, 301.2, 302.5], "status": [0, 0, 1]})
    assert len(df) == 3
    assert "sensor_temp" in df.columns


def test_visualization_libraries():
    """Verify Matplotlib and Seaborn can be imported."""
    import matplotlib
    import seaborn as sns

    assert matplotlib.__version__ is not None
    assert sns.__version__ is not None


def test_machine_learning_libraries():
    """Verify Scikit-learn, XGBoost, and Joblib can be imported and initialized."""
    import sklearn
    from sklearn.linear_model import LogisticRegression
    import xgboost as xgb
    import joblib

    clf = LogisticRegression()
    assert clf is not None

    xgb_clf = xgb.XGBClassifier(n_estimators=10, max_depth=2, eval_metric="logloss")
    assert xgb_clf is not None
    assert joblib.__version__ is not None


def test_explainability_library():
    """Verify SHAP can be imported."""
    import shap

    assert shap.__version__ is not None


def test_jupyterlab_installed():
    """Verify JupyterLab package is present."""
    import jupyterlab

    assert jupyterlab.__version__ is not None

