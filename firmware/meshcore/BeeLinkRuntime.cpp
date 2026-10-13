#include "BeeLinkRuntime.h"
#include "IntervalGate.h"
#include "TelemetryPolicy.h"
#include "MyMesh.h"
#include <Arduino.h>
#include <TinyGPSPlus.h>
#include <esp_timer.h>
#include <esp_system.h>

#if !defined(BEELINK_GNSS_RESET_ISOLATED) || BEELINK_GNSS_RESET_ISOLATED != 1
#error Confirm isolation of L76K D10 reset from radio MOSI before building this target.
#endif

namespace {
TinyGPSPlus gps;
HardwareSerial gnss(1);
beelink::IntervalGate gate;
beelink::Snapshot snapshot;
bool location = false;
uint8_t channel_index = 1, state = 0;
unsigned minutes = 15;
uint8_t expected_key[32] = {};
uint64_t utc_anchor_ms = 0;
uint32_t utc_anchor = 0;
uint64_t nowMs() { return static_cast<uint64_t>(esp_timer_get_time()) / 1000; }
unsigned jitter() { return esp_random() % 60001U; }

bool privateChannel(uint8_t index, ChannelDetails& result) {
    if (index == 0 || index >= MAX_GROUP_CHANNELS || !the_mesh.getChannel(index, result)) return false;
    uint8_t zero[32] = {};
    // Decoded upstream PUBLIC_GROUP_PSK (izOH6cXN6mrJ5e26oRXNcg==), padded to 32.
    const uint8_t public_key[32] = {0x8b,0x33,0x87,0xe9,0xc5,0xcd,0xea,0x6a,
                                  0xc9,0xe5,0xed,0xba,0xa1,0x15,0xcd,0x72};
    return result.name[0] && std::memcmp(result.channel.secret, zero, 32) != 0 &&
           std::memcmp(result.channel.secret, public_key, 32) != 0;
}
uint32_t gpsEpoch() {
    unsigned y = gps.date.year(), m = gps.date.month(), d = gps.date.day();
    if (y < 2024 || y > 2099 || m < 1 || m > 12 || d < 1 || d > 31) return 0;
    const unsigned days_month[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    unsigned max_day = days_month[m-1] + (m == 2 && y % 4 == 0);
    if (d > max_day || gps.time.hour() > 23 || gps.time.minute() > 59 || gps.time.second() > 59) return 0;
    uint32_t days = 0;
    for (unsigned year = 1970; year < y; ++year) days += 365 + (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0));
    for (unsigned month = 1; month < m; ++month) days += days_month[month-1] + (month == 2 && y % 4 == 0);
    days += d-1;
    return days*86400U + gps.time.hour()*3600U + gps.time.minute()*60U + gps.time.second();
}
void status(uint8_t* reply) {
    reply[0] = 0xE0; reply[1] = 1;
    reply[2] = gate.enabled(); reply[3] = location; reply[4] = channel_index;
    reply[5] = minutes & 255; reply[6] = minutes >> 8; reply[7] = state;
    uint64_t now = nowMs();
    uint32_t remaining = gate.enabled() && gate.deadline() > now ? (gate.deadline()-now+999)/1000 : 0;
    for (unsigned i = 0; i < 4; ++i) reply[8+i] = (remaining >> (8*i)) & 255;
}
}

void beeLinkBegin() {
    // L76K host RX=D7/GPIO44, TX=D6/GPIO43. No reset drive on D10/GPIO9.
    // GPIO1/D0 is reserved for GNSS wake; other capture pins stay unassigned.
    pinMode(D0, OUTPUT); digitalWrite(D0, HIGH);
    gnss.begin(9600, SERIAL_8N1, D7, D6);
}
void beeLinkVerifiedSoc(double percent, uint64_t capture_monotonic_ms) {
    snapshot.soc.value = percent;
    snapshot.soc.captured_ms = capture_monotonic_ms;
    snapshot.soc.verified = true;
    snapshot.soc.simulated = false;
}
size_t beeLinkCommand(const uint8_t* command, size_t length, uint8_t* reply) {
    if (!length || (command[0] != 0xE0 && command[0] != 0xE1)) return 0;
    if (command[0] == 0xE1 && length == 2 && command[1] == 1) { status(reply); return 12; }
    if (command[0] != 0xE0 || length != 8 || command[1] != 1 || command[2] > 1 || command[3] > 1 || command[7] > 1) {
        reply[0] = 1; reply[1] = 2; return 2;
    }
    unsigned new_minutes = command[5] | (unsigned(command[6]) << 8);
    ChannelDetails selected;
    if (new_minutes < 15 || new_minutes > 1440 || command[4] == 0 || command[4] >= MAX_GROUP_CHANNELS ||
        (command[2] && (command[7] != 1 || !privateChannel(command[4], selected)))) {
        reply[0] = 1; reply[1] = 2; return 2;
    }
    if (!gate.configure(command[2], new_minutes, nowMs(), jitter())) { reply[0] = 1; reply[1] = 2; return 2; }
    location = command[3]; channel_index = command[4]; minutes = new_minutes;
    if (command[2]) std::memcpy(expected_key, selected.channel.secret, 32);
    else std::memset(expected_key, 0, 32);
    state = gate.enabled() ? 1 : 0;
    status(reply); return 12;
}
void beeLinkLoop() {
    // Bounded UART work. No waits or filesystem operations in the radio path.
    for (unsigned count = 0; count < 256 && gnss.available(); ++count) gps.encode(gnss.read());
    const uint64_t now = nowMs();
    if (gps.location.isUpdated() && gps.location.isValid()) {
        snapshot.latitude.value = gps.location.lat(); snapshot.longitude.value = gps.location.lng();
        snapshot.latitude.captured_ms = snapshot.longitude.captured_ms = now - gps.location.age();
        snapshot.latitude.verified = snapshot.longitude.verified = true;
    }
    if (gps.speed.isUpdated() && gps.speed.isValid()) {
        snapshot.speed.value = gps.speed.kmph(); snapshot.speed.captured_ms = now - gps.speed.age(); snapshot.speed.verified = true;
    }
    if (gps.time.isUpdated() && gps.time.isValid() && gps.date.isValid() && gps.time.age() <= 1000 && gps.date.age() <= 1000) {
        uint32_t epoch = gpsEpoch();
        if (epoch) { utc_anchor = epoch; utc_anchor_ms = now-gps.time.age(); }
    }
    if (!gate.take(now, jitter())) return;
    snapshot.utc_valid = utc_anchor && now >= utc_anchor_ms && now-utc_anchor_ms <= 60000;
    snapshot.utc_seconds = utc_anchor + (now-utc_anchor_ms)/1000;
    char message[121];
    ChannelDetails selected;
    if (!privateChannel(channel_index, selected) || std::memcmp(expected_key, selected.channel.secret, 32) != 0) {
        gate.configure(false, minutes, now, 0); location = false; std::memset(expected_key, 0, 32); state = 4; return;
    }
    if (!beelink::format(snapshot, now, location, message)) { state = 2; return; }
    // Reuses upstream encrypted group text. Success is packet queuing, not delivery.
    state = the_mesh.sendGroupMessage(snapshot.utc_seconds, selected.channel, "Bee-Link", message, std::strlen(message)) ? 3 : 4;
}
