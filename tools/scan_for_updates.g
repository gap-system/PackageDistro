#############################################################################
##
##  This file is part of GAP, a system for computational discrete algebra.
##
##  Copyright of GAP belongs to its developers, whose names are too numerous
##  to list here. Please refer to the COPYRIGHT file for details.
##
##  SPDX-License-Identifier: GPL-2.0-or-later
##

LoadPackage("json");

InstallMethod(RecNames, [IsRecord and IsInternalRep], x -> AsSSortedList(REC_NAMES(x)));

PackageInfoRec := function(pkginfo_file)
    Unbind(GAPInfo.PackageInfoCurrent);
    Read(pkginfo_file);
    if not IsBound(GAPInfo.PackageInfoCurrent) then
      Error(StringFormatted("reading {} failed", pkginfo_file));
    fi;
    return GAPInfo.PackageInfoCurrent;
end;

InstallMethod(_GapToJsonStreamInternal,
[IsOutputStream, IsObject],
function(o, x)
    PrintTo(o, "null");
end);

OutputJson := function(updated_pkgs, pkginfos_dir)
  local pkginfo, pkginfo_rec, pkgname, json_fname;

  if not IsString(pkginfos_dir) or not IsDirectoryPath(pkginfos_dir) then
    Error(StringFormatted("the directory {} does not exist", pkginfos_dir));
  fi;

  pkginfos_dir := Directory(pkginfos_dir);

  for pkgname in updated_pkgs do
    pkginfo := Filename(pkginfos_dir, Concatenation(pkgname, ".g"));
    pkginfo_rec := PackageInfoRec(pkginfo);
    Assert(0, pkgname = LowercaseString(pkginfo_rec.PackageName));
    json_fname := Concatenation("packages/", pkgname, "/meta.json");
    if not IsExistingFile(json_fname) then
      PrintFormatted("{1} does not exist, skipping!\n", json_fname);
      continue;
    fi;
    PrintFormatted("updating {}\n", json_fname);
    if IsBound(pkginfo_rec.PackageDoc) and not IsList(pkginfo_rec.PackageDoc) then
      pkginfo_rec.PackageDoc := [pkginfo_rec.PackageDoc];
    fi;
    FileString(json_fname, GapToJsonString(pkginfo_rec));
  od;
end;
