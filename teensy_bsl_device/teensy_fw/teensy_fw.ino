/*
  Define PINs and Serial Ports
*/
#define TEST_PIN 10
#define SRST_PIN 11
#define LED_PIN 13
#define TARGET_SERIAL Serial1

/*
  Lag for Entering BSL
*/
#define BSL_LAG_US 100

/*
  Baud Commands
*/
int baud_cmd[4] = {
  0x80,
  0x02,
  0x00,
  0x52
};

typedef enum{
  b9k6     = 0x01,
  b19k2    = 0x02,
  b38k4    = 0x03,
  b57k6    = 0x04,
  b115k2   = 0x05
}BaudRates_e;

void changeBaudrate(BaudRates_e baud_code){
  uint32_t baudRate = 9600;
  switch(baud_code){
    case b9k6:
      baudRate = 9600;
      break;

    case b19k2:
      baudRate = 19200;
      break;

    case b38k4:
      baudRate = 38400;
      break;

    case b57k6:
      baudRate = 57600;
      break;

    case b115k2:
      baudRate = 115200;
      break;
  }
  // wait
  delay(5);
  // close serials
  TARGET_SERIAL.end();
  Serial.end();
  // reopen
  TARGET_SERIAL.begin(baudRate, SERIAL_8E1);
  Serial.begin(baudRate);
}

/*
  BSL Entering Sequence
*/
void enterBSL(){
  /* configure pinmodes for bsl entry */
  pinMode(TEST_PIN, OUTPUT);
  pinMode(SRST_PIN, OUTPUT);
  /* pull msp430 into reset */
  digitalWrite(SRST_PIN, LOW);
  digitalWrite(TEST_PIN, LOW);
  /* create edges */
  for(uint32_t i = 0; i<2; i++){
      digitalWrite(TEST_PIN, LOW);
      delayMicroseconds(BSL_LAG_US);
      digitalWrite(TEST_PIN, HIGH);
      delayMicroseconds(BSL_LAG_US);
  }
  /* release reset */
  digitalWrite(SRST_PIN, HIGH);
  digitalWrite(TEST_PIN, LOW);
}

/*
  Main Program
*/

void setup() {
  /* setup serial ports */
  Serial.begin(9600);
  TARGET_SERIAL.begin(9600, SERIAL_8E1);
  while(!Serial);
  // check on detailed bsl serial settings
  /* enter bsl */
  enterBSL();
  /* setup led */
  pinMode(LED_PIN, OUTPUT);
}

static bool led_on = false;
static uint32_t led_count = 5e5;

static uint32_t baud_cmd_blocks_seen = 0;
static bool change_baud = false;
static BaudRates_e new_baud = b9k6;

void loop() {
  /* 
    forward serial data 
  */
  if (Serial.available() > 0) {
    int byte_ = Serial.read();
    TARGET_SERIAL.write(byte_);
    /*
       Listen for through comming baud rate change command
    */
    if(baud_cmd_blocks_seen > 3){
      if(baud_cmd_blocks_seen == 4){
        new_baud = (BaudRates_e)byte_;
      }else if(baud_cmd_blocks_seen == 6){
        change_baud = true;
        baud_cmd_blocks_seen = 0;
      }
      baud_cmd_blocks_seen++;
      
    }else if(byte_ == baud_cmd[baud_cmd_blocks_seen]){
      // start counting
      baud_cmd_blocks_seen++;
     
    }else{
      // reset counting if not seen
      baud_cmd_blocks_seen = 0;
    }
    
  }

  if (TARGET_SERIAL.available() > 0) {
    Serial.write(TARGET_SERIAL.read());
  }

  /*
    Change BaudRates
  */
  if (change_baud){
    changeBaudrate(new_baud);
    change_baud = false;  
    baud_cmd_blocks_seen = 0;
  }
  
  /*
    Trigger LED
  */
  if(led_count){
    led_count--;  
  }else{
    if(led_on){
      digitalWrite(LED_PIN, LOW);
      led_on = false;
    }else{
      digitalWrite(LED_PIN, HIGH);
      led_on = true;
    }
    led_count = 5e5;
  }
}
