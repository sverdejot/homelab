{ lib, ... }: {
  users.users.root.openssh.authorizedKeys.keys = [
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDrmz07HwGLmolDv93gK9QUfU7cP207iJA80ZVsoAV+h sverdejot@sverdehost.local"
  ];
  networking.wireless.enable = lib.mkForce false;
}
