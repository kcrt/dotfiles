## PACKAGE MANAGEMENT (nix-env)
nix-env -i|-e python3       # -i: install, -e: uninstall
  -q: list installed packages
  -qa: query all available packages
  -qaP python: search packages with pattern 
  -u [python]: upgrade all (or specified) packages
  --list-generations: list generations

## TEMPORARY ENVIRONMENTS (nix-shell)
nix-shell -p python311 R [--run python]	# Create temporal environment with packages (and run command)
nix-shell                               # load shell.nix and create environment

## FLAKES (Modern Nix)
  * flakes = reproducible, shareable Nix projects including package and NixOS configurations
nix flake init|update|show|check
nix run nixpkgs#hello # run package from flake
nix run .#myapp			  # run app from local flake
nix develop			      # enter development shell from flake.nix
nix develop nixpkgs#python3	# dev shell with package
nix build			        # build flake
nix search nixpkgs python

## FLAKE.NIX EXAMPLE
{
  description = "My project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      packages.${system}.default = pkgs.hello;
      devShells.${system}.default = pkgs.mkShell {
        packages = [ pkgs.python3 ];
      };
    };
}

## GARBAGE COLLECTION & OPTIMIZATION
nix-collect-garbage	 [-d]
nix-store --gc|--optimize

## STORE OPERATIONS (operate /nix/store)
nix-store -q --references|--referres|tree /nix/store/XXXX   # show dependencies
nix-store --repair-path /nix/store/XXXX                     # repair corrupted path

## DEVELOPMENT
nix-build			# build default.nix