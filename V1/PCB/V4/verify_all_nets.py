import pcbnew

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")
all_nets = {str(k) for k in b.GetNetsByName().keys()} - {''}
print(f"Total nets in board: {len(all_nets)}")

categorized = [
    # 1. Ground
    'GND', 'PGND',
    # 2. Power trunks
    '+6V', 'V_SERVO', 'V_UBEC', '+6V_BUCK', 'VMOT', 'M1_OUT1', 'M1_OUT2', 'M2_OUT1', 'M2_OUT2',
    'VBAT_RAW', 'VBAT', 'VBUS', 'VBAT_LOGIC', 'LOG_SW', '+3V3_PRE', '+3V3',
    # 3. High-speed USB & CC
    'USB_D+', 'USB_D-', 'CC1', 'CC2',
    # 4. Local IC & strapping nets
    'CPH1', 'CPL1', 'CPH2', 'CPL2', 'VCP1', 'VCP2', 'IPROPI1', 'IPROPI2',
    'SRV_BOOT', 'SRV_PH', 'SRV_EN', 'SRV_RT', 'FB_SERVO', 'SRV_COMP', 'COMP_NODE',
    'LOG_BOOT', 'LOG_EN', 'FB_3V3', 'BST', 'CHG_LX', 'VSET', 'ISET', 'NTC',
    'CHG_STAT', 'CHG_LED', 'D_STAT_A', 'D_CHG_A', 'GATE_PROT', 'VBATM', 'BOOT', 'ESP_EN',
    # 5. Servo FB channels
    'SERVO1_FB', 'SERVO2_FB', 'SERVO3_FB', 'SERVO4_FB', 'SERVO5_FB', 'SERVO6_FB',
    'SRV1_FB_IN', 'SRV2_FB_IN', 'SRV3_FB_IN', 'SRV4_FB_IN', 'SRV5_FB_IN', 'SRV6_FB_IN',
    # 6. Servo PWM channels
    'SERVO1_PWM', 'SERVO2_PWM', 'SERVO3_PWM', 'SERVO4_PWM', 'SERVO5_PWM', 'SERVO6_PWM',
    'SRV1_PWM_OUT', 'SRV2_PWM_OUT', 'SRV3_PWM_OUT', 'SRV4_PWM_OUT', 'SRV5_PWM_OUT', 'SRV6_PWM_OUT',
    # 7. Motor control
    'M1_IN1', 'M1_IN2', 'M2_IN1', 'M2_IN2', 'M1_SLEEP', 'M2_SLEEP', 'M1_FAULT', 'M2_FAULT',
    # 8. Encoders
    'ENC1_A_RAW', 'ENC1_B_RAW', 'M1_ENC_A', 'M1_ENC_B',
    'ENC2_A_RAW', 'ENC2_B_RAW', 'M2_ENC_A', 'M2_ENC_B',
    # 9. Buses
    'SPI1_SCK', 'SPI1_MOSI', 'SPI1_MISO', 'SPI1_CS',
    'SPI2_SCK', 'SPI2_MOSI', 'SPI2_MISO', 'SPI2_CS',
    'I2C_SCL', 'I2C_SDA', 'IMU_INT', 'UART0_RXD', 'UART0_TXD'
]

cat_set = set(categorized)
print(f"Total categorized nets: {len(cat_set)}")
diff = all_nets - cat_set
print(f"Uncategorized nets: {diff}")
extra = cat_set - all_nets
print(f"Extra categorized nets: {extra}")
