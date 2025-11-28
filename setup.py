"""
LogSim - Semantic Log Compression System
Setup configuration for package installation
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip() 
        for line in requirements_file.read_text(encoding="utf-8").split("\n")
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="logsim",
    version="1.0.0",
    author="Adam Bouafia",
    author_email="adam.bouafia@example.com",
    description="Automatic Schema Extraction & Semantic-Aware Compression for System Logs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/adam-bouafia/LogSim",
    project_urls={
        "Bug Tracker": "https://github.com/adam-bouafia/LogSim/issues",
        "Documentation": "https://github.com/adam-bouafia/LogSim#readme",
        "Source Code": "https://github.com/adam-bouafia/LogSim",
    },
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Logging",
        "Topic :: System :: Archiving :: Compression",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-benchmark>=4.0.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "logsim=logsim.__main__:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
