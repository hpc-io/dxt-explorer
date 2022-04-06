#!/usr/bin/env Rscript

#options(warn = -1)

#sink(file('/dev/null', open='wt'), type = 'message')

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
    install.packages(packages[!installed_packages], repos='http://cran.us.r-project.org')
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

df$label = paste0('Rank: ', df$rank, '\nOperation: ', df$operation, '\nDuration: ', round(df$duration, digits = 3), ' seconds\nSize: ', (df$size / 1024), ' KB\nOffset: ', df$offset)

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

maximum = max(df$end) + (max(df$end) * 0.01)

plot_posix_write <- ggplot(
    df[df$api == 'POSIX' & df$operation == 'read', ],
    aes(
        x = offset,
        ymin = start,
        ymax = end,
        size = size,
        color = size,
        text = label
    )) +
    geom_linerange() +
    coord_flip() +
    scale_x_continuous(breaks = seq(0, maximum, length.out = 10)) +
    facet_grid(operation ~ .) +
    scale_color_gradientn(
        'Request size\n(bytes)',
        colours = palette
    ) +  
    expand_limits(x = 0) +
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
    rangeslider(min(df$start), max(df$end), thickness = 0.03) %>%
    layout(
        margin = list(pad = 0),
        legend = list(orientation = "h", x = 0, y = length(df$ranks) + 6),
        autosize = TRUE,
        xaxis = list(title = 'Runtime (seconds)', matches = 'x'),
        yaxis = list(title = 'File Offset (bytes)', fixedrange = FALSE),
        hoverlabel = list(font = list(color = 'white')),
        title = '<b>DXT Explorer</b> File Offset/Time'
    ) %>%
    style(
            showlegend = FALSE
    ) %>%
    toWebGL()

p <- subplot(
    p_posix_write,
    nrows = 1,
    titleY = TRUE,
    titleX = TRUE,
    shareX = TRUE,
    shareY = TRUE
)

saveWidget(p, selfcontained = self_contained, 'explore-space-time.html')
