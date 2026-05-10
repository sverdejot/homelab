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

  users.users.homelab = {
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

  security.sudo.wheelNeedsPassword = false;

  time.timeZone = "Europe/Madrid";

  boot.loader.raspberry-pi.bootloader = "kernel";

  system.stateVersion = "24.05";

  sops = {
    defaultSopsFile = ./token.yaml;
    age.keyFile = "/var/lib/sops-nix/age-key";

    secrets.k3s-token = {
      # decrypted to /run/secrets/k3s-token
    };
  };

  systemd.tmpfiles.rules = [
    "d /var/lib/sops-nix 0700 root root - -"
    "f /var/lib/sops-nix/age-key 0400 root root - AGE-SECRET-KEY-1TT4P2U7ZR949SAK435HY5RAC3AK9NFVP0EE7GEFN28R97LW9R9CQNXFSL5"
  ];
}
