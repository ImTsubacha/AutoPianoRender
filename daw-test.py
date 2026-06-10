import os
import sys
import subprocess
import glob
import music21
import fitz
import shutil

# Step 4用のDAWライブラリを読み込み（インストールされていない場合のエラー回避付き）
try:
    from pedalboard import Pedalboard, Reverb, Compressor, HighpassFilter, Gain
    from pedalboard.io import AudioFile
    HAS_PEDALBOARD = True
except ImportError:
    HAS_PEDALBOARD = False

def main():
    # ==========================================
    # 【Step 0】 楽譜(PDF)の選択
    # ==========================================
    score_dir = "Score" 
    
    if not os.path.exists(score_dir):
        print(f"エラー: '{score_dir}' フォルダが見つかりません。")
        print(f"Pythonファイルと同じ場所に '{score_dir}' という名前のフォルダを作り、中にPDFを入れてください。")
        sys.exit()

    pdf_files = glob.glob(os.path.join(score_dir, "*.pdf"))
    
    if not pdf_files:
        print(f"エラー: '{score_dir}' フォルダの中にPDFファイル(楽譜)がありません。")
        sys.exit()

    print("\n処理する楽譜(PDF)を番号で選択してください:")
    for i, file_path in enumerate(pdf_files):
        print(f"  [{i + 1}] {os.path.basename(file_path)}")

    while True:
        choice = input(f"\n番号を入力 (1-{len(pdf_files)}): ").strip()
        if choice.isdigit():
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(pdf_files):
                pdf_path = pdf_files[choice_idx]
                break
        print("リストにある正しい番号(数字)を入力してください。") 
    
    # Audiveris.exe のフルパス
    audiveris_exe = os.path.abspath(r".\Audiveris\Audiveris.exe")

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Completed フォルダの下に曲名のフォルダを作る
    dir_name = os.path.join("Completed", base_name)
    os.makedirs(dir_name, exist_ok=True)
    print(f"保存用ディレクトリ '{dir_name}' を作成/確認しました。")

    midi_path = os.path.join(dir_name, f"{base_name}_full_song.mid")

    # ==========================================
    # 【Step 1】 Audiveris 解析 (対話型スキップ)
    # ==========================================
    mxl_files = glob.glob(os.path.join(dir_name, "**", "*.mxl"), recursive=True)
    skip_step1 = False
    
    if mxl_files:
        ans = input(f"\n【Step 1】 解析済みのXMLがあります。Audiverisの処理をスキップしますか？ [Y/n]: ").strip().lower()
        if ans != 'n':
            skip_step1 = True
            mxl_path = mxl_files[0]
            print("Step 1 をスキップしました。")
    
    if not skip_step1:
        os.environ["_JAVA_OPTIONS"] = "-Xmx16G"
        print("\nAudiverisに最大16GBのメモリ(RAM)を強制割り当てしました！")
        
        # 事前にPDFの総ページ数（分母）を取得しておく
        try:
            temp_doc = fitz.open(pdf_path)
            total_sheets = len(temp_doc)
            temp_doc.close()
        except Exception:
            total_sheets = 1 # 万が一取得できなかった場合の保険

        completed_sheets = 0
        print(f"【Step 1】Audiverisによる全ページ一括解析を開始します (全{total_sheets}ページ)")
        
        # 初期状態(0%)を表示
        print(f"解析中: 0% (0/{total_sheets} ページ完了)".ljust(50), end='\r', flush=True)
        
        cmd = [
            audiveris_exe, "-batch", "-export",
            "-output", os.path.abspath(dir_name),
            os.path.abspath(pdf_path) 
        ]
        
        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                encoding='utf-8', 
                errors='replace',
                bufsize=1
            )
            
            for line in process.stdout:
                line = line.strip()
                
                # 1ページ分のXMLが保存された時だけカウントアップ
                if "Stored /sheet" in line and ".xml" in line:
                    completed_sheets += 1
                    # パーセントを計算して整数にする (例: 1 / 4枚 * 100 = 25%)
                    percent = int((completed_sheets / total_sheets) * 100)
                    
                    # ここで \r を使って同じ行の % を上書きする！
                    print(f"解析中: {percent}% ({completed_sheets}/{total_sheets} ページ完了)".ljust(50), end='\r', flush=True)

            process.wait()
            
            # 処理が終わったら改行して完了メッセージを出す
            print(f"解析中: 100% ({total_sheets}/{total_sheets} ページ完了)".ljust(50))
            print("全ページの解析処理が完了しました！")
            
            log_dir = os.path.join(dir_name, "log")
            os.makedirs(log_dir, exist_ok=True)
            
            # dir_name 以下のすべての .log ファイルを探して移動
            for log_file in glob.glob(os.path.join(dir_name, "**", "*.log"), recursive=True):
                # 既に log フォルダに入っているものは除外
                if os.path.abspath(os.path.dirname(log_file)) != os.path.abspath(log_dir):
                    try:
                        shutil.move(log_file, log_dir)
                    except Exception:
                        pass

            if process.returncode != 0:
                print(f"\nエラー: Audiverisが異常終了しました。(コード: {process.returncode})")
                return

            mxl_files = glob.glob(os.path.join(dir_name, "**", "*.mxl"), recursive=True)
            if not mxl_files:
                print(f"エラー: .mxl ファイルが生成されませんでした。")
                return
            mxl_path = mxl_files[0]
            print(f"見つかったXMLファイル: {mxl_path}")
            
        except Exception as e:
            print(f"\nエラー: Audiverisの実行中に問題が発生しました。\n{e}")
            return
        
        

    # ==========================================
    # 【Step 2】 Music21 論理補正 (対話型スキップ)
    # ==========================================
    skip_step2 = False
    if os.path.exists(midi_path):
        ans = input(f"\n【Step 2】 補正済みのMIDIがあります。Music21の処理をスキップしますか？ [Y/n]: ").strip().lower()
        if ans != 'n':
            skip_step2 = True
            print("Step 2 をスキップしました。")

    if not skip_step2:
        print(f"\n【Step 2】Music21によるデータ補正を開始します...")
        try:
            score_data = music21.converter.parse(mxl_path)
        except Exception as e:
            print(f"エラー: XMLデータ破損 ({e})。")
            return

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

        ans_bpm = input("2/3: テンポ(BPM)を強制指定しますか？ (数値を入力してください。指定しない場合は Enter か n): ").strip().lower()
        if ans_bpm and ans_bpm != 'n':
            try:
                bpm_val = float(ans_bpm)
                print(f"テンポを {bpm_val} に設定しています...")
                score_data.insert(0, music21.tempo.MetronomeMark(number=bpm_val))
            except ValueError:
                print("数値として認識できなかったため、BPMの強制指定をスキップします。")

        ans_rhy = input("3/3: OMRの認識漏れによる「小節の長さ不足」を自動補正しますか？ [Y/n]: ").strip().lower()
        if ans_rhy != 'n':
            print("リズムの論理補正を実行しています...")
            for part in score_data.parts:
                for m in part.getElementsByClass(music21.stream.Measure):
                    notes = m.flatten().notes
                    total_duration = sum(n.duration.quarterLength for n in notes)
                    if 0 < total_duration < 4.0:
                        diff = 4.0 - total_duration
                        if len(notes) > 0:
                            notes[-1].duration.quarterLength += diff

        score_data.write('midi', fp=midi_path)
        print(f"全ページの抽出とデータ補正完了！ MIDIを保存しました: {midi_path}")

    # ==========================================
    # 【Step 3】 sfizzによるWAVレンダリング
    # ==========================================
    output_wav = os.path.abspath(os.path.join(dir_name, f"{base_name}.wav"))
    
    print("\n【Step 3】sfizzエンジンでSFZをWAVへ一括レンダリング中...")
    
    sfz_dir = os.path.abspath(r".\AccurateSalamanderGrandPianoV6.2beta2_48khz24bit\sfz_daw")
    sfz_filename = "Accurate-SalamanderGrandPiano_flat.Recommended.sfz"
    
    midi_path_abs = os.path.abspath(midi_path)
    sfizz_exe_abs = os.path.abspath(r".\sfizz-1.2.3-win64\bin\Release\sfizz_render.exe")
    
    cmd_sfizz = [
        sfizz_exe_abs,
        "--sfz", sfz_filename,
        "--midi", midi_path_abs,
        "--wav", output_wav,
        "--samplerate", "44100" 
    ]
    
    sfizz_success = False
    try:
        subprocess.run(cmd_sfizz, check=True, cwd=sfz_dir)
        print(f"フルコーラス '{output_wav}' が出力されました")
        sfizz_success = True
    except FileNotFoundError:
        print("エラー: sfizz_render.exe が見つかりません。")
    except subprocess.CalledProcessError as e:
        print(f"エラー: sfizzのレンダリング中に問題が発生しました。\n{e}")

    # ==========================================
    # 【Step 4】 Pedalboardによる自動マスタリング
    # ==========================================
    if sfizz_success and os.path.exists(output_wav):
        print("\n【Step 4】内蔵DAW (Pedalboard) で最終マスタリングを実行中...")
        
        if not HAS_PEDALBOARD:
            print(" 警告: 'pedalboard' ライブラリがインストールされていません。")
            print("コマンドプロンプトで 'pip install pedalboard soundfile' を実行すると、次から自動マスタリングが有効になります。")
        else:
            try:
                # _mastered.wav という名前で新しいファイルを作る
                mastered_wav = output_wav.replace(".wav", "_mastered.wav")
                
                with AudioFile(output_wav) as f:
                    audio = f.read(f.frames)
                    samplerate = f.samplerate
                
                #エフェクトチェーンの構築
                board = Pedalboard([
                    # 超低音の濁りだけを切り落としてクリアに
                    HighpassFilter(cutoff_frequency_hz=30),
                    
                    # メリハリの要：アタックを遅くして「鍵盤を叩くアタック音」は潰さずに通す
                    Compressor(
                        threshold_db=-15, 
                        ratio=2.5, 
                        attack_ms=25.0,  # ここが重要！打鍵感を残す
                        release_ms=150.0
                    ),
                    
                    # なめらかさを足すだけの「隠し味」リバーブ
                    Reverb(
                        room_size=0.4,   # 空間を狭く（ホールからスタジオへ）
                        damping=0.6,     # 高音のキンキンした反射を吸収させる
                        wet_level=0.4,  # リバーブの量を前回の半分以下に
                        dry_level=0.75   # 原音（生のピアノ）をガッツリ前に出す
                    ),
                    
                    # 最終的な音量アップ
                    Gain(gain_db=2.5)
                ])
                
                effected = board(audio, samplerate)
                
                with AudioFile(mastered_wav, 'w', samplerate, effected.shape[0]) as f:
                    f.write(effected)
                
                print(f"自動マスタリング完了！ '{os.path.basename(mastered_wav)}' を出力しました！")
            
            except Exception as e:
                print(f"マスタリング中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()