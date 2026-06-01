# -*- coding: utf-8 -*-
# pylint: disable=missing-function-docstring

import os
import sys
import tarfile
from os.path import join

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)

from assemble_distro import make_packages_tar_gz


def make_archive(path, source_dir):
    with tarfile.open(path, "w:gz") as tf:
        tf.add(source_dir, arcname=os.path.basename(source_dir))


def tar_modes(path):
    with tarfile.open(path) as tf:
        return {
            member.name.removeprefix("./"): member.mode & 0o7777
            for member in tf.getmembers()
        }


def test_make_packages_tar_gz_normalizes_permissions(monkeypatch, tmpdir):
    os.chdir(str(tmpdir))

    source_dir = join(str(tmpdir), "upstream")
    doc_dir = join(source_dir, "doc")
    os.makedirs(doc_dir)

    files = {
        join(source_dir, "group-writable.txt"): 0o666,
        join(source_dir, "owner-readonly.txt"): 0o444,
        join(source_dir, "run.sh"): 0o700,
    }
    for filename, mode in files.items():
        with open(filename, "w") as f:
            f.write("test\n")
        os.chmod(filename, mode)

    os.chmod(source_dir, 0o777)
    os.chmod(doc_dir, 0o700)

    archive_dir = join(str(tmpdir), "_archives")
    release_dir = join(str(tmpdir), "_releases")
    os.mkdir(archive_dir)
    os.mkdir(release_dir)
    archive_path = join(archive_dir, "modepkg.tar.gz")
    make_archive(archive_path, source_dir)

    monkeypatch.setattr("assemble_distro.download_archive", lambda *_: archive_path)

    make_packages_tar_gz("packages.tar.gz", archive_dir, release_dir, ["modepkg"])

    modes = tar_modes(join(release_dir, "packages.tar.gz"))
    assert modes["modepkg"] == 0o755
    assert modes["modepkg/doc"] == 0o755
    assert modes["modepkg/group-writable.txt"] == 0o644
    assert modes["modepkg/owner-readonly.txt"] == 0o644
    assert modes["modepkg/run.sh"] == 0o755
