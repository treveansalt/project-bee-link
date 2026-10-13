#pragma once
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstring>

namespace beelink {
struct Reading {
    double value = 0;
    uint64_t captured_ms = 0;
    bool verified = false;
    bool simulated = false;
};
struct Snapshot {
    Reading soc, speed, latitude, longitude;
    uint32_t utc_seconds = 0;
    bool utc_valid = false;
};
inline bool fresh(const Reading& r, uint64_t now, double low, double high) {
    return r.verified && !r.simulated && std::isfinite(r.value) &&
           r.value >= low && r.value <= high && now >= r.captured_ms &&
           now - r.captured_ms <= 60000;
}
// Separate per-field freshness. Output time is the current trusted GNSS anchor.
inline bool format(const Snapshot& s, uint64_t now, bool location, char (&out)[121]) {
    out[0] = 0;
    if (!s.utc_valid || s.utc_seconds < 1704067200U) return false;
    char fields[96] = {};
    size_t used = 0;
    if (fresh(s.soc, now, 0, 100))
        used += std::snprintf(fields + used, sizeof(fields) - used, " BAT %.0f%%", s.soc.value);
    if (fresh(s.speed, now, 0, 250))
        used += std::snprintf(fields + used, sizeof(fields) - used, " SPD %.1fkm/h", s.speed.value);
    if (location && fresh(s.latitude, now, -90, 90) && fresh(s.longitude, now, -180, 180)) {
        uint64_t a = s.latitude.captured_ms, b = s.longitude.captured_ms;
        if ((a > b ? a - b : b - a) <= 5000)
            used += std::snprintf(fields + used, sizeof(fields) - used, " GPS %.4f,%.4f", s.latitude.value, s.longitude.value);
    }
    if (!used || used >= sizeof(fields)) return false;
    unsigned hour = (s.utc_seconds / 3600) % 24, minute = (s.utc_seconds / 60) % 60;
    int size = std::snprintf(out, sizeof(out), "Bee-Link %02u:%02uZ%s", hour, minute, fields);
    return size > 0 && size <= 120;
}
}
