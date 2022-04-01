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
LoadPackage("crypting");

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

HexSHA256String := function(str)
    local sha, i;
    sha := List(SHA256String(str), HexStringInt);
    for i in [1..8] do
        while Length(sha[i]) < 8 do
            Add(sha[i], '0', 1);
        od;
    od;
    return LowercaseString(Concatenation(sha));
end;

# This function takes a list of paths to PackageInfo.g files, parses
# each of them, and finally prints everything in JSON format to stdout.
OutputJson := function(pkginfo_paths)
  local fname, pkginfo, pkginfos_list, out;
  pkginfos_list := [];
  for fname in pkginfo_paths do
    pkginfo := PackageInfoRec(fname);
    pkginfo.PackageInfoSHA256 := HexSHA256String(StringFile(fname));
    if IsBound(pkginfo.PackageDoc) and not IsList(pkginfo.PackageDoc) then
      pkginfo.PackageDoc := [pkginfo.PackageDoc];
    fi;
    Add(pkginfos_list, pkginfo);
  od;
  out := OutputTextUser();
  SetPrintFormattingStatus(out, false);
  PrintTo(out, GapToJsonString(pkginfos_list));
  CloseStream(out);
end;
