"""
Root Architecture Smoke Test
Validates that required project directories and documentation files exist.
"""

from pathlib import Path


def test_project_structure_exists():
    """Verify core directories are present in the project tree."""
    root = Path(__file__).resolve().parent.parent

    expected_directories = [
        root / "frontend",
        root / "backend",
        root / "ml",
        root / "ml" / "datasets" / "raw",
        root / "ml" / "datasets" / "processed",
        root / "ml" / "notebooks",
        root / "ml" / "experiments",
        root / "ml" / "src" / "data",
        root / "ml" / "src" / "preprocessing",
        root / "ml" / "src" / "features",
        root / "ml" / "src" / "models",
        root / "ml" / "src" / "evaluation",
        root / "ml" / "src" / "utils",
        root / "ml" / "artifacts",
        root / "ml" / "tests",
        root / "docs",
        root / "infra" / "docker",
        root / "tests",
    ]

    for directory in expected_directories:
        assert directory.is_dir(), f"Expected directory does not exist: {directory}"


def test_documentation_and_config_files_exist():
    """Verify essential governance and config files are present."""
    root = Path(__file__).resolve().parent.parent

    expected_files = [
        root / "docs" / "PRD.md",
        root / "docs" / "DATASET_NOTES.md",
        root / "docs" / "ML_EXPERIMENT_LOG.md",
        root / ".env.example",
        root / ".gitignore",
        root / "README.md",
        root / "ml" / "requirements.txt",
    ]

    for file_path in expected_files:
        assert file_path.is_file(), f"Expected file does not exist: {file_path}"

