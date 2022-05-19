#!/usr/bin/env python3

import os
import glob
import pytest

from explore import dxt 

DEBUG = True

PREFIX = '.'

samples = glob.glob('sample/sample.darshan')

@pytest.mark.parametrize('darshan', samples)
def test_list(darshan):
	assert os.path.isfile(darshan) is True

	explorer = dxt.DXT(
		DEBUG
	)

	explorer.list_files(
		darshan
	)
