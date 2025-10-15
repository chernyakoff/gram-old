FROM minio/minio:latest

COPY init_minio.sh /usr/local/bin/init_minio.sh

RUN chmod +x /usr/local/bin/init_minio.sh

ENTRYPOINT ["/usr/local/bin/init_minio.sh"]
CMD ["server", "/data", "--console-address", ":9001"]