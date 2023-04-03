import os
import explorer
import numpy as np
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
    "-e", 
    "--end", 
    type="int", 
    default=None, 
    help="Mark trace end time", 
    metavar="end"
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

dict_request_sizes_posix_read = {}
dict_request_sizes_posix_write = {}

if ("POSIX" in df["api"].unique()):
    df_posix = df[df["api"]=="POSIX"]
    df_posix_size = df_posix["size"].tolist()
    df_posix_operation = df_posix["operation"].tolist()
    df_posix_osts = df_posix["osts"].tolist()
    df_posix_osts_unique = []

    for i in range(len(df_posix_osts)):
        df_posix_osts[i] = list(df_posix_osts[i])
        if df_posix_osts[i] not in df_posix_osts_unique:
            df_posix_osts_unique.append(df_posix_osts[i])

    for ost in df_posix_osts_unique:
        ost_index = [i for i in range(len(df_posix_osts)) if df_posix_osts[i] == ost]
        for index in ost_index:
            osts = df_posix_osts[index]
            for ost in osts:
                ost_operation = df_posix_operation[index]
                if ost_operation == "read":
                    ost_size = df_posix_size[index]
                    if ost not in dict_request_sizes_posix_read:
                        dict_request_sizes_posix_read[ost] = ost_size
                    else:
                        dict_request_sizes_posix_read[ost] += ost_size
                elif ost_operation == "write":
                    ost_size = df_posix_size[index]
                    if ost not in dict_request_sizes_posix_write:
                        dict_request_sizes_posix_write[ost] = ost_size
                    else:
                        dict_request_sizes_posix_write[ost] += ost_size

dict_request_sizes_mpiio_read = {}
dict_request_sizes_mpiio_write = {}

if ("MPIIO" in df["api"].unique()):
    df_mpiio = df[df["api"]=="MPIIO"]
    df_mpiio_size = df_mpiio["size"].tolist()
    df_mpiio_operation = df_mpiio["operation"].tolist()
    df_mpiio_osts = df_mpiio["osts"].tolist()
    df_mpiio_osts_unique = []

    for i in range(len(df_mpiio_osts)):
        df_mpiio_osts[i] = list(df_mpiio_osts[i])
        if df_mpiio_osts[i] not in df_mpiio_osts_unique:
            df_mpiio_osts_unique.append(df_mpiio_osts[i])

    for ost in df_mpiio_osts_unique:
        ost_index = [i for i in range(len(df_mpiio_osts)) if df_mpiio_osts[i] == ost]
        for index in ost_index:
            osts = df_mpiio_osts[index]
            for ost in osts:
                ost_operation = df_mpiio_operation[index]
                if ost_operation == "read":
                    ost_size = df_mpiio_size[index]
                    if ost not in dict_request_sizes_mpiio_read:
                        dict_request_sizes_mpiio_read[ost] = ost_size
                    else:
                        dict_request_sizes_mpiio_read[ost] += ost_size
                elif ost_operation == "write":
                    ost_size = df_mpiio_size[index]
                    if ost not in dict_request_sizes_mpiio_write:
                        dict_request_sizes_mpiio_write[ost] = ost_size
                    else:
                        dict_request_sizes_mpiio_write[ost] += ost_size
            
posix_read = pd.DataFrame(
    dict_request_sizes_posix_read.items(), columns=["OST", "size"]
)
posix_read["operation"] = "read"

posix_write = pd.DataFrame(
    dict_request_sizes_posix_write.items(), columns=["OST", "size"]
)
posix_write["operation"] = "write"

mpiio_read = pd.DataFrame(
    dict_request_sizes_mpiio_read.items(), columns=["OST", "size"]
)
mpiio_read["operation"] = "read"

mpiio_write = pd.DataFrame(
    dict_request_sizes_mpiio_write.items(), columns=["OST", "size"]
)
mpiio_write["operation"] = "write"

request_df_posix = pd.concat([posix_read, posix_write])
request_df_posix["api"] = "POSIX"

request_df_mpiio = pd.concat([mpiio_read, mpiio_write])
request_df_mpiio["api"] = "MPIIO"

request_df = pd.concat([request_df_posix, request_df_mpiio])
request_df['OST'] = request_df['OST'].astype('string')
fig = px.bar(
    request_df,
    x="OST",
    y="size",
    color="operation",
    facet_row=facet_row,
    color_discrete_sequence=["#f0746e", "#3c93c2"],
    category_orders=category_orders,
)

fig.update_xaxes(showline=True, linewidth=1, linecolor="black", mirror=True)
fig.update_yaxes(showline=True, linewidth=1, linecolor="black", mirror=True)
fig.for_each_yaxis(lambda yaxis: yaxis.update(title="Size (Bytes)"))

fig.update_layout(
    legend=dict(
        itemsizing="constant",
        orientation="h",
        yanchor="bottom",
        y=1.008,
        xanchor="right",
        traceorder="reversed",
        x=0.98,
    ),
    template="plotly_white",
    autosize=False,
    height=1200,
    width=1800,
    margin=dict(r=20, l=20, b=75, t=125),
    title=("Explore <b>OST usage transfer</b> <br>" + options["identifier"]),
    title_x=0.5,
    title_y=0.98,
    font=dict(size=13, color="#000000"),
    xaxis_title="OST #",
    xaxis=dict(
        rangeslider=dict(visible=False),
        type="-",
    ),
    xaxis_rangeslider_thickness=0.04,
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
