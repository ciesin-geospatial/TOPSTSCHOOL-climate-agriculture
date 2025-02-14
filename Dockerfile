# Base image
FROM rocker/binder:latest

ADD . /CLIMATE

# Use root user for installations
USER root


# Install system dependencies for Python and Quarto
RUN apt-get update && apt-get install -y \
    libkrb5-dev \
    build-essential \
    curl \
    pandoc \
    libcurl4-openssl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Quarto CLI
RUN curl -LO https://github.com/quarto-dev/quarto-cli/releases/download/v1.3.340/quarto-1.3.340-linux-amd64.deb \
    && dpkg -i quarto-1.3.340-linux-amd64.deb \
    && rm quarto-1.3.340-linux-amd64.deb

# Install Python packages
RUN pip install --no-cache-dir \
    quarto \
    jupyterlab-quarto \
    geopandas pyproj shapely xarray rioxarray \
    rasterio netcdf4 h5netcdf dask bottleneck nc-time-axis folium \
    numpy pandas matplotlib requests boto3 \
    rasterstats pygadm plotly pygris contextily tabulate \
    scipy pysal splot gssapi arcgis jupyterlab

# Enable JupyterLab extension for Quarto
RUN jupyter labextension enable jupyterlab-quarto

# Start JupyterLab
CMD ["/init"]