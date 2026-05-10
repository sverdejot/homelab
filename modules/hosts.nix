{
  nodeCount = 4;
  baseIP = "192.168.1";
  ipOffset = 2;

  master = {
    nodeNum = 0;
    storageModule = ./disko/nvme.nix;
    extraModules = [ ./k3s/server.nix ];
  };

  agent = {
    storageModule = ./disko/sd.nix;
    extraModules = [ ./k3s/agent.nix ];
  };
}
