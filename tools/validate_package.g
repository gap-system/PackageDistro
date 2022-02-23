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

ValidatePackagesArchive := function(unpacked_dir, pkgnames)

  unpacked_dir := Directory(unpacked_dir);
  for pkgname in pkgnames do
      archive_dir := Directory(Filename(unpacked_dir, pkgname));
      pkginfo_file := Filename(
      if not ValidatePackageInfo(pkginfo_dir_file) then
        Print(StringFormatted("{}: ValidatePackageInfo(\"{}\"); failed, skipping!\n",
                              pkgname,
                              pkginfo_file));
        continue;
      fi;
      # TODO should be meta.json
      json_file := Concatenation(pkgname, "/", pkgname, ".json");
      json := JsonStringToGap(StringFile(json_file));
      if not CompareVersionNumbers(pkginfo_record.Version, json.Version) then
        Print(StringFormatted("{}: release version is {}, but last release was {}, skipping!\n",
                              pkgname,
                              pkginfo_record.Version,
                              json.Version));
        continue;
      fi;
      if EndsWith(LowercaseString(pkginfo_record.Version), "dev") then
        Print(StringFormatted("{}: invalid release version {}, skipping!\n",
                              pkgname,
                              pkginfo_record.Version));
        continue;
      fi;
      if not ComparePkgInfoDates(json.Date, pkginfo_record.Date) then
        Print(StringFormatted("{}: release date is {}, but last release date was {}, skipping!\n",
                              pkgname,
                              pkginfo_record.Date,
                              json.Date));
        continue;
      fi;

      WriteJson(pkginfo_record);
    fi;
  od;
end;
