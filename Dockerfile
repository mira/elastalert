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

ENV PYTHONPATH /elastalert
ENV ELASTALERT_INDEX elastalert
WORKDIR $PYTHONPATH
 
RUN python2.7 create_index.py --index $ELASTALERT_INDEX --old-index ''

ADD files /files

ENTRYPOINT /files/generate_config.sh && cat $CONFIG_PATH
ENTRYPOINT /files/generate_config.sh && python2.7 elastalert.py --verbose
