{ nixos-raspberrypi, disko, lib }:

let
  net = n: {
    networking.hostName = "homelab-${toString n}";
    networking.useDHCP = false;
    networking.interfaces.end0.ipv4.addresses = [{
      address = "192.168.1.${toString (n + 2)}";
      prefixLength = 24;
    }];
    networking.defaultGateway = { address = "192.168.1.1"; interface = "end0"; };
    networking.nameservers = [ "192.168.1.1" ];
  };

  node = { n, disk, mods ? [ ] }:
    nixos-raspberrypi.lib.nixosSystem {
      specialArgs = { inherit nixos-raspberrypi; };
      modules = [
        nixos-raspberrypi.nixosModules.raspberry-pi-5.base
        nixos-raspberrypi.nixosModules.raspberry-pi-5.page-size-16k
        disko.nixosModules.disko
        disk
        ./common.nix
        (net n)
      ] ++ mods;
    };

  image = nixos-raspberrypi.nixosConfigurations.rpi5-installer.extendModules;

  agents = builtins.genList (x: x + 1) (3);

  gen = suffix: fn: builtins.listToAttrs (map (n: {
    name = "homelab-${toString n}${suffix}";
    value = fn n;
  }) agents);
in {
  nixosConfigurations = {
    homelab-installer = image { modules = [ ./installer.nix ]; };
    homelab-0 = node { n = 0; disk = ./disko/nvme.nix; mods = [ ./k3s/server.nix ]; };
  } // gen "" (n: node { inherit n; disk = ./disko/sd.nix; mods = [ ./k3s/agent.nix ]; })
    // gen "-image" (n: image {
         modules = [
           ./common.nix
           ./k3s/agent.nix
           (net n)
           { networking.useDHCP = lib.mkForce false; networking.wireless.enable = lib.mkForce false; }
         ];
       });
}
