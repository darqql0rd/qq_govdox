"""Bildvarianten: scan.jpg (300 dpi, sauber) und foto.jpg (Handyfoto-Simulation).

Mehrseitige PDFs: Seite 1 -> scan.jpg / foto.jpg, weitere Seiten -> scan_s2.jpg, foto_s2.jpg, ...
unlesbar=True: foto.jpg wird stark beschädigt (Unschärfe, Bewegung, Blendung, sehr tiefe Auflösung).
"""
import glob, os, subprocess, tempfile
import cv2
import numpy as np


def _render(pdf, dpi, prefix):
    subprocess.run(["pdftoppm", "-r", str(dpi), "-jpeg", "-jpegopt", "quality=92", pdf, prefix], check=True)
    return sorted(glob.glob(prefix + "-*.jpg"), key=lambda p: int(p.rsplit("-", 1)[1].split(".")[0]))


def _hintergrund(h, w, rng):
    base = rng.choice([(92, 118, 150), (70, 90, 115), (150, 160, 165), (60, 60, 62), (120, 140, 160)])
    bg = np.zeros((h, w, 3), np.float32) + np.array(base, np.float32)
    noise = rng.normal(0, 18, (h // 8 + 1, w // 8 + 1, 1)).astype(np.float32)
    noise = cv2.resize(noise, (w, h), interpolation=cv2.INTER_CUBIC)[..., None]
    streaks = cv2.GaussianBlur(rng.normal(0, 25, (h, 1, 1)).astype(np.float32), (1, 0), 9)
    bg += noise + np.repeat(streaks.reshape(h, 1, 1), w, axis=1) * 0.6
    return np.clip(bg, 0, 255)


def foto(src, dst, rng, unlesbar=False):
    img = cv2.imread(src)
    h0, w0 = img.shape[:2]
    scale = 1500 / w0
    img = cv2.resize(img, (int(w0 * scale), int(h0 * scale)), interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]
    pad = int(0.14 * w)
    H, W = h + 2 * pad, w + 2 * pad
    bg = _hintergrund(H, W, rng)

    j = 0.045 if not unlesbar else 0.10
    src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst_pts = src_pts + pad + rng.uniform(-j, j, (4, 2)).astype(np.float32) * np.float32([w, h])
    ang = np.deg2rad(rng.uniform(-3.5, 3.5) if not unlesbar else rng.choice([-1, 1]) * rng.uniform(8, 14))
    c = np.float32([W / 2, H / 2])
    R = np.float32([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
    dst_pts = (dst_pts - c) @ R.T + c
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(img, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0)).astype(np.float32)
    mask = cv2.warpPerspective(np.ones((h, w), np.float32), M, (W, H))
    mask = cv2.GaussianBlur(mask, (5, 5), 1.2)[..., None]
    # leichter Schlagschatten unter dem Blatt
    sh = cv2.GaussianBlur(cv2.warpAffine(mask[..., 0], np.float32([[1, 0, 12], [0, 1, 16]]), (W, H)), (0, 0), 14)[..., None]
    bg = bg * (1 - 0.45 * sh)
    out = warped * mask + bg * (1 - mask)

    # Beleuchtung: Verlauf + weicher Schatten (Hand/Handy)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    a = rng.uniform(0, 2 * np.pi)
    grad = ((xx / W - 0.5) * np.cos(a) + (yy / H - 0.5) * np.sin(a))
    light = 1.0 - (0.22 if not unlesbar else 0.45) * (grad - grad.min()) / (grad.max() - grad.min())
    cx, cy = rng.uniform(0.2, 0.8) * W, rng.uniform(0.55, 1.0) * H
    blob = np.exp(-(((xx - cx) / (0.28 * W)) ** 2 + ((yy - cy) / (0.20 * H)) ** 2))
    light *= 1 - (0.28 if not unlesbar else 0.6) * blob
    out *= light[..., None]
    out *= np.float32([rng.uniform(0.92, 1.0), rng.uniform(0.96, 1.02), rng.uniform(1.0, 1.08)])  # BGR: warmer Stich

    if unlesbar:
        gx, gy = rng.uniform(0.3, 0.7) * W, rng.uniform(0.2, 0.5) * H
        glare = np.exp(-(((xx - gx) / (0.25 * W)) ** 2 + ((yy - gy) / (0.18 * H)) ** 2))
        out = out + 230 * glare[..., None]
        k = np.zeros((31, 31), np.float32); k[15, :] = 1; k /= k.sum()
        k = cv2.warpAffine(k, cv2.getRotationMatrix2D((15, 15), rng.uniform(0, 180), 1), (31, 31))
        out = cv2.filter2D(out, -1, k / max(k.sum(), 1e-6))
        out = cv2.GaussianBlur(out, (0, 0), 4.5)
    else:
        out = cv2.GaussianBlur(out, (0, 0), rng.uniform(0.6, 1.1))
    out += rng.normal(0, 3.5 if not unlesbar else 10, out.shape).astype(np.float32)
    out = np.clip(out, 0, 255).astype(np.uint8)

    target = 1700 if not unlesbar else 520
    s = target / max(out.shape[:2])
    out = cv2.resize(out, (int(out.shape[1] * s), int(out.shape[0] * s)), interpolation=cv2.INTER_AREA)
    if unlesbar:  # nochmals hochskaliert, wie ein schlecht vergrössertes Bild
        out = cv2.resize(out, (out.shape[1] * 2, out.shape[0] * 2), interpolation=cv2.INTER_LINEAR)
    q = int(rng.integers(62, 76)) if not unlesbar else 12
    cv2.imwrite(dst, out, [cv2.IMWRITE_JPEG_QUALITY, q])


def erzeuge(pdf, outdir, seed=0, unlesbar=False):
    rng = np.random.default_rng(seed)
    with tempfile.TemporaryDirectory() as tmp:
        pages = _render(pdf, 300, os.path.join(tmp, "p"))
        for i, pg in enumerate(pages, start=1):
            suf = "" if i == 1 else f"_s{i}"
            os.replace(pg, os.path.join(outdir, f"scan{suf}.jpg"))
            foto(os.path.join(outdir, f"scan{suf}.jpg"), os.path.join(outdir, f"foto{suf}.jpg"), rng,
                 unlesbar=unlesbar and i == 1)
