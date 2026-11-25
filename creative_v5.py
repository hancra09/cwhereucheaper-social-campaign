"""creative-v5 look (Owner request, 25 November 2026).

Full-bleed motion backgrounds, kinetic headlines, word-by-word captions synced to the
narration, animated price cards, a CWUC website bridge and a free-account end card.
Original generated visuals plus the real CWUC homepage capture; no music, stock media
or paid API. Disclosure stays on screen as a compact tag.
"""
import math
import re
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H, FPS = 1080, 1920, 30
NAVY = (7, 27, 54)
NAVY2 = (14, 52, 98)
YELLOW = (255, 230, 90)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (240, 72, 72)
GREEN = (60, 200, 120)
GREY = (168, 183, 204)


def clamp(x):
    return max(0.0, min(1.0, x))


def ease_out(x):
    return 1 - (1 - clamp(x)) ** 3


def ease_back(x):
    x = clamp(x)
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


class Renderer:
    def __init__(self, cfg, narration, assets, giveaway_card=None):
        self.cfg = cfg
        self.cuts = narration['cuts']
        self.total = narration['duration']
        self.giveaway_card = giveaway_card
        fonts = assets / 'fonts'
        self._anton = str(fonts / 'Anton-Regular.ttf')
        self._mont = str(fonts / 'Montserrat-Variable.ttf')
        self._cache = {}
        photo = Image.open(assets / cfg['asset']).convert('RGB')
        self.photo = ImageOps.fit(photo, (1300, 2311), Image.Resampling.LANCZOS)
        self.halves = None
        if cfg['asset'] in ('pouches.png', 'bottles.png'):
            split = {'pouches.png': 540, 'bottles.png': 515}[cfg['asset']]
            self.halves = [ImageOps.fit(photo.crop(box), (1300, 2311), Image.Resampling.LANCZOS)
                           for box in ((0, 0, split, photo.height), (split, 0, photo.width, photo.height))]
        self.blur = self.photo.filter(ImageFilter.GaussianBlur(28))
        self.web = Image.open(assets / 'website.png').convert('RGB')
        self.shade = self._gradient()
        self.words = self._word_times()

    # ------------------------------------------------------------------ fonts
    def font(self, kind, size, weight=b'Black'):
        key = (kind, size, weight)
        if key not in self._cache:
            if kind == 'head':
                f = ImageFont.truetype(self._anton, size)
            else:
                f = ImageFont.truetype(self._mont, size)
                f.set_variation_by_name(weight)
            self._cache[key] = f
        return self._cache[key]

    # ------------------------------------------------------------------ timing
    def _word_times(self):
        out = []
        for i, (_, line) in enumerate(self.cfg['beats']):
            start, end = self.cuts[i] + 0.05, self.cuts[i + 1] - 0.24
            words = line.split()
            weights = [len(re.sub(r'\W', '', w)) + 2.5 for w in words]
            total = sum(weights) or 1
            t = start
            beat = []
            for w, wt in zip(words, weights):
                d = (end - start) * wt / total
                beat.append((w, t, t + d))
                t += d
            out.append(beat)
        return out

    def _gradient(self):
        g = Image.new('L', (1, H))
        for y in range(H):
            top = clamp((620 - y) / 620) * 200
            bottom = clamp((y - 1050) / 870) * 235
            g.putpixel((0, y), int(max(top, bottom)))
        return g.resize((W, H))

    # ------------------------------------------------------------------ helpers
    def beat_at(self, t):
        for i, end in enumerate(self.cuts[1:]):
            if t < end:
                return i
        return len(self.cuts) - 2

    def ken_burns(self, img, local, z0, z1, dur, fx=.5, fy=.45, dx=0):
        p = clamp(local / max(dur, .1))
        z = z0 + (z1 - z0) * p
        w, h = int(W * z), int(H * z)
        im = img.resize((w, h), Image.Resampling.BILINEAR)
        x = int((w - W) * fx + dx * p)
        y = int((h - H) * fy)
        x = max(0, min(w - W, x))
        return im.crop((x, y, x + W, y + H))

    def darken(self, im):
        im.paste(Image.new('RGB', (W, H), BLACK), (0, 0), self.shade)
        return im

    def fit_size(self, text, kind, size, width, weight=b'Black'):
        d = ImageDraw.Draw(Image.new('L', (1, 1)))
        while size > 40 and d.textbbox((0, 0), text, font=self.font(kind, size, weight))[2] > width:
            size -= 4
        return size

    def wrap(self, text, kind, size, width):
        d = ImageDraw.Draw(Image.new('L', (1, 1)))
        lines, cur = [], ''
        for w in text.split():
            cand = (cur + ' ' + w).strip()
            if cur and d.textbbox((0, 0), cand, font=self.font(kind, size))[2] > width:
                lines.append(cur)
                cur = w
            else:
                cur = cand
        if cur:
            lines.append(cur)
        return lines

    def headline(self, im, text, local, y=250, hl=YELLOW, ink=NAVY):
        """Kinetic headline: drops in with overshoot, highlighted block letters."""
        size = 128
        lines = self.wrap(text, 'head', size, 900)
        while len(lines) > 2 and size > 84:
            size -= 8
            lines = self.wrap(text, 'head', size, 900)
        f = self.font('head', size)
        layer = Image.new('RGBA', (W, 520), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        cy = 20
        for line in lines:
            box = d.textbbox((0, 0), line, font=f)
            tw, th = box[2] - box[0], box[3] - box[1]
            x = (W - tw) // 2
            d.rounded_rectangle((x - 30, cy - 6, x + tw + 30, cy + th + box[1] + 26), 18, fill=hl + (255,))
            d.text((x - box[0], cy), line, font=f, fill=ink)
            cy += th + box[1] + 44
        layer = layer.crop((0, 0, W, cy + 10))
        p = ease_back(local / .32)
        scale = .6 + .4 * p
        if scale != 1:
            lw, lh = max(1, int(layer.width * scale)), max(1, int(layer.height * scale))
            layer = layer.resize((lw, lh), Image.Resampling.BILINEAR)
        alpha = clamp(local / .12)
        if alpha < 1:
            layer.putalpha(layer.getchannel('A').point(lambda a: int(a * alpha)))
        im.paste(layer, ((W - layer.width) // 2, y - int(40 * (1 - ease_out(local / .3)))), layer)

    def captions(self, im, beat, t, y=1250):
        """Three-word caption chunks with the spoken word highlighted and popped."""
        words = self.words[beat]
        if not words:
            return
        idx = 0
        for i, (_, s, _) in enumerate(words):
            if t >= s:
                idx = i
        chunk_start = idx - idx % 3
        chunk = words[chunk_start:chunk_start + 3]
        text = ' '.join(w for w, _, _ in chunk).upper()
        size = self.fit_size(text, 'cap', 92, 940)
        f = self.font('cap', size)
        d = ImageDraw.Draw(im)
        widths = [d.textbbox((0, 0), w.upper() + ' ', font=f)[2] for w, _, _ in chunk]
        x = (W - sum(widths) + d.textbbox((0, 0), ' ', font=f)[2]) // 2
        for j, (w, s, e) in enumerate(chunk):
            active = chunk_start + j == idx
            word = w.upper()
            if active:
                pop = 1 + .14 * (1 - ease_out((t - s) / .14))
                fa = self.font('cap', int(size * pop))
                bb = d.textbbox((0, 0), word, font=fa)
                ox = x + (d.textbbox((0, 0), word, font=f)[2] - bb[2]) // 2
                d.text((ox, y - (bb[3] - d.textbbox((0, 0), word, font=f)[3]) // 2), word, font=fa,
                       fill=YELLOW, stroke_width=9, stroke_fill=BLACK)
            else:
                d.text((x, y), word, font=f, fill=WHITE, stroke_width=9, stroke_fill=BLACK)
            x += widths[j]

    def tag(self, im):
        cfg = self.cfg
        if cfg.get('synthetic_test'):
            label, fill = 'SIMULATED VIEWER REQUEST', (139, 36, 56)
        elif cfg.get('is_price_evidence'):
            label, fill = 'PRICE CHECK · AI VISUALS', NAVY
        elif cfg.get('is_example'):
            label, fill = 'EXAMPLE PRICES · AI VISUALS', NAVY
        else:
            label, fill = 'AI VISUALS', NAVY
        f = self.font('cap', 30, b'Bold')
        d = ImageDraw.Draw(im)
        tw = d.textbbox((0, 0), label, font=f)[2]
        d.rounded_rectangle((60, 120, 60 + tw + 44, 176), 28, fill=fill)
        d.text((82, 131), label, font=f, fill=WHITE)

    def progress(self, im, t):
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, 12), fill=(30, 40, 60))
        d.rectangle((0, 0, int(W * t / self.total), 12), fill=YELLOW)

    def whip(self, im, local):
        """Quick slide-in transition at each cut."""
        if local >= .14:
            return im
        off = int(160 * (1 - ease_out(local / .14)))
        out = Image.new('RGB', (W, H), BLACK)
        out.paste(im, (off, 0))
        return out

    # ------------------------------------------------------------------ scenes
    def scene_photo(self, beat, local, dur):
        src = self.photo
        if self.halves and beat in (1, 2):
            src = self.halves[beat - 1]
        if beat == 0:
            im = self.ken_burns(src, local, 1.22, 1.06, dur, .5, .42)
        elif beat == 1:
            im = self.ken_burns(src, local, 1.10, 1.24, dur, .35, .45)
        else:
            im = self.ken_burns(src, local, 1.30, 1.16, dur, .62, .5)
        return self.darken(im)

    def scene_compare(self, local, dur):
        (a, b), win = self.cfg['compare']
        im = self.ken_burns(self.blur, local, 1.05, 1.1, dur)
        im = Image.blend(im, Image.new('RGB', (W, H), NAVY), .72)
        d = ImageDraw.Draw(im)
        for i, (label, value) in enumerate((a, b)):
            p = ease_back((local - .1 - i * .18) / .4)
            x0 = 80 + i * 480
            y0 = 640 + int((1 - p) * 500)
            winner = i == win
            reveal = local > .9
            fill = (255, 255, 255) if not (reveal and not winner) else (120, 130, 150)
            d.rounded_rectangle((x0, y0, x0 + 440, y0 + 560), 36, fill=fill,
                                outline=YELLOW if (reveal and winner) else None, width=12)
            lf = self.font('cap', self.fit_size(label, 'cap', 46, 380, b'ExtraBold'), b'ExtraBold')
            lw = d.textbbox((0, 0), label, font=lf)[2]
            d.text((x0 + 220 - lw // 2, y0 + 70), label, font=lf, fill=NAVY)
            vf = self.font('head', self.fit_size(value, 'head', 150, 390))
            vw = d.textbbox((0, 0), value, font=vf)[2]
            d.text((x0 + 220 - vw // 2, y0 + 190), value, font=vf, fill=NAVY)
            if reveal and not winner:
                d.line((x0 + 40, y0 + 470, x0 + 400, y0 + 130), fill=RED, width=18)
        if local > .9:
            p = ease_back((local - .9) / .3)
            stamp = Image.new('RGBA', (520, 150), (0, 0, 0, 0))
            sd = ImageDraw.Draw(stamp)
            sd.rounded_rectangle((0, 0, 519, 149), 30, fill=GREEN + (255,))
            sf = self.font('head', 96)
            sw = sd.textbbox((0, 0), 'CHEAPER', font=sf)[2]
            sd.text(((520 - sw) // 2, 8), 'CHEAPER', font=sf, fill=WHITE)
            stamp = stamp.rotate(-8, expand=True, resample=Image.Resampling.BICUBIC)
            s = .4 + .6 * p
            stamp = stamp.resize((max(1, int(stamp.width * s)), max(1, int(stamp.height * s))))
            cx = 80 + win * 480 + 220
            im.paste(stamp, (cx - stamp.width // 2, 1150 - stamp.height // 2), stamp)
        return im

    def scene_site(self, local, dur):
        """The CWUC bridge: real homepage capture in a floating browser card."""
        im = Image.new('RGB', (W, H), NAVY)
        d = ImageDraw.Draw(im)
        for y in range(0, H, 6):
            k = y / H
            d.rectangle((0, y, W, y + 6), fill=tuple(int(NAVY[c] * (1 - k) + NAVY2[c] * k) for c in range(3)))
        p = ease_out(local / .45)
        z = 1.0 + .5 * clamp(local / max(dur, .1))
        cw, ch = 960, 760
        crop_w, crop_h = int(self.web.width / z), int(self.web.width / z * ch / cw)
        crop_h = min(crop_h, self.web.height)
        x = int((self.web.width - crop_w) * .18)
        y = int((self.web.height - crop_h) * .35)
        shot = self.web.crop((x, y, x + crop_w, y + crop_h)).resize((cw, ch), Image.Resampling.LANCZOS)
        card = Image.new('RGB', (cw + 24, ch + 100), (240, 242, 246))
        cd = ImageDraw.Draw(card)
        for i, c in enumerate(((240, 90, 90), (245, 190, 60), (80, 200, 110))):
            cd.ellipse((24 + i * 40, 30, 50 + i * 40, 56), fill=c)
        cd.rounded_rectangle((160, 22, cw - 10, 64), 20, fill=WHITE)
        cd.text((184, 28), 'cwhereucheaper.co.za', font=self.font('cap', 28, b'SemiBold'), fill=(60, 70, 90))
        card.paste(shot, (12, 88))
        mask = Image.new('L', card.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, card.width - 1, card.height - 1), 30, fill=255)
        cy = 720 + int((1 - p) * 700)
        shadow = Image.new('L', (card.width + 80, card.height + 80), 0)
        ImageDraw.Draw(shadow).rounded_rectangle((40, 50, card.width + 40, card.height + 50), 40, fill=150)
        shadow = shadow.filter(ImageFilter.GaussianBlur(24))
        im.paste(BLACK, ((W - card.width) // 2 - 40, cy - 40), shadow)
        im.paste(card, ((W - card.width) // 2, cy), mask)
        # tap ripple on the search area
        if local > .8:
            r = int(30 + 90 * ((local - .8) % 1.0))
            a = 1 - ((local - .8) % 1.0)
            cx, cyy = W // 2 - 60, cy + 560
            ring = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse((cx - r, cyy - r, cx + r, cyy + r), outline=YELLOW + (int(255 * a),), width=10)
            im.paste(ring, (0, 0), ring)
        return im

    def scene_end(self, t, local):
        im = Image.new('RGB', (W, H), NAVY)
        d = ImageDraw.Draw(im)
        for i in range(-H, W, 140):
            d.line((i, H, i + H, 0), fill=(11, 36, 70), width=50)
        for k, (line, col, y) in enumerate((('FREE', YELLOW, 360), ('ACCOUNT', WHITE, 560))):
            pk = ease_back((local - k * .12) / .35)
            sz = max(10, int(170 * (.5 + .5 * pk)))
            fk = self.font('head', sz)
            tw = d.textbbox((0, 0), line, font=fk)[2]
            d.text(((W - tw) // 2, y), line, font=fk, fill=col)
        sub = 'Same product. Every shop. One search.'
        sf = self.font('cap', self.fit_size(sub, 'cap', 46, 900, b'Bold'), b'Bold')
        sw = d.textbbox((0, 0), sub, font=sf)[2]
        d.text(((W - sw) // 2, 820), sub, font=sf, fill=GREY)
        pulse = 1 + .04 * math.sin(local * 7)
        pw, ph = int(900 * pulse), int(150 * pulse)
        x0, y0 = (W - pw) // 2, 1000 - (ph - 150) // 2
        d.rounded_rectangle((x0, y0, x0 + pw, y0 + ph), ph // 2, fill=YELLOW)
        uf = self.font('cap', self.fit_size('cwhereucheaper.co.za', 'cap', 66, pw - 80), b'Black')
        uw = d.textbbox((0, 0), 'cwhereucheaper.co.za', font=uf)
        d.text(((W - uw[2]) // 2, y0 + (ph - uw[3]) // 2 - 6), 'cwhereucheaper.co.za', font=uf, fill=NAVY)
        if local > .4:
            bob = int(14 * math.sin(local * 6))
            lf = self.font('head', 92)
            lt = 'LINK IN BIO'
            lw = d.textbbox((0, 0), lt, font=lf)[2]
            ax = W // 2
            d.polygon([(ax - 40, 1250 + bob), (ax + 40, 1250 + bob), (ax, 1205 + bob)], fill=YELLOW)
            d.text(((W - lw) // 2, 1270 + bob), lt, font=lf, fill=WHITE)
        return im

    # ------------------------------------------------------------------ frame
    def frame(self, t):
        beat = self.beat_at(t)
        last = len(self.cfg['beats']) - 1
        local = t - self.cuts[beat]
        dur = self.cuts[beat + 1] - self.cuts[beat]
        if beat == last and self.giveaway_card:
            return self.giveaway_card(t)
        headline = self.cfg['beats'][beat][0]
        bridge = beat == last - 1 and re.search(r'cwhereucheaper|cwuc', self.cfg['beats'][beat][1], re.I)
        if beat == last:
            im = self.scene_end(t, local)
            self.captions(im, beat, t, y=1520)
        elif bridge:
            im = self.scene_site(local, dur)
            self.headline(im, headline, local, y=250)
            self.captions(im, beat, t, y=1640)
        elif beat == 2 and self.cfg.get('compare'):
            im = self.scene_compare(local, dur)
            self.headline(im, headline, local, y=250)
            self.captions(im, beat, t, y=1430)
        else:
            im = self.scene_photo(beat, local, dur)
            if beat == 0 and local < .09:
                im = Image.blend(im, Image.new('RGB', (W, H), WHITE), .7 * (1 - local / .09))
            self.headline(im, headline, local, y=260, hl=YELLOW if beat != 1 else WHITE)
            self.captions(im, beat, t)
        im = self.whip(im, local) if beat else im
        self.tag(im)
        self.progress(im, t)
        return im
