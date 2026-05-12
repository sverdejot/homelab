{ config, pkgs, lib, ... }:

{
  nix = {
    package = pkgs.nixVersions.stable;
  };

  networking.firewall = lib.mkForce {
    enable = true;

    allowedTCPPorts = [
      22                      # ssh
      80 443                  # ingresses
      3260                    # open-iccsi // longhorn
      6443                    # k8s
      7946 7472 7473          # MetalLB
      9100                    # Prometheus
    ];
    allowedTCPPortRanges = [
      { from = 10000; to = 10100; }   # longhorn (replicas)
    ];

    allowedUDPPorts = [
      53                      # core-dns
      8472 7946               # MetalLB
    ];
    trustedInterfaces = [ 
      "flannel.1"             # MetalLB
      "cni0"                  # open-iscsi // longhorn
    ]; 
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
