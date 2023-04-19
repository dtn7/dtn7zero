"""
The script must be run on the esp32 and deletes all files in the filesystem on it.

This was used as I once corrupted one esp32s filesystem and could not get the files removed with an external tool (mpremote).

May it be also useful for somebody else in the future.
"""

import os
import sys

if not sys.implementation.name == 'micropython':
    raise Exception("Call this script on the microcontroller directly! (mpremote run scripts/clear-device-filesystem.py)")


def gather_files_and_directories(root=''):
    files = []
    directories = []
    # iterate over all files and directories in root. node-tuple size is system dependend: name, type, inode, (size)
    for node in os.ilistdir(root):
        name = node[0]
        node_type = node[1]

        path = '{}/{}'.format(root, name)

        if node_type == 0x4000:
            # recursively gather files from directories
            print('found directory: {}'.format(path))
            directories.append(path)
            sub_files, sub_directories = gather_files_and_directories(path)
            files += sub_files
            directories += sub_directories
        elif node_type == 0x8000:
            # add files
            print('found file: {}'.format(path))
            files.append(path)
        else:
            raise Exception('{} has unknown filesystem type {}'.format(path, node_type))

    return files, directories


file_paths, dir_paths = gather_files_and_directories('lib')

for p in file_paths:
    print('removing file: {}'.format(p))
    os.remove(p)

for p in dir_paths[::-1]:
    print('removing directory: {}'.format(p))
    os.remove(p)
