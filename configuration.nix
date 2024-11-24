{ config, pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    neovim
    k3s
  ];

  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ 6443 ];
  };

  services.k3s = {
    enable = true;
    role = "server";
		extraArgs = [
			# need to define here the token for other nodes to be able to register
			"--disable=traefik"
		];
  };

  time.timeZone = "Europe/Madrid";

  system.stateVersion = "24.05"; 
}
