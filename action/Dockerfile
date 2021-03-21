FROM python:3.8-alpine

COPY entrypoint.sh /entrypoint.sh
COPY ../validate_info.py /validate_info.py
COPY ../requirements.txt /requirements.txt

RUN pip install --user --no-cache-dir -r /requirements.txt

# File to execute when the docker container starts up
ENTRYPOINT ["/entrypoint.sh"]