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
    'png',
    'ggplot2',
    'optparse',
    'plyr',
    'plotly',
    'rmarkdown',
    'htmlwidgets',
    'R.utils',
    'Cairo'
)

# Install packages not yet installed
installed_packages <- packages %in% rownames(installed.packages())

dir.create(path = Sys.getenv("R_LIBS_USER"), showWarnings = FALSE, recursive = TRUE)

if (any(installed_packages == FALSE)) {
    install.packages(packages[!installed_packages], repos='http://cran.us.r-project.org', quiet=TRUE, lib=Sys.getenv("R_LIBS_USER"))
}

# Packages loading
invisible(lapply(packages, library, warn.conflicts = FALSE, quietly = TRUE, character.only = TRUE))

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
        metavar = 'file'
    ),
    make_option(
        c('-s', '--start'),
        type = 'numeric',
        default = NULL, 
        help = 'Mark trace start time',
        metavar = 'start'
    ),
    make_option(
        c('-e', '--end'),
        type = 'numeric',
        default = NULL, 
        help = 'Mark trace end time',
        metavar = 'end'
    ),
    make_option(
        c('-n', '--from'),
        type = 'numeric',
        default = NULL, 
        help = 'Display trace from rank N',
        metavar = 'from'
    ),
    make_option(
        c('-m', '--to'),
        type = 'numeric',
        default = NULL, 
        help = 'Display trace up to rank M',
        metavar = 'to'
    ),
    make_option(
        c('-o', '--output'),
        type = 'character',
        default = NULL, 
        help = 'Name of the output file',
        metavar = 'output'
    ),
    make_option(
        c('-x', '--identifier'),
        type = 'character',
        default = TRUE, 
        help = 'Set the identifier of the original file captured by Darshan DXT',
        metavar = 'identifier'
    )
)

opt_parser = OptionParser(option_list=option_list)
opt = parse_args(opt_parser)

base = commandArgs()
base = base[grepl('--file', base, fixed=TRUE)]
if (!is.null(base)) {
    base = strsplit(base, split='=')
    base = sapply(base, tail, 1)
}

base = dirname(base)

df <- read.csv(file=opt$file, sep = ',')

df$duration = df$end - df$start

duration = max(df$end) - min(df$start)

minimum = 0
maximum = max(df$end)

maximum_rank = max(df$rank)

minimum_limit = -0.05
maximum_limit = max(df$end) + (duration * 0.05)

if (!is.null(opt$start)) {
    df <- df[df$start >= opt$start, ]
}

if (!is.null(opt$end)) {
    df <- df[df$end <= opt$end, ]
}

if (!is.null(opt$from)) {
    df <- df[df$rank >= opt$from, ]
}

if (!is.null(opt$to)) {
    df <- df[df$rank <= opt$to, ]
}

if (nrow(df) == 0) {
    quit()
}

df$label = paste0(
    'Rank: ', df$rank, '\n',
    'Operation: ', df$operation, '\n',
    'Duration: ', round(df$duration, digits = 3), ' seconds\n',
    'Size: ', (df$size / 1024), ' KB\n',
    'Offset: ', df$offset, '\n',
    'Lustre OST: ', ifelse(is.na(df$ost), '-', df$ost)
)

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
        label = c('', '', '', ''),
        ost = c(NA, NA, NA, NA)
    )
)

df$operation <- as.factor(df$operation)

plot_posix <- ggplot(
    df[df$api == 'POSIX', ],
    aes(
        xmin = start,
        xmax = end,
        y = rank,
        color = operation,
        text = label
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
    ylim(0, maximum_rank)

if (!is.null(opt$start)) {
    plot_posix <- plot_posix +
        geom_vline(
            xintercept = opt$start,
            linetype = "longdash"
        ) +
        geom_vline(
            xintercept = minimum_limit - (duration * 0.05),
            alpha = 0
        ) + 
        annotate(
            "rect",
            fill = "gray",
            alpha = 0.5,
            xmin = minimum,
            xmax = opt$start,
            ymin = 0,
            ymax = maximum_rank
        )
}

    plot_posix <- plot_posix +
        geom_vline(
            xintercept = minimum
        ) +
        geom_vline(
            xintercept = minimum_limit,
            alpha = 0
        ) 

if (!is.null(opt$end)) {
    plot_posix <- plot_posix +
        geom_vline(
            xintercept = opt$end,
            linetype = "longdash"
        ) +
        geom_vline(
            xintercept = maximum_limit + (duration * 0.05),
            alpha = 0
        ) + 
        annotate(
            "rect",
            fill = "gray",
            alpha = 0.5,
            xmin = opt$end,
            xmax = maximum,
            ymin = 0,
            ymax = maximum_rank
        )
}

    plot_posix <- plot_posix + 
        geom_vline(
            xintercept = maximum
        ) +
        geom_vline(
            xintercept = maximum_limit,
            alpha = 0
        )

if (!is.null(opt$from)) {
    plot_posix <- plot_posix +
        geom_hline(
            yintercept = opt$from,
            linetype = "longdash"
        ) + 
        annotate(
            "rect",
            fill = "gray",
            alpha = 0.5,
            xmin = minimum,
            xmax = maximum,
            ymin = 0,
            ymax = opt$from
        )
}

if (!is.null(opt$to)) {
    plot_posix <- plot_posix +
        geom_hline(
            yintercept = opt$to,
            linetype = "longdash"
        ) + 
        annotate(
            "rect",
            fill = "gray",
            alpha = 0.5,
            xmin = minimum,
            xmax = maximum,
            ymin = opt$to,
            ymax = maximum_rank
        )
}

plot_posix <- plot_posix +
    xlab('Time') +
    ylab('Rank #') +
    theme_bw() +
    theme(
        legend.position = "top",
        plot.title = element_text(size = 10),
        strip.background = element_rect(colour = NA, fill = NA)
    )

plot_mpiio <- ggplot(
    df[df$api == 'MPIIO', ],
    aes(
        xmin = start,
        xmax = end,
        y = rank,
        color = operation,
        text = label
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
    ylim(0, maximum_rank)

if (!is.null(opt$start)) {
    plot_mpiio <- plot_mpiio +
        geom_vline(
            xintercept = opt$start,
            linetype = "longdash"
        ) +
        geom_vline(
            xintercept = minimum_limit - (duration * 0.05),
            alpha = 0
        )+ 
        annotate(
            "rect",
            fill = "gray",
            alpha = 0.5,
            xmin = minimum,
            xmax = opt$start,
            ymin = 0,
            ymax = maximum_rank
        )
}
    plot_mpiio <- plot_mpiio +
        geom_vline(
            xintercept = minimum
        ) +
        geom_vline(
            xintercept = minimum_limit,
            alpha = 0
        ) 

if (!is.null(opt$end)) {
    plot_mpiio <- plot_mpiio +
        geom_vline(
            xintercept = opt$end,
            linetype = "longdash"
        ) +
        geom_vline(
            xintercept = maximum_limit + (duration * 0.05),
            alpha = 0
        ) + 
        annotate(
            "rect",
            fill = "gray",
            alpha = 0.5,
            xmin = opt$end,
            xmax = maximum,
            ymin = 0,
            ymax = maximum_rank
        )
}
    plot_mpiio <- plot_mpiio + 
        geom_vline(
            xintercept = maximum
        ) +
        geom_vline(
            xintercept = maximum_limit,
            alpha = 0
        )

if (!is.null(opt$from)) {
    plot_mpiio <- plot_mpiio +
        geom_hline(
            yintercept = opt$from,
            linetype = "longdash"
        ) + 
        annotate(
            "rect",
            fill = "gray",
            alpha = 0.5,
            xmin = minimum,
            xmax = maximum,
            ymin = 0,
            ymax = opt$from
        )
}

if (!is.null(opt$to)) {
    plot_mpiio <- plot_mpiio +
        geom_hline(
            yintercept = opt$to,
            linetype = "longdash"
        ) + 
        annotate(
            "rect",
            fill = "gray",
            alpha = 0.5,
            xmin = minimum,
            xmax = maximum,
            ymin = opt$to,
            ymax = maximum_rank
        )
}

plot_mpiio <- plot_mpiio +
    xlab('Time') +
    ylab('Rank #') +
    theme_bw() +
    theme(
        legend.position = "top",
        plot.title = element_text(size = 10),
        strip.background = element_rect(colour = NA, fill = NA)
    )

p_posix <- ggplotly(
        plot_posix,
        width = 1800,
        height = 1000,
        tooltip = "text",
        dynamicTicks = TRUE
    )

if (!is.null(opt$start)) { 
    p_posix <- p_posix %>% add_annotations(
        x = opt$start,
        y = maximum_rank / 2,
        ax = -20,
        ay = 0,
        text = "TIMELINE IS TRUNCATED",
        textangle = -90,
        font = list(
            color = '#454545',
            size = 10
        )
    )
}

if (!is.null(opt$end)) {
    p_posix <- p_posix %>% add_annotations(
        x = opt$end,
        y = maximum_rank / 2,
        ax = 20,
        ay = 0,
        text = "TIMELINE IS TRUNCATED",
        textangle = 90,
        font = list(
            color = '#454545',
            size = 10
        )
    )
}

if (!is.null(opt$from)) { 
    p_posix <- p_posix %>% add_annotations(
        x = maximum / 2,
        y = opt$from,
        ax = 0,
        ay = 20,
        text = "RANK BEHAVIOR IS TRUNCATED",
        font = list(
            color = '#454545',
            size = 10
        )
    )
}

if (!is.null(opt$to)) {
    p_posix <- p_posix %>% add_annotations(
        x = maximum / 2,
        y = opt$to,
        ax = 0,
        ay = -20,
        text = "RANK BEHAVIOR IS TRUNCATED",
        font = list(
            color = '#454545',
            size = 10
        )
    )
}

p_posix <- p_posix %>%
    rangeslider(minimum, maximum, thickness = 0.03) %>%
    layout(
        margin = list(pad = 0),
        legend = list(orientation = "h", x = 1, y = length(df$ranks) + 6),
        autosize = TRUE,
        xaxis = list(title = 'Runtime (seconds)', matches = 'x'),
        yaxis = list(title = 'Rank', matches = 'y', fixedrange = FALSE),
        hoverlabel = list(font = list(color = 'white')),
        title = paste0(
            'Explore <b>Operation</b>',
            '<br>',
            '<sup>',
            opt$identifier,
            '</sup>'
        )
    ) %>%
    style(
        showlegend = FALSE
    ) %>%
    toWebGL()

p_mpiio <- ggplotly(
        plot_mpiio,
        width = 1800,
        height = 1000,
        tooltip = "text",
        legendgroup = operation,
        dynamicTicks = TRUE
    )

if (!is.null(opt$start)) { 
    p_mpiio <- p_mpiio %>% add_annotations(
        x = opt$start,
        y = maximum_rank / 2,
        ax = -20,
        ay = 0,
        text = "TIMELINE IS TRUNCATED",
        textangle = -90,
        font = list(
            color = '#454545',
            size = 10
        )
    )
}

if (!is.null(opt$end)) {
    p_mpiio <- p_mpiio %>% add_annotations(
        x = opt$end,
        y = maximum_rank / 2,
        ax = 20,
        ay = 0,
        text = "TIMELINE IS TRUNCATED",
        textangle = 90,
        font = list(
            color = '#454545',
            size = 10
        )
    )
}

if (!is.null(opt$from)) { 
    p_mpiio <- p_mpiio %>% add_annotations(
        x = maximum / 2,
        y = opt$from,
        ax = 0,
        ay = 20,
        text = "RANK BEHAVIOR IS TRUNCATED",
        font = list(
            color = '#454545',
            size = 10
        )
    )
}

if (!is.null(opt$to)) {
    p_mpiio <- p_mpiio %>% add_annotations(
        x = maximum / 2,
        y = opt$to,
        ax = 0,
        ay = -20,
        text = "RANK BEHAVIOR IS TRUNCATED",
        font = list(
            color = '#454545',
            size = 10
        )
    )
}

p_mpiio <- p_mpiio %>%
    layout(
        margin = list(pad = 0),
        # legend = list(orientation = "h", x = 0, y = length(df$ranks) + 6),
        autosize = TRUE,
        xaxis = list(matches = 'x'),
        yaxis = list(title = 'Rank', matches = 'y', fixedrange = FALSE),
        hoverlabel = list(font = list(color = 'white'))
    ) %>%
    style(
        showlegend = FALSE
    ) %>%
    toWebGL()

p <- subplot(
    p_mpiio, p_posix,
    nrows = 2,
    titleY = TRUE,
    titleX = TRUE,
    shareX = TRUE,
    shareY = TRUE
) %>%
layout (
    margin = list(t = 130),
    images = list(
        source = raster2uri(as.raster(readPNG(paste(base, 'dxt-explorer.png', sep = '/')))),
        x = 0,
        y = 1.02, 
        sizex = 0.2,
        sizey = 0.2,
        xref = 'paper',
        yref = 'paper', 
        xanchor = 'middle',
        yanchor = 'bottom'
    )
) %>%
config(
    displaylogo = FALSE
)

saveWidget(p, selfcontained = self_contained, opt$output)
