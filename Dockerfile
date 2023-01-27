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
    autoconf \
    zlib1g \
    libtool \
    r-base
RUN rm -rf /var/lib/apt/lists/*
RUN pip install matplotlib==3.5.1

RUN wget ftp://ftp.mcs.anl.gov/pub/darshan/releases/darshan-3.4.0.tar.gz
RUN tar zxvf darshan-3.4.0.tar.gz
WORKDIR /darshan-3.4.0/
RUN ./prepare.sh

WORKDIR /darshan-3.4.0/darshan-util/
RUN ./configure --enable-pydarshan 
RUN make
RUN make install

WORKDIR /

RUN git clone https://github.com/hpc-io/dxt-explorer-2

WORKDIR /dxt-explorer-2

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install .

ENTRYPOINT ["dxt-explorer"]
