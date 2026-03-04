# =============================================================================
# vcv-rack-mcp-server — VCV Rack 2 Plugin
# Makefile: VCV Library-compatible build system
#
# USAGE:
#   export RACK_DIR=/path/to/Rack-SDK-2.x.x
#   make dep       # auto-downloads cpp-httplib (run once)
#   make           # builds the plugin .so/.dylib/.dll
#   make install   # installs to your Rack plugins folder
#   make dist      # creates distributable .vcvplugin package
#   make clean     # removes build artifacts
# =============================================================================

RACK_DIR ?= $(HOME)/Rack-SDK

# ── Plugin identity ──────────────────────────────────────────────────────────
SLUG    = VCVRackMcpServer
VERSION = 2.0.0

# ── Sources ──────────────────────────────────────────────────────────────────
SOURCES  = src/plugin.cpp
SOURCES += src/RackMcpServer.cpp

# ── Compiler flags ───────────────────────────────────────────────────────────
# dep/include is where httplib.h lands after `make dep`
FLAGS += -Idep/include
FLAGS += -std=c++17

# httplib.h uses std::thread; link pthreads on Linux/Mac.
# On Windows the Rack toolchain handles this automatically.
UNAME := $(shell uname -s 2>/dev/null || echo Windows)
ifneq ($(UNAME), Windows)
  LDFLAGS += -lpthread
endif

# ── Dependency auto-download ──────────────────────────────────────────────────
HTTPLIB_VERSION = v0.18.0
HTTPLIB_URL     = https://github.com/yhirose/cpp-httplib/releases/download/$(HTTPLIB_VERSION)/httplib.h
HTTPLIB_HEADER  = dep/include/httplib.h

# Called before the main build by `make dep` or automatically by the CI.
# Also hooked into the standard Rack SDK dep target so `make dep && make` works.
dep: $(HTTPLIB_HEADER)

$(HTTPLIB_HEADER):
	@echo "[vcv-rack-mcp-server] Downloading cpp-httplib $(HTTPLIB_VERSION)..."
	@mkdir -p dep/include
	@curl -fsSL "$(HTTPLIB_URL)" -o "$@" || \
	  wget -q  "$(HTTPLIB_URL)" -O "$@"
	@echo "[vcv-rack-mcp-server] cpp-httplib downloaded → $@"

# ── VCV Rack build system (must be last) ─────────────────────────────────────
include $(RACK_DIR)/plugin.mk
