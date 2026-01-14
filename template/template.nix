{ pkgs ? import <nixpkgs> {} }:

pkgs.stdenv.mkDerivation {
  pname = "example";
  version = "0.1.0";
  src = ./.;

  buildInputs = with pkgs; [
    # Add dependencies here
  ];

  buildPhase = ''
    echo "Build phase"
  '';

  installPhase = ''
    mkdir -p $out
    echo "Install phase"
  '';

  meta = {
    description = "A template package";
    homepage = "";
    license = pkgs.lib.licenses.mit;
    maintainers = with pkgs.lib.maintainers; [ ];
  };
}
