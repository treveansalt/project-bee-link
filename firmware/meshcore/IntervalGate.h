#pragma once
#include <cstdint>

namespace beelink {
// Mac local-model draft, repaired to retain the interval on every attempt.
class IntervalGate {
public:
    bool configure(bool enabled, unsigned minutes, uint64_t now_ms, unsigned jitter_ms) {
        if (minutes < 15 || minutes > 1440 || jitter_ms > 60000) return false;
        interval_ = static_cast<uint64_t>(minutes) * 60000;
        enabled_ = enabled;
        deadline_ = enabled ? now_ms + interval_ + jitter_ms : 0;
        return true;
    }
    bool take(uint64_t now_ms, unsigned jitter_ms) {
        if (!enabled_ || jitter_ms > 60000 || now_ms < deadline_) return false;
        deadline_ = now_ms + interval_ + jitter_ms;
        return true;
    }
    bool enabled() const { return enabled_; }
    uint64_t deadline() const { return deadline_; }
private:
    bool enabled_ = false;
    uint64_t deadline_ = 0;
    uint64_t interval_ = 900000;
};
}
