#!/bin/bash

SCRIPTPATH=$(dirname $(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null||echo $0))
PYTHON_BIN=$SCRIPTPATH/vendor/linux/python/AppRun
PYTHON_DESKTOP="$(dirname "$SCRIPTPATH")"/Python.desktop
SQLWB_DESKTOP="$(dirname "$SCRIPTPATH")"/SQLWB.desktop
PIP_DONE=$SCRIPTPATH/vendor/linux/python/pip_done
JAVA_BIN=$SCRIPTPATH/vendor/linux/jre/bin/java
OJDBC10=$SCRIPTPATH/vendor/jars/ojdbc10.jar
JARS=$SCRIPTPATH/vendor/jars/sqlworkbench.jar


install_python_runtime() {
    if [ ! -f $PYTHON_BIN ]; then
        cd $SCRIPTPATH/vendor/linux
        wget https://github.com/niess/python-appimage/releases/download/python3.8/python3.8.{9..0}-cp38-cp38-manylinux2014_x86_64.AppImage -O python.AppImage
        chmod u+x python.AppImage;
        ./python.AppImage --appimage-extract > /dev/null
        rm python.AppImage
        mv squashfs-root python

        if [ ! -f $PYTHON_DESKTOP ]; then
            cp $SCRIPTPATH/vendor/config/Python.desktop $PYTHON_DESKTOP
        fi
    fi
}

# TODO: Endre senere så både windows og linux bruker samme versjon av jpype (når bugs fikset der og i jaydebeapi)
install_python_packages() {
    if [ -e $PYTHON_BIN ]; then
        if [ ! -f $PIP_DONE ]; then
            cd $SCRIPTPATH/vendor/linux/python
            ./AppRun -m pip install --no-warn-script-location --force-reinstall JPype1==0.6.3  psutil jaydebeapi toposort flake8 autopep8 rope beautifulsoup4 lxml pygments petl wand ocrmypdf img2pdf pdfy cchardet dulwich filetype
            # TODO: Fjerne wand og img2pdf?
            touch $PIP_DONE
        fi
    fi
}

install_java() {
    if [ ! -f $JAVA_BIN ]; then
        cd $SCRIPTPATH/vendor/linux
        wget https://corretto.aws/downloads/latest/amazon-corretto-11-x64-linux-jdk.tar.gz
        tar -xf amazon-corretto-11-x64-linux-jdk.tar.gz
        cd amazon-corretto-*-linux-x64/bin/
        ./jlink --output $SCRIPTPATH/vendor/linux/jre --compress=2 --no-header-files --no-man-pages --module-path ../jmods --add-modules java.base,java.datatransfer,java.desktop,java.management,java.net.http,java.security.jgss,java.sql,java.sql.rowset,java.xml,jdk.net,jdk.unsupported,jdk.unsupported.desktop,jdk.xml.dom
        rm $SCRIPTPATH/vendor/linux/amazon-corretto-11-x64-linux-jdk.tar.gz
        rm -rdf $SCRIPTPATH/vendor/linux/amazon-corretto-*-linux-x64

        if [ ! -f $SQLWB_DESKTOP ]; then
            cp $SCRIPTPATH/vendor/config/SQLWB.desktop $SQLWB_DESKTOP
        fi
    fi
}


install_ojdbc() {
    if [ ! -f $OJDBC10 ]; then
        cd $SCRIPTPATH/vendor/jars
        wget https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc10/19.6.0.0/ojdbc10-19.6.0.0.jar -O ojdbc10.jar
    fi
}


install_jars() {
    if [ ! -f $JARS ]; then
        cd /tmp && wget https://github.com/Preservation-Workbench/deps/releases/latest/download/deps.zip
        cd $SCRIPTPATH/vendor/jars && unzip -j /tmp/deps.zip 
    fi
}











