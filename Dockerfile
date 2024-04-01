FROM python:3.10.13
LABEL authors=""

RUN apt update
RUN apt install -y nodejs=18.19.0+dfsg-6~deb12u1
RUN apt install -y npm

ADD ./requirements.txt ./requirements.txt

RUN pip install pip -U
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install -r requirements.txt

ADD ./js_setup.py ./js_setup.py

RUN python js_setup.py

RUN mkdir /VILLAGER/
ADD . /VILLAGER/

WORKDIR /VILLAGER/

ENTRYPOINT python run.py