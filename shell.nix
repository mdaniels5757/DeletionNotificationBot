{
  pkgs ? import <nixpkgs> {},
}:

pkgs.mkShell {
  packages = with pkgs; [
    (python313.withPackages (ps: with ps; [
      cryptography
      mwparserfromhell
      pywikibot
      pyyaml
      redis
      requests-oauthlib
      sseclient
      tqdm
      urllib3
      wikitextparser
      ipython
      pytest
    ]))
    uv
    ty
    ruff
  ];
}
