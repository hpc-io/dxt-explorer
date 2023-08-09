import logging
import pandas as pd
import logging.handlers


class insights:
    def __init__(self, df):
        """Initialize the recommendation system."""
        self.df = df
        self.configure_log()

    def configure_log(self):
        """Configure the logging system."""
        self.logger = logging.getLogger("DXT Explorer")

        # Defines the format of the logger
        formatter = logging.Formatter(
            "%(asctime)s %(module)s - %(levelname)s - %(message)s"
        )

        console = logging.StreamHandler()

        console.setFormatter(formatter)

        self.logger.addHandler(console)

    def get_stats(self, df, read_count, write_count, total_size, time_flag, time=None):
        total = 0
        for i in range(len(df)):
            read_count.append(df[i]["read_count"])
            write_count.append(df[i]["write_count"])
            if not df[i]["write_segments"].empty:
                total = total + sum(df[i]["write_segments"]["length"])
            if not df[i]["read_segments"].empty:
                total = total + sum(df[i]["read_segments"]["length"])

            total_size.append(total)
            total = 0

            if time_flag:
                duration_read = 0
                duration_write = 0
                if not df[i]["write_segments"].empty:
                    duration_write = (
                        df[i]["write_segments"]["end_time"]
                        - df[i]["write_segments"]["start_time"]
                    )
                    duration_write = sum(duration_write)
                if not df[i]["read_segments"].empty:
                    duration_read = (
                        df[i]["read_segments"]["end_time"]
                        - df[i]["read_segments"]["start_time"]
                    )
                    duration_read = sum(duration_read)
                time.append(duration_read + duration_write)

    def rank_zero_workload(self):
        message = []
        if not self.df.empty:
            read_count_mpiio = 0
            write_count_mpiio = 0
            total_size_mpiio = 0

            read_count_posix = 0
            write_count_posix = 0
            total_size_posix = 0

            break_flag_mpiio = [False, False, False]
            break_flag_posix = [False, False, False]

            unique_val = self.df["rank"].unique().tolist()

            for val in unique_val:
                if val == 0:
                    temp_df = self.df.loc[self.df["rank"] == val]
                    temp_df = temp_df.loc[temp_df["api"] == "MPIIO"]
                    if not temp_df.empty:
                        total_size_mpiio = temp_df["size"].sum()
                        read_count_mpiio = len(
                            temp_df.loc[temp_df["operation"] == "read"]
                        )
                        write_count_mpiio = len(
                            temp_df.loc[temp_df["operation"] == "write"]
                        )

                    temp_df = self.df.loc[self.df["rank"] == val]
                    temp_df = temp_df.loc[temp_df["api"] == "POSIX"]
                    if not temp_df.empty:
                        total_size_posix = temp_df["size"].sum()
                        read_count_posix = len(
                            temp_df.loc[temp_df["operation"] == "read"]
                        )
                        write_count_posix = len(
                            temp_df.loc[temp_df["operation"] == "write"]
                        )
                else:
                    if all(break_flag_posix) and all(break_flag_mpiio):
                        break
                    else:
                        if not all(break_flag_mpiio):
                            temp_df = self.df.loc[self.df["rank"] == val]
                            temp_df = temp_df.loc[temp_df["api"] == "MPIIO"]
                            if not temp_df.empty:
                                if temp_df["size"].sum() > total_size_mpiio:
                                    break_flag_mpiio[0] = True
                                if (
                                    len(temp_df.loc[temp_df["operation"] == "read"])
                                    > read_count_mpiio
                                ):
                                    break_flag_mpiio[1] = True
                                if (
                                    len(temp_df.loc[temp_df["operation"] == "write"])
                                    > write_count_mpiio
                                ):
                                    break_flag_mpiio[2] = True

                        if not all(break_flag_posix):
                            temp_df = self.df.loc[self.df["rank"] == val]
                            temp_df = temp_df.loc[temp_df["api"] == "POSIX"]
                            if not temp_df.empty:
                                if temp_df["size"].sum() > total_size_posix:
                                    break_flag_posix[0] = True
                                if (
                                    len(temp_df.loc[temp_df["operation"] == "read"])
                                    > read_count_posix
                                ):
                                    break_flag_posix[1] = True
                                if (
                                    len(temp_df.loc[temp_df["operation"] == "write"])
                                    > write_count_posix
                                ):
                                    break_flag_posix[2] = True

            if (
                break_flag_mpiio[0] is False
                and break_flag_mpiio[1] is False
                and break_flag_mpiio[2] is False
            ):
                diagnosis = "True: MPIIO doing more I/O operations than the rest of the workload"
            elif break_flag_mpiio[0] is False and break_flag_mpiio[1] is False:
                diagnosis = "True: MPIIO doing more read operations than the rest of the workload"
            elif break_flag_mpiio[0] is False and break_flag_mpiio[2] is False:
                diagnosis = "True: MPIIO doing more read operations than the rest of the workload"
            else:
                diagnosis = "False: MPIIO not doing more I/0 operations than the rest of the workload"

            message.append(diagnosis)

            if (
                break_flag_posix[0] is False
                and break_flag_posix[1] is False
                and break_flag_posix[2] is False
            ):
                diagnosis = "True: POSIX doing more I/O operations than the rest of the workload"
            elif break_flag_posix[0] is False and break_flag_posix[1] is False:
                diagnosis = "True: POSIX doing more read operations than the rest of the workload"
            elif break_flag_posix[0] is False and break_flag_posix[2] is False:
                diagnosis = "True: POSIX doing more read operations than the rest of the workload"
            else:
                diagnosis = "False: POSIX not doing more I/0 operations than the rest of the workload"

            message.append(diagnosis)

        return message

    def unbalanced_workloads(self):
        ranks_dict = {}

        df_posix = self.df[self.df["api"] == "POSIX"]
        if not df_posix.empty:
            read_count_posix = []
            write_count_posix = []
            total_size = []
            time = []

            unique_val = df_posix["rank"].unique().tolist()

            for val in unique_val:
                temp_df = df_posix.loc[df_posix["rank"] == val]
                if not temp_df.empty:
                    total_size.append(temp_df["size"].sum())
                    read_count_posix.append(
                        len(temp_df.loc[temp_df["operation"] == "read"])
                    )
                    write_count_posix.append(
                        len(temp_df.loc[temp_df["operation"] == "write"])
                    )
                    time.append(temp_df["duration"].sum())

            mean_read = sum(read_count_posix) / len(read_count_posix)
            variance = sum([((x - mean_read) ** 2) for x in read_count_posix]) / len(
                read_count_posix
            )
            std_dev_read = variance**0.5

            mean_write = sum(write_count_posix) / len(write_count_posix)
            variance = sum([((x - mean_write) ** 2) for x in write_count_posix]) / len(
                write_count_posix
            )
            std_dev_write = variance**0.5

            mean_size = sum(total_size) / len(total_size)
            variance = sum([((x - mean_size) ** 2) for x in total_size]) / len(
                total_size
            )
            std_dev_size = variance**0.5

            mean_time = sum(time) / len(time)
            variance = sum([((x - mean_time) ** 2) for x in time]) / len(time)
            std_dev_time = variance**0.5

            threshold = 1

            rank_read = []
            for i in range(len(read_count_posix)):
                if read_count_posix[i] > mean_read + threshold * std_dev_read:
                    rank_read.append(i)

            rank_write = []
            for i in range(len(write_count_posix)):
                if write_count_posix[i] > mean_write + threshold * std_dev_write:
                    rank_write.append(i)

            rank_size = []
            for i in range(len(total_size)):
                if total_size[i] > mean_size + threshold * std_dev_size:
                    rank_size.append(i)

            rank_time = []
            for i in range(len(time)):
                if time[i] > mean_time + threshold * std_dev_time:
                    rank_time.append(i)

            common_ranks = set(rank_read).intersection(set(rank_write))
            common_ranks = common_ranks.intersection(set(rank_size))
            common_ranks = common_ranks.intersection(set(rank_time))

            common_ranks = list(common_ranks)

            if common_ranks:
                ranks_dict["POSIX"] = common_ranks

        df_mpiio = self.df[self.df["api"] == "MPIIO"]
        if not df_mpiio.empty:
            read_count_mpiio = []
            write_count_mpiio = []
            total_size = []
            time = []

            unique_val = df_mpiio["rank"].unique().tolist()

            for val in unique_val:
                temp_df = df_mpiio.loc[df_mpiio["rank"] == val]
                if not temp_df.empty:
                    total_size.append(temp_df["size"].sum())
                    read_count_mpiio.append(
                        len(temp_df.loc[temp_df["operation"] == "read"])
                    )
                    write_count_mpiio.append(
                        len(temp_df.loc[temp_df["operation"] == "write"])
                    )
                    time.append(temp_df["duration"].sum())

            mean_read = sum(read_count_mpiio) / len(read_count_mpiio)
            variance = sum([((x - mean_read) ** 2) for x in read_count_mpiio]) / len(
                read_count_mpiio
            )
            std_dev_read = variance**0.5

            mean_write = sum(write_count_mpiio) / len(write_count_mpiio)
            variance = sum([((x - mean_write) ** 2) for x in write_count_mpiio]) / len(
                write_count_mpiio
            )
            std_dev_write = variance**0.5

            mean_size = sum(total_size) / len(total_size)
            variance = sum([((x - mean_size) ** 2) for x in total_size]) / len(
                total_size
            )
            std_dev_size = variance**0.5

            mean_time = sum(time) / len(time)
            variance = sum([((x - mean_time) ** 2) for x in time]) / len(time)
            std_dev_time = variance**0.5

            threshold = 1

            rank_read = []
            for i in range(len(read_count_mpiio)):
                if read_count_mpiio[i] > mean_read + threshold * std_dev_read:
                    rank_read.append(i)

            rank_write = []
            for i in range(len(write_count_mpiio)):
                if write_count_mpiio[i] > mean_write + threshold * std_dev_write:
                    rank_write.append(i)

            rank_size = []
            for i in range(len(total_size)):
                if total_size[i] > mean_size + threshold * std_dev_size:
                    rank_size.append(i)

            rank_time = []
            for i in range(len(time)):
                if time[i] > mean_time + threshold * std_dev_time:
                    rank_time.append(i)

            common_ranks = set(rank_read).intersection(set(rank_write))
            common_ranks = common_ranks.intersection(set(rank_size))
            common_ranks = common_ranks.intersection(set(rank_time))

            common_ranks = list(common_ranks)

            if common_ranks:
                ranks_dict["MPIIO"] = common_ranks

        return ranks_dict

    def collective_metadata(self):

        df_posix = self.df[self.df["api"] == "POSIX"]
        rank_count = df_posix["rank"].unique().size
        df_posix = df_posix[df_posix["size"] < 93000]
        df = df_posix.groupby(["offset"], as_index=False)["rank"].count()
        df = df[df["rank"] >= rank_count - 1]
        offset_list = df["offset"].values.tolist()
        df_posix = df_posix[df_posix["offset"].isin(offset_list)]

        return df_posix

    def stragglers(self, df):
        stragglers_df = df
        df_posix = stragglers_df[stragglers_df["api"] == "POSIX"]
        io_phases_with_rank_posix = pd.DataFrame(
            columns=["api", "rank", "start", "end", "duration", "operation"]
        )

        for i in range(len(df_posix)):
            df_row = df_posix.iloc[i]
            row_fastest = [
                df_row["api"],
                df_row["fastest_rank"],
                df_row["fastest_rank_start"],
                df_row["fastest_rank_end"],
                df_row["fastest_rank_duration"],
                "fastest",
            ]
            row_slowest = [
                df_row["api"],
                df_row["slowest_rank"],
                df_row["slowest_rank_start"],
                df_row["slowest_rank_end"],
                df_row["slowest_rank_duration"],
                "slowest",
            ]

            io_phases_with_rank_posix.loc[
                len(io_phases_with_rank_posix.index)
            ] = row_fastest
            io_phases_with_rank_posix.loc[
                len(io_phases_with_rank_posix.index)
            ] = row_slowest
            io_phases_with_rank_posix["duration"] = io_phases_with_rank_posix[
                "duration"
            ].round(4)

        df_mpiio = stragglers_df[stragglers_df["api"] == "MPIIO"]
        io_phases_with_rank_mpiio = pd.DataFrame(
            columns=["api", "rank", "start", "end", "duration", "operation"]
        )

        for i in range(len(df_mpiio)):
            df_row = df_mpiio.iloc[i]
            row_fastest = [
                df_row["api"],
                df_row["fastest_rank"],
                df_row["fastest_rank_start"],
                df_row["fastest_rank_end"],
                df_row["fastest_rank_duration"],
                "fastest",
            ]
            row_slowest = [
                df_row["api"],
                df_row["slowest_rank"],
                df_row["slowest_rank_start"],
                df_row["slowest_rank_end"],
                df_row["slowest_rank_duration"],
                "slowest",
            ]

            io_phases_with_rank_mpiio.loc[
                len(io_phases_with_rank_mpiio.index)
            ] = row_fastest
            io_phases_with_rank_mpiio.loc[
                len(io_phases_with_rank_mpiio.index)
            ] = row_slowest
            io_phases_with_rank_mpiio["duration"] = io_phases_with_rank_mpiio[
                "duration"
            ].round(4)

        return io_phases_with_rank_posix, io_phases_with_rank_mpiio
