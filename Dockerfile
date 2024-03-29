FROM rockylinux:8
LABEL maintainer="tonin@uco.es"

# Install dependencies
RUN rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-rockyofficial && \
    yum -y install bash-completion redhat-lsb-core strace glibc.i686 epel-release &&\
    #yum -y update &&\
	yum -y install python39 &&\
    yum -y install python3-pip python3-requests &&\
    yum -y install glibc-langpack-es &&\
	yum -y install gcc python3-devel &&\
    # Clean cache
    yum -y clean all
#RUN localedef  -c -i es_ES -f UTF-8 es_ES.UTF-8
ENV LANG es_ES.UTF-8
ENV LANGUAGE es_ES.UTF-8
ENV LC_ALL es_ES.UTF-8
COPY requirements.txt /
COPY licenses_exporter.py /
COPY --chmod=777 LinuxBins/lsmon /
COPY --chmod=777 LinuxBins/lmutil /
COPY --chmod=777 LinuxBins/rlmutil /

RUN pip3.9 install -r /requirements.txt

EXPOSE      8000
USER        nobody
ENTRYPOINT ["python3.9", "licenses_exporter.py"]
