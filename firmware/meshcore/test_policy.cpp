#include "IntervalGate.h"
#include "TelemetryPolicy.h"
#include <cassert>
#include <cstring>
#include <limits>
#include <iostream>

int main() {
    beelink::IntervalGate gate;
    assert(!gate.enabled() && !gate.take(9000000, 0));
    assert(gate.configure(true, 15, 0, 60000));
    assert(!gate.take(959999, 0));
    assert(gate.take(960000, 0));
    assert(gate.deadline() == 1860000); // catches the local model's missing interval
    assert(!gate.take(960001, 0));
    assert(gate.take(90000000, 0));
    assert(!gate.take(90000000, 0)); // no backlog burst
    assert(!gate.configure(true, 14, 0, 0));
    assert(!gate.configure(true, 15, 0, 60001));
    assert(gate.configure(false, 15, 90000000, 0));
    assert(!gate.take(99999999, 0));
    // Long uptime and intervals use 64 bits, not overflowing Arduino millis().
    assert(gate.configure(true, 1440, 5000000000ULL, 0));
    assert(gate.deadline() == 5086400000ULL);
    beelink::Snapshot s;
    s.utc_valid = true; s.utc_seconds = 1791892800; // 2026-10-13 12:00 UTC
    s.soc.value = 65; s.soc.captured_ms = 900; s.soc.verified = true;
    s.speed.value = 12.3; s.speed.captured_ms = 900; s.speed.verified = true;
    s.latitude.value = 51; s.latitude.captured_ms = 900; s.latitude.verified = true;
    s.longitude.value = -1; s.longitude.captured_ms = 900; s.longitude.verified = true;
    char out[121];
    assert(beelink::format(s, 1000, false, out));
    assert(std::strcmp(out, "Bee-Link 12:00Z BAT 65% SPD 12.3km/h") == 0);
    assert(beelink::format(s, 1000, true, out) && std::strstr(out, "GPS 51.0000,-1.0000"));
    assert(std::strlen(out) <= 120);
    assert(!beelink::format(s, 60901, true, out));
    assert(!beelink::format(s, 899, true, out)); // future samples
    s.soc.value = std::numeric_limits<double>::infinity();
    assert(beelink::format(s, 1000, false, out) && !std::strstr(out, "BAT"));
    s.speed.simulated = true;
    assert(!beelink::format(s, 1000, false, out));
    assert(beelink::format(s, 1000, true, out)); // independent location-only fix
    s.longitude.captured_ms = 7000;
    assert(!beelink::format(s, 7000, true, out)); // incoherent fix
    s.longitude.captured_ms = 900; s.latitude.value = 91;
    assert(!beelink::format(s, 1000, true, out));
    s.latitude.value = 51; s.utc_valid = false;
    assert(!beelink::format(s, 1000, true, out));
    std::cout << "Embedded scheduling and telemetry policy checks passed\n";
}
