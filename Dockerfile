FROM apache/airflow:2.9.2

USER root

RUN apt-get update && apt-get install -y curl apt-transport-https gnupg2 unixodbc-dev
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl -fsSL https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18

USER airflow

RUN pip install pandas sqlalchemy pyodbc