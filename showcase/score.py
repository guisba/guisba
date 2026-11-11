"""Original synthesized soundtrack for the guisba public portfolio film.
Deterministic, generated locally; no samples or licensed recordings.
"""
from pathlib import Path
import numpy as np
import wave

RATE = 44100
DURATION = 39.5

def compose(out: str | Path) -> None:
    n = round(RATE * DURATION)
    left = np.zeros(n, dtype=np.float32)
    right = np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(2086)

    def add(start: float, duration: float, signal: np.ndarray, pan: float = 0.0, vol: float = 1.0):
        first = int(start * RATE)
        if first < 0 or first >= n:
            return
        m = min(int(duration * RATE), len(signal), n - first)
        if m < 1:
            return
        left[first:first + m] += vol * np.sqrt((1 - pan) / 2) * signal[:m]
        right[first:first + m] += vol * np.sqrt((1 + pan) / 2) * signal[:m]

    def tone(hz: float, duration: float, decay: float = 1.0, attack: float = .018, overtones=True):
        p = np.arange(max(1, int(RATE * duration))) / RATE
        waveform = (np.sin(2 * np.pi * hz * p) + (.15 * np.sin(2 * np.pi * 2.01 * hz * p) if overtones else 0))
        env = np.minimum(1, p / max(.001, attack)) * np.minimum(1, (duration - p) / .07) * np.exp(-decay * p)
        return (waveform * np.maximum(0, env)).astype(np.float32)

    harmony = [(0, 73.42, 10.5), (10.5, 65.41, 7.5), (18, 82.41, 7),
               (25, 55.00, 5), (30, 73.42, 4), (34, 73.42, 5.5)]
    for start,root,duration in harmony:
        for i,mult in enumerate([1,1.5,2.0]):
            p = np.arange(round(RATE * duration)) / RATE
            env = np.minimum(1,p/1.3)*np.minimum(1,(duration-p)/1.2)
            vib = .002*np.sin(2*np.pi*(.19+.05*i)*p)
            sig = (np.sin(2*np.pi*root*mult*(p+vib))*.27 +
                   .19*np.sin(2*np.pi*(root*mult*1.003)*p)) * np.maximum(0,env)
            add(start,duration,sig.astype(np.float32),[-.43,.25,.55][i],.18)

    bpm = 103
    beat = 60/bpm
    for i in range(int(DURATION/beat)+1):
        when = i*beat
        if when > DURATION-.4: break
        dur=.38;p=np.arange(round(RATE*dur))/RATE
        freq=52+48*np.exp(-30*p)
        phase=2*np.pi*np.cumsum(freq)/RATE
        kick=np.sin(phase)*np.exp(-16*p)
        add(when,dur,kick.astype(np.float32),0,.47 if i%4==0 else .26)
        if i % 2 == 0:
            f=[73.42,98.0,110.,87.3][(i//2)%4]
            add(when+.045,.46,tone(f,.46,5,overtones=False),(-.1,.1)[i%2],.24)
        for j in range(2):
            htime=when+j*beat/2
            sz=.07; k=np.arange(round(RATE*sz))/RATE
            noise=rng.standard_normal(len(k)).astype(np.float32)
            hi=np.diff(np.concatenate(([0], noise))).astype(np.float32)
            hi=hi/8*np.exp(-65*k)
            add(htime,sz,hi,(-.6,.6)[j],.18)
    notes=[146.83,174.61,220.,196.,164.81,130.81,146.83,220.]
    for i in range(60):
        when=.35+i*beat*.95
        if when>=34: break
        if i%8 in (3,7): continue
        hz=notes[i%len(notes)]
        add(when,.63,tone(hz,.63,5,overtones=True),.42 if i%2 else -.4,.085)
    for j,when in enumerate([0.,5.,10.5,18.,25.,30.,34.]):
        dur=.88;p=np.arange(round(RATE*dur))/RATE
        x=rng.standard_normal(len(p)).astype(np.float32)
        smoothed=np.convolve(x,np.ones(24,dtype=np.float32)/24,mode='same')
        rise=(np.sin(np.pi*np.minimum(1,p/dur)))**2
        add(max(0,when),dur,(smoothed*rise*.38).astype(np.float32),-.4 if j%2 else .4,.45)
        add(when,.7,tone(42,.7,8,attack=.003,overtones=False),0,.33)
    k=np.arange(n)/RATE
    fade=np.minimum(1,k/.6)*np.minimum(1,(DURATION-k)/1.05)
    stereo=np.stack((left,right),axis=-1)*np.maximum(fade,0)[:,None]
    stereo=np.tanh(stereo*1.22)
    peak=float(np.max(np.abs(stereo)))
    if peak: stereo*=.88/peak
    pcm=(np.clip(stereo,-1,1)*32767).astype('<i2')
    with wave.open(str(out),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(pcm.tobytes())

if __name__=='__main__':
    compose(Path(__file__).with_name('soundtrack.wav'))
    print('Created soundtrack.wav (original synthesized score)')
