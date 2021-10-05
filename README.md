<p align="center">
  <img src="https://github.com/hpc-io/dxt-explorer/raw/main/dxt-explorer.png" alt="DXT Explorer"/>
</p>

DXT Explorer is an interactive web-based log analysis tool to visualize Darshan DXT logs and help understand the I/O behavior of applications. Our tool adds an interactive component to Darshan trace analysis that can aid researchers, developers, and end-users to visually inspect their applications' I/O behavior, zoom-in on areas of interest and have a clear picture of where is the I/O problem. 

### Dependencies

The Darshan eXtended Tracing (DXT) support is disabled by default in Darshan. To enable tracing globally for all files, you need to set the `DXT_ENABLE_IO_TRACE ` environment variable as follows:

```bash
export DXT_ENABLE_IO_TRACE=1
```

To enable tracing for particular files you can refer to the Darshan's [documentation](https://www.mcs.anl.gov/research/projects/darshan/docs/darshan-runtime.html#_using_the_darshan_extended_tracing_dxt_module) page.

To use DXT Explorer, you need to have Python 3 and R already installed in your system, and install some required Python libraries:

```bash
pip install -r requirements.txt
```

In the first execution ever, DXT Explorer will automatically download any missing R packages required, thus it might take longer to generate the plot.

You also need to have Darshan Utils installed (`darshan-dxt-parser`) and available in your path.

### Explore!

Once you have the dependencies installed, you can run:

```bash
python3 explore.py DARSHAN_FILE_COLLECTED_WITH_DXT_ENABLE.darshan
```

```bash
usage: explore.py [-h] [-o OUTPUT] [-t] [-s] darshan

DXT Explorer:

positional arguments:
  darshan               Input .darshan file

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Name of the output file
  -t, --transfer        Generate an interactive data transfer explorer
  -s, --spatiality      Generate an interactive spatiality explorer
```

DXT Explorer will generate by default a `explore.html` file with an interactive plot that you can open in any browser to explore. If you enabled the transfer or spatility plots, additional `.html` files will be generated, one for each type.

### Docker Image

You can also use a Docker image already pre-configured with all dependencies to run DXT Explorer:

```bash
docker pull jlbez/dxt-explorer
```

Since we need to provide an input file and access the generated `.html` files, make sure you are mounting your current directory in the container and removing the container after using it. You can pass the same arguments described above, after the container name (`dxt-explorer`).

```bash
docker run --rm --mount \
  type=bind,source="$(PWD)",target="/dxt-explorer/darshan" \
  dxt-explorer darshan/<FILE>.darshan
```

```bash
2021-10-05 03:21:34,907 explore - INFO - darshan-dxt-parser: FOUND
2021-10-05 03:21:34,907 explore - INFO - Rscript: FOUND
2021-10-05 03:21:34,907 explore - INFO - parsing darshan/<FILE>.darshan file
2021-10-05 03:21:35,248 explore - INFO - generating an intermediate CSV file
2021-10-05 03:21:36,240 explore - INFO - generating interactive operation plot
2021-10-05 03:21:54,657 explore - INFO - SUCCESS
```

---

DXT Explorer Copyright (c) 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy). All rights reserved.

If you have questions about your rights to use or distribute this software, please contact Berkeley Lab's Intellectual Property Office at IPO@lbl.gov.

NOTICE.  This Software was developed under funding from the U.S. Department of Energy and the U.S. Government consequently retains certain rights.  As such, the U.S. Government has been granted for itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in the Software to reproduce, distribute copies to the public, prepare derivative works, and perform publicly and display publicly, and to permit others to do so.
