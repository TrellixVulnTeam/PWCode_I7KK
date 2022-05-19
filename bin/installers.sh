#!/bin/bash

SCRIPTPATH=$(dirname $(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null||echo $0))
PYTHON_BIN=$SCRIPTPATH/vendor/linux/python/AppRun
PYTHON_DESKTOP="$(dirname "$SCRIPTPATH")"/Python.desktop
SQLWB_DESKTOP="$(dirname "$SCRIPTPATH")"/SQLWB.desktop
PIP_DONE=$SCRIPTPATH/vendor/linux/python/pip_done
JAVA_BIN=$SCRIPTPATH/vendor/linux/jre/bin/java
OJDBC10=$SCRIPTPATH/vendor/jars/ojdbc10.jar
JARS=$SCRIPTPATH/vendor/jars/sqlworkbench.jar
CONVERTER=$(dirname $SCRIPTPATH)/config/scripts/PWConvert/convert.py

install_python_runtime() {
    if [ ! -f $PYTHON_BIN ]; then
        wget https://github.com/niess/python-appimage/releases/download/python3.8/python3.8.{20..10}-cp38-cp38-manylinux2014_x86_64.AppImage -O $SCRIPTPATH/vendor/linux/python.AppImage
        chmod u+x $SCRIPTPATH/vendor/linux/python.AppImage;
        cd $SCRIPTPATH/vendor/linux && ./python.AppImage --appimage-extract > /dev/null && cd -;
        rm $SCRIPTPATH/vendor/linux/python.AppImage
        mv $SCRIPTPATH/vendor/linux/squashfs-root $SCRIPTPATH/vendor/linux/python

        if [ ! -f $PYTHON_DESKTOP ]; then
            cp $SCRIPTPATH/vendor/config/Python.desktop $PYTHON_DESKTOP
        fi
    fi
}

# WAIT: Endre så mindre blir installert når ikke installert på PWLinux?
install_python_packages() {
    if [ -e $PYTHON_BIN ]; then
        if [ ! -f $PIP_DONE ]; then
            $SCRIPTPATH/vendor/linux/python/AppRun -m pip install --no-warn-script-location -U  JayDeBeApi JPype1 blake3 \
            psutil toposort flake8 autopep8 rope beautifulsoup4 lxml pygments petl wand ocrmypdf img2pdf pdfy cchardet dulwich filetype
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
        ./jlink --output $SCRIPTPATH/vendor/linux/jre --compress=2 --no-header-files --no-man-pages --module-path ../jmods --add-modules java.base,java.datatransfer,java.desktop,java.management,java.net.http,java.security.jgss,java.sql,java.sql.rowset,java.xml,jdk.net,jdk.unsupported,jdk.unsupported.desktop,jdk.xml.dom,jdk.zipfs
        rm $SCRIPTPATH/vendor/linux/amazon-corretto-11-x64-linux-jdk.tar.gz
        rm -rdf $SCRIPTPATH/vendor/linux/amazon-corretto-*-linux-x64

        if [ ! -f $SQLWB_DESKTOP ]; then
            cp $SCRIPTPATH/vendor/config/SQLWB.desktop $SQLWB_DESKTOP
        fi
    fi
}

install_ojdbc() {
    if [ ! -f $OJDBC10 ]; then
        wget https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc10/19.6.0.0/ojdbc10-19.6.0.0.jar -O $SCRIPTPATH/vendor/jars/ojdbc10.jar;
    fi
}

install_jars() {
    if [ ! -f $JARS ]; then
        wget https://github.com/Preservation-Workbench/deps/releases/latest/download/deps.zip -O /tmp/deps.zip;
        cd $SCRIPTPATH/vendor/jars && unzip -j /tmp/deps.zip;
    fi
}

install_converter() {
    if [ ! -f $CONVERTER ]; then
        REPOSRC="https://github.com/Preservation-Workbench/PWConvert.git"
        LOCALREPO=$(dirname $CONVERTER)
        # LOCALREPO="/home/pwb/bin/PWCode/config/scripts/PWConvert/"
        # # echo "test"
        git clone --depth 1 "$REPOSRC" "$LOCALREPO" 2> /dev/null || git -C "$LOCALREPO" pull;
    fi
}

main() {
    install_python_runtime;
    install_python_packages;
    install_java;
    install_jars;
    install_ojdbc;
    install_converter;
}

if [ "${1}" == "--install" ]; then
    main "${@}"
fi
