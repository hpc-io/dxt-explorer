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

options(warn = -1)

sink(file('/dev/null', open='wt'), type = 'message')

packages <- c(
	'ggplot2',
	'optparse',
	'plyr',
	'plotly',
	'htmlwidgets'
)

# Install packages not yet installed
installed_packages <- packages %in% rownames(installed.packages())

if (any(installed_packages == FALSE)) {
	install.packages(packages[!installed_packages], repos='http://cran.us.r-project.org')
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
 
opt_parser = OptionParser(option_list=option_list)
opt = parse_args(opt_parser)

df <- read.csv(file=opt$file, sep = ',')

df$duration = df$end - df$start

df$label = paste0(
	'Rank: ', df$rank, '\n',
	'Operation: ', df$operation, '\n',
	'Duration: ', round(df$duration, digits = 3), ' seconds\n',
	'Size: ', (df$size / 1024), ' KB\n',
	'Offset: ', df$offset
)

maximum = max(df$end) + (max(df$end) * 0.01)

plot_posix <- ggplot(
	df[df$api == 'POSIX', ],
	aes(
		x = start,
		xend = end,
		y = rank,
		yend = rank,
		color = operation,
		text = label
	)) +
	geom_segment() +
	scale_color_manual(
		"",
		values = c(
			"#f0746e",
			"#3c93c2"
		)
	) +
	scale_x_continuous(breaks = seq(0, maximum, length.out = 10)) +
	facet_grid(api ~ .) +
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
		x = start,
		xend = end,
		y = rank,
		yend = rank,
		color = operation,
		text = label
	)) +
	geom_segment() +
	scale_color_manual(
		"",
		values = c(
			"#f0746e",
			"#3c93c2"
		)
	) +
	scale_x_continuous(breaks = seq(0, maximum, length.out = 10)) +
	facet_grid(api ~ .) +
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
		legendgroup = operation
	) %>%
	layout(
		margin = list(pad = 0),
		yaxis = list(fixedrange = FALSE),
		legend = list(orientation = "h", x = 0, y = length(df$ranks) + 6),
		autosize = TRUE,
		xaxis = list(matches = 'x')
	) %>%
	toWebGL()

p_mpiio <- ggplotly(
		plot_mpiio,
		width = 1800,
		height = 1000,
		tooltip = "text",
		legendgroup = operation
	) %>%
	rangeslider(min(df$start), max(df$end), thickness = 0.05) %>%
	layout(
		margin = list(pad = 0),
		yaxis = list(fixedrange = FALSE),
		legend = list(orientation = "h", x = 0, y = length(df$ranks) + 6),
		autosize = TRUE,
		xaxis = list(matches = 'x')

	) %>%
	style(
    		showlegend = FALSE
	) %>%
	toWebGL()

p <- subplot(p_posix, p_mpiio, nrows = 2)

saveWidget(p, selfcontained = FALSE, 'explore.html')
