import time
import board
import busio
from digitalio import DigitalInOut, Direction
from pwmio import PWMOut
from adafruit_pn532.i2c import PN532_I2C
import wifi
import socketpool

# --- Moteurs ---
M1_IN1 = PWMOut(board.GP18)
M1_IN2 = PWMOut(board.GP19)
M2_IN1 = PWMOut(board.GP20)
M2_IN2 = PWMOut(board.GP21)
M3_IN1 = PWMOut(board.GP6)
M3_IN2 = PWMOut(board.GP7)
M4_IN1 = PWMOut(board.GP8)
M4_IN2 = PWMOut(board.GP9)

VITESSE = 16000
VITESSE_TOURNE = 20000
VITESSE_CORRECTION = 12000

# --- Capteurs IR ---
CAPTEUR_GAUCHE = DigitalInOut(board.GP10)
CAPTEUR_GAUCHE.direction = Direction.INPUT
CAPTEUR_MILIEU = DigitalInOut(board.GP11)
CAPTEUR_MILIEU.direction = Direction.INPUT
CAPTEUR_DROIT = DigitalInOut(board.GP12)
CAPTEUR_DROIT.direction = Direction.INPUT

DETECTE = True
NON_DETECTE = False

# --- NFC ---
i2c = busio.I2C(scl=board.GP5, sda=board.GP4)
nfc = PN532_I2C(i2c, debug=False)
nfc.SAM_configuration()

# --- Variables ---
nfc_en_cours = False
dernier_etat_capteurs = -1
attend_commande = False
dernier_tag_lu = "Aucun"
position_actuelle = "A2"  # Position de départ
direction_actuelle = "NORD"  # Direction de départ (NORD, SUD, EST, OUEST)
chemin_en_cours = []
index_chemin = 0

# --- Dictionnaire des tags NFC ---
uid_to_tag = {
    "B2:C6:02:6E": "A1",
    "52:F0:40:67": "A2",
    "A2:E4:44:67": "A3",
    "12:0D:C3:66": "B1",
    "C2:86:BD:66": "B2",
    "E2:69:C1:66": "B3",
    "B2:3A:F9:6D": "C1",
    "52:26:FE:6D": "C2",
    "E2:56:C3:66": "C3",
}

# --- Grille et navigation ---
grille_positions = {
    "C1": (0, 0), "C2": (0, 1), "C3": (0, 2),
    "B1": (1, 0), "B2": (1, 1), "B3": (1, 2),
    "A1": (2, 0), "A2": (2, 1), "A3": (2, 2)
}

positions_grille = {v: k for k, v in grille_positions.items()}

directions = ["NORD", "EST", "SUD", "OUEST"]
mouvements = {
    "NORD": (-1, 0),  # Vers le haut (C)
    "SUD": (1, 0),    # Vers le bas (A)
    "EST": (0, 1),    # Vers la droite
    "OUEST": (0, -1)  # Vers la gauche
}

# --- Fonctions moteurs ---
def duty_pwm(pwm_out, value):
    pwm_out.duty_cycle = value

def stop_all():
    for moteur in [M1_IN1, M1_IN2, M2_IN1, M2_IN2, M3_IN1, M3_IN2, M4_IN1, M4_IN2]:
        duty_pwm(moteur, 0)

def avancer():
    duty_pwm(M1_IN1, VITESSE)
    duty_pwm(M1_IN2, 0)
    duty_pwm(M2_IN1, 0)
    duty_pwm(M2_IN2, VITESSE)
    duty_pwm(M3_IN1, 0)
    duty_pwm(M3_IN2, VITESSE)
    duty_pwm(M4_IN1, 0)
    duty_pwm(M4_IN2, VITESSE)

def corriger_droite_lent():
    duty_pwm(M1_IN1, VITESSE)
    duty_pwm(M1_IN2, 0)
    duty_pwm(M2_IN1, 0)
    duty_pwm(M2_IN2, VITESSE)
    duty_pwm(M3_IN1, VITESSE_CORRECTION)
    duty_pwm(M3_IN2, 0)
    duty_pwm(M4_IN1, VITESSE_CORRECTION)
    duty_pwm(M4_IN2, 0)

def corriger_gauche_lent():
    duty_pwm(M1_IN1, 0)
    duty_pwm(M1_IN2, VITESSE_CORRECTION)
    duty_pwm(M2_IN1, VITESSE_CORRECTION)
    duty_pwm(M2_IN2, 0)
    duty_pwm(M3_IN1, 0)
    duty_pwm(M3_IN2, VITESSE)
    duty_pwm(M4_IN1, 0)
    duty_pwm(M4_IN2, VITESSE)

def tourne_gauche():
    impulsion()
    time.sleep(0.10)
    duty_pwm(M1_IN1, 0)
    duty_pwm(M1_IN2, VITESSE_TOURNE)
    duty_pwm(M2_IN1, 0)
    duty_pwm(M2_IN2, 0)
    duty_pwm(M3_IN1, 0)
    duty_pwm(M3_IN2, VITESSE_TOURNE)
    duty_pwm(M4_IN1, 0)
    duty_pwm(M4_IN2, VITESSE_TOURNE)
    time.sleep(0.3)
    t0 = time.monotonic()
    while (CAPTEUR_GAUCHE.value == NON_DETECTE and CAPTEUR_MILIEU.value == NON_DETECTE and CAPTEUR_DROIT.value == NON_DETECTE):
        if (time.monotonic() - t0) > 1.0:
            print("[TIMEOUT] Sortie forcée tourne_gauche.")
            break
        time.sleep(0.01)
    stop_all()

def tourne_droite():
    impulsion()
    time.sleep(0.10)
    duty_pwm(M1_IN1, VITESSE_TOURNE)
    duty_pwm(M1_IN2, 0)
    duty_pwm(M2_IN1, 0)
    duty_pwm(M2_IN2, VITESSE_TOURNE)
    duty_pwm(M3_IN1, 0)
    duty_pwm(M3_IN2, 0)
    duty_pwm(M4_IN1, VITESSE_TOURNE)
    duty_pwm(M4_IN2, 0)
    time.sleep(0.3)
    t0 = time.monotonic()
    while (CAPTEUR_GAUCHE.value == NON_DETECTE and CAPTEUR_MILIEU.value == NON_DETECTE and CAPTEUR_DROIT.value == NON_DETECTE):
        if (time.monotonic() - t0) > 1.0:
            print("[TIMEOUT] Sortie forcée tourne_droite.")
            break
        time.sleep(0.01)
    stop_all()

def impulsion():
    duty_pwm(M1_IN1, VITESSE_TOURNE)
    duty_pwm(M1_IN2, 0)
    duty_pwm(M2_IN1, 0)
    duty_pwm(M2_IN2, VITESSE_TOURNE)
    duty_pwm(M3_IN1, 0)
    duty_pwm(M3_IN2, VITESSE_TOURNE)
    duty_pwm(M4_IN1, 0)
    duty_pwm(M4_IN2, VITESSE_TOURNE)

def avancer_intersection(timeout=8):
    """Avance jusqu'à la prochaine intersection ou timeout"""
    global position_actuelle, dernier_tag_lu
    print(f"[NAVIGATION] Avance de {position_actuelle} vers {direction_actuelle}")
    pos_actuelle = grille_positions[position_actuelle]
    mouvement = mouvements[direction_actuelle]
    nouvelle_pos = (pos_actuelle[0] + mouvement[0], pos_actuelle[1] + mouvement[1])
    tag_precedent = dernier_tag_lu
    t_start = time.monotonic()
    trouve = False
    while True:
        if not attend_commande:
            suivi_ligne()
            lire_nfc()
            if dernier_tag_lu != tag_precedent and dernier_tag_lu in grille_positions:
                trouve = True
                break
        if (time.monotonic() - t_start) > timeout:
            print("[TIMEOUT] Intersection non détectée, arrêt sécurité.")
            stop_all()
            break
        time.sleep(0.01)
    if trouve and nouvelle_pos in positions_grille:
        position_actuelle = positions_grille[nouvelle_pos]
        print(f"[NAVIGATION] Nouvelle position: {position_actuelle}")
    elif not trouve:
        print(f"[ERREUR] Timeout sans détection de tag !")
    else:
        print(f"[ERREUR] Position invalide: {nouvelle_pos}")

def tourner_vers_direction(direction_cible):
    """Tourne le robot vers la direction cible"""
    global direction_actuelle
    if direction_actuelle == direction_cible:
        return
    index_actuel = directions.index(direction_actuelle)
    index_cible = directions.index(direction_cible)
    diff = (index_cible - index_actuel) % 4
    if diff == 1:  # Tourner à droite
        print(f"[NAVIGATION] Tourne à droite de {direction_actuelle} vers {direction_cible}")
        tourne_droite()
    elif diff == 3:  # Tourner à gauche
        print(f"[NAVIGATION] Tourne à gauche de {direction_actuelle} vers {direction_cible}")
        tourne_gauche()
    elif diff == 2:  # Demi-tour
        print(f"[NAVIGATION] Demi-tour de {direction_actuelle} vers {direction_cible}")
        tourne_droite()
        tourne_droite()
    direction_actuelle = direction_cible

def calculer_chemin(depart, arrivee):
    """Calcule le chemin le plus court entre deux points"""
    if depart == arrivee:
        return []
    pos_depart = grille_positions[depart]
    pos_arrivee = grille_positions[arrivee]
    chemin = []
    pos_actuelle = pos_depart
    while pos_actuelle != pos_arrivee:
        # Mouvement horizontal
        if pos_actuelle[1] < pos_arrivee[1]:  # Aller à droite
            direction_necessaire = "EST"
            pos_actuelle = (pos_actuelle[0], pos_actuelle[1] + 1)
        elif pos_actuelle[1] > pos_arrivee[1]:  # Aller à gauche
            direction_necessaire = "OUEST"
            pos_actuelle = (pos_actuelle[0], pos_actuelle[1] - 1)
        # Mouvement vertical
        elif pos_actuelle[0] < pos_arrivee[0]:  # Aller vers le bas (A)
            direction_necessaire = "SUD"
            pos_actuelle = (pos_actuelle[0] + 1, pos_actuelle[1])
        elif pos_actuelle[0] > pos_arrivee[0]:  # Aller vers le haut (C)
            direction_necessaire = "NORD"
            pos_actuelle = (pos_actuelle[0] - 1, pos_actuelle[1])
        chemin.append(direction_necessaire)
    return chemin

def executer_chemin():
    """Exécute le chemin calculé étape par étape"""
    global chemin_en_cours, index_chemin, attend_commande
    if not chemin_en_cours or index_chemin >= len(chemin_en_cours):
        print("[NAVIGATION] Trajet terminé!")
        attend_commande = False
        chemin_en_cours = []
        index_chemin = 0
        return
    direction_cible = chemin_en_cours[index_chemin]
    print(f"[NAVIGATION] Étape {index_chemin + 1}/{len(chemin_en_cours)}: {direction_cible}")
    tourner_vers_direction(direction_cible)
    avancer_intersection()
    index_chemin += 1
    if index_chemin < len(chemin_en_cours):
        print(f"[NAVIGATION] Prochaine étape dans 2 secondes...")
    else:
        print("[NAVIGATION] Destination atteinte!")
        attend_commande = False
        chemin_en_cours = []
        index_chemin = 0

def lire_nfc():
    global nfc_en_cours, attend_commande, dernier_tag_lu, position_actuelle
    if nfc_en_cours:
        return
    nfc_en_cours = True
    uid = nfc.read_passive_target(timeout=0.05)
    if uid:
        uid_str = ":".join([f"{i:02X}" for i in uid])
        tag_name = uid_to_tag.get(uid_str, f"Inconnu ({uid_str})")
        print(f"[NFC] UID: {uid_str} → {tag_name}")
        stop_all()
        if tag_name in grille_positions:
            position_actuelle = tag_name
            print(f"[POSITION] Position mise à jour: {position_actuelle}")
        attend_commande = True
        dernier_tag_lu = tag_name
    nfc_en_cours = False

def suivi_ligne():
    global dernier_etat_capteurs
    cap_g = CAPTEUR_GAUCHE.value
    cap_m = CAPTEUR_MILIEU.value
    cap_d = CAPTEUR_DROIT.value
    pattern = (cap_g << 2) | (cap_m << 1) | cap_d
    if pattern != dernier_etat_capteurs:
        print(f"[CAPTEURS] Pattern: {bin(pattern)} → ", end='')
        if pattern == 0b010:
            print("AVANCE")
            avancer()
        elif pattern in [0b001, 0b011]:
            print("CORRECTION GAUCHE")
            corriger_gauche_lent()
        elif pattern in [0b100, 0b110]:
            print("CORRECTION DROITE")
            corriger_droite_lent()
        elif pattern == 0b111:
            print("INTERSECTION")
            avancer()
        elif pattern == 0b000:
            print("PLUS DE LIGNE - STOP")
            stop_all()
        else:
            print("ÉTAT INCONNU")
        dernier_etat_capteurs = pattern

# --- Point d'accès Wi-Fi ---
ssid = "RobotTransporteur"
password = "12345678"
print("Démarrage point d'accès Wi-Fi...")
wifi.radio.start_ap(ssid=ssid, password=password)
time.sleep(2)
print("Point d'accès actif:", ssid)

pool = socketpool.SocketPool(wifi.radio)
server = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
server.bind(("0.0.0.0", 80))
server.listen(5)
server.settimeout(None)

print("Serveur HTTP démarré")

# --- Boucle principale ---
while True:
    if chemin_en_cours and not attend_commande:
        executer_chemin()
        time.sleep(2)
        continue

    if not attend_commande:
        suivi_ligne()
        lire_nfc()

    try:
        client_sock, client_addr = server.accept()
        print(f"Client connecté depuis {client_addr}")
        client_sock.settimeout(1)
        try:
            buffer = bytearray(1024)
            received = client_sock.recv_into(buffer)
            if received == 0:
                print("Client a fermé la connexion immédiatement")
                client_sock.close()
                continue
            request = buffer[:received].decode("utf-8")
            print("Requête reçue :", request.split("\n")[0])
        except Exception as e:
            print("Erreur réception requête:", e)
            client_sock.close()
            continue

        if "GET /status" in request:
            status_json = '{"position":"' + position_actuelle + '","direction":"' + direction_actuelle + '","en_attente":' + str(attend_commande).lower() + ',"dernier_tag":"' + dernier_tag_lu + '","chemin_actif":' + str(len(chemin_en_cours) > 0).lower() + ',"index_chemin":' + str(index_chemin) + ',"chemin_total":' + str(len(chemin_en_cours)) + '}'
            response = f"HTTP/1.1 200 OK\nContent-Type: application/json\n\n{status_json}"
            client_sock.send(response.encode("utf-8"))
            client_sock.close()
            continue

        destination = None
        if "GET /?destination=" in request:
            start = request.find("destination=") + 12
            end = request.find(" ", start)
            if end == -1:
                end = request.find("&", start)
            if end == -1:
                end = len(request)
            destination = request[start:end]

        if destination and destination in grille_positions:
            print(f"[COMMANDE] Navigation vers {destination} depuis {position_actuelle}")
            chemin_en_cours = calculer_chemin(position_actuelle, destination)
            index_chemin = 0
            print(f"[CHEMIN] Calculé: {chemin_en_cours}")
            attend_commande = False

        action = None
        if "GET /?action=left" in request:
            action = "left"
        elif "GET /?action=right" in request:
            action = "right"
        elif "GET /?action=forward" in request:
            action = "forward"

        if attend_commande and action:
            if action == "left":
                print("Commande manuelle : tourner à gauche")
                tourne_gauche()
            elif action == "right":
                print("Commande manuelle : tourner à droite")
                tourne_droite()
            elif action == "forward":
                print("Commande manuelle : avancer")
                avancer_intersection()
            attend_commande = False

        # Page HTML (inchangé)
        html_page = """HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Navigation Robot</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Roboto', sans-serif;
            margin: 40px;
            background-color: #f9f9f9;
            color: #333;
        }

        h1 {
            font-size: 2em;
            margin-bottom: 20px;
        }

        .grid-container {
            display: flex;
            justify-content: center;
            margin-bottom: 40px;
        }

        table {
            border-collapse: collapse;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        }

        td {
            width: 80px;
            height: 80px;
            border: 1px solid #ccc;
            text-align: center;
            vertical-align: middle;
            font-size: 18px;
            font-weight: bold;
            background-color: white;
            cursor: pointer;
            transition: background-color 0.3s, color 0.3s, transform 0.2s;
        }

        td:hover {
            background-color: #2196F3;
            color: white;
            transform: scale(1.05);
        }

        td.current {
            background-color: #f44336;
            color: white;
        }

        td.target {
            background-color: #4CAF50;
            color: white;
        }

        .controls {
            text-align: center;
            margin-bottom: 30px;
        }

        button {
            padding: 12px 24px;
            margin: 8px;
            font-size: 16px;
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: background-color 0.3s, transform 0.2s;
        }

        button:hover {
            background-color: #1976D2;
            transform: translateY(-2px);
        }

        .status {
            max-width: 500px;
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            margin: 0 auto 40px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            font-family: monospace;
            font-size: 14px;
            line-height: 1.6;
        }

        .status strong {
            color: #555;
        }
    </style>
</head>
<body>

<h1>🤖 Navigation Robot</h1>

<div class="status">
    <strong>Position actuelle:</strong> <span id="position">""" + position_actuelle + """</span><br>
    <strong>Direction:</strong> <span id="direction">""" + direction_actuelle + """</span><br>
    <strong>En attente:</strong> <span id="attente">""" + str(attend_commande) + """</span><br>
    <strong>Dernier tag NFC:</strong> <span id="dernier_tag">""" + dernier_tag_lu + """</span><br>
    <strong>Chemin actif:</strong> <span id="chemin_actif">""" + str(len(chemin_en_cours) > 0) + """</span>
</div>

<div class="grid-container">
    <div>
        <h3 style="text-align:center; margin-bottom: 10px;">🗺️ Grille de Navigation</h3>
        <p style="text-align:center;">Cliquez sur une case pour y naviguer</p>
        <table id="grid">
            <tr>
                <td id="C1" onclick="naviguer('C1')">C1</td>
                <td id="C2" onclick="naviguer('C2')">C2</td>
                <td id="C3" onclick="naviguer('C3')">C3</td>
            </tr>
            <tr>
                <td id="B1" onclick="naviguer('B1')">B1</td>
                <td id="B2" onclick="naviguer('B2')">B2</td>
                <td id="B3" onclick="naviguer('B3')">B3</td>
            </tr>
            <tr>
                <td id="A1" onclick="naviguer('A1')">A1</td>
                <td id="A2" onclick="naviguer('A2')">A2</td>
                <td id="A3" onclick="naviguer('A3')">A3</td>
            </tr>
        </table>
    </div>
</div>

<div class="controls">
    <h3>🎮 Contrôles Manuels</h3>
    <button onclick="commande('left')">↺ Tourner à gauche</button>
    <button onclick="commande('right')">↻ Tourner à droite</button>
    <button onclick="commande('forward')">↑ Avancer</button>
</div>

<script>
function naviguer(destination) {
    window.location.href = '/?destination=' + destination;
}

function commande(action) {
    window.location.href = '/?action=' + action;
}

async function updateStatus() {
    try {
        const response = await fetch('/status');
        if(response.ok) {
            const status = JSON.parse(await response.text());

            document.getElementById('position').textContent = status.position || 'Inconnu';
            document.getElementById('direction').textContent = status.direction || 'Inconnu';
            document.getElementById('attente').textContent = status.en_attente ? 'Oui' : 'Non';
            document.getElementById('dernier_tag').textContent = status.dernier_tag || 'Aucun';
            document.getElementById('chemin_actif').textContent = status.chemin_actif ?
                'Oui (' + (status.index_chemin || 0) + '/' + (status.chemin_total || 0) + ')' : 'Non';

            document.querySelectorAll('#grid td').forEach(td => {
                td.classList.remove('current', 'target');
                td.innerHTML = td.id;
            });

            if(status.position && status.position !== 'Aucun') {
                const cell = document.getElementById(status.position);
                if(cell) {
                    cell.classList.add('current');
                    cell.innerHTML = status.position + '<br>🤖';
                }
            }
        }
    } catch(e) {
        console.error('Erreur mise à jour status:', e);
    }
}

setInterval(updateStatus, 1000);
updateStatus();
</script>

</body>
</html>"""
        client_sock.send(html_page.encode("utf-8"))
        print("Page HTML envoyée")
        client_sock.close()
    except OSError as e:
        print("OSError:", e)
    except Exception as e:
        print("Exception:", e)
    time.sleep(0.01)
