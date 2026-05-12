{ config, pkgs, lib, ... }:

{
  nix = {
    package = pkgs.nixVersions.stable;
  };

  networking.firewall = lib.mkForce {
    enable = true;

    allowedTCPPorts = [ 22 80 443 3260 6443 7946 7472 7473 9100 ];
    allowedTCPPortRanges = [
      { from = 9500; to = 9600; }
      { from = 10000; to = 30000; }
    ];

    allowedUDPPorts = [ 53 8472 7946 ];
    trustedInterfaces = [ "flannel.1" "cni0" ];
  };

  services.openssh.enable = true;

  services.openiscsi = {
    enable = true;
    name = "iqn.2016-01.com.homelab:${config.networking.hostName}";
  };

  systemd.services.iscsid.serviceConfig = {
    PrivateMounts = "yes";
    BindPaths = "/run/current-system/sw/bin:/bin";
  };

  services.avahi = {
    enable = true;
    nssmdns4 = true;
    publish = {
      enable = true;
      addresses = true;
      workstation = true;
    };
  };

  users.users.homelab = {
    isNormalUser = true;
    extraGroups = [ "wheel" ];
    createHome = true;
    home = "/home/homelab";
    homeMode = "700";
    useDefaultShell = true;
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDrmz07HwGLmolDv93gK9QUfU7cP207iJA80ZVsoAV+h sverdejot@sverdehost.local"
    ];
  };

  boot.kernelParams = [
    "cgroup_memory=1"
    "cgroup_enable=memory"
  ];

  security.sudo.wheelNeedsPassword = false;

  time.timeZone = "Europe/Madrid";

  boot.loader.raspberry-pi.bootloader = "kernel";

  system.stateVersion = "26.05";
}
