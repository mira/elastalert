FROM miraco/python:2.7.13

WORKDIR /

ADD requirements.txt requirements.txt
ADD setup.py setup.py

RUN python2.7 -m pip install -r requirements.txt
RUN python2.7 setup.py install

ADD elastalert elastalert
WORKDIR /elastalert
ENV CONFIG_PATH /elastalert/config.yaml

ENV PYTHONPATH /elastalert
ENV ES_INDEX elastalert
WORKDIR $PYTHONPATH
 
ADD files /files

ENTRYPOINT /files/generate_config.sh && python2.7 create_index.py --index $ES_INDEX --old-index '' && python2.7 elastalert.py --verbose
