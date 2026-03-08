let nextPlayTime = 0;

export function createAudioContext(): AudioContext {
  nextPlayTime = 0;
  return new AudioContext({ sampleRate: 24000 });
}

export function playAudioChunk(ctx: AudioContext, base64Audio: string): void {
  try {
    const binaryString = atob(base64Audio);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    const int16Array = new Int16Array(bytes.buffer);
    if (int16Array.length === 0) return;

    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    const audioBuffer = ctx.createBuffer(1, float32Array.length, 24000);
    audioBuffer.getChannelData(0).set(float32Array);

    const source = ctx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(ctx.destination);

    // Schedule chunks sequentially so they don't overlap
    const now = ctx.currentTime;
    if (nextPlayTime < now) {
      nextPlayTime = now;
    }
    source.start(nextPlayTime);
    nextPlayTime += audioBuffer.duration;
  } catch (err) {
    console.warn('Audio playback error:', err);
  }
}

export function resetPlaybackSchedule(): void {
  nextPlayTime = 0;
}

export function createAudioWorkletProcessor(): string {
  const processorCode = `
    class PCM16CaptureProcessor extends AudioWorkletProcessor {
      constructor() {
        super();
        this.buffer = [];
      }

      process(inputs) {
        const input = inputs[0];
        if (input && input[0]) {
          const channelData = input[0];
          for (let i = 0; i < channelData.length; i++) {
            this.buffer.push(channelData[i]);
          }

          if (this.buffer.length >= 4096) {
            const samples = this.buffer.splice(0, 4096);
            const int16 = new Int16Array(samples.length);
            for (let i = 0; i < samples.length; i++) {
              const s = Math.max(-1, Math.min(1, samples[i]));
              int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }

            const bytes = new Uint8Array(int16.buffer);
            let binary = '';
            for (let i = 0; i < bytes.length; i++) {
              binary += String.fromCharCode(bytes[i]);
            }

            this.port.postMessage({ pcm16: binary });
          }
        }
        return true;
      }
    }

    registerProcessor('pcm16-capture', PCM16CaptureProcessor);
  `;

  const blob = new Blob([processorCode], { type: 'application/javascript' });
  return URL.createObjectURL(blob);
}
