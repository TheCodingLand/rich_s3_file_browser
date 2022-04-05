FROM python:3.9.12-alpine3.15
COPY main.py main.py
CMD ["python" ,"main.py"]