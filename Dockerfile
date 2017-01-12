FROM python:3.5
MAINTAINER Disqus <opensource@disqus.com>

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY requirements requirements
COPY setup.py setup.cfg README.rst ./
COPY fastly_slurper fastly_slurper

RUN set -exv \
 && pip install -e .

ENTRYPOINT ["fastly-slurper"]
