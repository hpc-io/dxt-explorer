Spatiality Plot
===================================

Once the dependencies and DXT Explorer have been installed:

.. code-block:: bash

   dxt-explorer -s DARSHAN_FILE_COLLECTED_WITH_DXT_ENABLE.darshan

.. image:: _static/images/spatiality.png
  :width: 800
  :alt: Spatiality Plot

This will generate the base ``spatiality.html`` plot. Spatiality refers to the file offsets between consecutive I/O accesses. Typical spatial access patterns are contiguous, strided, or random. The ``spatiality.html`` plot shows the spatiality of the accesses in file made by each rank. Contextual information link ``Rank``, ``Operation``, ``Duration``, ``Size``, ``Offset``, ``Lustre OST`` can also be seen by hovering over a request. 

This is the expected console output when calling DXT Explorer:

.. code-block:: text

   2022-11-02 12:58:22,979 dxt - INFO - FILE: <Filename> (ID <File ID>)
   2022-11-02 12:58:22,979 dxt - INFO - generating dataframes
   2022-11-02 12:58:26,681 dxt - INFO - generating interactive spatiality for: <Filename>
   2022-11-02 12:58:30,826 dxt - INFO - SUCCESS: <Path to the newly created spatiality.html>
   2022-11-02 12:58:30,834 dxt - INFO - SUCCESS: <Path to the newly created index.html>
   2022-11-02 12:58:30,834 dxt - INFO - You can open the index.html file in your browser to interactively explore all plots

Interactive examples of DXT traces collected from FLASH, E2E, and OpenPMD are available in the `companion repository <https://jeanbez.gitlab.io/pdsw-2021>`_ of our PDSW'21 paper.

