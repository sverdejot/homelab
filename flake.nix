{
  description = "sverdejot-homelab";

  nixConfig = {
    extra-substituters = [
      "https://nixos-raspberrypi.cachix.org"
    ];
    extra-trusted-public-keys = [
      "nixos-raspberrypi.cachix.org-1:4iMO9LXa8BqhU+Rpg6LQKiGa2lsNh/j2oiYLNOQ5sPI="
    ];
  };

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

  outputs = { nixpkgs, nixos-raspberrypi, disko, ... }:
  let
    inherit (nixpkgs) lib;
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

    agentImages = builtins.listToAttrs (map (n: {
      name = "homelab-${toString n}-image";
      value = nixos-raspberrypi.nixosConfigurations.rpi5-installer.extendModules {
        modules = [
          ./modules/common.nix
          ./modules/k3s/agent.nix
          ({ ... }: {
            networking.hostName = "homelab-${toString n}";
            networking.useDHCP = lib.mkForce false;
            networking.interfaces.end0.ipv4.addresses = [{
              address = mkIP n;
              prefixLength = 24;
            }];
            networking.defaultGateway = {
              address = "192.168.1.1";
              interface = "end0";
            };
            networking.nameservers = [ "192.168.1.1" ];
            networking.wireless.enable = lib.mkForce false;
          })
        ];
      };
    }) (builtins.genList (x: x + 1) (hosts.nodeCount - 1)));
  in {
    nixosConfigurations = {
      homelab-installer = nixos-raspberrypi.nixosConfigurations.rpi5-installer.extendModules {
        modules = [ ./modules/installer.nix ];
      };

      "homelab-${toString hosts.master.nodeNum}" = mkNode hosts.master;
    } // agentNodes // agentImages;
  };
}
