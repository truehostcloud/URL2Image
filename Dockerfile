FROM python:latest

RUN mkdir /app/tmp_images

RUN pip install -r /app/requirements.txt

COPY url2_image /app/url2_image
COPY ./start.sh /app/
COPY ./configs/gunicorn/gunicorn.conf.py /etc/
COPY ./wsgi.py /app/
COPY ./.git-commit /app/
COPY ./.git-branch /app/
COPY ./tests/ /app/tests/
COPY ./pytest.ini /app/
WORKDIR /app
EXPOSE 5000

ARG GIT_COMMIT=unspecified
LABEL git_commit=$GIT_COMMIT
ENV COMMIT_SHA=${GIT_COMMIT}

CMD ["/app/start.sh"]

