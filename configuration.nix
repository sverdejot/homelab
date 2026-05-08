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
    home = "/home/sverdejot";
    homeMode = "700";
    useDefaultShell = true;
    packages = with pkgs; [
      neovim
      k9s
    ];
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
