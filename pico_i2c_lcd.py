import machine
from time import sleep_ms

class I2cLcd:
    def __init__(self, i2c, i2c_addr, num_lines, num_columns):
        self.i2c = i2c
        self.i2c_addr = i2c_addr
        self.i2c.writeto(self.i2c_addr, bytes([0]))
        self.i2c.writeto(self.i2c_addr, bytes([0]))
        sleep_ms(20)
        # Inicializace pro 4-bit mode
        self.hal_write_init_nibble(0x03)
        self.hal_write_init_nibble(0x03)
        self.hal_write_init_nibble(0x03)
        self.hal_write_init_nibble(0x02)

        self.backlight = True
        self.display_off = False
        self.backlight_val = 0x08
        self.num_lines = num_lines
        self.num_columns = num_columns
        
        # Konstanty příkazů
        self.LCD_OPT = 0x28
        self.LCD_CMD = 0
        self.LCD_CHR = 1
        
        self.hal_write_command(self.LCD_OPT) # Function set
        self.hal_write_command(0x0C) # Display On
        self.hal_write_command(0x06) # Entry Mode
        self.clear()

    def hal_write_init_nibble(self, nibble):
        byte = nibble << 4 | 0x08 # 0x08 je podsvícení
        self.i2c.writeto(self.i2c_addr, bytes([byte | 0x04]))
        sleep_ms(1)
        self.i2c.writeto(self.i2c_addr, bytes([byte & ~0x04]))
        sleep_ms(1)

    def hal_backlight_on(self):
        self.backlight_val = 0x08
        self.hal_write_command(0)

    def hal_backlight_off(self):
        self.backlight_val = 0x00
        self.hal_write_command(0)

    def hal_write_command(self, cmd):
        self.hal_write_byte(cmd, 0)

    def hal_write_data(self, data):
        self.hal_write_byte(data, 1)

    def hal_write_byte(self, data, mode):
        high = mode | (data & 0xF0) | self.backlight_val
        low = mode | ((data << 4) & 0xF0) | self.backlight_val
        self.i2c.writeto(self.i2c_addr, bytes([high | 0x04]))
        self.i2c.writeto(self.i2c_addr, bytes([high & ~0x04]))
        self.i2c.writeto(self.i2c_addr, bytes([low | 0x04]))
        self.i2c.writeto(self.i2c_addr, bytes([low & ~0x04]))

    def clear(self):
        self.hal_write_command(0x01)
        sleep_ms(2)

    def move_to(self, cursor_x, cursor_y):
        addr = cursor_x & 0x3F
        if cursor_y & 1:
            addr += 0x40    # Lines 1 & 3 add 0x40
        if cursor_y & 2:    # Lines 2 & 3 add number of columns
            addr += self.num_columns
        self.hal_write_command(0x80 | addr)

    def putstr(self, string):
        for char in string:
            self.hal_write_data(ord(char))