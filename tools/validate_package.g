LoadPackage("json");

InstallMethod(RecNames, [IsRecord and IsInternalRep], x -> AsSSortedList(REC_NAMES(x)));

PackageInfoRec := function(pkginfo_file)
    Unbind(GAPInfo.PackageInfoCurrent);
    Read(pkginfo_file);
    if not IsBound(GAPInfo.PackageInfoCurrent) then
      # TODO better error message
      Error("reading PackageInfo.g failed");
    fi;
    return GAPInfo.PackageInfoCurrent;
end;

# The format checks are the ones from the local 'CheckDateValidity' function
# of 'ValidatePackageInfo'.
NormalizePkgDate := function(x)
  local date;
  if not (IsString(x) and Length(x) = 10
    and (ForAll(x{[1, 2, 4, 5, 7, 8, 9, 10]}, IsDigitChar)
    and x{[ 3, 6 ]} = "//"
    or ForAll(x{[1, 2, 3, 4, 6, 7, 9, 10]}, IsDigitChar)
       and x{[5, 8]} = "--")) then
      return false;
  elif x{[ 3, 6 ]} = "//" then
      date := List( SplitString( x, "/" ), Int );
  elif x{[ 5, 8 ]} = "--" then
      date := List( SplitString( x, "-" ), Int );
      date := date{[ 3, 2, 1 ]};
  fi;
  if not (date[2] in [1 .. 12] and date[3] >= 1999 and date[1] in [1 ..
    DaysInMonth(date[2], date[3])]) then
    return fail;
  fi;
  return date;
end;

ComparePkgInfoDates := function(pkg1, pkg2)
  # TODO check for fails
  return DayDMY(NormalizePkgDate(pkg1)) <= DayDMY(NormalizePkgDate(pkg2));
end;

# For each package name <nam> in <pkgnames>, ASSUME that
# - <unpacked_dir> is a directory path having a subdirectory <nam>
#   that contains the files of the package,
# - the current directory contains files <nam>/meta.json and <nam>/meta.json.old,
# - <unpacked_dir>/<nam>/PackageInfo.g has the checksum stored in
#   PackageInfoSha256 of <nam>/meta.json (this is checked easier outside GAP)
#   [Note that the stored PackageInfoSha256 was derived from the downloaded
#   PackageInfo.g file, which might differ from the PackageInfo.g in the
#   archive.],
# and CHECK that
# - calling 'ValidatePackageInfo' for <unpacked_dir>/<nam>/PackageInfo.g
#   returns 'true',
# - the package at <unpacked_dir>/<nam> is not a dev version
#   (according to its version number),
# - the version number in <nam>/meta.json is *strictly larger than*
#   the version number in <nam>/meta.json.old,
# - the release date in <nam>/meta.json is *at least* the release date
#   in <nam>/meta.json.old.

ValidatePackagesArchive := function(unpacked_dir, pkgnames)
  local meta_dir, pkgname, archive_dir, pkginfo_file,
        json_file, json_file_old, pkginfo_record, json, json_old;

  unpacked_dir := Directory(unpacked_dir);
  meta_dir:= DirectoryCurrent();
  for pkgname in pkgnames do
      archive_dir := Directory(Filename(unpacked_dir, pkgname));
      pkginfo_file := Filename(archive_dir, "PackageInfo.g");

      # We call 'ValidatePackageInfo' with the filename not with the record,
      # because then the validity of some filenames
      # relative to the package directory can be checked.
      if not ValidatePackageInfo(pkginfo_file) then
        PrintFormatted("{}: ValidatePackageInfo(\"{}\"); failed, skipping!\n",
                              pkgname,
                              pkginfo_file));
        continue;
      fi;

      json_file := Concatenation(pkgname, "/meta.json");
      json_file_old := Concatenation(pkgname, "/meta.json.old");

      pkginfo_record:= PackageInfoRec(pkginfo_file);

      json := JsonStringToGap(StringFile(Filename(meta_dir, json_file)));
      json_old := JsonStringToGap(StringFile(Filename(meta_dir, json_file_old)));
      if CompareVersionNumbers(json_old.Version, json.Version) then
        PrintFormatted("{}: current release version is {}, but previous release version was {}, skipping!\n",
                              pkgname,
                              json.Version,
                              json_old.Version));
        continue;
      fi;

      if EndsWith(LowercaseString(pkginfo_record.Version), "dev") then
        PrintFormatted("{}: invalid release version {}, skipping!\n",
                              pkgname,
                              pkginfo_record.Version));
        continue;
      fi;

      if not ComparePkgInfoDates(json_old.Date, pkginfo_record.Date) then
        PrintFormatted("{}: current release date is {}, but previous release date was {}, skipping!\n",
                              pkgname,
                              pkginfo_record.Date,
                              json_old.Date));
        continue;
      fi;
  od;
end;
