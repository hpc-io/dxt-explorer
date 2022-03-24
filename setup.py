import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

with open("requirements.txt") as f:
    requirements = f.readlines()

setuptools.setup(
    name="dxt-explorer",
    keywords="dxt-explorer",
    version="1.2",
    author="Jean Luca Bez, Suren Byna",
    author_email="jlbez@lbl.gov, sbyna@lbl.gov",
    description="DXT Explorer is an interactive web-based log analysis tool to visualize Darshan DXT logs and help understand the I/O behavior of applications.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hpc-io/dxt-explorer",
    install_requires=requirements,
    packages=setuptools.find_packages(),
    scripts=[
    	"dxt-explorer"
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3 :: Only"
    ],
    python_requires='>=3.6',
)