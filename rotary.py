from machine import Pin
import time

class Rotary:
    def __init__(self, dt, clk, sw):
        self.dt_pin = Pin(dt, Pin.IN, Pin.PULL_UP)
        self.clk_pin = Pin(clk, Pin.IN, Pin.PULL_UP)
        self.sw_pin = Pin(sw, Pin.IN, Pin.PULL_UP)
        
        self.val_prev = 0
        self.val_new = 0
        self.last_status = 0
        self.handlers = []
        self.last_button_press = 0
        
        # Nastavení přerušení (IRQ) pro detekci otáčení
        self.dt_pin.irq(handler=self.rotary_change, trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING)
        self.clk_pin.irq(handler=self.rotary_change, trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING)
        # Přerušení pro tlačítko
        self.sw_pin.irq(handler=self.button_press, trigger=Pin.IRQ_FALLING)

    def rotary_change(self, pin):
        val_new = self.clk_pin.value()
        val_dt = self.dt_pin.value()
        status = (val_new << 1) | val_dt
        
        # Detekce směru
        if self.last_status != status:
            if (self.last_status == 3) and (status == 2):
                self.call_handlers(1) # Vpravo
            elif (self.last_status == 3) and (status == 1):
                self.call_handlers(-1) # Vlevo
            self.last_status = status

    def button_press(self, pin):
        # Debouncing (ošetření zákmytů tlačítka) - min 250ms mezi stisky
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_button_press) > 250:
            self.last_button_press = now
            self.call_handlers(0) # 0 = Tlačítko stisknuto

    def add_handler(self, handler):
        self.handlers.append(handler)

    def call_handlers(self, direction):
        for handler in self.handlers:
            handler(direction)