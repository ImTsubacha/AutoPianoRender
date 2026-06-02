import os
import subprocess
import glob
import music21

def main():
    pdf_path = "Ray.pdf" 
    bpm = 132
    
    # ⚠️ Audiveris.exe のフルパス
    audiveris_exe = r"C:\Program Files\Audiveris\Audiveris.exe"

    dir_name = "test"
    os.makedirs(dir_name, exist_ok=True)
    print(f"📁 保存用ディレクトリ '{dir_name}' を作成/確認しました。")

    # 画像の白塗り・再結合処理を全廃止！直接元のPDFを解析させます。
    print(f"\n【Step 1】Audiverisによる全ページ一括解析を開始します (元PDFを直接読み込み)")
    print("⏳ ※数分かかる場合があります。お茶でも飲んでお待ちください...")
    
    cmd = [
        audiveris_exe,
        "-batch",
        "-export",
        "-output", os.path.abspath(dir_name),
        os.path.abspath(pdf_path) # 元のPDFをダイレクトアタック！
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    except subprocess.CalledProcessError as e:
        print(f"\n❌ エラー: Audiverisの解析に失敗しました。")
        print("--- 🔍 内部クラッシュログ (stdout の最後2000文字) ---")
        print(e.stdout[-2000:] if e.stdout else "stdoutなし")
        print("--- ⚠️ エラーログ (stderr) ---")
        print(e.stderr if e.stderr else "stderrなし")
        return

    # dir_nameの中に作られたフォルダから .mxl を探す
    mxl_files = glob.glob(os.path.join(dir_name, "**", "*.mxl"), recursive=True)

    if not mxl_files:
        print(f"❌ エラー: .mxl ファイルが生成されませんでした。")
        return

    mxl_path = mxl_files[0]
    print(f"✅ 見つかったXMLファイル: {mxl_path}")

    print(f"\n【Step 2】Music21によるリズムの論理補正を開始します...")
    try:
        score_data = music21.converter.parse(mxl_path)
    except Exception as e:
        print(f"エラー: XMLデータ破損 ({e})。")
        return

    # --- 🚀 リズムの補正（小節パズル） ---
    score_data.insert(0, music21.tempo.MetronomeMark(number=bpm))

    for part in score_data.parts:
        for m in part.getElementsByClass(music21.stream.Measure):
            notes = m.flatten().notes
            total_duration = sum(n.duration.quarterLength for n in notes)
            
            # 4拍に足りなければ、最後の音符を延長
            if 0 < total_duration < 4.0:
                diff = 4.0 - total_duration
                if len(notes) > 0:
                    notes[-1].duration.quarterLength += diff

    midi_path = os.path.join(dir_name, f"{dir_name}_full_song.mid")
    score_data.write('midi', fp=midi_path)
    print(f"✅ 全ページの抽出と補正完了！ MIDIを保存しました: {midi_path}")

    print("\n【Step 3】FluidSynthで高音質WAVへ一括レンダリング中...")
    sf2_path = "UprightPianoKW-20220221.sf2"
    output_wav = os.path.join(dir_name, f"{dir_name}_full_song.wav")
    fluidsynth_exe = r".\fluidsynth.exe"
    
    cmd_fluid = [
        fluidsynth_exe, "-ni",                              
        "-o", "synth.reverb.active=1",      
        "-F", output_wav, "-r", "44100",                      
        sf2_path, midi_path                           
    ]
    
    try:
        subprocess.run(cmd_fluid, check=True)
        print(f"✨✨ フルコーラス完成！ '{output_wav}' が出力されました！ ✨✨")
    except FileNotFoundError:
        print("エラー: fluidsynthが見つかりません。")

if __name__ == "__main__":
    main()