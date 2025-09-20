FROM python:3.12-slim

# نصب ابزارهای مورد نیاز به‌علاوه netcat-openbsd
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    make \
    wget \
    curl \
    build-essential \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

WORKDIR /app

COPY requirements.txt /app/

# نصب پایتون پکیج‌ها
RUN pip install --upgrade pip \
    && pip install --no-cache-dir TA-Lib pandas-ta \
    && pip install --no-cache-dir -r requirements.txt

# کپی کردن entrypoint و دادن اجازه اجرا
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint]()
