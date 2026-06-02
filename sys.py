import numpy as np
from scipy.io import wavfile

def synthesize_piano_string(freq, duration_sec, sample_rate=44100):
    print(f"周波数 {freq}Hz の弦の物理挙動を計算中...")

    # 弦の長さに相当する「遅延バッファ（配列）」のサイズを計算
    # 波が端から端まで往復するのにかかるサンプル数
    delay_length = int(sample_rate / freq)
    
    # 弦の初期状態（ハンマーが叩いた瞬間の衝撃波）を生成
    # ここでは、少し丸みを帯びた衝撃（ローパスされたノイズ）でフェルトのハンマーを表現
    noise = np.random.uniform(-1, 1, delay_length)
    hammer_strike = np.convolve(noise, np.ones(5)/5, mode='same')
    
    # ウェーブガイド（遅延線）の初期化
    waveguide = hammer_strike.copy()
    
    # 出力する音声データを格納する巨大な配列を用意
    total_samples = int(sample_rate * duration_sec)
    output_audio = np.zeros(total_samples)
    
    # 音の減衰と、高い音ほど早く消える特性（ブリッジでのエネルギー損失）を表現するフィルタ係数
    decay_factor = 0.996
    
    # --- ここからが物理モデリングのコア（毎秒44,100回のループ計算） ---
    # 波をバッファの中でぐるぐる回しながら、少しずつ削っていく
    for i in range(total_samples):
        # バッファの先頭の音を出力として取り出す
        current_sample = waveguide[0]
        output_audio[i] = current_sample
        
        # 波が弦の端（ブリッジ）で反射する際の「エネルギー損失」と「高音の吸収」を計算
        # （直前のサンプルとの平均を取るローパスフィルタで表現）
        reflected_wave = (waveguide[0] + waveguide[1]) * 0.5 * decay_factor
        
        # バッファの中身を1つずつ前にずらす（波が移動している表現）
        waveguide[:-1] = waveguide[1:]
        
        # 反射した波をバッファの最後尾に戻す（波が折り返した表現）
        waveguide[-1] = reflected_wave

    print("計算完了！")
    return output_audio

def main():
    # A4（ラ = 440Hz）の音を3秒間生成
    audio_data = synthesize_piano_string(freq=440.0, duration_sec=3.0)
    
    # 音量が大きすぎると割れるので正規化（-32767 〜 32767の範囲に収める）
    audio_data = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)
    
    # 生成した波形をWAVファイルとして保存
    filename = "synthesized_piano_string.wav"
    wavfile.write(filename, 44100, audio_data)
    print(f"✨ 物理モデリングで生成した音を '{filename}' として保存しました！")
    print("フォルダを開いて再生してみてください。")

if __name__ == "__main__":
    main()