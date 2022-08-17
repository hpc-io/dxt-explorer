#!/usr/bin/env Rscript

packages <- c(
    'png',
    'ggplot2',
    'optparse',
    'plyr',
    'plotly',
    'rmarkdown',
    'htmlwidgets',
    'wesanderson',
    'Cairo'
)

dir.create(
    path = Sys.getenv("R_LIBS_USER"),
    showWarnings = FALSE,
    recursive = TRUE
)

install.packages(
    packages,
    repos='http://cran.us.r-project.org',
    lib=Sys.getenv("R_LIBS_USER")
)