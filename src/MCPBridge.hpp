#pragma once

#include "plugin.hpp"

#define CPPHTTPLIB_OPENSSL_SUPPORT 0
#include <httplib.h>

#include <atomic>
#include <thread>

class RackHttpServer {
public:
    httplib::Server svr;
    std::thread serverThread;
    std::atomic<bool> running{false};
    int port = 2600;

    RackHttpServer() = default;
    ~RackHttpServer();

    void setupRoutes();
    void start();
    void stop();
};

struct MCPBridge : Module {
    enum ParamIds {
        PORT_PARAM,
        ENABLED_PARAM,
        NUM_PARAMS
    };
    enum InputIds { NUM_INPUTS };
    enum OutputIds {
        HEARTBEAT_OUTPUT,
        NUM_OUTPUTS
    };
    enum LightIds {
        RUNNING_LIGHT,
        NUM_LIGHTS
    };

    RackHttpServer* server = nullptr;
    bool wasEnabled = false;
    float heartbeatPhase = 0.f;

    MCPBridge();
    ~MCPBridge() override;

    void startServer(int port);
    void stopServer();
    void process(const ProcessArgs& args) override;
    json_t* dataToJson() override;
    void dataFromJson(json_t* rootJ) override;
};

struct MCPBridgeWidget : ModuleWidget {
    explicit MCPBridgeWidget(MCPBridge* module);
    void appendContextMenu(Menu* menu) override;
};
