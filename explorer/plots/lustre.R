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

df$rate <- (df$size / 1024 / 1024 / 1024) / df$duration

plot_posix_write <- ggplot(
	df[df$api == 'POSIX' & df$operation == 'write', ],
	aes(
		x = as.factor(ost),
		y = rate
	)) +
	geom_boxplot() +
	theme_bw() +
	theme(
		legend.position = "top",
		plot.title = element_text(size = 10),
		strip.background = element_rect(colour = NA, fill = NA)
	)

plot_posix_read <- ggplot(
	df[df$api == 'POSIX' & df$operation == 'read' & !is.nan(df$rate), ],
	aes(
		x = as.factor(ost),
		y = rate
	)) +
	geom_boxplot() +
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
		dynamicTicks = TRUE
	) %>%
	layout(
		margin = list(pad = 0),
		autosize = TRUE,
		xaxis = list(title = 'Lustre OST', matches = 'x'),
		yaxis = list(title = 'I/O ratio (GB/s)', matches = 'y', fixedrange = FALSE),
		title = '<b>DXT Explorer</b> Lustre OST'
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
		dynamicTicks = TRUE
	) %>%
	layout(
		margin = list(pad = 0),
		autosize = TRUE,
		xaxis = list(title = 'Lustre OST', matches = 'x'),
		yaxis = list(title = 'I/O ratio (GB/s)', matches = 'y', fixedrange = FALSE)
	) %>%
	style(
    		showlegend = FALSE
	) %>%
	toWebGL()

p <- subplot(
	p_posix_write, p_posix_read,
	nrows = 2,
	titleY = TRUE,
	titleX = TRUE,
	shareX = TRUE,
	shareY = TRUE
)

saveWidget(p, selfcontained = TRUE, 'explore-lustre.html')
