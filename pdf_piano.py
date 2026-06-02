import os
import subprocess
import glob
import music21

def main():
    pdf_path = "WatashiwaWatashinoKotogaSuki.pdf" 
    bpm = 193
    
    # ⚠️ Audiveris.exe のフルパス
    audiveris_exe = r"C:\Program Files\Audiveris\Audiveris.exe"

    base_name = os.path.splitext(pdf_path)[0]
    dir_name = f"{base_name}_Audiveris"
    
    os.makedirs(dir_name, exist_ok=True)
    print(f"📁 保存用ディレクトリ '{dir_name}' を作成/確認しました。")

    # ハードウェアパワーの解放：Javaのメモリ上限を16GBに引き上げる
    os.environ["_JAVA_OPTIONS"] = "-Xmx16G"
    print("🔋 Audiverisに最大16GBのメモリ(RAM)を強制割り当てしました！")

    print(f"\n【Step 1】Audiverisによる全ページ一括解析を開始します (元PDFを直接読み込み)")
    
    cmd = [
        audiveris_exe,
        "-batch",
        "-export",
        "-output", os.path.abspath(dir_name),
        os.path.abspath(pdf_path) 
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

    # --- 🚀 追加：ダイナミクス（強弱）の完全無効化（エラー回避版） ---
    print("🔊 楽譜内の強弱記号を削除し、音量を均一に設定しています...")
    
    # 1. p, f, mf などの強弱記号をすべて探し出して削除（文字列指定）
    for dyn in score_data.recurse().getElementsByClass('Dynamic'):
        try:
            dyn.activeSite.remove(dyn)
        except:
            pass
        
    # 2. 松葉杖記号（クレッシェンド ＜ やデクレッシェンド ＞）をすべて削除（文字列指定）
    for wedge in score_data.recurse().getElementsByClass('DynamicWedge'):
        try:
            wedge.activeSite.remove(wedge)
        except:
            pass

    # 3. 全ての音符の音量（MIDIベロシティ）を一定値に強制固定
    for n in score_data.recurse().notes:
        n.volume.velocity = 85  # ★ここを変えると全体の音量が変わります（0〜127）
    # ----------------------------------------------------

    score_data.insert(0, music21.tempo.MetronomeMark(number=bpm))

    for part in score_data.parts:
        for m in part.getElementsByClass(music21.stream.Measure):
            notes = m.flatten().notes
            total_duration = sum(n.duration.quarterLength for n in notes)
            
            if 0 < total_duration < 4.0:
                diff = 4.0 - total_duration
                if len(notes) > 0:
                    notes[-1].duration.quarterLength += diff

    midi_path = os.path.join(dir_name, f"{base_name}_full_song.mid")
    score_data.write('midi', fp=midi_path)
    print(f"✅ 全ページの抽出と補正完了！ MIDIを保存しました: {midi_path}")

    print("\n【Step 3】FluidSynthで高音質WAVへ一括レンダリング中...")
    sf2_path = "UprightPianoKW-20220221.sf2"
    output_wav = os.path.join(dir_name, f"{base_name}_full_song.wav")
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