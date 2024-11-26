{ config, pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    k3s
  ];

	nix = {
		package = pkgs.nixVersions.stable;
	};

  networking.firewall = {
    enable = true;
    allowedTCPPorts = [
			6443
			22
		];
  };

  services.k3s = {
    enable = true;
    role = "server";
		extraFlags = toString ([
			# need to define here the token for other nodes to be able to register
			"--disable=traefik"
		]);
  };

	# Enable this when deploying to the RPi
	# services.openssh.enabled = true;

	# Configure a 'usable' user to ssh into the machine
	users.users.sverdejot = {
		isNormalUser = true;
		extraGroups = [ "wheel" ];
		createHome = true;
		home = "/home/sverdejot";
		homeMode = "700";
		useDefaultShell = true;
		packages = with pkgs; [
			neovim
		];
		hashedPassword = "$6$aGWdzWH.vlIZ0N7/$XSX2YSug4vWgH0J9FK//6iAI5A56fXP/gpdjCshV6wtegsiIhFQycC5csyCovms7Ga6.RxazgQ7GfuKaxUu2J0";
		openssh.authorizedKeys.keys = [
			"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDrmz07HwGLmolDv93gK9QUfU7cP207iJA80ZVsoAV+h sverdejot@sverdehost.local"
		];
	};

	# 👀‼️
  security.sudo.wheelNeedsPassword = false;

  time.timeZone = "Europe/Madrid";

  system.stateVersion = "24.05"; 
}
