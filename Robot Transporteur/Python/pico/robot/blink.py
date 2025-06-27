import time
import board
import busio
import digitalio
from adafruit_pn532.i2c import PN532_I2C
import RPi.GPIO as GPIO

# --- Configuration GPIO ---
MOTEURS = {
    'M1_IN1': 18, 'M1_IN2': 19,
    'M2_IN1': 20, 'M2_IN2': 21,
    'M3_IN1': 6,  'M3_IN2': 7,
    'M4_IN1': 8,  'M4_IN2': 9
}

CAPTEURS = {
    'GAUCHE': 10,
    'MILIEU': 11,
    'DROIT': 12
}

VITESSE = 1  # Pour PWM sinon HIGH/LOW
VITESSE_TOURNE = 1
VITESSE_CORRECTION = 1

DETECTE = GPIO.HIGH
NON_DETECTE = GPIO.LOW

# --- Initialisation GPIO ---
GPIO.setmode(GPIO.BCM)
for pin in MOTEURS.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

for pin in CAPTEURS.values():
    GPIO.setup(pin, GPIO.IN)

# --- NFC Setup ---
i2c = busio.I2C(board.SCL, board.SDA)
pn532 = PN532_I2C(i2c, debug=False)
pn532.SAM_configuration()

# --- Variables de contrôle ---
nfc_initialise = True
dernier_etat_capteurs = -1
nfc_en_cours = False
dernier_changement_etat = time.time()
INTERVALLE_MESURE = 0.01
derniere_mesure = time.time()

# --- Fonctions moteurs ---
def arreter():
    for pin in MOTEURS.values():
        GPIO.output(pin, GPIO.LOW)

def avancerToutDroit():
    GPIO.output(MOTEURS['M1_IN1'], GPIO.HIGH)
    GPIO.output(MOTEURS['M1_IN2'], GPIO.LOW)
    GPIO.output(MOTEURS['M2_IN1'], GPIO.LOW)
    GPIO.output(MOTEURS['M2_IN2'], GPIO.HIGH)
    GPIO.output(MOTEURS['M3_IN1'], GPIO.LOW)
    GPIO.output(MOTEURS['M3_IN2'], GPIO.HIGH)
    GPIO.output(MOTEURS['M4_IN1'], GPIO.LOW)
    GPIO.output(MOTEURS['M4_IN2'], GPIO.HIGH)

def corrigerDroiteLent():
    avancerToutDroit()
    GPIO.output(MOTEURS['M3_IN1'], GPIO.HIGH)
    GPIO.output(MOTEURS['M3_IN2'], GPIO.LOW)
    GPIO.output(MOTEURS['M4_IN1'], GPIO.HIGH)
    GPIO.output(MOTEURS['M4_IN2'], GPIO.LOW)

def corrigerGaucheLent():
    GPIO.output(MOTEURS['M1_IN1'], GPIO.LOW)
    GPIO.output(MOTEURS['M1_IN2'], GPIO.HIGH)
    GPIO.output(MOTEURS['M2_IN1'], GPIO.HIGH)
    GPIO.output(MOTEURS['M2_IN2'], GPIO.LOW)
    GPIO.output(MOTEURS['M3_IN1'], GPIO.LOW)
    GPIO.output(MOTEURS['M3_IN2'], GPIO.HIGH)
    GPIO.output(MOTEURS['M4_IN1'], GPIO.LOW)
    GPIO.output(MOTEURS['M4_IN2'], GPIO.HIGH)

def tourneDroite():
    GPIO.output(MOTEURS['M1_IN1'], GPIO.HIGH)
    GPIO.output(MOTEURS['M1_IN2'], GPIO.LOW)
    GPIO.output(MOTEURS['M2_IN1'], GPIO.LOW)
    GPIO.output(MOTEURS['M2_IN2'], GPIO.HIGH)
    GPIO.output(MOTEURS['M3_IN1'], GPIO.LOW)
    GPIO.output(MOTEURS['M3_IN2'], GPIO.LOW)
    GPIO.output(MOTEURS['M4_IN1'], GPIO.HIGH)
    GPIO.output(MOTEURS['M4_IN2'], GPIO.LOW)

def tourneGauche():
    GPIO.output(MOTEURS['M1_IN1'], GPIO.LOW)
    GPIO.output(MOTEURS['M1_IN2'], GPIO.HIGH)
    GPIO.output(MOTEURS['M2_IN1'], GPIO.LOW)
    GPIO.output(MOTEURS['M2_IN2'], GPIO.LOW)
    GPIO.output(MOTEURS['M3_IN1'], GPIO.LOW)
    GPIO.output(MOTEURS['M3_IN2'], GPIO.HIGH)
    GPIO.output(MOTEURS['M4_IN1'], GPIO.LOW)
    GPIO.output(MOTEURS['M4_IN2'], GPIO.HIGH)

def impulsion():
    for name in ['M1_IN1', 'M2_IN2', 'M3_IN2', 'M4_IN2']:
        GPIO.output(MOTEURS[name], GPIO.HIGH)

# --- Lecture NFC ---
def lireNFC():
    global nfc_en_cours
    if not nfc_initialise or nfc_en_cours:
        return

    nfc_en_cours = True
    uid = pn532.read_passive_target(timeout=0.05)
    if uid:
        print("[NFC] Tag détecté. UID:", [hex(i) for i in uid])
        arreter()
        time.sleep(0.5)
        impulsion()
        time.sleep(0.2)
        tourneGauche()
        time.sleep(0.6)

        while all(GPIO.input(pin) == NON_DETECTE for pin in CAPTEURS.values()):
            tourneGauche()

        avancerToutDroit()

    nfc_en_cours = False

# --- Suivi de ligne ---
def suiviLigne():
    global dernier_etat_capteurs, derniere_mesure

    maintenant = time.time()
    if maintenant - derniere_mesure < INTERVALLE_MESURE:
        return
    derniere_mesure = maintenant

    gauche = GPIO.input(CAPTEURS['GAUCHE'])
    milieu = GPIO.input(CAPTEURS['MILIEU'])
    droit = GPIO.input(CAPTEURS['DROIT'])

    pattern = (gauche << 2) | (milieu << 1) | droit

    if pattern != dernier_etat_capteurs:
        print(f"[CAPTEURS] Pattern: {bin(pattern)}", end=" → ")

        if pattern == 0b010:
            print("AVANCE")
            avancerToutDroit()
        elif pattern in [0b011, 0b001]:
            print("CORRECTION GAUCHE")
            corrigerGaucheLent()
        elif pattern in [0b100, 0b110]:
            print("CORRECTION DROITE")
            corrigerDroiteLent()
        elif pattern == 0b111:
            print("TOUT NOIR")
            avancerToutDroit()
        elif pattern == 0b000:
            print("PLUS DE LIGNE")
            time.sleep(0.05)
            arreter()
        else:
            print("ÉTAT INCONNU")

        dernier_etat_capteurs = pattern

# --- Boucle principale ---
try:
    print("[INIT] Système démarré")
    while True:
        suiviLigne()
        lireNFC()
        time.sleep(0.01)
except KeyboardInterrupt:
    print("Arrêt manuel")
finally:
    GPIO.cleanup()
