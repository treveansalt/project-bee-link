#pragma once
#include <cstddef>
#include <cstdint>

void beeLinkBegin();
void beeLinkLoop();
// Local companion extension. No incoming mesh packet can call this.
size_t beeLinkCommand(const uint8_t* command, size_t length, uint8_t* reply);
// Future validated CAN decoder calls from the same main-loop task only.
// Never call this from a CAN ISR, or with guessed/simulated bike SOC.
void beeLinkVerifiedSoc(double percent, uint64_t capture_monotonic_ms);
