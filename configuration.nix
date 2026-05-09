{ config, pkgs, ... }:

{
  nix = {
    package = pkgs.nixVersions.stable;
  };

  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ 22 ];
  };

  services.openssh.enable = true;

  services.avahi = {
    enable = true;
    nssmdns4 = true;
    publish = {
      enable = true;
      addresses = true;
      workstation = true;
    };
  };

  users.users.sverdejot = {
    isNormalUser = true;
    extraGroups = [ "wheel" ];
    createHome = true;
    home = "/home/homelab";
    homeMode = "700";
    useDefaultShell = true;
    hashedPassword = "$6$H64VBbiI4Smitv2a$t60NdAAB6yQNmSJ7Au4iodkW7zBwD8yeU22MEOds4AvcxXOqMCR7hyDD8zYlWvjwyov2lmTri//m3nIS.iv.Z0";
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDrmz07HwGLmolDv93gK9QUfU7cP207iJA80ZVsoAV+h sverdejot@sverdehost.local"
    ];
  };

  boot.kernelParams = [
    "cgroup_memory=1"
    "cgroup_enable=memory"
  ];

  # 👀‼️
  security.sudo.wheelNeedsPassword = false;

  time.timeZone = "Europe/Madrid";

  boot.loader.raspberry-pi.bootloader = "kernel";

  system.stateVersion = "24.05";
}
