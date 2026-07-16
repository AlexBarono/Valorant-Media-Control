# Game Media Control

Kleines Windows-Tool mit modernem Windows-Setup und drei Tabs:

- **Valorant**: Rot im gewaehlten Bildschirmbereich gilt als `tot`, kein Rot als `nicht tot`.
- **LoL**: Eine Zahl oder ein Countdown im gewaehlten Bildschirmbereich gilt als `tot`, keine Zahl als `nicht tot`.

Pro Tab kannst du getrennt einstellen, ob das Tool `Play/Pause` sendet oder nur die Lautstaerke einer ausgewaehlten Medienwiedergabe aendert.

Der dritte Tab zeigt diese README direkt im Programm.

Das Tool liest nur den Bildschirm und sendet normale Windows-Medientasten. Es greift nicht in Spiel-Speicher, Dateien, Netzwerk oder Anti-Cheat ein.

## Installation

Die fertige Setup-Datei heisst `Game Media Control Setup.exe` und liegt nach dem Build im Ordner `setup`.

Das Setup bietet:

- Installation nur fuer den aktuellen Benutzer unter `%LOCALAPPDATA%\Programs\Game Media Control\`
- Installation fuer alle Benutzer unter `C:\Program Files\Game Media Control\` bei 64-Bit oder `C:\Program Files (x86)\Game Media Control\` bei 32-Bit
- Lizenzvereinbarung mit ausdruecklicher Zustimmung
- optionale Desktopverknuepfung
- Startmenue-Eintrag
- optionalen Autostart-Waechter fuer Valorant und/oder League of Legends
- Deinstaller mit optionalem Loeschen der persoenlichen Daten

Zum Bauen:

```powershell
.\build_release.ps1
```

## Start

1. `start_valorant_media_guard.bat` doppelklicken.
2. Wenn Python fehlt, fragt die Startdatei, ob Python installiert werden soll.
3. Den passenden Tab auswaehlen: `Valorant` oder `LoL`.
4. Im Spiel am besten `Fenster-Vollbild` oder `Randlos` nutzen, falls Screenshots bei exklusivem Vollbild schwarz bleiben.
5. `Bereich waehlen` klicken und den Bereich markieren, der ueberwacht werden soll.
6. Bei Valorant `Farbe waehlen` klicken oder die Farbe manuell eintragen, z. B. `#ff4655` oder `255,70,85`.
7. Unter `Medienwiedergabe` auf `Aktualisieren` klicken und z. B. Spotify, Browser oder Player auswaehlen.
8. Entweder `Play/Pause steuern` oder `Nur Lautstaerke anpassen` waehlen.
9. Bei Lautstaerke-Modus `Tot %` und `Nicht tot %` eintragen und mit `Test Tot` / `Test Nicht tot` pruefen.
10. `Start` klicken.

## Valorant-Tipps

- `Rot %`: So viel Prozent des gewaehlten Bereichs muessen die gespeicherte Farbe enthalten. Standard: `1.0`.
- `Farbe`: Die erkannte Farbe wird als Farbfeld und Text angezeigt. Manuell moeglich sind z. B. `#ff4655`, `ff4655`, `255,70,85`, `rgb(255,70,85)` oder `rgba(255,70,85,1)`.
- `Toleranz`: Standard ist `0`, damit nur exakt die gespeicherte Farbe erkannt wird.

## LoL-Tipps

- Markiere nur den kleinen Bereich, in dem die Zahl herunterzaehlt. Je kleiner und klarer der Bereich ist, desto besser.
- `Hell %`: So viel Prozent des Bereichs muessen helle Pixel enthalten. Standard: `0.25`.
- `Hell min`: Ab welchem Farbwert ein Pixel als hell gilt. Standard: `150`.
- `Ziffer Hoehe` und `Ziffer Flaeche`: Mindestgroesse fuer ziffernartige Formen.
- `Komponenten`: Wie viele ziffernartige Formen mindestens gefunden werden muessen. Standard: `1`.

## Allgemein

- Oben im Programm steht die installierte Version und die neueste Version auf GitHub.
- Wenn GitHub neuer ist, erscheint der Button `Jetzt aktualisieren`.
- Das Update laedt bei der EXE eine neue EXE von GitHub, ersetzt die alte Datei nach dem Schliessen und startet die App neu. Im Quellordner wird weiterhin per ZIP aktualisiert.
- Git muss fuer normale Nutzer nicht installiert sein.
- Die Oberflaeche unterstuetzt Hell/Dunkel/System-Design.
- Die Inhalte der Tabs sind scrollbar und bleiben auch auf kleinen Bildschirmen sowie bei hoher Windows-Skalierung nutzbar.
- Die automatische Spielerkennung wird durch `Game Media Watcher.exe` umgesetzt. Der Watcher prueft nur laufende Prozessnamen und greift nicht in Spiele ein.
- Erkannte Prozesse:
  - Valorant: `VALORANT-Win64-Shipping.exe`, `RiotClientServices.exe`
  - League of Legends: `LeagueClient.exe`, `LeagueClientUx.exe`, `League of Legends.exe`
- Ein PNG-Ersatzbild mit `gif` im Dateinamen wird als Headerbild genutzt; `Gangcord.gif` bleibt nur Fallback.
- `logo der app.png` wird als App-Logo genutzt.
- Valorant und LoL speichern Bereich, Ziel, Modus und Lautstaerke getrennt.
- Wenn die Erkennung wackelt, waehle einen kleineren, klareren Bereich.
- Wenn dein Mediaplayer direkte `Play`/`Pause`-Befehle ignoriert, stelle in der App auf `Fallback: Medien-Toggle bei jedem Wechsel`.
- Die Medienziel-Auswahl wirkt auf die Lautstaerke der ausgewaehlten Windows-Audio-Sitzung.
- `Stabil` hoeher machen, wenn kurze Bildschirmwechsel stoeren.
- Die Einstellungen werden unter `%LOCALAPPDATA%\Game Media Control\config.json` gespeichert. Logs liegen unter `%LOCALAPPDATA%\Game Media Control\Logs\`. Neben der EXE wird keine neue Konfigurationsdatei angelegt.
