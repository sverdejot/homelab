{ config, pkgs, modulesPath, ... }:

{
  imports =
    [
      "${modulesPath}/virtualisation/lxc-container.nix"
			# needed for NixOS VM running on OrbStack
      ./lxd.nix
      ./orbstack.nix
    ];

  users.mutableUsers = false;

  networking = {
    dhcpcd.enable = false;
    useDHCP = false;
    useHostResolvConf = false;
  };

  systemd.network = {
    enable = true;
    networks."50-eth0" = {
      matchConfig.Name = "eth0";
      networkConfig = {
        DHCP = "ipv4";
        IPv6AcceptRA = true;
      };
      linkConfig.RequiredForOnline = "routable";
    };
  };
}

