FROM centos:7
LABEL maintainer="tonin@uco.es"

# Install dependencies
RUN rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7 && \
    yum -y install bash-completion redhat-lsb-core strace glibc.i686 epel-release &&\
    #yum -y update &&\
    yum -y install python3-pip pythoni3-requests &&\
    #yum -y install locales &&\
	yum -y install gcc python3-devel &&\
    # Clean cache
    yum -y clean all
RUN localedef  -c -i es_ES -f UTF-8 es_ES.UTF-8
ENV LANG es_ES.UTF-8
ENV LANGUAGE es_ES.UTF-8
ENV LC_ALL es_ES.UTF-8
COPY requirements.txt /
COPY licenses_exporter.py /
COPY --chmod=777 LinuxBins/lsmon /
COPY --chmod=777 LinuxBins/lmutil /
COPY --chmod=777 LinuxBins/rlmutil /

RUN pip3 install -r /requirements.txt

EXPOSE      8000
USER        nobody
ENTRYPOINT ["python3", "licenses_exporter.py"]
