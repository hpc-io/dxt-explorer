import plotly.express as px
from optparse import OptionParser
from PIL import Image
import pyarrow.feather as feather

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
    help="Display trace up to rank N",
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

if ("POSIX" in df.values) & ("MPIIO" in df.values):
    facet_row = "api"
    category_orders = {"api": ["MPIIO", "POSIX"]}
else:
    facet_row = None
    category_orders = None

fig = px.scatter(
    df,
    x="start",
    y="index",
    range_y=[-0.2, 0.2],
    color="operation",
    error_x="duration",
    render_mode="auto",
    facet_row=facet_row,
    facet_row_spacing=0.1,
    template="plotly_white",
    color_discrete_sequence=["#3c93c2", "#7AF06E", "#f0746e"],
    category_orders=category_orders,
    hover_data={
        "operation": False,
        "start": False,
        "index": False,
        "api": False,
        "fastest_rank": True,
        "fastest_rank_duration": ":.2f",
        "slowest_rank": True,
        "slowest_rank_duration": ":.2f",
    },
)

io_phases_df_mpiio = df[df["api"] == "MPIIO"]

if not io_phases_df_mpiio.empty:
    threshold_mpiio = io_phases_df_mpiio.iloc[0]
    threshold_mpiio = threshold_mpiio["threshold"]

    fig.add_annotation(
        text="Threshold = "
        + str(round(threshold_mpiio, 5))
        + "s"
        + ", Total I/O Phases = "
        + str(len(io_phases_df_mpiio)),
        xref="paper",
        yref="paper",
        x=0,
        y=1.03,
        showarrow=False,
    )

io_phases_df_posix = df[df["api"] == "POSIX"]
if not io_phases_df_posix.empty:
    threshold_posix = io_phases_df_posix.iloc[0]
    threshold_posix = threshold_posix["threshold"]
    fig.add_annotation(
        text="Threshold = "
        + str(round(threshold_posix, 5))
        + "s"
        + ", Total I/O Phases = "
        + str(len(io_phases_df_posix)),
        xref="paper",
        yref="paper",
        x=0,
        y=0.47,
        showarrow=False,
    )

fig.update_xaxes(showline=True, linewidth=1, linecolor="black", mirror=True)
fig.update_yaxes(showline=True, linewidth=1, linecolor="black", mirror=True)
fig.update_yaxes(title="", visible=True, showticklabels=False)

fig.update_traces(
    error_x=dict(width=0, thickness=100, visible=True, symmetric=False),
    marker=dict(
        size=1,
    ),
)

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
    height=900,
    width=1800,
    margin=dict(r=20, l=20, t=200),
    title=("Explore <b>I/O Phases</b> <br>" + options["identifier"]),
    title_x=0.5,
    title_y=0.96,
    font=dict(size=13, color="#000000"),
    xaxis_title="Runtime (Seconds)",
    xaxis=dict(
        rangeslider=dict(visible=False),
        type="-",
    ),
    xaxis_rangeslider_thickness=0.04,
)
pyLogo = Image.open("dxt-explorer.png")
fig.add_layout_image(
    dict(
        source=pyLogo,
        xref="paper",
        yref="paper",
        x=0,
        y=1.35,
        sizex=0.2,
        sizey=0.2,
        xanchor="left",
        yanchor="top",
    )
)
fig.write_html(options["output"], include_plotlyjs="cdn", full_html=False)
