FROM ubuntu:20.04

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    curl \
    unzip \
    vim \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/kalkan_sdk

COPY . .

ENV LD_LIBRARY_PATH="/opt/kalkan_sdk/Linux/C:$LD_LIBRARY_PATH"

CMD ["/bin/bash"]
