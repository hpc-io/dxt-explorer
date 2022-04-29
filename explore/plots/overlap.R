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
    'htmlwidgets',
    'wesanderson'
)

# Install packages not yet installed
installed_packages <- packages %in% rownames(installed.packages())

dir.create(path = Sys.getenv("R_LIBS_USER"), showWarnings = FALSE, recursive = TRUE)

if (any(installed_packages == FALSE)) {
    install.packages(packages[!installed_packages], repos='http://cran.us.r-project.org', lib=Sys.getenv("R_LIBS_USER"))
}

# Packages loading
invisible(lapply(packages, library, character.only = TRUE))

option_list = list(
    make_option(
        c('-f', '--file'),
        type = 'character',
        default = NULL, 
        help = 'DXT CSV file name',
        metavar = 'character'
    )
)

if (pandoc_available()) {
    self_contained = TRUE
} else {
    self_contained = FALSE
}
 
opt_parser = OptionParser(option_list=option_list)
opt = parse_args(opt_parser)

df <- read.csv(file=opt$file, sep = ',')

df$label = paste0('Rank: ', df$rank, '\nOperation: ', df$operation)

df$operation <- as.factor(df$operation)

# Include a zero record to ensure we can facet the plot
df <- rbind(df, 
    data.frame(
        api = c('POSIX', 'POSIX', 'MPIIO', 'MPIIO'),
        rank = c(0, 0, 0, 0),
        operation = c('write', 'read', 'write', 'read'),
        start_offset = c(0, 0, 0, 0),
        end_offset = c(0, 0, 0, 0),
        label = c('', '', '', '')
    )
)

palette <- wes_palette('Zissou1', 100, type = 'continuous')

maximum = max(df$end) + (max(df$end) * 0.01)

plot_posix <- ggplot(
    df[df$api == 'POSIX', ],
    aes(
        x = start_offset,
        xend = end_offset,
        y = rank,
        yend = rank,
        #color = size,
        text = label
    )) +
    geom_segment() +
    scale_x_continuous(breaks = seq(0, maximum, length.out = 10)) +
    facet_grid(api ~ .) +
    scale_color_gradientn(
        'Request size\n(bytes)',
        colours = palette
    ) +  
    expand_limits(x = 0) +
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
        x = start_offset,
        xend = end_offset,
        y = rank,
        yend = rank,
        #color = size,
        text = label
    )) +
    geom_segment() +
    scale_x_continuous(breaks = seq(0, maximum, length.out = 10)) +
    facet_grid(api ~ .) +
    scale_color_gradientn(
        'Request size\n(bytes)',
        colours = palette
    ) +  
    expand_limits(x = 0) +
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
        legendgroup = operation,
        dynamicTicks = TRUE
    ) %>%
    rangeslider(min(df$start), max(df$end), thickness = 0.03) %>%
    layout(
        margin = list(pad = 0),
        legend = list(orientation = "h", x = 0, y = length(df$ranks) + 6),
        autosize = TRUE,
        xaxis = list(title = 'Runtime (seconds)', matches = 'x'),
        yaxis = list(title = 'Rank', matches = 'y', fixedrange = FALSE),
        hoverlabel = list(font = list(color = 'white')),
        title = '<b>DXT Explorer</b> Transfer Size'
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
    ) %>%
    layout(
        margin = list(pad = 0),
        legend = list(orientation = "h", x = 0, y = length(df$ranks) + 6),
        autosize = TRUE,
        xaxis = list(matches = 'x'),
        yaxis = list(title = 'Rank', matches = 'y', fixedrange = FALSE),
        hoverlabel = list(font = list(color = 'white'))
    ) %>%
    toWebGL()

p <- subplot(
    p_mpiio, p_posix,
    nrows = 2,
    titleY = TRUE,
    titleX = TRUE,
    shareX = TRUE,
    shareY = TRUE
)

saveWidget(p, selfcontained = self_contained, 'explore-overlap.html')
