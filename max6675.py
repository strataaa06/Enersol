import time

class MAX6675:
    def __init__(self, spi, cs_pin):
        """
        spi: inicializovaný SPI objekt
        cs_pin: inicializovaný Pin objekt (nastavený jako OUT)
        """
        self.spi = spi
        self.cs = cs_pin
        self.cs.value(1) # Deaktivovat při startu

    def read(self):
        """
        Přečte teplotu. Vrací float (stupně Celsia) nebo None, pokud je chyba.
        """
        self.cs.value(0) # Aktivovat čip (Low)
        
        # Přečíst 2 byty (16 bitů)
        # MAX6675 nevyžaduje posílání dat, jen čteme
        raw_data = self.spi.read(2)
        
        self.cs.value(1) # Deaktivovat čip (High)

        if not raw_data or len(raw_data) != 2:
            return None

        # Složení dvou bytů do jednoho čísla
        value = (raw_data[0] << 8) | raw_data[1]

        # Bit D2 (třetí od konce) indikuje, zda je termočlánek odpojený
        if value & 0x04:
            return float('nan') # Termočlánek není připojen (Open Circuit)

        # Data jsou v bitech D14 až D3 (12 bitů)
        # Musíme posunout o 3 bity doprava
        value >>= 3

        # Rozlišení je 0.25 °C
        return value * 0.25