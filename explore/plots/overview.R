#!/usr/bin/env Rscript

# DXT Explorer Copyright (c) 2021, The Regents of the University of
# California, through Lawrence Berkeley National Laboratory (subject
# to receipt of any required approvals from the U.S. Dept. of Energy). 
# All rights reserved.
# 
# If you have questions about your rights to use or distribute this software,
# please contact Berkeley Lab's Intellectual Property Office at
# IPO@lbl.gov.
# 
# NOTICE.  This Software was developed under funding from the U.S. Department
# of Energy and the U.S. Government consequently retains certain rights.  As
# such, the U.S. Government has been granted for itself and others acting on
# its behalf a paid-up, nonexclusive, irrevocable, worldwide license in the
# Software to reproduce, distribute copies to the public, prepare derivative 
# works, and perform publicly and display publicly, and to permit others to do so.

packages <- c(
    'ggplot2',
    'optparse',
    'plyr',
    'plotly',
    'rmarkdown',
    'htmlwidgets'
)

# Install packages not yet installed
installed_packages <- packages %in% rownames(installed.packages())

dir.create(path = Sys.getenv("R_LIBS_USER"), showWarnings = FALSE, recursive = TRUE)

if (any(installed_packages == FALSE)) {
    install.packages(packages[!installed_packages], repos='http://cran.us.r-project.org', lib=Sys.getenv("R_LIBS_USER"))
}

# Packages loading
invisible(lapply(packages, library, character.only = TRUE))

if (pandoc_available()) {
    self_contained = TRUE
} else {
    self_contained = FALSE
}

option_list = list(
    make_option(
        c('-f', '--file'),
        type = 'character',
        default = NULL, 
        help = 'DXT CSV file name',
        metavar = 'character'
    )
)

opt_parser = OptionParser(option_list=option_list)
opt = parse_args(opt_parser)

df <- read.csv(file=opt$file, sep = ',')

df$duration = df$end - df$start

duration = max(df$end) - min(df$start)

minimum = 0
maximum = max(df$end)

maximum_rank = max(df$rank)

minimum_limit = min(df$start) - (duration * 0.05)
maximum_limit = max(df$end) + (duration * 0.05)

# Include a zero record to ensure we can facet the plot
df <- rbind(df, 
    data.frame(
        file_id = c(0, 0, 0, 0),
        api = c('POSIX', 'POSIX', 'MPIIO', 'MPIIO'),
        rank = c(0, 0, 0, 0),
        operation = c('write', 'read', 'write', 'read'),
        segment = c(0, 0, 0, 0),
        offset = c(0, 0, 0, 0),
        size = c(0, 0, 0, 0),
        start = c(0, 0, 0, 0),
        end = c(0, 0, 0, 0),
        duration = c(0, 0, 0, 0),
        ost = c(NA, NA, NA, NA)
    )
)

df$operation <- as.factor(df$operation)

plot <- ggplot(
    df,
    aes(
        xmin = start,
        xmax = end,
        y = rank,
        color = operation
    )) +
    geom_errorbarh(height=0) +
#   geom_segment() +
    scale_color_manual(
        "",
        values = c(
            "#f0746e",
            "#3c93c2"
        ),
        drop = FALSE
    ) +
    scale_x_continuous(limits = c(minimum_limit, maximum_limit), breaks = seq(minimum_limit, maximum_limit, length.out = 10)) +
    facet_grid(api ~ ., scales="free_x") +
    ylim(0, maximum_rank) +
    geom_vline(
        xintercept = minimum
    ) +
    geom_vline(
        xintercept = minimum_limit,
        alpha = 0
    ) +
    geom_vline(
        xintercept = maximum
    ) +
    geom_vline(
        xintercept = maximum_limit,
        alpha = 0
    ) +
    xlab('Time') +
    ylab('Rank #') +
    theme_bw() +
    theme(
        legend.position = "top",
        plot.title = element_text(size = 10),
        strip.background = element_rect(colour = NA, fill = NA)
    )

#pdf(file = 'explore-overview.pdf', width = 10, height = 8)
#plot
#dev.off()

png(file = 'explore-overview.png', width = 2000, height = 1200)
plot
dev.off()
