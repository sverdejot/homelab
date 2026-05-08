{
  description = "sverdejot-homelab";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    nixos-raspberrypi = {
      url = "github:nvmd/nixos-raspberrypi/main";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    disko = {
      url = "github:nix-community/disko";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, nixos-raspberrypi, disko, ... }:
  let
    mkNode = { hostname, storageModule, extraModules ? [] }:
      nixos-raspberrypi.lib.nixosSystem {
        specialArgs = { inherit nixos-raspberrypi; };
        modules = [
          nixos-raspberrypi.nixosModules.raspberry-pi-5
          nixos-raspberrypi.nixosModules.page-size-16k
          disko.nixosModules.disko
          storageModule
          ./configuration.nix
          { networking.hostName = hostname; }
        ] ++ extraModules;
      };
  in {
    nixosConfigurations = {
      homelab-0 = mkNode { 
        hostname = "homelab-0"; 
        storageModule = ./nvme.nix; 
        extraModules = [ ./k3s-server.nix ]; 
      };
      homelab-1 = mkNode { 
        hostname = "homelab-1"; 
        storageModule = ./sd.nix; 
        extraModules = [ ./k3s-agent.nix ]; 
      };
      homelab-2 = mkNode { 
        hostname = "homelab-2"; 
        storageModule = ./sd.nix; 
        extraModules = [ ./k3s-agent.nix ]; 
      };
      homelab-3 = mkNode { 
        hostname = "homelab-3"; 
        storageModule = ./sd.nix; 
        extraModules = [ ./k3s-agent.nix ]; 
      };
    };

  };
}
