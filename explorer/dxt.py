"""
DXT Explorer.

DXT Explorer Copyright (c) 2021, The Regents of the University of
California, through Lawrence Berkeley National Laboratory (subject
to receipt of any required approvals from the U.S. Dept. of Energy).
All rights reserved.

If you have questions about your rights to use or distribute this software,
please contact Berkeley Lab's Intellectual Property Office at
IPO@lbl.gov.

NOTICE.  This Software was developed under funding from the U.S. Department
of Energy and the U.S. Government consequently retains certain rights.  As
such, the U.S. Government has been granted for itself and others acting on
its behalf a paid-up, nonexclusive, irrevocable, worldwide license in the
Software to reproduce, distribute copies to the public, prepare derivative
works, and perform publicly and display publicly, and to permit others to do
so.
"""

import os
import sys
import time
import shlex
import logging
import darshan
import argparse
import datetime
import subprocess
import webbrowser
import pandas as pd
import pkg_resources
import pyranges as pr
import logging.handlers
import pyarrow.feather as feather
# import darshan.backend.cffi_backend as darshanll

from recorder_utils import RecorderReader
from recorder_utils.build_offset_intervals import build_offset_intervals
from explorer import version as dxt_version

LOG_TYPE_DARSHAN = 0
LOG_TYPE_RECORDER = 1

class Explorer:
    def __init__(self, args):
        """Initialize the explorer."""
        self.args = args
        self.configure_log()

        self.generated_files = {}

        self.ROOT = os.path.abspath(os.path.dirname(__file__))

    def configure_log(self):
        """Configure the logging system."""
        self.logger = logging.getLogger("DXT Explorer")

        if self.args.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        # Defines the format of the logger
        formatter = logging.Formatter(
            "%(asctime)s %(module)s - %(levelname)s - %(message)s"
        )

        console = logging.StreamHandler()

        console.setFormatter(formatter)

        self.logger.addHandler(console)

    def run(self):
        self.explorer_start_time = time.time()

        log_type = self.check_log_type(self.args.log_path)

        if not self.args.prefix:
            self.prefix = os.getcwd()
        else:
            self.prefix = self.args.prefix

        report = None
        filename = self.args.log_path
        if log_type == LOG_TYPE_DARSHAN:
            # log = darshanll.log_open(self.args.log_path)
            # information = darshanll.log_get_job(log)
            # log_version = information["metadata"]["lib_ver"]
            # library_version = darshanll.darshan.backend.cffi_backend.get_lib_version()
            # filename = self.check_log_version(
            #     self.args.log_path, log_version, library_version
            # )
            report = darshan.DarshanReport(filename, read_all=True)
            if "DXT_POSIX" not in report.records and "DXT_MPIIO" not in report.records:
                self.logger.info("No DXT trace data found in file: {}".format(filename))
                exit()
        elif log_type == LOG_TYPE_RECORDER:
            report = RecorderReader(filename)

        if self.args.list_files:
            self.list_files(report, log_type)
            exit()

        self.generate_plot(filename, report, log_type)

        if self.args.transfer:
            self.generate_transfer_plot(filename, report, log_type)

        if self.args.spatiality:
            self.generate_spatiality_plot(filename, report, log_type)

        if self.args.io_phase:
            self.generate_phase_plot(filename, report, log_type)

        if self.args.ost_usage_operation:
            self.generate_ost_usage_operation_plot(filename, report, log_type)

        if self.args.ost_usage_transfer:
            self.generate_ost_usage_transfer_plot(filename, report, log_type)

        self.generate_index(filename, report, log_type)

    def check_log_type(self, path):
        if path.endswith(".darshan"):
            if not os.path.isfile(path):
                self.logger.error('Unable to open .darshan file.')
                sys.exit(os.EX_NOINPUT)
            else: return LOG_TYPE_DARSHAN
        else: # check whether is a valid recorder log
            if not os.path.isdir(path):
                self.logger.error('Unable to open recorder folder.')
                sys.exit(os.EX_NOINPUT)
            else: return LOG_TYPE_RECORDER

    def list_files(self, report, log_type, display=True):
        total = 0
        file_ids = {}
        if log_type == LOG_TYPE_DARSHAN:
            """Create a dictionary of file id as key and file name as value."""
            file_ids = report.log["name_records"]
            for key, value in dict(file_ids).items():
                if value == "<STDOUT>":
                    del file_ids[key]
                if value == "<STDERR>":
                    del file_ids[key]

        elif log_type == LOG_TYPE_RECORDER:
            ranks = report.GM.total_ranks
            for rank in range(ranks):
                file_ids.update(report.LMs[rank].filemap)

        for file_id, file_name in file_ids.items():
            total += 1
            if display:
                self.logger.info("FILE: {} (ID {})".format(file_name, file_id))

        if total == 0:
            self.logger.critical("No DXT records found in {}".format(self.args.log_path))

            if log_type == LOG_TYPE_DARSHAN:
                self.logger.critical(
                    "To enable Darshan DXT, set this before your application runs:"
                )
                self.logger.critical("$ export DXT_ENABLE_IO_TRACE=1")

            exit()

        return file_ids

    def get_id_to_record_mapping(self, report, mod):
        """
        Get mapping of id to records for a given module.

        Arguments:
            report (DarshanReport): the the record belongs to
            mod (String): name of module

        Returns:
            Dictionary with lists of records by their id
        """

        if mod not in report.records:
            return []

        recs_by_id = {}
        for i, rec in enumerate(report.records[mod]):
            if rec["id"] not in recs_by_id:
                recs_by_id[rec["id"]] = []

            if mod in ["LUSTRE"]:
                recs_by_id[rec["id"]] = [rec]
            else:
                recs_by_id[rec["id"]].append(rec)

        return recs_by_id

    def dxt_record_attach_osts_inplace(self, report, record, lustre_records_by_id):
        """
        For a given DXT record, attach targeted Lustre OSTs.

        Arguments:
            report: DarshanReport the the record belongs to
            record: DarshanRecord to update
            lustre_records_by_id: mapping to use (recreating the mapping is potentially expensive for larger logs)

        Returns:
            reference to updated record
        """

        rec = record

        if rec["id"] not in lustre_records_by_id:
            raise Exception(
                self.logger.info(
                    "No matching lustre records found. (This is not necessarily an error, just that the file may not reside on a Lustre system.)"
                )
            )

        lrec = lustre_records_by_id[rec["id"]][0]
        lcounters = dict(zip(report.counters["LUSTRE"]["counters"], lrec["counters"]))

        osts = list(lrec["ost_ids"])

        stripe_size = lcounters["LUSTRE_STRIPE_SIZE"]
        stripe_count = lcounters["LUSTRE_STRIPE_WIDTH"]

        for op in ["read_segments", "write_segments"]:
            segs = rec[op]

            for access in segs:
                access["osts"] = []

                offset = access["offset"]
                length = access["length"]

                cur_offset = offset
                ost_idx = int(offset / stripe_size) % stripe_count

                add_count = 0
                while cur_offset <= (offset + length):
                    ost_id = osts[ost_idx]
                    access["osts"].append(ost_id)

                    cur_offset = (int(cur_offset / stripe_size) + 1) * stripe_size

                    if ost_idx == (stripe_count - 1):
                        ost_idx = 0
                    else:
                        ost_idx += 1

                    add_count += 1
                    if add_count >= stripe_count:
                        break
        return rec

    def create_dataframe(
        self, file_id, subset_dataset_file, log_type, df_posix=None, df_mpiio=None
    ):
        """Create a dataframe from parsed records."""

        column_names = [
            "file_id",
            "api",
            "rank",
            "operation",
            "segment",
            "offset",
            "size",
            "start",
            "end",
            "osts",
        ]
        total_logs = 0
        runtime = 0

        df = []
        result = pd.DataFrame()

        if log_type == LOG_TYPE_DARSHAN:
            if not df_posix.empty:
                df_posix_temp = df_posix.loc[df_posix["id"] == file_id]
                for index, row in df_posix_temp.iterrows():
                    write_segments = row["write_segments"]
                    write_segments["operation"] = "write"
                    read_segments = row["read_segments"]
                    read_segments["operation"] = "read"

                    temp_result = pd.concat([write_segments, read_segments])
                    temp_result["file_id"] = file_id
                    temp_result["rank"] = row["rank"]
                    temp_result["api"] = "POSIX"

                    temp_result = temp_result.rename(
                        columns={"length": "size", "start_time": "start", "end_time": "end"}
                    )

                    total_logs = total_logs + len(temp_result)
                    runtime = max(runtime, temp_result["end"].max())

                    temp_result["start"] = temp_result["start"].round(decimals=4)
                    temp_result["end"] = temp_result["end"].round(decimals=4)

                    temp_result.index.name = "segment"
                    temp_result.reset_index(inplace=True)
                    temp_result = temp_result.reindex(columns=column_names)

                    df.append(temp_result)

            if not df_mpiio.empty:
                df_mpiio_temp = df_mpiio.loc[df_mpiio["id"] == file_id]
                for index, row in df_mpiio_temp.iterrows():
                    write_segments = row["write_segments"]
                    write_segments["operation"] = "write"
                    read_segments = row["read_segments"]
                    read_segments["operation"] = "read"

                    temp_result = pd.concat([write_segments, read_segments])
                    temp_result["file_id"] = file_id
                    temp_result["rank"] = row["rank"]
                    temp_result["api"] = "MPIIO"

                    temp_result = temp_result.rename(
                        columns={"length": "size", "start_time": "start", "end_time": "end"}
                    )

                    total_logs = total_logs + len(temp_result)
                    runtime = max(runtime, temp_result["end"].max())

                    temp_result["start"] = temp_result["start"].round(decimals=4)
                    temp_result["end"] = temp_result["end"].round(decimals=4)

                    temp_result.index.name = "segment"
                    temp_result.reset_index(inplace=True)
                    temp_result = temp_result.reindex(columns=column_names)

                    df.append(temp_result)

            if df:
                result = pd.concat(df, axis=0, ignore_index=True)

        elif log_type == LOG_TYPE_RECORDER:
            if not df_posix.empty:
                df_posix_temp = df_posix.loc[df_posix["file_id"] == file_id]
            if not df_mpiio.empty:
                df_mpiio_temp = df_mpiio.loc[df_mpiio["file_id"] == file_id]

            if not df_posix_temp.empty or not df_mpiio_temp.empty:
                result = pd.concat([df_posix_temp, df_mpiio_temp], ignore_index=True)
                result = result.reindex(columns=column_names)
                total_logs = len(result)
                runtime = result['end'].max()

        feather.write_feather(
            result, subset_dataset_file + ".dxt", compression="uncompressed"
        )

        if self.args.csv:
            result.to_csv(
                subset_dataset_file + ".dxt.csv", mode="w", index=False, header=True 
            )

        column_names = ["total_logs", "runtime"]
        result = pd.DataFrame(columns=column_names)

        row = [total_logs, runtime]
        result.loc[len(result.index)] = row
        result.to_csv(
            subset_dataset_file + ".summary.dxt.csv", mode="w", index=False, header=True
        )

    def subset_dataset(self, file, file_ids, report, log_type):
        """Subset the dataset based on file id and save to a csv file."""
        self.logger.info("generating dataframes")
        df_posix, df_mpiio = [], []
        if log_type == LOG_TYPE_DARSHAN:
            lustre_records_by_id = self.get_id_to_record_mapping(report, "LUSTRE")

            if lustre_records_by_id:

                def graceful_wrapper(r, rec, lustre_records_by_id):
                    try:
                        self.dxt_record_attach_osts_inplace(
                            report, rec, lustre_records_by_id
                        )
                    except Exception:
                        pass

                list(
                    map(
                        lambda rec: graceful_wrapper(report, rec, lustre_records_by_id),
                        report.records["DXT_POSIX"],
                    )
                )
                list(
                    map(
                        lambda rec: graceful_wrapper(report, rec, lustre_records_by_id),
                        report.records["DXT_MPIIO"],
                    )
                )

            if "DXT_POSIX" in report.records:
                df_posix = report.records["DXT_POSIX"].to_df()

            if "DXT_MPIIO" in report.records:
                df_mpiio = report.records["DXT_MPIIO"].to_df()

            df_posix = pd.DataFrame(df_posix)
            df_mpiio = pd.DataFrame(df_mpiio)

        elif log_type == LOG_TYPE_RECORDER:
            def add_api(row):
                if 'MPI' in row['function']:
                    return 'MPIIO'
                elif 'H5' in row['function']:
                    return 'H5F'
                else:
                    return 'POSIX'
                
            def add_operation(row):
                if 'read' in row['function']:
                    return 'read'
                else: return 'write'
            
            df_intervals = build_offset_intervals(report)
            df_intervals['api'] = df_intervals.apply(add_api, axis=1)
            df_intervals['operation'] = df_intervals.apply(add_operation, axis=1)
            df_posix = df_intervals[(df_intervals['api'] == 'POSIX')]
            df_mpiio = df_intervals[(df_intervals['api'] == 'MPIIO')]

        for file_id in file_ids:
            subset_dataset_file = "{}.{}".format(file, file_id)

            if os.path.exists(subset_dataset_file + ".dxt"):
                self.logger.debug("using existing parsed log file")
                continue

            self.create_dataframe(file_id, subset_dataset_file, log_type, df_posix, df_mpiio)

    def merge_overlapping_io_phases(self, overlapping_df, df, module):
        io_phases_df = pd.DataFrame(
            columns=[
                "index",
                "api",
                "operation",
                "start",
                "end",
                "duration",
                "fastest_rank",
                "fastest_rank_start",
                "fastest_rank_end",
                "fastest_rank_duration",
                "slowest_rank",
                "slowest_rank_start",
                "slowest_rank_end",
                "slowest_rank_duration",
                "threshold",
            ]
        )

        overlapping_df_end = overlapping_df[["End"]].to_numpy()
        overlapping_df_start = overlapping_df[["Start"]].to_numpy()
        interval_duration = 0

        for i in range(len(overlapping_df_end) - 1):
            interval_start = overlapping_df_end[i]
            interval_end = overlapping_df_start[i + 1]
            interval_duration = interval_duration + (interval_end - interval_start)

        threshold = float(interval_duration / (len(overlapping_df_end) - 1))
        merged_df = pd.DataFrame(columns=["Start", "End"])

        if len(overlapping_df_end) != 0:
            prev_value = overlapping_df_end[0]
            prev_index = 0

            for i in range(1, len(overlapping_df_end)):
                if overlapping_df_start[i] - prev_value <= threshold:
                    prev_value = overlapping_df_end[i]
                if (
                    overlapping_df_start[i] - prev_value > threshold
                    or i == len(overlapping_df_end) - 1
                ):
                    merged_df.loc[len(merged_df.index)] = [
                        float(overlapping_df_start[prev_index]),
                        float(prev_value),
                    ]
                    prev_index = i
                    prev_value = overlapping_df_end[i]

        if not merged_df.empty:
            for i in range(len(merged_df)):
                start = merged_df["Start"].iat[i]
                end = merged_df["End"].iat[i]

                df_temp = df[df["start"] >= start]
                df_temp = df_temp[df_temp["end"] <= end]
                df_temp["duration"] = df_temp["end"] - df_temp["start"]

                min = df_temp.loc[df_temp["end"] == df_temp["end"].min()]
                fastest_rank = min["rank"].tolist()
                fastest_rank_start = min["start"].tolist()
                fastest_rank_end = min["end"].tolist()
                fastest_rank_duration = min["duration"].tolist()
                if fastest_rank:
                    fastest_rank = fastest_rank[0]
                    fastest_rank_duration = fastest_rank_duration[0]
                    fastest_rank_start = fastest_rank_start[0]
                    fastest_rank_end = fastest_rank_end[0]

                max = df_temp.loc[df_temp["end"] == df_temp["end"].max()]
                slowest_rank = max["rank"].tolist()
                slowest_rank_start = max["start"].tolist()
                slowest_rank_end = max["end"].tolist()
                slowest_rank_duration = max["duration"].tolist()
                if slowest_rank:
                    slowest_rank = slowest_rank[0]
                    slowest_rank_duration = slowest_rank_duration[0]
                    slowest_rank_start = slowest_rank_start[0]
                    slowest_rank_end = slowest_rank_end[0]

                operation = ""
                if df_temp["operation"].eq("read").any():
                    if df_temp["operation"].eq("write").any():
                        operation = "read&write"
                    else:
                        operation = "read"
                elif df_temp["operation"].eq("write").any():
                    operation = "write"

                start = df_temp["start"].min()
                end = df_temp["end"].max()
                duration = end - start
                io_phases_df.loc[len(io_phases_df.index)] = [
                    0,
                    module,
                    operation,
                    start,
                    end,
                    duration,
                    fastest_rank,
                    fastest_rank_start,
                    fastest_rank_end,
                    fastest_rank_duration,
                    slowest_rank,
                    slowest_rank_start,
                    slowest_rank_end,
                    slowest_rank_duration,
                    threshold,
                ]

        io_phases_df.dropna(inplace=True)
        return io_phases_df

    def calculate_io_phases(
        self, file, file_ids, file_id=None, snapshot=None, snapshot_flag=False
    ):
        if snapshot_flag:
            subset_dataset_file = "{}.{}.{}-{}.{}".format(
                file, file_id, "snapshot", snapshot, "dxt"
            )
            file_name = subset_dataset_file.split(".dxt")[0]
            phases_file = "{}.{}".format(file_name, "io_phases")

            if not os.path.exists(phases_file):
                self.logger.info("generating I/O phases dataframe")
                df = feather.read_feather(subset_dataset_file)
                if not df.empty:
                    df_selected = df[["api", "start", "end"]].copy()
                    df_selected["start"] = df_selected["start"] * 10000
                    df_selected["end"] = df_selected["end"] * 10000
                    df_selected.columns = ["Chromosome", "Start", "End"]

                    gr = pr.PyRanges(df_selected)
                    overlapping = gr.merge()
                    overlapping = overlapping.as_df()

                    overlapping["Start"] = overlapping["Start"] / 10000
                    overlapping["End"] = overlapping["End"] / 10000

                    df_posix = df[df["api"] == "POSIX"]
                    df_posix = df_posix.sort_values("start")

                    overlapping_POSIX = overlapping[
                        overlapping["Chromosome"] == "POSIX"
                    ]

                    io_phases_df_posix = self.merge_overlapping_io_phases(
                        overlapping_POSIX, df_posix, "POSIX"
                    )

                    df_mpiio = df[df["api"] == "MPIIO"]
                    df_mpiio = df_mpiio.sort_values("start")

                    overlapping_MPIIO = overlapping[
                        overlapping["Chromosome"] == "MPIIO"
                    ]

                    io_phases_df_mpiio = self.merge_overlapping_io_phases(
                        overlapping_MPIIO, df_mpiio, "MPIIO"
                    )

                    frames = [io_phases_df_posix, io_phases_df_mpiio]
                    result = pd.concat(frames)
                    feather.write_feather(result, phases_file)
                else:
                    result = pd.DataFrame()
                    feather.write_feather(result, phases_file)
        else:
            for file_id in file_ids:
                if snapshot_flag:
                    subset_dataset_file = "{}.{}.{}-{}.{}".format(
                        file, file_id, "snapshot", snapshot, "dxt"
                    )
                else:
                    subset_dataset_file = "{}.{}.{}".format(file, file_id, "dxt")

                file_name = subset_dataset_file.split(".dxt")[0]
                phases_file = "{}.{}".format(file_name, "io_phases")
                if not os.path.exists(phases_file):
                    self.logger.info("generating I/O phases dataframe")
                    df = feather.read_feather(subset_dataset_file)
                    if not df.empty:
                        df_selected = df[["api", "start", "end"]].copy()
                        df_selected["start"] = df_selected["start"] * 10000
                        df_selected["end"] = df_selected["end"] * 10000
                        df_selected.columns = ["Chromosome", "Start", "End"]

                        gr = pr.PyRanges(df_selected)
                        overlapping = gr.merge()
                        overlapping = overlapping.as_df()

                        overlapping["Start"] = overlapping["Start"] / 10000
                        overlapping["End"] = overlapping["End"] / 10000

                        df_posix = df[df["api"] == "POSIX"]
                        df_posix = df_posix.sort_values("start")

                        overlapping_POSIX = overlapping[
                            overlapping["Chromosome"] == "POSIX"
                        ]

                        io_phases_df_posix = self.merge_overlapping_io_phases(
                            overlapping_POSIX, df_posix, "POSIX"
                        )

                        df_mpiio = df[df["api"] == "MPIIO"]
                        df_mpiio = df_mpiio.sort_values("start")

                        overlapping_MPIIO = overlapping[
                            overlapping["Chromosome"] == "MPIIO"
                        ]

                        io_phases_df_mpiio = self.merge_overlapping_io_phases(
                            overlapping_MPIIO, df_mpiio, "MPIIO"
                        )

                        frames = [io_phases_df_posix, io_phases_df_mpiio]
                        result = pd.concat(frames)
                        feather.write_feather(result, phases_file)
                    else:
                        result = pd.DataFrame()
                        feather.write_feather(result, phases_file)

    def generate_plot(self, file, report, log_type):
        """Generate an interactive operation plot."""
        limits = ""
        insights = ""

        if self.args.start:
            limits += " -s {} ".format(self.args.start)

        if self.args.end:
            limits += " -e {} ".format(self.args.end)

        if self.args.start_rank:
            limits += " -n {} ".format(self.args.start_rank)

        if self.args.end_rank:
            limits += " -m {} ".format(self.args.end_rank)

        if self.args.rank_zero_workload:
            insights += " -0 {} ".format(self.args.rank_zero_workload)

        if self.args.unbalanced_workload:
            insights += " -1 {} ".format(self.args.unbalanced_workload)

        file_ids = self.list_files(report, log_type)

        if len(file_ids) == 0:
            self.logger.info("No data to generate plots")
        else:
            self.subset_dataset(file, file_ids, report, log_type)

            if self.args.stragglers:
                insights += " -2 {} ".format(self.args.stragglers)
                self.calculate_io_phases(file, file_ids)

            for file_id, file_name in file_ids.items():
                csv_file = "{}.{}.summary.dxt.csv".format(file, file_id)
                df = pd.read_csv(csv_file, sep=",")

                total_logs = df["total_logs"].iloc[0]
                runtime = df["runtime"].iloc[0]

                threshold = 20000000

                if total_logs > threshold:
                    self.logger.info(
                        "The total duration of the log is {}s. The plots will be split into small intervals.".format(
                            str(runtime)
                        )
                    )

                    csv_file = "{}.{}.dxt".format(file, file_id)
                    df = pd.read_csv(csv_file, sep=",")

                    start = 0
                    increment_amount = total_logs / threshold
                    increment_amount = runtime / increment_amount
                    end = increment_amount
                    snapshot = 1

                    while end < runtime:
                        val = input(
                            "Do you want to generate plots for the next interval? Enter Y to continue, N to quit.\n"
                        )

                        if val == "Y" or val == "y":
                            self.logger.info(
                                "Generating plots for the interval {}s - {}s".format(
                                    round(start, 4), round(end, 4)
                                )
                            )
                            snapshot_file = "{}.{}.{}-{}.{}".format(
                                file, file_id, "snapshot", snapshot, "dxt"
                            )

                            if not os.path.exists(snapshot_file):
                                rows_before_start = df[
                                    (df["start"] < start) & (df["end"] > start)
                                ].copy()
                                if not rows_before_start.empty:
                                    rows_before_start.loc[:, "start"] = round(start, 4)

                                rows_after_end = df[
                                    (df["start"] < end) & (df["end"] > end)
                                ].copy()

                                if not rows_after_end.empty:
                                    rows_after_end.loc[:, "end"] = round(end, 4)

                                rows = df[df["start"] >= start]
                                rows = rows[rows["end"] <= end]
                                frames = [rows_before_start, rows_after_end, rows]

                                df_snap = pd.concat(frames)
                                df_snap.to_csv(snapshot_file)

                            if self.args.stragglers:
                                self.calculate_io_phases(
                                    file, file_ids, file_id, snapshot, True
                                )

                            output_file = "{}/{}-{}-{}-{}.html".format(
                                self.prefix, file_id, "snapshot", snapshot, "operation"
                            )
                            path = "plots/operation.py"
                            script = pkg_resources.resource_filename(__name__, path)

                            command = "python3 {} -p {} -f {}.{}.{}-{}.dxt -i {}.{}.{}-{}.io_phases {} {} -o {} -x {} -t {} -r {}".format(
                                script,
                                file,
                                file,
                                file_id,
                                "snapshot",
                                snapshot,
                                file,
                                file_id,
                                "snapshot",
                                snapshot,
                                limits,
                                insights,
                                output_file,
                                file_name,
                                "large",
                                runtime,
                            )

                            args = shlex.split(command)
                            self.logger.info(
                                "generating interactive operation for: {}".format(
                                    file_name
                                )
                            )
                            self.logger.debug(command)
                            s = subprocess.run(args)

                            if s.returncode == 0:
                                if file_id not in self.generated_files:
                                    self.generated_files[file_id] = []

                                if os.path.exists(output_file):
                                    self.logger.info("SUCCESS: {}".format(output_file))

                                    if self.args.browser:
                                        webbrowser.open("file://{}".format(output_file), new=2)

                                    self.generated_files[file_id].append(output_file)

                                else:
                                    self.logger.warning("no data to generate interactive plots")

                            else:
                                self.logger.error(
                                    "failed to generate the interactive plots (error %s)",
                                    s.returncode,
                                )

                                sys.exit(os.EX_SOFTWARE)

                            start = end
                            end = end + increment_amount
                            snapshot += 1
                        elif val == "N" or val == "n":
                            self.logger.info("Quitting the application!")
                            break
                        else:
                            self.logger.info("Incorrect input. Please try again.")
                else:
                    output_file = "{}/{}-{}.html".format(
                        self.prefix, file_id, "operation"
                    )
                    path = "plots/operation.py"
                    script = pkg_resources.resource_filename(__name__, path)

                    command = "python3 {} -p {} -f {}.{}.dxt -i {}.{}.io_phases{} {} -o {} -x {}".format(
                        script,
                        file,
                        file,
                        file_id,
                        file,
                        file_id,
                        limits,
                        insights,
                        output_file,
                        file_name,
                    )

                    args = shlex.split(command)
                    self.logger.info(
                        "generating interactive operation for: {}".format(file_name)
                    )
                    self.logger.debug(command)

                    s = subprocess.run(args)

                    if s.returncode == 0:
                        if file_id not in self.generated_files:
                            self.generated_files[file_id] = []

                        if os.path.exists(output_file):
                            self.logger.info("SUCCESS: {}".format(output_file))

                            if self.args.browser:
                                webbrowser.open("file://{}".format(output_file), new=2)

                            self.generated_files[file_id].append(output_file)

                        else:
                            self.logger.warning("no data to generate interactive plots")

                    else:
                        self.logger.error(
                            "failed to generate the interactive plots (error %s)",
                            s.returncode,
                        )

                        sys.exit(os.EX_SOFTWARE)

    def generate_transfer_plot(self, file, report, log_type):
        """Generate an interactive transfer plot."""
        limits = ""

        if self.args.start:
            limits += " -s {} ".format(self.args.start)

        if self.args.end:
            limits += " -e {} ".format(self.args.end)

        if self.args.start_rank:
            limits += " -n {} ".format(self.args.start_rank)

        if self.args.end_rank:
            limits += " -m {} ".format(self.args.end_rank)

        file_ids = self.list_files(report, log_type)

        if len(file_ids) == 0:
            self.logger.info("No data to generate plots")
        else:
            # Generated the CSV files for each plot

            self.subset_dataset(file, file_ids, report, log_type)

            for file_id, file_name in file_ids.items():
                output_file = "{}/{}-{}.html".format(self.prefix, file_id, "transfer")

                path = "plots/transfer.py"
                script = pkg_resources.resource_filename(__name__, path)

                command = "python3 {} -f {}.{}.dxt {} -o {} -x {}".format(
                    script, file, file_id, limits, output_file, file_name
                )

                args = shlex.split(command)

                self.logger.info(
                    "generating interactive transfer for: {}".format(file_name)
                )
                self.logger.debug(command)

                s = subprocess.run(args)

                if s.returncode == 0:
                    if file_id not in self.generated_files:
                        self.generated_files[file_id] = []

                    if os.path.exists(output_file):
                        self.logger.info("SUCCESS: {}".format(output_file))

                        if self.args.browser:
                            webbrowser.open("file://{}".format(output_file), new=2)

                        self.generated_files[file_id].append(output_file)

                    else:
                        self.logger.warning("no data to generate transfer plots")

                else:
                    self.logger.error(
                        "failed to generate the transfer plots (error %s)",
                        s.returncode,
                    )

                    sys.exit(os.EX_SOFTWARE)

    def generate_spatiality_plot(self, file, report, log_type):
        """Generate an interactive spatiality plot."""
        file_ids = self.list_files(report, log_type)
        if len(file_ids) == 0:
            self.logger.info("No data to generate plots")
        else:
            # Generated the CSV files for each plot
            self.subset_dataset(file, file_ids, report, log_type)

            for file_id, file_name in file_ids.items():
                output_file = "{}/{}-{}.html".format(self.prefix, file_id, "spatiality")

                path = "plots/spatiality.py"
                script = pkg_resources.resource_filename(__name__, path)

                command = "python3 {} -f {}.{}.dxt -o {} -x {}".format(
                    script, file, file_id, output_file, file_name
                )

                args = shlex.split(command)
                self.logger.info(
                    "generating interactive spatiality for: {}".format(file_name)
                )

                s = subprocess.run(args)

                if s.returncode == 0:
                    if file_id not in self.generated_files:
                        self.generated_files[file_id] = []

                    if os.path.exists(output_file):
                        self.logger.info("SUCCESS: {}".format(output_file))

                        if self.args.browser:
                            webbrowser.open("file://{}".format(output_file), new=2)

                        self.generated_files[file_id].append(output_file)

                    else:
                        self.logger.warning("no data to generate spatiality plots")

                else:
                    self.logger.error(
                        "failed to generate the spatiality plots (error %s)",
                        s.returncode,
                    )

                    sys.exit(os.EX_SOFTWARE)

    def generate_phase_plot(self, file, report, log_type):
        """Generate an interactive I/O phase plot."""
        file_ids = self.list_files(report, log_type)

        if len(file_ids) == 0:
            self.logger.info("No data to generate plots")
        else:
            self.subset_dataset(file, file_ids, report, log_type)
            self.calculate_io_phases(file, file_ids)

            for file_id, file_name in file_ids.items():
                output_file = "{}/{}-{}.html".format(self.prefix, file_id, "io_phase")
                path = "plots/io_phase.py"
                script = pkg_resources.resource_filename(__name__, path)

                command = "python3 {} -f {}.{}.io_phases -o {} -x {}".format(
                    script, file, file_id, output_file, file_name
                )

                args = shlex.split(command)
                self.logger.info(
                    "generating interactive I/O phase plot for: {}".format(file_name)
                )

                s = subprocess.run(args)

                if s.returncode == 0:
                    if file_id not in self.generated_files:
                        self.generated_files[file_id] = []

                    if os.path.exists(output_file):
                        self.logger.info("SUCCESS: {}".format(output_file))

                        if self.args.browser:
                            webbrowser.open("file://{}".format(output_file), new=2)

                        self.generated_files[file_id].append(output_file)

                    else:
                        self.logger.warning("no data to generate I/O phase plots")
                    
                else:
                    self.logger.error(
                        "failed to generate I/O phase plots (error %s)",
                        s.returncode,
                    )

                    sys.exit(os.EX_SOFTWARE)

    def generate_ost_usage_operation_plot(self, file, report, log_type):
        """Generate an interactive OST usage operation plot."""
        file_ids = self.list_files(report, log_type)

        if len(file_ids) == 0:
            self.logger.info("No data to generate plots")
        else:
            self.subset_dataset(file, file_ids, report, log_type)

            for file_id, file_name in file_ids.items():
                output_file = "{}/{}-{}.html".format(
                    self.prefix, file_id, "ost_usage_operation"
                )
                path = "plots/ost_usage_operation.py"
                script = pkg_resources.resource_filename(__name__, path)

                command = "python3 {} -f {}.{}.dxt -o {} -x {}".format(
                    script, file, file_id, output_file, file_name
                )

                args = shlex.split(command)
                self.logger.info(
                    "generating interactive OST usage operation plot for: {}".format(
                        file_name
                    )
                )

                s = subprocess.run(args)

                if s.returncode == 0:
                    if file_id not in self.generated_files:
                        self.generated_files[file_id] = []

                    if os.path.exists(output_file):
                        self.logger.info("SUCCESS: {}".format(output_file))

                        if self.args.browser:
                            webbrowser.open("file://{}".format(output_file), new=2)

                        self.generated_files[file_id].append(output_file)

                    else:
                        self.logger.warning("no data to generate interactive OST usage operation plots")

                else:
                    self.logger.error(
                        "failed to generate interactive OST usage operation plots (error %s)",
                        s.returncode,
                    )

                    sys.exit(os.EX_SOFTWARE)

    def generate_ost_usage_transfer_plot(self, file, report, log_type):
        """Generate an interactive OST usage data transfer plot."""
        file_ids = self.list_files(report, log_type)

        if len(file_ids) == 0:
            self.logger.info("No data to generate plots")
        else:
            self.subset_dataset(file, file_ids, report, log_type)

            for file_id, file_name in file_ids.items():
                output_file = "{}/{}-{}.html".format(
                    self.prefix, file_id, "ost_usage_transfer"
                )
                path = "plots/ost_usage_transfer.py"
                script = pkg_resources.resource_filename(__name__, path)

                command = "python3 {} -f {}.{}.dxt -o {} -x {}".format(
                    script, file, file_id, output_file, file_name
                )

                args = shlex.split(command)
                self.logger.info(
                    "generating interactive OST usage transfer plot for: {}".format(
                        file_name
                    )
                )

                s = subprocess.run(args)

                if s.returncode == 0:
                    if file_id not in self.generated_files:
                        self.generated_files[file_id] = []

                    if os.path.exists(output_file):
                        self.logger.info("SUCCESS: {}".format(output_file))

                        if self.args.browser:
                            webbrowser.open("file://{}".format(output_file), new=2)

                        self.generated_files[file_id].append(output_file)

                    else:
                        self.logger.warning("no data to generate interactive OST usage transfer plots")
                    
                else:
                    self.logger.error(
                        "failed to generate interactive OST usage transfer plots (error %s)",
                        s.returncode,
                    )

                    sys.exit(os.EX_SOFTWARE)

    def generate_index(self, file, report, log_type):
        """Generate index file with all the plots."""
        file_ids = self.list_files(report, log_type, False)

        file = open(os.path.join(self.ROOT, "plots/index.html"), mode="r")
        template = file.read()
        file.close()

        file_index = ""

        for file_id, file_names in self.generated_files.items():
            plots = []

            for file_name in file_names:
                plot_type = None

                if "operation" in file_name:
                    plot_type = "OPERATION"

                if "transfer" in file_name:
                    plot_type = "TRANSFER"

                if "spatiality" in file_name:
                    plot_type = "SPATIALITY"

                if "io_phase" in file_name:
                    plot_type = "IO PHASES"

                if "ost_usage_operation" in file_name:
                    plot_type = "OST USAGE OPERATION"

                if "ost_usage_transfer" in file_name:
                    plot_type = "OST USAGE TRANSFER"

                plots.append(
                    """
                    <li>
                        <a href="{}" target="_blank">{}</a>
                    </li>
                """.format(
                        os.path.basename(file_name), plot_type
                    )
                )

            file_index += """
                <li>
                    {}<br/>
                    <ul class='buttons'>
                        {}
                    </ul>
                </li>
            """.format(
                file_ids[file_id], "".join(plots)
            )

        self.explorer_end_time = time.time()

        template = template.replace("DXT_LOG_PATH", self.args.log_path)
        template = template.replace("DXT_EXPLORER_FILES", file_index)
        template = template.replace("DXT_EXPLORER_VERSION", dxt_version.__version__)
        template = template.replace("DXT_EXPLORER_DATE", str(datetime.datetime.now()))
        template = template.replace(
            "DXT_EXPLORER_RUNTIME",
            "{:03f}".format(self.explorer_end_time - self.explorer_start_time),
        )

        output_file = "{}/{}.html".format(self.prefix, "index")

        file = open(output_file, mode="w")
        file.write(template)
        file.close()

        self.logger.info("SUCCESS: {}".format(output_file))
        self.logger.info(
            "You can open the index.html file in your browser to interactively explore all plots"
        )

def main():
    PARSER = argparse.ArgumentParser(description="DXT Explorer: ")

    PARSER.add_argument("log_path", help="Input .darshan file or recorder folder")

    PARSER.add_argument(
        "-o",
        "--output",
        default=sys.stdout,
        type=argparse.FileType("w"),
        help="Output directory",
    )

    PARSER.add_argument("-p", "--prefix", default=None, help="Output directory")

    PARSER.add_argument(
        "-t",
        "--transfer",
        default=False,
        action="store_true",
        help="Generate an interactive data transfer explorer",
    )

    PARSER.add_argument(
        "-s",
        "--spatiality",
        default=False,
        action="store_true",
        help="Generate an interactive spatiality explorer",
    )

    PARSER.add_argument(
        "-i",
        "--io_phase",
        default=False,
        action="store_true",
        help="Generate an interactive I/O phase explorer",
    )

    PARSER.add_argument(
        "-oo",
        "--ost_usage_operation",
        default=False,
        action="store_true",
        help="Generate an interactive OST usage operation explorer",
    )

    PARSER.add_argument(
        "-ot",
        "--ost_usage_transfer",
        default=False,
        action="store_true",
        help="Generate an interactive OST usage data transfer size explorer",
    )

    PARSER.add_argument(
        "-r",
        "--rank_zero_workload",
        default=False,
        action="store_true",
        dest="rank_zero_workload",
        help="Determine if rank 0 is doing more I/O than the rest of the workload",
    )

    PARSER.add_argument(
        "-u",
        "--unbalanced_workload",
        default=False,
        action="store_true",
        dest="unbalanced_workload",
        help="Determine which ranks have unbalanced workload",
    )

    PARSER.add_argument(
        "-st",
        "--stragglers",
        default=False,
        action="store_true",
        dest="stragglers",
        help="Determine the 5 percent slowest operations in the time distribution",
    )

    PARSER.add_argument(
        "-d", "--debug", action="store_true", dest="debug", help="Enable debug mode"
    )

    PARSER.add_argument(
        "-l",
        "--list",
        action="store_true",
        dest="list_files",
        help="List all the files with trace",
    )

    PARSER.add_argument(
        "--start",
        action="store",
        dest="start",
        help="Report starts from X seconds (e.g., 3.7) from beginning of the job",
    )

    PARSER.add_argument(
        "--end",
        action="store",
        dest="end",
        help="Report ends at X seconds (e.g., 3.9) from beginning of the job",
    )

    PARSER.add_argument(
        "--from", action="store", dest="start_rank", help="Report start from rank N"
    )

    PARSER.add_argument(
        "--to", action="store", dest="end_rank", help="Report up to rank M"
    )

    PARSER.add_argument(
        "--browser",
        default=False,
        action="store_true",
        dest="browser",
        help="Open the browser with the generated plot",
    )

    PARSER.add_argument(
        "-csv",
        "--csv",
        default=False,
        action="store_true",
        dest="csv",
        help="Save the parsed DXT trace data into a csv",
    )

    PARSER.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s "
        + dxt_version.__version__
        + " ("
        + dxt_version.__release_date__
        + ")",
    )

    ARGS = PARSER.parse_args()

    EXPLORE = Explorer(ARGS)
    EXPLORE.run()
 
if __name__ == "__main__":
    main()