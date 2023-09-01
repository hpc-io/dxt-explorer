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
    "-s",
    "--start",
    type="int",
    default=None,
    help="Mark trace start time",
    metavar="start",
)
parser.add_option(
    "-e", "--end", type="int", default=None, help="Mark trace end time", metavar="end"
)
parser.add_option(
    "-n",
    "--from",
    type="int",
    default=None,
    help="Display trace from rank N",
    metavar="from",
)
parser.add_option(
    "-m",
    "--to",
    type="int",
    default=None,
    help="Display trace up torank N",
    metavar="to",
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

duration = max(df["end"]) - min(df["start"])

minimum = 0
maximum = max(df["end"])

minimum_limit = -0.05
maximum_limit = max(df["end"]) + (duration * 0.05)

rank_gap = max(df["rank"]) * 0.075
maximum_rank = max(df["rank"])

if options["start"] is not None:
    df = df[df["start"] >= options["start"]]

if options["end"] is not None:
    df = df[df["end"] <= options["end"]]

if options["from"] is not None:
    df = df[df["rank"] >= options["from"]]

if options["to"] is not None:
    df = df[df["rank"] <= options["to"]]

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
values = [
    "0-100",
    "101-1K",
    "1K-10K",
    "10K-100K",
    "100K-1M",
    "1M-4M",
    "4M-10M",
    "10M-100M",
    "100M-1G",
    "1G+",
]
df["bin"] = np.select(conditions, values)

fig = px.scatter(
    df,
    x="start",
    y="rank",
    color="bin",
    error_x="duration",
    range_x=(0 - (duration * 0.05), maximum_limit),
    range_y=(0 - rank_gap, maximum_rank + rank_gap),
    facet_row="api",
    custom_data=["label"],
    template="plotly_white",
    color_discrete_sequence=[
        "#b82a14",
        "#b86512",
        "#d9ae11",
        "#f0ec0a",
        "#9cf00a",
        "#43f00a",
        "#0af0ba",
        "#0acaf0",
        "#0a75f0",
        "#0a21f0",
    ],
    category_orders={
        "api": ["MPIIO", "POSIX"],
        "bin": [
            "0-100",
            "101-1K",
            "1K-10K",
            "10K-100K",
            "100K-1M",
            "1M-4M",
            "4M-10M",
            "10M-100M",
            "100M-1G",
            "1G+",
        ],
    },
)

fig.update_yaxes(matches=None)
fig.update_xaxes(showline=True, linewidth=1, linecolor="black", mirror=True)
fig.update_yaxes(showline=True, linewidth=1, linecolor="black", mirror=True)

fig.update_traces(
    error_x=dict(
        width=0,
    ),
    marker=dict(size=1, autocolorscale=True),
    error_x_symmetric=False,
    hovertemplate="<br>".join(
        [
            "%{customdata[0]}",
        ]
    ),
)

if options["start"] is not None:
    fig.add_vline(x=minimum, line_width=3, line_dash="dash", line_color="black")
    fig.add_vline(
        x=options["start"], line_width=3, line_dash="dash", line_color="black"
    )
    fig.add_vrect(
        x0=minimum,
        x1=options["start"],
        line_width=0,
        fillcolor="grey",
        opacity=0.2,
        annotation_text="TIMELINE IS TRUNCATED",
        annotation_position="inside right",
    )

if options["end"] is not None:
    fig.add_vline(x=options["end"], line_width=3, line_dash="dash", line_color="black")
    fig.add_vline(x=maximum_limit, line_width=3, line_dash="dash", line_color="black")
    fig.add_vrect(
        x0=options["end"],
        x1=maximum_limit,
        line_width=0,
        fillcolor="grey",
        opacity=0.2,
        annotation_text="TIMELINE IS TRUNCATED",
        annotation_position="inside left",
    )

if options["from"] is not None:
    fig.add_hline(y=0, line_width=3, line_dash="dash", line_color="black")
    fig.add_hline(y=options["from"], line_width=3, line_dash="dash", line_color="black")
    fig.add_hrect(
        y0=0,
        y1=options["from"],
        line_width=0,
        fillcolor="grey",
        opacity=0.2,
        annotation_text="RANK BEHAVIOUR IS TRUNCATED",
        annotation_position="inside top",
    )

if options["to"] is not None:
    fig.add_hline(y=options["to"], line_width=3, line_dash="dash", line_color="black")
    fig.add_hline(y=maximum_rank, line_width=3, line_dash="dash", line_color="black")
    fig.add_hrect(
        y0=options["to"],
        y1=maximum_rank,
        line_width=0,
        fillcolor="grey",
        opacity=0.2,
        annotation_text="RANK BEHAVIOUR  IS TRUNCATED",
        annotation_position="inside bottom",
    )

fig.add_shape(
    type="line",
    x0=0,
    y0=0,
    x1=0,
    y1=maximum_rank,
    line=dict(
        color="Black",
    ),
    xref="x",
    yref="y",
    row="all",
    col="all",
)

fig.add_shape(
    type="line",
    x0=maximum,
    y0=0,
    x1=maximum,
    y1=maximum_rank,
    line=dict(
        color="Black",
    ),
    xref="x",
    yref="y",
    row="all",
    col="all",
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
    if "POSIX" in annotation.text:
        annotation.text = "POSIX"
    elif "MPIIO" in annotation.text:
        annotation.text = "MPIIO"

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
    title=("Explore <b>Data Transfer Size</b> <br>" + options["identifier"]),
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
