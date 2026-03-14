#pragma once
#include <rack.hpp>
#include <vector>

using namespace rack;

namespace rack {
namespace plugin {
extern std::vector<Plugin*> plugins;
}
}

// Plugin instance is defined in plugin.cpp
extern Plugin* pluginInstance;

// Declare the external model instances that are defined in the module .cpp files
extern Model* modelRackMcpServer;
extern Model* modelMCPBridge;
