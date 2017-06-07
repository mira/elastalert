FROM miraco/python:2.7.13

RUN apt-get install -y curl

WORKDIR /

ADD requirements.txt requirements.txt
ADD setup.py setup.py

RUN python2.7 -m pip install -r requirements.txt
RUN python2.7 setup.py install

ADD elastalert elastalert
WORKDIR /elastalert
ENV CONFIG_PATH /elastalert/config.yaml
RUN elastalert-create-index &2> /dev/null

ENV PYTHONPATH /elastalert
WORKDIR $PYTHONPATH

ADD files /files

ENTRYPOINT /files/generate_config.sh && cat $CONFIG_PATH
ENTRYPOINT /files/generate_config.sh && python2.7 elastalert.py --verbose
