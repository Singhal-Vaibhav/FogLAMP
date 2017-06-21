FROM python:3.5

ADD . /Foglamp
WORKDIR /Foglamp/src/python
VOLUME /Foglamp/src/python

RUN pip install --no-cache-dir -r requirements_dev.txt
RUN pip install -e .
CMD ["python", "foglamp_start.py"]
# RUN foglampd
EXPOSE 8080
