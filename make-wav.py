import subprocess
import os

def main():
    print("FluidSynthで高音質WAVへ一括レンダリング中...")
    
    sf2_path = "UprightPianoKW-20220221.sf2"
    midi_path = "full_song_temp.mid"
    output_wav = "full_song_high_quality.wav"
    
    # exeを直接指定（今のフォルダに置いた前提）
    fluidsynth_exe = r".\fluidsynth.exe"
    
    if not os.path.exists(fluidsynth_exe):
        print(f"【エラー】{fluidsynth_exe} が見つかりません！同じフォルダにコピーしてください。")
        return
        
    cmd = [
        fluidsynth_exe,
        "-ni",                              
        "-o", "synth.reverb.active=1",      
        "-o", "synth.reverb.room-size=0.8", 
        "-o", "synth.reverb.damp=0.4",      
        "-o", "synth.reverb.width=100.0",   
        "-o", "synth.reverb.level=0.7",     
        "-F", output_wav,                   
        "-r", "44100",                      
        sf2_path,                           
        midi_path                           
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"✨✨ 完了！ '{output_wav}' にフルコーラスの高音質演奏が書き出されました！ ✨✨")
    except subprocess.CalledProcessError:
        print("エラー: 変換中に問題が発生しました。")

if __name__ == "__main__":
    main()