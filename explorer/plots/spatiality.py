import os
import explorer
import numpy as np
import plotly.express as px
import pyarrow.feather as feather

from PIL import Image
from optparse import OptionParser


parser = OptionParser()
parser.add_option(
    "-f",
    "--file",
    type="string",
    default=None,
    help="DXT CSV file name",
    metavar="FILE",
)
parser.add_option(
    "-o",
    "--output",
    type="string",
    default=None,
    help="Name of the output file",
    metavar="output",
)
parser.add_option(
    "-x",
    "--identifier",
    type="string",
    default=None,
    help="Set the identifier of the original file captured by Darshan DXT",
    metavar="identifier",
)

(options, args) = parser.parse_args()
options = vars(options)

df = feather.read_feather(options["file"])

if df.empty:
    quit()

df["duration"] = df["end"] - df["start"]
rank_gap = max(df["rank"]) * 0.075
maximum_rank = max(df["rank"])

if len(df.index) == 0:
    quit()


def paste0():
    label = (
        "Rank: "
        + df["rank"].apply(str)
        + "<br>"
        + "Operation: "
        + df["operation"].apply(str)
        + "<br>"
        + "Duration: "
        + round(df["duration"], 3).apply(str)
        + " seconds<br>"
    )
    label = (
        label
        + "Size: "
        + (df["size"] / 1024).apply(str)
        + " KB<br>"
        + "Offset: "
        + df["offset"].apply(str)
        + "<br>"
        + "Lustre OST: "
    )

    if df["osts"] is None:
        label = label + "-"
    else:
        label = label + df["osts"].apply(str)
    return label


df["label"] = paste0()

df = df[df["api"] == "POSIX"]

conditions = [
    (df["size"] >= 0) & (df["size"] <= 100),
    (df["size"] >= 101) & (df["size"] <= 1000),
    (df["size"] >= 1001) & (df["size"] <= 10000),
    (df["size"] >= 10001) & (df["size"] <= 100000),
    (df["size"] >= 100001) & (df["size"] <= 1000000),
    (df["size"] >= 1000001) & (df["size"] <= 4000000),
    (df["size"] >= 4000001) & (df["size"] <= 10000000),
    (df["size"] >= 10000001) & (df["size"] <= 100000000),
    (df["size"] >= 100000001) & (df["size"] <= 10000000000),
    (df["size"] >= 10000000001),
]

values = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

df["bin"] = np.select(conditions, values)

fig = px.scatter(
    df,
    x="offset",
    y="rank",
    color="bin",
    range_y=(0 - rank_gap, maximum_rank + rank_gap),
    error_x="size",
    facet_row="operation",
    custom_data=["label"],
    template="plotly_white",
    category_orders={"bin": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]},
)

col_names = {
    "0": "0-100",
    "1": "101-1K",
    "2": "1K-10K",
    "3": "10K-100K",
    "4": "100K-1M",
    "5": "1M-4M",
    "6": "4M-10M",
    "7": "10M-100M",
    "8": "100M-1G",
    "9": "1G+",
}
fig.for_each_trace(lambda t: t.update(name=col_names[t.name]))

fig.update_xaxes(showline=True, linewidth=1, linecolor="black", mirror=True)
fig.update_yaxes(showline=True, linewidth=1, linecolor="black", mirror=True)

fig.update_traces(
    error_x=dict(
        width=0,
    ),
    marker=dict(size=1),
    error_x_symmetric=False,
    hovertemplate="<br>".join(
        [
            "%{customdata[0]}",
        ]
    ),
)


path = os.path.abspath(explorer.__file__)
path = path.split("__init__.py")[0]
pyLogo = Image.open(path + "plots/dxt-explorer.png")

fig.add_layout_image(
    dict(
        source=pyLogo,
        xref="paper",
        yref="paper",
        x=0,
        y=1.15,
        sizex=0.2,
        sizey=0.2,
        xanchor="left",
        yanchor="top",
    )
)

fig.for_each_yaxis(lambda yaxis: yaxis.update(title="Rank"))

for annotation in fig.layout.annotations:
    if "write" in annotation.text:
        annotation.text = "Write"
    elif "read" in annotation.text:
        annotation.text = "Read"

fig.update_layout(
    legend=dict(
        itemsizing="constant",
        orientation="h",
        yanchor="bottom",
        y=1.008,
        xanchor="right",
        x=0.98,
    ),
    legend_title="Request Size",
    autosize=False,
    height=1200,
    width=1800,
    margin=dict(r=20, l=20, b=75, t=125),
    title=("Explore <b>Spatiality</b> <br>" + options["identifier"]),
    title_x=0.5,
    title_y=0.98,
    font=dict(size=13, color="#000000"),
    xaxis_title="Runtime (Seconds)",
    xaxis=dict(
        rangeslider=dict(visible=True),
        type="-",
    ),
    xaxis_rangeslider_thickness=0.04,
)

fig.write_html(options["output"])
