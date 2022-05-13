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
    'wesanderson',
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
        file_id = c(0, 0),
        api = c('POSIX', 'POSIX'),
        rank = c(0, 0),
        operation = c('write', 'read'),
        segment = c(0, 0),
        offset = c(0, 0),
        size = c(0, 0),
        start = c(0, 0),
        end = c(0, 0),
        duration = c(0, 0),
        label = c('', ''),
        ost = c(NA, NA)
    )
)

df$operation <- as.factor(df$operation)

palette <- wes_palette('Zissou1', 100, type = 'continuous')

maximum = max(df$offset) + (max(df$offset) * 0.01)

plot_posix_write <- ggplot(
    df[df$api == 'POSIX' & df$operation == 'write', ],
    aes(
        xmin = offset,
        xmax = offset + size,
        y = rank,
        color = size,
        text = label
    )) +
    geom_errorbarh(height=0) +
    #geom_segment() +
    scale_x_continuous(breaks = seq(0, maximum, length.out = 10)) +
    facet_grid(operation ~ .) +
    scale_color_gradientn(
        'Request size\n(bytes)',
        colours = palette
    ) +  
    expand_limits(x = 0) +
    ylim(0, max(df$rank)) +
    xlab('File offset (bytes)') +
    ylab('Rank #') +
    theme_bw() +
    theme(
        legend.position = "top",
        plot.title = element_text(size = 10),
        strip.background = element_rect(colour = NA, fill = NA)
    )

plot_posix_read <- ggplot(
    df[df$api == 'POSIX' & df$operation == 'read', ],
    aes(
        xmin = offset,
        xmax = offset + size,
        y = rank,
        color = size,
        text = label
    )) +
    geom_errorbarh(height=0) +
    #geom_segment() +
    scale_x_continuous(breaks = seq(0, maximum, length.out = 10)) +
    facet_grid(operation ~ .) +
    scale_color_gradientn(
        'Request size\n(bytes)',
        colours = palette
    ) +  
    expand_limits(x = 0) +
    ylim(0, max(df$rank)) +
    xlab('File offset (bytes)') +
    ylab('Rank #') +
    theme_bw() +
    theme(
        legend.position = "top",
        plot.title = element_text(size = 10),
        strip.background = element_rect(colour = NA, fill = NA)
    )

p_posix_write <- ggplotly(
        plot_posix_write,
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
        xaxis = list(title = 'File offset (bytes)', matches = 'x'),
        yaxis = list(title = 'Rank', matches = 'y', fixedrange = FALSE),
        hoverlabel = list(font = list(color = 'white')),
        title = paste0(
            'Explore <b>Spatiality</b>',
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

p_posix_read <- ggplotly(
        plot_posix_read,
        width = 1800,
        height = 1000,
        tooltip = "text",
        legendgroup = operation,
        dynamicTicks = TRUE
    ) %>%
    rangeslider(0, maximum, thickness = 0.03) %>%
    layout(
        margin = list(pad = 0),
        legend = list(orientation = "h", x = 0, y = length(df$ranks) + 6),
        autosize = TRUE,
        xaxis = list(title = 'File offset (bytes)', matches = 'x'),
        yaxis = list(title = 'Rank', matches = 'y', fixedrange = FALSE),
        hoverlabel = list(font = list(color = 'white'))
    ) %>%
    toWebGL()

p <- subplot(
    p_posix_write, p_posix_read,
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
