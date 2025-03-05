"""GhostForge setup configuration."""

import os
from setuptools import setup, find_packages

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# Development requirements
dev_requirements = [
    "black>=23.12.1",
    "pylint>=3.0.3",
    "pytest>=7.4.3",
    "pytest-cov>=4.1.0",
]

setup(
    name="ghostforge-ai",
    version="0.1.0",
    author="David Maynor",
    author_email="dmaynor@gmail.com",
    description="An AI-powered troubleshooting assistant for DevOps",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dmaynor/ghostforge",
    project_urls={
        "Bug Tracker": "https://github.com/dmaynor/ghostforge/issues",
        "Documentation": "https://github.com/dmaynor/ghostforge#readme",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
    },
    entry_points={
        "console_scripts": [
            "ghostforge=ghostforge.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "ghostforge": [
            "prompts/*.yaml",
            "recipes/*.yaml",
        ],
    },
    data_files=[
        ("", ["README.md", "requirements.txt"]),
    ],
) 