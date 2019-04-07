import parselmouth
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os

if __name__ == '__main__':
    sns.set()
    snd = parselmouth.Sound(sys.argv[1])
    plt.figure()
    plt.plot(snd.xs(), snd.values.T)
    plt.axis('off')
    fn, ext = os.path.splitext(sys.argv[1])
    plt.savefig(f"{fn}_waveform.png")