import os
import copy
import explorer
import pandas as pd
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
if df.empty or df["osts"].isnull().all():
    quit()

df["duration"] = df["end"] - df["start"]
df["duration"] = df["duration"].round(4)

if ("POSIX" in df["api"].unique()) & ("MPIIO" in df["api"].unique()):
    facet_row = "api"
    category_orders = {"api": ["MPIIO", "POSIX"]}
else:
    facet_row = None
    category_orders = None

df_dict = df.to_dict('records')
new_records = []
for row in (df_dict):
    osts = row["osts"].tolist()
    if len(osts) > 1:
        for ost in osts[1:]:
            new_row = copy.deepcopy(row)
            new_row['osts'] = ost
            new_records.append(new_row)
        
    row["osts"] = osts[0]

df_dict = df_dict + new_records
new_df = pd.DataFrame.from_dict(df_dict)
new_df['osts'] = new_df['osts'].astype('string')
new_df.sort_values(by='start', ascending=False)

count = new_df["osts"].nunique()

fig = px.scatter(
    new_df,
    x="start",
    y="osts",
    color="operation",
    range_y=(-2, count + 2),
    error_x="duration",
    render_mode="auto",
    facet_row=facet_row,
    color_discrete_sequence=["#3c93c2", "#f0746e"],
    category_orders=category_orders,
)

fig.update_xaxes(showline=True, linewidth=1, linecolor="black", mirror=True)
fig.update_yaxes(showline=True, linewidth=1, linecolor="black", mirror=True)
fig.for_each_yaxis(lambda yaxis: yaxis.update(title="OST#"))

fig.update_layout(
    legend=dict(
        itemsizing="constant",
        orientation="h",
        yanchor="bottom",
        y=1.008,
        xanchor="right",
        x=0.98,
    ),
    template="plotly_white",
    autosize=False,
    height=1200,
    width=1800,
    margin=dict(r=20, l=20, b=75, t=125),
    title=("Explore <b>OST usage operation </b> <br>" + options["identifier"]),
    title_x=0.5,
    title_y=0.98,
    font=dict(size=13, color="#000000"),
    xaxis_title="Runtime (Seconds)",
    xaxis=dict(
        rangeslider=dict(visible=False),
        type="-",
    ),
    xaxis_rangeslider_thickness=0.04,
)

fig.update_traces(
    error_x=dict(
        width=0,
        visible=True,
        symmetric=False,
    ),
    marker=dict(
        size=1,
    ),
)

for annotation in fig.layout.annotations:
    if "POSIX" in annotation.text:
        annotation.text = "POSIX"
    elif "MPIIO" in annotation.text:
        annotation.text = "MPIIO"

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

fig.write_html(options["output"], include_plotlyjs="cdn", full_html=False)
