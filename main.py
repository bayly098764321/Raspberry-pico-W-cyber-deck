import machine
import utime
import network
import gc

from lcd1602 import LCD

# ================= LCD SETUP =================
lcd = LCD()
lcd.clear()
lcd.openlight()

# ================= JOYSTICK ==================
joy_y = machine.ADC(machine.Pin(27))
joy_btn = machine.Pin(22, machine.Pin.IN, machine.Pin.PULL_UP)

# ================= WIFI ======================
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

SSID = "Wifi name"      # <-- Add your Wi-Fi name
PASSWORD = "Wifi password"  # <-- Add your Wi-Fi password

if not wlan.isconnected():
    lcd.write(0, 0, "Connecting Wi-Fi")
    wlan.connect(SSID, PASSWORD)
    start = utime.time()
    while not wlan.isconnected():
        lcd.write(0, 1, "Please wait...")
        utime.sleep(1)
        if utime.time() - start > 15:
            lcd.write(0, 1, "Failed to connect")
            break
    else:
        lcd.write(0, 1, "Connected!")
        utime.sleep(1)

# ================= MENU ======================
menu = [
    "CYBER HUD",
    "NET STATUS",
    "SCAN MODE",
    "SYSTEM LOG",
    "ABOUT"
]
menu_index = 0

# ================= SYSTEM LOG =================
system_logs = []

def add_log(entry):
    system_logs.append(entry)
    if len(system_logs) > 5:
        system_logs.pop(0)

# ================= UTIL ======================
def clear():
    lcd.clear()

def draw_menu():
    clear()
    lcd.write(0, 0, ">" + menu[menu_index])
    if menu_index + 1 < len(menu):
        lcd.write(0, 1, " " + menu[menu_index + 1])

def wait_release():
    while not joy_btn.value():
        utime.sleep(0.05)

# ================= MODES =====================
def cyber_hud():
    add_log("Entered CYBER HUD")
    for _ in range(20):
        bars = "|" * (gc.mem_free() // 100)
        lcd.write(0, 0, "SIG:" + bars[:16])
        lcd.write(0, 1, "CPU: ACTIVE")
        utime.sleep(0.2)
        if not joy_btn.value():
            wait_release()
            add_log("Exited CYBER HUD")
            return

def net_status():
    clear()
    add_log("Entered NET STATUS")
    lcd.write(0, 0, "NET STATUS")
    while True:
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            ssid = wlan.config('essid')
            lcd.write(0, 1, "{} {:>8}".format(ssid[:8], ip))
        else:
            lcd.write(0, 1, "Offline         ")

        if not joy_btn.value():
            wait_release()
            add_log("Exited NET STATUS")
            return
        utime.sleep(0.1)

def scan_mode():
    clear()
    add_log("Entered SCAN MODE")
    lcd.write(0, 0, "SCANNING...")
    last_scan = utime.ticks_ms()
    net_index = 0
    networks_list = []

    while True:
        if not joy_btn.value():
            wait_release()
            add_log("Exited SCAN MODE")
            return

        if utime.ticks_diff(utime.ticks_ms(), last_scan) > 1500:
            last_scan = utime.ticks_ms()
            if wlan.isconnected():
                networks = wlan.scan()
                if networks:
                    networks_list = [(n[0].decode(), n[3]) for n in networks]
                    ssid, rssi = networks_list[net_index % len(networks_list)]
                    bars = "|" * max(1, int((100 + rssi)/10))
                    lcd.write(0, 1, "{} {:>3}dBm {}".format(ssid[:8], rssi, bars))
                    net_index += 1
                else:
                    lcd.write(0, 1, "No networks      ")
            else:
                lcd.write(0, 1, "WiFi OFF         ")

        utime.sleep(0.05)

def system_log():
    clear()
    add_log("Entered SYSTEM LOG")
    lcd.write(0, 0, "> SYSTEM LOG")
    while True:
        if system_logs:
            for log in system_logs[-2:]:
                lcd.write(0, 1, log[:16])
                for _ in range(20):
                    if not joy_btn.value():
                        wait_release()
                        add_log("Exited SYSTEM LOG")
                        return
                    utime.sleep(0.05)
        else:
            lcd.write(0, 1, "No logs yet")
            if not joy_btn.value():
                wait_release()
                add_log("Exited SYSTEM LOG")
                return
            utime.sleep(0.1)

def about():
    clear()
    add_log("Entered ABOUT")
    text = "PICO CYBERDECK"
    lcd.write(0, 1, "Version 1.0 ")
    scroll_pos = 0
    while True:
        lcd.write(0, 0, text[scroll_pos:scroll_pos+16])
        scroll_pos = (scroll_pos - 0) % len(text)
        if not joy_btn.value():
            wait_release()
            add_log("Exited ABOUT")
            return
        utime.sleep(0.01)

# ================= MAIN LOOP =================
draw_menu()
last_y = 0
last_activity = utime.ticks_ms()  # track last user activity
IDLE_DELAY = 15000  # 5 seconds inactivity
idle_text = "   CYBER DECK   "
loop_text = idle_text + idle_text
scroll_index = 0

while True:
    y = joy_y.read_u16()
    joystick_moved = False

    # Up/down scrolling
    if y < 10000 and last_y >= 10000:
        menu_index = (menu_index - 1) % len(menu)
        joystick_moved = True
    elif y > 55000 and last_y <= 55000:
        menu_index = (menu_index + 1) % len(menu)
        joystick_moved = True

    if joystick_moved:
        draw_menu()
        last_activity = utime.ticks_ms()

    last_y = y

    # Button press to enter menu
    if not joy_btn.value():
        wait_release()
        last_activity = utime.ticks_ms()
        if menu_index == 0:
            cyber_hud()
        elif menu_index == 1:
            net_status()
        elif menu_index == 2:
            scan_mode()
        elif menu_index == 3:
            system_log()
        elif menu_index == 4:
            about()
        draw_menu()
    
    # ================= IDLE MODE =================
    if utime.ticks_diff(utime.ticks_ms(), last_activity) > IDLE_DELAY:
        lcd.write(1, 1, "     Idle    ")  # bottom line static
        lcd.write(0, 0, loop_text[scroll_index:scroll_index + 16])
        scroll_index = (scroll_index - 1) % len(idle_text)  # smooth looping
        # reset idle if joystick moves or button pressed
        if (not joy_btn.value()) or (y < 10000 or y > 55000):
            last_activity = utime.ticks_ms()
            draw_menu()
        utime.sleep(0.3)
    else:
        utime.sleep(0.05)

