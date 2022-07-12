# set base image (host OS)
FROM python:3.8

# allow Google API to utilize downloaded credentials
ENV GOOGLE_APPLICATION_CREDENTIALS credentials.json

# set the working directory in the container
WORKDIR /code

# copy the dependencies file to the working directory
COPY requirements.txt .

# copy the gerrit cookies file to the working directory
COPY gerritcookies .

# copy the gcloud credentials file to the working directory
COPY credentials.json .

# install dependencies
RUN pip3 install -r requirements.txt

# copy the content of the local src directory to the working directory
COPY src/ ./

# command to run on container start
CMD [ "bash", "-c", "python3 ./main.py --stderrthreshold=info 2>&1" ]
