import os
import sys
import json
import shlex
import explorer
import subprocess
import pandas as pd
import plotly.express as px
import pyarrow.feather as feather
import plotly.graph_objects as go

from PIL import Image
from bs4 import BeautifulSoup
from explorer import insights
from optparse import OptionParser


def add_trace_to_graph(dataframe, color_scale=None, stragglers=False):
    if stragglers:
        custom_data = ["rank", "duration"]
    else:
        custom_data = ["rank", "duration", "size", "offset", "osts"]

    fig.add_traces(
        list(
            px.scatter(
                dataframe,
                x="start",
                y="rank",
                color="operation",
                range_x=(0 - (duration * 0.05), maximum_limit),
                range_y=(0 - rank_gap, maximum_rank + rank_gap),
                error_x="duration",
                render_mode="auto",
                facet_row=facet_row,
                color_discrete_sequence=color_scale,
                custom_data=custom_data,
                category_orders=category_orders,
            ).select_traces()
        )
    )


def determine_visiblity(fig, column):
    visible = [False] * len(fig.data)
    index = 0
    search = []
    if column == "Base":
        search = ["read", "write"]
    elif column == "Rank zero workload":
        search = [
            "read base",
            "write base",
            "rank 0 read - POSIX",
            "rank 0 write - POSIX",
            "rank 0 read - MPIIO",
            "rank 0 write - MPIIO",
        ]
    elif column == "Unbalanced ranks":
        search = [
            "read base",
            "write base",
            "read - POSIX",
            "write - POSIX",
            "read - MPIIO",
            "write - MPIIO",
        ]
    elif column == "Stragglers":
        search = ["fastest", "slowest"]

    for dat in fig.data:
        if dat.name in search:
            visible[index] = True
        index += 1

    return visible


def determine_legend(fig, column):
    legend = [False] * len(fig.data)
    index = 0
    search = []
    if column == "Base":
        search = ["read", "write"]
    elif column == "Rank zero workload":
        search = [
            "read base",
            "write base",
            "rank 0 read - POSIX",
            "rank 0 write - POSIX",
            "rank 0 read - MPIIO",
            "rank 0 write - MPIIO",
        ]
    elif column == "Unbalanced ranks":
        search = [
            "read base",
            "write base",
            "read - POSIX",
            "write - POSIX",
            "read - MPIIO",
            "write - MPIIO",
        ]
    elif column == "Stragglers":
        search = ["fastest", "slowest"]

    for dat in fig.data:
        if dat.name in search:
            legend[index] = True
            search.remove(dat.name)
        index += 1

    return legend


parser = OptionParser()
parser.add_option(
    "-f",
    "--file1",
    type="string",
    default=None,
    help="DXT CSV file name",
    metavar="FILE",
)
parser.add_option(
    "-i",
    "--file2",
    type="string",
    default=None,
    help="IO Phase file name",
    metavar="FILE",
)
parser.add_option(
    "-s",
    "--start",
    type="float",
    default=None,
    help="Mark trace start time",
    metavar="start",
)
parser.add_option(
    "-e", "--end", type="float", default=None, help="Mark trace end time", metavar="end"
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
    "-0",
    "--rank_zero_workload",
    type="string",
    default="False",
    help="Determine if rank 0 is doing more I/O than the rest of the workload",
    metavar="rank_zero_workload",
)
parser.add_option(
    "-1",
    "--unbalanced_workload",
    type="string",
    default="False",
    help="Determine which ranks have unbalanced workload",
    metavar="unbalanced_workload",
)
parser.add_option(
    "-2",
    "--stragglers",
    type="string",
    default="False",
    help="The 5 percent slowest operations in the time distribution",
    metavar="stragglers",
)
parser.add_option(
    "-3",
    "--collective_metadata",
    type="string",
    default="False",
    help="Determine if we have collective metadata operations",
    metavar="collective_metadata",
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
parser.add_option(
    "-t",
    "--graph_type",
    type="string",
    default=None,
    help="Type of graph",
    metavar="graph_type",
)
parser.add_option(
    "-r",
    "--runtime",
    type="string",
    default=None,
    help="Runtime of the graph",
    metavar="runtime",
)


(options, args) = parser.parse_args()
options = vars(options)

df = feather.read_feather(options["file1"])
if df.empty:
    quit()

df["osts"].fillna(value="-", inplace=True)
df.drop(df.tail(2).index, inplace=True)

if not options["graph_type"]:
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

df["duration"] = df["end"] - df["start"]
df["duration"] = df["duration"].round(4)

diagnosis = insights.insights(df.copy())

minimum = 0
maximum = max(df["end"])

duration = maximum - min(df["start"])

maximum_rank = max(df["rank"])
rank_gap = maximum_rank * 0.075

minimum_limit = -0.05
if not options["graph_type"]:
    maximum_limit = maximum + (duration * 0.05)
else:
    maximum_limit = options["runtime"]

if ("POSIX" in df["api"].unique()) & ("MPIIO" in df["api"].unique()):
    facet_row = "api"
    category_orders = {"api": ["MPIIO", "POSIX"]}
else:
    facet_row = None
    category_orders = None


dxt_issues = []

any_bottleneck = False
ranks_to_remove_from_base_posix = set()
ranks_to_remove_from_base_mpiio = set()

# Bottleneck 1
bottleneck1 = pd.DataFrame()
if options["rank_zero_workload"] == "True":
    any_bottleneck = True
    if options["from"] is not None and options["from"] > 0:
        options["rank_zero_workload"] = "False"
    else:
        messages = diagnosis.rank_zero_workload()
        isPOSIX_rank0 = False
        isMPIIO_rank0 = False
        for message in messages:
            if "True" in message:
                if "POSIX" in message:
                    isPOSIX_rank0 = True
                if "MPIIO" in message:
                    isMPIIO_rank0 = True

        df_zero_posix = pd.DataFrame()
        df_zero_mpiio = pd.DataFrame()
        if isPOSIX_rank0:
            ranks_to_remove_from_base_posix.add(0)
            df_zero_posix = df[(df["rank"] == 0) & (df["api"] == "POSIX")].copy()
            df_zero_posix.loc[
                (df_zero_posix["operation"] == "write"), ["operation"]
            ] = "rank 0 write - POSIX"
            df_zero_posix.loc[
                (df_zero_posix["operation"] == "read"), ["operation"]
            ] = "rank 0 read - POSIX"

        if isMPIIO_rank0:
            ranks_to_remove_from_base_mpiio.add(0)
            df_zero_mpiio = df[(df["rank"] == 0) & (df["api"] == "MPIIO")].copy()
            df_zero_mpiio.loc[
                (df_zero_mpiio["operation"] == "write"), ["operation"]
            ] = "rank 0 write - MPIIO"
            df_zero_mpiio.loc[
                (df_zero_mpiio["operation"] == "read"), ["operation"]
            ] = "rank 0 read - MPIIO"

        frames = [df_zero_posix, df_zero_mpiio]
        bottleneck1 = pd.concat(frames)

        if not bottleneck1.empty:
            msg = ""
            if isPOSIX_rank0:
                msg = msg + "POSIX"

            if isMPIIO_rank0:
                if msg == "":
                    msg = msg + "MPIIO"
                else:
                    msg = msg + " and MPIIO"

            messages = {
                "code": "D01",
                "level": 1,
                "issue": "Rank 0 is issuing a lot of I/O requests for " + msg,
                "recommendations": ["Consider using MPI-IO collective"],
            }

            dxt_issues.append(messages)

# Bottleneck 2
bottleneck2 = pd.DataFrame()
if options["unbalanced_workload"] == "True":
    any_bottleneck = True
    ranks = diagnosis.unbalanced_workloads()

    isPOSIX = False
    isMPIIO = False

    POSIX_ranks = []
    MPIIO_ranks = []
    for key, value in ranks.items():
        if "POSIX" in key:
            isPOSIX = True
            POSIX_ranks = value
        if "MPIIO" in key:
            isMPIIO = True
            MPIIO_ranks = value

    flag = False

    for rank in POSIX_ranks:
        if flag:
            break
        if options["from"] is not None:
            if rank < options["from"]:
                options["unbalanced_workload"] = "False"
                flag = True
        if options["to"] is not None:
            if rank > options["to"]:
                options["unbalanced_workload"] = "False"
                flag = True
        elif (options["from"] is None) & (options["to"] is None):
            break

    for rank in MPIIO_ranks:
        if flag:
            break
        if options["from"] is not None:
            if rank < options["from"]:
                options["unbalanced_workload"] = "False"
                flag = True
        if options["to"] is not None:
            if rank > options["to"]:
                options["unbalanced_workload"] = "False"
                flag = True
        elif (options["from"] is None) & (options["to"] is None):
            break

    if not flag:
        df_posix_ranks = pd.DataFrame()
        df_mpiio_ranks = pd.DataFrame()

        if isPOSIX:
            for rank in POSIX_ranks:
                ranks_to_remove_from_base_posix.add(rank)

            df_posix_ranks = df[df["api"] == "POSIX"].copy()
            df_posix_ranks = df_posix_ranks[df_posix_ranks["rank"].isin(POSIX_ranks)]

            df_posix_ranks.loc[
                (df_posix_ranks["operation"] == "write"), ["operation"]
            ] = "write - POSIX"
            df_posix_ranks.loc[
                (df_posix_ranks["operation"] == "read"), ["operation"]
            ] = "read - POSIX"
        if isMPIIO:
            for rank in MPIIO_ranks:
                ranks_to_remove_from_base_mpiio.add(rank)

            df_mpiio_ranks = df[df["api"] == "MPIIO"].copy()
            df_mpiio_ranks = df_mpiio_ranks[df_mpiio_ranks["rank"].isin(MPIIO_ranks)]
            df_mpiio_ranks.loc[
                (df_mpiio_ranks["operation"] == "write"), ["operation"]
            ] = "write - MPIIO"
            df_mpiio_ranks.loc[
                (df_mpiio_ranks["operation"] == "read"), ["operation"]
            ] = "read - MPIIO"

        frames = [df_posix_ranks, df_mpiio_ranks]
        bottleneck2 = pd.concat(frames)

        if not bottleneck2.empty:
            messages = {
                "code": "D02",
                "level": 1,
                "issue": "Detected unbalanced workload between the ranks",
                "recommendations": [
                    "Consider better balancing the data transfer between the application ranks",
                    "Consider tuning the stripe size and count to better distribute the data",
                    "If the application uses netCDF and HDF5, double check the need to set NO_FILL values",
                ],
            }

            dxt_issues.append(messages)

my_shapes = []
# Bottleneck 3
bottleneck3 = pd.DataFrame()
if options["stragglers"] == "True":
    any_bottleneck = True
    df_phases = feather.read_feather(options["file2"])
    io_phases_with_rank_posix, io_phases_with_rank_mpiio = diagnosis.stragglers(
        df_phases
    )

    if options["start"] is not None:
        io_phases_with_rank_posix = io_phases_with_rank_posix[
            io_phases_with_rank_posix["start"] >= options["start"]
        ]
        io_phases_with_rank_mpiio = io_phases_with_rank_mpiio[
            io_phases_with_rank_mpiio["start"] >= options["start"]
        ]

    if options["end"] is not None:
        io_phases_with_rank_posix = io_phases_with_rank_posix[
            io_phases_with_rank_posix["end"] <= options["end"]
        ]
        io_phases_with_rank_mpiio = io_phases_with_rank_mpiio[
            io_phases_with_rank_mpiio["end"] <= options["end"]
        ]

    if options["from"] is not None:
        io_phases_with_rank_posix = io_phases_with_rank_posix[
            io_phases_with_rank_posix["rank"] >= options["from"]
        ]
        io_phases_with_rank_mpiio = io_phases_with_rank_mpiio[
            io_phases_with_rank_mpiio["rank"] >= options["from"]
        ]

    if options["to"] is not None:
        io_phases_with_rank_posix = io_phases_with_rank_posix[
            io_phases_with_rank_posix["rank"] <= options["to"]
        ]
        io_phases_with_rank_mpiio = io_phases_with_rank_mpiio[
            io_phases_with_rank_mpiio["rank"] <= options["to"]
        ]

    frames = [io_phases_with_rank_posix, io_phases_with_rank_mpiio]
    bottleneck3 = pd.concat(frames)

    ind = 0
    my_shapes = []

    for index, row in io_phases_with_rank_posix.iterrows():
        if ind % 2 == 0:
            my_shapes.append(
                dict(
                    type="line",
                    x0=row["start"],
                    y0=0,
                    x1=row["start"],
                    y1=1024,
                    line=dict(color="Black", width=1, dash="dot"),
                    opacity=0.5,
                    xref="x",
                    yref="y",
                    visible=True,
                )
            )
        else:
            my_shapes.append(
                dict(
                    type="line",
                    x0=row["end"],
                    y0=0,
                    x1=row["end"],
                    y1=1024,
                    line=dict(color="Black", width=1, dash="dot"),
                    opacity=0.5,
                    xref="x",
                    yref="y",
                    visible=True,
                )
            )
        ind += 1

    ind = 0
    if not io_phases_with_rank_posix.empty:
        xref = "x2"
        yref = "y2"
    else:
        xref = "x"
        yref = "y"

    for index, row in io_phases_with_rank_mpiio.iterrows():
        if ind % 2 == 0:
            my_shapes.append(
                dict(
                    type="line",
                    x0=row["start"],
                    y0=0,
                    x1=row["start"],
                    y1=1024,
                    line=dict(color="Black", width=1, dash="dot"),
                    opacity=0.5,
                    xref=xref,
                    yref=yref,
                    visible=True,
                )
            )
        else:
            my_shapes.append(
                dict(
                    type="line",
                    x0=row["end"],
                    y0=0,
                    x1=row["end"],
                    y1=1024,
                    line=dict(color="Black", width=1, dash="dot"),
                    opacity=0.5,
                    xref=xref,
                    yref=yref,
                    visible=True,
                )
            )
        ind += 1

if any_bottleneck:
    temp_df = df.copy()

    temp_df_not_posix = temp_df[temp_df["api"] == "POSIX"]
    temp_df_not_posix = temp_df_not_posix[
        ~temp_df_not_posix["rank"].isin(ranks_to_remove_from_base_posix)
    ]

    temp_df_not_mpiio = temp_df[temp_df["api"] == "MPIIO"]
    temp_df_not_mpiio = temp_df_not_mpiio[
        ~temp_df_not_mpiio["rank"].isin(ranks_to_remove_from_base_mpiio)
    ]

    frames = [temp_df_not_posix, temp_df_not_mpiio]
    df_base = pd.concat(frames)

    df_base.loc[(df_base["operation"] == "write"), ["operation"]] = "write base"
    df_base.loc[(df_base["operation"] == "read"), ["operation"]] = "read base"

    fig = px.scatter(
        df_base,
        x="start",
        y="rank",
        color="operation",
        range_x=(0 - (duration * 0.05), maximum_limit),
        range_y=(0 - rank_gap, maximum_rank + rank_gap),
        error_x="duration",
        render_mode="auto",
        facet_row=facet_row,
        custom_data=["rank", "duration", "size", "offset", "osts"],
        color_discrete_sequence=["#d0e6f5", "#f7d8d5"],
        category_orders=category_orders,
    )

    if not bottleneck1.empty:
        add_trace_to_graph(bottleneck1, ["#3c93c2", "#f0746e"])
    if not bottleneck2.empty:
        add_trace_to_graph(bottleneck2, ["#3c93c2", "#f0746e"])
    if not bottleneck3.empty:
        add_trace_to_graph(bottleneck3, ["#3c93c2", "#f0746e"], True)

    fig.update_traces(visible=False, showlegend=False)

    add_trace_to_graph(df, ["#3c93c2", "#f0746e"])
else:
    fig = px.scatter(
        df,
        x="start",
        y="rank",
        color="operation",
        range_x=(0 - (duration * 0.05), maximum_limit),
        range_y=(0 - rank_gap, maximum_rank + rank_gap),
        error_x="duration",
        render_mode="auto",
        facet_row=facet_row,
        color_discrete_sequence=["#3c93c2", "#f0746e"],
        custom_data=["rank", "duration", "size", "offset", "osts"],
        category_orders=category_orders,
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
        annotation_textangle=90,
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
        annotation_textangle=90,
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
path = path.split('__init__.py')[0]
pyLogo = Image.open(path + "plots/dxt-explorer.png")
fig.add_layout_image(
    dict(
        source=pyLogo,
        xref="paper",
        yref="paper",
        x=0,
        y=1.14,
        sizex=0.2,
        sizey=0.2,
        xanchor="left",
        yanchor="top",
    )
)

fig.update_xaxes(showline=True, linewidth=1, linecolor="black", mirror=True)
fig.update_yaxes(showline=True, linewidth=1, linecolor="black", mirror=True)
fig.for_each_yaxis(lambda yaxis: yaxis.update(title="Rank"))

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
    autosize=True,
    height=1200,
    width=1800,
    margin=dict(r=20, l=20, b=100, t=125),
    title=("Explore <b>Operation</b> <br>" + options["identifier"]),
    title_x=0.5,
    title_y=0.97,
    font=dict(size=13, color="#000000"),
    xaxis_title="Runtime (Seconds)",
    xaxis=dict(
        rangeslider=dict(visible=True),
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

search = ["fastest", "slowest"]
fig.for_each_trace(
    lambda trace: trace.update(
        hovertemplate="<br>".join(
            [
                "Rank: %{customdata[0]}",
                "Duration: %{customdata[1]}",
                "Size: %{customdata[2]}",
                "Offset: %{customdata[3]}",
                "Osts: %{customdata[4]}",
            ]
        )
    )
    if trace.name not in search
    else (),
)

fig.for_each_trace(
    lambda trace: trace.update(
        hovertemplate="<br>".join(
            ["Rank: %{customdata[0]}", "Duration: %{customdata[1]}"]
        )
    )
    if trace.name in search
    else (),
)

for annotation in fig.layout.annotations:
    if "POSIX" in annotation.text:
        annotation.text = "POSIX"
    elif "MPIIO" in annotation.text:
        annotation.text = "MPIIO"

if any_bottleneck:
    fig_annotations = fig.layout.annotations
    fig_shapes = fig.layout.shapes
    my_shapes.append(fig.layout.shapes)

    button = []
    button.append(
        dict(
            label="Base Chart",
            method="update",
            args=[
                {
                    "visible": determine_visiblity(fig, "Base"),
                    "showlegend": determine_legend(fig, "Base"),
                },
                {"shapes": fig_shapes, "annotations": fig_annotations},
            ],
        )
    )
    if options["rank_zero_workload"] == "True":
        button.append(
            dict(
                label="Rank 0 Workload",
                method="update",
                args=[
                    {
                        "visible": determine_visiblity(fig, "Rank zero workload"),
                        "showlegend": determine_legend(fig, "Rank zero workload"),
                    },
                    {"shapes": fig_shapes, "annotations": fig_annotations},
                ],
            )
        )
    if options["unbalanced_workload"] == "True":
        button.append(
            dict(
                label="Unbalanced ranks",
                method="update",
                args=[
                    {
                        "visible": determine_visiblity(fig, "Unbalanced ranks"),
                        "showlegend": determine_legend(fig, "Unbalanced ranks"),
                    },
                    {"shapes": fig_shapes, "annotations": fig_annotations},
                ],
            )
        )
    if options["stragglers"] == "True":
        button.append(
            dict(
                label="Stragglers",
                method="update",
                args=[
                    {
                        "visible": determine_visiblity(fig, "Stragglers"),
                        "showlegend": determine_legend(fig, "Stragglers"),
                    },
                    {"shapes": my_shapes, "annotations": fig_annotations},
                ],
            )
        )

    fig.update_layout(
        updatemenus=[
            go.layout.Updatemenu(
                active=0, xanchor="left", x=1.02, showactive=True, buttons=button
            )
        ]
    )

fig.write_html(options["output"])

json_data = {}
json_data["dxt"] = dxt_issues
json_file_name = options["file1"].split(".dxt")[0] + ".json"
with open(json_file_name, "w") as outfile:
    json.dump(json_data, outfile)
json_file_path = os.path.abspath(json_file_name)

if any_bottleneck:
    size = 159
else:
    size = 176

file = options["file1"].split(".darshan")[0]
command = "drishti --html --light --size {} --json {} {}.darshan".format(
    size, json_file_path, file
)

args = shlex.split(command)
s = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
sOutput, sError = s.communicate()

if s.returncode == 0:
    drishti_output = open(file + ".drishti", "w")
    drishti_output.write(sOutput.decode())

    output_doc = BeautifulSoup()
    output_doc.append(output_doc.new_tag("body"))
    output_doc.append(output_doc.new_tag("head"))

    with open(options["output"], "r") as html_file:
        output_doc.body.extend(BeautifulSoup(html_file.read(), "html.parser").body)

    with open(file + ".darshan.html", "r") as html_file:
        output_doc.head.extend(BeautifulSoup(html_file.read(), "html.parser").head)

    with open(file + ".darshan.html", "r") as html_file:
        output_doc.body.extend(BeautifulSoup(html_file.read(), "html.parser").body)

    output_doc.style.append(BeautifulSoup("pre { padding-left: 60px;}", "html.parser"))

    with open(options["output"], "w") as output_file:
        output_file.write(str(output_doc))
else:
    sys.exit(os.EX_SOFTWARE)
