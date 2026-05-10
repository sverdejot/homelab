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
    sops-nix = {
      url = "github:Mic92/sops-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, nixos-raspberrypi, disko, sops-nix, ... }:
  let
    hosts = import ./modules/hosts.nix;

    mkIP = nodeNum: "${hosts.baseIP}.${toString (nodeNum + hosts.ipOffset)}";

    mkNode = { nodeNum, storageModule, extraModules ? [] }:
      let
        hostname = "homelab-${toString nodeNum}";
        ip = mkIP nodeNum;
      in nixos-raspberrypi.lib.nixosSystem {
        specialArgs = { inherit nixos-raspberrypi; };
        modules = [
          nixos-raspberrypi.nixosModules.raspberry-pi-5.base
          nixos-raspberrypi.nixosModules.raspberry-pi-5.page-size-16k
          disko.nixosModules.disko
          sops-nix.nixosModules.sops
          storageModule
          ./modules/common.nix
          {
            networking.hostName = hostname;
            networking.useDHCP = false;
            networking.interfaces.end0.ipv4.addresses = [{
              address = ip;
              prefixLength = 24;
            }];
            networking.defaultGateway = "192.168.1.1";
            networking.nameservers = [ "192.168.1.1" ];
          }
        ] ++ extraModules;
      };

    agentNodes = builtins.listToAttrs (map (n: {
      name = "homelab-${toString n}";
      value = mkNode (hosts.agent // { nodeNum = n; });
    }) (builtins.genList (x: x + 1) (hosts.nodeCount - 1)));
  in {
    nixosConfigurations = {
      homelab-installer = nixos-raspberrypi.nixosConfigurations.rpi5-installer.extendModules {
        modules = [ ./modules/installer.nix ];
      };

      "homelab-${toString hosts.master.nodeNum}" = mkNode hosts.master;
    } // agentNodes;
  };
}
