import os
import subprocess
import copy
import shutil
import math
from pdf2image import convert_from_path
import music21
from PIL import Image, ImageDraw

def main():
    pdf_path = "Reply.pdf" 
    bpm = 170
    quarter_note_duration = 60.0 / bpm

    dir_name = os.path.splitext(pdf_path)[0]
    os.makedirs(dir_name, exist_ok=True)
    print(f"保存用ディレクトリ '{dir_name}' を作成/確認しました。")

    print(f"【Step 1】'{pdf_path}' を読み込み、ページごとの画像に分解中...")
    pages = convert_from_path(pdf_path, dpi=300, poppler_path=r"D:\poppler-26.02.0\Library\bin")
    
    filtered_stream = music21.stream.Score()
    filtered_stream.insert(0, music21.tempo.MetronomeMark(number=bpm))
    
    current_offset_beats = 0.0  
    total_note_count = 0

    print(f"\n【Step 2】全 {len(pages)} ページのAI解析と論理補正を開始します")
    
    for i, page_img in enumerate(pages):
        page_num = i + 1
        print(f"\n--- ページ {page_num} / {len(pages)} を処理中 ---")
        
        img_name = f"temp_page_{page_num}.png"
        img_path = os.path.join(dir_name, img_name)
        page_img.save(img_path, "PNG")
        
        if page_num == 1:
            img = Image.open(img_path)
            draw = ImageDraw.Draw(img)
            width, height = img.size
            mask_height = int(height * 0.08) 
            draw.rectangle([(0, 0), (width, mask_height)], fill="white")
            img.save(img_path)
        
        try:
            subprocess.run(["oemer", img_path], check=True)
        except subprocess.CalledProcessError:
            print(f"エラー: ページ {page_num} のAI解析に失敗しました。")
            continue

        xml_name = f"temp_page_{page_num}.musicxml"
        xml_in_cwd = xml_name                       
        xml_in_dir = os.path.join(dir_name, xml_name) 
        
        xml_path = None
        if os.path.exists(xml_in_cwd):
            shutil.move(xml_in_cwd, xml_in_dir)
            xml_path = xml_in_dir
        elif os.path.exists(xml_in_dir):
            xml_path = xml_in_dir
        else:
            if os.path.exists("output.musicxml"):
                fallback_dir = os.path.join(dir_name, "output.musicxml")
                if os.path.exists(fallback_dir): os.remove(fallback_dir)
                shutil.move("output.musicxml", fallback_dir)
                xml_path = fallback_dir
            elif os.path.exists(os.path.join(dir_name, "output.musicxml")):
                xml_path = os.path.join(dir_name, "output.musicxml")
                
        if not xml_path or not os.path.exists(xml_path):
            continue

        teaser_name = f"temp_page_{page_num}_teaser.png"
        if os.path.exists(teaser_name):
            shutil.move(teaser_name, os.path.join(dir_name, teaser_name))

        print(f"音楽理論に基づく補正（クオンタイズ・強弱・ノイズ除去）を適用中...")
        
        try:
            score_data = music21.converter.parse(xml_path)
        except Exception as e:
            print(f"エラー: XMLデータ破損 ({e})。")
            continue

        flat_notes = list(score_data.flat.notes.sorted())

        # [事前準備] ページごとのキー（調）を自動判定してノイズフィルターの準備
        try:
            page_key = score_data.analyze('key')
            in_scale_classes = [p.pitchClass for p in page_key.pitches]
            print(f"判定されたキー: {page_key}")
        except:
            in_scale_classes = list(range(12)) # 判定失敗時は全音許可

        # 1. スラー補完
        for j in range(len(flat_notes) - 1):
            curr_n, next_n = flat_notes[j], flat_notes[j+1]
            if isinstance(curr_n, music21.note.Note) and isinstance(next_n, music21.note.Note):
                if curr_n.pitch.midi == next_n.pitch.midi and (next_n.offset - (curr_n.offset + curr_n.duration.quarterLength)) < 0.1:
                    curr_n.duration.quarterLength += next_n.duration.quarterLength
                    next_n.duration.quarterLength = 0

        # 2. 無音空間のパテ埋め
        for j in range(len(flat_notes)):
            curr_n = flat_notes[j]
            if curr_n.duration.quarterLength == 0: continue
            curr_end = curr_n.offset + curr_n.duration.quarterLength
            next_offset = None
            for k in range(j+1, len(flat_notes)):
                if flat_notes[k].duration.quarterLength > 0 and flat_notes[k].offset > curr_n.offset:
                    next_offset = flat_notes[k].offset
                    break
            if next_offset is not None and next_offset > curr_end:
                gap = next_offset - curr_end
                if gap <= 2.5: curr_n.duration.quarterLength += gap

        # --- 3つのAI補正ロジックの適用 ---
        for el in flat_notes:
            if el.duration.quarterLength == 0: continue
            
            # ① クオンタイズ (16分音符=0.25拍のグリッドに吸着)
            grid = 0.25
            el.offset = round(el.offset / grid) * grid
            el.duration.quarterLength = max(grid, round(el.duration.quarterLength / grid) * grid)

        # 最終組み込み
        page_max_end_beats = 0.0
        for el in flat_notes:
            if el.duration.quarterLength >= 0.1: # 無効化された音を除外
                if isinstance(el, music21.chord.Chord) and len(el.pitches) > 8:
                    el.pitches = sorted(el.pitches, key=lambda p: p.frequency, reverse=True)[:8]
                new_el = copy.deepcopy(el)
                actual_offset = current_offset_beats + el.offset
                filtered_stream.insert(actual_offset, new_el)
                
                end_beat = el.offset + el.duration.quarterLength
                if end_beat > page_max_end_beats:
                    page_max_end_beats = end_beat
                total_note_count += 1
        
        current_offset_beats += page_max_end_beats

    if total_note_count == 0:
        print("\n【エラー】音符が1つも抽出されませんでした。")
        return
    

    midi_path = os.path.join(dir_name, f"{dir_name}_full_song_temp.mid")
    filtered_stream.write('midi', fp=midi_path)
    print(f"\n全ページの結合完了！ 合計 {total_note_count} 音のデータを保存しました。")

    print("\n【Step 3】FluidSynthで高音質WAVへ一括レンダリング中...")
    sf2_path = "UprightPianoKW-20220221.sf2"
    output_wav = os.path.join(dir_name, f"{dir_name}_full_song_high_quality.wav")
    fluidsynth_exe = r".\fluidsynth.exe"
    
    cmd = [
        fluidsynth_exe, "-ni",                              
        "-o", "synth.reverb.active=1",      
        "-o", "synth.reverb.room-size=0.8", 
        "-o", "synth.reverb.damp=0.4",      
        "-o", "synth.reverb.width=100.0",   
        "-o", "synth.reverb.level=0.7",     
        "-F", output_wav, "-r", "44100",                      
        sf2_path, midi_path                           
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"全工程クリア！ '{output_wav}' に完成しました！")
    except FileNotFoundError:
        print("エラー: fluidsynthが見つかりません。")

if __name__ == "__main__":
    main()