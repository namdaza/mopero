// =============================================================================
// ARDUINO MOTOR CONTROLLER - Differential Drive Robot
// =============================================================================
// Hardware:
//   - Arduino Uno R3
//   - 2x BTS7960 Motor Driver
//   - 2x DC Motor 12V, 23 RPM (with encoder)
//   - Communicates với ROS 2 node trên Jetson Nano qua USB Serial
//
// Serial Protocol:
//   - NHẬN từ Jetson: "CMD,<left_rpm>,<right_rpm>\n"
//       Ví dụ: "CMD,15.0,-15.0\n"  → trái 15 RPM, phải -15 RPM (quay tại chỗ)
//   - GỬI lên Jetson:  "ENC,<left_ticks>,<right_ticks>,<left_rpm>,<right_rpm>\n"
//       Ví dụ: "ENC,1024,-1024,14.8,-14.8\n"
// =============================================================================

// --- CẤU HÌNH ENCODER ---
// Số xung encoder mỗi vòng (tính cả 2 cạnh của kênh A). 
// Đo thực tế: quay tay 1 vòng rồi đọc Serial xem left_ticks thay đổi bao nhiêu.
#define TICKS_PER_REV        4300   // Đo thực tế: ~4300 ticks/vòng (trái=4300, phải=4301)

// --- CẤU HÌNH PID ---
// Bắt đầu với Kp nhỏ, Ki=0, Kd=0, tăng dần khi test thực tế
#define KP                   8.0
#define KI                   3.0
#define KD                   0.5
#define PID_INTERVAL_MS      100    // Tính PID mỗi 100ms

// --- CẤU HÌNH MOTOR ---
#define MAX_RPM              25.0   // RPM tối đa thực tế
#define MIN_PWM              60     // Tăng từ 40->60 để thắng ma sát tĩnh, chống giật lúc chớm chạy
#define MAX_PWM              255
#define SERIAL_TIMEOUT_MS    3000   // Tăng lên 3000ms (3s) để bạn kịp nhìn khi test bằng tay

// --- CHÂN KẾT NỐI ---
// Encoder Bánh Trái
const int ENC_L_A = 2;  // INT0 - Hardware Interrupt
const int ENC_L_B = 4;

// Encoder Bánh Phải
const int ENC_R_A = 3;  // INT1 - Hardware Interrupt
const int ENC_R_B = 7;

// BTS7960 Bánh Trái (LPWM=forward, RPWM=backward)
const int L_LPWM = 5;
const int L_RPWM = 6;

// BTS7960 Bánh Phải (LPWM=forward, RPWM=backward)
const int R_LPWM = 9;
const int R_RPWM = 10;

// =============================================================================
// BIẾN TOÀN CỤC (volatile vì được dùng trong ISR)
// =============================================================================
volatile long left_ticks  = 0;
volatile long right_ticks = 0;

// Tốc độ mục tiêu (RPM) nhận từ ROS
float target_left_rpm  = 0.0;
float target_right_rpm = 0.0;

// Tốc độ hiện tại đo được (RPM)
float current_left_rpm  = 0.0;
float current_right_rpm = 0.0;

// Biến PID bánh trái
float pid_l_integral   = 0.0;
float pid_l_prev_error = 0.0;
int   pwm_left_output  = 0;

// Biến PID bánh phải
float pid_r_integral   = 0.0;
float pid_r_prev_error = 0.0;
int   pwm_right_output = 0;

// Timing
unsigned long last_pid_time    = 0;
unsigned long last_cmd_time    = 0;
long          prev_left_ticks  = 0;
long          prev_right_ticks = 0;

// Buffer đọc Serial
String serial_buffer = "";

// =============================================================================
// INTERRUPT SERVICE ROUTINES - Đọc encoder (Quadrature, kênh A)
// =============================================================================
void encoderLeftISR() {
  // Đã đảo ngược đếm dể đồng bộ pha với chiều quay tiến (+)
  if (digitalRead(ENC_L_B) == HIGH) {
    left_ticks--;
  } else {
    left_ticks++;
  }
}

void encoderRightISR() {
  if (digitalRead(ENC_R_B) == HIGH) {
    right_ticks++;
  } else {
    right_ticks--;
  }
}

// =============================================================================
// ĐIỀU KHIỂN MOTOR QUA BTS7960
// Tham số: speed = -255 đến 255
//   > 0 → tiến (LPWM hoạt động)
//   < 0 → lùi (RPWM hoạt động)
//   = 0 → dừng
// =============================================================================
void setMotorLeft(int speed) {
  speed = constrain(speed, -MAX_PWM, MAX_PWM);
  if (speed > 0) {
    analogWrite(L_LPWM, speed);
    analogWrite(L_RPWM, 0);
  } else if (speed < 0) {
    analogWrite(L_LPWM, 0);
    analogWrite(L_RPWM, -speed);
  } else {
    analogWrite(L_LPWM, 0);
    analogWrite(L_RPWM, 0);
  }
}

void setMotorRight(int speed) {
  speed = constrain(speed, -MAX_PWM, MAX_PWM);
  if (speed > 0) {
    analogWrite(R_LPWM, speed);
    analogWrite(R_RPWM, 0);
  } else if (speed < 0) {
    analogWrite(R_LPWM, 0);
    analogWrite(R_RPWM, -speed);
  } else {
    analogWrite(R_LPWM, 0);
    analogWrite(R_RPWM, 0);
  }
}

void stopMotors() {
  setMotorLeft(0);
  setMotorRight(0);
}

// =============================================================================
// TÍNH TOÁN PID
// =============================================================================
// Áp dụng bù trừ vùng chết (Deadband) và giới hạn PWM 0-255
int formatPWM(float pwm_val) {
  if (abs(pwm_val) < 1.0 && abs(target_left_rpm) < 0.1 && abs(target_right_rpm) < 0.1) return 0; // Để an toàn
  
  int pwm_out = (int)abs(pwm_val);
  if (pwm_out > 0 && pwm_out < MIN_PWM) pwm_out = MIN_PWM; // Ép ma sát tĩnh
  if (pwm_out > MAX_PWM) pwm_out = MAX_PWM;
  
  return (pwm_val > 0) ? pwm_out : -pwm_out;
}

void computePID(float dt_s) {
  // --- Bánh Trái ---
  float error_l    = target_left_rpm - current_left_rpm;
  pid_l_integral  += error_l * dt_s;
  pid_l_integral   = constrain(pid_l_integral, -100.0, 100.0);  // Giới hạn để không tích luỹ rác
  float derivative_l = (error_l - pid_l_prev_error) / dt_s;
  
  // Cốt lõi: Feed-Forward (Dự đoán mức PWM) + Căn chỉnh PID
  float ff_l = (target_left_rpm / MAX_RPM) * 255.0; 
  float output_l = ff_l + (KP * error_l) + (KI * pid_l_integral) + (KD * derivative_l);
  pid_l_prev_error = error_l;

  // --- Bánh Phải ---
  float error_r    = target_right_rpm - current_right_rpm;
  pid_r_integral  += error_r * dt_s;
  pid_r_integral   = constrain(pid_r_integral, -100.0, 100.0);
  float derivative_r = (error_r - pid_r_prev_error) / dt_s;
  
  float ff_r = (target_right_rpm / MAX_RPM) * 255.0;
  float output_r = ff_r + (KP * error_r) + (KI * pid_r_integral) + (KD * derivative_r);
  pid_r_prev_error = error_r;

  // Áp dụng chống vấp và giới hạn
  if(target_left_rpm == 0) output_l = 0;
  if(target_right_rpm == 0) output_r = 0;

  int pwm_left_output  = formatPWM(output_l);
  int pwm_right_output = formatPWM(output_r);

  setMotorLeft(pwm_left_output);
  setMotorRight(pwm_right_output);
}

// =============================================================================
// ĐO TỐC ĐỘ THỰC TẾ TỪ ENCODER
// =============================================================================
void updateCurrentRPM(float dt_s) {
  // Đọc và reset ticks trong interval
  long cur_left, cur_right;
  
  noInterrupts();
  cur_left  = left_ticks;
  cur_right = right_ticks;
  interrupts();

  long delta_left  = cur_left  - prev_left_ticks;
  long delta_right = cur_right - prev_right_ticks;

  prev_left_ticks  = cur_left;
  prev_right_ticks = cur_right;

  // Tính RPM: (ticks_trong_interval / ticks_per_rev) * (60 / dt_s)
  current_left_rpm  = ((float)delta_left  / TICKS_PER_REV) * (60.0 / dt_s);
  current_right_rpm = ((float)delta_right / TICKS_PER_REV) * (60.0 / dt_s);
}

// =============================================================================
// PHÂN TÍCH LỆNH SERIAL
// Format nhận: "CMD,<left_rpm>,<right_rpm>\n"
// Format đặc biệt:
//   "STOP\n"          → dừng khẩn cấp
//   "PID,<kp>,<ki>,<kd>\n" → cập nhật tham số PID tại runtime
// =============================================================================
float kp = KP, ki = KI, kd = KD;  // Có thể cập nhật runtime

bool is_pwm_mode = false;  // Flag cờ đánh dấu đang test PWM

void parseSerial(String &line) {
  line.trim();
  last_cmd_time = millis();

  if (line.startsWith("CMD,")) {
    is_pwm_mode = false; // Trở lại chế độ PID
    int comma1 = line.indexOf(',');
    int comma2 = line.indexOf(',', comma1 + 1);
    if (comma1 > 0 && comma2 > 0) {
      target_left_rpm  = line.substring(comma1 + 1, comma2).toFloat();
      target_right_rpm = line.substring(comma2 + 1).toFloat();
      target_left_rpm  = constrain(target_left_rpm,  -MAX_RPM, MAX_RPM);
      target_right_rpm = constrain(target_right_rpm, -MAX_RPM, MAX_RPM);
    }
  }
  else if (line.startsWith("PWM,")) {
    is_pwm_mode = true;  // Tắt hẳn sự can thiệp của PID
    int comma1 = line.indexOf(',');
    int comma2 = line.indexOf(',', comma1 + 1);
    if (comma1 > 0 && comma2 > 0) {
      int pwm_l = line.substring(comma1 + 1, comma2).toInt();
      int pwm_r = line.substring(comma2 + 1).toInt();
      setMotorLeft(pwm_l);
      setMotorRight(pwm_r);
      Serial.print("TEST_PWM_ACK,"); Serial.print(pwm_l); Serial.print(","); Serial.println(pwm_r);
    }
  }
  else if (line == "STOP") {
    is_pwm_mode = false;
    target_left_rpm  = 0;
    target_right_rpm = 0;
    pid_l_integral   = 0;
    pid_r_integral   = 0;
    stopMotors();
  }
  else if (line.startsWith("PID,")) {
    // Ví dụ: "PID,8.0,3.0,0.5" → cập nhật Kp, Ki, Kd tại chỗ không cần nạp lại code
    int c1 = line.indexOf(',');
    int c2 = line.indexOf(',', c1 + 1);
    int c3 = line.indexOf(',', c2 + 1);
    if (c1 > 0 && c2 > 0 && c3 > 0) {
      kp = line.substring(c1 + 1, c2).toFloat();
      ki = line.substring(c2 + 1, c3).toFloat();
      kd = line.substring(c3 + 1).toFloat();
      Serial.print("PID_ACK,");
      Serial.print(kp); Serial.print(",");
      Serial.print(ki); Serial.print(",");
      Serial.println(kd);
    }
  }
  else if (line == "PING") {
    Serial.println("PONG");
  }
  else if (line == "TICKS_RESET") {
    noInterrupts();
    left_ticks = right_ticks = 0;
    interrupts();
    prev_left_ticks = prev_right_ticks = 0;
    Serial.println("TICKS_RESET_OK");
  }
}

// =============================================================================
// SETUP
// =============================================================================
void setup() {
  Serial.begin(115200);

  // Cấu hình chân motor là OUTPUT
  pinMode(L_LPWM, OUTPUT);
  pinMode(L_RPWM, OUTPUT);
  pinMode(R_LPWM, OUTPUT);
  pinMode(R_RPWM, OUTPUT);
  stopMotors();

  // Cấu hình chân encoder
  pinMode(ENC_L_A, INPUT_PULLUP);
  pinMode(ENC_L_B, INPUT_PULLUP);
  pinMode(ENC_R_A, INPUT_PULLUP);
  pinMode(ENC_R_B, INPUT_PULLUP);

  // Gắn interrupt cho kênh A của mỗi encoder (RISING edge)
  attachInterrupt(digitalPinToInterrupt(ENC_L_A), encoderLeftISR, RISING);
  attachInterrupt(digitalPinToInterrupt(ENC_R_A), encoderRightISR, RISING);

  last_pid_time  = millis();
  last_cmd_time  = millis();

  Serial.println("MOTOR_CONTROLLER_READY");
  Serial.println("Protocol: CMD,<left_rpm>,<right_rpm>");
}

// =============================================================================
// MAIN LOOP
// =============================================================================
void loop() {
  // --- Đọc Serial ---
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      parseSerial(serial_buffer);
      serial_buffer = "";
    } else {
      serial_buffer += c;
      if (serial_buffer.length() > 64) serial_buffer = "";  // Chống tràn buffer
    }
  }

  // --- Safety: Dừng motor nếu mất kết nối với ROS ---
  if (millis() - last_cmd_time > SERIAL_TIMEOUT_MS) {
    target_left_rpm  = 0;
    target_right_rpm = 0;
    pid_l_integral   = 0;
    pid_r_integral   = 0;
    stopMotors();
  }

  // --- Vòng PID chạy theo chu kỳ cố định ---
  unsigned long now = millis();
  if (now - last_pid_time >= PID_INTERVAL_MS) {
    float dt_s = (now - last_pid_time) / 1000.0;
    last_pid_time = now;

    // 1. Đo tốc độ thực tế
    updateCurrentRPM(dt_s);

    // 2. Tính và áp dụng PID (bỏ qua nếu mục tiêu = 0 hoặc đang test PWM)
    if (!is_pwm_mode) {
      if (abs(target_left_rpm) < 0.1 && abs(target_right_rpm) < 0.1) {
        // Đặt mục tiêu 0 → dừng hẳn, reset integral
        stopMotors();
        pid_l_integral = pid_l_prev_error = 0;
        pid_r_integral = pid_r_prev_error = 0;
      } else {
        computePID(dt_s);
      }
    }

    // 3. Gửi dữ liệu encoder lên Jetson
    // Format: "ENC,<left_ticks>,<right_ticks>,<left_rpm>,<right_rpm>"
    noInterrupts();
    long lt = left_ticks;
    long rt = right_ticks;
    interrupts();

    Serial.print("ENC,");
    Serial.print(lt);          Serial.print(",");
    Serial.print(rt);          Serial.print(",");
    Serial.print(current_left_rpm,  2); Serial.print(",");
    Serial.println(current_right_rpm, 2);
  }
}
