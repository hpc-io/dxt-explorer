import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

with open("requirements.txt") as f:
    requirements = f.readlines()

setuptools.setup(
    name="dxt-explorer",
    keywords="dxt-explorer",
    version="2.0",
    author="Jean Luca Bez, Hammad Ather, Suren Byna",
    author_email="jlbez@lbl.gov, hather@lbl.gov, sbyna@lbl.gov",
    description="DXT Explorer is an interactive web-based log analysis tool to visualize Darshan DXT logs and help understand the I/O behavior.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hpc-io/dxt-explorer",
    install_requires=[
        "numpy>=1.23",
        "Pillow>=9.4.0",
        "plotly>=5.13.0",
        "argparse>=1.4.0",
        "pandas>=1.4.3",
        "pyranges>=0.0.120",
        "darshan",
        "pyarrow>=10.0.1",
        "bs4>=0.0.1",
        "drishti-io>=0.5",
    ],
    include_package_data=True,
    entry_points={"console_scripts": ["dxt-explorer=explorer.dxt:main"]},
    packages=["explorer"],
    package_data={
        "explorer": ["explorer/*.*", "explorer/plots/*.*"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3 :: Only",
    ],
    python_requires=">=3.8",
)
