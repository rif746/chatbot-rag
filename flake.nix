{
  description = "Lingkungan Pengembangan Python Deklaratif untuk RAG FAQ Lokal";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.python312
            pkgs.uv
            pkgs.sqlite
          ];

          # Required so pre-compiled PyPI wheels (numpy, sqlite-vec, etc.) find libstdc++ and zlib on Nix
          env.LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
            pkgs.stdenv.cc.cc.lib
            pkgs.zlib
          ];

          shellHook = ''
            if [ ! -d ".venv" ]; then
              uv venv --python ${pkgs.python312}/bin/python
            fi
            source .venv/bin/activate
            ln -sfn $(which python) .nix-python
          '';
        };
      }
    );
}
