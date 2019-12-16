# Welcome to the Elastic APM Server 6.8.5

Elastic APM Server

## Getting Started

To get started with APM Server, you need to set up Elasticsearch on your
localhost first. After that, start APM Server with:

     ./apm-server -c apm-server.yml -e

This will start APM Server and send the data to your Elasticsearch instance. To
load the dashboards for APM Server into Kibana, run:

    ./apm-server setup -e

For further steps visit the
[Getting started](https://www.elastic.co/guide/en/apm/get-started/6.8/) guide.

## Documentation

Visit [Elastic.co Docs](https://www.elastic.co/guide/en/apm/server/6.8/)
for the full apm-server documentation.
