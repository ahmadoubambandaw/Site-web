# ViralCut ⚽ — Montage TikTok automatique

Tu déposes une vidéo brute (match filmé, gameplay EA FC, entraînement,
tournoi de quartier...) et ViralCut sort un **montage vertical prêt à
poster sur TikTok** :

1. 🔊 **Détection des temps forts** — analyse de la piste audio : les pics
   d'énergie (buts, cris, ambiance qui explose) désignent les meilleurs
   moments.
2. ✂️ **Cuts rapides** — assemblage des moments retenus, style viral.
3. 📱 **Format 9:16 (1080×1920)** — recadrage avec fond flou, aucune bande
   noire, 30 fps.
4. 🔍 **Punch zoom** — léger zoom un segment sur deux pour le dynamisme.
5. 💬 **Texte d'accroche (hook)** incrusté les 3 premières secondes +
   ton `@pseudo` en filigrane.
6. 🎚️ **Son normalisé** (loudnorm -14 LUFS, le standard des plateformes)
   + musique de fond optionnelle.

## Prérequis

- Python 3.9+
- `ffmpeg` et `ffprobe` installés (`sudo apt install ffmpeg` /
  `brew install ffmpeg`)

```bash
pip install -r requirements.txt   # uniquement Flask, pour l'interface web
```

## Utilisation — interface web (recommandé)

```bash
python3 app.py
# puis ouvre http://localhost:5000
```

Glisse ta vidéo, écris ton accroche, clique **Créer mon montage viral**,
télécharge le résultat.

## Utilisation — ligne de commande

```bash
python3 viralcut.py match.mp4 -o tiktok.mp4 \
  --duration 30 \
  --hook "CE BUT A CHOQUE|TOUT LE STADE" \
  --handle "@tonpseudo" \
  --music beat.mp3
```

| Option | Description | Défaut |
|---|---|---|
| `--duration` | durée cible du montage (s) | 30 |
| `--hook` | texte d'accroche (`\|` = saut de ligne) | — |
| `--handle` | @pseudo en filigrane | — |
| `--music` | musique de fond (mixée à 35 %) | — |
| `--no-zoom` | désactive le punch zoom | — |
| `--pre` / `--post` | secondes gardées avant/après chaque pic | 2.5 / 3.5 |

## Comment ça marche ?

- L'audio est décodé en PCM mono, l'énergie RMS est mesurée par fenêtres
  de 0,5 s puis lissée.
- Les fenêtres les plus intenses sont sélectionnées une à une (avec une
  zone d'exclusion autour de chaque pic pour varier les moments), étendues
  en segments `[pic - 2,5 s ; pic + 3,5 s]`, fusionnées si elles se
  chevauchent, et rognées pour tenir dans la durée cible.
- Si la vidéo n'a pas d'audio exploitable, des segments répartis
  uniformément sont utilisés.
- Chaque segment est rendu en 1080×1920 (fond flou + recadrage centré),
  puis le tout est concaténé et stylisé en une passe finale ffmpeg.

## ⚠️ Rappel droits d'auteur

Les extraits de matchs officiels (Ligue 1, LDC, Premier League...) sont
protégés : TikTok peut couper le son ou retirer la vidéo. Utilise tes
propres images (gameplay, matchs amateurs, contenus face-cam) pour être
tranquille.
