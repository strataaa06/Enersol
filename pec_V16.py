import machine, time
from pico_i2c_lcd import I2cLcd
from max6675 import MAX6675
from rotary import Rotary

# --- 1. DEFINICE PINŮ ---

# Displej (I2C)
I2C_SDA = 0
I2C_SCL = 1

# Senzor (SPI)
TC_SCK = 2
TC_CS  = 3
TC_SO  = 4

# Enkodér
ENC_DT  = 6
ENC_CLK = 7
ENC_SW_DUMMY = 8 # NENÍ ZAPOJEN

# Tlačítka
PIN_BTN_START = 11   # Zelené
PIN_BTN_STOP  = 12   # Červené
PIN_BTN_MODE  = 13   # Modré

# Výstupy (POUZE 1 OKRUH)
PIN_RELAY = 16       # Spíná obě trubice najednou
PIN_LED   = 17       # Signalizace topení

# --- 2. INICIALIZACE HW ---

# Displej
i2c = machine.I2C(0, sda=machine.Pin(I2C_SDA), scl=machine.Pin(I2C_SCL), freq=400000)
try:
    lcd = I2cLcd(i2c, i2c.scan()[0], 4, 20)
except:
    # Nouzovka bez displeje
    led = machine.Pin(25, machine.Pin.OUT)
    while True: led.toggle(); time.sleep(0.1)

# Senzor
spi = machine.SPI(0, baudrate=1000000, sck=machine.Pin(TC_SCK), miso=machine.Pin(TC_SO))
sensor = MAX6675(spi, machine.Pin(TC_CS, machine.Pin.OUT))

# Nastavení výstupů
relay = machine.Pin(PIN_RELAY, machine.Pin.OUT)
led   = machine.Pin(PIN_LED, machine.Pin.OUT)

# Nastavení tlačítek
btn_mode  = machine.Pin(PIN_BTN_MODE, machine.Pin.IN, machine.Pin.PULL_UP)
btn_start = machine.Pin(PIN_BTN_START, machine.Pin.IN, machine.Pin.PULL_UP)
btn_stop  = machine.Pin(PIN_BTN_STOP, machine.Pin.IN, machine.Pin.PULL_UP)

# Proměnné pro odrušení tlačítek
cas_posledniho_stisku_mode = 0
cas_posledniho_stisku_start = 0
cas_posledniho_stisku_stop = 0

# --- 3. PROMĚNNÉ PROCESU ---

# Stavy
ST_SETUP       = 0 
ST_PREHEAT     = 1 
ST_SOAK        = 2 
ST_REFLOW_RAMP = 3 
ST_REFLOW_HOLD = 4 
ST_COOLING     = 5 
ST_DONE        = 6 

aktualni_stav = ST_SETUP

# Profil (Výchozí hodnoty)
teplota_soak   = 150    
cas_soak       = 120     
teplota_reflow = 230    
cas_reflow     = 15     

# Ostatní
kurzor_nastaveni = 0       
aktualni_teplota = 0.0
zacatek_odpoctu = 0        
hystereze = 2.0       
posledni_kontrola_casu = 0          

# --- 4. FUNKCE ---

def zapni_topeni(zapnuto):
    """
    Spíná jedno relé (pro obě trubice) a jednu LED.
    1 = Zapnuto, 0 = Vypnuto
    """
    if zapnuto:
        relay.value(1)
        led.value(1)
    else:
        relay.value(0)
        led.value(0)

# Obsluha enkodéru
def rot_handler(direction):
    global teplota_soak, cas_soak, teplota_reflow, cas_reflow
    
    if aktualni_stav != ST_SETUP or direction == 0: return
    
    if kurzor_nastaveni == 0:   # Soak Teplota
        teplota_soak = max(20, min(200, teplota_soak + direction * 5))
    elif kurzor_nastaveni == 1: # Soak Čas
        cas_soak = max(10, min(300, cas_soak + direction * 5))
    elif kurzor_nastaveni == 2: # Reflow Teplota
        teplota_reflow = max(20, min(350, teplota_reflow + direction * 5))
    elif kurzor_nastaveni == 3: # Reflow Čas
        cas_reflow = max(10, min(120, cas_reflow + direction * 5))

rot = Rotary(ENC_DT, ENC_CLK, ENC_SW_DUMMY)
rot.add_handler(rot_handler)

def aktualizuj_displej():
    t_str = f"{aktualni_teplota:>5.1f}"
    
    if aktualni_stav == ST_SETUP:
        s1 = ">" if kurzor_nastaveni == 0 else " "
        s2 = ">" if kurzor_nastaveni == 1 else " "
        s3 = ">" if kurzor_nastaveni == 2 else " "
        s4 = ">" if kurzor_nastaveni == 3 else " "
        
        lcd.move_to(0, 0); lcd.putstr("NASTAVENI PROFILU:  ")
        lcd.move_to(0, 1); lcd.putstr(f"Soak:{s1}{teplota_soak:<3}{chr(223)} {s2}{cas_soak:<3}s    ")
        lcd.move_to(0, 2); lcd.putstr(f"Refl:{s3}{teplota_reflow:<3}{chr(223)} {s4}{cas_reflow:<3}s    ")
        lcd.move_to(0, 3); lcd.putstr("Modr:VYBER Zel:START")

    else:
        nazev_faze = ""
        if aktualni_stav == ST_PREHEAT:     nazev_faze = "1.PREDEHREV (Ramp) "
        elif aktualni_stav == ST_SOAK:      nazev_faze = "2.NAMACENI (Soak) "
        elif aktualni_stav == ST_REFLOW_RAMP: nazev_faze = "3.REFLOW (Peak...)  "
        elif aktualni_stav == ST_REFLOW_HOLD: nazev_faze = "4.REFLOW (Hold)      "
        elif aktualni_stav == ST_COOLING:   nazev_faze = "5.CHLAZENI (Cool)    "
        elif aktualni_stav == ST_DONE:      nazev_faze = "!!! HOTOVO !!!      "
        
        lcd.move_to(0, 0); lcd.putstr(nazev_faze)
        
        cil = 0
        if aktualni_stav <= ST_SOAK: cil = teplota_soak
        elif aktualni_stav <= ST_REFLOW_HOLD: cil = teplota_reflow
        
        lcd.move_to(0, 1); lcd.putstr(f"Akt:{t_str}{chr(223)} Cil:{cil:<3}")

        lcd.move_to(0, 2)
        if aktualni_stav == ST_SOAK:
            ubehlo = (time.ticks_diff(time.ticks_ms(), zacatek_odpoctu) // 1000)
            zbyva = max(0, cas_soak - ubehlo)
            lcd.putstr(f"Cas Soak: {zbyva} sec    ")
        elif aktualni_stav == ST_REFLOW_HOLD:
            ubehlo = (time.ticks_diff(time.ticks_ms(), zacatek_odpoctu) // 1000)
            zbyva = max(0, cas_reflow - ubehlo)
            lcd.putstr(f"Cas Refl: {zbyva} sec    ")
        elif aktualni_stav == ST_COOLING:
             lcd.putstr("Neotvirat pec!      ")
        else:
            lcd.putstr("                    ") 

        lcd.move_to(0, 3)
        if aktualni_stav == ST_DONE:
             lcd.putstr("Cervene -> RESET    ")
        else:
             lcd.putstr("Cervena:STOP        ")

# Prvotní nastavení - vše vypnout
zapni_topeni(0)
aktualizuj_displej()

# --- 5. HLAVNÍ SMYČKA ---
while True:
    aktualni_cas = time.ticks_ms()

    # 1. STOP TLAČÍTKO
    if btn_stop.value() == 0:
        if time.ticks_diff(aktualni_cas, cas_posledniho_stisku_stop) > 300:
            cas_posledniho_stisku_stop = aktualni_cas
            zapni_topeni(0)
            aktualni_stav = ST_SETUP
            print("STOP TLAČÍTKO STISKNUTO!")
            aktualizuj_displej()

    # 2. MODE TLAČÍTKO
    if aktualni_stav == ST_SETUP:
        if btn_mode.value() == 0:
            if time.ticks_diff(aktualni_cas, cas_posledniho_stisku_mode) > 300:
                cas_posledniho_stisku_mode = aktualni_cas
                kurzor_nastaveni = kurzor_nastaveni + 1
                if kurzor_nastaveni > 3: 
                    kurzor_nastaveni = 0
                aktualizuj_displej()

    # 3. START TLAČÍTKO
    if aktualni_stav == ST_SETUP:
        if btn_start.value() == 0:
            if time.ticks_diff(aktualni_cas, cas_posledniho_stisku_start) > 300:
                cas_posledniho_stisku_start = aktualni_cas
                aktualni_stav = ST_PREHEAT
                aktualizuj_displej()

    # --- ŘÍZENÍ TEPLOTY ---
    if time.ticks_diff(aktualni_cas, posledni_kontrola_casu) > 1000:
        posledni_kontrola_casu = aktualni_cas
        
        hodnota = sensor.read()
        if str(hodnota) != 'nan': 
            aktualni_teplota = hodnota
        
        # LOGIKA PECE
        if aktualni_stav == ST_PREHEAT:
            if aktualni_teplota >= teplota_soak:
                aktualni_stav = ST_SOAK
                zacatek_odpoctu = aktualni_cas
                zapni_topeni(1)
            else:
                zapni_topeni(1)
                
        elif aktualni_stav == ST_SOAK:
            if aktualni_teplota < (teplota_soak - hystereze):
                zapni_topeni(1)
            elif aktualni_teplota > teplota_soak:
                zapni_topeni(0)
            
            ubehly_cas = (time.ticks_diff(aktualni_cas, zacatek_odpoctu) // 1000)
            if ubehly_cas >= cas_soak:
                aktualni_stav = ST_REFLOW_RAMP
                zapni_topeni(1)
                
        elif aktualni_stav == ST_REFLOW_RAMP:
            if aktualni_teplota >= teplota_reflow:
                aktualni_stav = ST_REFLOW_HOLD
                zacatek_odpoctu = aktualni_cas
                zapni_topeni(1)
            else:
                zapni_topeni(1)
        
        elif aktualni_stav == ST_REFLOW_HOLD:
            if aktualni_teplota < (teplota_reflow - hystereze):
                zapni_topeni(1)
            elif aktualni_teplota > teplota_reflow:
                zapni_topeni(0)
            
            ubehly_cas = (time.ticks_diff(aktualni_cas, zacatek_odpoctu) // 1000)
            if ubehly_cas >= cas_reflow:
                aktualni_stav = ST_COOLING
                zapni_topeni(0)
                
        elif aktualni_stav == ST_COOLING:
            zapni_topeni(0)
            if aktualni_teplota < 50:
                aktualni_stav = ST_DONE

        aktualizuj_displej()
        
    time.sleep(0.01)