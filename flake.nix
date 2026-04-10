{
  description = "garmin-bridge — Push notifications, alarms, and calendar to Garmin watches via BLE";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python312;
      pythonPkgs = pkgs.python312Packages;
    in
    {
      packages.${system}.default = python.pkgs.buildPythonApplication {
        pname = "garmin-bridge";
        version = "0.1.0";
        src = ./.;
        format = "pyproject";

        nativeBuildInputs = [ pythonPkgs.poetry-core ];
        propagatedBuildInputs = [
          pythonPkgs.bleak
          pythonPkgs.dbus-next
          pythonPkgs.icalendar
          pythonPkgs.click
        ];
      };

      devShells.${system}.default = pkgs.mkShell {
        buildInputs = [
          python
          pkgs.poetry
          pkgs.bluez
          pkgs.dbus
        ];
      };
    };
}
