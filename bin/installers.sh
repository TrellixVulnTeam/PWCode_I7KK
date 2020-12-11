#!/bin/bash

BINPATH=$(dirname $(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null||echo $0))
PYTHON_BIN=$BINPATH/vendor/linux/python/AppRun
PYTHON_DESKTOP="$(dirname "$BINPATH")"/Python.desktop
SQLWB_DESKTOP="$(dirname "$BINPATH")"/SQLWB.desktop
PIP_DONE=$BINPATH/vendor/linux/python/pip_done
JAVA_BIN=$BINPATH/vendor/linux/jre/bin/java
OJDBC10=$BINPATH/vendor/jars/ojdbc10.jar
JARS=$BINPATH/vendor/jars/sqlworkbench.jar


install_python_runtime() {
    if [ ! -f $PYTHON_BIN ]; then
        wget https://github.com/niess/python-appimage/releases/download/python3.8/python3.8.{9..0}-cp38-cp38-manylinux2014_x86_64.AppImage -O $BINPATH/vendor/linux/python.AppImage
        chmod u+x $BINPATH/vendor/linux/python.AppImage;
        cd $BINPATH/vendor/linux && ./python.AppImage --appimage-extract > /dev/null && cd -;
        rm $BINPATH/vendor/linux/python.AppImage
        mv $BINPATH/vendor/linux/squashfs-root $BINPATH/vendor/linux/python

        if [ ! -f $PYTHON_DESKTOP ]; then
            cp $BINPATH/vendor/config/Python.desktop $PYTHON_DESKTOP
        fi
    fi
}

# TODO: Endre senere så både windows og linux bruker samme versjon av jpype (når bugs fikset der og i jaydebeapi)
install_python_packages() {
    if [ -e $PYTHON_BIN ]; then
        if [ ! -f $PIP_DONE ]; then
            $BINPATH/vendor/linux/python/AppRun -m pip install --no-warn-script-location --force-reinstall JPype1==0.6.3  psutil \
            jaydebeapi toposort flake8 autopep8 rope beautifulsoup4 lxml pygments petl wand ocrmypdf img2pdf pdfy cchardet dulwich filetype
            # TODO: Fjerne wand og img2pdf?
            touch $PIP_DONE
        fi
    fi
}

install_java() {
    if [ ! -f $JAVA_BIN ]; then
        cd $BINPATH/vendor/linux
        wget https://corretto.aws/downloads/latest/amazon-corretto-11-x64-linux-jdk.tar.gz
        tar -xf amazon-corretto-11-x64-linux-jdk.tar.gz
        cd amazon-corretto-*-linux-x64/bin/
        ./jlink --output $BINPATH/vendor/linux/jre --compress=2 --no-header-files --no-man-pages --module-path ../jmods --add-modules java.base,java.datatransfer,java.desktop,java.management,java.net.http,java.security.jgss,java.sql,java.sql.rowset,java.xml,jdk.net,jdk.unsupported,jdk.unsupported.desktop,jdk.xml.dom
        rm $BINPATH/vendor/linux/amazon-corretto-11-x64-linux-jdk.tar.gz
        rm -rdf $BINPATH/vendor/linux/amazon-corretto-*-linux-x64

        if [ ! -f $SQLWB_DESKTOP ]; then
            cp $BINPATH/vendor/config/SQLWB.desktop $SQLWB_DESKTOP
        fi
    fi
}


install_ojdbc() {
    if [ ! -f $OJDBC10 ]; then
        mkdir -p $BINPATH/vendor/jars;
        wget https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc10/19.6.0.0/ojdbc10-19.6.0.0.jar -O $BINPATH/vendor/jars/ojdbc10.jar;
    fi
}


install_jars() {
    if [ ! -f $JARS ]; then
        cd /tmp && wget https://github.com/Preservation-Workbench/deps/releases/latest/download/deps.zip
        cd $BINPATH/vendor/jars && unzip -j /tmp/deps.zip 
    fi
}

main() {
    install_python_runtime;
    install_python_packages;
    install_java;
    install_jars;
    install_ojdbc;
}

if [ "${1}" == "--install" ]; then
    main "${@}"
fi
