# flake.nix — NixOS development environment for the Primordial Soup
#
# Usage:
#   nix develop .
#   python -m primordial_soup
#
#   # Rodar os testes:
#   python -m pytest tests/ -v
#   # ou
#   nix flake check
#
# Or, if you prefer a shell with the script already running:
#   nix develop . --command python -m primordial_soup

{
  description = "Primordial Soup — Python environment with NumPy, Pygame, Pillow and pytest";

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

        # Python com todas as dependências de runtime + teste.
        python = pkgs.python312.withPackages (
          ps: with ps; [
            numpy
            pygame
            pillow
            pytest
            # setuptools é exigido pelo pyproject.toml (build-backend).
            setuptools
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
            echo " Python  : $(python --version 2>&1)"
            echo " NumPy   : $(python -c 'import numpy; print(numpy.__version__)' 2>/dev/null || echo 'not installed')"
            echo " Pygame  : $(python -c 'import pygame; print(pygame.version.ver)' 2>/dev/null || echo 'not installed')"
            echo " Pillow  : $(python -c 'import PIL; print(PIL.__version__)' 2>/dev/null || echo 'not installed')"
            echo " pytest  : $(python -m pytest --version 2>/dev/null | head -n1 || echo 'not installed')"
            echo "──────────────────────────────────────────────"
            echo " Run:   python -m primordial_soup"
            echo " Test:  python -m pytest tests/ -v"
            echo ""
            echo " In-game keys:"
            echo "   Space   → play/pause"
            echo "   =       → 1 tick"
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
            unset VIRTUAL_ENV
            unset PYTHONPATH
          '';
        };

        # `nix run .` — executa a simulação.
        packages.default = pkgs.writeShellApplication {
          name = "primordial_soup";
          runtimeInputs = [ python ];
          text = ''
            exec python -m primordial_soup
          '';
        };

        # `nix flake check` / `nix build .#checks.${system}.pytest`
        # Roda a suíte de testes contra o source atual.
        checks.pytest = pkgs.stdenv.mkDerivation {
          name = "primordial-soup-pytest";
          src = ./.;

          nativeBuildInputs = [ python ];

          # Os testes usam pygame, que precisa de SDL disponível mesmo
          # em modo "headless" (import de pygame.event).
          buildInputs = [
            pkgs.SDL2
            pkgs.SDL2_image
            pkgs.SDL2_mixer
            pkgs.SDL2_ttf
            pkgs.libGL
            pkgs.glib
            pkgs.zlib
          ];

          # Força pygame a usar o driver "dummy" — os testes não abrem
          # janela, mas importam pygame.
          SDL_VIDEODRIVER = "dummy";
          SDL_AUDIODRIVER = "dummy";

          dontConfigure = true;
          dontBuild = true;

          doCheck = true;
          checkPhase = ''
            runHook preCheck
            python -m pytest tests/ -v
            runHook postCheck
          '';

          installPhase = ''
            runHook preInstall
            mkdir -p $out
            echo "pytest passed" > $out/result
            runHook postInstall
          '';
        };
      }
    );
}
