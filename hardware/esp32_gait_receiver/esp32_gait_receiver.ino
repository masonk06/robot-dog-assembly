// Supported robot prototype. USB 115200; servo UART GPIO16/17 at 1 Mbps.
// Commands: READ; LIMIT,id,min,max; ARM; GOAL,id,ticks; KEEP; STOP.
// LIVE telemetry includes position, target, voltage, temperature, motor load and current.
// Configuration is volatile. No movement on startup; no EEPROM writes.
#include <Arduino.h>
#include <string.h>
#include <stdlib.h>
#include <Wire.h>

HardwareSerial bus(2);
uint16_t lower[12] = {0}, upper[12] = {0}, lastGoal[12] = {0};
bool armed = false;
uint32_t lastCommand = 0;
constexpr uint32_t WATCHDOG_MS = 500;
constexpr int MAX_GOAL_DELTA = 20;
constexpr int MAX_TRACKING_ERROR = 100;
constexpr uint32_t TRACKING_GRACE_MS = 1000;
uint32_t lastMonitor = 0, badSince[12] = {0};
uint8_t monitorId = 1;
char line[128]; size_t used = 0; bool overflow = false;
uint8_t imuAddress = 0, imuIdentity = 0;
bool imuStreaming = false;
uint32_t lastImuStream = 0;

bool imuRead(uint8_t reg, uint8_t *data, size_t count) {
  Wire.beginTransmission(imuAddress); Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(imuAddress, count, true) != count) return false;
  for (size_t i = 0; i < count; ++i) data[i] = Wire.read();
  return true;
}
bool imuWrite(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(imuAddress); Wire.write(reg); Wire.write(value);
  return Wire.endTransmission(true) == 0;
}
void setupImu() {
  Wire.begin(21, 22, 100000); Wire.setTimeOut(5);
  for (uint8_t address : {uint8_t(0x68), uint8_t(0x69)}) {
    imuAddress = address; uint8_t id = 0;
    if (!imuRead(0x75, &id, 1) || (id != 0x68 && id != 0x70)) continue;
    imuIdentity = id;
    bool ok = imuWrite(0x6B, 0x01) && imuWrite(0x6C, 0x00);
    delay(100);
    ok = ok && imuWrite(0x1A, 0x03) && imuWrite(0x19, 0x09) &&
         imuWrite(0x1B, 0x08) && imuWrite(0x1C, 0x08);
    if (id == 0x70) ok = ok && imuWrite(0x1D, 0x03);
    if (!ok) imuIdentity = 0;
    break;
  }
  Serial.printf("IMU_STATUS,%s,0x%02X,0x%02X\n", imuIdentity ? "READY" : "UNAVAILABLE", imuAddress, imuIdentity);
}
int16_t imuWord(const uint8_t *data, int offset) {
  return int16_t((uint16_t(data[offset]) << 8) | data[offset+1]);
}
void reportImu() {
  if (!imuIdentity) { Serial.println("IMU_ERROR,UNAVAILABLE"); return; }
  uint8_t raw[14]; uint32_t stamp = micros();
  if (!imuRead(0x3B, raw, sizeof(raw))) { Serial.println("IMU_ERROR,READ_FAILED"); return; }
  constexpr float accel = 9.80665f / 8192.0f, gyro = (PI / 180.0f) / 65.5f;
  Serial.printf("IMU,%lu,%.4f,%.4f,%.4f,%.6f,%.6f,%.6f\n", (unsigned long)stamp,
    imuWord(raw,0)*accel, imuWord(raw,2)*accel, imuWord(raw,4)*accel,
    imuWord(raw,8)*gyro, imuWord(raw,10)*gyro, imuWord(raw,12)*gyro);
}

void packet(uint8_t id, uint8_t instruction, const uint8_t *params, size_t n) {
  uint8_t sum = id + uint8_t(n + 2) + instruction;
  bus.write(0xff); bus.write(0xff); bus.write(id); bus.write(uint8_t(n + 2)); bus.write(instruction);
  for (size_t i = 0; i < n; ++i) { bus.write(params[i]); sum += params[i]; }
  bus.write(uint8_t(~sum)); bus.flush();
}

bool response(uint8_t id, uint8_t *data, size_t count) {
  uint8_t frame[40]; size_t length = 0; uint32_t start = micros();
  while (uint32_t(micros() - start) < 12000) {
    if (!bus.available()) { delayMicroseconds(25); continue; }
    frame[length++] = uint8_t(bus.read());
    while (length >= 2 && (frame[0] != 255 || frame[1] != 255 ||
           (length >= 3 && frame[2] != id) || (length >= 4 && frame[3] != count + 2))) {
      memmove(frame, frame + 1, --length);
    }
    if (length == count + 6) {
      uint8_t sum = 0; for (size_t i = 2; i < length; ++i) sum += frame[i];
      if (sum == 255 && frame[4] == 0) { if (count) memcpy(data, frame + 5, count); return true; }
      memmove(frame, frame + 1, --length);
    }
  }
  return false;
}
void drain() { while (bus.available()) bus.read(); }
bool readRegs(uint8_t id, uint8_t address, uint8_t count, uint8_t *out) {
  drain(); uint8_t params[] = {address, count}; packet(id, 2, params, 2); return response(id, out, count);
}
bool writeRegs(uint8_t id, uint8_t address, const uint8_t *values, size_t count) {
  uint8_t params[10]; if (count > 9) return false;
  params[0] = address; memcpy(params + 1, values, count); drain();
  packet(id, 3, params, count + 1); return response(id, nullptr, 0);
}
void stopAll() {
  armed = false; bool ok = true;
  for (uint8_t id = 1; id <= 12; ++id) {
    uint8_t off = 0, actual = 1;
    writeRegs(id, 40, &off, 1);
    if (!readRegs(id, 40, 1, &actual) || actual != 0) ok = false;
  }
  Serial.println(ok ? "STOPPED,RELEASE_VERIFIED" : "STOPPED,RELEASE_UNCONFIRMED");
}
bool parseInt(const char *s, long &value) {
  if (!s || !*s) return false; char *end; value = strtol(s, &end, 10); return *end == 0;
}
int signedLoad(uint16_t raw) { return raw & 0x0400 ? -int(raw & 0x03ff) : int(raw & 0x03ff); }
int signedCurrent(uint16_t raw) { return raw & 0x8000 ? -int(raw & 0x7fff) : int(raw & 0x7fff); }
void arm() {
  if (armed) { Serial.println("ERR,ALREADY_ARMED"); return; }
  for (int i = 0; i < 12; ++i) if (lower[i] >= upper[i]) { Serial.println("ERR,LIMITS_NOT_CONFIGURED"); return; }
  for (uint8_t id = 1; id <= 12; ++id) {
    uint8_t data[31];
    if (!readRegs(id, 33, 31, data) || data[0] != 0 || data[7] != 0) { Serial.printf("ERR,READ_OR_MODE,%u\n", id); return; }
    int ticks = int(data[23]) | (int(data[24]) << 8);
    if (ticks < lower[id-1] || ticks > upper[id-1]) { Serial.printf("ERR,POSITION,%u\n", id); return; }
    lastGoal[id-1] = ticks;
    Serial.printf("STARTPOS,%u,%d\n", id, ticks);
  }
  for (uint8_t id = 1; id <= 12; ++id) {
    uint16_t ticks = lastGoal[id-1]; uint8_t goal[] = {uint8_t(ticks), uint8_t(ticks >> 8)};
    if (!writeRegs(id, 42, goal, 2)) { Serial.printf("ERR,PRELOAD,%u\n", id); stopAll(); return; }
  }
  for (uint8_t id = 1; id <= 12; ++id) {
    uint8_t on = 1;
    if (!writeRegs(id, 40, &on, 1)) { Serial.printf("ERR,ENABLE,%u\n", id); stopAll(); return; }
  }
  memset(badSince, 0, sizeof(badSince));
  armed = true; lastCommand = millis(); lastMonitor = millis(); Serial.println("ARMED");
}
void monitor() {
  // One servo every 10 ms: approximately 8 Hz per servo under ideal load.
  if (!armed || uint32_t(millis() - lastMonitor) < 10) return;
  lastMonitor = millis(); uint8_t id = monitorId;
  monitorId = id == 12 ? 1 : id + 1;
  // Read the contiguous live block through present-current at address 69.
  // These are read-only diagnostics; no servo configuration is changed.
  uint8_t data[15];
  if (!readRegs(id, 56, 15, data)) { Serial.printf("ERR,FEEDBACK,%u\n", id); stopAll(); return; }
  int ticks = int(data[0]) | (int(data[1]) << 8);
  if (ticks > 4095 || ticks < lower[id-1] || ticks > upper[id-1]) {
    Serial.printf("ERR,POSITION,%u,%d\n", id, ticks); stopAll(); return;
  }
  int error = ticks - int(lastGoal[id-1]);
  uint16_t loadRaw = uint16_t(data[4]) | (uint16_t(data[5]) << 8);
  uint16_t currentRaw = uint16_t(data[13]) | (uint16_t(data[14]) << 8);
  Serial.printf("LIVE,%u,%d,%u,%u,%u,%d,%d,%lu\n", id, ticks, lastGoal[id-1], data[6], data[7],
                signedLoad(loadRaw), signedCurrent(currentRaw), (unsigned long)micros());
  if (abs(error) > MAX_TRACKING_ERROR) {
    if (!badSince[id-1]) badSince[id-1] = millis();
    else if (uint32_t(millis() - badSince[id-1]) > TRACKING_GRACE_MS) {
      Serial.printf("ERR,TRACKING,%u,%d\n", id, error); stopAll();
    }
  } else badSince[id-1] = 0;
}
void handle(char *cmd) {
  char *context = nullptr; char *kind = strtok_r(cmd, ",", &context);
  if (!kind) return;
  if (!strcmp(kind, "PROFILE")) {
    if (armed) { Serial.println("ERR,PROFILE_WHILE_ARMED"); return; }
    for (uint8_t id = 1; id <= 12; ++id) {
      uint8_t data[7];
      if (!readRegs(id, 41, 7, data)) { Serial.printf("PROFILE_ERROR,%u\n", id); continue; }
      uint16_t speed = uint16_t(data[5]) | (uint16_t(data[6]) << 8);
      Serial.printf("PROFILE,%u,%u,%u\n", id, data[0], speed);
    }
    Serial.println("PROFILE_DONE"); return;
  }
  if (!strcmp(kind, "IMU")) { if (armed) { Serial.println("ERR,IMU_WHILE_ARMED"); return; } reportImu(); return; }
  if (!strcmp(kind, "IMUSTREAM")) {
    if (armed || !imuIdentity) { Serial.println("IMU_ERROR,STREAM_UNAVAILABLE"); return; }
    imuStreaming = true; Serial.println("OK,IMUSTREAM"); return;
  }
  if (!strcmp(kind, "IMUSTOP")) { imuStreaming = false; Serial.println("OK,IMUSTOP"); return; }
  if (!strcmp(kind, "READ")) {
    if (armed) { Serial.println("ERR,READ_WHILE_ARMED"); return; }
    for (uint8_t id = 1; id <= 12; ++id) {
      uint8_t data[31];
      if (!readRegs(id, 33, 31, data)) { Serial.printf("READ_ERROR,%u\n", id); continue; }
      uint16_t raw = uint16_t(data[23]) | (uint16_t(data[24]) << 8);
      int ticks = (raw & 0x8000) ? -int(raw & 0x7fff) : int(raw);
      Serial.printf("READ,%u,%d,%u,%u,%u,%u\n", id, ticks, data[7], data[0], data[29], data[30]);
    }
    Serial.println("READ_DONE"); return;
  }
  if (!strcmp(kind, "STOP")) { stopAll(); return; }
  if (!strcmp(kind, "ARM")) { arm(); return; }
  if (!strcmp(kind, "KEEP")) { if (armed) lastCommand = millis(); Serial.println(armed ? "OK,KEEP" : "ERR,NOT_ARMED"); return; }
  if (!strcmp(kind, "FRAME")) {
    uint16_t goals[12];
    for (int i = 0; i < 12; ++i) {
      long value; char *token = strtok_r(nullptr, ",", &context);
      if (!parseInt(token, value) || value < lower[i] || value > upper[i] || abs(value - int(lastGoal[i])) > MAX_GOAL_DELTA) {
        Serial.printf("ERR,FRAME,%d\n", i + 1); if (armed) stopAll(); return;
      }
      goals[i] = uint16_t(value);
    }
    if (!armed || strtok_r(nullptr, ",", &context)) { Serial.println("ERR,FRAME_STATE"); if (armed) stopAll(); return; }
    uint8_t params[38]; params[0] = 42; params[1] = 2;
    for (int i = 0; i < 12; ++i) {
      params[2 + i*3] = i+1; params[3 + i*3] = uint8_t(goals[i]); params[4 + i*3] = uint8_t(goals[i] >> 8);
    }
    drain(); packet(254, 0x83, params, sizeof(params));
    for (int i = 0; i < 12; ++i) lastGoal[i] = goals[i];
    lastCommand = millis(); Serial.println("OK,FRAME"); return;
  }
  long id, a, b; char *s1 = strtok_r(nullptr, ",", &context); char *s2 = strtok_r(nullptr, ",", &context);
  if (!parseInt(s1, id) || id < 1 || id > 12 || !parseInt(s2, a)) { Serial.println("ERR,ARGUMENTS"); return; }
  if (!strcmp(kind, "LIMIT")) {
    char *s3 = strtok_r(nullptr, ",", &context);
    if (armed || !parseInt(s3, b) || a < 0 || b > 4095 || a >= b || strtok_r(nullptr, ",", &context)) { Serial.println("ERR,LIMIT"); return; }
    lower[id-1] = a; upper[id-1] = b; Serial.printf("OK,LIMIT,%ld\n", id); return;
  }
  if (!strcmp(kind, "GOAL")) {
    if (!armed || strtok_r(nullptr, ",", &context) || a < lower[id-1] || a > upper[id-1] || abs(a - int(lastGoal[id-1])) > MAX_GOAL_DELTA) {
      Serial.println("ERR,GOAL_REJECTED"); if (armed) stopAll(); return;
    }
    uint8_t goal[] = {uint8_t(a), uint8_t(a >> 8)};
    if (!writeRegs(id, 42, goal, 2)) { Serial.printf("ERR,WRITE,%ld\n", id); stopAll(); return; }
    lastGoal[id-1] = a; lastCommand = millis(); Serial.printf("OK,GOAL,%ld,%ld\n", id, a); return;
  }
  Serial.println("ERR,UNKNOWN_COMMAND");
}
void setup() {
  Serial.begin(115200); bus.begin(1000000, SERIAL_8N1, 16, 17);
  setupImu();
  Serial.println("READY,DISARMED");
}
void loop() {
  while (Serial.available()) {
    char c = char(Serial.read());
    if (c == '\r' || c == '\n') {
      if (overflow) Serial.println("ERR,LINE_TOO_LONG"); else if (used) { line[used] = 0; handle(line); }
      used = 0; overflow = false;
    } else if (!overflow) { if (used < sizeof(line)-1) line[used++] = c; else overflow = true; }
  }
  if (armed && uint32_t(millis() - lastCommand) > WATCHDOG_MS) { Serial.println("ERR,WATCHDOG"); stopAll(); }
  monitor();
  if (imuStreaming && armed && uint32_t(millis() - lastImuStream) >= 50 && Serial.availableForWrite() >= 90) {
    lastImuStream = millis(); reportImu();
  }
}
