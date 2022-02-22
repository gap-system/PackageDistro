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
      # TODO better error message
      Error(StringFormatted("reading {} failed", pkginfo_file));
    fi;
    return GAPInfo.PackageInfoCurrent;
end;

InstallMethod(_GapToJsonStreamInternal,
[IsOutputStream, IsObject],
function(o, x)
    PrintTo(o, "null");
end);

WriteJson := function(json_dir, pkginfo_record)
  local json_fname, root;
  # TODO is the following necessary?
  # Remove the GAPROOT prefix from the package installation path
  if IsBound(pkginfo_record.InstallationPath) then
    for root in GAPInfo.RootPaths do
      pkginfo_record.InstallationPath :=
        ReplacedString(pkginfo_record.InstallationPath, root, "");
    od;
  fi;
  Print(json_dir, "\n");
  Print(pkginfo_record.PackageName, "\n");
  json_fname := Concatenation(json_dir![1],
                              LowercaseString(pkginfo_record.PackageName),
                              ".json");
  FileString(json_fname, GapToJsonString(pkginfo_record));
end;

OutputJson := function(pkginfos_dir, json_dir)
  local pkginfo;

  # TODO arg checks
  if not IsDirectoryPath(json_dir) then
    Exec(Concatenation("mkdir ", json_dir));
    Assert(0, IsDirectoryPath(json_dir));
  fi;

  pkginfos_dir := Directory(pkginfos_dir);
  json_dir     := Directory(json_dir);
  for pkginfo in DirectoryContents(pkginfos_dir) do
    if not StartsWith(pkginfo, ".") then
      pkginfo := Filename(pkginfos_dir, pkginfo);
      WriteJson(json_dir, PackageInfoRec(pkginfo));
    fi;
  od;
end;
