import numpy as np
from scipy.io import wavfile

def synthesize_piano_unison(base_freq, duration_sec, detune_amount=0.8, sample_rate=44100):
    print(f"基準周波数 {base_freq}Hz の『3本弦』の物理挙動を計算中...")
    
    total_samples = int(sample_rate * duration_sec)
    
    # 3本の弦の周波数をわずかにズラす（調律のシミュレート）
    # 例: 440Hz, 440.8Hz, 439.2Hz
    frequencies = [
        base_freq, 
        base_freq + detune_amount, 
        base_freq - detune_amount
    ]
    
    # 3本の弦の出力結果を足し合わせるための配列
    mixed_audio = np.zeros(total_samples)
    
    # 3本の弦それぞれについてウェーブガイドを計算
    for string_idx, freq in enumerate(frequencies):
        delay_length = int(sample_rate / freq)
        
        # ハンマーの衝撃（今回は少し硬めのフェルトをシミュレート）
        noise = np.random.uniform(-1, 1, delay_length)
        hammer_strike = np.convolve(noise, np.ones(3)/3, mode='same')
        
        waveguide = hammer_strike.copy()
        string_audio = np.zeros(total_samples)
        decay_factor = 0.997 # 弦の減衰率
        
        for i in range(total_samples):
            current_sample = waveguide[0]
            string_audio[i] = current_sample
            
            # ブリッジでの反射と高音の吸収（ローパス）
            reflected_wave = (waveguide[0] + waveguide[1]) * 0.5 * decay_factor
            
            waveguide[:-1] = waveguide[1:]
            waveguide[-1] = reflected_wave
            
        # 計算した1本分の弦の音をミックス
        mixed_audio += string_audio
        print(f"  -> 弦 {string_idx + 1} ({freq}Hz) の計算完了")

    print("3本弦の合成完了！")
    return mixed_audio

def main():
    # A4（ラ = 440Hz）の音を4秒間生成
    audio_data = synthesize_piano_unison(base_freq=440.0, duration_sec=4.0)
    
    # 音割れを防ぐための正規化処理
    audio_data = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)
    
    filename = "piano_3strings_unison.wav"
    wavfile.write(filename, 44100, audio_data)
    print(f"✨ 物理モデリング音源 '{filename}' を保存しました！")

if __name__ == "__main__":
    main()