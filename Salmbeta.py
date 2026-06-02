import os
import sys
import subprocess
import glob
import music21

def main():
    # ==========================================
    # 【Step 0】 楽譜(PDF)の選択
    # ==========================================
    # 自分で作成するフォルダの名前を指定
    score_dir = "Score" 
    
    # フォルダが存在するかチェック
    if not os.path.exists(score_dir):
        print(f"エラー: '{score_dir}' フォルダが見つかりません。")
        print(f"Pythonファイルと同じ場所に '{score_dir}' という名前のフォルダを作り、中にPDFを入れてください。")
        sys.exit()

    # フォルダ内のPDFを取得
    pdf_files = glob.glob(os.path.join(score_dir, "*.pdf"))
    
    if not pdf_files:
        print(f"エラー: '{score_dir}' フォルダの中にPDFファイル(楽譜)がありません。")
        sys.exit()

    # 楽譜リストを出力
    print("\n処理する楽譜(PDF)を番号で選択してください:")
    for i, file_path in enumerate(pdf_files):
        print(f"  [{i + 1}] {os.path.basename(file_path)}")

    # 数字で選択させるループ
    while True:
        choice = input(f"\n番号を入力 (1-{len(pdf_files)}): ").strip()
        
        # 入力が数字かどうか、かつ範囲内かチェック
        if choice.isdigit():
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(pdf_files):
                pdf_path = pdf_files[choice_idx]
                break
        
        print("リストにある正しい番号(数字)を入力してください。") 
    
    # Audiveris.exe のフルパス
    audiveris_exe = r"\Audiveris\Audiveris.exe"

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    dir_name = f"test_{base_name}_Audiveris"
    
    os.makedirs(dir_name, exist_ok=True)
    print(f"保存用ディレクトリ '{dir_name}' を作成/確認しました。")

    # 出力予定のファイルパス
    midi_path = os.path.join(dir_name, f"{base_name}_full_song.mid")

    # ==========================================
    # 【Step 1】 Audiveris 解析 (対話型スキップ)
    # ==========================================
    mxl_files = glob.glob(os.path.join(dir_name, "**", "*.mxl"), recursive=True)
    skip_step1 = False
    
    if mxl_files:
        # ファイルがある場合はユーザーに聞く
        ans = input(f"\n【Step 1】 解析済みのXMLがあります。Audiverisの処理をスキップしますか？ [Y/n]: ").strip().lower()
        if ans != 'n':
            skip_step1 = True
            mxl_path = mxl_files[0]
            print("⏭️ Step 1 をスキップしました。")
    
    if not skip_step1:
        os.environ["_JAVA_OPTIONS"] = "-Xmx16G"
        print("\nAudiverisに最大16GBのメモリ(RAM)を強制割り当てしました！")
        print(f"【Step 1】Audiverisによる全ページ一括解析を開始します (元PDFを直接読み込み)")
        
        cmd = [
            audiveris_exe, "-batch", "-export",
            "-output", os.path.abspath(dir_name),
            os.path.abspath(pdf_path) 
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            mxl_files = glob.glob(os.path.join(dir_name, "**", "*.mxl"), recursive=True)
            if not mxl_files:
                print(f"エラー: .mxl ファイルが生成されませんでした。")
                return
            mxl_path = mxl_files[0]
            print(f"見つかったXMLファイル: {mxl_path}")
        except subprocess.CalledProcessError as e:
            print(f"\nエラー: Audiverisの解析に失敗しました。")
            return

    # ==========================================
    # 【Step 2】 Music21 論理補正 (対話型スキップ)
    # ==========================================
    skip_step2 = False
    if os.path.exists(midi_path):
        # ファイルがある場合はユーザーに聞く
        ans = input(f"\n【Step 2】 補正済みのMIDIがあります。Music21の処理をスキップしますか？ [Y/n]: ").strip().lower()
        if ans != 'n':
            skip_step2 = True
            print("⏭Step 2 をスキップしました。")

    if not skip_step2:
        print(f"\n【Step 2】Music21によるデータ補正を開始します...")
        try:
            score_data = music21.converter.parse(mxl_path)
        except Exception as e:
            print(f"エラー: XMLデータ破損 ({e})。")
            return

        # --------------------------------------------------------
        # ① 強弱の無効化・音量均一化の選択
        # --------------------------------------------------------
        ans_dyn = input("1/3: 楽譜内の強弱記号(p, fなど)を無効化し、音量を均一(ベロシティ85)にしますか？ [Y/n]: ").strip().lower()
        if ans_dyn != 'n':
            print("強弱を無効化し、音量を均一に設定しています...")
            for dyn in score_data.recurse().getElementsByClass('Dynamic'):
                try: dyn.activeSite.remove(dyn)
                except: pass
            for wedge in score_data.recurse().getElementsByClass('DynamicWedge'):
                try: wedge.activeSite.remove(wedge)
                except: pass
            for n in score_data.recurse().notes:
                n.volume.velocity = 85  

        # --------------------------------------------------------
        # ② テンポ (BPM) 固定の選択
        # --------------------------------------------------------
        ans_bpm = input("2/3: テンポ(BPM)を強制指定しますか？ (数値を入力してください。指定しない場合は Enter か n): ").strip().lower()
        if ans_bpm and ans_bpm != 'n':
            try:
                bpm_val = float(ans_bpm)
                print(f"テンポを {bpm_val} に設定しています...")
                score_data.insert(0, music21.tempo.MetronomeMark(number=bpm_val))
            except ValueError:
                print("数値として認識できなかったため、BPMの強制指定をスキップします。")

        # --------------------------------------------------------
        # ③ リズム（小節の長さ）自動補正の選択
        # --------------------------------------------------------
        ans_rhy = input("3/3: OMRの認識漏れによる「小節の長さ不足」を自動補正しますか？ [Y/n]: ").strip().lower()
        if ans_rhy != 'n':
            print("リズムの論理補正を実行しています...")
            for part in score_data.parts:
                for m in part.getElementsByClass(music21.stream.Measure):
                    notes = m.flatten().notes
                    total_duration = sum(n.duration.quarterLength for n in notes)
                    # 4.0 (4/4拍子) に満たない小節の最後の音符を伸ばして補正
                    if 0 < total_duration < 4.0:
                        diff = 4.0 - total_duration
                        if len(notes) > 0:
                            notes[-1].duration.quarterLength += diff

        # 変更を保存
        score_data.write('midi', fp=midi_path)
        print(f"全ページの抽出とデータ補正完了！ MIDIを保存しました: {midi_path}")

    # ==========================================
    # 【Step 3】 sfizzによるWAVレンダリング (毎回実行)
    # ==========================================
    output_wav = os.path.abspath(os.path.join(dir_name, f"{base_name}.wav"))
    
    print("\n【Step 3】sfizzエンジンで最高音質SFZをWAVへ一括レンダリング中...")
    
    sfz_dir = r"D:\Program\Python\Piano\AccurateSalamanderGrandPianoV6.2beta2_48khz24bit\sfz_daw"
    sfz_filename = "Accurate-SalamanderGrandPiano_flat.Recommended.sfz"
    
    midi_path_abs = os.path.abspath(midi_path)
    sfizz_exe_abs = os.path.abspath(r"D:\Program\Python\Piano\sfizz-1.2.3-win64\bin\Release\sfizz_render.exe")
    
    cmd_sfizz = [
        sfizz_exe_abs,
        "--sfz", sfz_filename,
        "--midi", midi_path_abs,
        "--wav", output_wav,
        "--samplerate", "44100" 
    ]
    
    try:
        subprocess.run(cmd_sfizz, check=True, cwd=sfz_dir)
        print(f"フルコーラス '{output_wav}' が出力されました")
    except FileNotFoundError:
        print("エラー: sfizz_render.exe が見つかりません。")
    except subprocess.CalledProcessError as e:
        print(f"エラー: sfizzのレンダリング中に問題が発生しました。\n{e}")

if __name__ == "__main__":
    main()