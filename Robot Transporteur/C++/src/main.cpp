#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_PN532.h>

// --- Configuration NFC ---
#define PN532_IRQ -1
#define PN532_RESET -1
Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);

// --- Déclaration des broches moteurs ---
const int M1_IN1 = 18;
const int M1_IN2 = 19; // Moteur avant gauche
const int M2_IN1 = 20;
const int M2_IN2 = 21; // Moteur arrière gauche
const int M3_IN1 = 6;
const int M3_IN2 = 7; // Moteur arrière droit
const int M4_IN1 = 8;
const int M4_IN2 = 9; // Moteur avant droit

// --- Vitesses moteurs ---
const int VITESSE = 65; // Augmenté pour meilleure réactivité
const int VITESSE_TOURNE = 80;
const int VITESSE_CORRECTION = 65; // Augmenté proportionnellement

// --- Déclaration des capteurs IR ---
const int BROCHE_CAPTEUR_GAUCHE = 10;
const int BROCHE_CAPTEUR_MILIEU = 11;
const int BROCHE_CAPTEUR_DROIT = 12;

// --- États logiques des capteurs ---
const int DETECTE = 1;     // Noir détecté (ligne)
const int NON_DETECTE = 0; // Blanc (pas de ligne)

// --- Variables de contrôle ---
bool nfcInitialise = false;
unsigned long derniereLectureNFC = 0;
const unsigned long INTERVALLE_NFC = 2000; // Réduit à 2 secondes
int dernierEtatCapteurs = -1;
bool debugMode = true;
bool nfcEnCours = false;
unsigned long dernierChangementEtat = 0;
const unsigned long DELAI_RECUPERATION = 500; // Délai avant arrêt si ligne perdue
unsigned long derniereMesure = 0;
const unsigned long INTERVALLE_MESURE = 10; // Intervalle minimum entre mesures

void initialiser_moteurs()
{

    pinMode(M1_IN1, OUTPUT);
    pinMode(M1_IN2, OUTPUT);
    pinMode(M2_IN1, OUTPUT);
    pinMode(M2_IN2, OUTPUT);
    pinMode(M3_IN1, OUTPUT);
    pinMode(M3_IN2, OUTPUT);
    pinMode(M4_IN1, OUTPUT);
    pinMode(M4_IN2, OUTPUT);

    // Assurer que tous les moteurs sont arrêtés au démarrage
    analogWrite(M1_IN1, 0);
    analogWrite(M1_IN2, 0);
    analogWrite(M2_IN1, 0);
    analogWrite(M2_IN2, 0);
    analogWrite(M3_IN1, 0);
    analogWrite(M3_IN2, 0);
    analogWrite(M4_IN1, 0);
    analogWrite(M4_IN2, 0);
}

void initialiser_capteurs()
{
    pinMode(BROCHE_CAPTEUR_GAUCHE, INPUT);
    pinMode(BROCHE_CAPTEUR_MILIEU, INPUT);
    pinMode(BROCHE_CAPTEUR_DROIT, INPUT);
}

void initialiser_nfc()
{
    Wire.begin();
    nfc.begin();

    uint32_t versiondata = nfc.getFirmwareVersion();
    if (!versiondata)
    {
        if (Serial)
            Serial.println("[INIT] PN532 non détecté - Mode ligne seule");
        nfcInitialise = false;
        return;
    }

    nfc.SAMConfig();
    if (Serial)
        Serial.println("[INIT] PN532 prêt");
    nfcInitialise = true;
}

// --- Fonctions moteurs optimisées ---
void arreter()
{
    analogWrite(M1_IN1, 0);
    analogWrite(M1_IN2, 0);
    analogWrite(M2_IN1, 0);
    analogWrite(M2_IN2, 0);
    analogWrite(M3_IN1, 0);
    analogWrite(M3_IN2, 0);
    analogWrite(M4_IN1, 0);
    analogWrite(M4_IN2, 0);
}

void avancerToutDroit()
{
    analogWrite(M1_IN1, VITESSE);
    analogWrite(M1_IN2, 0);
    analogWrite(M2_IN1, 0);
    analogWrite(M2_IN2, VITESSE);
    analogWrite(M3_IN1, 0);
    analogWrite(M3_IN2, VITESSE);
    analogWrite(M4_IN1, 0);
    analogWrite(M4_IN2, VITESSE);
}

void corrigerDroiteLent()
{
    analogWrite(M1_IN1, VITESSE);
    analogWrite(M1_IN2, 0);
    analogWrite(M2_IN1, 0);
    analogWrite(M2_IN2, VITESSE);
    analogWrite(M3_IN1, VITESSE_CORRECTION);
    analogWrite(M3_IN2, 0);
    analogWrite(M4_IN1, VITESSE_CORRECTION);
    analogWrite(M4_IN2, 0);
}

void corrigerGaucheLent()
{
    analogWrite(M1_IN1, 0);
    analogWrite(M1_IN2, VITESSE_CORRECTION);
    analogWrite(M2_IN1, VITESSE_CORRECTION);
    analogWrite(M2_IN2, 0);
    analogWrite(M3_IN1, 0);
    analogWrite(M3_IN2, VITESSE);
    analogWrite(M4_IN1, 0);
    analogWrite(M4_IN2, VITESSE);
}

void tourneDroite()
{
    // Tourne sur place à droite
    analogWrite(M1_IN1, VITESSE_TOURNE);
    analogWrite(M1_IN2, 0); // Avant gauche
    analogWrite(M2_IN1, 0);
    analogWrite(M2_IN2, VITESSE_TOURNE); // Arrière gauche
    analogWrite(M3_IN1, 0);
    analogWrite(M3_IN2, 0); // Arriere droit
    analogWrite(M4_IN1, VITESSE_TOURNE);
    analogWrite(M4_IN2, 0); // Avant droit
}

void tourneGauche()
{
    // Tourne sur place à gauche
    analogWrite(M1_IN1, 0);
    analogWrite(M1_IN2, VITESSE_TOURNE); // Avant gauche
    analogWrite(M2_IN1, 0);
    analogWrite(M2_IN2, 0); // Arrière gauche
    analogWrite(M3_IN1, 0);
    analogWrite(M3_IN2, VITESSE_TOURNE); // Arrière droit
    analogWrite(M4_IN1, 0);
    analogWrite(M4_IN2, VITESSE_TOURNE); // Avant droit
}

void impulsion()
{
    analogWrite(M1_IN1, VITESSE_TOURNE);
    analogWrite(M1_IN2, 0);
    analogWrite(M2_IN1, 0);
    analogWrite(M2_IN2, VITESSE_TOURNE);
    analogWrite(M3_IN1, 0);
    analogWrite(M3_IN2, VITESSE_TOURNE);
    analogWrite(M4_IN1, 0);
    analogWrite(M4_IN2, VITESSE_TOURNE);
}

// --- Fonction NFC optimisée ---
void lireNFC()
{
    if (!nfcInitialise || nfcEnCours)
        return;

    nfcEnCours = true;
    uint8_t uid[7];
    uint8_t uidLength;

    if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 50))
    {
        Serial.print("[NFC] Tag détecté. UID: ");
        for (uint8_t i = 0; i < uidLength; i++)
        {
            if (uid[i] < 0x10)
                Serial.print("0");
            Serial.print(uid[i], HEX);
            Serial.print(" ");
        }
        Serial.println();

        arreter();
        delay(500);
        impulsion(); // Repart sur la ligne
        delay(200);
        // --- Tourner à gauche ---
        tourneGauche();
        delay(600); // Ajuste ce délai pour un vrai virage à 90°

        // --- Chercher la ligne après le virage ---
        while (
            digitalRead(BROCHE_CAPTEUR_DROIT) == NON_DETECTE &&
            digitalRead(BROCHE_CAPTEUR_MILIEU) == NON_DETECTE &&
            digitalRead(BROCHE_CAPTEUR_GAUCHE) == NON_DETECTE)
        {
            tourneGauche();
        }

        avancerToutDroit(); // Repart sur la ligne
    }

    nfcEnCours = false;
}

// --- Fonction de suivi de ligne améliorée ---
void suiviLigne()
{
    unsigned long maintenant = millis();
    if (maintenant - derniereMesure < INTERVALLE_MESURE)
        return;
    derniereMesure = maintenant;

    int capteurGauche = digitalRead(BROCHE_CAPTEUR_GAUCHE);
    int capteurMilieu = digitalRead(BROCHE_CAPTEUR_MILIEU);
    int capteurDroit = digitalRead(BROCHE_CAPTEUR_DROIT);

    int pattern = (capteurGauche << 2) | (capteurMilieu << 1) | capteurDroit;

    if (pattern != dernierEtatCapteurs)
    {
        dernierChangementEtat = maintenant;
        if (Serial && debugMode)
        {
            Serial.print("[CAPTEURS] ");
            Serial.print("Pattern: ");
            Serial.print(pattern, BIN);
            Serial.print(" → ");
        }

        switch (pattern)
        {
        case 0b010: // milieu détecté
            if (Serial)
                Serial.println("AVANCE");
            avancerToutDroit();
            break;
        case 0b011:
        case 0b001: // droite détectée
            if (Serial)
                Serial.println("LÉGÈRE CORRECTION GAUCHE");
            corrigerGaucheLent();
            break;
        case 0b110:
        case 0b100: // gauche détectée
            if (Serial)
                Serial.println("LÉGÈRE CORRECTION DROITE");
            corrigerDroiteLent();
            break;
        case 0b111: // tout noir
            if (Serial)
                Serial.println("STOP ou INTERSECTION");
            delay(1);
            avancerToutDroit(); // ou gérer virage/intersection
            break;
        case 0b000: // tout blanc
            if (Serial)
                Serial.println("PLUS DE LIGNE – RECUL ou STOP");
            delay(50);
            arreter();
            break;
        default:
            if (Serial)
                Serial.println("ÉTAT INCONNU");
            break;
        }

        dernierEtatCapteurs = pattern;
    }
}

void setup()
{
    Serial.begin(115200);

    initialiser_moteurs();
    initialiser_capteurs();
    delay(50); // Court délai de stabilisation
    initialiser_nfc();

    if (Serial)
    {
        Serial.println("[INIT] Système démarré");
        Serial.println("[INIT] Suivi de ligne + NFC actifs");
    }
}

void loop()
{
    suiviLigne(); // Priorité au suivi de ligne
    lireNFC();
    //    unsigned long maintenant = millis();
    //     if (maintenant - derniereLectureNFC >= INTERVALLE_NFC) {

    //         derniereLectureNFC = maintenant;
    //     }

    delay(10); // Délai minimal pour stabilité
}