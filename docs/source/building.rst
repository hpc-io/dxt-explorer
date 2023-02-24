Build Instructions
===================================

DXT Explorer requires a Darshan log file collected with tracing data. The Darshan eXtended Tracing (DXT) support is disabled by default in Darshan. To enable tracing globally for all files, you need to set the ``DXT_ENABLE_IO_TRACE`` environment variable as follows:

.. code-block:: bash

    export DXT_ENABLE_IO_TRACE=1

To enable tracing for particular files you can refer to the Darshan's documentation page.

-----------------------------------
Installing through git
-----------------------------------

To use DXT Explorer, you first need to get the Darshan version installed on system so that the matching pyDarshan version is installed from pip. To do this, run the following command (make sure you have Python 3 installed on your system):

.. code-block:: bash

    bash prepare.sh

This command will create a constraint.txt file which will contain the pyDarshan version to be installed through pip. 

Run the below command to install some required Python libraries:

.. code-block:: bash

    pip install -r requirements.txt -c constraints.txt

Then install dxt-explorer using the following command:

.. code-block:: bash

    pip install .

You also need to have Darshan Utils installed (``darshan-dxt-parser``) and available in your path.

-----------------------------------
Installing through pip
-----------------------------------

To install through pip, just run the following command:

.. code-block:: bash

    pip install dxt-explorer

.. warning::

    If you are installing dxt-explorer through pip, make sure the Darshan version installed on the machine matches the pyDarshan version installed through pip, otherwise you might get the following error:

    .. code-block:: bash

        darshan.discover_darshan.DarshanVersionError
        
.. note::

    In NERSC systems (i.e., Cori or Perlmutter) you might need to load the Darshan module if it is not already loaded. For other systems, please refer to their documentation to use the correct module name.
    
    .. code-block:: bash
    
        module load darshan
        
-----------------------------------
Build with Spack
-----------------------------------

You can also use Spack to install dxt-explorer:

.. code-block:: bash

    spack install dxt-explorer

.. note::

    Use the following installation guide to install spack on your machine if it is not already installed: https://spack-tutorial.readthedocs.io/en/latest/tutorial_basics.html

-----------------------------------
Docker Image
-----------------------------------

You can also use a Docker image already pre-configured with all dependencies to run DXT Explorer:

.. code-block:: bash

    docker pull hpcio/dxt-explorer

Since we need to provide an input file and access the generated ``.html`` files, make sure you are mounting your current directory in the container and removing the container after using it. You can pass the same arguments described above, after the container name (``dxt-explorer``).

.. code-block:: bash

    docker run --rm --mount \
        type=bind,source="$(pwd)",target="/dxt-explorer" \
        dxt-explorer darshan/<FILE>.darshan

