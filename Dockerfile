from docker.io/manjarolinux/base
run pacman --noconfirm -Syu git python python-pip python-aiohttp
RUN mkdir /bot
RUN mkdir /bot/source
RUN mkdir /data
COPY source/* /bot/source/
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python3 -m venv --system-site-packages /opt/venv
RUN pip3 install -r /bot/source/requirements.txt
RUN pip3 install git+https://github.com/ranaroussi/yfinance.git@dev
WORKDIR /data/
CMD ["python3","/bot/source/bot.py"]