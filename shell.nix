{
  pkgs ? import <nixpkgs> {},
}:

pkgs.mkShell {
  packages = [
    (pkgs.python313.withPackages (ps: [
      ps.pywikibot
    ]))
    pkgs.uv
  ];
}
