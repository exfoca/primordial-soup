# flake.nix — NixOS development environment for the Primordial Soup
#
# Usage:
#   nix develop .
#   python -m primordial_soup
#
# Or, if you prefer a shell with the script already running:
#   nix develop . --command python -m primordial_soup

{
  description = "Primordial Soup — Python environment with NumPy, Pygame and Pillow";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
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

        python = pkgs.python312.withPackages (
          ps: with ps; [
            numpy
            pygame
            pillow
          ]
        );
      in
      {
        devShells.default = pkgs.mkShell {
          name = "primordial-soup-python";

          packages = [
            python
            pkgs.uv
            pkgs.git
          ];

          shellHook = ''
            echo "──────────────────────────────────────────────"
            echo " Primordial Soup — Python environment ready"
            echo " Python : $(python --version 2>&1)"
            echo " NumPy  : $(python -c 'import numpy; print(numpy.__version__)' 2>/dev/null || echo 'not installed')"
            echo " Pygame : $(python -c 'import pygame; print(pygame.version.ver)' 2>/dev/null || echo 'not installed')"
            echo " Pillow : $(python -c 'import PIL; print(PIL.__version__)' 2>/dev/null || echo 'not installed')"
            echo "──────────────────────────────────────────────"
            echo " Run: python -m primordial_soup"
            echo ""
            echo " In-game keys:"
            echo "   Space   → play/pause"
            echo "   →       → 1 tick"
            echo "   R       → recreate population"
            echo "   G       → start/stop GIF recording"
            echo "   ESC     → quit"
            echo "──────────────────────────────────────────────"

            # Ensure native libraries (SDL2, libstdc++, etc.)
            # are found at runtime.
            export LD_LIBRARY_PATH="${
              pkgs.lib.makeLibraryPath [
                pkgs.stdenv.cc.cc.lib
                pkgs.SDL2
                pkgs.SDL2_image
                pkgs.SDL2_mixer
                pkgs.SDL2_ttf
                pkgs.libGL
                pkgs.glib
                pkgs.zlib
              ]
            }''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

            # Prevent Python from using the old broken venv.
            # If you want to use the venv, comment out the lines below.
            unset VIRTUAL_ENV
            unset PYTHONPATH

            # Bump process CPU priority (optional).
            # ulimit -s unlimited 2>/dev/null || true
          '';
        };

        # Optional executable package: `nix run .`
        packages.default = pkgs.writeShellApplication {
          name = "primordial_soup";
          runtimeInputs = [ python ];
          text = ''
            exec python -m primordial_soup
          '';
        };
      }
    );
}
