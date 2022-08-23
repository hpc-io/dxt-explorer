Exploring
===================================

Once you have the dependencies and DXT Explorer installed, you can run:

.. code-block:: bash

   dxt-explore DARSHAN_FILE_COLLECTED_WITH_DXT_ENABLE.darshan

.. code-block:: text

   usage: dxt-explorer [-h] [-o OUTPUT] [-t] [-s] [-d] [-l] [--start START] [--end END] [--from START_RANK] [--to END_RANK] [--browser] darshan

   DXT Explorer:

   positional arguments:
     darshan               Input .darshan file

   optional arguments:
     -h, --help            show this help message and exit
     -o OUTPUT, --output OUTPUT
                           Name of the output file
     -t, --transfer        Generate an interactive data transfer explorer
     -s, --spatiality      Generate an interactive spatiality explorer
     -d, --debug           Enable debug mode
     -l, --list            List all the files with trace
     --start START         Report starts from X seconds (e.g., 3.7) from beginning of the job
     --end END             Report ends at X seconds (e.g., 3.9) from beginning of the job
     --from START_RANK     Report start from rank N
     --to END_RANK         Report up to rank M
     --browser             Open the browser with the generated plot

DXT Explorer will generate by default a ``explore.html`` file with an interactive plot that you can open in any browser to explore. If you enabled the transfer or spatiality plots, additional ``.html`` files will be generated, one for each type. You are expected to visualize the following messages in the console:

.. code-block:: text

   2021-10-05 03:21:34,907 explore - INFO - darshan-dxt-parser: FOUND
   2021-10-05 03:21:34,907 explore - INFO - Rscript: FOUND
   2021-10-05 03:21:34,907 explore - INFO - parsing darshan/<FILE>.darshan file
   2021-10-05 03:21:35,248 explore - INFO - generating an intermediate CSV file
   2021-10-05 03:21:36,240 explore - INFO - generating interactive operation plot
   2021-10-05 03:21:54,657 explore - INFO - SUCCESS

You can find a couple of interactive examples of DXT traces collected from FLASH, E2E, and OpenPMD in the `companion repository <https://jeanbez.gitlab.io/pdsw-2021>`_ for our PDSW'21 paper.
