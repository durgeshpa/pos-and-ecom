# Use an official Python runtime as a parent image
FROM python:3.6

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

#Install dependencies for uWSGI
RUN set -ex \
    && buildDeps=' \
        gcc \
        libbz2-dev \
        libc6-dev \
        libgdbm-dev \
        liblzma-dev \
        libncurses-dev \
        libreadline-dev \
        libsqlite3-dev \
        libssl-dev \
        libpcre3-dev \
        make \
        tcl-dev \
        tk-dev \
        wget \
        xz-utils \
        zlib1g-dev \
    ' \
    && deps=' \
        libexpat1 \
    ' \
    && apt-get update && apt-get install -y $buildDeps $deps --no-install-recommends  && rm -rf /var/lib/apt/lists/* \
    && pip install uwsgi \
    && apt-get purge -y --auto-remove $buildDeps \
    && find /usr/local -depth \
    \( \
        \( -type d -a -name test -o -name tests \) \
        -o \
        \( -type f -a -name '*.pyc' -o -name '*.pyo' \) \
    \) -exec rm -rf '{}' +


# Install any needed packages specified in requirements.txt
RUN apt-get update
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80
EXPOSE 8000

# Define environment variable
ENV NAME World
ENV SECRET_KEY $eo=@a@w)ad!1wvvy&74%ig^h2($-uv&wdqkhp!&l!++!s8ztl
ENV DEBUG True
ENV ALLOWED_HOSTS [127.0.0.1,localhost,dev.gramfactory.com,0.0.0.0]
#DB_NAME=gf_db_2
ENV DB_NAME nripesh_db
ENV DB_USER dev_nripesh
ENV DB_PASSWORD nripesh@123
ENV DB_HOST postgres2.c8f3lvoda0ke.ap-south-1.rds.amazonaws.com
ENV DB_HOST_READ livedb-read-replica.c8f3lvoda0ke.ap-south-1.rds.amazonaws.com
ENV SMS_AUTH_KEY kjgfsr536re79wfduhgvcf5r4fesfc3425gttrf
ENV DB_PORT 5432
ENV ENVIRONMENT local

ENV AWS_ACCESS_KEY_ID 'AKIAIJQKI6M5JSFTHMYQ'
ENV AWS_SECRET_ACCESS_KEY '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'
ENV AWS_STORAGE_BUCKET_NAME 'gramfactorymedia'
ENV BLOCKING_TIME_IN_MINUTS 1

# Run app.py when the container launches
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
