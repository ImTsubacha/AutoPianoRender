import numpy as np
from scipy.io import wavfile
import mido

def synthesize_piano_string(freq, duration_sec, sample_rate=44100):
    """弦の物理モデリング（元のコードと同じ）"""
    if freq <= 0 or duration_sec <= 0:
        return np.zeros(0)
        
    delay_length = int(sample_rate / freq)
    if delay_length <= 0:
        delay_length = 1
        
    noise = np.random.uniform(-1, 1, delay_length)
    hammer_strike = np.convolve(noise, np.ones(5)/5, mode='same')
    
    waveguide = hammer_strike.copy()
    total_samples = int(sample_rate * duration_sec)
    output_audio = np.zeros(total_samples)
    
    decay_factor = 0.996
    
    for i in range(total_samples):
        output_audio[i] = waveguide[0]
        reflected_wave = (waveguide[0] + waveguide[1]) * 0.5 * decay_factor
        waveguide[:-1] = waveguide[1:]
        waveguide[-1] = reflected_wave

    return output_audio

def midi_note_to_freq(midi_note):
    """MIDIノート番号（0〜127）を周波数（Hz）に変換"""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))

def load_midi_score(midi_path):
    """MIDIファイルを読み込んで (ノート番号, 開始時間, 長さ) のリストを返す"""
    mid = mido.MidiFile(midi_path)
    score = []
    active_notes = {}
    current_time = 0.0

    print(f"'{midi_path}' を読み込んでいます...")
    
    # MIDIメッセージを一つずつ処理して時間と音の長さを計算
    for msg in mid:
        current_time += msg.time
        
        # 音の開始
        if msg.type == 'note_on' and msg.velocity > 0:
            active_notes[msg.note] = current_time
            
        # 音の終了
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in active_notes:
                start_time = active_notes.pop(msg.note)
                duration = current_time - start_time
                # 極端に短い音は弾き飛ばす
                if duration > 0.05:
                    score.append((msg.note, start_time, duration))
                    
    return score

def main():
    # 読み込むMIDIファイル名を指定
    midi_filename = "reply_cover.mid" # ★ここに用意したMIDIファイル名を入れる
    
    try:
        score = load_midi_score(midi_filename)
    except FileNotFoundError:
        print(f"エラー: '{midi_filename}' が見つかりません。同じフォルダにMIDIファイルを置いてください。")
        return

    sample_rate = 44100
    
    # 曲の長さを計算してキャンバスを用意
    end_times = [start_time + duration for _, start_time, duration in score]
    total_duration = max(end_times) + 2.0 # 余韻のために2秒追加
    total_samples = int(total_duration * sample_rate)
    master_audio = np.zeros(total_samples)

    print(f"総ノート数: {len(score)}音。音声の生成を開始します（かなり時間がかかります）...")

    # MIDIデータから音を生成して重ねる
    for i, (midi_note, start_time, duration) in enumerate(score):
        freq = midi_note_to_freq(midi_note)
        wave = synthesize_piano_string(freq, duration, sample_rate)
        
        start_idx = int(start_time * sample_rate)
        end_idx = start_idx + len(wave)
        
        # 音を重ね合わせる
        master_audio[start_idx:end_idx] += wave
        
        # 進捗を表示（100音ごと）
        if (i + 1) % 100 == 0:
            print(f"進捗: {i + 1} / {len(score)} 音 完了...")

    # 正規化と保存
    master_audio = np.int16(master_audio / np.max(np.abs(master_audio)) * 32767)
    output_filename = "synthesized_reply.wav"
    wavfile.write(output_filename, sample_rate, master_audio)
    
    print(f"✨ 完了！ '{output_filename}' として保存しました。")

if __name__ == "__main__":
    main()