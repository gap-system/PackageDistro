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

## Print all needed (and suggested) packages of the package <pkgname>
## and recursively its needed (and suggested) packages.
##
## We assume that the <pkgname>/meta.json files are stored in the
## current directory.
NamesOfAllDependencies:= function( pkgname, onlyneeded )
    local meta_dir, todo, pairs, unknown, result, name, filenam, file, meta,
          deps;

    meta_dir:= DirectoryCurrent();
    pkgname:= LowercaseString( pkgname );

    todo:= [ pkgname ];
    pairs:= [ [ pkgname, true ] ];
    unknown:= [];
    result:= [];

    for name in todo do
      filenam:= Concatenation( name, "/meta.json" );
      file:= StringFile( Filename( meta_dir, filenam ) );
      if file = fail then
        # A package may suggest some "non-official" package,
        # we simply ignore this.
        # But is a non-official package is needed, we are in trouble.
        AddSet( unknown, name );
      else
        Add( result, name );
        meta:= JsonStringToGap( file );
        deps:= Set( meta.Dependencies.NeededOtherPackages,
                    l -> [ LowercaseString( l[1] ), true ] );
        if not onlyneeded and
           IsBound( meta.Dependencies.SuggestedOtherPackages ) then
          UniteSet( deps, 
                    Set( meta.Dependencies.SuggestedOtherPackages,
                         l -> [ LowercaseString( l[1] ), false ] ) );
        fi;
        UniteSet( pairs, deps );
        deps:= List( deps, x -> x[1] );
        Append( todo, Difference( deps, todo ) );
      fi;
    od;

    for name in Set( result ) do
      Print( name, "\n" );
    od;

    for name in unknown do
      if [ name, true ] in pairs then
        Print( "Error: ", name, "\n");
      fi;
    od;
end;
