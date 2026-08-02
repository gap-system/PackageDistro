#############################################################################
##
##  This file is part of GAP, a system for computational discrete algebra.
##
##  Copyright of GAP belongs to its developers, whose names are too numerous
##  to list here. Please refer to the COPYRIGHT file for details.
##
##  SPDX-License-Identifier: GPL-2.0-or-later
##
##  While reading a file, GAP reports problems such as a reference to an
##  unbound global variable as a "Syntax warning", but then carries on. Thus
##  loading a package with such a problem still succeeds and none of our tests
##  notices, even though the message looks alarming to users and almost always
##  indicates a genuine mistake in the package. The code below loads a package
##  and turns any such message about one of the package's own files into a
##  failure, so that we can report the problem upstream.
##

# Load the package <pkgname> and report all syntax errors and warnings GAP
# printed for files belonging to that package. Returns `true` if there were
# none, and `false` otherwise.
#
# Options are passed on to `LoadPackage`, so that
#     LoadPackageAndCheckSyntax("lpres" : OnlyNeeded);
# does the same as `LoadPackage("lpres" : OnlyNeeded);` plus the extra check.
LoadPackageAndCheckSyntax := function(pkgname)
  local out, stream, paths, lines, problems, formatting, i, line;

  out := "";
  stream := OutputTextString(out, true);
  # `OutputLogTo` logs rather than redirects, so the output still shows up in
  # the CI log as usual. It also covers the syntax messages, even though GAP
  # prints those to stderr.
  OutputLogTo(stream);
  LoadPackage(pkgname);
  OutputLogTo();
  CloseStream(stream);

  # What is logged is the output as it appeared on the screen, i.e. broken
  # into lines of screen width, with a backslash marking each break. Undo
  # that, as it can tear a file name apart.
  out := ReplacedString(out, "\\\n", "");

  # Only complain about the package's own files: problems in files of its
  # dependencies are found and reported when those packages are tested.
  paths := [];
  if IsBound(GAPInfo.PackagesInfo.(LowercaseString(pkgname))) then
    paths := List(GAPInfo.PackagesInfo.(LowercaseString(pkgname)),
                  info -> info.InstallationPath);
  fi;

  # Such a message consists of a line naming the problem and the file it
  # occurred in, followed by the offending source line and a marker line.
  problems := [];
  lines := SplitString(out, "", "\n");
  for i in [1 .. Length(lines)] do
    line := lines[i];
    if (StartsWith(line, "Syntax error:") or StartsWith(line, "Syntax warning:"))
       and ForAny(paths, path -> PositionSublist(line, path) <> fail) then
      Append(problems, lines{[i .. Minimum(i + 2, Length(lines))]});
    fi;
  od;

  if IsEmpty(problems) then
    return true;
  fi;

  # Report the problems, with line breaking turned off so that GAP does not
  # tear the file names apart again.
  formatting := PrintFormattingStatus("*stdout*");
  SetPrintFormattingStatus("*stdout*", false);
  Print("::error::Syntax errors or warnings occurred while loading ",
        pkgname, "\n");
  for line in problems do
    Print(line, "\n");
  od;
  SetPrintFormattingStatus("*stdout*", formatting);

  return false;
end;
