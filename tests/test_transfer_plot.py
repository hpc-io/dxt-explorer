#!/usr/bin/env python3

import os
import glob
import pytest

from explore import dxt 

DEBUG = True

PREFIX = '.'

samples = glob.glob('sample/sample.darshan')

@pytest.mark.parametrize('darshan', samples)
def test_transfer_plot(darshan):
	assert os.path.isfile(darshan) is True

	explorer = dxt.DXT(
		DEBUG
	)

	explorer.run(
		PREFIX,
		darshan,
		True,
		False
	)
