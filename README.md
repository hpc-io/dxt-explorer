![DXT Explorer Logo](dxt-explorer.png)

You need to have Python 3 and install some required libraries:

```bash
pip install -r requirements.txt
```

You also need to have Darshan Utils installed (`darshan-dxt-parser`) and available in your path.

Once you have the dependencies installed, you can run:

```bash
python3 explore.py DARSHAN_FILE_COLLECTED_WITH_DXT_ENABLE.darshan
```

```bash
usage: explore.py [-h] [-o OUTFILE] [-t] [-s] darshan
```

It will generate a `explore.html` file with an interactive plot that you can open in any browser to explore.

---

DXT Explorer Copyright (c) 2021, The Regents of the University ofCalifornia, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy). All rights reserved.

If you have questions about your rights to use or distribute this software, please contact Berkeley Lab's Intellectual Property Office at IPO@lbl.gov.

NOTICE.  This Software was developed under funding from the U.S. Department of Energy and the U.S. Government consequently retains certain rights.  As such, the U.S. Government has been granted for itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in the Software to reproduce, distribute copies to the public, prepare derivative works, and perform publicly and display publicly, and to permit others to do so.
