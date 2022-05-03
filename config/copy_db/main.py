import shutil
import os
import sys
from common.xml_settings import XMLSettings

if os.name != "posix":
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def main():
    from defs import (  # .defs.py
        export_db_schema,
        test_db_connect,
        Connection
    )

    bin_dir = os.environ["pwcode_bin_dir"]  # Get PWCode executable path
    java_path = os.environ['pwcode_java_path']  # Get Java home path
    class_path = os.environ['CLASSPATH']  # Get jar path
    config_dir = os.environ['pwcode_config_dir']  # Get PWCode config path
    tmp_dir = os.path.join(config_dir, 'tmp')
    os.chdir(tmp_dir)  # Avoid littering from subprocesses
    data_dir = os.environ['pwcode_data_dir']
    tmp_config_path = os.path.join(config_dir, 'tmp', 'pwcode.xml')
    tmp_config = XMLSettings(tmp_config_path)

    if not os.path.isfile(tmp_config_path):
        return 'No config file found. Exiting.'

    project_name = tmp_config.get('name')
    project_dir = os.path.join(data_dir, project_name)

    if not os.path.isdir(project_dir):
        return 'No project folder found. Exiting.'

    archive = os.path.join(project_dir, project_name + '.tar')
    if os.path.isfile(archive):
        return "'" + archive + "' already exists. Exiting."

    config_path = os.path.join(project_dir, 'pwcode.xml')
    if not os.path.isfile(config_path):
        shutil.copyfile(tmp_config_path, config_path)

    config = XMLSettings(config_path)
    memory = '-Xmx' + config.get('options/memory').split(' ')[0] + 'g'
    ddl = config.get('options/ddl')

    source = Connection(config.get('source' + '/name'),
                        config.get('source' + '/schema_name'),
                        config.get('source' + '/jdbc_url'),
                        config.get('source' + '/user'),
                        config.get('source' + '/password')
                        )

    source_db_check = test_db_connect(source,
                                      bin_dir,
                                      class_path,
                                      java_path,
                                      memory,
                                      None,
                                      None,
                                      None)

    if not source_db_check == 'ok':
        return source_db_check

    target = Connection(config.get('target' + '/name'),
                        config.get('target' + '/schema_name'),
                        config.get('target' + '/jdbc_url'),
                        config.get('target' + '/user'),
                        config.get('target' + '/password')
                        )

    target_db_check = test_db_connect(target,
                                      bin_dir,
                                      class_path,
                                      java_path,
                                      memory,
                                      None,
                                      None,
                                      None,
                                      True
                                      )

    if not target_db_check == 'ok':
        return target_db_check

    db_result = export_db_schema(
        source,
        target,
        bin_dir,
        class_path,
        java_path,
        memory,
        project_dir,
        None,
        None,
        None,
        ddl
    )

    return db_result


if __name__ == '__main__':
    msg = main()
    print(msg)
    print('\n')  # WAIT: For flushing last print in def. Better fix later
