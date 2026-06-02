import pygame
import fluidsynth

def run_high_quality_piano_2octaves():
    print("サウンドエンジン(FluidSynth)を起動中...")
    fs = fluidsynth.Synth()
    # --- ここから高音質化の魔法 ---
    fs.setting("synth.sample-rate", 44100.0) # 音の解像度をCD(44100)以上に引き上げる
    fs.setting("synth.polyphony", 128)       # ペダルを踏んだ時の和音の重なりが途切れないように上限を増やす

    fs.start(driver="dsound") 

    # リバーブ（空間の反響）を豊かにする
    # set_reverb(部屋の広さ, 音の吸収率, 広がり, リバーブの音量)
    fs.set_reverb(0.8, 0.4, 100.0, 0.7)

    print("巨大なSoundFontをメモリに読み込んでいます...")
    sfid = fs.sfload("UprightPianoKW-20220221.sf2")
    fs.program_select(0, sfid, 0, 0)

    pygame.init()
    screen = pygame.display.set_mode((500, 300))
    pygame.display.set_caption("2 Octave Upright Piano")

    print("\n🎹 2オクターブ版・高音質キーボードピアノが起動しました！")
    print("【重要】黒いウィンドウをクリックして一番手前にしてから弾いてください。\n")
    
    print("▼ キー配置（2オクターブ） ▼")
    print("-" * 45)
    print("【上のオクターブ: C5〜C6】")
    print("黒鍵:   2   3       5   6   7")
    print("      C#5 D#5     F#5 G#5 A#5")
    print("白鍵: Q   W   E   R   T   Y   U   I")
    print("     ド  レ  ミ  ファ ソ  ラ  シ  ド")
    print("-" * 45)
    print("【下のオクターブ: C4〜C5】")
    print("黒鍵:   S   D       G   H   J")
    print("      C#4 D#4     F#4 G#4 A#4")
    print("白鍵: Z   X   C   V   B   N   M   ,")
    print("     ド  レ  ミ  ファ ソ  ラ  シ  ド")
    print("-" * 45)

    # 2オクターブ分のキーマッピング
    key_mapping = {
        # --- 下のオクターブ (C4〜C5) ---
        pygame.K_z: 60,  # C4 (ド)
        pygame.K_s: 61,  # C#4
        pygame.K_x: 62,  # D4 (レ)
        pygame.K_d: 63,  # D#4
        pygame.K_c: 64,  # E4 (ミ)
        pygame.K_v: 65,  # F4 (ファ)
        pygame.K_g: 66,  # F#4
        pygame.K_b: 67,  # G4 (ソ)
        pygame.K_h: 68,  # G#4
        pygame.K_n: 69,  # A4 (ラ)
        pygame.K_j: 70,  # A#4
        pygame.K_m: 71,  # B4 (シ)
        pygame.K_COMMA: 72, # C5 (高いド)

        # --- 上のオクターブ (C5〜C6) ---
        pygame.K_q: 72,  # C5 (ド - 下のオクターブのカンマと同じ音)
        pygame.K_2: 73,  # C#5
        pygame.K_w: 74,  # D5 (レ)
        pygame.K_3: 75,  # D#5
        pygame.K_e: 76,  # E5 (ミ)
        pygame.K_r: 77,  # F5 (ファ)
        pygame.K_5: 78,  # F#5
        pygame.K_t: 79,  # G5 (ソ)
        pygame.K_6: 80,  # G#5
        pygame.K_y: 81,  # A5 (ラ)
        pygame.K_7: 82,  # A#5
        pygame.K_u: 83,  # B5 (シ)
        pygame.K_i: 84,  # C6 (さらに高いド)
    }

    playing_notes = set()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key in key_mapping and event.key not in playing_notes:
                    note = key_mapping[event.key]
                    fs.noteon(0, note, 100)
                    playing_notes.add(event.key)
            
            elif event.type == pygame.KEYUP:
                if event.key in key_mapping and event.key in playing_notes:
                    note = key_mapping[event.key]
                    fs.noteoff(0, note)
                    playing_notes.remove(event.key)

    print("終了処理をしています...")
    fs.delete()
    pygame.quit()
    print("再生を終了しました！")

if __name__ == "__main__":
    run_high_quality_piano_2octaves()