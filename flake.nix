{
  description = "sverdejot-homelab";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs";

  outputs = { self, nixpkgs, ... }: {
    nixosConfigurations = {
      homelab = nixpkgs.lib.nixosSystem {
        system = "aarch64-linux"; 
        modules = [
          ./configuration.nix
          ./virtualization.nix
        ];
      };
    };
  };
}

