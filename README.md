# Portfolio — ayushcreativeai.github.io

A single static page. No build step, no framework, no dependencies to install.
Edit the file, commit, push. GitHub Pages redeploys in one to two minutes.

---

## Editing this from any computer

### One-time setup on a new machine

```bash
# 1. install the GitHub CLI (skip if you already have it)
winget install --id GitHub.cli          # Windows
brew install gh                         # macOS

# 2. sign in - opens a browser, no password typed anywhere
gh auth login --web --git-protocol https

# 3. clone the repo
gh repo clone ayushcreativeai/ayushcreativeai.github.io
cd ayushcreativeai.github.io
```

### Making a change

```bash
git pull                                # always start here
# ...edit index.html...
git add -A
git commit -m "what changed"
git push
```

Then wait one to two minutes and hard-refresh the live site (Ctrl+Shift+R).

### Telling Codex (or any agent) what to do

Open the folder and give it this context:

> This is a single-file static portfolio. Everything lives in `index.html` —
> markup, CSS in one `<style>` block, JS in one `<script>` block at the bottom.
> Videos are in `vid/`, images in `img/`, client logos in `img/logo/`, pipeline
> stage media in `img/pipe/`. There is no build step. After editing, run
> `git add -A && git commit -m "..." && git push`. It deploys itself.

That is genuinely all an agent needs. The whole point of the single-file build is
that it has no hidden state.

---

## Where things are in `index.html`

| Section | Find it by searching for |
|---|---|
| Colour and type tokens | `:root{` |
| Nav island | `class="island"` |
| Hero, job title, proof figures | `<header>` |
| Case studies | `<!-- ------ APEX -->`, `BLUEMAGIC`, `ECHO`, `TECHY TANTRUMS` |
| Statics grid | `<!-- ------ STATICS -->` |
| Pipeline stage rail | `class="prail"` |
| Hiring-manager block | `class="hire"` |
| Background motion graphics | `id="mg"` (canvas) and the `LINES` array in the script |

### Common edits

**Change a colour** — edit the tokens in `:root{}` only. Everything reads from them.
Current palette: `#ECF0F1` ground, `#2C3E50` ink, `#34495E` secondary,
`#E67E22` accent, `#A84E06` accent for small text and buttons.

> Check contrast before changing the accent. Small text needs 4.5:1 against the
> ground, large text and icons need 3:1. `#E67E22` only clears 2.48:1, which is
> why it is never used for type — `#A84E06` (4.87:1) is.

**Add a video** — compress it first, or the repo bloats:

```bash
python compress.py "path/to/source.mp4" vid/new_name.mp4
```

(see `compress.py` below — roughly 3 MB per 40-second vertical ad at 540x960)

Then copy an existing `<div class="card rv">` block and change the `src`,
`poster`, `tag`, `hook` and `why`.

**Add a client logo** — drop it in `img/logo/`, then reference it in that case's
`<h2 class="rv brand">`. White logos will be invisible on the light ground; invert
them first.

---

## Rules worth not breaking

1. **Every colour comes from a token.** No hard-coded hex outside `:root{}`.
2. **Reveals are opt-in.** `.rv` elements are visible by default and only hide once
   JS confirms it can animate. If you invert that, a JS failure renders a blank page.
3. **The canvas needs explicit `width`/`height`.** It is a replaced element, so
   `inset:0` alone leaves it at its intrinsic 300x150.
4. **Draw the first canvas frame synchronously.** `requestAnimationFrame` never
   fires in a background or prerendered tab.
5. **Keep videos small.** GitHub Pages has a soft 1 GB repo limit and a 100 MB
   per-file cap. Current total is around 37 MB.
6. **Do not delete `.nojekyll`.** Without it, Pages runs Jekyll and can skip
   asset folders.

---

## `compress.py`

Requires `pip install av pillow`. No ffmpeg binary needed — PyAV bundles it.

```python
import av, sys
from fractions import Fraction
from av.audio.resampler import AudioResampler

src, dst, TARGET_W, CRF = sys.argv[1], sys.argv[2], 540, "30"

with av.open(src) as ic:
    ivs = ic.streams.video[0]; ivs.thread_type = "AUTO"
    sw, sh = ivs.codec_context.width, ivs.codec_context.height
    fps = ivs.average_rate or Fraction(30, 1)
    w = TARGET_W - TARGET_W % 2
    h = int(sh * (TARGET_W / sw)); h -= h % 2

    oc = av.open(dst, "w", options={"movflags": "+faststart"})
    ovs = oc.add_stream("libx264", rate=fps)
    ovs.width, ovs.height, ovs.pix_fmt = w, h, "yuv420p"
    ovs.options = {"crf": CRF, "preset": "veryfast", "profile": "main", "g": "60"}
    tb = Fraction(1, 90000); ovs.time_base = tb
    step = int(round(90000 / float(fps)))

    oas = oc.add_stream("aac", rate=44100); oas.bit_rate = 64000
    res = AudioResampler(format="fltp", layout="stereo", rate=44100)

    n = 0
    for frame in ic.decode(video=0):
        nf = frame.reformat(width=w, height=h, format="yuv420p")
        nf.pts = n * step; nf.time_base = tb; n += 1
        for pkt in ovs.encode(nf): oc.mux(pkt)
    for pkt in ovs.encode(): oc.mux(pkt)

    apts = 0
    with av.open(src) as ic2:
        for af in ic2.decode(audio=0):
            for rf in res.resample(af):
                rf.pts = apts; rf.time_base = Fraction(1, 44100)
                apts += rf.samples
                for pkt in oas.encode(rf): oc.mux(pkt)
    for pkt in oas.encode(): oc.mux(pkt)
    oc.close()
print("done:", dst)
```

**Why timestamps are set by hand:** several source files are variable frame rate.
Leaving `pts = None` produces non-monotonic timestamps and the mux fails with
`ArgumentError ... returned 22`. Assigning `pts` against a fixed 1/90000 time base
fixes it.

---

## Deploy checks

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://ayushcreativeai.github.io/
gh api repos/ayushcreativeai/ayushcreativeai.github.io/pages | python -c "import json,sys; print(json.load(sys.stdin)['status'])"
```

`built` means live. `building` means wait.
