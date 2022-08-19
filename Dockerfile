FROM ubuntu

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    pip \
    make \
    git \
    wget \
    libssl-dev \
    libcurl4-openssl-dev \
    r-base \
    r-cran-curl \
    r-cran-openssl \
    r-cran-httr \
    r-cran-plotly \
    r-cran-cairo
RUN rm -rf /var/lib/apt/lists/*

RUN wget ftp://ftp.mcs.anl.gov/pub/darshan/releases/darshan-3.3.1.tar.gz
RUN tar zxvf darshan-3.3.1.tar.gz
WORKDIR /darshan-3.3.1/darshan-util/

RUN ./configure
RUN make
RUN make install

WORKDIR /

RUN git clone https://github.com/hpc-io/dxt-explorer

WORKDIR /dxt-explorer

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN Rscript install-r-libraries.R
RUN pip install .

ENTRYPOINT ["dxt-explorer"]
