FROM ubuntu

RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y \
    python3 \
    pip \
    make \
    git \
    wget \
    libssl-dev \
    libcurl4-openssl-dev \
    autoconf \
    zlib1g \
    libtool
RUN rm -rf /var/lib/apt/lists/*
RUN pip install matplotlib==3.5.1

RUN wget ftp://ftp.mcs.anl.gov/pub/darshan/releases/darshan-3.4.2.tar.gz
RUN tar zxvf darshan-3.4.2.tar.gz
WORKDIR /darshan-3.4.2/
RUN ./prepare.sh

WORKDIR /darshan-3.4.2/darshan-util/
RUN ./configure --enable-pydarshan --enable-shared
RUN make
RUN make install

WORKDIR /

RUN git clone https://github.com/hpc-io/dxt-explorer
RUN cd dxt-explorer && git checkout pre-release
WORKDIR /dxt-explorer

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install .

RUN echo "/usr/local/lib/" > /etc/ld.so.conf.d/libdarshan.conf
RUN ldconfig

ENTRYPOINT ["dxt-explorer"]