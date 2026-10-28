#include <string.h>
// Combined IMU + read-only STS3215 telemetry for NodeMCU-32S.
// Move SDA to GPIO 21 and SCL to GPIO 22 before use; GPIO 8/9 are flash pins.
#include <Arduino.h>
#include <Wire.h>

#if !defined(CONFIG_IDF_TARGET_ESP32)
#error "This sketch is configured for NodeMCU-32S (classic ESP32). Select that board."
#endif

constexpr int SDA_PIN = 21;
constexpr int SCL_PIN = 22;
constexpr uint32_t SAMPLE_INTERVAL_US = 10000;  // 100 Hz output.
uint8_t sensorAddress = 0;
bool sensorReady = false;
bool isMpu6500 = false;
const char *sensorName = "unknown";
uint32_t lastSampleUs = 0;
uint32_t sequenceNumber = 0;
uint32_t lastErrorMs = 0;


// Host USB remains 115200 baud. The separate servo UART uses 1 Mbps.
constexpr int SERVO_RX_PIN = 16;
constexpr int SERVO_TX_PIN = 17;
constexpr uint32_t SERVO_INTERVAL_US = 100000; // One ID per 100 ms: each ID ~1.2 s.
constexpr uint32_t SERVO_REPLY_TIMEOUT_US = 6000;
constexpr uint8_t SERVO_READ_START = 33;
constexpr uint8_t SERVO_READ_COUNT = 31; // Registers 33..63: mode, torque, position, V, temp.
HardwareSerial ServoBus(2);
enum class DisplayMode { Both, Imu, Servos };
DisplayMode displayMode = DisplayMode::Both;
uint32_t lastServoUs = 0;
uint8_t nextServoId = 1;
char commandBuffer[16];
size_t commandLength = 0;
bool commandOverflow = false;

bool showImu() { return displayMode != DisplayMode::Servos; }
bool showServos() { return displayMode != DisplayMode::Imu; }

void printHelp() {
  Serial.println("# Read-only: BOTH / IMU / SERVOS / HELP, then Enter.");
  Serial.println("# These commands change display output only; no motor commands are supported.");
  Serial.println("# servo,id,t_us,ticks,voltage_v,temp_c,torque_enabled,mode,status");
  Serial.println("# IDs are not assigned to physical legs by this sketch.");
}

void handleCommands() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r' || c == '\n') {
      if (commandOverflow) Serial.println("# Command too long; ignored.");
      else if (commandLength) {
        commandBuffer[commandLength] = '\0';
        if (!strcmp(commandBuffer, "BOTH")) displayMode = DisplayMode::Both;
        else if (!strcmp(commandBuffer, "IMU")) displayMode = DisplayMode::Imu;
        else if (!strcmp(commandBuffer, "SERVOS")) displayMode = DisplayMode::Servos;
        else if (strcmp(commandBuffer, "HELP")) Serial.println("# Unknown command; ignored.");
        printHelp();
      }
      commandLength = 0;
      commandOverflow = false;
    } else if (c != ' ' && c != '\t') {
      if (c >= 'a' && c <= 'z') c -= 'a' - 'A';
      if (commandLength < sizeof(commandBuffer) - 1) commandBuffer[commandLength++] = c;
      else commandOverflow = true;
    }
  }
}

bool readServoRegisters(uint8_t id, uint8_t *data, uint8_t &status) {
  while (ServoBus.available()) ServoBus.read();
  // The ONLY servo instruction emitted anywhere in this sketch is READ (0x02).
  uint8_t request[] = {0xFF, 0xFF, id, 4, 0x02, SERVO_READ_START, SERVO_READ_COUNT, 0};
  uint8_t sum = 0;
  for (size_t i = 2; i < sizeof(request) - 1; ++i) sum += request[i];
  request[sizeof(request) - 1] = static_cast<uint8_t>(~sum);
  ServoBus.write(request, sizeof(request));
  ServoBus.flush();
  uint8_t frame[SERVO_READ_COUNT + 6];
  size_t used = 0;
  uint32_t start = micros();
  while (static_cast<uint32_t>(micros() - start) < SERVO_REPLY_TIMEOUT_US) {
    if (!ServoBus.available()) { delayMicroseconds(25); continue; }
    frame[used++] = static_cast<uint8_t>(ServoBus.read());
    // Drop noise, request echoes, and replies for another ID before accepting a frame.
    while (used >= 2 && (frame[0] != 0xFF || frame[1] != 0xFF ||
           (used >= 3 && frame[2] != id) ||
           (used >= 4 && frame[3] != SERVO_READ_COUNT + 2))) {
      memmove(frame, frame + 1, --used);
    }
    if (used != sizeof(frame)) continue;
    uint8_t checksum = 0;
    for (size_t i = 2; i < used; ++i) checksum += frame[i];
    if (checksum == 0xFF) {
      status = frame[4];
      memcpy(data, frame + 5, SERVO_READ_COUNT);
      return true;
    }
    memmove(frame, frame + 1, --used);
  }
  return false;
}

void pollServo() {
  uint32_t now = micros();
  if (static_cast<uint32_t>(now - lastServoUs) < SERVO_INTERVAL_US) return;
  // Start just after an IMU sample so a missing servo has a bounded time budget.
  if (sensorReady && static_cast<uint32_t>(now - lastSampleUs) > 3000) return;
  lastServoUs = now;
  uint8_t id = nextServoId;
  nextServoId = nextServoId == 12 ? 1 : nextServoId + 1;
  uint8_t data[SERVO_READ_COUNT];
  uint8_t status = 0;
  if (!readServoRegisters(id, data, status)) {
    if (showServos()) Serial.printf("servo_error,%u,no_valid_response\n", id);
    return;
  }
  constexpr size_t POSITION = 56 - SERVO_READ_START;
  uint16_t raw = static_cast<uint16_t>(data[POSITION]) |
                 (static_cast<uint16_t>(data[POSITION + 1]) << 8);
  int ticks = (raw & 0x8000) ? -static_cast<int>(raw & 0x7FFF) : raw;
  if (showServos()) Serial.printf("servo,%u,%lu,%d,%.1f,%u,%u,%u,%u\n",
      id, static_cast<unsigned long>(micros()), ticks,
      data[62 - SERVO_READ_START] / 10.0f, data[63 - SERVO_READ_START],
      data[40 - SERVO_READ_START], data[33 - SERVO_READ_START], status);
}

bool readRegisters(uint8_t reg, uint8_t *buffer, size_t count) {
  Wire.beginTransmission(sensorAddress);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  size_t received = Wire.requestFrom(sensorAddress, count, true);
  if (received != count) {
    while (Wire.available()) Wire.read();
    return false;
  }
  for (size_t i = 0; i < count; ++i) buffer[i] = Wire.read();
  return true;
}

bool writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(sensorAddress);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission(true) == 0;
}

int16_t signedWord(const uint8_t *buffer, size_t offset) {
  return static_cast<int16_t>((static_cast<uint16_t>(buffer[offset]) << 8) |
                              buffer[offset + 1]);
}

void setupImu() {

  Serial.printf("# MPU6xxx sensor-only test v3; SDA=GPIO%d SCL=GPIO%d\n", SDA_PIN, SCL_PIN);
  if (!Wire.begin(SDA_PIN, SCL_PIN, 100000)) {
    Serial.println("ERR,I2C_INIT_FAILED");
    return;
  }
  Wire.setTimeOut(20);
  Serial.printf("# Idle bus levels: SDA=%d SCL=%d (normally both 1)\n", digitalRead(SDA_PIN), digitalRead(SCL_PIN));
  for (uint8_t candidate : {uint8_t(0x68), uint8_t(0x69)}) {
    sensorAddress = candidate;
    Wire.beginTransmission(sensorAddress);
    uint8_t status = Wire.endTransmission(true);
    Serial.printf("# Probe 0x%02X: status=%u (0=ACK, 2=no address response)\n", candidate, status);
    if (status != 0) continue;
    uint8_t identity = 0;
    if (!readRegisters(0x75, &identity, 1)) {
      Serial.println("ERR,WHO_AM_I_READ_FAILED");
      continue;
    }
    Serial.printf("# WHO_AM_I at 0x%02X = 0x%02X\n", candidate, identity);
    if (identity == 0x68 || identity == 0x70) {
      isMpu6500 = identity == 0x70;
      sensorName = isMpu6500 ? "MPU6500-compatible" : "MPU6050-compatible";
      sensorReady = true;
      break;
    }
  }
  if (!sensorReady) {
    unsigned found = 0;
    unsigned busErrors = 0;
    Serial.println("# Scanning I2C addresses 0x08..0x77");
    for (uint8_t address = 0x08; address <= 0x77; ++address) {
      Wire.beginTransmission(address);
      uint8_t status = Wire.endTransmission(true);
      if (status == 0) {
        Serial.printf("# I2C device ACK at 0x%02X\n", address);
        ++found;
      } else if (status != 2) {
        ++busErrors;
      }
    }
    Serial.printf("# Scan complete: devices=%u bus_errors=%u\n", found, busErrors);
    Serial.println(found ? "ERR,I2C_PRESENT_BUT_SUPPORTED_MPU_ID_NOT_VERIFIED" : "ERR,NO_I2C_DEVICES_DETECTED");
    return;
  }
  // Configure the sensor only: PLL clock, all axes active, low-pass filter,
  // 100 Hz sample rate, +/-500 deg/s gyro, +/-4 g accelerometer.
  sensorReady = writeRegister(0x6B, 0x01) && writeRegister(0x6C, 0x00);
  delay(100);
  sensorReady = sensorReady && writeRegister(0x1A, 0x03) &&
                writeRegister(0x19, 0x09) && writeRegister(0x1B, 0x08) &&
                writeRegister(0x1C, 0x08) && writeRegister(0x38, 0x01);
  // MPU6500 adds ACCEL_CONFIG2; use its filtered 1 kHz accel path before dividing.
  if (isMpu6500) sensorReady = sensorReady && writeRegister(0x1D, 0x03);
  for (uint8_t reg : {uint8_t(0x19), uint8_t(0x1A), uint8_t(0x1B), uint8_t(0x1C)}) {
    uint8_t actual = 0;
    uint8_t expected = reg == 0x19 ? 0x09 : reg == 0x1A ? 0x03 : 0x08;
    if (!readRegisters(reg, &actual, 1) || actual != expected) sensorReady = false;
  }
  if (isMpu6500) {
    uint8_t actual = 0;
    if (!readRegisters(0x1D, &actual, 1) || actual != 0x03) sensorReady = false;
  }
  if (!sensorReady) {
    Serial.println("ERR,MPU6050_CONFIGURATION_FAILED");
    return;
  }
  Serial.printf("# Profile=%s address=0x%02X; accel includes gravity; gyro is uncalibrated\n", sensorName, sensorAddress);
  Serial.println("# imu,t_us,seq,ax_m_s2,ay_m_s2,az_m_s2,gx_rad_s,gy_rad_s,gz_rad_s,temp_c");
}

void pollImu() {
  if (!sensorReady) {
    return;
  }
  uint32_t now = micros();
  if (static_cast<uint32_t>(now - lastSampleUs) < SAMPLE_INTERVAL_US) {
    delay(1);
    return;
  }
  lastSampleUs = now;
  uint8_t status = 0;
  uint8_t raw[14];
  if (!readRegisters(0x3A, &status, 1) ||
      ((status & 1) && !readRegisters(0x3B, raw, sizeof(raw)))) {
    if (millis() - lastErrorMs >= 1000) {
      Serial.println("ERR,IMU_READ_FAILED");
      lastErrorMs = millis();
    }
    return;
  }
  if (!(status & 1)) return;  // Never publish fabricated samples when data is stale.
  constexpr float ACCEL_SCALE = 9.80665f / 8192.0f;
  constexpr float GYRO_SCALE = (PI / 180.0f) / 65.5f;
  float temperature = isMpu6500 ? signedWord(raw, 6) / 333.87f + 21.0f
                               : signedWord(raw, 6) / 340.0f + 36.53f;
  if (showImu()) Serial.printf("imu,%lu,%lu,%.4f,%.4f,%.4f,%.6f,%.6f,%.6f,%.2f\n",
      static_cast<unsigned long>(now), static_cast<unsigned long>(sequenceNumber++),
      signedWord(raw, 0) * ACCEL_SCALE, signedWord(raw, 2) * ACCEL_SCALE,
      signedWord(raw, 4) * ACCEL_SCALE, signedWord(raw, 8) * GYRO_SCALE,
      signedWord(raw, 10) * GYRO_SCALE, signedWord(raw, 12) * GYRO_SCALE, temperature);
}


void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("# RoboDog IMU + servo telemetry v1 - servo READ instructions only");
  ServoBus.setRxBufferSize(256);
  ServoBus.begin(1000000, SERIAL_8N1, SERVO_RX_PIN, SERVO_TX_PIN);
  Serial.println("# Servo UART RX=GPIO16 TX=GPIO17; Waveshare UART jumpers=A");
  setupImu();
  printHelp();
}

void loop() {
  handleCommands();
  pollImu();
  pollServo();
  if (!sensorReady) delay(1);
}
