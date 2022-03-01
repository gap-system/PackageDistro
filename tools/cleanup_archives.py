#!/usr/bin/env python3

#############################################################################
##
##  This file is part of GAP, a system for computational discrete algebra.
##
##  Copyright of GAP belongs to its developers, whose names are too numerous
##  to list here. Please refer to the COPYRIGHT file for details.
##
##  SPDX-License-Identifier: GPL-2.0-or-later
##
import os
from utils import all_packages, archive_name

# remove unused files from _archives
def cleanup_archives():
    archive_dir = "_archives"
    pkgs = all_packages()
    needed_archives = set([archive_name(p) for p in pkgs])
    all_archives = set(os.listdir(archive_dir))
    for fname in all_archives - needed_archives:
        path = os.path.join(archive_dir, fname)
        print("removing", path)
        os.remove(path)

if __name__ == "__main__":
    cleanup_archives()
