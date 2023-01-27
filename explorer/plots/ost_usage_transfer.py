import pandas as pd
import plotly.express as px

from PIL import Image
from optparse import OptionParser
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

dict_request_sizes_mpiio_read = {}
dict_request_sizes_mpiio_write = {}

for i in range(len(df)):
    osts = df["osts"][i]
    osts = osts.tolist()
    flag = True

    for ost in osts:
        ost = str(ost)
        if flag:
            df.at[i, "osts"] = ost
            flag = False
        else:
            df.loc[len(df.index)] = df.iloc[i]
            df.at[len(df.index) - 1, "osts"] = ost

        if df["api"][i] == "POSIX":
            if df["operation"][i] == "write":
                if ost in dict_request_sizes_posix_write:
                    dict_request_sizes_posix_write[ost] += df.at[i, "size"]
                else:
                    dict_request_sizes_posix_write[ost] = df.at[i, "size"]
            elif df["operation"][i] == "read":
                if ost in dict_request_sizes_posix_read:
                    dict_request_sizes_posix_read[ost] += df.at[i, "size"]
                else:
                    dict_request_sizes_posix_read[ost] = df.at[i, "size"]
        elif df["api"][i] == "MPIIO":
            if df["operation"][i] == "write":
                if ost in dict_request_sizes_mpiio_write:
                    dict_request_sizes_mpiio_write[ost] += df.at[i, "size"]
                else:
                    dict_request_sizes_mpiio_write[ost] = df.at[i, "size"]
            elif df["operation"][i] == "read":
                if ost in dict_request_sizes_mpiio_read:
                    dict_request_sizes_mpiio_read[ost] += df.at[i, "size"]
                else:
                    dict_request_sizes_mpiio_read[ost] = df.at[i, "size"]

count = df["osts"].nunique()


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
    title_y=0.95,
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

pyLogo = Image.open("dxt-explorer.png")
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
