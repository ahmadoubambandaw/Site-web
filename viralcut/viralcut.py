#!/usr/bin/env python3
"""
ViralCut - Montage TikTok automatique pour contenus football.

Donne-lui une video brute (match, gaming, entrainement...) et il produit
un montage vertical 9:16 pret a poster :
  1. Analyse la piste audio pour reperer les temps forts (buts, cris,
     ambiance qui monte) via les pics d'energie sonore.
  2. Coupe et assemble les meilleurs moments (cuts rapides, style viral).
  3. Recadre en 1080x1920 avec fond flou (aucune bande noire).
  4. Ajoute un "punch zoom" un segment sur deux pour le dynamisme.
  5. Incruste un texte d'accroche (hook) et ton @pseudo.
  6. Normalise le son (loudnorm) + musique de fond optionnelle.

Usage :
    python3 viralcut.py match.mp4 -o tiktok.mp4 \
        --hook "CE BUT A CHOQUE TOUT LE STADE" --handle "@monpseudo"

Dependances : ffmpeg/ffprobe uniquement (pas de bibliotheque Python externe).
"""

import argparse
import array
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import tempfile

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

OUT_W, OUT_H, OUT_FPS = 1080, 1920, 30
ANALYSIS_RATE = 4000        # Hz, mono - suffisant pour mesurer l'energie
WINDOW_SEC = 0.5            # taille de fenetre d'analyse RMS


class VideoInfo:
    def __init__(self, duration, width, height, has_audio):
        self.duration = duration
        self.width = width
        self.height = height
        self.has_audio = has_audio


def run(cmd, **kw):
    """Execute une commande, leve une erreur claire si echec."""
    res = subprocess.run(cmd, capture_output=True, **kw)
    if res.returncode != 0:
        stderr = res.stderr.decode("utf-8", "replace")[-2000:]
        raise RuntimeError(f"Commande echouee: {' '.join(map(str, cmd))}\n{stderr}")
    return res


def probe(path):
    res = run([FFPROBE, "-v", "error", "-print_format", "json",
               "-show_format", "-show_streams", str(path)])
    data = json.loads(res.stdout)
    duration = float(data["format"].get("duration", 0))
    width = height = 0
    has_audio = False
    for s in data.get("streams", []):
        if s["codec_type"] == "video" and not width:
            width, height = int(s.get("width", 0)), int(s.get("height", 0))
        elif s["codec_type"] == "audio":
            has_audio = True
    if not width or duration <= 0:
        raise RuntimeError("Fichier video illisible ou sans piste video.")
    return VideoInfo(duration, width, height, has_audio)


def audio_rms_profile(path):
    """Decode l'audio en PCM mono et retourne l'energie RMS par fenetre."""
    res = run([FFMPEG, "-v", "error", "-i", str(path), "-vn",
               "-ac", "1", "-ar", str(ANALYSIS_RATE), "-f", "s16le", "-"])
    samples = array.array("h")
    samples.frombytes(res.stdout[: len(res.stdout) // 2 * 2])
    win = int(WINDOW_SEC * ANALYSIS_RATE)
    if len(samples) < win:
        return []
    rms = []
    for i in range(0, len(samples) - win + 1, win):
        acc = 0
        for s in samples[i:i + win]:
            acc += s * s
        rms.append(math.sqrt(acc / win))
    # lissage leger (moyenne glissante sur 3) pour eviter les faux pics
    if len(rms) >= 3:
        rms = [rms[0]] + [(rms[i - 1] + rms[i] + rms[i + 1]) / 3
                          for i in range(1, len(rms) - 1)] + [rms[-1]]
    return rms


def pick_segments(rms, duration, target, pre, post):
    """Choisit les segments les plus intenses, retournes en ordre chronologique."""
    if duration <= target + 2:
        return [(0.0, duration)]

    seg_len = pre + post
    if not rms or max(rms) <= 0:
        # Pas d'audio exploitable : segments repartis uniformement
        count = max(1, int(target // seg_len))
        step = duration / count
        return [(min(duration - seg_len, i * step + step / 2 - pre) if duration > seg_len else 0,
                 min(duration, i * step + step / 2 + post)) for i in range(count)]

    med = statistics.median(rms)
    scores = list(rms)
    picked = []
    budget = target
    while budget > 1.0:
        idx = max(range(len(scores)), key=scores.__getitem__)
        # On s'arrete si plus aucun moment ne sort du lot
        if scores[idx] <= 0 or (picked and med > 0 and scores[idx] < 1.1 * med):
            break
        t = idx * WINDOW_SEC + WINDOW_SEC / 2
        start = max(0.0, t - pre)
        end = min(duration, t + post)
        # neutralise le voisinage pour ne pas repiocher le meme moment
        z0 = max(0, int((start - 3) / WINDOW_SEC))
        z1 = min(len(scores), int((end + 3) / WINDOW_SEC) + 1)
        for j in range(z0, z1):
            scores[j] = 0
        picked.append([start, end])
        budget -= end - start

    picked.sort()
    merged = []
    for seg in picked:
        if merged and seg[0] <= merged[-1][1] + 0.25:
            merged[-1][1] = max(merged[-1][1], seg[1])
        else:
            merged.append(seg)

    # Respecte la duree cible en rognant la fin si besoin
    total = 0.0
    final = []
    for start, end in merged:
        if total >= target:
            break
        if total + (end - start) > target:
            end = start + (target - total)
        if end - start >= 0.8:
            final.append((start, end))
            total += end - start
    return final or [(0.0, min(duration, target))]


def vertical_filter(punch_zoom):
    """Filtre video : cadrage 9:16 avec fond flou + punch zoom optionnel."""
    chain = (
        f"[0:v]split[bg_in][fg_in];"
        f"[bg_in]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
        f"crop={OUT_W}:{OUT_H},boxblur=20:2,eq=brightness=-0.06[bg];"
        f"[fg_in]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
    )
    if punch_zoom:
        chain += f",crop=iw/1.08:ih/1.08,scale={OUT_W}:{OUT_H}"
    chain += f",fps={OUT_FPS},setsar=1,format=yuv420p[v]"
    return chain


def render_segment(src, start, end, dest, punch_zoom, has_audio):
    dur = end - start
    cmd = [FFMPEG, "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}",
           "-i", str(src)]
    if not has_audio:
        cmd += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100"]
    fc = vertical_filter(punch_zoom)
    audio_src = "[0:a]" if has_audio else "[1:a]"
    fc += f";{audio_src}aresample=44100,aformat=channel_layouts=stereo[a]"
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-f", "mpegts", str(dest)]
    run(cmd)


def build_drawtext(textfile, fontsize, y_expr, start, end, font=FONT_BOLD,
                   color="white", border=6):
    return (
        f"drawtext=fontfile={font}:textfile={textfile}:fontsize={fontsize}:"
        f"fontcolor={color}:borderw={border}:bordercolor=black:"
        f"line_spacing=12:x=(w-text_w)/2:y={y_expr}:"
        f"enable='between(t,{start},{end})'"
    )


def hook_fontsize(text):
    longest = max(len(line) for line in text.split("\n"))
    return max(40, min(84, int(980 / (0.62 * max(longest, 1)))))


def assemble(seg_files, out_path, hook, handle, has_music, music_path, tmp):
    concat_list = os.path.join(tmp, "list.txt")
    with open(concat_list, "w") as f:
        for seg in seg_files:
            f.write(f"file '{seg}'\n")

    vf_parts = []
    if hook:
        hook_file = os.path.join(tmp, "hook.txt")
        with open(hook_file, "w") as f:
            f.write(hook)
        vf_parts.append(build_drawtext(hook_file, hook_fontsize(hook),
                                       "h*0.14", 0.2, 3.2))
    if handle:
        handle_file = os.path.join(tmp, "handle.txt")
        with open(handle_file, "w") as f:
            f.write(handle)
        vf_parts.append(build_drawtext(handle_file, 34, "h-170", 0, 99999,
                                       font=FONT_REG, color="white@0.85",
                                       border=2))
    vchain = "[0:v]" + (",".join(vf_parts) + "," if vf_parts else "") + "null[v]"

    cmd = [FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0",
           "-i", concat_list]
    if has_music:
        cmd += ["-stream_loop", "-1", "-i", str(music_path)]
        achain = ("[1:a]volume=0.35,aformat=channel_layouts=stereo[m];"
                  "[0:a][m]amix=inputs=2:duration=first:normalize=0,"
                  "loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    else:
        achain = "[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    achain += ";[a]aresample=44100[aout]"

    cmd += ["-filter_complex", vchain + ";" + achain,
            "-map", "[v]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-r", str(OUT_FPS), "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out_path)]
    run(cmd)


def make_viral(input_path, output_path, target_duration=30.0, hook="",
               handle="", music=None, punch_zoom=True, pre=2.5, post=3.5,
               progress=print):
    """Pipeline complet. `progress` recoit des messages d'avancement."""
    info = probe(input_path)
    progress(f"Video : {info.width}x{info.height}, "
             f"{info.duration:.1f}s, audio={'oui' if info.has_audio else 'non'}")

    rms = audio_rms_profile(input_path) if info.has_audio else []
    progress("Analyse audio terminee, selection des temps forts...")
    segments = pick_segments(rms, info.duration, target_duration, pre, post)
    progress("Temps forts retenus : " +
             ", ".join(f"{s:.1f}s-{e:.1f}s" for s, e in segments))

    tmp = tempfile.mkdtemp(prefix="viralcut_")
    try:
        seg_files = []
        for i, (start, end) in enumerate(segments):
            progress(f"Montage du segment {i + 1}/{len(segments)}...")
            seg = os.path.join(tmp, f"seg_{i:03d}.ts")
            render_segment(input_path, start, end, seg,
                           punch_zoom and i % 2 == 1, info.has_audio)
            seg_files.append(seg)

        progress("Assemblage final (texte, son, export 1080x1920)...")
        assemble(seg_files, output_path, hook, handle,
                 music is not None, music, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    progress(f"Termine : {output_path}")
    return output_path


def main():
    p = argparse.ArgumentParser(description="Montage TikTok automatique")
    p.add_argument("input", help="video source (mp4, mov, mkv...)")
    p.add_argument("-o", "--output", default="viral.mp4")
    p.add_argument("--duration", type=float, default=30.0,
                   help="duree cible du montage en secondes (defaut 30)")
    p.add_argument("--hook", default="", help="texte d'accroche affiche au debut"
                   " (utilise | pour un saut de ligne)")
    p.add_argument("--handle", default="", help="ton @pseudo en filigrane")
    p.add_argument("--music", default=None, help="musique de fond optionnelle")
    p.add_argument("--no-zoom", action="store_true",
                   help="desactive le punch zoom alterne")
    p.add_argument("--pre", type=float, default=2.5,
                   help="secondes gardees avant chaque pic (defaut 2.5)")
    p.add_argument("--post", type=float, default=3.5,
                   help="secondes gardees apres chaque pic (defaut 3.5)")
    args = p.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"Fichier introuvable : {args.input}")
    if args.music and not os.path.exists(args.music):
        sys.exit(f"Musique introuvable : {args.music}")

    make_viral(args.input, args.output, args.duration,
               args.hook.replace("|", "\n"), args.handle, args.music,
               not args.no_zoom, args.pre, args.post)


if __name__ == "__main__":
    main()
