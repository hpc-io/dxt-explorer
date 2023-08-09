OST Usage Operation Plot
===================================

Once the dependencies and DXT Explorer have been installed:

.. code-block:: bash

   dxt-explorer -oo DARSHAN_FILE_COLLECTED_WITH_DXT_ENABLE.darshan

.. image:: _static/images/base-ost-usage-over-time.png
  :width: 800
  :alt: OST Usage Operation Plot

This will generate the ``ost-usage-operation.html`` plot. The ``ost-usage-operation.html`` plot shows the usage of each OST server for read and write operations throughout the runtime of the application.

``Warning``: This plot will only be generated if the application was exectued on Lustre File System and Darshan collected those metrics. 

This is the expected console output when calling DXT Explorer:

.. code-block:: text

   2022-11-02 12:58:22,979 dxt - INFO - FILE: <Filename> (ID <File ID>)
   2022-11-02 12:58:22,979 dxt - INFO - generating dataframes
   2022-11-02 12:58:26,681 dxt - INFO - generating interactive OST usage operation plot for: <Filename>
   2022-11-02 12:58:30,826 dxt - INFO - SUCCESS: <Path to the newly created operation.html>
   2022-11-02 12:58:30,834 dxt - INFO - SUCCESS: <Path to the newly created index.html>
   2022-11-02 12:58:30,834 dxt - INFO - You can open the index.html file in your browser to interactively explore all plots
