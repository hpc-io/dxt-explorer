Build Instructions
===================================

-----------------------------------
Dependencies
-----------------------------------

DXT Explorer requires a Darshan log file collected with tracing data. The Darshan eXtended Tracing (DXT) support is disabled by default in Darshan. To enable tracing globally for all files, you need to set the ``DXT_ENABLE_IO_TRACE`` environment variable as follows:

.. code-block:: bash

    export DXT_ENABLE_IO_TRACE=1

To enable tracing for particular files you can refer to the Darshan's documentation page.

To use DXT Explorer, you need to have Python 3 and R already installed in your system, and install some required Python libraries:

.. code-block:: bash

    pip install -r requirements.txt

In the first execution ever, DXT Explorer will automatically download any missing R packages required, thus it might take longer to generate the plot. This is all done at user level, without any need for elevated priviledges.

You also need to have Darshan Utils installed (``darshan-dxt-parser``) and available in your path.

.. note::

    In Summit, if you want to run DXT Explorer, you need to load some modules:

    .. code-block:: bash

        module load python r cairo

-----------------------------------
Docker Image
-----------------------------------

You can also use a Docker image already pre-configured with all dependencies to run DXT Explorer:

.. code-block:: bash

    docker pull hpcio/dxt-explorer

Since we need to provide an input file and access the generated ``.html`` files, make sure you are mounting your current directory in the container and removing the container after using it. You can pass the same arguments described above, after the container name (``dxt-explorer``).

.. code-block:: bash

    docker run --rm --mount \
        type=bind,source="$(PWD)",target="/dxt-explorer/darshan" \
        dxt-explorer darshan/<FILE>.darshan
