packages <- c(
        'ggplot2',
        'optparse',
        'plyr',
        'plotly',
        'htmlwidgets'
)

installed_packages <- packages %in% rownames(installed.packages())

dir.create(path = Sys.getenv("R_LIBS_USER"), showWarnings = FALSE, recursive = TRUE)

if (any(installed_packages == FALSE)) {
        install.packages(packages[!installed_packages], repos='http://cran.us.r-project.org', lib=Sys.getenv("R_LIBS_USER"))
}