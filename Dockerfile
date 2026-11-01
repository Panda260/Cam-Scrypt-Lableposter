FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
# pip wird nur zum Bauen gebraucht; danach entfernen, damit seine
# mitgelieferten Pakete (msgpack, urllib3, setuptools) nicht im Image bleiben.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip \
    && rm -rf /usr/local/lib/python3*/ensurepip

COPY main.py .
COPY cam.png .

CMD ["python", "-u", "main.py"]
