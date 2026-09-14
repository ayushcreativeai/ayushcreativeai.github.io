"""Compress a video for the portfolio.

    python compress.py "D:/path/to/source.mp4" vid/new_name.mp4 [max_seconds]

Roughly 3 MB per 40 second vertical ad at 540x960. Requires: pip install av pillow
No ffmpeg binary needed, PyAV bundles its own.
"""
import sys
from fractions import Fraction

import av
from av.audio.resampler import AudioResampler

TARGET_W = 540
CRF = "30"


def compress(src, dst, limit=None):
    with av.open(src) as ic:
        ivs = ic.streams.video[0]
        ivs.thread_type = "AUTO"
        sw, sh = ivs.codec_context.width, ivs.codec_context.height
        fps = ivs.average_rate or Fraction(30, 1)
        has_audio = len(ic.streams.audio) > 0

        w = TARGET_W - TARGET_W % 2
        h = int(sh * (TARGET_W / sw))
        h -= h % 2

        oc = av.open(dst, "w", options={"movflags": "+faststart"})
        ovs = oc.add_stream("libx264", rate=fps)
        ovs.width, ovs.height, ovs.pix_fmt = w, h, "yuv420p"
        ovs.options = {"crf": CRF, "preset": "veryfast", "profile": "main", "g": "60"}

        # Fixed time base with hand-assigned pts. Several sources are variable
        # frame rate, and pts=None there yields non-monotonic timestamps, which
        # makes the mux fail with ArgumentError ... returned 22.
        tb = Fraction(1, 90000)
        ovs.time_base = tb
        step = int(round(90000 / float(fps)))

        oas = res = None
        if has_audio:
            oas = oc.add_stream("aac", rate=44100)
            oas.bit_rate = 64000
            res = AudioResampler(format="fltp", layout="stereo", rate=44100)

        n = 0
        for frame in ic.decode(video=0):
            if limit and frame.time and frame.time > limit:
                break
            nf = frame.reformat(width=w, height=h, format="yuv420p")
            nf.pts = n * step
            nf.time_base = tb
            n += 1
            for pkt in ovs.encode(nf):
                oc.mux(pkt)
        for pkt in ovs.encode():
            oc.mux(pkt)

        if has_audio:
            apts = 0
            with av.open(src) as ic2:
                for af in ic2.decode(audio=0):
                    if limit and af.time and af.time > limit:
                        break
                    for rf in res.resample(af):
                        rf.pts = apts
                        rf.time_base = Fraction(1, 44100)
                        apts += rf.samples
                        for pkt in oas.encode(rf):
                            oc.mux(pkt)
            for pkt in oas.encode():
                oc.mux(pkt)
        oc.close()

    import os
    print(f"{dst}  {w}x{h}  {os.path.getsize(dst)/1048576:.2f} MB")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    lim = float(sys.argv[3]) if len(sys.argv) > 3 else None
    compress(sys.argv[1], sys.argv[2], lim)
