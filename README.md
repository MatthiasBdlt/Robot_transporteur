# 🚗 Robot Suiveur de Ligne avec Navigation NFC

Ce projet met en œuvre un robot mobile capable de suivre une ligne noire à l’aide de capteurs infrarouges et de se localiser/diriger à l’aide de tags NFC. Le robot est contrôlé par une carte **Raspberry Pi Pico** et utilise des moteurs PWM, des capteurs IR, et un lecteur NFC pour détecter des intersections et se déplacer automatiquement sur une grille définie.

---

## 📸 Aperçu du projet

| Composant         | Rôle                                       |
|------------------|--------------------------------------------|
| **Capteurs IR**   | Suivi de ligne (gauche, milieu, droite)   |
| **PN532 NFC**     | Lecture de tags NFC pour se localiser     |
| **Moteurs PWM**   | Déplacement du robot (avancer, tourner)   |
| **Raspberry Pi Pico** | Contrôle principal (MicroPython / CircuitPython) |

---

## 🔧 Matériel utilisé

- 1x Raspberry Pi Pico  
- 1x Lecteur NFC **PN532** (I2C)
- 3x Capteurs infrarouges (suivi de ligne)
- 4x Moteurs DC (contrôlés en PWM)
- Modules pont en H (ex: L298N ou similaire)
- Tags NFC (collés sur une grille physique)
- Fils, châssis robot, roues...

---

## 📦 Structure du code

Le projet contient les modules/fonctions suivants :

| Fonction                   | Description                                         |
|---------------------------|-----------------------------------------------------|
| `avancer()`               | Fait avancer le robot tout droit                   |
| `corriger_gauche_lent()`  | Corrige vers la gauche si décalé                   |
| `corriger_droite_lent()`  | Corrige vers la droite si décalé                   |
| `tourne_gauche()` / `tourne_droite()` | Rotation à 90° à une intersection    |
| `lire_nfc()`              | Lit les tags NFC pour mise à jour de position      |
| `calculer_chemin()`       | Calcule un chemin optimal dans la grille           |
| `executer_chemin()`       | Fait suivre le chemin calculé au robot             |
| `suivi_ligne()`           | Suit la ligne avec les capteurs IR                 |
| `grille_positions`        | Grille logique des positions (A1, B2, etc.)        |

---

## 🧭 Exemple de Grille (3x3)

C1 C2 C3  
B1 B2 B3  
A1 A2 A3  


Les tags NFC sont disposés aux intersections, et permettent au robot de se repérer en temps réel.

---

## ▶️ Démarrer

1. Flash ton Raspberry Pi Pico avec **CircuitPython**
2. Copie le fichier `.py` dans le volume **CIRCUITPY**
3. Branche tous les composants (NFC, moteurs, capteurs IR)
4. Démarre l'alimentation du robot
5. Utilise la grille et les tags NFC pour tester la navigation automatique !

---

## 📈 Améliorations possibles

- Détection d’obstacle avec capteur à ultrasons
- Interface web pour envoyer des destinations
- Optimisation du PID du suivi de ligne
- Ajout de logs sur carte SD

---

## 🧠 Crédits

Projet conçu et codé par [Matthias BIDAULT].  
Basé sur Raspberry Pi Pico + CircuitPython avec bibliothèque **Adafruit PN532**.

---

