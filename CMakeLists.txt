cmake_minimum_required(VERSION 3.21)
project(VCVRackMcpServer VERSION 2.0.0 LANGUAGES CXX)

# =============================================================================
# vcv-rack-mcp-server — VCV Rack 2 Plugin  (CMake build)
#
# USAGE:
#   cmake -B build -DRACK_DIR=/path/to/Rack-SDK-2.x.x
#   cmake --build build
#   cmake --install build   # installs to Rack plugins folder
#
# CMake will automatically download cpp-httplib via FetchContent.
# Set RACK_DIR to your Rack SDK path (or set the env variable).
# =============================================================================

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ── Rack SDK location ─────────────────────────────────────────────────────────
if(NOT DEFINED RACK_DIR)
  if(DEFINED ENV{RACK_DIR})
    set(RACK_DIR $ENV{RACK_DIR})
  else()
    message(FATAL_ERROR
      "RACK_DIR not set. Pass -DRACK_DIR=/path/to/Rack-SDK or set the RACK_DIR env variable.\n"
      "Download the Rack SDK from: https://vcvrack.com/downloads")
  endif()
endif()
message(STATUS "Using Rack SDK at: ${RACK_DIR}")

# ── FetchContent: cpp-httplib (header-only, MIT) ──────────────────────────────
include(FetchContent)

FetchContent_Declare(
  httplib
  URL      https://github.com/yhirose/cpp-httplib/releases/download/v0.18.0/httplib.h
  URL_HASH SHA256=0                          # set to real hash for reproducible builds
  DOWNLOAD_NO_EXTRACT TRUE                   # it's a single header, not an archive
  DOWNLOAD_DIR ${CMAKE_BINARY_DIR}/_deps/httplib
)
FetchContent_MakeAvailable(httplib)

# Create an interface target so we can link against it cleanly
add_library(httplib INTERFACE)
target_include_directories(httplib INTERFACE
  ${CMAKE_BINARY_DIR}/_deps/httplib
)

# ── Detect platform/architecture ─────────────────────────────────────────────
if(APPLE)
  if(CMAKE_SYSTEM_PROCESSOR MATCHES "arm64")
    set(RACK_ARCH "mac-arm64")
  else()
    set(RACK_ARCH "mac-x64")
  endif()
  set(PLUGIN_EXT ".dylib")
elseif(WIN32)
  set(RACK_ARCH "win-x64")
  set(PLUGIN_EXT ".dll")
else()
  set(RACK_ARCH "lin-x64")
  set(PLUGIN_EXT ".so")
endif()

# ── Rack SDK include / link paths ─────────────────────────────────────────────
set(RACK_INCLUDE_DIR  ${RACK_DIR}/include)
set(RACK_DEP_DIR      ${RACK_DIR}/dep/include)
set(RACK_LIB          ${RACK_DIR}/libRack${CMAKE_SHARED_LIBRARY_SUFFIX})

if(NOT EXISTS ${RACK_INCLUDE_DIR}/rack.hpp)
  message(FATAL_ERROR "rack.hpp not found in ${RACK_INCLUDE_DIR}. Check RACK_DIR.")
endif()

# ── Plugin shared library ─────────────────────────────────────────────────────
add_library(VCVRackMcpServer MODULE
  src/plugin.cpp
  src/RackMcpServer.cpp
)

set_target_properties(VCVRackMcpServer PROPERTIES
  PREFIX   ""
  SUFFIX   ${PLUGIN_EXT}
  OUTPUT_NAME "plugin"
)

target_include_directories(VCVRackMcpServer PRIVATE
  ${RACK_INCLUDE_DIR}
  ${RACK_DEP_DIR}
  ${CMAKE_BINARY_DIR}/_deps/httplib   # httplib.h lives here after FetchContent
)

target_compile_options(VCVRackMcpServer PRIVATE
  -fPIC
  -O3
  -march=nocona        # Rack SDK minimum (SSE4.2 equivalent baseline)
  -funsafe-math-optimizations
  -fno-omit-frame-pointer
  $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra -Wno-unused-parameter>
)

target_compile_definitions(VCVRackMcpServer PRIVATE
  ARCH_${RACK_ARCH}   # lets source code #ifdef on arch if needed
)

if(APPLE)
  target_link_options(VCVRackMcpServer PRIVATE
    -undefined dynamic_lookup   # Rack symbols resolved at load time by Rack
    -Wl,-install_name,@rpath/plugin.dylib
  )
elseif(UNIX)
  target_link_options(VCVRackMcpServer PRIVATE
    -Wl,--allow-shlib-undefined  # same — Rack resolves symbols at load time
  )
  target_link_libraries(VCVRackMcpServer PRIVATE pthread)
elseif(WIN32)
  target_link_libraries(VCVRackMcpServer PRIVATE ws2_32 mswsock)
endif()

# ── Install target ────────────────────────────────────────────────────────────
# Determines Rack plugins folder per platform
if(APPLE)
  set(RACK_PLUGINS_DIR "$ENV{HOME}/Documents/Rack2/plugins")
elseif(WIN32)
  set(RACK_PLUGINS_DIR "$ENV{APPDATA}/Rack2/plugins")
else()
  set(RACK_PLUGINS_DIR "$ENV{HOME}/.Rack2/plugins")
endif()

set(PLUGIN_INSTALL_DIR ${RACK_PLUGINS_DIR}/VCVRackMcpServer)

install(TARGETS VCVRackMcpServer
  LIBRARY DESTINATION ${PLUGIN_INSTALL_DIR}
)
install(FILES plugin.json
  DESTINATION ${PLUGIN_INSTALL_DIR}
)
install(DIRECTORY res/
  DESTINATION ${PLUGIN_INSTALL_DIR}/res
  OPTIONAL
)

message(STATUS "Install target: ${PLUGIN_INSTALL_DIR}")

# ── Summary ───────────────────────────────────────────────────────────────────
message(STATUS "vcv-rack-mcp-server plugin configured.")
message(STATUS "  Platform : ${RACK_ARCH}")
message(STATUS "  Rack SDK : ${RACK_DIR}")
message(STATUS "  Build    : cmake --build <build_dir>")
message(STATUS "  Install  : cmake --install <build_dir>")
